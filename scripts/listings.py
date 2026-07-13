#!/usr/bin/env python3
"""
매물 탐색 — 실거래 기반 단지 프로필 + AI 위험 스코어 + 외부 플랫폼 아웃링크

원칙
────
- 매물 원천은 국토부 실거래(recommend_base.parquet, 102,671건)만 사용 → 허위매물 구조적 0%
- 카드의 위험확률 = exp_006 4-모델 앙상블이 전수 사전 스코어링한 값
- 외부 플랫폼(네이버부동산·다방)은 '키워드 검색 아웃링크'만 — 데이터 수집 0바이트 (대회 규정 준수)
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"

SIGNAL_COLOR = {"빨강": "#DC2626", "주황": "#F97316", "노랑": "#F59E0B", "초록": "#10B981"}
SIGNAL_BG = {"빨강": "#FEF2F2", "주황": "#FFF7ED", "노랑": "#FFFBEB", "초록": "#ECFDF5"}
SIGNAL_LABEL = {"빨강": "심각", "주황": "위험", "노랑": "주의", "초록": "안전"}


def risk_signal(p: float) -> str:
    """4단계 신호 — 빨강 일색(양치기) 방지를 위해 위험 구간을 세분화."""
    if p >= 0.9:
        return "빨강"
    if p >= 0.7:
        return "주황"
    if p >= 0.3:
        return "노랑"
    return "초록"


def make_links(dong: str, complex_name: str,
               coords: tuple[float, float] | None = None) -> dict[str, str]:
    """민간 플랫폼 아웃링크 (데이터 미수집) — 2026-07-13 실브라우저 검증 체계.

    - 네이버: 통합검색 '{단지명} 전세 매물' — 최상단에 네이버부동산 해당 단지 매물 블록 착지
      (구 m.land/new.land 키워드 라우트는 fin.land 개편으로 404 확인되어 폐기)
    - 다방: 키워드 딥링크 미지원 → 동네 좌표 지도 진입 (해당 동 매물 즉시 노출)
    """
    q_naver = urllib.parse.quote(f"천안 {complex_name} 전세 매물")
    q_map = urllib.parse.quote(f"천안 {dong} {complex_name}")
    if coords:
        dabang = (f"https://www.dabangapp.com/map/onetwo"
                  f"?m_lat={coords[0]:.4f}&m_lng={coords[1]:.4f}&m_zoom=16")
    else:
        dabang = "https://www.dabangapp.com/map/onetwo"
    return {
        "네이버부동산": f"https://search.naver.com/search.naver?query={q_naver}",
        "다방": dabang,
        "지도": f"https://map.naver.com/p/search/{q_map}",
        "국토부 실거래": "https://rt.molit.go.kr/",
    }


def load_complex_profiles() -> pd.DataFrame:
    """단지(법정동, 단지명) 단위 프로필 집계 — 카드 그리드의 원천."""
    base = pd.read_parquet(PROCESSED / "recommend_base.parquet")
    base = base.dropna(subset=["단지명", "법정동명", "앙상블_위험확률"])
    base = base[base["단지명"].astype(str).str.strip().ne("")]

    base = base.sort_values("거래일")
    g = base.groupby(["법정동명", "단지명"])
    prof = g.agg(
        거래수=("보증금_만원", "size"),
        최근거래일=("거래일", "last"),
        최근보증금=("보증금_만원", "last"),
        최근면적=("전용면적_㎡", "last"),
        면적min=("전용면적_㎡", "min"),
        면적max=("전용면적_㎡", "max"),
        건축년도=("건축년도", "last"),
        위험확률=("앙상블_위험확률", "mean"),
        최근위험확률=("앙상블_위험확률", "last"),
        전세가율=("전세가율", "median"),
        동남구=("동남구", "max"),
    ).reset_index()

    # 등급 = 천안 전체 단지 내 상대 분위 (심각 일색 '양치기' 방지) — %는 절대값 그대로 표시
    _pct = prof["최근위험확률"].rank(pct=True)
    prof["신호등"] = pd.cut(_pct, bins=[0, 0.30, 0.70, 0.90, 1.0],
                             labels=["초록", "노랑", "주황", "빨강"], include_lowest=True).astype(str)
    # 규정 일관성: 전세가율 80%+(위험선 초과) 단지는 '안전' 표기 금지 → 최소 '주의'
    _over = prof["전세가율"].fillna(0) >= 0.80
    prof.loc[_over & (prof["신호등"] == "초록"), "신호등"] = "노랑"
    prof["건물연령"] = 2026 - prof["건축년도"]
    from scripts.dong_coords import DONG_COORDS
    prof["_lat"] = prof["법정동명"].map(lambda d: DONG_COORDS.get(d, [None, None])[0])
    prof["_lng"] = prof["법정동명"].map(lambda d: DONG_COORDS.get(d, [None, None])[1])
    return prof


def reason_line(row: pd.Series) -> str:
    """카드용 1줄 근거 (규정·데이터 기반, 사전계산 값만 사용)."""
    bits = []
    if pd.notna(row["전세가율"]):
        r = row["전세가율"]
        if r >= 1.0:
            bits.append(f"전세가율 {r:.0%} — 깡통 구간")
        elif r >= 0.8:
            bits.append(f"전세가율 {r:.0%} — 규정상 위험 경계 초과")
        elif r <= 0.6:
            bits.append(f"전세가율 {r:.0%} — 안전 구간")
        else:
            bits.append(f"전세가율 {r:.0%} — 주의 구간")
    age = row["건물연령"]
    if pd.notna(age):
        if age <= 7:
            bits.append("신축급")
        elif age >= 25:
            bits.append(f"노후 {age:.0f}년")
    return " · ".join(bits) if bits else "실거래 기반 프로필"


def card_html(row: pd.Series) -> str:
    """직방 스타일 매물 카드 (design_template 팔레트)."""
    sig = row["신호등"]
    c, bg = SIGNAL_COLOR[sig], SIGNAL_BG[sig]
    p = row["최근위험확률"]
    _coords = (row["_lat"], row["_lng"]) if pd.notna(row.get("_lat")) else None
    links = make_links(row["법정동명"], row["단지명"], coords=_coords)
    gauge_w = max(4, min(100, p * 100))
    area_txt = (f"{row['면적min']:.0f}~{row['면적max']:.0f}㎡"
                if row["면적max"] - row["면적min"] > 1 else f"{row['최근면적']:.0f}㎡")
    year_txt = f"{row['건축년도']:.0f}년식" if pd.notna(row["건축년도"]) else ""
    date_txt = pd.to_datetime(row["최근거래일"]).strftime("%Y.%m")

    return f"""
<div style="border:1px solid #E2E8F0;border-left:4px solid {c};border-radius:14px;background:#fff;
            overflow:hidden;margin-bottom:14px;font-family:inherit;">
  <div style="background:{bg};padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-weight:700;color:{c};font-size:0.95rem;">● 위험확률 {('<1%' if p < 0.01 else f'{p:.0%}')} · {SIGNAL_LABEL[sig]}</span>
    <span style="color:#94A3B8;font-size:0.75rem;">앙상블 4모델 스코어</span>
  </div>
  <div style="padding:4px 14px 0 14px;">
    <div style="background:#F1F5F9;border-radius:6px;height:6px;">
      <div style="background:{c};width:{gauge_w:.0f}%;height:6px;border-radius:6px;"></div>
    </div>
  </div>
  <div style="padding:10px 14px 6px 14px;">
    <div style="font-weight:700;color:#0F172A;font-size:1.02rem;line-height:1.3;">{row['단지명']}</div>
    <div style="color:#475569;font-size:0.86rem;margin-top:2px;">{row['법정동명']} · {'동남구' if row['동남구']==1 else '서북구'}</div>
    <div style="color:#0F172A;font-size:0.95rem;margin-top:6px;">
      전세 <b>{row['최근보증금']:,.0f}만원</b>
      <span style="color:#94A3B8;font-size:0.8rem;">(최근 실거래 {date_txt})</span>
    </div>
    <div style="color:#475569;font-size:0.84rem;margin-top:2px;">{area_txt} · {year_txt} · 거래 {row['거래수']}건</div>
    <div style="color:#64748B;font-size:0.8rem;margin-top:6px;border-top:1px dashed #E2E8F0;padding-top:6px;">
      💡 {reason_line(row)}</div>
  </div>
  <div style="padding:8px 14px 12px 14px;display:flex;gap:6px;flex-wrap:wrap;">
    <a href="{links['네이버부동산']}" target="_blank" style="text-decoration:none;font-size:0.78rem;font-weight:600;
       color:#0F172A;border:1px solid #E2E8F0;border-radius:999px;padding:4px 10px;background:#F8FAFC;">네이버 매물검색 ↗</a>
    <a href="{links['다방']}" target="_blank" style="text-decoration:none;font-size:0.78rem;font-weight:600;
       color:#0F172A;border:1px solid #E2E8F0;border-radius:999px;padding:4px 10px;background:#F8FAFC;">다방 지도(동네) ↗</a>
    <a href="{links['지도']}" target="_blank" style="text-decoration:none;font-size:0.78rem;font-weight:600;
       color:#0F172A;border:1px solid #E2E8F0;border-radius:999px;padding:4px 10px;background:#F8FAFC;">지도 ↗</a>
  </div>
</div>"""


FEATURE_KO = {
    "보증금_만원": "보증금 수준", "보증금_log": "보증금 수준", "㎡당_보증금": "㎡당 보증금",
    "전용면적": "전용면적", "건물연령": "건물 연식", "동남구": "구도심(동남구) 여부",
    "동_평균보증금": "동네 평균 보증금", "동_거래건수": "동네 거래량",
    "보증금_동평균_비율": "동네 평균 대비 보증금", "보증금_구평균_비율": "구 평균 대비 보증금",
    "면적_구평균_비율": "구 평균 대비 면적", "연도별_동_위험도": "동네 과거 위험 이력",
    "거래연도": "거래 연도", "동_평균건물연령": "동네 평균 건물연령",
    "동_건물연령_std": "동네 건물연령 편차", "동_노후비율": "동네 노후건물 비율",
    "동_심각노후비율": "동네 심각노후 비율", "동_내진비율": "동네 내진설계 비율",
    "동_건물수": "동네 건물 수", "동_평균세대수": "동네 평균 세대수",
    "동_평균총면적": "동네 평균 연면적", "동_평균지상층": "동네 평균 층수",
    "동_철근콘크리트비율": "철근콘크리트 비율", "동_벽돌비율": "벽돌구조 비율",
    "동_목구조비율": "목구조 비율", "건물연령_동평균차": "동네 평균 대비 연식",
    "보증금_노후도_교차": "보증금×노후도 결합",
}

DONGNAM_KEYS = ["목천", "병천", "북면", "풍세", "성남", "수신", "동면", "광덕"]


def diagnose(dong: str, deposit: float, area: float, year: int, dongnam: int) -> dict | None:
    """단지 카드용 실시간 LightGBM+SHAP 정밀 진단."""
    from scripts.simulator import predict

    gu = "동남구" if dongnam == 1 or any(k in dong for k in DONGNAM_KEYS) else "서북구"
    try:
        res = predict(보증금_만원=float(deposit), 전용면적=float(area),
                      법정동명=dong, 건축년도=int(year), 구=gu)
    except Exception:
        return None
    return {
        "risk_prob": res["risk_prob"],
        "signal": res["signal"],
        "signal_label": res["signal_label"],
        "safety_score": res.get("safety_score"),
        "shap": [
            {"name": FEATURE_KO.get(x["feature"], x["feature"]),
             "value": float(x["shap_value"])}
            for x in res["shap_top5"][:4]
        ],
    }
