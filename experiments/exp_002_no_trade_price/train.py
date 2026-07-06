#!/usr/bin/env python3
"""
exp_002: 깡통전세 분류기 — 매매가 제외 (LightGBM + 휴리스틱 약지도 + SHAP)

exp_001 대비 변경점:
- '보증금_매매가비율' 피처 제거 (실서비스에서 매매가를 모를 수 있음)
- 대체 proxy 피처 추가:
  - 보증금_구평균_비율: 보증금 / 구 평균 보증금
  - 면적_구평균_비율: 전용면적 / 구 평균 전용면적
  - 연도별_동_위험도: 해당 동에서 과거 위험 라벨 누적 건수 (historical risk)

라벨 전략 (exp_001 동일):
- Positive (위험): 전세가율 >= 90%
- Negative (안전): 전세가율 <= 60%
- Unlabeled: 60~90% 사이 → 학습에서 제외
"""

import json
import sys
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
    """전세가율 + 건축물대장 → 통합 데이터셋."""
    df_rate = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")
    df_rent = pd.read_parquet(PROCESSED_DIR / "realestate_rent.parquet")
    df_bldg = pd.read_parquet(PROCESSED_DIR / "building_residential.parquet")

    # 전월세에서 전세만
    df_jeonse = df_rent[df_rent["전세여부"] == True].copy()

    # 구 코드
    df_jeonse["구코드"] = df_jeonse["_lawd_cd"].astype(str).str[:5]
    df_jeonse["동남구"] = (df_jeonse["구코드"] == "44131").astype(int)

    # 연월
    df_jeonse["연월"] = df_jeonse["거래일"].dt.to_period("M")

    # 동별 통계
    df_jeonse = df_jeonse.sort_values("거래일")
    dong_stats = (
        df_jeonse.groupby("법정동명")
        .agg(동_평균보증금=("보증금_만원", "mean"), 동_거래건수=("보증금_만원", "count"))
        .reset_index()
    )
    df_jeonse = df_jeonse.merge(dong_stats, on="법정동명", how="left")

    # 구별 통계 (신규 proxy 피처용)
    gu_stats = (
        df_jeonse.groupby("구코드")
        .agg(
            구_평균보증금=("보증금_만원", "mean"),
            구_평균면적=("전용면적_㎡", "mean"),
        )
        .reset_index()
    )
    df_jeonse = df_jeonse.merge(gu_stats, on="구코드", how="left")

    # 전세가율 매칭 (동+단지+연월 기준)
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

    return merged


def compute_dong_historical_risk(df):
    """
    연도별_동_위험도: 각 거래 시점 기준으로 해당 동에서
    과거에 위험(전세가율 >= 0.90)으로 판정된 건수를 누적 집계.
    Data leakage 방지를 위해 해당 행의 연도 이전 데이터만 사용.
    """
    df = df.copy()
    df["거래연도_tmp"] = df["거래일"].dt.year
    df["위험여부_tmp"] = (df["전세가율"] >= 0.90).astype(int)

    # 동+연도별 위험 건수 누적
    dong_year_risk = (
        df.groupby(["법정동명", "거래연도_tmp"])["위험여부_tmp"]
        .sum()
        .reset_index()
        .rename(columns={"위험여부_tmp": "연도_위험건수"})
    )
    dong_year_risk = dong_year_risk.sort_values(["법정동명", "거래연도_tmp"])

    # 누적합 (해당 연도 이전까지만 = shift 사용)
    dong_year_risk["누적_위험건수"] = (
        dong_year_risk.groupby("법정동명")["연도_위험건수"]
        .cumsum()
        .shift(1, fill_value=0)
    )
    # shift가 그룹 경계를 넘을 수 있으므로 재계산
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
    """피처 엔지니어링 — 매매가 관련 피처 제외, proxy 피처 추가."""

    features = pd.DataFrame()

    # 보증금 관련
    features["보증금_만원"] = df["보증금_만원"]
    features["보증금_log"] = np.log1p(df["보증금_만원"])

    # 면적 관련
    features["전용면적"] = df["전용면적_㎡"]

    # 단위 면적당 보증금
    features["㎡당_보증금"] = df["보증금_만원"] / df["전용면적_㎡"].replace(0, np.nan)

    # 건축년도 → 건물연령
    features["건물연령"] = 2026 - df["건축년도"]
    features.loc[features["건물연령"] < 0, "건물연령"] = np.nan
    features.loc[features["건물연령"] > 100, "건물연령"] = np.nan

    # 구 더미
    features["동남구"] = df["동남구"]

    # 동별 통계
    features["동_평균보증금"] = df["동_평균보증금"]
    features["동_거래건수"] = df["동_거래건수"]

    # 보증금 vs 동 평균 비율
    features["보증금_동평균_비율"] = df["보증금_만원"] / df["동_평균보증금"].replace(0, np.nan)

    # --- exp_002 신규 proxy 피처 ---
    # 보증금_구평균_비율: 보증금 / 구 평균 보증금
    features["보증금_구평균_비율"] = df["보증금_만원"] / df["구_평균보증금"].replace(0, np.nan)

    # 보증금_규모: log of deposit (보증금_log와 동일하지만 명시적 alias)
    # 이미 보증금_log가 있으므로 별도 추가하지 않음

    # 면적_구평균_비율: 전용면적 / 구 평균 전용면적
    features["면적_구평균_비율"] = df["전용면적_㎡"] / df["구_평균면적"].replace(0, np.nan)

    # 연도별_동_위험도: 해당 동의 과거 위험 라벨 누적 건수
    features["연도별_동_위험도"] = df["연도별_동_위험도"]

    # --- 제거됨: 보증금_매매가비율 (매매가 정보 불필요) ---

    # 거래 시점 (연도)
    if "거래일" in df.columns:
        features["거래연도"] = df["거래일"].dt.year

    return features


def create_labels(df):
    """
    휴리스틱 약지도 라벨 생성.

    위험 (1): 전세가율 >= 0.90
    안전 (0): 전세가율 <= 0.60
    제외 (NaN): 0.60 < 전세가율 < 0.90
    """
    labels = pd.Series(np.nan, index=df.index)
    labels[df["전세가율"] >= 0.90] = 1  # 위험
    labels[df["전세가율"] <= 0.60] = 0  # 안전

    print(f"\n라벨 분포:")
    print(f"  위험 (1): {(labels == 1).sum():,}건")
    print(f"  안전 (0): {(labels == 0).sum():,}건")
    print(f"  제외 (NaN): {labels.isna().sum():,}건")

    return labels


def train_and_evaluate(features, labels):
    """5-fold CV + SHAP."""
    # 라벨이 있는 데이터만
    mask = labels.notna()
    X = features.loc[mask].copy()
    y = labels.loc[mask].astype(int).copy()

    # 결측 처리
    feature_cols = X.columns.tolist()
    X = X.fillna(-999)

    print(f"\n학습 데이터: {len(X):,}건 (위험 {y.sum():,} / 안전 {(1-y).sum():,})")
    print(f"피처 {len(feature_cols)}개: {feature_cols}")

    # LightGBM params
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

    # 5-fold CV
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

    # 전체 OOF 성능
    oof_auc = roc_auc_score(y, oof_preds)
    oof_f1 = f1_score(y, (oof_preds >= 0.5).astype(int))
    print(f"\n=== OOF 성능 ===")
    print(f"  AUC: {oof_auc:.4f}")
    print(f"  F1:  {oof_f1:.4f}")

    # Classification report
    print("\n분류 리포트:")
    print(classification_report(y, (oof_preds >= 0.5).astype(int),
                              target_names=["안전", "위험"]))

    # Feature importance
    best_model = models[np.argmax([s["auc"] for s in fold_scores])]
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": best_model.feature_importance(importance_type="gain"),
    }).sort_values("importance", ascending=False)

    print("\n피처 중요도:")
    for _, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.0f}")

    # 모델 저장
    best_model.save_model(str(MODELS_DIR / "lgbm_gangton_v2_no_trade.txt"))

    # SHAP
    print("\nSHAP 분석 중...")
    explainer = shap.TreeExplainer(best_model)
    shap_values = explainer.shap_values(X.iloc[:1000])

    # SHAP summary → JSON으로 저장
    if isinstance(shap_values, list):
        shap_arr = shap_values[1]  # positive class
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

    # 전체 데이터에 예측 점수 부여 (라벨 없는 데이터 포함)
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
    print("exp_002: 깡통전세 분류기 — 매매가 제외 (LightGBM)")
    print("=" * 60)

    # 1. 데이터 로드 + 병합
    df = load_and_merge()

    # 2. 연도별 동 위험도 계산 (라벨 기반이므로 피처 엔지니어링 전에 수행)
    df = compute_dong_historical_risk(df)

    # 3. 피처 엔지니어링
    features = engineer_features(df)

    # 4. 라벨 생성
    labels = create_labels(df)

    # 5. 학습 + 평가
    results = train_and_evaluate(features, labels)

    # 6. train_log.json 저장
    train_log = {
        "experiment_id": "exp_002_no_trade_price",
        "model_type": "gangton_classifier",
        "hypothesis": "매매가(보증금_매매가비율) 피처 제거 후 구별 평균 비율 + 동 위험도 proxy로 대체. 실서비스에서 매매가 미입력 시나리오 검증.",
        "removed_features": ["보증금_매매가비율"],
        "added_features": ["보증금_구평균_비율", "면적_구평균_비율", "연도별_동_위험도"],
        "cv_score": results["oof_auc"],
        "cv_std": np.std([s["auc"] for s in results["fold_scores"]]),
        "metric": "AUC",
        "f1_score": results["oof_f1"],
        "n_folds": 5,
        "n_samples": int(sum(labels.notna())),
        "n_positive": int((labels == 1).sum()),
        "n_negative": int((labels == 0).sum()),
        "seed": SEED,
        "cheonan_codes": ["44131", "44133"],
        "shap_generated": True,
        "feature_importance": results["importance"][:10],
        "shap_importance": results["shap_importance"][:10],
    }

    with open(EXP_DIR / "train_log.json", "w", encoding="utf-8") as f:
        json.dump(train_log, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n실험 완료")
    print(f"  AUC: {results['oof_auc']:.4f}")
    print(f"  F1:  {results['oof_f1']:.4f}")
    print(f"  모델: {MODELS_DIR / 'lgbm_gangton_v2_no_trade.txt'}")
    print(f"  SHAP: {SHAP_DIR / 'shap_importance.csv'}")
    print(f"  로그: {EXP_DIR / 'train_log.json'}")


if __name__ == "__main__":
    main()
