#!/usr/bin/env python3
"""
깡통전세 위험도 시뮬레이터

사용자 입력:
  - 보증금 (만원)
  - 전용면적 (㎡)
  - 법정동명
  - 건축년도
  - 구 (동남구/서북구)

출력:
  - 위험확률 (0~1)
  - 신호등 (초록/노랑/빨강)
  - SHAP 기여도 상위 5개
  - 안전점수 (동별)
"""

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_PATH = PROJECT_ROOT / "experiments" / "exp_004_threshold_80" / "models" / "lgbm_gangton_v4_t80.txt"

# 모델 로드
_model = None
_explainer = None


def _load_model():
    global _model, _explainer
    if _model is None:
        _model = lgb.Booster(model_file=str(MODEL_PATH))
        _explainer = shap.TreeExplainer(_model)
    return _model, _explainer


# 사전 계산된 통계 (ETL 결과 기반)
def _load_stats():
    df_rent = pd.read_parquet(PROCESSED_DIR / "realestate_rent.parquet")
    df_bldg = pd.read_parquet(PROCESSED_DIR / "building_residential.parquet")

    df_jeonse = df_rent[df_rent["전세여부"] == True].copy()
    df_jeonse["구코드"] = df_jeonse["_lawd_cd"].astype(str).str[:5]

    # 동별 통계
    dong_stats = df_jeonse.groupby("법정동명").agg(
        동_평균보증금=("보증금_만원", "mean"),
        동_거래건수=("보증금_만원", "count"),
    ).to_dict("index")

    # 구별 통계
    gu_stats = df_jeonse.groupby("구코드").agg(
        구_평균보증금=("보증금_만원", "mean"),
        구_평균면적=("전용면적_㎡", "mean"),
    ).to_dict("index")

    # 동별 건축물 통계
    dong_bldg = df_bldg.groupby("법정동명").agg(
        동_평균건물연령=("건물연령", "mean"),
        동_건물연령_std=("건물연령", "std"),
        동_노후비율=("건물연령", lambda x: (x >= 25).mean()),
        동_심각노후비율=("건물연령", lambda x: (x >= 35).mean()),
        동_내진비율=("내진설계", "mean"),
        동_건물수=("건물연령", "count"),
        동_평균세대수=("hhldCnt", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        동_평균총면적=("totArea", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        동_평균지상층=("grndFlrCnt", lambda x: pd.to_numeric(x, errors="coerce").mean()),
    ).to_dict("index")

    # 구조 비율
    strct_ratio = {}
    for dong in df_bldg["법정동명"].dropna().unique():
        mask = df_bldg["법정동명"] == dong
        total = mask.sum()
        if total == 0:
            continue
        strct_ratio[dong] = {
            "동_철근콘크리트비율": (df_bldg.loc[mask, "구조_대분류"] == "철근콘크리트").mean(),
            "동_벽돌비율": (df_bldg.loc[mask, "구조_대분류"] == "벽돌").mean(),
            "동_목구조비율": (df_bldg.loc[mask, "구조_대분류"] == "목구조").mean(),
        }

    # 동별 위험도 (최신 누적)
    df_jeonse_rate = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")
    dong_risk = df_jeonse_rate.groupby("법정동명").apply(
        lambda x: (x["전세가율"] >= 0.90).sum()
    ).to_dict()

    return dong_stats, gu_stats, dong_bldg, strct_ratio, dong_risk


_stats_cache = None


def _get_stats():
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = _load_stats()
    return _stats_cache


# 피처 순서 (exp_003 train.py와 동일)
FEATURE_COLS = [
    "보증금_만원", "보증금_log", "전용면적", "㎡당_보증금",
    "건물연령", "동남구", "동_평균보증금", "동_거래건수",
    "보증금_동평균_비율", "보증금_구평균_비율", "면적_구평균_비율",
    "연도별_동_위험도", "거래연도",
    "동_평균건물연령", "동_건물연령_std", "동_노후비율", "동_심각노후비율",
    "동_내진비율", "동_건물수", "동_평균세대수", "동_평균총면적", "동_평균지상층",
    "동_철근콘크리트비율", "동_벽돌비율", "동_목구조비율",
    "건물연령_동평균차", "보증금_노후도_교차",
]


def predict(
    보증금_만원: float,
    전용면적: float,
    법정동명: str,
    건축년도: int,
    구: str = "동남구",
) -> dict:
    """
    깡통전세 위험도 예측.

    Returns:
        dict with keys: risk_prob, signal, shap_top5, safety_score, features
    """
    model, explainer = _load_model()
    dong_stats, gu_stats, dong_bldg, strct_ratio, dong_risk = _get_stats()

    # 구코드
    구코드 = "44131" if 구 == "동남구" else "44133"
    동남구 = 1 if 구 == "동남구" else 0

    # 동별 통계
    ds = dong_stats.get(법정동명, {"동_평균보증금": 10000, "동_거래건수": 100})
    gs = gu_stats.get(구코드, {"구_평균보증금": 15000, "구_평균면적": 69})

    # 건축물대장 통계
    db = dong_bldg.get(법정동명, {})
    sr = strct_ratio.get(법정동명, {})
    dr = dong_risk.get(법정동명, 0)

    건물연령 = 2026 - 건축년도

    features = {
        "보증금_만원": 보증금_만원,
        "보증금_log": np.log1p(보증금_만원),
        "전용면적": 전용면적,
        "㎡당_보증금": 보증금_만원 / max(전용면적, 1),
        "건물연령": 건물연령 if 0 < 건물연령 < 100 else -999,
        "동남구": 동남구,
        "동_평균보증금": ds["동_평균보증금"],
        "동_거래건수": ds["동_거래건수"],
        "보증금_동평균_비율": 보증금_만원 / max(ds["동_평균보증금"], 1),
        "보증금_구평균_비율": 보증금_만원 / max(gs["구_평균보증금"], 1),
        "면적_구평균_비율": 전용면적 / max(gs["구_평균면적"], 1),
        "연도별_동_위험도": dr,
        "거래연도": 2026,
        "동_평균건물연령": db.get("동_평균건물연령", -999),
        "동_건물연령_std": db.get("동_건물연령_std", -999),
        "동_노후비율": db.get("동_노후비율", -999),
        "동_심각노후비율": db.get("동_심각노후비율", -999),
        "동_내진비율": db.get("동_내진비율", -999),
        "동_건물수": db.get("동_건물수", -999),
        "동_평균세대수": db.get("동_평균세대수", -999),
        "동_평균총면적": db.get("동_평균총면적", -999),
        "동_평균지상층": db.get("동_평균지상층", -999),
        "동_철근콘크리트비율": sr.get("동_철근콘크리트비율", -999),
        "동_벽돌비율": sr.get("동_벽돌비율", -999),
        "동_목구조비율": sr.get("동_목구조비율", -999),
        "건물연령_동평균차": (건물연령 - db.get("동_평균건물연령", 건물연령))
            if db.get("동_평균건물연령") else -999,
        "보증금_노후도_교차": np.log1p(보증금_만원) * db.get("동_노후비율", 0.5)
            if db.get("동_노후비율") else -999,
    }

    X = pd.DataFrame([features])[FEATURE_COLS]
    risk_prob = float(model.predict(X)[0])

    # SHAP
    shap_values = explainer.shap_values(X)
    if isinstance(shap_values, list):
        shap_arr = shap_values[1][0]
    else:
        shap_arr = shap_values[0]

    shap_df = pd.DataFrame({
        "feature": FEATURE_COLS,
        "shap_value": shap_arr,
        "feature_value": X.iloc[0].values,
    }).sort_values("shap_value", key=abs, ascending=False)

    # 신호등
    if risk_prob >= 0.7:
        signal = "빨강"
        signal_label = "위험"
    elif risk_prob >= 0.3:
        signal = "노랑"
        signal_label = "주의"
    else:
        signal = "초록"
        signal_label = "안전"

    # 안전점수 조회
    try:
        df_safety = pd.read_parquet(PROCESSED_DIR / "dong_safety_score.parquet")
        safety_row = df_safety[df_safety["법정동명"] == 법정동명]
        safety_score = float(safety_row["종합안전점수"].iloc[0]) if len(safety_row) > 0 else None
    except Exception:
        safety_score = None

    return {
        "risk_prob": round(risk_prob, 4),
        "signal": signal,
        "signal_label": signal_label,
        "safety_score": safety_score,
        "shap_top5": shap_df.head(5).to_dict("records"),
        "input": {
            "보증금_만원": 보증금_만원,
            "전용면적": 전용면적,
            "법정동명": 법정동명,
            "건축년도": 건축년도,
            "구": 구,
        },
    }


def main():
    """데모 시나리오 실행."""
    print("=" * 60)
    print("깡통전세 위험도 시뮬레이터")
    print("=" * 60)

    # 시나리오 1: 페르소나 A — 안서동 다가구 보증금 5000만원
    scenarios = [
        {"보증금_만원": 5000, "전용면적": 33, "법정동명": "안서동", "건축년도": 2000, "구": "동남구"},
        {"보증금_만원": 7000, "전용면적": 59, "법정동명": "두정동", "건축년도": 2005, "구": "서북구"},
        {"보증금_만원": 15000, "전용면적": 84, "법정동명": "불당동", "건축년도": 2018, "구": "서북구"},
        {"보증금_만원": 3000, "전용면적": 20, "법정동명": "원성동", "건축년도": 1990, "구": "동남구"},
        {"보증금_만원": 20000, "전용면적": 84, "법정동명": "성성동", "건축년도": 2022, "구": "서북구"},
    ]

    signal_icons = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}

    for i, s in enumerate(scenarios, 1):
        print(f"\n--- 시나리오 {i} ---")
        print(f"  {s['법정동명']} | 보증금 {s['보증금_만원']:,}만원 | {s['전용면적']}㎡ | {s['건축년도']}년식")

        result = predict(**s)

        icon = signal_icons[result["signal"]]
        print(f"  → {icon} {result['signal_label']} (위험확률 {result['risk_prob']:.1%})")
        if result["safety_score"]:
            print(f"  → 동네 안전점수: {result['safety_score']:.1f}/100")

        print(f"  → 위험 요인 (SHAP):")
        for item in result["shap_top5"]:
            direction = "↑위험" if item["shap_value"] > 0 else "↓안전"
            print(f"     {item['feature']}: {item['shap_value']:+.3f} ({direction})")


if __name__ == "__main__":
    main()
