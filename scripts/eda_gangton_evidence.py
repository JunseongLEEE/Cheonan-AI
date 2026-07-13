#!/usr/bin/env python3
"""
EDA Evidence — "현재 데이터셋만으로 깡통전세를 밝혀낼 수 있다"의 정량 근거 산출

4단계 논증:
  1. 실재성: 전세가율 ≥100% (보증금>매매가) 거래가 실측 데이터에 존재
  2. 신호성: 매매가 없이 관측 가능한 피처가 위험/안전 그룹을 단독 분리 (single-feature AUC)
  3. 구조성: 위험이 공간(구도심)·시간(특정 연도)에 구조적으로 집중
  4. 복원성: 매매가·전세가율을 피처에서 제외해도 OOF AUC 0.99로 위험 복원

출력: data/processed/eda_evidence.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

base = pd.read_parquet(PROCESSED / "recommend_base.parquet")   # 102,671 매칭 거래
oof = pd.read_parquet(ROOT / "experiments" / "exp_006_multimodel_ensemble" / "oof_predictions.parquet")
bldg = pd.read_parquet(PROCESSED / "building_residential.parquet")

ev: dict = {}

# ── 1. 실재성 ──
r = base["전세가율"].dropna()
ev["existence"] = {
    "n_matched": int(len(r)),
    "median_rate": round(float(r.median()), 4),
    "mean_rate": round(float(r.mean()), 4),
    "n_over_60": int((r > 0.60).sum()),
    "n_over_80": int((r >= 0.80).sum()),
    "n_over_90": int((r >= 0.90).sum()),
    "n_over_100": int((r >= 1.00).sum()),
    "pct_over_80": round(float((r >= 0.80).mean()), 4),
    "pct_over_100": round(float((r >= 1.00).mean()), 4),
}

# ── 2. 신호성: single-feature AUC (관측 가능 피처만) ──
df = oof.copy()
df["건물연령"] = df["거래일"].dt.year - df["건축년도"]
df.loc[(df["건물연령"] < 0) | (df["건물연령"] > 100), "건물연령"] = np.nan
df["㎡당_보증금"] = df["보증금_만원"] / df["전용면적_㎡"].replace(0, np.nan)
dong_avg = df.groupby("법정동명")["보증금_만원"].transform("mean")
df["보증금_동평균_비율"] = df["보증금_만원"] / dong_avg
dong_old = bldg.groupby("법정동명")["건물연령"].apply(lambda x: (x >= 25).mean())
df["동_노후비율"] = df["법정동명"].map(dong_old)

y = df["위험라벨"].astype(int)
ev["signal"] = {}
for feat in ["㎡당_보증금", "건물연령", "보증금_동평균_비율", "동_노후비율", "전용면적_㎡", "보증금_만원"]:
    m = df[feat].notna()
    auc = roc_auc_score(y[m], df.loc[m, feat])
    direction = "높을수록 위험" if auc >= 0.5 else "낮을수록 위험"
    ev["signal"][feat] = {"auc": round(max(auc, 1 - auc), 4), "direction": direction,
                          "risk_median": round(float(df.loc[m & (y == 1), feat].median()), 2),
                          "safe_median": round(float(df.loc[m & (y == 0), feat].median()), 2)}

# ── 3. 구조성 ──
b = base.dropna(subset=["전세가율"]).copy()
b["위험거래"] = (b["전세가율"] >= 0.80).astype(int)
dong_risk = (b.groupby("법정동명")
             .agg(위험률=("위험거래", "mean"), 거래수=("위험거래", "count"),
                  동남구=("동남구", "max")))
dong_risk = dong_risk[dong_risk["거래수"] >= 100].sort_values("위험률", ascending=False)
ev["spatial"] = {
    "n_dongs_100plus": int(len(dong_risk)),
    "risk_rate_range": [round(float(dong_risk["위험률"].min()), 3),
                        round(float(dong_risk["위험률"].max()), 3)],
    "dongnam_mean_risk": round(float(dong_risk[dong_risk["동남구"] == 1]["위험률"].mean()), 4),
    "seobuk_mean_risk": round(float(dong_risk[dong_risk["동남구"] == 0]["위험률"].mean()), 4),
    "top10": [
        {"dong": d, "risk": round(float(row["위험률"]), 3), "n": int(row["거래수"]),
         "gu": "동남구" if row["동남구"] == 1 else "서북구"}
        for d, row in dong_risk.head(10).iterrows()
    ],
}
b["연도"] = b["거래일"].dt.year
yearly = b[b["연도"].between(2019, 2026)].groupby("연도").agg(
    위험비율=("위험거래", "mean"), 거래수=("위험거래", "count"))
ev["temporal"] = {int(yy): {"risk": round(float(row["위험비율"]), 4), "n": int(row["거래수"])}
                  for yy, row in yearly.iterrows()}

# ── 4. 복원성 (exp_006 OOF) ──
probs = oof["앙상블_위험확률"]
pred = (probs >= 0.5).astype(int)
ev["recovery"] = {
    "note": "피처에 매매가·전세가율 미포함 (실서비스 조건) — 라벨은 전세가율 기반",
    "oof_auc_ensemble": round(roc_auc_score(y, probs), 4),
    "recall_at_0.5": round(recall_score(y, pred), 4),
    "precision_at_0.5": round(precision_score(y, pred), 4),
    "prob_median_risk": round(float(probs[y == 1].median()), 4),
    "prob_median_safe": round(float(probs[y == 0].median()), 4),
    "model_aucs": {m: round(roc_auc_score(y, oof[f"oof_{m}"]), 4)
                   for m in ["LightGBM", "XGBoost", "CatBoost", "RandomForest", "HistGB", "LogisticReg"]},
}

out = PROCESSED / "eda_evidence.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print(json.dumps(ev, ensure_ascii=False, indent=2))
print(f"\n✓ 저장: {out}")
