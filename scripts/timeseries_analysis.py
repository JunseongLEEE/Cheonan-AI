#!/usr/bin/env python3
"""
동별 전세가율 시계열 분석

분석:
1. 동별 월간 전세가율 추이
2. 최근 12개월 추세 (상승/하락/정체)
3. 위험 급등 동네 탐지
4. 전체 천안시 추세

출력: data/processed/dong_jeonse_timeseries.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def compute_monthly_jeonse_rate():
    """동별 월간 전세가율 집계."""
    df = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")

    # 월별 동별 집계
    monthly = df.groupby(["법정동명", "연월"]).agg(
        전세가율_평균=("전세가율", "mean"),
        전세가율_중앙값=("전세가율", "median"),
        거래수=("전세가율", "count"),
        위험거래수=("전세가율", lambda x: (x >= 0.80).sum()),
        깡통거래수=("전세가율", lambda x: (x >= 1.00).sum()),
    ).reset_index()

    monthly["연월"] = monthly["연월"].astype(str)
    monthly["위험비율"] = monthly["위험거래수"] / monthly["거래수"]

    return monthly


def compute_trend(series, window=6):
    """이동평균 기반 추세 계산. 양수=상승, 음수=하락."""
    if len(series) < window:
        return 0.0
    ma = series.rolling(window).mean()
    if ma.dropna().empty or len(ma.dropna()) < 2:
        return 0.0
    recent = ma.iloc[-1]
    past = ma.iloc[-window] if len(ma) >= window else ma.dropna().iloc[0]
    if pd.isna(recent) or pd.isna(past):
        return 0.0
    return float(recent - past)


def analyze_dong_trends(monthly):
    """동별 추세 분석."""
    results = []

    for dong in monthly["법정동명"].unique():
        dong_data = monthly[monthly["법정동명"] == dong].sort_values("연월")

        if len(dong_data) < 6:
            continue

        # 전체 기간 통계
        avg_rate = dong_data["전세가율_평균"].mean()
        latest_rate = dong_data["전세가율_평균"].iloc[-1]
        total_trades = dong_data["거래수"].sum()

        # 최근 12개월 추세
        recent_12 = dong_data.tail(12)
        trend_12m = compute_trend(recent_12["전세가율_평균"], window=6)

        # 최근 6개월 추세
        recent_6 = dong_data.tail(6)
        trend_6m = compute_trend(recent_6["전세가율_평균"], window=3)

        # 최근 위험비율 추세
        risk_trend = compute_trend(recent_12["위험비율"], window=6)

        # 추세 판정
        if trend_6m > 0.03:
            trend_label = "급상승"
        elif trend_6m > 0.01:
            trend_label = "상승"
        elif trend_6m < -0.03:
            trend_label = "급하락"
        elif trend_6m < -0.01:
            trend_label = "하락"
        else:
            trend_label = "정체"

        # 전세가율 변동성 (표준편차)
        volatility = dong_data["전세가율_평균"].std()

        results.append({
            "법정동명": dong,
            "전체평균_전세가율": avg_rate,
            "최근_전세가율": latest_rate,
            "12개월_추세": trend_12m,
            "6개월_추세": trend_6m,
            "위험추세": risk_trend,
            "추세_판정": trend_label,
            "변동성": volatility,
            "총거래수": total_trades,
            "데이터_개월수": len(dong_data),
        })

    return pd.DataFrame(results)


def main():
    print("=" * 60)
    print("동별 전세가율 시계열 분석")
    print("=" * 60)

    monthly = compute_monthly_jeonse_rate()
    print(f"월별 데이터: {len(monthly):,}건 ({monthly['법정동명'].nunique()}개 동)")

    # 전체 천안시 추세
    city_monthly = monthly.groupby("연월").agg(
        전세가율=("전세가율_평균", "mean"),
        거래수=("거래수", "sum"),
    ).reset_index().sort_values("연월")

    print(f"\n=== 천안시 전체 추세 ===")
    for _, row in city_monthly.tail(12).iterrows():
        bar = "█" * int(row["전세가율"] * 20)
        print(f"  {row['연월']} | {row['전세가율']:.0%} {bar} ({int(row['거래수'])}건)")

    # 동별 추세
    trends = analyze_dong_trends(monthly)
    trends = trends.sort_values("6개월_추세", ascending=False)

    print(f"\n=== 동별 추세 (6개월 기준) ===")
    print(f"\n[급상승/상승 동네]")
    rising = trends[trends["추세_판정"].isin(["급상승", "상승"])]
    for _, row in rising.iterrows():
        icon = "🔺" if row["추세_판정"] == "급상승" else "△"
        print(f"  {icon} {row['법정동명']}: {row['최근_전세가율']:.0%} (6M: {row['6개월_추세']:+.1%}, 12M: {row['12개월_추세']:+.1%})")

    print(f"\n[급하락/하락 동네]")
    falling = trends[trends["추세_판정"].isin(["급하락", "하락"])]
    for _, row in falling.iterrows():
        icon = "🔻" if row["추세_판정"] == "급하락" else "▽"
        print(f"  {icon} {row['법정동명']}: {row['최근_전세가율']:.0%} (6M: {row['6개월_추세']:+.1%}, 12M: {row['12개월_추세']:+.1%})")

    print(f"\n[정체 동네]")
    stable = trends[trends["추세_판정"] == "정체"]
    for _, row in stable.head(10).iterrows():
        print(f"  ─ {row['법정동명']}: {row['최근_전세가율']:.0%}")

    # 위험 경보
    print(f"\n=== 위험 경보 ===")
    alerts = trends[
        (trends["최근_전세가율"] >= 0.80) &
        (trends["6개월_추세"] > 0)
    ].sort_values("6개월_추세", ascending=False)

    if len(alerts) > 0:
        print(f"⚠️ 전세가율 80%+ 이면서 상승 추세인 동: {len(alerts)}개")
        for _, row in alerts.iterrows():
            print(f"  🚨 {row['법정동명']}: {row['최근_전세가율']:.0%} (↑{row['6개월_추세']:+.1%})")
    else:
        print("  현재 위험 상승 경보 없음")

    # 저장
    monthly.to_parquet(PROCESSED_DIR / "dong_jeonse_monthly.parquet", index=False)
    trends.to_parquet(PROCESSED_DIR / "dong_jeonse_trends.parquet", index=False)
    print(f"\n저장: dong_jeonse_monthly.parquet, dong_jeonse_trends.parquet")
    print("✅ 시계열 분석 완료")


if __name__ == "__main__":
    main()
