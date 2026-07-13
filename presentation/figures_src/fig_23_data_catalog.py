"""Figure 23 — 사용 데이터 카탈로그 (Tier1-A)
심사위원이 3초 안에 파악해야 할 메시지: 무엇을·어디서·얼마나 — 전량 공공데이터, 출처·기간·용도가 투명하다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

# (그룹, 액센트, [(데이터셋, 제공기관, 규모, 기간/시점, 핵심 필드, 용도)])
GROUPS = [
    ("실거래 (핵심)", "#0EA5E9", [
        ("전월세 실거래 4종\n(아파트·연립다세대·오피스텔·단독다가구)", "국토교통부\n공공데이터포털 API",
         "371,612건", "2019.01~2026.06", "보증금·면적·건축년도·층", "진단 대상 + 전세금"),
        ("매매 실거래 4종 (동일 유형)", "국토교통부\n공공데이터포털 API",
         "270,307건", "2019.01~2026.06", "거래금액·면적·층", "매매가 중앙값 → 라벨 전용"),
    ]),
    ("건축물·가격", "#8B5CF6", [
        ("건축물대장 표제부", "국토교통부 건축HUB API",
         "21,669동", "2026.06 시점", "사용승인일·구조·내진·세대수", "건물 노후 피처 12종"),
        ("공동주택가격·개별공시지가", "국토교통부 API",
         "수집 완료", "2026 공시", "공시가격", "HUG 126% 규칙 참조"),
    ]),
    ("행정·통계", "#10B981", [
        ("SGIS 통계 6종", "통계청 SGIS API",
         "31개 행정동", "최신 집계연도", "인구·가구·주택·사업체", "65개 법정동으로 매핑 → 안전점수 축"),
        ("침수흔적·CCTV·상가·병원약국·대기질", "행안부·심평원·환경공단 등 5개 API",
         "파이프라인 구축", "—", "위치·시설", "8축 확장 (로드맵)"),
    ]),
    ("파생 데이터 (자체 구축)", "#F59E0B", [
        ("전세가율 테이블", "자체 ETL (매매↔전세 매칭)",
         "27,348 단지·월", "2019~2026", "전세가율·매매가 중앙값", "규정 기반 라벨 생성"),
        ("동별 안전점수·위험확률·이상탐지", "자체 모델 (exp_004/006)",
         "65개 동 · 102,671건", "—", "8축 점수·앙상블 확률", "지도·추천·LLM 툴"),
    ]),
]

COLS = ["데이터셋", "제공기관", "규모", "기간·시점", "핵심 필드", "파이프라인 내 용도"]
COL_X = [0.35, 4.45, 7.05, 8.75, 10.75, 13.35]
COL_W = [4.0, 2.5, 1.6, 1.9, 2.5, 2.6]

fig, ax = plt.subplots(figsize=(16, 10.2), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 10.2); ax.axis("off")

ax.text(0.35, 9.8, "사용 데이터 카탈로그 — 전량 공공데이터 · 출처 명시",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.35, 9.36, "정식 공공 API만 사용 (민간 크롤링 0건) · 수집 스크립트 9종 공개 (collector/01~09)",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# 헤더
hy = 8.75
for cx, label in zip(COL_X, COLS):
    ax.text(cx, hy, label, fontsize=11, fontweight="bold", color=COLOR["ink600"])
ax.plot([0.3, 15.7], [hy - 0.18, hy - 0.18], color=COLOR["ink400"], linewidth=1.0)

y = hy - 0.45
for gname, accent, rows in GROUPS:
    # 그룹 밴드
    ax.add_patch(patches.Rectangle((0.3, y - 0.34), 0.12, 0.3, color=accent))
    ax.text(0.55, y - 0.19, gname, fontsize=12, fontweight="bold", color=COLOR["ink900"], va="center")
    y -= 0.46
    for row in rows:
        n_lines = max(len(str(c).split("\n")) for c in row)
        rh = 0.30 * n_lines + 0.20
        ax.add_patch(FancyBboxPatch((0.3, y - rh + 0.1), 15.4, rh - 0.04,
                                    boxstyle="round,pad=0.01,rounding_size=0.06",
                                    facecolor=COLOR["soft"], edgecolor=COLOR["line"],
                                    linewidth=0.7, zorder=1))
        for cx, cell, bold in zip(COL_X, row, [True, False, True, False, False, False]):
            for j, line in enumerate(str(cell).split("\n")):
                ax.text(cx, y - 0.12 - j * 0.29, line, fontsize=9.8,
                        color=COLOR["ink900"] if bold else COLOR["ink600"],
                        weight="semibold" if bold else "normal",
                        va="center", zorder=2)
        y -= rh + 0.06
    y -= 0.10

ax.text(8, 0.16, "모든 원본에 수집시점·범위·컬럼·출처 URL 기재 (대회 데이터 규정 준수) · 직방/다방 등 민간 플랫폼 데이터 미사용",
        ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

save(fig, "fig_Data_Catalog")
