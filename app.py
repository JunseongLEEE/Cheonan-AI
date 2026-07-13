#!/usr/bin/env python3
"""
천안 청년 자취방 안전지도 — Streamlit 앱
시민 중심 UX: 매물 체크 → 안전지도 → 예산 추천 → 계약 가이드 → AI 상담 → 데이터 더보기
"""

import json
import os
from pathlib import Path

import folium
from folium.plugins import HeatMap
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from styles.cinematic import inject_theme, hero, chapter_divider, grade_pill, COLOR

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(
    page_title="천안 청년 자취방 안전지도",
    page_icon="🌙",
    layout="wide",
)

# ─── 다크 시네마틱 테마 주입 ───
inject_theme()

# ─── 공식 포털형 상단 헤더 (좌: 천안시 심벌 + 워드마크) ───
from scripts.brand_assets import mascot_uri as _mascot_uri, symbol_uri as _symbol_uri

_sym = _symbol_uri()
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:10px 4px 12px 4px;border-bottom:2px solid #2E86E6;margin-bottom:6px;">
  <div style="display:flex;align-items:center;gap:12px;">
    {f'<img src="{_sym}" alt="천안시" style="height:34px;"/>' if _sym else ''}
    <div>
      <span style="font-size:1.28rem;font-weight:800;color:#16233A;letter-spacing:-0.02em;">천안세이프</span>
      <span style="font-size:0.85rem;color:#55677F;margin-left:10px;">천안 청년 자취방 안전지도</span>
    </div>
  </div>
  <div style="font-size:0.8rem;color:#2E86E6;font-weight:600;">하늘 아래 가장 편안한 자취방</div>
</div>
""", unsafe_allow_html=True)


# ─── Plotly 시네마틱 다크 우주 템플릿 ───
import plotly.io as pio
_C = COLOR  # noqa: shorthand
pio.templates["cosmos"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Pretendard Variable, Pretendard, sans-serif",
                  color=_C["fg"], size=13),
        title=dict(font=dict(color=_C["fg"], size=18, family="Pretendard Variable"), x=0.02),
        colorway=[_C["primary_soft"], _C["caution_soft"], _C["safe_soft"],
                  _C["risk_strong"], _C["cyan"], _C["highlight"], "#F472B6", "#93C5FD"],
        xaxis=dict(gridcolor="rgba(46,134,230,0.10)", zerolinecolor="rgba(46,134,230,0.18)",
                   linecolor=_C["line"], tickcolor=_C["line"],
                   tickfont=dict(color=_C["fg_muted"]), title=dict(font=dict(color=_C["fg_muted"]))),
        yaxis=dict(gridcolor="rgba(46,134,230,0.10)", zerolinecolor="rgba(46,134,230,0.18)",
                   linecolor=_C["line"], tickcolor=_C["line"],
                   tickfont=dict(color=_C["fg_muted"]), title=dict(font=dict(color=_C["fg_muted"]))),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor=_C["line"], borderwidth=1,
                    font=dict(color=_C["fg"])),
        hoverlabel=dict(bgcolor=_C["surface_hi"], bordercolor=_C["primary"],
                        font=dict(color=_C["fg"], family="Pretendard Variable")),
        margin=dict(l=48, r=32, t=56, b=48),
    )
)
pio.templates.default = "plotly_dark+cosmos"

# ─── 데이터 로드 (캐시) ───

@st.cache_data
def load_safety_scores():
    return pd.read_parquet(PROCESSED_DIR / "dong_safety_score.parquet")

@st.cache_data
def load_jeonse_rate():
    return pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")

@st.cache_data
def load_dong_list():
    df = load_safety_scores()
    return sorted(df["법정동명"].dropna().unique().tolist())

# 모델 캐싱 (전역 — 매물 체크 + 챗봇 공용)
@st.cache_resource
def load_predict_fn():
    from scripts.simulator import predict
    return predict

# 천안시 동별 좌표 (folium 마커용) — 65개 법정동 전체
from scripts.dong_coords import DONG_COORDS

# ── 공통 유틸 ──
DONGNAM_DONGS = {"원성동", "봉명동", "신방동", "신부동", "청당동", "안서동",
                 "용곡동", "청수동", "구성동", "문화동", "대흥동", "사직동",
                 "삼룡동", "영성동", "성황동", "와촌동", "구룡동", "오룡동", "다가동"}

def _auto_gu(dong_name):
    return "동남구" if dong_name in DONGNAM_DONGS or any(k in dong_name for k in ["목천","북면","병천","풍세","광덕","성남","수신","동면"]) else "서북구"

FEAT_KR = {
    "보증금_만원": "보증금이 큰 편", "보증금_log": "보증금 수준",
    "전용면적": "전용면적", "㎡당_보증금": "㎡당 보증금 수준",
    "건물연령": "건물이 오래됨", "동남구": "구도심(동남구) 입지",
    "동_평균보증금": "동네 평균 보증금 수준", "동_거래건수": "동네 거래 활발도",
    "보증금_동평균_비율": "동네 평균 대비 보증금", "보증금_구평균_비율": "구 평균 대비 보증금",
    "면적_구평균_비율": "구 평균 대비 면적", "연도별_동_위험도": "동네의 과거 위험 이력",
    "거래연도": "최근 시장 시점 효과", "동_평균건물연령": "동네 평균 건물연령",
    "동_건물연령_std": "동네 건물연령 편차", "동_노후비율": "동네 노후건물 비율",
    "동_심각노후비율": "동네 심각노후 비율", "동_내진비율": "동네 내진설계 비율",
    "동_건물수": "동네 건물 수", "동_평균세대수": "동네 평균 세대수",
    "동_평균총면적": "동네 평균 연면적", "동_평균지상층": "동네 평균 층수",
    "동_철근콘크리트비율": "철근콘크리트 비율", "동_벽돌비율": "벽돌구조 비율",
    "동_목구조비율": "목구조 비율", "건물연령_동평균차": "동네 대비 건물 연식",
    "보증금_노후도_교차": "높은 보증금×노후 결합",
}


# ─── 탭 (시민 중심 순서) ───
tab1, tab2, tab_listing, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 내 매물 체크",
    "🗺️ 안전지도",
    "🏠 매물 탐색",
    "💰 예산별 추천",
    "✅ 계약 가이드",
    "💬 AI 상담",
    "📊 데이터 더보기",
])


# ═══════════════════════════════════════════
# 탭 1: 내 매물 체크 (핵심 — 시민이 가장 먼저 쓰는 기능)
# ═══════════════════════════════════════════
with tab1:
    # ─── 히어로 (Ch. 00) ───

    hero(
        title_html='<em>하늘 아래에서,</em><br/>계약 전 밤을 밝힙니다',
        subtitle="'하늘 아래 가장 편안한 도시' 천안의 청년 19.7만 명 — 86%가 세입자입니다. 동네와 매물은 따로 진단해야 합니다: 실거래 10만+ 건과 65개 동 8축 안전점수로, 계약 전 그 답을 드립니다.",
        eyebrow="천안시 공공데이터 기반 · CHEONAN YOUTH HOUSING SAFETY",
        pills=[
            ("", "청년 19.7만 명"),
            ("risk", "전세사기 288세대"),
            ("caution", "위험 경보 19개 동 · 80%+ 상승추세"),
            ("safe", "AUC 0.9893 / F1 0.9690"),
            ("", "실거래 102,671건 · 65개 동"),
        ],
        hint="매물 체크 → 안전지도 → 매물 탐색 → 예산별 추천 → 계약 가이드 → AI 상담",
        mascot_uri=_mascot_uri("기본"),
        symbol_uri=_symbol_uri(),
        cert_line="천안시 공공데이터 · 국토부 실거래가 기반  |  본 서비스는 천안시청과 무관한 학술·시연 프로젝트입니다",
    )

    # ─── 왜 필요한가 — 천안시 전세사기 현황 ───
    with st.expander("Ch. 00 · 왜 지금 이 서비스가 필요한가 — 천안시 청년 주거 위기 현황", expanded=False):
        why_cols = st.columns(4)
        why_cols[0].metric("청년 무주택 비율", "86.1%", help="천안시 18~39세 중 주택 미소유 비율")
        why_cols[1].metric("전세사기 피해", "288세대", "145억원 피해", delta_color="inverse")
        why_cols[2].metric("위험 경보 동", "19개", help="전세가율 80% 이상 + 6개월 상승 추세인 법정동 (시계열 경보 기준)")
        why_cols[3].metric("이상 거래 탐지", "5,134건", "전체의 5.0%", delta_color="inverse")
        st.markdown("""
    **천안시 청년 19.7만명 중 86%가 무주택** — 대부분 전세·월세로 거주합니다.
    그러나 전세사기 피해는 계속 증가하고 있으며, 특히 **구도심(동남구)**의 노후 건물에 집중됩니다.

    이 서비스는 **계약 전에 AI가 위험을 미리 진단**하여 피해를 예방합니다:
    - 🔍 **내 매물 체크**: 보증금·면적·동네를 넣으면 깡통전세 확률 진단
    - 🗺️ **안전지도**: 동네별 종합 안전점수 한눈에 비교
    - 💰 **예산별 추천**: 내 예산에서 가장 안전한 동네 추천
    - ✅ **계약 가이드**: 등기부등본·HUG보험 등 필수 체크리스트
    """)

    chapter_divider("01", "이 매물, 계약해도 될까")
    st.caption("보증금·면적·동네·건축년도를 입력하면 AI가 깡통전세 위험도를 진단합니다")

    # 데모 시나리오 프리셋
    DEMO_SCENARIOS = {
        "직접 입력": None,
        "🎓 대학가 원룸 (안서동, 위험)": {"dong": "안서동", "deposit": 5000, "area": 33.0, "year": 2000, "gu": "동남구"},
        "💼 사회초년생 (불당동, 주의)": {"dong": "불당동", "deposit": 15000, "area": 84.0, "year": 2018, "gu": "서북구"},
        "⚠️ 구도심 원룸 (원성동, 위험)": {"dong": "원성동", "deposit": 3000, "area": 20.0, "year": 1990, "gu": "동남구"},
        "🟢 신도시 신축 (성성동, 안전)": {"dong": "성성동", "deposit": 20000, "area": 84.0, "year": 2022, "gu": "서북구"},
    }

    # 결과 렌더 함수
    def _render_result(result, dong_name, compact=False):
        risk = result["risk_prob"]
        signal = result["signal"]
        signal_label = result["signal_label"]

        if signal == "빨강":
            st.error(f"🔴 **{signal_label}** — 위험확률 {risk:.1%}")
        elif signal == "노랑":
            st.warning(f"🟡 **{signal_label}** — 위험확률 {risk:.1%}")
        else:
            st.success(f"🟢 **{signal_label}** — 위험확률 {risk:.1%}")

        # 게이지 차트
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk * 100,
            title={"text": f"{dong_name} 위험도" if compact else "깡통전세 위험도"},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#e74c3c" if risk >= 0.7 else "#f39c12" if risk >= 0.3 else "#27ae60"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(39,174,96,0.15)"},
                    {"range": [30, 70], "color": "rgba(243,156,18,0.15)"},
                    {"range": [70, 100], "color": "rgba(231,76,60,0.15)"},
                ],
            },
        ))
        fig_gauge.update_layout(height=220 if compact else 250, margin=dict(t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 한줄 해석
        if risk >= 0.8:
            st.caption("🚨 매우 위험 — 이 조건의 전세는 깡통전세 가능성이 매우 높습니다. 계약을 재고하세요.")
        elif risk >= 0.5:
            st.caption("⚠️ 위험 — 보증금 반환이 어려울 수 있습니다. HUG 보증보험 가입을 강력 권장합니다.")
        elif risk >= 0.3:
            st.caption("🟡 주의 — 일부 위험 요소가 있습니다. 등기부등본과 전세가율을 꼼꼼히 확인하세요.")
        else:
            st.caption("🟢 양호 — 현재 조건에서 큰 위험 요소가 감지되지 않았습니다.")

        if result["safety_score"]:
            st.metric("동네 안전점수", f"{result['safety_score']:.1f}/100")

        # SHAP — "왜 이 결과가 나왔나?"
        st.markdown("**위험/안전 판단 근거:**")
        shap_df = pd.DataFrame(result["shap_top5"])
        shap_df["feature_kr"] = shap_df["feature"].map(FEAT_KR).fillna(shap_df["feature"])
        colors = ["#e74c3c" if v > 0 else "#27ae60" for v in shap_df["shap_value"]]
        fig_shap = go.Figure()
        fig_shap.add_trace(go.Bar(
            x=shap_df["shap_value"], y=shap_df["feature_kr"],
            orientation="h", marker_color=colors,
            text=[f"{v:+.3f}" for v in shap_df["shap_value"]], textposition="outside",
            textfont=dict(size=13), cliponaxis=False,
        ))
        _absmax = float(shap_df["shap_value"].abs().max()) * 1.35 or 1.0
        fig_shap.update_layout(
            height=220 if compact else 280,
            margin=dict(l=20, r=70, t=10, b=30),
            xaxis_title="위험 기여도 (빨강=위험↑, 초록=안전↑)",
            xaxis=dict(title_font=dict(size=11), range=[-_absmax, _absmax]),
            yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
        )
        st.plotly_chart(fig_shap, use_container_width=True)
        st.caption("→ 빨간 막대(+)는 위험을 높인 요인, 초록 막대(−)는 낮춘 요인입니다")

    # ── 모드 선택 ──
    sim_mode = st.radio("분석 모드", ["단일 분석", "비교 분석"], horizontal=True, key="sim_mode",
                        help="비교 분석: 두 매물의 위험도를 나란히 비교합니다")

    preset = st.selectbox("예시 시나리오 (빠른 체험)", list(DEMO_SCENARIOS.keys()), index=3, key="sim_preset",
                          help="첫 화면은 구도심 원성동 위험 사례가 자동 진단됩니다 — 직접 입력으로 바꿔 내 매물을 진단하세요")
    preset_data = DEMO_SCENARIOS[preset]

    if sim_mode == "단일 분석":
        col_input, col_result = st.columns([1, 1.5])

        # 프리셋 선택 시 입력값 자동 세팅
        if preset_data is not None:
            p_dong = preset_data["dong"]
            p_dep = preset_data["deposit"]
            p_area = preset_data["area"]
            p_year = preset_data["year"]
        else:
            p_dong = "두정동"
            p_dep = 7000
            p_area = 59.0
            p_year = 2005

        with col_input:
            st.subheader("매물 정보 입력")
            dong_list = load_dong_list()
            dong_idx = dong_list.index(p_dong) if p_dong in dong_list else 0
            dong = st.selectbox("동네", dong_list, index=dong_idx, key=f"sim_dong_{preset}")
            deposit = st.number_input("보증금 (만원)", min_value=100, max_value=100000,
                                      value=p_dep, step=500,
                                      help="전세 보증금을 만원 단위로 입력하세요",
                                      key=f"sim_dep_{preset}")
            area = st.number_input("전용면적 (㎡)", min_value=5.0, max_value=200.0,
                                   value=p_area, step=1.0,
                                   help="계약서에 적힌 전용면적",
                                   key=f"sim_area_{preset}")
            build_year = st.number_input("건축년도", min_value=1970, max_value=2026,
                                         value=p_year, step=1,
                                         help="건축물대장 또는 등기부등본에서 확인",
                                         key=f"sim_year_{preset}")
            gu = _auto_gu(dong)
            st.info(f"📍 {dong} → {gu}")
            run_sim = st.button("🔍 위험도 체크", type="primary", use_container_width=True)

        should_run = run_sim or (preset_data is not None)

        with col_result:
            if should_run:
                with st.spinner("AI 분석 중..."):
                    try:
                        predict_fn = load_predict_fn()
                        result = predict_fn(보증금_만원=float(deposit), 전용면적=float(area),
                                            법정동명=dong, 건축년도=int(build_year), 구=gu)
                        _render_result(result, dong)

                        # 위험하면 대체 동네 추천
                        if result["risk_prob"] >= 0.3:
                            st.subheader("비슷한 조건에서 더 안전한 동네")
                            df_safe = load_safety_scores()
                            current_score = result["safety_score"] or 50
                            alternatives = df_safe[
                                (df_safe["종합안전점수"] > current_score) & (df_safe["법정동명"] != dong)
                            ].sort_values("종합안전점수", ascending=False).head(5)
                            if len(alternatives) > 0:
                                alt_cols = st.columns(min(len(alternatives), 5))
                                for i, (_, alt_row) in enumerate(alternatives.iterrows()):
                                    with alt_cols[i]:
                                        alt_signal = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}.get(alt_row["신호등"], "⚪")
                                        diff = alt_row["종합안전점수"] - current_score
                                        jrate = alt_row.get("전세가율_평균", 0)
                                        jrate_str = f"{jrate:.0%}" if pd.notna(jrate) and jrate > 0 else "-"
                                        st.markdown(
                                            f"""<div style="border:2px solid #22c55e;
                                            border-radius:10px; padding:0.8rem; text-align:center;">
                                            <div style="font-size:1.3rem;">{alt_signal}</div>
                                            <div style="font-size:1rem; font-weight:bold; margin:0.3rem 0;">{alt_row['법정동명']}</div>
                                            <div style="font-size:1.4rem; font-weight:bold; color:#22c55e;">{alt_row['종합안전점수']:.1f}점</div>
                                            <div style="font-size:0.8rem; opacity:0.7;">전세가율 {jrate_str}</div>
                                            <div style="font-size:0.8rem; color:#22c55e;">+{diff:.1f}점 더 안전</div>
                                            </div>""",
                                            unsafe_allow_html=True,
                                        )

                        # 이 매물 계약 시 체크리스트 안내
                        if result["risk_prob"] >= 0.5:
                            st.markdown("---")
                            st.markdown("⚠️ **이 매물은 위험도가 높습니다.** 계약 전 반드시 **계약 가이드** 탭에서 체크리스트를 확인하세요.")

                        with st.expander("동네 과거 거래 통계 + 유사 거래 사례", expanded=False):
                            try:
                                df_rate_local = load_jeonse_rate()
                                dong_trades = df_rate_local[df_rate_local["법정동명"] == dong]
                                if len(dong_trades) > 0:
                                    avg_rate = dong_trades['전세가율'].mean()
                                    max_rate = dong_trades['전세가율'].max()
                                    n_trades = len(dong_trades)
                                    avg_price = dong_trades['매매가_중앙값'].mean()

                                    stat_cols = st.columns(4)
                                    stat_cols[0].metric("평균 전세가율", f"{avg_rate:.0%}")
                                    stat_cols[1].metric("최대 전세가율", f"{max_rate:.0%}")
                                    stat_cols[2].metric("거래 건수", f"{n_trades:,}")
                                    stat_cols[3].metric("평균 매매가", f"{avg_price:,.0f}만")

                                    # 해석 텍스트
                                    if max_rate >= 1.0:
                                        st.warning(f"⚠️ 이 동네에는 전세가율 100% 이상(역전세) 거래가 있었습니다. 보증금이 매매가를 초과하는 거래는 각별히 주의하세요.")
                                    if avg_rate >= 0.80:
                                        st.error(f"🔴 평균 전세가율이 {avg_rate:.0%}로 위험 수준입니다. 이 동네에서 전세 계약 시 HUG 보증보험 가입을 강력 권장합니다.")
                                    elif avg_rate >= 0.60:
                                        st.info(f"🟡 평균 전세가율 {avg_rate:.0%} — 주의가 필요합니다. 개별 매물의 전세가율을 반드시 확인하세요.")
                                    else:
                                        st.success(f"🟢 평균 전세가율 {avg_rate:.0%} — 비교적 안전한 수준입니다.")

                                    # 위험거래 비율
                                    danger_count = len(dong_trades[dong_trades['전세가율'] >= 0.80])
                                    if danger_count > 0:
                                        st.caption(f"📊 전체 {n_trades:,}건 중 위험(80%+) 거래 {danger_count}건 ({danger_count/n_trades:.0%})")

                                    # 유사 거래 사례
                                    st.markdown("---")
                                    st.markdown(f"**{dong} 최근 거래 사례 (보증금 유사):**")
                                    similar = dong_trades.copy()
                                    similar["보증금차이"] = abs(similar["전세금_중앙값"] - deposit)
                                    top_similar = similar.nsmallest(5, "보증금차이")
                                    if len(top_similar) > 0:
                                        for _, tr in top_similar.iterrows():
                                            jrate_c = "🔴" if tr["전세가율"] >= 0.80 else "🟡" if tr["전세가율"] >= 0.60 else "🟢"
                                            name = tr.get("단지명", "-")
                                            st.caption(f"{jrate_c} {name} — 전세 {tr['전세금_중앙값']:,.0f}만원 | 전세가율 {tr['전세가율']:.0%}")
                                else:
                                    st.info("해당 동의 거래 데이터가 없습니다")
                            except Exception:
                                pass
                    except Exception as e:
                        st.error(f"분석 실패: {e}")
            else:
                st.info("👈 왼쪽에서 매물 정보를 입력하고 '위험도 체크' 버튼을 누르세요")
                st.markdown("""
**💡 처음이신가요?** 위 '예시 시나리오' 드롭다운에서 프리셋을 선택하면 바로 결과를 볼 수 있습니다:
- 🎓 **대학가 원룸** — 안서동, 보증금 5000만원 (위험 사례)
- 💼 **사회초년생** — 불당동, 보증금 1.5억 (주의 사례)
- ⚠️ **구도심 원룸** — 원성동, 보증금 3000만원 (위험 사례)
- 🟢 **신도시 신축** — 성성동, 보증금 2억 (안전 사례)
""")

    else:  # 비교 분석 모드
        st.subheader("두 매물 비교")
        st.caption("같은 예산으로 동네에 따라 위험도가 어떻게 달라지는지 비교합니다")

        comp_col1, comp_col2 = st.columns(2)
        dong_list = load_dong_list()

        with comp_col1:
            st.markdown("**매물 A**")
            dong_a = st.selectbox("동네", dong_list, index=dong_list.index("안서동") if "안서동" in dong_list else 0, key="cmp_dong_a")
            dep_a = st.number_input("보증금 (만원)", min_value=100, max_value=100000, value=5000, step=500, key="cmp_dep_a")
            area_a = st.number_input("전용면적 (㎡)", min_value=5.0, max_value=200.0, value=33.0, step=1.0, key="cmp_area_a")
            year_a = st.number_input("건축년도", min_value=1970, max_value=2026, value=2000, step=1, key="cmp_year_a")

        with comp_col2:
            st.markdown("**매물 B**")
            dong_b = st.selectbox("동네", dong_list, index=dong_list.index("불당동") if "불당동" in dong_list else 0, key="cmp_dong_b")
            dep_b = st.number_input("보증금 (만원)", min_value=100, max_value=100000, value=5000, step=500, key="cmp_dep_b")
            area_b = st.number_input("전용면적 (㎡)", min_value=5.0, max_value=200.0, value=33.0, step=1.0, key="cmp_area_b")
            year_b = st.number_input("건축년도", min_value=1970, max_value=2026, value=2018, step=1, key="cmp_year_b")

        if st.button("🔍 비교 분석", type="primary", use_container_width=True, key="cmp_run"):
            predict_fn = load_predict_fn()
            res_col1, res_col2 = st.columns(2)

            with res_col1:
                st.markdown(f"### 매물 A: {dong_a}")
                try:
                    r_a = predict_fn(보증금_만원=float(dep_a), 전용면적=float(area_a),
                                     법정동명=dong_a, 건축년도=int(year_a), 구=_auto_gu(dong_a))
                    _render_result(r_a, dong_a, compact=True)
                except Exception as e:
                    st.error(f"분석 실패: {e}")
                    r_a = None

            with res_col2:
                st.markdown(f"### 매물 B: {dong_b}")
                try:
                    r_b = predict_fn(보증금_만원=float(dep_b), 전용면적=float(area_b),
                                     법정동명=dong_b, 건축년도=int(year_b), 구=_auto_gu(dong_b))
                    _render_result(r_b, dong_b, compact=True)
                except Exception as e:
                    st.error(f"분석 실패: {e}")
                    r_b = None

            if r_a and r_b:
                st.divider()
                st.subheader("비교 결과")
                diff = r_a["risk_prob"] - r_b["risk_prob"]
                safer = dong_b if diff > 0 else dong_a
                safer_risk = min(r_a["risk_prob"], r_b["risk_prob"])
                riskier = dong_a if diff > 0 else dong_b
                riskier_risk = max(r_a["risk_prob"], r_b["risk_prob"])

                st.markdown(
                    f"**{safer}**({safer_risk:.1%})이 **{riskier}**({riskier_risk:.1%})보다 "
                    f"**{abs(diff):.1%}p 더 안전**합니다."
                )

                fig_cmp = go.Figure()
                fig_cmp.add_trace(go.Bar(
                    x=[dong_a, dong_b], y=[r_a["risk_prob"]*100, r_b["risk_prob"]*100],
                    marker_color=[
                        "#e74c3c" if r_a["risk_prob"] >= 0.7 else "#f39c12" if r_a["risk_prob"] >= 0.3 else "#27ae60",
                        "#e74c3c" if r_b["risk_prob"] >= 0.7 else "#f39c12" if r_b["risk_prob"] >= 0.3 else "#27ae60",
                    ],
                    text=[f"<b>{r_a['risk_prob']:.1%}</b>", f"<b>{r_b['risk_prob']:.1%}</b>"],
                    textposition="outside", textfont=dict(size=16),
                ))
                fig_cmp.update_layout(
                    height=300, yaxis_title="위험확률 (%)", yaxis_range=[0, 110],
                    xaxis=dict(tickfont=dict(size=14)),
                    title=dict(text="매물 위험도 비교", font=dict(size=16)),
                )
                st.plotly_chart(fig_cmp, use_container_width=True)

                # 안전점수 비교
                sa = r_a.get("safety_score")
                sb = r_b.get("safety_score")
                if sa and sb:
                    safer_dong = dong_a if sa > sb else dong_b
                    st.info(f"🏠 동네 안전점수: **{dong_a}** {sa:.1f}점 vs **{dong_b}** {sb:.1f}점 → **{safer_dong}**이 더 안전한 동네입니다")

    # 탭 1 하단 CTA
    st.divider()
    st.markdown("**다음 단계:**")
    cta_cols = st.columns(3)
    with cta_cols[0]:
        st.markdown("""<div style="border:1px solid rgba(52,152,219,0.4); border-radius:10px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem;">🗺️</div>
        <div style="font-weight:bold; margin:0.3rem 0;">안전지도</div>
        <div style="font-size:0.8rem; opacity:0.7;">동네별 안전점수를 지도에서 비교</div>
        </div>""", unsafe_allow_html=True)
    with cta_cols[1]:
        st.markdown("""<div style="border:1px solid rgba(39,174,96,0.4); border-radius:10px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem;">💰</div>
        <div style="font-weight:bold; margin:0.3rem 0;">예산별 추천</div>
        <div style="font-size:0.8rem; opacity:0.7;">내 예산에 맞는 안전한 동네 찾기</div>
        </div>""", unsafe_allow_html=True)
    with cta_cols[2]:
        st.markdown("""<div style="border:1px solid rgba(243,156,18,0.4); border-radius:10px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem;">✅</div>
        <div style="font-weight:bold; margin:0.3rem 0;">계약 가이드</div>
        <div style="font-size:0.8rem; opacity:0.7;">계약 전 필수 체크리스트 확인</div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 탭 2: 안전지도
# ═══════════════════════════════════════════
with tab2:
    chapter_divider("02", "천안시 동네별 안전지도")
    st.caption("행정동 31개 지도 (법정동 65개 안전점수 집계) — 마우스를 올리면 상세 점수가 나타납니다  ·  "
               "ⓘ 신호등 '위험'은 8축 종합점수 기준(1개 동), '경보 19개 동'은 전세가율 추세 기준 — 서로 다른 렌즈입니다")

    df_safety = load_safety_scores()

    # ── (신규) 시네마틱 SVG choropleth: 행정경계 + district-cell-in ──
    from styles.svg_map import render_cinematic_map
    render_cinematic_map(df_safety, height_px=620)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""<div class='chapter-tag'>
            <span class='num'>CH. 02.5</span>
            <span class='title'>정밀 인터랙션 — 65개 법정동 마커 + 히트맵</span>
            <span class='rule'></span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption("정확한 좌표 · 클릭 시 아래 상세 정보 자동 갱신 | 🔴위험 🟡주의 🟢안전")

    # 지도 생성
    m = folium.Map(location=[36.815, 127.114], zoom_start=12, tiles="CartoDB dark_matter")
    folium.TileLayer("CartoDB positron", name="라이트 지도").add_to(m)

    marker_layer = folium.FeatureGroup(name="동네별 안전점수")
    heat_data = []

    for _, row in df_safety.iterrows():
        dong = row["법정동명"]
        if dong not in DONG_COORDS:
            continue

        score = row["종합안전점수"]
        signal = row["신호등"]
        lat, lon = DONG_COORDS[dong]

        if signal == "빨강":
            color = "#e74c3c"
        elif signal == "초록":
            color = "#27ae60"
        else:
            color = "#f39c12"

        count = row.get("전세거래수", 0)
        radius = max(5, min(25, (count or 0) ** 0.5 * 1.5))

        jr = row.get("전세가율_평균", 0)
        jr_str = f"{jr:.0%}" if pd.notna(jr) and jr > 0 else "데이터 없음"
        cnt_str = f"{int(count)}" if pd.notna(count) and count > 0 else "데이터 없음"
        popup_html = f"""
        <b>{dong}</b><br>
        종합안전: <b>{score:.1f}</b>/100<br>
        신호등: {signal}<br>
        금융: {row['금융안전_점수']:.2f} | 건물: {row['건물노후_점수']:.2f}<br>
        치안: {row['치안_점수']:.2f} | 편의: {row['편의시설_점수']:.2f}<br>
        전세가율: {jr_str}<br>
        거래수: {cnt_str}
        """
        tooltip_text = f"{dong} | {score:.1f}점 | {signal}"

        folium.CircleMarker(
            location=[lat, lon], radius=radius,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=folium.Tooltip(tooltip_text),
            color=color, fill=True, fill_color=color, fill_opacity=0.7, weight=2,
        ).add_to(marker_layer)

        jeonse_rate = row.get("전세가율_평균", 0) or 0
        n_trades = int(count) if pd.notna(count) else 1
        for _ in range(max(1, n_trades // 10)):
            heat_data.append([lat, lon, max(0, jeonse_rate)])

    marker_layer.add_to(m)

    heat_layer = folium.FeatureGroup(name="위험 히트맵 (전세가율)")
    HeatMap(
        heat_data, radius=30, blur=20, max_zoom=13,
        gradient={0.2: '#27ae60', 0.5: '#f39c12', 0.7: '#e67e22', 1.0: '#e74c3c'},
    ).add_to(heat_layer)
    heat_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # ── st_folium으로 렌더 → 마커 클릭 시 아래 selectbox 자동 갱신 ──
    st.caption("💡 마커 클릭 또는 아래 **동네 선택**에서 고르면 실제 Google Roadmap이 표시됩니다.")
    map_state = st_folium(
        m, height=550, width=None,
        returned_objects=["last_object_clicked"],
        key="safety_map",
    )

    # 마커 클릭 감지 → session_state["map_detail_dong"] 갱신 (아래 selectbox와 동기화)
    clicked = map_state.get("last_object_clicked") if map_state else None
    if clicked and clicked.get("lat") is not None:
        c_lat, c_lon = float(clicked["lat"]), float(clicked["lng"])
        best_dong, best_dist = None, float("inf")
        for dong, (lat, lon) in DONG_COORDS.items():
            d = (lat - c_lat) ** 2 + (lon - c_lon) ** 2
            if d < best_dist:
                best_dist = d
                best_dong = dong
        # 유클리드 임계값: 약 500m 이내면 그 동으로 매칭
        if best_dong and best_dist < 0.005 ** 2 * 100:  # ~0.005도 ≈ 500m
            prev = st.session_state.get("_last_clicked_dong")
            if best_dong != prev:
                st.session_state["_last_clicked_dong"] = best_dong
                st.session_state["map_detail_dong"] = best_dong
                st.rerun()

    # 요약 카드
    col1, col2, col3, col4 = st.columns(4)
    red_count = len(df_safety[df_safety["신호등"] == "빨강"])
    yellow_count = len(df_safety[df_safety["신호등"] == "노랑"])
    green_count = len(df_safety[df_safety["신호등"] == "초록"])
    col1.metric("🔴 위험", f"{red_count}개 동")
    col2.metric("🟡 주의", f"{yellow_count}개 동")
    col3.metric("🟢 안전", f"{green_count}개 동")
    col4.metric("총 분석", f"{len(df_safety)}개 동")

    # 위험 동 빠른 경고
    red_dongs = df_safety[df_safety["신호등"] == "빨강"].sort_values("종합안전점수")
    if len(red_dongs) > 0:
        red_names = ", ".join(red_dongs["법정동명"].tolist())
        st.error(f"🚨 **위험 동네**: {red_names} — 이 지역에서 전세 계약 시 각별한 주의가 필요합니다")

    # 동 상세 정보
    st.divider()
    st.subheader("동네 상세 정보")
    _dong_list = load_dong_list()
    _default_idx = _dong_list.index("불당동") if "불당동" in _dong_list else 0
    detail_dong = st.selectbox("동네 선택", _dong_list, index=_default_idx, key="map_detail_dong")
    detail_row = df_safety[df_safety["법정동명"] == detail_dong]

    # ── Google Roadmap 임베드 (선택된 동네) ──
    if detail_dong in DONG_COORDS:
        d_lat, d_lon = DONG_COORDS[detail_dong]
        # 좌표 대신 "천안시 {동네}"로 검색 → Google이 정확 지오코딩
        import urllib.parse
        query = urllib.parse.quote(f"천안시 {detail_dong}")

        gr_col1, gr_col2 = st.columns([3, 1])
        with gr_col1:
            st.markdown(f"##### 📍 {detail_dong} — 실제 위치 (Google Roadmap)")
        with gr_col2:
            gmap_url = f"https://www.google.com/maps/search/?api=1&query={query}"
            st.link_button("🔗 Google Maps 열기", gmap_url, use_container_width=True)

        # 검색 기반 embed URL (스트리트뷰 fallback 없음)
        embed_url = f"https://maps.google.com/maps?q={query}&hl=ko&z=16&output=embed"
        st.components.v1.iframe(embed_url, height=360)

        # 항공사진(위성뷰) 링크 — 스트리트뷰는 소규모 동네 미지원 많음
        satellite_url = f"https://www.google.com/maps/@{d_lat},{d_lon},17z/data=!3m1!1e3"
        st.markdown(
            f"<div style='text-align:center;margin-top:0.3rem;margin-bottom:0.6rem;'>"
            f"<a href='{satellite_url}' target='_blank' style='font-size:0.9rem;color:#90caf9;'>"
            f"🛰️ 위성뷰로 보기</a>"
            f"</div>",
            unsafe_allow_html=True,
        )

    if len(detail_row) > 0:
        dr = detail_row.iloc[0]
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        signal_icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}.get(dr["신호등"], "⚪")
        d_col1.metric(f"{signal_icon} 종합안전", f"{dr['종합안전점수']:.1f}/100")
        jrate_val = dr['전세가율_평균']
        d_col2.metric("전세가율", f"{jrate_val:.0%}" if pd.notna(jrate_val) and jrate_val > 0 else "데이터 없음")
        trade_cnt = dr['전세거래수']
        d_col3.metric("거래수", f"{int(trade_cnt):,}" if pd.notna(trade_cnt) and trade_cnt > 0 else "데이터 없음")
        d_col4.metric("금융안전", f"{dr['금융안전_점수']*100:.0f}/100")

        # 8축 레이더 차트 (비교 동네 선택 가능)
        axes = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]
        values = [dr[f"{a}_점수"] for a in axes]
        values.append(values[0])
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values, theta=axes + [axes[0]], fill="toself",
            name=detail_dong, line_color="#3498db",
        ))

        # 비교 동네 선택
        compare_dong = st.selectbox(
            "비교할 동네 (선택사항)", ["없음"] + [d for d in load_dong_list() if d != detail_dong],
            key="map_compare_dong",
        )
        if compare_dong != "없음":
            cmp_row = df_safety[df_safety["법정동명"] == compare_dong]
            if len(cmp_row) > 0:
                cr = cmp_row.iloc[0]
                cmp_values = [cr[f"{a}_점수"] for a in axes]
                cmp_values.append(cmp_values[0])
                fig_radar.add_trace(go.Scatterpolar(
                    r=cmp_values, theta=axes + [axes[0]], fill="toself",
                    name=compare_dong, line_color="#e74c3c", opacity=0.6,
                ))

        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(46,134,230,0.05)",
                radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=10, color="#55677F"),
                                gridcolor="rgba(46,134,230,0.18)"),
                angularaxis=dict(tickfont=dict(size=12, color="#16233A"),
                                 gridcolor="rgba(46,134,230,0.18)"),
            ),
            height=400,
            title=dict(
                text=f"안전 프로필 비교" if compare_dong != "없음" else f"{detail_dong} 안전 프로필",
                font=dict(size=15),
            ),
            legend=dict(font=dict(size=12)),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        try:
            trends = pd.read_parquet(PROCESSED_DIR / "dong_jeonse_trends.parquet")
            t_row = trends[trends["법정동명"] == detail_dong]
            if len(t_row) > 0:
                tr = t_row.iloc[0]
                st.markdown(f"📈 6개월 전세가율 추세: **{tr['6개월_추세']:+.1%}** ({tr['추세_판정']})")
        except FileNotFoundError:
            pass

    # 구도심-신도심 비교 (접힘)
    with st.expander("구도심 vs 신도심 비교", expanded=False):
        df_safety["구"] = df_safety["법정동명"].apply(
            lambda x: "동남구" if x in DONGNAM_DONGS or any(k in x for k in ["목천","병천","북면","풍세","성남"]) else "서북구"
        )
        col_dn, col_sb = st.columns(2)
        with col_dn:
            dn = df_safety[df_safety["구"] == "동남구"]
            st.markdown("**🏙️ 동남구 (구도심)**")
            st.markdown(f"- 평균 안전점수: **{dn['종합안전점수'].mean():.1f}**/100")
            st.markdown(f"- 평균 전세가율: **{dn['전세가율_평균'].mean():.0%}**")
            worst_dn = dn.nsmallest(3, "종합안전점수")
            st.markdown(f"- 주의 동네: {', '.join(worst_dn['법정동명'].tolist())}")
        with col_sb:
            sb = df_safety[df_safety["구"] == "서북구"]
            st.markdown("**🌆 서북구 (신도심)**")
            st.markdown(f"- 평균 안전점수: **{sb['종합안전점수'].mean():.1f}**/100")
            st.markdown(f"- 평균 전세가율: **{sb['전세가율_평균'].mean():.0%}**")
            best_sb = sb.nlargest(3, "종합안전점수")
            st.markdown(f"- 안전 동네: {', '.join(best_sb['법정동명'].tolist())}")
        gap = sb["종합안전점수"].mean() - dn["종합안전점수"].mean()
        if gap > 3:
            st.info(f"서북구가 동남구보다 평균 {gap:.1f}점 높습니다. 구도심은 전세가율이 높고 건물이 노후한 곳이 많아 계약 시 더 주의가 필요합니다.")

        # 비교 차트
        compare_data = pd.DataFrame({
            "구분": ["동남구(구도심)", "서북구(신도심)"],
            "평균 안전점수": [dn["종합안전점수"].mean(), sb["종합안전점수"].mean()],
            "평균 전세가율": [dn["전세가율_평균"].mean() * 100, sb["전세가율_평균"].mean() * 100],
            "평균 건물연령": [dn["평균건물연령"].mean() if "평균건물연령" in dn.columns else 0,
                         sb["평균건물연령"].mean() if "평균건물연령" in sb.columns else 0],
        })
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(name="안전점수", x=compare_data["구분"], y=compare_data["평균 안전점수"],
                                     marker_color=["#e74c3c", "#27ae60"], text=[f"{v:.1f}" for v in compare_data["평균 안전점수"]], textposition="outside"))
        fig_compare.update_layout(height=280, yaxis_title="점수", title="구도심 vs 신도심 안전점수 비교")
        st.plotly_chart(fig_compare, use_container_width=True)


# ═══════════════════════════════════════════
# 탭 3: 예산별 추천
# ═══════════════════════════════════════════
with tab3:
    chapter_divider("03", "내 예산으로 어디가 안전할까")
    st.caption("보증금 예산을 입력하면 해당 가격대에서 안전한 동네를 추천합니다")

    df_safety = load_safety_scores()
    df_rate = load_jeonse_rate()

    # 예산 입력 — 빠른 버튼과 슬라이더 동기화
    if "budget_val" not in st.session_state:
        st.session_state["budget_val"] = 5000

    budget_col1, budget_col2 = st.columns([1, 2])

    with budget_col1:
        st.subheader("내 조건")

        st.markdown("**예산 빠른 선택:**")
        quick_budgets = st.columns(3)
        with quick_budgets[0]:
            if st.button("3천만", key="b3k", use_container_width=True):
                st.session_state["budget_val"] = 3000
                st.rerun()
        with quick_budgets[1]:
            if st.button("5천만", key="b5k", use_container_width=True):
                st.session_state["budget_val"] = 5000
                st.rerun()
        with quick_budgets[2]:
            if st.button("1억", key="b1e", use_container_width=True):
                st.session_state["budget_val"] = 10000
                st.rerun()

        budget = st.slider("보증금 예산 (만원)", min_value=1000, max_value=30000,
                           value=st.session_state["budget_val"], step=500,
                           help="이 예산 이하로 전세 거래가 있는 동네를 찾습니다",
                           key="budget_slider")
        st.session_state["budget_val"] = budget

        min_trades = st.slider("최소 거래 건수", min_value=1, max_value=50, value=3, step=1,
                               help="이 수 이상의 거래가 있는 동네만 추천합니다 (거래가 너무 적으면 신뢰도 낮음)")
        prefer_new = st.checkbox("신축 선호 (2010년 이후)", value=False)

    with budget_col2:
        st.subheader("추천 동네")

        # 예산에 맞는 동네 찾기: 전세 거래 데이터에서 해당 예산 이하 거래가 있는 동 필터
        budget_val = budget
        budget_range_low = budget_val * 0.5
        budget_range_high = budget_val * 1.2

        matching_trades = df_rate[
            (df_rate["전세금_중앙값"] >= budget_range_low) &
            (df_rate["전세금_중앙값"] <= budget_range_high)
        ]

        if len(matching_trades) > 0:
            dong_trade_count = matching_trades.groupby("법정동명").agg(
                거래수=("전세금_중앙값", "count"),
                평균전세금=("전세금_중앙값", "mean"),
                평균전세가율=("전세가율", "mean"),
            ).reset_index()

            # 안전점수 병합
            recommend = dong_trade_count.merge(
                df_safety[["법정동명", "종합안전점수", "신호등", "전세가율_평균", "평균건물연령", "금융안전_점수"]],
                on="법정동명", how="inner"
            )

            # 최소 거래 건수 필터
            recommend = recommend[recommend["거래수"] >= min_trades]

            if prefer_new:
                recommend = recommend[recommend["평균건물연령"].fillna(99) <= 16]

            # 안전점수 + 낮은 전세가율 종합 정렬
            recommend["전세가율_평균"] = recommend["전세가율_평균"].fillna(0.5)
            recommend["추천점수"] = recommend["종합안전점수"] * 0.6 + (1 - recommend["평균전세가율"].clip(0, 1.5)) * 40
            # 규정 일관성: 전세가율 80%+(위험선 초과) 동네는 추천에서 제외
            _excluded = recommend[recommend["전세가율_평균"] >= 0.80]["법정동명"].tolist()
            recommend = recommend[recommend["전세가율_평균"] < 0.80]
            # 순위 기준을 헤더 문구("가장 안전한 동네")와 일치시킴: 안전점수 → 동률 시 낮은 전세가율
            recommend = recommend.sort_values(["종합안전점수", "전세가율_평균"], ascending=[False, True])

            top_dongs = recommend.head(5)

            if len(top_dongs) > 0:
                # 요약 문장
                best = top_dongs.iloc[0]
                budget_str = f"{budget_val/10000:.0f}억" if budget_val >= 10000 else f"{budget_val:,}만원"
                st.success(
                    f"💡 **{budget_str} 예산**으로 가장 안전한 동네는 **{best['법정동명']}** "
                    f"(안전점수 {best['종합안전점수']:.1f}, 평균 전세금 {best['평균전세금']:,.0f}만원)입니다."
                )

                _ANCHORS = {"병천": "🎓 한기대 도보권", "안서동": "🎓 단국대·백석대 캠퍼스권",
                            "부대동": "🎓 공주대 천안캠", "쌍용동": "🎓 나사렛대 인근",
                            "성환": "🚇 1호선 성환역 · 남서울대", "두정동": "🚇 1호선 두정역",
                            "성정동": "🚇 1호선 두정역 생활권", "불당동": "🚄 KTX 천안아산역",
                            "백석동": "🚄 KTX 생활권 · 백석대", "신월": "🏭 성거 산단 인접",
                            "직산": "🚇 1호선 직산역 · 산단 통근"}
                for rank, (_, r) in enumerate(top_dongs.iterrows(), 1):
                    avg_deposit = r["평균전세금"]
                    score = r["종합안전점수"]
                    jrate = r["전세가율_평균"]
                    border_c = "#10B981" if r["신호등"] == "초록" else "#F59E0B" if r["신호등"] == "노랑" else "#EF4444"
                    rank_label = ["1", "2", "3", "4", "5"][rank - 1]
                    medal_bg = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}.get(rank, "#DCE6F2")
                    medal_fg = "#16233A" if rank <= 3 else "#55677F"
                    is_top = rank == 1
                    fin_score = r.get("금융안전_점수", 0)
                    fin_label = "양호" if fin_score >= 0.7 else "주의" if fin_score >= 0.4 else "위험"
                    _anchor = next((v for k, v in _ANCHORS.items() if k in r["법정동명"]), None)
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:16px;background:{'#F0F7FF' if is_top else '#FFFFFF'};
            border:{'2px solid #2E86E6' if is_top else '1px solid #DCE6F2'};border-left:5px solid {border_c};
            border-radius:14px;padding:14px 18px;margin-bottom:10px;
            box-shadow:0 3px 12px rgba(23,64,133,{'0.10' if is_top else '0.05'});">
  <div style="min-width:44px;height:44px;border-radius:50%;background:{medal_bg};color:{medal_fg};
              display:flex;align-items:center;justify-content:center;font-size:1.15rem;font-weight:800;
              box-shadow:inset 0 -2px 4px rgba(0,0,0,0.12);">{rank_label}위</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:1.08rem;font-weight:800;color:#16233A;">
      {r['법정동명']} {'<span style="font-size:0.72rem;background:#2E86E6;color:#fff;border-radius:999px;padding:2px 9px;margin-left:6px;vertical-align:middle;">최고 추천</span>' if is_top else ''}</div>
    <div style="font-size:0.82rem;color:#55677F;margin-top:3px;">
      거래 {int(r['거래수'])}건 · 평균 전세금 {avg_deposit:,.0f}만원 · 금융안전 {fin_label}{f' · <b style="color:#1E64B8;">{_anchor}</b>' if _anchor else ''}</div>
  </div>
  <div style="text-align:center;min-width:86px;border-left:1px solid #E8F0FA;padding-left:16px;">
    <div style="font-size:0.72rem;color:#8494A9;">안전점수</div>
    <div style="font-size:1.35rem;font-weight:800;color:{border_c};">{score:.1f}</div>
  </div>
  <div style="text-align:center;min-width:86px;border-left:1px solid #E8F0FA;padding-left:16px;">
    <div style="font-size:0.72rem;color:#8494A9;">전세가율</div>
    <div style="font-size:1.35rem;font-weight:800;color:#16233A;">{jrate:.0%}</div>
  </div>
</div>""", unsafe_allow_html=True)

                if _excluded:
                    st.caption(f"ⓘ 이 예산대 후보 중 평균 전세가율 80% 이상(규정상 위험선 초과)인 {len(_excluded)}개 동을 추천에서 제외했습니다: {', '.join(_excluded[:4])}{' 외' if len(_excluded) > 4 else ''}")
                st.markdown("---")
                st.info(f"💡 보증금 {budget_val:,}만원 기준으로 {budget_range_low:,.0f}~{budget_range_high:,.0f}만원 범위의 거래가 있는 동네입니다.")
                st.markdown("👉 관심 동네의 구체적인 매물 위험도는 **내 매물 체크** 탭에서 확인하세요.")

                # 추천 동네 지도
                with st.expander("추천 동네 지도", expanded=True):
                    from styles.svg_map import render_reco_svg
                    _sel = [
                        {"법정동명": r["법정동명"], "rank": _ri + 1,
                         "score": float(r["종합안전점수"]), "grade": str(r["신호등"])}
                        for _ri, (_, r) in enumerate(top_dongs.iterrows())
                    ]
                    render_reco_svg(_sel)
                    st.caption("오프라인 벡터 지도 — 외부 타일 서버 없이 렌더링됩니다 (시연 안전)")
            else:
                st.warning("해당 조건에 맞는 동네가 없습니다. 예산을 조정해보세요.")
        else:
            st.warning("해당 예산 범위에 거래 데이터가 부족합니다. 예산을 조정해보세요.")

    # 탭 3 하단 CTA
    st.divider()
    st.markdown("**다음 단계:**")
    cta3_cols = st.columns(2)
    with cta3_cols[0]:
        st.markdown("""<div style="border:1px solid rgba(52,152,219,0.4); border-radius:10px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem;">🔍</div>
        <div style="font-weight:bold; margin:0.3rem 0;">내 매물 체크</div>
        <div style="font-size:0.8rem; opacity:0.7;">관심 동네의 구체적인 매물 위험도 분석</div>
        </div>""", unsafe_allow_html=True)
    with cta3_cols[1]:
        st.markdown("""<div style="border:1px solid rgba(243,156,18,0.4); border-radius:10px; padding:1rem; text-align:center;">
        <div style="font-size:1.5rem;">✅</div>
        <div style="font-weight:bold; margin:0.3rem 0;">계약 가이드</div>
        <div style="font-size:0.8rem; opacity:0.7;">계약 전 필수 체크리스트 확인</div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 탭 4: 계약 가이드
# ═══════════════════════════════════════════
with tab4:
    chapter_divider("04", "전세 계약 전 체크리스트")
    st.caption("계약 전 꼭 확인해야 할 사항을 하나씩 체크하세요 — 하나라도 빠지면 위험합니다")

    _cta1, _cta2, _cta3 = st.columns(3)
    with _cta1:
        st.link_button("🏛 천안시 안심계약 도움서비스 신청", "https://www.cheonan.go.kr", use_container_width=True)
    with _cta2:
        st.link_button("💰 청년월세지원 자격 확인 (복지로)", "https://www.bokjiro.go.kr", use_container_width=True)
    with _cta3:
        st.link_button("🛡 HUG 전세보증금 반환보증", "https://www.khug.or.kr", use_container_width=True)

    # 체크리스트 상태 관리
    if "checklist" not in st.session_state:
        st.session_state.checklist = {}

    checklist_items = [
        {
            "id": "registry",
            "title": "등기부등본 확인",
            "desc": "계약 당일 등기부등본을 직접 발급받아 소유자·근저당·가압류·전세권을 확인하세요.",
            "detail": "인터넷등기소(iros.go.kr)에서 발급 가능 (수수료 700원). 근저당이 설정되어 있으면 보증금 회수가 어려울 수 있습니다.",
            "risk": "미확인 시 가짜 집주인 사기, 근저당 과다 설정 등의 피해 가능",
        },
        {
            "id": "owner_verify",
            "title": "임대인 본인 확인",
            "desc": "등기부등본상 소유자와 계약 상대방이 동일인인지 신분증으로 확인하세요.",
            "detail": "대리인 계약 시 위임장 + 인감증명서 필수. 소유자 본인에게 직접 전화로 확인하는 것이 가장 안전합니다.",
            "risk": "대리인 사칭, 이중계약 등의 전세사기 피해 가능",
        },
        {
            "id": "jeonse_rate",
            "title": "전세가율 확인 (80% 이하인가?)",
            "desc": "보증금 ÷ 매매가 = 전세가율. 80% 이상이면 위험, 90% 이상이면 깡통전세입니다.",
            "detail": "국토교통부 실거래가 공개시스템(rt.molit.go.kr)에서 주변 매매가를 확인하세요. '내 매물 체크' 탭에서 AI 위험도 분석도 가능합니다.",
            "risk": "전세가율이 높으면 집값 하락 시 보증금을 돌려받지 못할 수 있음",
        },
        {
            "id": "hug_insurance",
            "title": "전세보증금 반환보증 가입",
            "desc": "HUG(주택도시보증공사) 전세보증금 반환보증에 가입하면 임대인이 보증금을 못 돌려줘도 HUG가 대신 갚아줍니다.",
            "detail": "보증료: 연 0.115~0.154%. 보증금 5천만원이면 연 5.7~7.7만원 수준. 전입신고 + 확정일자 받기 전에 신청해야 합니다.",
            "risk": "보증 미가입 시 임대인 파산/잠적 때 보증금 전액 손실 가능",
        },
        {
            "id": "move_in",
            "title": "전입신고 + 확정일자",
            "desc": "이사 당일 주민센터에서 전입신고하고, 계약서에 확정일자를 받으세요.",
            "detail": "전입신고 + 확정일자 = 대항력 + 우선변제권 확보. 이 두 가지가 없으면 경매 시 보증금을 돌려받을 수 없습니다.",
            "risk": "전입신고 지연 시 제3자에게 권리를 주장할 수 없음",
        },
        {
            "id": "building_check",
            "title": "건물 상태 확인",
            "desc": "건물 연식, 관리 상태, 누수·곰팡이, 소방시설을 직접 확인하세요.",
            "detail": "건축물대장은 정부24(gov.kr)에서 무료 열람. 건축년도 30년 이상이면 노후 건물. 소화기·감지기 설치 여부도 확인.",
            "risk": "노후 건물은 하자 보수비 부담 + 안전사고 위험",
        },
        {
            "id": "neighborhood",
            "title": "동네 안전성 확인",
            "desc": "'안전지도' 탭에서 동네 종합 안전점수, 치안, 편의시설을 확인하세요.",
            "detail": "CCTV 설치 현황, 가로등, 편의점·병원 접근성, 대중교통 등을 종합적으로 고려합니다.",
            "risk": "치안이 취약한 지역은 1인 가구에게 특히 위험",
        },
        {
            "id": "special_clause",
            "title": "특약사항 기재",
            "desc": "계약서에 '임대인 귀책 시 보증금 즉시 반환' 등 보호 특약을 넣으세요.",
            "detail": "추천 특약: ①임대인 근저당 추가 설정 금지 ②임대인 변경 시 보증금 반환 보증 ③계약 해지 시 보증금 반환 기한 명시",
            "risk": "특약 없이 계약하면 분쟁 시 보호받기 어려움",
        },
    ]

    # 진행률 표시
    checked = sum(1 for item in checklist_items if st.session_state.checklist.get(item["id"], False))
    total = len(checklist_items)
    progress = checked / total

    if progress == 1.0:
        st.success(f"🎉 모든 항목을 확인했습니다! ({checked}/{total}) — 안전하게 계약을 진행하세요")
    elif progress >= 0.75:
        st.info(f"거의 다 됐습니다! {checked}/{total} 항목 확인 — 나머지 {total - checked}개도 꼭 확인하세요")
    elif progress >= 0.5:
        st.info(f"진행 중: {checked}/{total} 항목 확인 ({progress:.0%})")
    elif checked > 0:
        st.warning(f"⚠️ 아직 {total - checked}개 항목을 확인하지 않았습니다 ({checked}/{total}) — 하나라도 빠지면 위험합니다")
    else:
        st.info(f"📋 총 {total}개 체크 항목이 있습니다. 위에서부터 하나씩 체크해 보세요!")

    st.progress(progress)

    # 체크리스트 렌더
    step_icons = ["📋", "👤", "📊", "🛡️", "🏠", "🔧", "🗺️", "📝"]
    for idx, item in enumerate(checklist_items):
        is_checked = st.session_state.checklist.get(item["id"], False)

        col_check, col_num, col_content = st.columns([0.4, 0.6, 9])
        with col_check:
            new_val = st.checkbox("", value=is_checked, key=f"check_{item['id']}", label_visibility="collapsed")
            if new_val != is_checked:
                st.session_state.checklist[item["id"]] = new_val
                st.rerun()
        with col_num:
            icon = step_icons[idx] if idx < len(step_icons) else "📌"
            done_mark = "✅" if is_checked else icon
            st.markdown(f"### {done_mark}")
        with col_content:
            if is_checked:
                st.markdown(f"~~**{item['title']}**~~ — 확인 완료")
            else:
                st.markdown(f"**{item['title']}**")
            st.caption(item["desc"])
            with st.expander("자세히 보기 + 위험 안내"):
                st.markdown(item["detail"])
                st.error(f"⚠️ 미확인 시 위험: {item['risk']}")

    st.divider()
    st.markdown("**유용한 링크:**")
    link_cols = st.columns(4)
    link_cols[0].markdown("""<a href="https://www.iros.go.kr" target="_blank" style="text-decoration:none;">
    <div style="border:1px solid rgba(128,128,128,0.3); border-radius:8px; padding:0.8rem; text-align:center;">
    📋<br><b>인터넷등기소</b><br><span style="font-size:0.7rem; opacity:0.6;">등기부등본 발급</span>
    </div></a>""", unsafe_allow_html=True)
    link_cols[1].markdown("""<a href="https://rt.molit.go.kr" target="_blank" style="text-decoration:none;">
    <div style="border:1px solid rgba(128,128,128,0.3); border-radius:8px; padding:0.8rem; text-align:center;">
    🏠<br><b>실거래가 공개</b><br><span style="font-size:0.7rem; opacity:0.6;">매매/전세 시세 확인</span>
    </div></a>""", unsafe_allow_html=True)
    link_cols[2].markdown("""<a href="https://www.khug.or.kr" target="_blank" style="text-decoration:none;">
    <div style="border:1px solid rgba(128,128,128,0.3); border-radius:8px; padding:0.8rem; text-align:center;">
    🛡️<br><b>HUG 보증보험</b><br><span style="font-size:0.7rem; opacity:0.6;">전세보증금 반환보증</span>
    </div></a>""", unsafe_allow_html=True)
    link_cols[3].markdown("""<a href="https://www.gov.kr" target="_blank" style="text-decoration:none;">
    <div style="border:1px solid rgba(128,128,128,0.3); border-radius:8px; padding:0.8rem; text-align:center;">
    🏗️<br><b>정부24</b><br><span style="font-size:0.7rem; opacity:0.6;">건축물대장 열람</span>
    </div></a>""", unsafe_allow_html=True)

    st.caption("💡 이 체크리스트를 인쇄하려면 브라우저의 **Ctrl+P** (인쇄) 기능을 사용하세요. 체크 완료 상태는 이 세션 동안 유지됩니다.")


# ═══════════════════════════════════════════
# 탭 5: AI 상담 챗봇 (RAG + LightGBM Tool)
# ═══════════════════════════════════════════
with tab5:
    chapter_divider("05", "AI 주거안전 상담")
    _nr = _mascot_uri("안내")
    if _nr:
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;">'
                    f'<img src="{_nr}" style="height:44px;border-radius:50%;'
                    f'border:2px solid #2E86E6;background:#fff;"/>'
                    f'<span style="color:#55677F;">천안 마스코트 <b style="color:#16233A;">나랑이</b>가 '
                    f'매물 데이터를 직접 찾아 근거와 함께 답해요 — 자연어로 물어보세요</span></div>',
                    unsafe_allow_html=True)
    else:
        st.caption("매물 데이터를 직접 찾아 근거와 함께 답하는 AI — 자연어로 물어보세요")

    # ── 연결 상태 뱃지 (배포 진단용) ──
    _local_ok = False
    try:
        from scripts import rag_chatbot as _rag
        from scripts.llm import local_llm as _local
        _local_ok = _local.is_available()
        _key_ok = bool(os.getenv("OPENAI_API_KEY")) or _rag._has_openai_key()
    except Exception:
        _key_ok = False

    # ── RAG 아키텍처 안내 + 엔진 상태 (접힘) ──
    with st.expander("🧠 챗봇 아키텍처 (RAG + Tool Use)", expanded=False):
        if _local_ok:
            st.success("🟢 천안세이프 LLM (자체모델)")
        elif _key_ok:
            st.success("🟢 천안세이프 AI 엔진 연결")
        else:
            st.error("🔴 AI 엔진 미연결 (규칙 기반 모드)")

        st.markdown("""
        **파이프라인**: `Query → 천안세이프 LLM(자체 파인튜닝) → Tool Calling(시뮬레이터/동조회/뉴스/추천) → Response`

        | 컴포넌트 | 역할 |
        |---|---|
        | **천안세이프 LLM** | Qwen2.5-7B + 깡통전세 QLoRA 파인튜닝 (RTX 3090×2 자체 학습) — 툴 선택·호출·답변 전담 |
        | **Simulator Tool** | LightGBM 깡통전세 분류기 (AUC 0.989) + SHAP 설명 |
        | **Dong Lookup Tool** | 65개 동 8축 안전점수 · 전세가율 추세 조회 |
        | **News Tool** | Google News RSS 검색 (키 불필요, 한국어 매체 우선) |
        | **Recommend Tool** | exp_006 4-모델 앙상블 기반 예산별 안전 동네·매물 추천 |
        | **Knowledge Base** | 정책·개념·체크리스트 문서 14편 — 파인튜닝 데이터에 내재화 |
        | **Fallback** | 로컬 LLM 미기동 시 OpenAI → rule-based 순 자동 폴백 (무중단) |
        """)

        # 배포 진단 (연결 실패 시만 자세히 표시)
        if st.button("🔧 LLM 연결 진단", key="diag_btn"):
            with st.spinner("진단 중..."):
                info = _rag.diagnose()
            st.json(info)
            if not info["openai_reachable"]:
                st.warning(
                    "**해결 방법**\n\n"
                    "1. Streamlit Cloud 대시보드 → 앱 → **⋯ (설정)** → **Secrets**\n"
                    "2. 아래 형식으로 입력되어 있는지 확인 (따옴표 필수):\n"
                    "```toml\nOPENAI_API_KEY = \"sk-proj-...\"\n```\n"
                    "3. 저장 후 앱 **Reboot**"
                )

    @st.cache_data
    def load_chatbot_context():
        df_safety = pd.read_parquet(PROCESSED_DIR / "dong_safety_score.parquet")
        df_trends = pd.read_parquet(PROCESSED_DIR / "dong_jeonse_trends.parquet")
        return df_safety, df_trends

    @st.cache_resource
    def get_rag_module():
        """RAG 모듈 캐싱 (KB 임베딩 재사용)."""
        from scripts import rag_chatbot
        # KB 임베딩 사전 빌드 (첫 요청 지연 제거)
        rag_chatbot._build_kb_index()
        return rag_chatbot

    def _try_simulate(user_msg: str, dong_name: str) -> str:
        """자연어에서 보증금/면적/건축년도를 추출해 시뮬레이터 실행."""
        import re
        dep_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:만원|만)', user_msg)
        dep_eok = re.search(r'(\d+(?:\.\d+)?)\s*억', user_msg)
        deposit = None
        if dep_match:
            deposit = float(dep_match.group(1))
        elif dep_eok:
            deposit = float(dep_eok.group(1)) * 10000

        area_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:㎡|평|제곱)', user_msg)
        area = None
        if area_match:
            val = float(area_match.group(1))
            area = val * 3.3058 if '평' in user_msg else val

        year_match = re.search(r'(19[7-9]\d|20[0-2]\d)\s*(?:년|식|년식|년도)', user_msg)
        build_year = int(year_match.group(1)) if year_match else None

        if deposit is None:
            return None

        area = area or 59.0
        build_year = build_year or 2010
        gu = _auto_gu(dong_name)

        try:
            predict_fn = load_predict_fn()
            result = predict_fn(보증금_만원=deposit, 전용면적=area, 법정동명=dong_name, 건축년도=build_year, 구=gu)
            risk = result["risk_prob"]
            signal_icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}[result["signal"]]
            safety = f" | 동네 안전점수: {result['safety_score']:.1f}/100" if result["safety_score"] else ""

            shap_lines = []
            for sh in result["shap_top5"][:3]:
                direction = "↑위험" if sh["shap_value"] > 0 else "↓안전"
                shap_lines.append(f"  - {sh['feature']}: {sh['shap_value']:+.3f} ({direction})")

            return (
                f"**AI 위험도 분석 결과** ({dong_name})\n\n"
                f"- 보증금: {deposit:,.0f}만원 | 면적: {area:.0f}㎡ | 건축: {build_year}년\n"
                f"- {signal_icon} **{result['signal_label']}** — 위험확률 **{risk:.1%}**{safety}\n\n"
                f"**주요 위험 요인:**\n" + "\n".join(shap_lines) +
                f"\n\n💡 자세한 분석은 **내 매물 체크** 탭에서 확인하세요."
            )
        except Exception:
            return None

    def mock_llm_response(user_msg: str) -> str:
        msg = user_msg.lower().strip()
        df_safety, df_trends = load_chatbot_context()

        detected_dong = None
        for dong_name in df_safety["법정동명"].tolist():
            if dong_name in user_msg:
                detected_dong = dong_name
                break

        if detected_dong and any(k in msg for k in ["만원", "만", "억", "㎡", "평"]):
            sim_result = _try_simulate(user_msg, detected_dong)
            if sim_result:
                return sim_result

        if detected_dong:
            row = df_safety[df_safety["법정동명"] == detected_dong]
            if len(row) > 0:
                r = row.iloc[0]
                trend_row = df_trends[df_trends["법정동명"] == detected_dong]
                trend_info = ""
                if len(trend_row) > 0:
                    tr = trend_row.iloc[0]
                    trend_info = f"\n📈 최근 전세가율: {tr['최근_전세가율']:.0%}, 6개월 추세: {tr['6개월_추세']:+.1%} ({tr['추세_판정']})"

                jrate_display = f"{r['전세가율_평균']:.0%}" if pd.notna(r['전세가율_평균']) and r['전세가율_평균'] > 0 else "데이터 없음"

                # 8축 레이더 차트를 세션에 저장 (채팅 메시지 렌더 시 사용)
                axes_names = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]
                axes_vals = [r.get(f"{a}_점수", 0.5) for a in axes_names]
                st.session_state["_chat_radar_data"] = {
                    "dong": detected_dong, "axes": axes_names, "values": axes_vals
                }

                # 텍스트 요약도 포함 (가장 강한/약한 축)
                best_axis = axes_names[axes_vals.index(max(axes_vals))]
                worst_axis = axes_names[axes_vals.index(min(axes_vals))]

                return (
                    f"**{detected_dong}** 분석 결과입니다.\n\n"
                    f"🏠 **종합 안전점수**: {r['종합안전점수']:.1f}/100 ({r['신호등']})\n"
                    f"- 평균 전세가율: {jrate_display}"
                    f"{trend_info}\n\n"
                    f"**8축 안전 프로필:** (차트 참고)\n"
                    f"- 💪 가장 강한 축: **{best_axis}** ({max(axes_vals):.2f})\n"
                    f"- ⚠️ 가장 약한 축: **{worst_axis}** ({min(axes_vals):.2f})\n\n"
                    f"{'⚠️ 이 지역은 주의가 필요합니다. **내 매물 체크** 탭에서 구체적인 매물 위험도를 확인하세요.' if r['신호등'] != '초록' else '✅ 비교적 안전한 지역입니다. 다만 개별 매물은 **내 매물 체크** 탭에서 확인하세요.'}"
                    f"\n\n---RADAR---"
                )

        if any(k in msg for k in ["구도심", "신도심", "격차", "동남구", "서북구"]):
            _dn = df_safety[df_safety["법정동명"].apply(lambda x: x in DONGNAM_DONGS or any(k in x for k in ["목천","병천","북면","풍세","성남"]))]
            _sb = df_safety[~df_safety.index.isin(_dn.index)]
            dn_avg = _dn["종합안전점수"].mean() if len(_dn) > 0 else 0
            sb_avg = _sb["종합안전점수"].mean() if len(_sb) > 0 else 0
            gap = sb_avg - dn_avg
            dn_jrate = _dn["전세가율_평균"].mean()
            sb_jrate = _sb["전세가율_평균"].mean()
            return (
                "**구도심(동남구) vs 신도심(서북구) 비교:**\n\n"
                f"| 항목 | 동남구(구도심) | 서북구(신도심) |\n"
                f"|------|------------|------------|\n"
                f"| 평균 안전점수 | {dn_avg:.1f}점 | {sb_avg:.1f}점 |\n"
                f"| 평균 전세가율 | {dn_jrate:.0%} | {sb_jrate:.0%} |\n"
                f"| 분석 동 수 | {len(_dn)}개 | {len(_sb)}개 |\n\n"
                f"📊 **격차: {gap:.1f}점** — 서북구가 평균 {gap:.1f}점 더 안전합니다.\n\n"
                f"💡 구도심에도 양호한 동네가 있으므로 **안전지도** 탭에서 개별 동네를 확인하세요."
            )

        if any(k in msg for k in ["안전", "어디", "추천", "살기 좋"]):
            top5 = df_safety.nlargest(5, "종합안전점수")
            lines = []
            for rank, (_, r) in enumerate(top5.iterrows(), 1):
                sig = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}.get(r["신호등"], "⚪")
                jrate = f"{r['전세가율_평균']:.0%}" if pd.notna(r['전세가율_평균']) and r['전세가율_평균'] > 0 else "-"
                lines.append(f"{rank}. {sig} **{r['법정동명']}** — 안전 {r['종합안전점수']:.1f}점 | 전세가율 {jrate}")
            result = "천안시 **안전점수 TOP 5** 동네입니다.\n\n" + "\n".join(lines)
            result += "\n\n💡 **예산별 추천** 탭에서 내 예산에 맞는 안전한 동네를 찾아보세요."
            return result

        if any(k in msg for k in ["위험", "조심", "피해"]):
            alerts = df_trends[
                (df_trends["최근_전세가율"] >= 0.80) & (df_trends["6개월_추세"] > 0)
            ].nlargest(5, "6개월_추세")
            if len(alerts) > 0:
                lines = [f"- 🔴 **{r['법정동명']}**: 전세가율 {r['최근_전세가율']:.0%}, 6개월 추세 {r['6개월_추세']:+.1%}↑" for _, r in alerts.iterrows()]
                return (
                    f"🚨 현재 **주의가 필요한 지역 TOP {len(alerts)}**입니다\n"
                    f"(전세가율 80% 이상 + 상승 추세):\n\n"
                    + "\n".join(lines)
                    + "\n\n⚠️ 이 지역에서 전세 계약 시:\n"
                    + "1. **등기부등본** 근저당 확인 필수\n"
                    + "2. **HUG 전세보증보험** 가입 강력 권장\n"
                    + "3. **계약 가이드** 탭에서 체크리스트 확인"
                )

        if any(k in msg for k in ["깡통", "전세사기", "사기"]):
            return (
                "**깡통전세**란 전세보증금이 매매가에 근접하거나 초과하는 상태를 말합니다.\n\n"
                "⚠️ 천안시 전세사기 현황: **288세대**, 피해액 **145억원**\n"
                "- 전세가율 80% 이상이면 위험, 100% 이상이면 '깡통'\n"
                "- **내 매물 체크** 탭에서 AI가 위험도를 진단해줍니다\n\n"
                "**예방 팁**: 등기부등본 확인, HUG 전세보증보험 가입, 공인중개사 통한 거래 → **계약 가이드** 탭 참고"
            )

        if any(k in msg for k in ["정책", "지원", "제도", "안심"]):
            return (
                "천안시 주거안전 관련 지원:\n\n"
                "1. **안심계약 도움서비스** — 전세 계약 시 전문가 동석 지원\n"
                "2. **HUG 전세보증보험** — 전세보증금 반환보증 (보증료 지원)\n"
                "3. **청년 월세 지원** — 무주택 청년 월 최대 20만원\n"
                "4. **전세사기 피해자 지원** — 긴급 주거·법률 상담·이주비\n\n"
                "문의: 천안시청 주거복지과 041-521-5252"
            )

        if any(k in msg for k in ["전세가율", "뜻", "의미", "설명"]):
            return (
                "**전세가율** = 전세보증금 ÷ 매매가 × 100%\n\n"
                "- **60% 이하**: 안전\n"
                "- **60~80%**: 주의\n"
                "- **80~90%**: 위험\n"
                "- **90% 이상**: 심각 위험\n"
                "- **100% 이상**: 깡통전세\n\n"
                "천안시 평균 전세가율은 약 77%입니다."
            )

        if any(k in msg for k in ["체크", "확인", "계약"]):
            return (
                "전세 계약 전 반드시 확인할 사항:\n\n"
                "1. 등기부등본 (근저당·가압류 확인)\n"
                "2. 임대인 본인 확인 (신분증 대조)\n"
                "3. 전세가율 확인 (80% 이하가 안전)\n"
                "4. HUG 전세보증보험 가입\n"
                "5. 전입신고 + 확정일자\n\n"
                "**계약 가이드** 탭에서 자세한 체크리스트를 확인하세요."
            )

        return (
            "안녕하세요! 천안시 주거안전 AI 상담입니다. 이런 질문을 해보세요:\n\n"
            "- **\"불당동 안전한가요?\"** — 동네 안전 분석\n"
            "- **\"안전한 동네 추천\"** — 안전점수 상위 동네\n"
            "- **\"안서동 5000만원 33㎡\"** — 매물 위험도 분석\n"
            "- **\"깡통전세가 뭐야?\"** — 개념 설명\n"
            "- **\"계약 전 뭐 확인해?\"** — 체크리스트\n"
            "- **\"주거 정책 알려줘\"** — 천안시 지원 제도\n"
        )

    # ── RAG 답변 wrapper — mock_llm_response와 동일한 인터페이스 유지 ──
    def rag_answer(user_msg: str) -> str:
        """RAG 챗봇 호출. 실패 시 rule-based mock으로 fallback."""
        try:
            rag = get_rag_module()
            df_safety, df_trends = load_chatbot_context()
            history = st.session_state.get("chat_messages", [])
            result = rag.answer(
                query=user_msg,
                df_safety=df_safety,
                df_trends=df_trends,
                history=history,
                dongnam_dongs=DONGNAM_DONGS,
            )
            # 8축 레이더 데이터를 세션에 저장 (기존 _render_chat_msg가 사용)
            if result.get("radar_data"):
                st.session_state["_chat_radar_data"] = result["radar_data"]

            # 툴 사용 배지 + 근거 문서 표시 (투명성)
            badges = []
            if "simulator" in result["tool_used"]:
                badges.append("🔧 LightGBM 시뮬레이터")
            if "dong_lookup" in result["tool_used"]:
                badges.append("📊 동네 조회")
            if "news" in result["tool_used"] or "news_search" in result["tool_used"]:
                badges.append("🔎 뉴스 검색")
            if "recommend" in result["tool_used"]:
                badges.append("🏠 안전매물 추천")
            if result["llm"] == "local":
                llm_badge = "🤖 천안세이프 LLM (자체 파인튜닝 7B)"
            elif result["llm"] == "openai":
                llm_badge = "🤖 천안세이프 AI (클라우드 백업 엔진)"
            else:
                llm_badge = "⚙️ Rule-based (LLM 미연결)"
            badges.append(llm_badge)

            text = result["text"]

            # 뉴스가 있으면 본문 아래에 출처 링크 나열 (LLM 답변에도, fallback에도 공통 적용)
            news_items = result.get("news") or []
            if news_items and "📰" not in text:
                text += "\n\n**📰 참고한 최근 뉴스**\n"
                for i, n in enumerate(news_items[:4], 1):
                    title = (n.get("title") or "").strip()
                    link = (n.get("link") or "").strip()
                    src = n.get("source", "")
                    pub = (n.get("pubDate") or "").strip()[:16]
                    if link:
                        text += f"{i}. [{title}]({link}) — *{src}* {pub}\n"
                    else:
                        text += f"{i}. {title} — *{src}* {pub}\n"

            # ⚠ Fallback 사용 시 상단에 눈에 띄는 경고
            if result["llm"] not in ("local", "openai"):
                text = (
                    "> ⚠️ **LLM이 응답하지 않아 rule-based 응답으로 대체되었습니다.** "
                    "챗봇 상단 '🔧 LLM 연결 진단' 버튼으로 원인을 확인하세요.\n\n"
                ) + text

            if result.get("radar_data"):
                text += "\n\n---RADAR---"

            # 하단에 근거 표시
            refs = []
            for d in result.get("retrieved", [])[:2]:
                if d.get("score", 0) > 0.35:  # 임계값 이상만
                    refs.append(f"📚 {d['title']}")
            footer_bits = []
            if badges:
                footer_bits.append(" · ".join(badges))
            if refs:
                footer_bits.append("근거: " + " / ".join(refs))
            if footer_bits:
                text += f"\n\n<sub style='opacity:0.7;'>{' | '.join(footer_bits)}</sub>"
            return text
        except Exception as e:
            # 최후 방어: 기존 rule-based로
            return mock_llm_response(user_msg)

    # 채팅 히스토리
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "안녕하세요! 천안시 주거안전 AI 상담입니다.\n\n동네 안전성, 매물 위험도, 계약 주의사항을 물어보세요.\n\n예시: *\"두정동 안전한가요?\"*, *\"5000만원으로 어디가 좋아?\"* — 아래 빠른질문 버튼으로 바로 체험할 수 있어요."}
        ]

    import re as _re
    def _fix_bold(t):
        # '**75.3%**이며'처럼 한글 인접 볼드가 리터럴 노출되는 것 방지 → 공백 삽입
        t = _re.sub(r"(?<=\S)\*\*(?=\S)", lambda m: "**", t)
        t = _re.sub(r"\*\*(\S[^*]*?\S)\*\*(?=[가-힣])", r"**\1** ", t)
        return t
    def _render_chat_msg(content):
        # 채팅 메시지 렌더 (RADAR 마커 있으면 Plotly 레이더도 표시)
        content = _fix_bold(content)
        if "---RADAR---" in content:
            text_part = content.replace("---RADAR---", "").strip()
            st.markdown(text_part, unsafe_allow_html=True)
            radar_data = st.session_state.get("_chat_radar_data")
            if radar_data:
                vals = radar_data["values"] + [radar_data["values"][0]]
                axes = radar_data["axes"] + [radar_data["axes"][0]]
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(
                    r=vals, theta=axes, fill="toself",
                    name=radar_data["dong"], line_color="#3498db",
                ))
                fig_r.update_layout(
                    polar=dict(bgcolor="rgba(46,134,230,0.05)",
                               radialaxis=dict(visible=True, range=[0, 1],
                                               gridcolor="rgba(46,134,230,0.18)",
                                               tickfont=dict(color="#55677F")),
                               angularaxis=dict(gridcolor="rgba(46,134,230,0.18)",
                                                tickfont=dict(color="#16233A"))),
                    height=280, margin=dict(t=30, b=20, l=40, r=40),
                    showlegend=False,
                )
                st.plotly_chart(fig_r, use_container_width=True)
        else:
            st.markdown(content, unsafe_allow_html=True)

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_chat_msg(msg["content"])
            else:
                st.markdown(msg["content"])

    if user_input := st.chat_input("궁금한 점을 물어보세요..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("검색·추론 중..."):
                response = rag_answer(user_input)
            _render_chat_msg(response)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

    st.divider()
    st.markdown("**빠른 질문:**")
    quick_cols = st.columns(3)
    quick_questions = [
        "안전한 동네 추천", "위험 지역 알려줘", "깡통전세가 뭐야?",
        "불당동 안전한가요?", "안서동 5000만원 33㎡ 분석해줘", "구도심 vs 신도심 격차",
        "원성동 3000만원 20㎡ 1990년", "천안아산역 통근하면 어디 살까?", "계약 전 뭐 확인해?",
    ]
    for i, q in enumerate(quick_questions):
        with quick_cols[i % 3]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": q})
                response = rag_answer(q)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()


# ═══════════════════════════════════════════
# 탭 6: 데이터 더보기 (기존 대시보드+추세+이상탐지 통합)
# ═══════════════════════════════════════════
with tab6:
    chapter_divider("06", "데이터 분석 상세")
    st.caption("이 서비스의 기반이 되는 데이터 분석 결과입니다")

    df_safety = load_safety_scores()
    df_rate = load_jeonse_rate()

    # 상단 요약 — 히어로 타일 1 + 보조 4 (시각 위계)
    n_danger = len(df_safety[df_safety['신호등']=='빨강'])
    n_caution = len(df_safety[df_safety['신호등']=='노랑'])
    n_safe = len(df_safety[df_safety['신호등']=='초록'])
    _hero_col, _rest = st.columns([1.6, 3])
    with _hero_col:
        st.markdown(f"""
<div style="border:1px solid rgba(239,68,68,0.45);border-radius:16px;padding:18px 20px;
            background:linear-gradient(135deg,rgba(239,68,68,0.14),rgba(245,158,11,0.10));">
  <div style="font-size:0.8rem;color:#C2414F;font-weight:700;letter-spacing:0.06em;">신호등 분포 · 65개 동</div>
  <div style="font-size:2.3rem;font-weight:800;color:#16233A;line-height:1.1;margin-top:4px;">
    🔴 {n_danger} <span style="color:#F59E0B;">🟡 {n_caution}</span> <span style="color:#10B981;">🟢 {n_safe}</span></div>
  <div style="font-size:0.82rem;color:#55677F;margin-top:6px;">위험 1곳 = 원성동 (구도심) — 지역균형발전 과제의 지도적 근거</div>
</div>""", unsafe_allow_html=True)
    with _rest:
        col2, col3, col5 = st.columns(3)
        col2.metric("평균 안전점수", f"{df_safety['종합안전점수'].mean():.1f}")
        col3.metric("평균 전세가율", f"{df_safety['전세가율_평균'].mean():.0%}")
        col5.metric("전세 거래 수", f"{int(df_safety['전세거래수'].sum()):,}")
        st.caption("ⓘ 거래 수는 안전점수 산출용 최근 전세 계약 기준 — 히어로의 102,671건은 매매 포함 전체 매칭 실거래")

    # 구도심 vs 신도심 격차 요약
    _dn = df_safety[df_safety["법정동명"].apply(lambda x: x in DONGNAM_DONGS or any(k in x for k in ["목천","병천","북면","풍세","성남"]))]
    _sb = df_safety[~df_safety.index.isin(_dn.index)]
    if len(_dn) > 0 and len(_sb) > 0:
        gap = _sb["종합안전점수"].mean() - _dn["종합안전점수"].mean()
        if gap > 2:
            st.caption(f"📍 구도심(동남구) 평균 {_dn['종합안전점수'].mean():.1f}점 vs 신도심(서북구) 평균 {_sb['종합안전점수'].mean():.1f}점 — 격차 {gap:.1f}점")

    # ── 섹션 1: 동별 안전 랭킹 ──
    st.divider()
    st.subheader("동별 안전 랭킹")
    color_map = {"빨강": "#e74c3c", "노랑": "#f39c12", "초록": "#27ae60"}

    _top10 = df_safety.nlargest(10, "종합안전점수")
    _bot10 = df_safety.nsmallest(10, "종합안전점수")
    df_plot = pd.concat([_bot10, _top10]).sort_values("종합안전점수", ascending=True)
    fig1 = px.bar(
        df_plot, x="종합안전점수", y="법정동명",
        orientation="h", color="신호등", color_discrete_map=color_map,
        title="안전 Top 10 · 취약 Bottom 10 (전체 65개는 아래 펼침)",
    )
    fig1.update_layout(
        height=560, showlegend=True,
        yaxis=dict(dtick=1, tickfont=dict(size=13), title=None),
        xaxis=dict(title="종합안전점수", range=[0, 105]),
    )
    st.plotly_chart(fig1, use_container_width=True)
    with st.expander(f"전체 {len(df_safety)}개 동 랭킹 보기"):
        _all = df_safety.sort_values("종합안전점수", ascending=True)
        _figall = px.bar(_all, x="종합안전점수", y="법정동명", orientation="h",
                         color="신호등", color_discrete_map=color_map)
        _figall.update_layout(height=max(500, len(_all) * 20), showlegend=False,
                              yaxis=dict(dtick=1, tickfont=dict(size=11), title=None))
        st.plotly_chart(_figall, use_container_width=True)

    ranking = df_safety[["법정동명", "종합안전점수", "신호등", "전세가율_평균", "전세거래수",
                          "금융안전_점수", "건물노후_점수"]].copy()
    ranking["구"] = ranking["법정동명"].apply(
        lambda x: "동남구" if x in DONGNAM_DONGS or any(k in x for k in ["목천","병천","북면","풍세","성남"]) else "서북구"
    )
    ranking["전세거래수"] = ranking["전세거래수"].fillna(0).astype(int)
    ranking["전세가율_평균"] = (ranking["전세가율_평균"].fillna(0) * 100).round(1)
    ranking["금융안전_점수"] = (ranking["금융안전_점수"] * 100).round(0)
    ranking["건물노후_점수"] = (ranking["건물노후_점수"] * 100).round(0)
    ranking = ranking.sort_values("종합안전점수", ascending=False).reset_index(drop=True)
    ranking.index = ranking.index + 1
    ranking.index.name = "순위"

    ranking = ranking[["법정동명", "구", "종합안전점수", "신호등", "전세가율_평균", "전세거래수",
                        "금융안전_점수", "건물노후_점수"]]
    st.dataframe(
        ranking, use_container_width=True, height=400,
        column_config={
            "종합안전점수": st.column_config.ProgressColumn("안전점수", min_value=0, max_value=100, format="%.1f"),
            "전세가율_평균": st.column_config.NumberColumn("전세가율", format="%.1f%%"),
            "전세거래수": st.column_config.NumberColumn("거래수", format="%d"),
            "금융안전_점수": st.column_config.ProgressColumn("금융안전", min_value=0, max_value=100, format="%.0f"),
            "건물노후_점수": st.column_config.ProgressColumn("건물안전", min_value=0, max_value=100, format="%.0f"),
        },
    )

    # ── 섹션 2: 전세가율 분포 ──
    with st.expander("전세가율 분포 분석", expanded=False):
        fig2 = px.histogram(
            df_rate, x="전세가율", nbins=50,
            title="천안시 전세가율 분포",
            labels={"전세가율": "전세가율", "count": "거래 수"},
            color_discrete_sequence=["#3498db"],
        )
        fig2.add_vline(x=0.80, line_dash="dash", line_color="orange", annotation_text="위험선 80%")
        fig2.add_vline(x=0.90, line_dash="dash", line_color="red", annotation_text="깡통선 90%")
        fig2.add_vline(x=1.00, line_dash="dash", line_color="darkred", annotation_text="역전세 100%")
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

        df_safety["전세거래수"] = df_safety["전세거래수"].fillna(0)
        fig3 = px.scatter(
            df_safety, x="금융안전_점수", y="건물노후_점수",
            size="전세거래수", color="신호등", color_discrete_map=color_map,
            hover_name="법정동명",
            title="동별 금융안전 vs 건물노후 (원 크기=거래수)",
        )
        fig3.add_annotation(x=0.3, y=0.3, text="⚠️ 이중 위험 구간",
                            showarrow=False, font=dict(size=11, color="#e74c3c"),
                            bgcolor="rgba(231,76,60,0.1)", borderpad=4)
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

    # ── 섹션 3: 추세 분석 ──
    with st.expander("전세가율 추세 분석", expanded=False):
        try:
            @st.cache_data
            def load_trends():
                monthly = pd.read_parquet(PROCESSED_DIR / "dong_jeonse_monthly.parquet")
                trends = pd.read_parquet(PROCESSED_DIR / "dong_jeonse_trends.parquet")
                return monthly, trends

            monthly_ts, dong_trends = load_trends()

            # 위험 경보
            st.markdown("**🚨 위험 경보 — 전세가율 80%+ & 상승 추세**")
            alerts = dong_trends[
                (dong_trends["최근_전세가율"] >= 0.80) & (dong_trends["6개월_추세"] > 0)
            ].sort_values("6개월_추세", ascending=False)

            if len(alerts) > 0:
                alert_cols = st.columns(min(len(alerts), 4))
                for i, (_, row) in enumerate(alerts.head(4).iterrows()):
                    with alert_cols[i]:
                        rate_val = row['최근_전세가율']
                        trend_val = row['6개월_추세']
                        border_color = "#e74c3c" if rate_val >= 0.90 else "#f39c12"
                        text_color = "#ef4444" if rate_val >= 0.90 else "#f59e0b"
                        st.markdown(
                            f"""<div style="border:2px solid {border_color};
                            padding:0.8rem; border-radius:8px;">
                            <div style="font-size:0.85rem; opacity:0.7;">{row['법정동명']}</div>
                            <div style="font-size:1.5rem; font-weight:bold; color:{text_color};">{rate_val:.0%}</div>
                            <div style="font-size:0.85rem; color:{text_color};">▲ {trend_val:+.1%} (6M)</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
            else:
                st.success("현재 위험 상승 경보 없음")

            # 추세 차트
            col_trend_l, col_trend_r = st.columns(2)
            with col_trend_l:
                trend_summary = dong_trends["추세_판정"].value_counts().reset_index()
                trend_summary.columns = ["추세", "동 수"]
                color_map_trend = {"급상승": "#e74c3c", "상승": "#f39c12", "정체": "#95a5a6",
                                   "하락": "#3498db", "급하락": "#2c3e50"}
                fig_trend = px.bar(trend_summary, x="추세", y="동 수",
                                   color="추세", color_discrete_map=color_map_trend,
                                   title="전세가율 추세 분포")
                fig_trend.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_trend_r:
                top_bottom = pd.concat([
                    dong_trends.nlargest(5, "6개월_추세"),
                    dong_trends.nsmallest(5, "6개월_추세"),
                ])
                fig_tb = px.bar(
                    top_bottom.sort_values("6개월_추세"),
                    x="6개월_추세", y="법정동명", orientation="h",
                    color="6개월_추세", color_continuous_scale="RdYlGn_r",
                    title="6개월 변동 상위/하위 5",
                )
                fig_tb.update_layout(height=350, yaxis=dict(dtick=1))
                st.plotly_chart(fig_tb, use_container_width=True)

            # 시계열
            selected_dongs = st.multiselect(
                "동별 시계열 비교 (최대 5개)",
                dong_trends["법정동명"].tolist(),
                default=["두정동", "불당동", "원성동"] if all(d in dong_trends["법정동명"].values for d in ["두정동", "불당동", "원성동"]) else dong_trends["법정동명"].head(3).tolist(),
                max_selections=5, key="trend_ts_dong",
            )
            if selected_dongs:
                ts_data = monthly_ts[monthly_ts["법정동명"].isin(selected_dongs)].copy()
                fig_ts = px.line(ts_data, x="연월", y="전세가율_평균", color="법정동명",
                                 title="월별 전세가율 추이")
                fig_ts.add_hline(y=0.80, line_dash="dash", line_color="orange", annotation_text="위험선 80%")
                fig_ts.add_hline(y=1.00, line_dash="dash", line_color="red", annotation_text="깡통 100%")
                fig_ts.update_layout(height=400, yaxis_tickformat=".0%")
                st.plotly_chart(fig_ts, use_container_width=True)

        except FileNotFoundError:
            st.warning("시계열 데이터가 없습니다.")

    # ── 섹션 4: 이상거래 탐지 ──
    with st.expander("이상거래 탐지 (Isolation Forest)", expanded=False):
        try:
            @st.cache_data
            def load_anomaly():
                anom = pd.read_parquet(PROCESSED_DIR / "anomaly_results.parquet")
                dong_anom = pd.read_parquet(PROCESSED_DIR / "dong_anomaly_rate.parquet")
                return anom, dong_anom

            df_anom, dong_anom_rate = load_anomaly()

            total = len(df_anom)
            n_anom = df_anom["이상"].sum()
            gangton = len(df_anom[(df_anom["이상"]) & (df_anom["전세가율"] >= 1.0)])

            anom_cols = st.columns(4)
            anom_cols[0].metric("총 거래", f"{total:,}")
            anom_cols[1].metric("이상 거래", f"{n_anom:,}", f"{n_anom/total:.1%}")
            anom_cols[2].metric("깡통 후보", f"{gangton:,}")
            anom_cols[3].metric("이상 평균 보증금", f"{df_anom[df_anom['이상']]['보증금_만원'].mean():,.0f}만")

            col_l, col_r = st.columns(2)
            with col_l:
                top_dongs = dong_anom_rate.head(15)
                fig_anom = px.bar(
                    top_dongs, x="이상비율", y="법정동명", orientation="h",
                    color="이상비율", color_continuous_scale="Reds",
                    title="이상 거래 집중 동 (상위 15)",
                    text=top_dongs.apply(lambda r: f"{r['이상거래']:.0f}/{r['총거래']:.0f}", axis=1),
                )
                fig_anom.update_layout(height=450, yaxis=dict(autorange="reversed", dtick=1))
                st.plotly_chart(fig_anom, use_container_width=True)

            with col_r:
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=df_anom[~df_anom["이상"]]["전세가율"], name="정상", opacity=0.7,
                    marker_color="#3498db", nbinsx=50))
                fig_dist.add_trace(go.Histogram(
                    x=df_anom[df_anom["이상"]]["전세가율"], name="이상", opacity=0.7,
                    marker_color="#e74c3c", nbinsx=50))
                fig_dist.update_layout(barmode="overlay", height=450,
                                       xaxis_title="전세가율", yaxis_title="거래 수",
                                       xaxis_tickformat=".0%")
                st.plotly_chart(fig_dist, use_container_width=True)

            st.markdown("**이상 거래 상세 (이상점수 하위 20건)**")
            worst = df_anom[df_anom["이상"]].nsmallest(20, "이상점수")
            display_cols = ["법정동명", "단지명", "전세가율", "보증금_만원", "전용면적_㎡", "이상점수"]
            avail_cols = [c for c in display_cols if c in worst.columns]
            st.dataframe(
                worst[avail_cols].reset_index(drop=True), use_container_width=True,
                column_config={
                    "전세가율": st.column_config.NumberColumn(format=".0%"),
                    "보증금_만원": st.column_config.NumberColumn(format="%d만원"),
                    "이상점수": st.column_config.NumberColumn(format="%.3f"),
                },
            )

        except FileNotFoundError:
            st.warning("이상탐지 데이터가 없습니다.")

    # ── 섹션 5: 연도별 추이 ──
    with st.expander("연도별 전세가율 추이", expanded=False):
        df_rate_ts = df_rate.copy()
        df_rate_ts["연도"] = df_rate_ts["연월"].astype(str).str[:4].astype(int)
        yearly = df_rate_ts.groupby("연도")["전세가율"].agg(["mean", "median", "count"]).reset_index()
        yearly.columns = ["연도", "평균", "중앙값", "거래수"]

        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=yearly["연도"], y=yearly["평균"], mode="lines+markers", name="평균 전세가율"))
        fig4.add_trace(go.Scatter(x=yearly["연도"], y=yearly["중앙값"], mode="lines+markers", name="중앙값 전세가율"))
        fig4.add_hline(y=0.80, line_dash="dash", line_color="orange", annotation_text="위험선")
        fig4.update_layout(height=300, yaxis_title="전세가율", xaxis_title="연도", yaxis_tickformat=".0%")
        st.plotly_chart(fig4, use_container_width=True)


# ─── AI 모델 & 데이터 출처 (대회 심사용) ───
with st.expander("🤖 AI 모델 아키텍처 & 데이터 출처", expanded=False):
    st.markdown("### AI 모델 파이프라인")
    st.markdown("""
**1. 깡통전세 위험도 분류기 (LightGBM)**
- **문제 정의**: 전세 거래의 깡통전세 여부를 이진 분류
- **라벨링**: 공공데이터에 정답 라벨 없음 → **PU러닝 (Positive-Unlabeled Learning)** 기법으로 휴리스틱 약지도 학습
  - Positive 기준: 전세가율 ≥ 80% AND (보증금 > 공시가×1.26 OR 건물연령 > 30년)
- **피처**: 보증금, 전용면적, 건물연령, 동별 평균보증금, 동별 노후비율 등 **30개** 피처 (건축물대장 연계)
- **성능**: AUC **0.989**, F1 **0.969** (5-fold Stratified CV)
- **해석**: SHAP (SHapley Additive exPlanations)으로 개별 예측 설명

**2. 8축 종합 안전점수**
- 금융안전(0.25), 건물노후(0.15), 침수위험(0.10), 치안(0.15), 소방(0.05), 교통(0.10), 편의시설(0.10), 환경(0.10)
- 각 축 0~1 정규화 후 가중합 × 100 = 종합점수
- SGIS 인구·사업체 통계로 치안·편의 축 실데이터 연계

**3. 이상거래 탐지 (Isolation Forest)**
- 전체 102,671건 중 5,134건 이상 탐지 (5.0%)
- 깡통 후보(전세가율 ≥ 100%): 1,129건
- 동별 이상 비율 산출 → 금융안전 점수에 반영
""")

    st.markdown("### 데이터 출처 (100% 공공데이터)")
    data_sources = pd.DataFrame({
        "데이터": ["아파트 전월세 실거래가", "아파트 매매 실거래가", "건축물대장 기본개요",
                  "SGIS 인구통계", "SGIS 사업체통계", "공시가격"],
        "출처": ["국토교통부 실거래가 API", "국토교통부 실거래가 API", "국토교통부 건축물대장 API",
                "통계청 SGIS API", "통계청 SGIS API", "국토교통부 공시가격 API"],
        "수집 시점": ["2018~2025", "2018~2025", "2025.06", "2024", "2024", "2024~2025"],
        "주요 컬럼": ["보증금, 전용면적, 법정동, 계약연월", "거래금액, 전용면적, 법정동",
                    "건축년도, 구조, 용도, 세대수, 면적", "인구수, 가구수, 인구밀도",
                    "사업체수, 종사자수", "공시가격(㎡당)"],
        "URL": ["https://www.data.go.kr/data/15058747", "https://www.data.go.kr/data/15058017",
                "https://www.data.go.kr/data/15044713", "https://sgis.kostat.go.kr",
                "https://sgis.kostat.go.kr", "https://www.data.go.kr/data/15126674"],
    })
    st.dataframe(data_sources, use_container_width=True, hide_index=True)

    st.caption("※ 모든 데이터는 공공데이터포털 또는 통계청 API를 통해 합법적으로 수집하였으며, 민간 크롤링 데이터는 일절 사용하지 않았습니다.")


# ─── Footer ───
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.85rem; padding: 0.5rem 0;">
    <b>천안 청년 자취방 안전지도</b> | 2026 천안시 AI·데이터 기반 정책 아이디어 경진대회<br>
    📊 데이터 출처: 국토교통부 실거래가 API · 건축물대장 API · SGIS 통계지리정보 | 100% 공공데이터 기반<br>
    <span style="font-size: 0.75rem; color: #888;">
        최종 데이터 업데이트: 2025.06 | 이 서비스는 참고용이며, 실제 계약 시 반드시 전문가 상담을 받으세요.
    </span>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# 탭: 매물 탐색 — 직방 스타일 카드 + AI 신호등 + 외부 플랫폼 연결
# ═══════════════════════════════════════════
with tab_listing:
    from scripts import listings as _lst

    from scripts.brand_assets import mascot_uri as _lst_mascot
    _lm = _lst_mascot("안내")
    st.markdown(
        f"""
<div style="background:linear-gradient(95deg,#2E86E6,#4A9BF0);border-radius:14px;
            padding:18px 22px;margin-bottom:14px;position:relative;">
  {f'<img src="{_lm}" style="position:absolute;right:18px;bottom:0;height:76px;"/>' if _lm else ''}
  <div style="color:#fff;font-size:1.25rem;font-weight:700;">🏠 매물 탐색 — 모든 카드에 AI 신호등</div>
  <div style="color:rgba(255,255,255,0.88);font-size:0.86rem;margin-top:4px;">
    국토부 실거래 102,671건 전수를 4-모델 앙상블이 사전 스코어링 · 실거래만 표시 = <b style="color:#BBF7D0;">허위매물 0%</b>
    · 현재 매물 확인은 카드의 외부 링크에서 (민간 데이터 미수집)</div>
</div>""",
        unsafe_allow_html=True,
    )

    @st.cache_data(show_spinner="단지 프로필 집계 중...")
    def _load_profiles():
        return _lst.load_complex_profiles()

    @st.cache_data(show_spinner=False)
    def _diagnose_cached(dong, deposit, area, year, dongnam):
        return _lst.diagnose(dong, deposit, area, year, dongnam)

    @st.cache_data(show_spinner=False)
    def _load_history(dong: str, complex_name: str):
        base = pd.read_parquet("data/processed/recommend_base.parquet")
        h = base[(base["법정동명"] == dong) & (base["단지명"] == complex_name)]
        h = h.sort_values("거래일", ascending=False).head(10)
        out = pd.DataFrame({
            "거래일": h["거래일"].dt.strftime("%Y-%m-%d"),
            "보증금(만원)": h["보증금_만원"].map("{:,.0f}".format),
            "면적(㎡)": h["전용면적_㎡"].round(1),
            "전세가율": h["전세가율"].map(lambda v: f"{v:.0%}" if pd.notna(v) else "—"),
            "AI 위험확률": h["앙상블_위험확률"].map("{:.0%}".format),
        })
        return out.reset_index(drop=True)

    prof = _load_profiles()

    # ── 천안 특화: 대학가 원클릭 프리셋 (12개 대학 도시) ──
    UNIV_PRESETS = {
        "🎓 단국대·상명대·백석대": ("안서동",),
        "🎓 공주대 천안캠": ("부대동",),
        "🎓 한기대": ("병천면",),
        "🎓 나사렛대": ("쌍용동",),
        "🎓 남서울대": ("성환읍",),
        "🚄 KTX 천안아산역": ("불당동", "백석동"),
        "🚇 1호선 두정·성환": ("두정동", "성정동", "성환읍"),
    }
    if "lst_univ" not in st.session_state:
        st.session_state["lst_univ"] = None
    st.caption("🎯 대학가·통근 원클릭 필터 — 버튼을 누르면 해당 생활권 매물만 표시")
    uc = st.columns(len(UNIV_PRESETS))
    for _i, (_label, _prefix) in enumerate(UNIV_PRESETS.items()):
        with uc[_i]:
            _active = st.session_state["lst_univ"] == _prefix
            if st.button(("✓ " if _active else "") + _label, key=f"univ_{_i}", use_container_width=True):
                st.session_state["lst_univ"] = None if _active else _prefix
                st.rerun()

    # ── 필터 바 ──
    f1, f2, f3, f4 = st.columns([1.5, 1.0, 1.6, 1.0])
    with f1:
        kw = st.text_input("단지·동네 검색", placeholder="예: 불당, 두정 코아루", key="lst_kw")
    with f2:
        dong_sel = st.selectbox("법정동", ["전체"] + sorted(prof["법정동명"].unique().tolist()), key="lst_dong")
    with f3:
        sig_sel = st.multiselect("신호등", ["초록", "노랑", "주황", "빨강"], default=["초록", "노랑", "주황", "빨강"], key="lst_sig")
    with f4:
        sort_sel = st.selectbox("정렬", ["AI 안전순", "AI 위험순", "최신 거래순", "보증금 낮은순"], key="lst_sort")

    g1, g2, g3 = st.columns(3)
    with g1:
        dep_rng = st.slider("보증금 (만원)", 0, 40000, (0, 20000), step=500, key="lst_dep")
    with g2:
        area_rng = st.slider("전용면적 (㎡)", 0, 150, (0, 100), step=5, key="lst_area")
    with g3:
        year_min = st.slider("준공년도 이후", 1980, 2026, 1990, step=1, key="lst_year")
        recent_only = st.checkbox("최근 3년 실거래만 (신뢰도↑)", value=True, key="lst_recent")

    q = prof[
        prof["신호등"].isin(sig_sel)
        & prof["최근보증금"].between(*dep_rng)
        & prof["최근면적"].between(*area_rng)
        & (prof["건축년도"].fillna(2000) >= year_min)
    ]
    if st.session_state.get("lst_univ"):
        _prefixes = st.session_state["lst_univ"]
        if isinstance(_prefixes, str):
            _prefixes = (_prefixes,)
        q = q[q["법정동명"].str.startswith(tuple(_prefixes))]
        st.info(f"📍 프리셋 필터 적용 중: {' · '.join(_prefixes)} — 같은 버튼을 다시 누르면 해제됩니다.")
    if dong_sel != "전체":
        q = q[q["법정동명"] == dong_sel]
    if kw.strip():
        terms = kw.split()
        for t in terms:
            q = q[q["단지명"].str.contains(t, na=False) | q["법정동명"].str.contains(t, na=False)]

    sort_map = {
        "AI 안전순": ("최근위험확률", True),
        "AI 위험순": ("최근위험확률", False),
        "최신 거래순": ("최근거래일", False),
        "보증금 낮은순": ("최근보증금", True),
    }
    if recent_only:
        _cutoff = q["최근거래일"].max() - pd.DateOffset(years=3)
        q = q[q["최근거래일"] >= _cutoff]
    col_s, asc = sort_map[sort_sel]
    if sort_sel == "AI 안전순":
        # 동률(0%대) 안에서는 최근·다거래 단지 우선 — 오래된 소표본이 1위로 오지 않게
        q = q.sort_values(["최근위험확률", "최근거래일", "거래수"], ascending=[True, False, False])
    else:
        q = q.sort_values(col_s, ascending=asc)

    n_g = int((q["신호등"] == "초록").sum()); n_y = int((q["신호등"] == "노랑").sum())
    n_o = int((q["신호등"] == "주황").sum()); n_r = int((q["신호등"] == "빨강").sum())
    st.markdown(
        f"**{len(q):,}개 단지** · 🟢 안전 {n_g:,} 🟡 주의 {n_y:,} 🟠 위험 {n_o:,} 🔴 심각 {n_r:,} "
        f"<span style='color:#94A3B8;font-size:0.85rem;'>— %는 절대 위험확률, 등급은 천안 전체 단지 내 상대 분위(심각=상위 10%)</span>",
        unsafe_allow_html=True,
    )

    # ── 카드 그리드 + 상세 ──
    if "lst_show" not in st.session_state:
        st.session_state["lst_show"] = 12
    show_n = st.session_state["lst_show"]
    page = q.head(show_n)

    if len(page) == 0:
        st.info("조건에 맞는 단지가 없습니다. 필터를 넓혀보세요.")
    cols = st.columns(3)
    for i, (_, row) in enumerate(page.iterrows()):
        with cols[i % 3]:
            st.markdown(_lst.card_html(row), unsafe_allow_html=True)
            with st.expander("📋 거래 이력 · AI 정밀 진단"):
                hist = _load_history(row["법정동명"], row["단지명"])
                st.dataframe(hist, use_container_width=True, height=180)
                d = _diagnose_cached(row["법정동명"], float(row["최근보증금"]),
                                     float(row["최근면적"]), int(row["건축년도"] or 2010),
                                     int(row["동남구"]))
                if d:
                    icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}[d["signal"]]
                    st.markdown(f"{icon} **LightGBM 정밀 진단: {d['signal_label']} {d['risk_prob']:.1%}**"
                                + (f" · 동네 안전점수 {d['safety_score']:.0f}/100" if d.get("safety_score") else ""))
                    for s in d["shap"]:
                        arrow = "🔺 위험↑" if s["value"] > 0 else "🔽 위험↓"
                        st.caption(f"{arrow} {s['name']} ({s['value']:+.2f})")

    if len(q) > show_n:
        if st.button(f"더 보기 ({show_n:,} / {len(q):,})", use_container_width=True, key="lst_more"):
            st.session_state["lst_show"] += 12
            st.rerun()

    st.caption("ⓘ 카드 정보는 국토부 실거래 공공데이터 기반 '단지 프로필'입니다. 현재 나와있는 매물·호가는 "
               "외부 링크(네이버부동산·다방)에서 확인하세요 — 본 서비스는 민간 플랫폼 데이터를 수집·저장하지 않습니다.")
