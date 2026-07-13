"""Figure 30 — HUG 안심전세 vs 천안세이프 비교 (Tier3-H)
심사위원이 3초 안에 파악해야 할 메시지: 정부 앱과 경쟁이 아니라 보완 — '시세를 모르는 계약 전 순간'을 우리가 채운다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

ROWS = [
    ("진단 시점", "등기·시세 확인 가능한 매물", "계약 전 어떤 매물이든 (주소·시세 불필요)"),
    ("시세(매매가) 의존", "필요 — 공시가·시세 기반 산정", "불필요 — 관측 피처 27종으로 복원 (AUC 0.99)"),
    ("커버 범위", "조회한 '1채' 단위 진단", "도시 전체 65개 동 선제 스캔 + 개별 매물"),
    ("동 단위 선제 경보", "없음", "위험 경보 19개 동 · 이상거래 감시"),
    ("이유 설명", "등급·금액 중심", "SHAP 요인 설명 ('왜 위험한지')"),
    ("상담 방식", "메뉴형 조회", "자체 LLM 대화형 (진단·추천·뉴스·정책)"),
    ("운영 비용", "정부 운영", "온프레미스 GPU — 외부 API 비용 0원"),
]

fig, ax = plt.subplots(figsize=(16, 8.6), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 8.6); ax.axis("off")

ax.text(0.4, 8.2, "\"이미 정부 앱이 있잖아요?\" — HUG 안심전세와의 관계",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.4, 7.76, "경쟁이 아닌 보완 — HUG의 규정(126%·80%)을 그대로 쓰되, HUG가 못 보는 '계약 전·시세 불명' 구간을 채운다",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")

col_x = [0.4, 4.6, 10.2]
col_w = [4.0, 5.4, 5.4]
hy = 7.1
headers = ["", "HUG 안심전세 (정부)", "천안세이프 (본 서비스)"]
for cx, cw, h, c in zip(col_x, col_w, headers, [None, COLOR["ink600"], COLOR["safe"]]):
    if h:
        ax.add_patch(FancyBboxPatch((cx, hy - 0.15), cw - 0.2, 0.62,
                                    boxstyle="round,pad=0.02,rounding_size=0.14",
                                    facecolor=c, edgecolor="none"))
        ax.text(cx + (cw - 0.2) / 2, hy + 0.16, h, ha="center", va="center",
                fontsize=13.5, fontweight="bold", color="white")

y = hy - 0.55
row_h = 0.88
for i, (item, hug, ours) in enumerate(ROWS):
    yy = y - i * row_h
    if i % 2 == 0:
        ax.add_patch(patches.Rectangle((0.4, yy - row_h + 0.14), 15.2, row_h - 0.06,
                                       facecolor=COLOR["soft"], edgecolor="none", zorder=0))
    ax.text(col_x[0] + 0.15, yy - row_h / 2 + 0.12, item, fontsize=12,
            fontweight="bold", color=COLOR["ink900"], va="center", zorder=2)
    ax.text(col_x[1] + 0.15, yy - row_h / 2 + 0.12, hug, fontsize=11,
            color=COLOR["ink600"], va="center", zorder=2)
    ax.add_patch(Circle((col_x[2] + 0.22, yy - row_h / 2 + 0.12), 0.07,
                        color=COLOR["safe"], zorder=2))
    ax.text(col_x[2] + 0.45, yy - row_h / 2 + 0.12, ours, fontsize=11,
            color=COLOR["ink900"], weight="semibold", va="center", zorder=2)

ax.text(8, 0.28, "연계 시나리오: 천안세이프에서 위험 판정 → HUG 반환보증 가입·안심계약 도움서비스로 연결하는 '전달 경로' 역할",
        ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

save(fig, "fig_HUG_Compare")
