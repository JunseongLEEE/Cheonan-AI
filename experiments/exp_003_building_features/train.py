#!/usr/bin/env python3
"""
exp_003: 깡통전세 분류기 — 건축물대장 피처 연계 (LightGBM + SHAP)

exp_002 대비 변경점:
- 동별 건축물대장 집계 피처 추가:
  - 동_평균건물연령, 동_노후비율(25년+), 동_내진비율
  - 동_철근콘크리트비율, 동_벽돌비율
  - 동_평균세대수, 동_평균총면적
- 매매가 피처 제외 유지 (실서비스 시나리오)
- 건축년도 기반 개별 건물연령 + 동 수준 건물 통계 동시 활용
"""

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import (
    classification_report,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXP_DIR = Path(__file__).resolve().parent
MODELS_DIR = EXP_DIR / "models"
SHAP_DIR = EXP_DIR / "shap"
MODELS_DIR.mkdir(exist_ok=True)
SHAP_DIR.mkdir(exist_ok=True)

SEED = 42
np.random.seed(SEED)


def load_and_merge():
    """전세가율 + 건축물대장 동별 집계 → 통합 데이터셋."""
    df_rate = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")
    df_rent = pd.read_parquet(PROCESSED_DIR / "realestate_rent.parquet")
    df_bldg = pd.read_parquet(PROCESSED_DIR / "building_residential.parquet")

    # --- 동별 건축물대장 집계 ---
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
    ).reset_index()

    # 구조 비율
    for strct in ["철근콘크리트", "벽돌", "목구조"]:
        col = f"동_{strct}비율"
        strct_ratio = (
            df_bldg.groupby("법정동명")["구조_대분류"]
            .apply(lambda x: (x == strct).mean())
            .reset_index()
            .rename(columns={"구조_대분류": col})
        )
        dong_bldg = dong_bldg.merge(strct_ratio, on="법정동명", how="left")

    print(f"동별 건축물 통계: {len(dong_bldg)}개 동")

    # --- 전세 데이터 준비 ---
    df_jeonse = df_rent[df_rent["전세여부"] == True].copy()
    df_jeonse["구코드"] = df_jeonse["_lawd_cd"].astype(str).str[:5]
    df_jeonse["동남구"] = (df_jeonse["구코드"] == "44131").astype(int)
    df_jeonse["연월"] = df_jeonse["거래일"].dt.to_period("M")

    # 동별 전세 통계
    df_jeonse = df_jeonse.sort_values("거래일")
    dong_stats = (
        df_jeonse.groupby("법정동명")
        .agg(동_평균보증금=("보증금_만원", "mean"), 동_거래건수=("보증금_만원", "count"))
        .reset_index()
    )
    df_jeonse = df_jeonse.merge(dong_stats, on="법정동명", how="left")

    # 구별 통계
    gu_stats = (
        df_jeonse.groupby("구코드")
        .agg(구_평균보증금=("보증금_만원", "mean"), 구_평균면적=("전용면적_㎡", "mean"))
        .reset_index()
    )
    df_jeonse = df_jeonse.merge(gu_stats, on="구코드", how="left")

    # 건축물대장 동별 통계 조인
    df_jeonse = df_jeonse.merge(dong_bldg, on="법정동명", how="left")

    # 전세가율 매칭
    df_rate["연월"] = df_rate["연월"].astype(str)
    df_jeonse["연월_str"] = df_jeonse["연월"].astype(str)

    merged = df_jeonse.merge(
        df_rate[["법정동명", "단지명", "연월", "전세가율", "매매가_중앙값"]],
        left_on=["법정동명", "단지명", "연월_str"],
        right_on=["법정동명", "단지명", "연월"],
        how="inner",
        suffixes=("", "_rate"),
    )

    print(f"전세 거래: {len(df_jeonse):,}건")
    print(f"전세가율 매칭: {len(merged):,}건")
    print(f"건축물 통계 매칭: {merged['동_평균건물연령'].notna().sum():,}건")

    return merged


def compute_dong_historical_risk(df):
    """동별 과거 위험 누적 건수."""
    df = df.copy()
    df["거래연도_tmp"] = df["거래일"].dt.year
    df["위험여부_tmp"] = (df["전세가율"] >= 0.90).astype(int)

    dong_year_risk = (
        df.groupby(["법정동명", "거래연도_tmp"])["위험여부_tmp"]
        .sum()
        .reset_index()
        .rename(columns={"위험여부_tmp": "연도_위험건수"})
    )
    dong_year_risk = dong_year_risk.sort_values(["법정동명", "거래연도_tmp"])
    dong_year_risk["누적_위험건수"] = (
        dong_year_risk.groupby("법정동명")["연도_위험건수"]
        .apply(lambda s: s.cumsum().shift(1, fill_value=0))
        .reset_index(level=0, drop=True)
    )

    df = df.merge(
        dong_year_risk[["법정동명", "거래연도_tmp", "누적_위험건수"]],
        on=["법정동명", "거래연도_tmp"],
        how="left",
    )
    df["연도별_동_위험도"] = df["누적_위험건수"].fillna(0)
    df.drop(columns=["거래연도_tmp", "위험여부_tmp", "누적_위험건수"], inplace=True)
    return df


def engineer_features(df):
    """피처 엔지니어링 — 건축물대장 동별 피처 추가."""
    features = pd.DataFrame()

    # === 기존 피처 (exp_002) ===
    features["보증금_만원"] = df["보증금_만원"]
    features["보증금_log"] = np.log1p(df["보증금_만원"])
    features["전용면적"] = df["전용면적_㎡"]
    features["㎡당_보증금"] = df["보증금_만원"] / df["전용면적_㎡"].replace(0, np.nan)

    features["건물연령"] = 2026 - df["건축년도"]
    features.loc[features["건물연령"] < 0, "건물연령"] = np.nan
    features.loc[features["건물연령"] > 100, "건물연령"] = np.nan

    features["동남구"] = df["동남구"]
    features["동_평균보증금"] = df["동_평균보증금"]
    features["동_거래건수"] = df["동_거래건수"]
    features["보증금_동평균_비율"] = df["보증금_만원"] / df["동_평균보증금"].replace(0, np.nan)
    features["보증금_구평균_비율"] = df["보증금_만원"] / df["구_평균보증금"].replace(0, np.nan)
    features["면적_구평균_비율"] = df["전용면적_㎡"] / df["구_평균면적"].replace(0, np.nan)
    features["연도별_동_위험도"] = df["연도별_동_위험도"]

    if "거래일" in df.columns:
        features["거래연도"] = df["거래일"].dt.year

    # === 신규: 건축물대장 동별 집계 피처 ===
    features["동_평균건물연령"] = df["동_평균건물연령"]
    features["동_건물연령_std"] = df["동_건물연령_std"]
    features["동_노후비율"] = df["동_노후비율"]
    features["동_심각노후비율"] = df["동_심각노후비율"]
    features["동_내진비율"] = df["동_내진비율"]
    features["동_건물수"] = df["동_건물수"]
    features["동_평균세대수"] = df["동_평균세대수"]
    features["동_평균총면적"] = df["동_평균총면적"]
    features["동_평균지상층"] = df["동_평균지상층"]
    features["동_철근콘크리트비율"] = df["동_철근콘크리트비율"]
    features["동_벽돌비율"] = df["동_벽돌비율"]
    features["동_목구조비율"] = df["동_목구조비율"]

    # === 교차 피처 ===
    # 개별 건물연령 vs 동 평균 건물연령 차이 (이 건물이 동네 평균보다 얼마나 오래된지)
    features["건물연령_동평균차"] = features["건물연령"] - df["동_평균건물연령"]
    # 보증금 대비 동 노후도 (노후 동네에서 높은 보증금 = 위험 신호)
    features["보증금_노후도_교차"] = features["보증금_log"] * df["동_노후비율"]

    return features


def create_labels(df):
    labels = pd.Series(np.nan, index=df.index)
    labels[df["전세가율"] >= 0.90] = 1
    labels[df["전세가율"] <= 0.60] = 0

    print(f"\n라벨 분포:")
    print(f"  위험 (1): {(labels == 1).sum():,}건")
    print(f"  안전 (0): {(labels == 0).sum():,}건")
    print(f"  제외 (NaN): {labels.isna().sum():,}건")

    return labels


def train_and_evaluate(features, labels):
    """5-fold CV + SHAP."""
    mask = labels.notna()
    X = features.loc[mask].copy()
    y = labels.loc[mask].astype(int).copy()

    feature_cols = X.columns.tolist()
    X = X.fillna(-999)

    print(f"\n학습 데이터: {len(X):,}건 (위험 {y.sum():,} / 안전 {(1-y).sum():,})")
    print(f"피처 {len(feature_cols)}개: {feature_cols}")

    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": SEED,
        "is_unbalance": True,
    }

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof_preds = np.zeros(len(X))
    fold_scores = []
    models = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        train_set = lgb.Dataset(X_train, y_train)
        val_set = lgb.Dataset(X_val, y_val, reference=train_set)

        model = lgb.train(
            params,
            train_set,
            num_boost_round=500,
            valid_sets=[val_set],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
        )

        val_pred = model.predict(X_val)
        oof_preds[val_idx] = val_pred

        auc = roc_auc_score(y_val, val_pred)
        f1 = f1_score(y_val, (val_pred >= 0.5).astype(int))
        fold_scores.append({"fold": fold + 1, "auc": auc, "f1": f1})
        models.append(model)

        print(f"  Fold {fold+1}: AUC={auc:.4f} F1={f1:.4f}")

    oof_auc = roc_auc_score(y, oof_preds)
    oof_f1 = f1_score(y, (oof_preds >= 0.5).astype(int))
    print(f"\n=== OOF 성능 ===")
    print(f"  AUC: {oof_auc:.4f}")
    print(f"  F1:  {oof_f1:.4f}")

    print("\n분류 리포트:")
    print(classification_report(y, (oof_preds >= 0.5).astype(int),
                              target_names=["안전", "위험"]))

    best_model = models[np.argmax([s["auc"] for s in fold_scores])]
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": best_model.feature_importance(importance_type="gain"),
    }).sort_values("importance", ascending=False)

    print("\n피처 중요도:")
    for _, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.0f}")

    best_model.save_model(str(MODELS_DIR / "lgbm_gangton_v3_bldg.txt"))

    print("\nSHAP 분석 중...")
    explainer = shap.TreeExplainer(best_model)
    shap_values = explainer.shap_values(X.iloc[:1000])

    if isinstance(shap_values, list):
        shap_arr = shap_values[1]
    else:
        shap_arr = shap_values

    shap_importance = pd.DataFrame({
        "feature": feature_cols,
        "mean_abs_shap": np.abs(shap_arr).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)

    print("\nSHAP 피처 중요도:")
    for _, row in shap_importance.iterrows():
        print(f"  {row['feature']}: {row['mean_abs_shap']:.4f}")

    shap_importance.to_csv(SHAP_DIR / "shap_importance.csv", index=False)

    X_all = features.fillna(-999)
    all_preds = best_model.predict(X_all)

    return {
        "oof_auc": oof_auc,
        "oof_f1": oof_f1,
        "fold_scores": fold_scores,
        "importance": importance.to_dict("records"),
        "shap_importance": shap_importance.to_dict("records"),
        "all_preds": all_preds,
    }


def main():
    print("=" * 60)
    print("exp_003: 깡통전세 분류기 — 건축물대장 피처 (LightGBM)")
    print("=" * 60)

    df = load_and_merge()
    df = compute_dong_historical_risk(df)
    features = engineer_features(df)
    labels = create_labels(df)
    results = train_and_evaluate(features, labels)

    train_log = {
        "experiment_id": "exp_003_building_features",
        "model_type": "gangton_classifier",
        "hypothesis": "동별 건축물대장 집계 피처(노후비율, 내진비율, 구조분포, 세대수) 추가 → 건물 인프라 수준이 깡통전세 위험도와 상관있는지 검증",
        "base_experiment": "exp_002_no_trade_price",
        "added_features": [
            "동_평균건물연령", "동_건물연령_std", "동_노후비율", "동_심각노후비율",
            "동_내진비율", "동_건물수", "동_평균세대수", "동_평균총면적", "동_평균지상층",
            "동_철근콘크리트비율", "동_벽돌비율", "동_목구조비율",
            "건물연령_동평균차", "보증금_노후도_교차",
        ],
        "cv_score": results["oof_auc"],
        "cv_std": float(np.std([s["auc"] for s in results["fold_scores"]])),
        "metric": "AUC",
        "f1_score": results["oof_f1"],
        "n_folds": 5,
        "n_samples": int(sum(labels.notna())),
        "n_positive": int((labels == 1).sum()),
        "n_negative": int((labels == 0).sum()),
        "seed": SEED,
        "shap_generated": True,
        "feature_importance": results["importance"][:10],
        "shap_importance": results["shap_importance"][:10],
    }

    with open(EXP_DIR / "train_log.json", "w", encoding="utf-8") as f:
        json.dump(train_log, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n실험 완료")
    print(f"  AUC: {results['oof_auc']:.4f}")
    print(f"  F1:  {results['oof_f1']:.4f}")
    print(f"  모델: {MODELS_DIR / 'lgbm_gangton_v3_bldg.txt'}")
    print(f"  SHAP: {SHAP_DIR / 'shap_importance.csv'}")


if __name__ == "__main__":
    main()
