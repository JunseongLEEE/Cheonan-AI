#!/usr/bin/env python3
"""
exp_006: 깡통전세 다중모델 앙상블 — LightGBM 단일 모델을 넘어
6개 이종 모델 + soft-voting + stacking을 5-fold CV로 비교한다.

exp_004 대비 변경점:
- 동일 데이터 파이프라인/라벨(80% 임계) 유지 → 공정 비교
- 신규 모델: XGBoost, CatBoost, RandomForest, HistGradientBoosting, LogisticRegression
- 앙상블: soft-voting(상위 4개 부스팅 계열) + stacking(LogReg meta)
- 앙상블 OOF 확률 저장 → 추천시스템(scripts/recommender.py)의 위험 점수원
"""

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXP_DIR = Path(__file__).resolve().parent
MODELS_DIR = EXP_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

SEED = 42
np.random.seed(SEED)

# ─────────────────────────────────────────────
# 데이터 파이프라인 (exp_004와 동일 — 공정 비교를 위해 재사용)
# ─────────────────────────────────────────────
import sys
sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "exp_004_threshold_80"))
from train import (  # noqa: E402
    load_and_merge,
    compute_dong_historical_risk,
    engineer_features,
    create_labels,
)


def get_models():
    """비교할 모델 사전. 각 항목은 (이름, sklearn-호환 predict_proba 지원 여부)."""
    import xgboost as xgb
    from catboost import CatBoostClassifier

    return {
        "LightGBM": lgb.LGBMClassifier(
            num_leaves=31, learning_rate=0.05, n_estimators=500,
            feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=5,
            is_unbalance=True, random_state=SEED, verbose=-1,
        ),
        "XGBoost": xgb.XGBClassifier(
            max_depth=7, learning_rate=0.05, n_estimators=500,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="auc", random_state=SEED, n_jobs=-1,
            tree_method="hist",
        ),
        "CatBoost": CatBoostClassifier(
            depth=7, learning_rate=0.05, iterations=500,
            random_seed=SEED, verbose=0, auto_class_weights="Balanced",
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=16, n_jobs=-1,
            class_weight="balanced", random_state=SEED,
        ),
        "HistGB": HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.06, random_state=SEED,
        ),
        "LogisticReg": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"),
        ),
    }


def cross_validate_all(X, y):
    """모든 모델 5-fold OOF + soft-voting + stacking."""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))
    model_names = list(get_models().keys())

    oof = {name: np.zeros(len(X)) for name in model_names}
    times = {}
    results = {}

    for name in model_names:
        t0 = time.time()
        for fold, (tr, va) in enumerate(folds):
            model = get_models()[name]  # fold마다 새 인스턴스
            model.fit(X.iloc[tr], y.iloc[tr])
            oof[name][va] = model.predict_proba(X.iloc[va])[:, 1]
        times[name] = time.time() - t0
        auc = roc_auc_score(y, oof[name])
        f1 = f1_score(y, (oof[name] >= 0.5).astype(int))
        results[name] = {"auc": auc, "f1": f1, "train_time_s": round(times[name], 1)}
        print(f"  {name:<14} AUC={auc:.4f}  F1={f1:.4f}  ({times[name]:.0f}s)")

    # ── Soft-voting: 부스팅 계열 4개 평균 ──
    vote_members = ["LightGBM", "XGBoost", "CatBoost", "HistGB"]
    vote_oof = np.mean([oof[m] for m in vote_members], axis=0)
    results["Ensemble(Voting)"] = {
        "auc": roc_auc_score(y, vote_oof),
        "f1": f1_score(y, (vote_oof >= 0.5).astype(int)),
        "members": vote_members,
    }
    print(f"  {'Voting':<14} AUC={results['Ensemble(Voting)']['auc']:.4f}  "
          f"F1={results['Ensemble(Voting)']['f1']:.4f}")

    # ── Stacking: 전 모델 OOF를 meta LogReg 입력으로 (fold 재분할로 누수 방지) ──
    meta_X = np.column_stack([oof[m] for m in model_names])
    meta_oof = np.zeros(len(X))
    for tr, va in folds:
        meta = LogisticRegression(max_iter=1000)
        meta.fit(meta_X[tr], y.iloc[tr])
        meta_oof[va] = meta.predict_proba(meta_X[va])[:, 1]
    results["Ensemble(Stacking)"] = {
        "auc": roc_auc_score(y, meta_oof),
        "f1": f1_score(y, (meta_oof >= 0.5).astype(int)),
        "members": model_names,
    }
    print(f"  {'Stacking':<14} AUC={results['Ensemble(Stacking)']['auc']:.4f}  "
          f"F1={results['Ensemble(Stacking)']['f1']:.4f}")

    return results, oof, vote_oof, meta_oof


def train_final_models(X, y):
    """전체 데이터로 최종 voting 멤버 학습 → 추천시스템용 저장."""
    import joblib
    members = ["LightGBM", "XGBoost", "CatBoost", "HistGB"]
    fitted = {}
    for name in members:
        model = get_models()[name]
        model.fit(X, y)
        fitted[name] = model
    joblib.dump(
        {"members": fitted, "feature_cols": X.columns.tolist()},
        MODELS_DIR / "ensemble_voting.joblib",
    )
    print(f"  최종 앙상블 저장: {MODELS_DIR / 'ensemble_voting.joblib'}")
    return fitted


def main():
    print("=" * 60)
    print("exp_006: 깡통전세 다중모델 앙상블 (6모델 + voting + stacking)")
    print("=" * 60)

    df = load_and_merge()
    df = compute_dong_historical_risk(df)
    features = engineer_features(df)
    labels = create_labels(df)

    mask = labels.notna()
    X = features.loc[mask].fillna(-999)
    y = labels.loc[mask].astype(int)
    print(f"\n학습 데이터: {len(X):,}건 (위험 {y.sum():,} / 안전 {(1 - y).sum():,})\n")

    results, oof, vote_oof, meta_oof = cross_validate_all(X, y)
    train_final_models(X, y)

    # 앙상블 OOF 확률 저장 (추천시스템 + figure 용)
    oof_df = df.loc[mask, ["법정동명", "보증금_만원", "전용면적_㎡", "건축년도", "거래일", "전세가율"]].copy()
    oof_df["위험라벨"] = y.values
    oof_df["앙상블_위험확률"] = vote_oof
    for name, preds in oof.items():
        oof_df[f"oof_{name}"] = preds
    oof_df.to_parquet(EXP_DIR / "oof_predictions.parquet")

    best_single = max(
        (k for k in results if not k.startswith("Ensemble")),
        key=lambda k: results[k]["auc"],
    )
    best_overall = max(results, key=lambda k: results[k]["auc"])

    train_log = {
        "experiment_id": "exp_006_multimodel_ensemble",
        "model_type": "gangton_classifier_ensemble",
        "hypothesis": "이종 모델 앙상블이 단일 LightGBM 대비 강건성·성능을 높이는지 검증",
        "base_experiment": "exp_004_threshold_80",
        "n_samples": int(len(X)),
        "n_positive": int(y.sum()),
        "n_negative": int((1 - y).sum()),
        "n_folds": 5,
        "seed": SEED,
        "results": results,
        "best_single_model": best_single,
        "best_overall": best_overall,
        "metric": "AUC",
        "cv_score": results[best_overall]["auc"],
        "f1_score": results[best_overall]["f1"],
    }
    with open(EXP_DIR / "train_log.json", "w", encoding="utf-8") as f:
        json.dump(train_log, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n실험 완료 — 최고 단일: {best_single} / 최고 전체: {best_overall} "
          f"(AUC {results[best_overall]['auc']:.4f})")


if __name__ == "__main__":
    main()
