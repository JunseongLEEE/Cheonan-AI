#!/usr/bin/env python3
"""
전세깡통 안전매물 추천시스템 — exp_006 앙상블 기반

파이프라인
──────────
  1. exp_006 voting 앙상블(LightGBM+XGBoost+CatBoost+HistGB)로
     전세가율 매칭 전 거래에 위험확률 배치 예측 → recommend_base.parquet 캐시
  2. recommend(예산, 면적, 우선순위) →
     - 예산·면적 필터 + 최근 18개월 거래
     - 동별 집계: 앙상블 위험확률, 8축 안전점수, 전세가율 추세
     - 종합 추천점수 = w_risk·(1-위험확률) + w_safety·안전점수 + w_axis·우선축점수
     - Top-k 동네 + 동별 대표 안전 매물(실거래) 반환

사용 예
───────
  from scripts.recommender import recommend
  out = recommend(budget=8000, area_min=20, area_max=50, priority="교통")
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXP006_DIR = PROJECT_ROOT / "experiments" / "exp_006_multimodel_ensemble"
BASE_PATH = PROCESSED_DIR / "recommend_base.parquet"

AXES = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]

_base_cache: pd.DataFrame | None = None
_safety_cache: pd.DataFrame | None = None


def build_base(force: bool = False) -> pd.DataFrame:
    """전 거래 위험확률 배치 예측 → 캐시. (train.py 실행 후 1회)"""
    if BASE_PATH.exists() and not force:
        return pd.read_parquet(BASE_PATH)

    import sys
    import joblib
    sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "exp_004_threshold_80"))
    from train import load_and_merge, compute_dong_historical_risk, engineer_features

    bundle = joblib.load(EXP006_DIR / "models" / "ensemble_voting.joblib")
    members, feature_cols = bundle["members"], bundle["feature_cols"]

    df = load_and_merge()
    df = compute_dong_historical_risk(df)
    X = engineer_features(df).fillna(-999)[feature_cols]

    probs = np.mean([m.predict_proba(X)[:, 1] for m in members.values()], axis=0)

    base = df[["법정동명", "단지명", "보증금_만원", "전용면적_㎡", "건축년도",
               "거래일", "전세가율", "동남구"]].copy()
    base["앙상블_위험확률"] = probs
    base.to_parquet(BASE_PATH)
    print(f"✓ recommend_base 생성: {len(base):,}건 → {BASE_PATH}")
    return base


def _get_base() -> pd.DataFrame:
    global _base_cache
    if _base_cache is None:
        _base_cache = build_base()
    return _base_cache


def _get_safety() -> pd.DataFrame:
    global _safety_cache
    if _safety_cache is None:
        _safety_cache = pd.read_parquet(PROCESSED_DIR / "dong_safety_score.parquet")
    return _safety_cache


def recommend(
    budget: float,
    area_min: float = 0,
    area_max: float = 999,
    priority: str | None = None,
    gu: str | None = None,
    top_k: int = 5,
    budget_tolerance: float = 0.25,
    months: int = 18,
) -> dict:
    """
    예산·조건 기반 안전 동네 + 매물 추천.

    Args:
        budget: 보증금 예산 (만원)
        area_min/area_max: 희망 전용면적 범위 (㎡)
        priority: 우선 안전축 (금융안전/건물노후/침수위험/치안/소방/교통/편의시설/환경)
        gu: "동남구"/"서북구" 선호 (None이면 전체)
        top_k: 추천 동네 수
    """
    base = _get_base()
    safety = _get_safety()

    cutoff = base["거래일"].max() - pd.DateOffset(months=months)
    lo, hi = budget * (1 - budget_tolerance), budget * (1 + budget_tolerance)

    cand = base[
        (base["거래일"] >= cutoff)
        & base["보증금_만원"].between(lo, hi)
        & base["전용면적_㎡"].between(area_min, area_max)
    ].copy()
    if gu == "동남구":
        cand = cand[cand["동남구"] == 1]
    elif gu == "서북구":
        cand = cand[cand["동남구"] == 0]

    if len(cand) == 0:
        return {"query": {"budget": budget, "priority": priority}, "dongs": [],
                "message": "조건에 맞는 최근 거래가 없습니다. 예산 범위를 넓혀보세요."}

    # ── 동별 집계 ──
    agg = cand.groupby("법정동명").agg(
        거래수=("보증금_만원", "count"),
        평균_위험확률=("앙상블_위험확률", "mean"),
        중위_보증금=("보증금_만원", "median"),
        평균_전세가율=("전세가율", "mean"),
    ).reset_index()
    agg = agg[agg["거래수"] >= 3]  # 표본 3건 미만 동 제외

    axis_cols = [f"{a}_점수" for a in AXES if f"{a}_점수" in safety.columns]
    agg = agg.merge(
        safety[["법정동명", "종합안전점수", "신호등", *axis_cols]],
        on="법정동명", how="inner",
    )

    # ── 종합 추천점수 (0~100) ──
    w_risk, w_safety, w_axis = 0.5, 0.3, 0.2
    risk_score = (1 - agg["평균_위험확률"]) * 100
    safety_score = agg["종합안전점수"]
    if priority and f"{priority}_점수" in agg.columns:
        axis_score = agg[f"{priority}_점수"] * 100
    else:
        axis_score = safety_score
        w_risk, w_safety, w_axis = 0.6, 0.4, 0.0
    agg["추천점수"] = w_risk * risk_score + w_safety * safety_score + w_axis * axis_score
    agg = agg.sort_values("추천점수", ascending=False).head(top_k)

    # ── 동별 대표 안전 매물 (위험확률 최저 실거래 3건) ──
    dongs = []
    for _, row in agg.iterrows():
        listings = (
            cand[cand["법정동명"] == row["법정동명"]]
            .nsmallest(3, "앙상블_위험확률")
            [["단지명", "보증금_만원", "전용면적_㎡", "건축년도", "앙상블_위험확률", "거래일"]]
        )
        dongs.append({
            "법정동명": row["법정동명"],
            "추천점수": round(float(row["추천점수"]), 1),
            "신호등": str(row["신호등"]),
            "종합안전점수": round(float(row["종합안전점수"]), 1),
            "평균_위험확률": round(float(row["평균_위험확률"]), 3),
            "중위_보증금_만원": round(float(row["중위_보증금"])),
            "평균_전세가율": round(float(row["평균_전세가율"]), 3)
                if pd.notna(row["평균_전세가율"]) else None,
            "거래수": int(row["거래수"]),
            "대표매물": [
                {
                    "단지명": str(l["단지명"]),
                    "보증금_만원": float(l["보증금_만원"]),
                    "전용면적_㎡": float(l["전용면적_㎡"]),
                    "건축년도": int(l["건축년도"]) if pd.notna(l["건축년도"]) else None,
                    "위험확률": round(float(l["앙상블_위험확률"]), 3),
                    "거래일": str(l["거래일"].date()),
                }
                for _, l in listings.iterrows()
            ],
        })

    return {
        "query": {
            "budget_만원": budget, "area": [area_min, area_max],
            "priority": priority, "gu": gu,
            "budget_range": [round(lo), round(hi)], "months": months,
        },
        "n_candidates": int(len(cand)),
        "dongs": dongs,
    }


if __name__ == "__main__":
    import json
    build_base(force=True)
    out = recommend(budget=8000, area_min=20, area_max=60, priority="교통")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:3000])
