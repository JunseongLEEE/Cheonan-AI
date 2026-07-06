#!/usr/bin/env python3
"""
이상탐지 — Isolation Forest 기반 비정상 전세 거래 탐지

탐지 대상:
1. 동 내 전세가율 분포 대비 비정상적 고전세가율
2. 면적 대비 비정상적 보증금
3. 건물연령 대비 비정상적 보증금
4. 동별 이상 거래 집중도 → 행정 우선 점검 대상

출력: data/processed/anomaly_results.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_data():
    """전세가율 + 전세 거래 데이터 로드."""
    df_rate = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")
    df_rent = pd.read_parquet(PROCESSED_DIR / "realestate_rent.parquet")

    df_jeonse = df_rent[df_rent["전세여부"] == True].copy()
    df_jeonse["구코드"] = df_jeonse["_lawd_cd"].astype(str).str[:5]
    df_jeonse["연월"] = df_jeonse["거래일"].dt.to_period("M").astype(str)

    # 전세가율 매칭
    df_rate["연월"] = df_rate["연월"].astype(str)

    merged = df_jeonse.merge(
        df_rate[["법정동명", "단지명", "연월", "전세가율", "매매가_중앙값"]],
        left_on=["법정동명", "단지명", "연월"],
        right_on=["법정동명", "단지명", "연월"],
        how="inner",
    )

    print(f"전세가율 매칭 거래: {len(merged):,}건")
    return merged


def build_features(df):
    """이상탐지용 피처 구성."""
    features = pd.DataFrame(index=df.index)

    features["전세가율"] = df["전세가율"]
    features["보증금_만원"] = df["보증금_만원"]
    features["전용면적"] = df["전용면적_㎡"]
    features["건물연령"] = 2026 - df["건축년도"]

    # 단위 면적당 보증금
    features["m2당_보증금"] = df["보증금_만원"] / df["전용면적_㎡"].replace(0, np.nan)

    # 동별 통계 대비 비율
    dong_avg = df.groupby("법정동명")["전세가율"].transform("mean")
    dong_std = df.groupby("법정동명")["전세가율"].transform("std").replace(0, 1)
    features["전세가율_동z"] = (df["전세가율"] - dong_avg) / dong_std

    dong_avg_dep = df.groupby("법정동명")["보증금_만원"].transform("mean")
    dong_std_dep = df.groupby("법정동명")["보증금_만원"].transform("std").replace(0, 1)
    features["보증금_동z"] = (df["보증금_만원"] - dong_avg_dep) / dong_std_dep

    # 결측 처리
    features = features.fillna(0)
    features = features.replace([np.inf, -np.inf], 0)

    return features


def run_isolation_forest(features, contamination=0.05):
    """Isolation Forest 실행."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    labels = iso.fit_predict(X_scaled)  # -1=anomaly, 1=normal
    scores = iso.decision_function(X_scaled)  # 낮을수록 이상

    return labels, scores


def main():
    print("=" * 60)
    print("이상탐지 — Isolation Forest")
    print("=" * 60)

    df = load_data()
    features = build_features(df)

    print(f"\n피처: {features.columns.tolist()}")
    print(f"피처 통계:\n{features.describe().round(2)}")

    # Isolation Forest 실행
    labels, scores = run_isolation_forest(features, contamination=0.05)

    df["이상여부"] = labels
    df["이상점수"] = scores
    df["이상"] = df["이상여부"] == -1

    n_anomaly = df["이상"].sum()
    print(f"\n=== 이상탐지 결과 ===")
    print(f"전체: {len(df):,}건")
    print(f"이상: {n_anomaly:,}건 ({n_anomaly/len(df):.1%})")
    print(f"정상: {(~df['이상']).sum():,}건")

    # 이상 거래 분석
    anomalies = df[df["이상"]].copy()

    print(f"\n[이상 거래 vs 정상 거래 비교]")
    for col in ["전세가율", "보증금_만원", "전용면적_㎡"]:
        anom_mean = anomalies[col].mean()
        norm_mean = df[~df["이상"]][col].mean()
        print(f"  {col}: 이상 {anom_mean:.2f} vs 정상 {norm_mean:.2f}")

    # 동별 이상 거래 집중도
    print(f"\n[동별 이상 거래 비율 (상위 15)]")
    dong_anomaly = df.groupby("법정동명").agg(
        총거래=("이상", "count"),
        이상거래=("이상", "sum"),
    ).reset_index()
    dong_anomaly["이상비율"] = dong_anomaly["이상거래"] / dong_anomaly["총거래"]
    dong_anomaly = dong_anomaly[dong_anomaly["총거래"] >= 10]  # 최소 10건
    dong_anomaly = dong_anomaly.sort_values("이상비율", ascending=False)

    for _, row in dong_anomaly.head(15).iterrows():
        bar = "█" * int(row["이상비율"] * 30)
        print(f"  {row['법정동명']:>12}: {row['이상비율']:.0%} ({int(row['이상거래'])}/{int(row['총거래'])}) {bar}")

    # 이상 거래 상세 샘플
    print(f"\n[이상 거래 샘플 (이상점수 낮은 순 10건)]")
    worst = anomalies.nsmallest(10, "이상점수")
    for _, row in worst.iterrows():
        print(f"  {row['법정동명']} | {row.get('단지명','?')} | "
              f"전세가율 {row['전세가율']:.0%} | 보증금 {row['보증금_만원']:,.0f}만 | "
              f"{row['전용면적_㎡']:.0f}㎡ | 이상점수 {row['이상점수']:.3f}")

    # 전세가율 > 100% + 이상 = 깡통 후보
    gangton_candidates = anomalies[anomalies["전세가율"] >= 1.0]
    print(f"\n[깡통전세 후보 (이상 + 전세가율 100%+)]: {len(gangton_candidates):,}건")

    # 저장
    out_cols = ["법정동명", "단지명", "보증금_만원", "전용면적_㎡", "건축년도",
                "전세가율", "이상여부", "이상점수", "이상", "연월", "거래일"]
    save_cols = [c for c in out_cols if c in df.columns]
    df[save_cols].to_parquet(PROCESSED_DIR / "anomaly_results.parquet", index=False)

    dong_anomaly.to_parquet(PROCESSED_DIR / "dong_anomaly_rate.parquet", index=False)

    print(f"\n저장: anomaly_results.parquet, dong_anomaly_rate.parquet")
    print("✅ 이상탐지 완료")


if __name__ == "__main__":
    main()
