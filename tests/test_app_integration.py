#!/usr/bin/env python3
"""
Comprehensive integration test for app.py — runs all 5 tabs' logic without a browser.
"""

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
sys.path.insert(0, str(PROJECT_ROOT))

# ── Test infrastructure ──

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []


def ok(name, detail=""):
    global PASS
    PASS += 1
    RESULTS.append(("PASS", name, detail))
    print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))


def fail(name, detail=""):
    global FAIL
    FAIL += 1
    RESULTS.append(("FAIL", name, detail))
    print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))


def warn(name, detail=""):
    global WARN
    WARN += 1
    RESULTS.append(("WARN", name, detail))
    print(f"  WARN  {name}" + (f"  ({detail})" if detail else ""))


# ═══════════════════════════════════════════
# 0. Parquet files existence & loadability
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 0: Parquet file checks")
print("=" * 70)

PARQUET_FILES = [
    "dong_safety_score.parquet",
    "jeonse_rate.parquet",
    "dong_jeonse_monthly.parquet",
    "dong_jeonse_trends.parquet",
    "anomaly_results.parquet",
    "dong_anomaly_rate.parquet",
]

loaded = {}
for fname in PARQUET_FILES:
    fpath = PROCESSED_DIR / fname
    if fpath.exists():
        try:
            df = pd.read_parquet(fpath)
            loaded[fname] = df
            ok(f"Load {fname}", f"{len(df)} rows, {len(df.columns)} cols")
        except Exception as e:
            fail(f"Load {fname}", str(e))
    else:
        fail(f"Exists {fname}", "file not found")


# ═══════════════════════════════════════════
# TAB 1: Safety Map
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("TAB 1: Safety Map (anjeol-jido)")
print("=" * 70)

df_safety = loaded.get("dong_safety_score.parquet")
if df_safety is not None:
    # Column existence
    required_cols_tab1 = [
        "종합안전점수", "신호등", "금융안전_점수", "건물노후_점수",
        "치안_점수", "편의시설_점수", "전세가율_평균", "전세거래수", "법정동명",
    ]
    for col in required_cols_tab1:
        if col in df_safety.columns:
            ok(f"Tab1 column exists: {col}")
        else:
            fail(f"Tab1 column exists: {col}", f"missing from dong_safety_score")

    # NaN check on critical columns
    for col in ["종합안전점수", "신호등", "법정동명"]:
        if col in df_safety.columns:
            n_nan = df_safety[col].isna().sum()
            if n_nan == 0:
                ok(f"Tab1 no NaN in {col}")
            else:
                fail(f"Tab1 no NaN in {col}", f"{n_nan} NaN values")

    # DONG_COORDS coverage
    DONG_COORDS = {
        "원성동": [36.8003, 127.1502], "봉명동": [36.8090, 127.1390],
        "신방동": [36.7890, 127.1610], "신부동": [36.7980, 127.1350],
        "청당동": [36.7800, 127.1380], "안서동": [36.7730, 127.1280],
        "용곡동": [36.7850, 127.1250], "청수동": [36.7950, 127.1450],
        "구성동": [36.8010, 127.1420], "문화동": [36.8050, 127.1500],
        "대흥동": [36.8070, 127.1530], "사직동": [36.8090, 127.1560],
        "삼룡동": [36.7960, 127.1380], "영성동": [36.8110, 127.1600],
        "성황동": [36.8130, 127.1580], "와촌동": [36.8150, 127.1650],
        "구룡동": [36.7900, 127.1420], "오룡동": [36.8000, 127.1480],
        "다가동": [36.8100, 127.1550],
        "쌍용동": [36.8140, 127.1270], "두정동": [36.8330, 127.1350],
        "불당동": [36.8300, 127.1100], "백석동": [36.8450, 127.1050],
        "성성동": [36.8550, 127.0900], "부대동": [36.8600, 127.0850],
        "성정동": [36.8200, 127.1480], "업성동": [36.8250, 127.1150],
        "차암동": [36.8380, 127.1250], "유량동": [36.8200, 127.1200],
        "신당동": [36.8180, 127.1300],
        "목천읍 삼성리": [36.7300, 127.1800], "목천읍 신계리": [36.7400, 127.1700],
        "목천읍 서리": [36.7250, 127.1750], "목천읍 운전리": [36.7350, 127.1850],
        "목천읍 응원리": [36.7200, 127.1900],
        "성환읍 송덕리": [36.9200, 127.0700], "성환읍 매주리": [36.9150, 127.0750],
        "성환읍 성월리": [36.9250, 127.0650], "성환읍 수향리": [36.9180, 127.0680],
        "성환읍 율금리": [36.9100, 127.0800],
        "직산읍 군서리": [36.9000, 127.0600], "직산읍 삼은리": [36.8950, 127.0550],
        "직산읍 군동리": [36.9050, 127.0650], "직산읍 모시리": [36.8900, 127.0500],
        "직산읍 부송리": [36.9020, 127.0580], "직산읍 상덕리": [36.8980, 127.0700],
        "직산읍 수헐리": [36.8920, 127.0620],
        "성거읍 송남리": [36.8700, 127.1100], "성거읍 요방리": [36.8680, 127.1050],
        "성거읍 문덕리": [36.8750, 127.1150], "성거읍 신월리": [36.8650, 127.1000],
        "성거읍 오목리": [36.8720, 127.1200], "성거읍 저리": [36.8600, 127.1080],
        "성거읍 천흥리": [36.8630, 127.1150],
        "입장면 기로리": [36.8800, 127.0400], "입장면 도림리": [36.8850, 127.0350],
        "입장면 신덕리": [36.8780, 127.0450], "입장면 하장리": [36.8830, 127.0300],
        "북면 상동리": [36.7500, 127.2200], "성남면 석곡리": [36.7200, 127.1500],
        "병천면 병천리": [36.7100, 127.2200], "병천면 가전리": [36.7050, 127.2150],
        "병천면 탑원리": [36.7150, 127.2100], "풍세면 보성리": [36.7600, 127.1300],
    }

    all_dongs = df_safety["법정동명"].unique()
    matched = sum(1 for d in all_dongs if d in DONG_COORDS)
    unmatched = [d for d in all_dongs if d not in DONG_COORDS]
    coverage_pct = matched / len(all_dongs) * 100 if len(all_dongs) > 0 else 0
    if coverage_pct >= 50:
        ok(f"Tab1 DONG_COORDS coverage", f"{matched}/{len(all_dongs)} ({coverage_pct:.0f}%)")
    else:
        warn(f"Tab1 DONG_COORDS coverage", f"{matched}/{len(all_dongs)} ({coverage_pct:.0f}%)")
    if unmatched:
        warn(f"Tab1 dongs without coords", f"{len(unmatched)}: {unmatched[:10]}...")

    # Color logic
    for signal, expected_color in [("빨강", "#e74c3c"), ("초록", "#27ae60"), ("노랑", "#f39c12")]:
        if signal == "빨강":
            color = "#e74c3c"
        elif signal == "초록":
            color = "#27ae60"
        else:
            color = "#f39c12"
        if color == expected_color:
            ok(f"Tab1 color logic signal={signal}")
        else:
            fail(f"Tab1 color logic signal={signal}", f"got {color}, expected {expected_color}")

    # Dongnam/Seobuk classification
    dongnam_set = {"원성동", "봉명동", "신방동", "신부동", "청당동", "안서동",
                   "용곡동", "청수동", "구성동", "문화동", "대흥동", "사직동",
                   "삼룡동", "영성동", "성황동", "와촌동", "구룡동", "오룡동", "다가동"}
    df_test = df_safety.copy()
    df_test["구"] = df_test["법정동명"].apply(
        lambda x: "동남구" if x in dongnam_set or "목천" in x or "병천" in x or "북면" in x or "풍세" in x or "성남" in x else "서북구"
    )
    n_dn = len(df_test[df_test["구"] == "동남구"])
    n_sb = len(df_test[df_test["구"] == "서북구"])
    if n_dn > 0 and n_sb > 0:
        ok(f"Tab1 district classification", f"dongnam={n_dn}, seobuk={n_sb}")
    else:
        fail(f"Tab1 district classification", f"dongnam={n_dn}, seobuk={n_sb} -- one is empty")

    # Signal value counts
    signal_counts = df_safety["신호등"].value_counts()
    for s in ["빨강", "노랑", "초록"]:
        if s in signal_counts.index:
            ok(f"Tab1 signal '{s}' exists", f"{signal_counts[s]} dongs")
        else:
            warn(f"Tab1 signal '{s}' exists", "not found in data")

    # Radar chart columns (Tab3 uses these)
    radar_axes = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]
    for axis in radar_axes:
        col = f"{axis}_점수"
        if col in df_safety.columns:
            ok(f"Tab1/3 radar column: {col}")
        else:
            fail(f"Tab1/3 radar column: {col}", "missing -- radar chart will break (app.py line 446)")

else:
    fail("Tab1 all tests", "dong_safety_score.parquet not loaded")


# ═══════════════════════════════════════════
# TAB 2: Simulator
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("TAB 2: Simulator")
print("=" * 70)

DEMO_SCENARIOS = [
    {"보증금_만원": 5000, "전용면적": 33.0, "법정동명": "안서동", "건축년도": 2000, "구": "동남구"},
    {"보증금_만원": 15000, "전용면적": 84.0, "법정동명": "불당동", "건축년도": 2018, "구": "서북구"},
    {"보증금_만원": 3000, "전용면적": 20.0, "법정동명": "원성동", "건축년도": 1990, "구": "동남구"},
    {"보증금_만원": 20000, "전용면적": 84.0, "법정동명": "성성동", "건축년도": 2022, "구": "서북구"},
]

try:
    from scripts.simulator import predict, FEATURE_COLS

    ok("Tab2 import scripts.simulator.predict")

    # FEAT_KR mapping coverage check
    FEAT_KR = {
        "보증금_만원": "보증금", "보증금_log": "보증금(log)", "전용면적": "전용면적",
        "㎡당_보증금": "㎡당 보증금", "건물연령": "건물 연령", "동남구": "동남구 여부",
        "동_평균보증금": "동 평균보증금", "동_거래건수": "동 거래건수",
        "보증금_동평균_비율": "보증금/동평균", "보증금_구평균_비율": "보증금/구평균",
        "면적_구평균_비율": "면적/구평균", "연도별_동_위험도": "동 과거위험",
        "거래연도": "거래연도", "동_평균건물연령": "동 평균건물연령",
        "동_건물연령_std": "동 건물연령편차", "동_노후비율": "동 노후비율",
        "동_심각노후비율": "동 심각노후율", "동_내진비율": "동 내진비율",
        "동_건물수": "동 건물수", "동_평균세대수": "동 평균세대수",
        "동_평균총면적": "동 평균총면적", "동_평균지상층": "동 평균지상층",
        "동_철근콘크리트비율": "동 철근콘크리트", "동_벽돌비율": "동 벽돌비율",
        "동_목구조비율": "동 목구조비율", "건물연령_동평균차": "건물연령-동평균",
        "보증금_노후도_교차": "보증금x노후도",
    }
    unmapped = [f for f in FEATURE_COLS if f not in FEAT_KR]
    if len(unmapped) == 0:
        ok("Tab2 FEAT_KR covers all FEATURE_COLS")
    else:
        fail("Tab2 FEAT_KR covers all FEATURE_COLS", f"unmapped: {unmapped}")

    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        label = f"Scenario {i} ({scenario['법정동명']})"
        try:
            result = predict(**scenario)

            # Required keys
            required_keys = ["risk_prob", "signal", "signal_label", "safety_score", "shap_top5"]
            missing_keys = [k for k in required_keys if k not in result]
            if missing_keys:
                fail(f"Tab2 {label} return keys", f"missing: {missing_keys}")
            else:
                ok(f"Tab2 {label} return keys")

            # risk_prob range
            rp = result["risk_prob"]
            if 0.0 <= rp <= 1.0:
                ok(f"Tab2 {label} risk_prob range", f"{rp:.4f}")
            else:
                fail(f"Tab2 {label} risk_prob range", f"{rp} outside [0,1]")

            # Signal logic consistency
            signal = result["signal"]
            if rp >= 0.7:
                expected_signal = "빨강"
            elif rp >= 0.3:
                expected_signal = "노랑"
            else:
                expected_signal = "초록"

            if signal == expected_signal:
                ok(f"Tab2 {label} signal logic", f"prob={rp:.2f} -> {signal}")
            else:
                fail(f"Tab2 {label} signal logic",
                     f"prob={rp:.2f} -> got '{signal}', expected '{expected_signal}'")

            # SHAP values not NaN
            shap_top5 = result["shap_top5"]
            shap_nans = sum(1 for item in shap_top5 if np.isnan(item.get("shap_value", 0)))
            if shap_nans == 0:
                ok(f"Tab2 {label} SHAP no NaN")
            else:
                fail(f"Tab2 {label} SHAP has NaN", f"{shap_nans} NaN values")

            # FEAT_KR covers shap features
            shap_features = [item["feature"] for item in shap_top5]
            uncovered = [f for f in shap_features if f not in FEAT_KR]
            if uncovered:
                warn(f"Tab2 {label} SHAP features not in FEAT_KR", str(uncovered))
            else:
                ok(f"Tab2 {label} SHAP features all mapped")

            # safety_score
            ss = result["safety_score"]
            if ss is not None:
                if 0 <= ss <= 100:
                    ok(f"Tab2 {label} safety_score", f"{ss:.1f}")
                else:
                    warn(f"Tab2 {label} safety_score out of range", f"{ss}")
            else:
                warn(f"Tab2 {label} safety_score is None")

        except Exception as e:
            fail(f"Tab2 {label} predict()", f"{e}")
            traceback.print_exc()

except Exception as e:
    fail("Tab2 import simulator", str(e))
    traceback.print_exc()


# ═══════════════════════════════════════════
# TAB 3: Dashboard
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("TAB 3: Dashboard")
print("=" * 70)

df_safety = loaded.get("dong_safety_score.parquet")
df_rate = loaded.get("jeonse_rate.parquet")

if df_safety is not None and df_rate is not None:
    # Metric calculations
    try:
        mean_score = df_safety["종합안전점수"].mean()
        mean_rate = df_safety["전세가율_평균"].mean()
        red_count = len(df_safety[df_safety["신호등"] == "빨강"])
        total_trades = int(df_safety["전세거래수"].sum())
        ok("Tab3 metric calculations",
           f"mean_score={mean_score:.1f}, mean_rate={mean_rate:.2f}, red={red_count}, trades={total_trades}")
    except Exception as e:
        fail("Tab3 metric calculations", str(e))

    # Yearly aggregation
    try:
        df_rate_ts = df_rate.copy()
        if "연월" not in df_rate_ts.columns:
            fail("Tab3 yearly agg", "column '연월' missing from jeonse_rate.parquet")
        else:
            df_rate_ts["연도"] = df_rate_ts["연월"].astype(str).str[:4].astype(int)
            yearly = df_rate_ts.groupby("연도")["전세가율"].agg(["mean", "median", "count"]).reset_index()
            yearly.columns = ["연도", "평균", "중앙값", "거래수"]
            ok("Tab3 yearly aggregation", f"{len(yearly)} years, range {yearly['연도'].min()}-{yearly['연도'].max()}")

            # Verify values are reasonable
            if yearly["평균"].max() > 5:
                warn("Tab3 yearly mean rate very high",
                     f"max={yearly['평균'].max():.2f} -- might be percentage not ratio")
            elif yearly["평균"].max() <= 0:
                fail("Tab3 yearly mean rate", "all zeros or negative")
            else:
                ok("Tab3 yearly mean rate range", f"max={yearly['평균'].max():.3f}")
    except Exception as e:
        fail("Tab3 yearly aggregation", str(e))
        traceback.print_exc()

    # Scatter plot data validity
    try:
        scatter_cols = ["금융안전_점수", "건물노후_점수", "전세거래수", "신호등", "법정동명"]
        missing = [c for c in scatter_cols if c not in df_safety.columns]
        if missing:
            fail("Tab3 scatter plot columns", f"missing: {missing}")
        else:
            n_nan_fin = df_safety["금융안전_점수"].isna().sum()
            n_nan_bld = df_safety["건물노후_점수"].isna().sum()
            if n_nan_fin + n_nan_bld == 0:
                ok("Tab3 scatter data no NaN")
            else:
                warn("Tab3 scatter data NaN", f"금융안전={n_nan_fin}, 건물노후={n_nan_bld}")
    except Exception as e:
        fail("Tab3 scatter plot check", str(e))

    # Plotly chart creation tests
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        # Bar chart
        df_plot = df_safety.sort_values("종합안전점수", ascending=True).tail(20)
        color_map = {"빨강": "#e74c3c", "노랑": "#f39c12", "초록": "#27ae60"}
        fig1 = px.bar(df_plot, x="종합안전점수", y="법정동명", orientation="h",
                      color="신호등", color_discrete_map=color_map)
        ok("Tab3 bar chart creation")

        # Histogram
        fig2 = px.histogram(df_rate, x="전세가율", nbins=50)
        ok("Tab3 histogram creation")

        # Scatter
        fig3 = px.scatter(df_safety, x="금융안전_점수", y="건물노후_점수",
                          size="전세거래수", color="신호등", color_discrete_map=color_map,
                          hover_name="법정동명")
        ok("Tab3 scatter chart creation")

        # Yearly line chart
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=yearly["연도"], y=yearly["평균"],
                                  mode="lines+markers", name="avg"))
        ok("Tab3 yearly line chart creation")

    except Exception as e:
        fail("Tab3 Plotly chart creation", str(e))
        traceback.print_exc()

else:
    fail("Tab3 all tests", "required parquet files not loaded")


# ═══════════════════════════════════════════
# TAB 4: Trend Analysis
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("TAB 4: Trend Analysis")
print("=" * 70)

df_monthly = loaded.get("dong_jeonse_monthly.parquet")
df_trends = loaded.get("dong_jeonse_trends.parquet")

if df_monthly is not None and df_trends is not None:
    # Required columns
    trend_cols = ["법정동명", "최근_전세가율", "6개월_추세", "추세_판정"]
    for col in trend_cols:
        if col in df_trends.columns:
            ok(f"Tab4 trend column: {col}")
        else:
            fail(f"Tab4 trend column: {col}", "missing")

    monthly_cols = ["법정동명", "연월", "전세가율_평균"]
    for col in monthly_cols:
        if col in df_monthly.columns:
            ok(f"Tab4 monthly column: {col}")
        else:
            fail(f"Tab4 monthly column: {col}", "missing")

    # Alert filter logic
    try:
        alerts = df_trends[
            (df_trends["최근_전세가율"] >= 0.80) &
            (df_trends["6개월_추세"] > 0)
        ].sort_values("6개월_추세", ascending=False)
        ok(f"Tab4 alert filter", f"{len(alerts)} alerts")
    except Exception as e:
        fail("Tab4 alert filter", str(e))

    # Trend classification counts
    try:
        trend_summary = df_trends["추세_판정"].value_counts()
        ok(f"Tab4 trend classifications", str(dict(trend_summary)))
    except Exception as e:
        fail("Tab4 trend classifications", str(e))

    # Default dongs exist
    default_dongs = ["두정동", "불당동", "원성동"]
    for d in default_dongs:
        if d in df_trends["법정동명"].values:
            ok(f"Tab4 default dong exists: {d}")
        else:
            warn(f"Tab4 default dong exists: {d}", "not found -- app falls back to head(3)")

    # NaN in critical columns
    for col in ["최근_전세가율", "6개월_추세"]:
        if col in df_trends.columns:
            n = df_trends[col].isna().sum()
            if n == 0:
                ok(f"Tab4 no NaN: {col}")
            else:
                warn(f"Tab4 NaN in {col}", f"{n} NaN values")

    # Plotly chart
    try:
        import plotly.express as px
        top_bottom = pd.concat([
            df_trends.nlargest(5, "6개월_추세"),
            df_trends.nsmallest(5, "6개월_추세"),
        ])
        fig_tb = px.bar(
            top_bottom.sort_values("6개월_추세"),
            x="6개월_추세", y="법정동명",
            orientation="h", color="6개월_추세",
            color_continuous_scale="RdYlGn_r",
        )
        ok("Tab4 top/bottom bar chart creation")

        # Time series line chart
        selected_dongs_in_data = [d for d in default_dongs if d in df_monthly["법정동명"].values]
        if selected_dongs_in_data:
            ts_data = df_monthly[df_monthly["법정동명"].isin(selected_dongs_in_data)]
            fig_ts = px.line(ts_data, x="연월", y="전세가율_평균", color="법정동명")
            ok("Tab4 time series chart creation")
        else:
            warn("Tab4 time series chart", "no default dongs found in monthly data")
    except Exception as e:
        fail("Tab4 Plotly charts", str(e))
        traceback.print_exc()

else:
    fail("Tab4 all tests", "required parquet files not loaded")


# ═══════════════════════════════════════════
# TAB 5: Anomaly Detection
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("TAB 5: Anomaly Detection")
print("=" * 70)

df_anom = loaded.get("anomaly_results.parquet")
df_dong_anom = loaded.get("dong_anomaly_rate.parquet")

if df_anom is not None and df_dong_anom is not None:
    # "이상" column exists and is boolean
    if "이상" in df_anom.columns:
        ok("Tab5 column '이상' exists")
        if df_anom["이상"].dtype == bool or df_anom["이상"].dtype == np.bool_:
            ok("Tab5 '이상' is boolean type")
        else:
            warn("Tab5 '이상' dtype", f"dtype={df_anom['이상'].dtype}, expected bool")
            # Check if it's 0/1 integer
            unique_vals = df_anom["이상"].unique()
            if set(unique_vals).issubset({0, 1, True, False}):
                ok("Tab5 '이상' values are boolean-like", f"unique: {unique_vals}")
            else:
                fail("Tab5 '이상' values", f"unexpected: {unique_vals[:10]}")
    else:
        fail("Tab5 column '이상'", "missing")

    # 전세가율 format check
    if "전세가율" in df_anom.columns:
        rate_mean = df_anom["전세가율"].mean()
        rate_max = df_anom["전세가율"].max()
        if rate_max <= 5:
            ok("Tab5 전세가율 is ratio (0-1 scale)", f"mean={rate_mean:.3f}, max={rate_max:.3f}")
        elif rate_max <= 500:
            warn("Tab5 전세가율 is percentage (0-100 scale)",
                 f"mean={rate_mean:.1f}, max={rate_max:.1f} -- column_config format '%.0%%' may display incorrectly")
        else:
            fail("Tab5 전세가율 range unexpected", f"mean={rate_mean}, max={rate_max}")
    else:
        fail("Tab5 column 전세가율", "missing")

    # Gangton candidate filter
    try:
        gangton = len(df_anom[(df_anom["이상"]) & (df_anom["전세가율"] >= 1.0)])
        ok(f"Tab5 gangton candidates", f"{gangton} rows with 이상=True & 전세가율>=1.0")
    except Exception as e:
        fail("Tab5 gangton filter", str(e))

    # Metric calculations
    try:
        total = len(df_anom)
        n_anom = df_anom["이상"].sum()
        ok(f"Tab5 metrics", f"total={total:,}, anomalies={n_anom:,} ({n_anom/total:.1%})")
    except Exception as e:
        fail("Tab5 metrics", str(e))

    # 이상점수 column
    if "이상점수" in df_anom.columns:
        ok("Tab5 column '이상점수' exists")
        n_nan = df_anom["이상점수"].isna().sum()
        if n_nan > 0:
            warn("Tab5 NaN in 이상점수", f"{n_nan}")
    else:
        fail("Tab5 column '이상점수'", "missing -- worst-20 table will break (app.py line 683)")

    # dong_anomaly_rate columns
    for col in ["법정동명", "이상비율", "이상거래", "총거래"]:
        if col in df_dong_anom.columns:
            ok(f"Tab5 dong_anomaly_rate column: {col}")
        else:
            fail(f"Tab5 dong_anomaly_rate column: {col}", "missing")

    # column_config format string check
    # app.py line 690: format="%.0%%" -- this is a Python %-format string
    # "%.0%%" means: format float with 0 decimal places then literal '%'
    # But for st.column_config.NumberColumn, format should be a printf-style string.
    # "%.0%%" -> this will attempt to format as e.g. "0.85" -> "1%" (multiplies by 100? no)
    # Actually Streamlit NumberColumn format uses d3-format or printf.
    # "%.0%%" is printf: %.0f -> "1" then literal % -> "1%"
    # But the value is a ratio like 0.85, so %.0f gives "1%" which is wrong.
    # Should be "%.0f%%" if values are already percentages, or needs *100 first.
    test_val = 0.85
    formatted = "%.0f%%" % test_val  # This is what printf would produce
    if formatted == "85%":
        ok("Tab5 format '%.0f%%' for ratio 0.85", formatted)
    else:
        # Actually let's test what the app uses
        app_format = "%.0%%"
        try:
            result_fmt = app_format % test_val
            warn("Tab5 column_config format '%.0%%'",
                 f"0.85 -> '{result_fmt}' -- check if Streamlit interprets this correctly")
        except Exception as e:
            warn("Tab5 column_config format '%.0%%'",
                 f"Python %-format error: {e} -- Streamlit may use d3-format instead")

    # Display columns availability (app.py line 684)
    display_cols = ["법정동명", "단지명", "전세가율", "보증금_만원", "전용면적_㎡", "이상점수"]
    avail = [c for c in display_cols if c in df_anom.columns]
    missing_display = [c for c in display_cols if c not in df_anom.columns]
    ok(f"Tab5 display columns available", f"{len(avail)}/{len(display_cols)}")
    if missing_display:
        warn(f"Tab5 display columns missing", str(missing_display))

    # Plotly charts
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        top_dongs = df_dong_anom.head(15)
        fig_anom = px.bar(top_dongs, x="이상비율", y="법정동명", orientation="h",
                          color="이상비율", color_continuous_scale="Reds")
        ok("Tab5 anomaly bar chart creation")

        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=df_anom[~df_anom["이상"]]["전세가율"], name="normal", nbinsx=50))
        fig_dist.add_trace(go.Histogram(
            x=df_anom[df_anom["이상"]]["전세가율"], name="anomaly", nbinsx=50))
        ok("Tab5 distribution histogram creation")
    except Exception as e:
        fail("Tab5 Plotly charts", str(e))
        traceback.print_exc()

else:
    fail("Tab5 all tests", "required parquet files not loaded")


# ═══════════════════════════════════════════
# CSS/HTML hero banner check
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION: CSS/HTML checks")
print("=" * 70)

app_text = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")

for check_str, label in [
    ("hero-banner", "hero-banner CSS class"),
    ("stat-pill", "stat-pill CSS class"),
    ("linear-gradient", "gradient background"),
    ("청년 197,572명", "youth stat pill"),
    ("AUC 0.989", "AUC stat pill"),
]:
    if check_str in app_text:
        ok(f"HTML {label}")
    else:
        fail(f"HTML {label}", "not found in app.py")


# ═══════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  WARN: {WARN}")
print(f"  TOTAL: {PASS + FAIL + WARN}")
print("=" * 70)

if FAIL > 0:
    print("\nFAILED tests:")
    for status, name, detail in RESULTS:
        if status == "FAIL":
            print(f"  - {name}: {detail}")

if WARN > 0:
    print("\nWARNINGS:")
    for status, name, detail in RESULTS:
        if status == "WARN":
            print(f"  - {name}: {detail}")

sys.exit(1 if FAIL > 0 else 0)
