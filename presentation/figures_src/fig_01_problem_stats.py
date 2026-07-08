"""Figure 1 — 문제 통계 3-Numbers
심사위원이 3초 안에 파악해야 할 메시지: 청년 20만 중 86%가 세입자, 그런데 전세사기 288세대가 이미 발생했다.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from matplotlib.lines import Line2D
from viz_style import apply_style, save, COLOR

apply_style()


def _draw_users_icon(ax, cx, cy, r, color):
    """Lucide 'users' 스타일: 두 사람 실루엣 (얇은 선)."""
    lw = 1.6
    # 뒷사람 (작게, 왼쪽)
    ax.add_patch(Circle((cx - r*0.42, cy + r*0.18), r*0.22,
                        facecolor="none", edgecolor=color, linewidth=lw, zorder=5))
    # 앞사람 (오른쪽)
    ax.add_patch(Circle((cx + r*0.05, cy + r*0.10), r*0.28,
                        facecolor="none", edgecolor=color, linewidth=lw, zorder=5))
    # 어깨선 (뒷사람)
    ax.add_patch(patches.Arc((cx - r*0.42, cy - r*0.35), r*0.9, r*0.7,
                             theta1=0, theta2=180,
                             color=color, linewidth=lw, zorder=5))
    # 어깨선 (앞사람)
    ax.add_patch(patches.Arc((cx + r*0.05, cy - r*0.42), r*1.05, r*0.85,
                             theta1=0, theta2=180,
                             color=color, linewidth=lw, zorder=5))


def _draw_key_icon(ax, cx, cy, r, color):
    """Lucide 'key' 스타일: 원 + 축 + 이빨."""
    lw = 1.6
    ax.add_patch(Circle((cx - r*0.35, cy), r*0.28,
                        facecolor="none", edgecolor=color, linewidth=lw, zorder=5))
    # 축 (오른쪽 스템)
    ax.plot([cx - r*0.10, cx + r*0.55], [cy, cy],
            color=color, linewidth=lw, zorder=5, solid_capstyle="round")
    # 이빨 2개
    ax.plot([cx + r*0.25, cx + r*0.25], [cy, cy - r*0.22],
            color=color, linewidth=lw, zorder=5, solid_capstyle="round")
    ax.plot([cx + r*0.50, cx + r*0.50], [cy, cy - r*0.18],
            color=color, linewidth=lw, zorder=5, solid_capstyle="round")


def _draw_alert_icon(ax, cx, cy, r, color):
    """Lucide 'alert-triangle' 스타일: 삼각형 + 느낌표."""
    lw = 1.6
    # 삼각형 (round vertex 흉내: 꼭짓점을 살짝 안쪽으로)
    tri = patches.Polygon(
        [(cx, cy + r*0.55), (cx + r*0.55, cy - r*0.42), (cx - r*0.55, cy - r*0.42)],
        closed=True, facecolor="none", edgecolor=color, linewidth=lw,
        joinstyle="round", zorder=5)
    ax.add_patch(tri)
    # 느낌표 세로선
    ax.plot([cx, cx], [cy + r*0.20, cy - r*0.15],
            color=color, linewidth=lw, solid_capstyle="round", zorder=6)
    # 느낌표 점
    ax.add_patch(Circle((cx, cy - r*0.28), r*0.045,
                        facecolor=color, edgecolor="none", zorder=6))


ICON_DRAW = {"users": _draw_users_icon, "key": _draw_key_icon, "alert": _draw_alert_icon}

# ── 데이터 (data_facts.md §1) ──
# 3번째 카드는 pct 대신 stat_pill 표시 — 288세대·145억은 비율(%)로 환원 불가
CARDS = [
    dict(big="19.7만명", title="18~39세 청년 인구",
         sub="천안 전체의 약 30%",   pct=0.30,
         pct_label="천안 전체 대비",
         color=COLOR["safe"], soft=COLOR["safe_soft"], icon_kind="users"),
    dict(big="86%",       title="청년 무주택 비율",
         sub="10명 중 8~9명이 세입자", pct=0.86,
         pct_label="세입자 비율",
         color=COLOR["caution"], soft=COLOR["caution_soft"], icon_kind="key"),
    dict(big="288세대",   title="전세사기 피해 (2024)",
         sub="피해액 145억 · 원성동 집중", pct=None,   # 비율 시각화 부적합
         pct_label=None,
         stat_pill="즉시 개입 필요",
         color=COLOR["risk"], soft=COLOR["risk_soft"], icon_kind="alert"),
]

# 16:6 히어로 비율
fig, ax = plt.subplots(figsize=(16, 6), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 6); ax.axis("off")

# ── 타이틀 ──
ax.text(8, 5.5, "천안 청년 주거 안전, 왜 지금인가",
        ha="center", fontsize=22, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 5.05, "청년 인구는 늘어나는데, 안전한 자취방 정보는 부재하다",
        ha="center", fontsize=13, color=COLOR["ink600"])

# ── 카드 배치 (8px grid: 카드 폭 4.16, gap 0.8) ──
card_w, card_h = 4.16, 3.0
card_y = 1.4
xs = [1.28, 5.92, 10.56]  # 8px 그리드 근사

for x, c in zip(xs, CARDS):
    # 카드 (흰 배경 + 얇은 테두리)
    ax.add_patch(FancyBboxPatch((x, card_y), card_w, card_h,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor="white", zorder=1))
    # 상단 4px 액센트 바 (semantic color)
    ax.add_patch(patches.Rectangle((x + 0.15, card_y + card_h - 0.08),
                                   card_w - 0.30, 0.08,
                                   facecolor=c["color"], edgecolor="none", zorder=2))

    # 아이콘 뱃지 (좌상단, semantic soft 배경)
    badge_x, badge_y = x + 0.35, card_y + card_h - 0.75
    r_badge = 0.32
    ax.add_patch(patches.Circle((badge_x, badge_y), r_badge,
                                facecolor=c["soft"], edgecolor=c["color"],
                                linewidth=1.5, zorder=3))
    ICON_DRAW[c["icon_kind"]](ax, badge_x, badge_y, r_badge * 0.85, c["color"])

    # 큰 숫자 (H1) — 위쪽으로 이동해 하단 progress bar와 여유 확보
    ax.text(x + card_w / 2, card_y + card_h - 1.20, c["big"],
            ha="center", va="center", fontsize=34, fontweight="bold",
            color=COLOR["ink900"], zorder=3)
    # 라벨
    ax.text(x + card_w / 2, card_y + card_h - 1.80, c["title"],
            ha="center", va="center", fontsize=13, color=COLOR["ink900"],
            weight="semibold", zorder=3)
    ax.text(x + card_w / 2, card_y + card_h - 2.15, c["sub"],
            ha="center", va="center", fontsize=10.5, color=COLOR["ink400"], zorder=3)

    # 하단 progress bar — pct 있는 카드만. 라벨을 바 "위"로 배치해 캡션과 분리.
    bar_x, bar_y = x + 0.4, card_y + 0.30
    bar_w_local = card_w - 0.8
    if c["pct"] is not None:
        # 바 위쪽에 라벨 (캡션과 progress bar 사이 시각적 층 분리)
        ax.text(bar_x, bar_y + 0.28, c["pct_label"],
                ha="left", fontsize=9.5, color=COLOR["ink400"],
                weight="semibold", zorder=5)
        ax.text(bar_x + bar_w_local, bar_y + 0.28,
                f"{int(c['pct']*100)}%",
                ha="right", fontsize=10, color=c["color"],
                weight="bold", zorder=5)
        # 트랙 + 채움
        ax.add_patch(patches.FancyBboxPatch((bar_x, bar_y), bar_w_local, 0.10,
                                            boxstyle="round,pad=0,rounding_size=0.05",
                                            facecolor=COLOR["line"], edgecolor="none",
                                            zorder=3))
        ax.add_patch(patches.FancyBboxPatch((bar_x, bar_y), bar_w_local * c["pct"], 0.10,
                                            boxstyle="round,pad=0,rounding_size=0.05",
                                            facecolor=c["color"], edgecolor="none",
                                            zorder=4))
    else:
        # 3번째 카드: 비율 대신 semantic stat pill (100% progress bar 오해 방지)
        pill_h_local = 0.42
        pill_y_local = card_y + 0.25
        ax.add_patch(FancyBboxPatch((bar_x, pill_y_local), bar_w_local, pill_h_local,
                                    boxstyle="round,pad=0.02,rounding_size=0.20",
                                    facecolor=c["soft"], edgecolor=c["color"],
                                    linewidth=1.2, zorder=3))
        ax.text(bar_x + bar_w_local / 2, pill_y_local + pill_h_local / 2,
                c["stat_pill"], ha="center", va="center",
                fontsize=11.5, color=c["color"], weight="bold", zorder=4)

# ── 카드 사이 인과 화살표 (진한 chevron으로 인과 서사 강조) ──
# 카드1(청년 인구) → 카드2(무주택) → 카드3(전세사기) : 진행형 색상 강조
ARROW_COLORS = [COLOR["caution"], COLOR["risk"]]
LABELS = ["세입자화", "사기 노출"]
for i in range(2):
    arrow_x0 = xs[i] + card_w + 0.12
    arrow_x1 = xs[i+1] - 0.12
    ay = card_y + card_h / 2   # 정중앙, 수평 배치 → 아이콘 배지와 간섭 없음
    # 인과 라벨 (화살표 아래쪽)
    ax.text((arrow_x0 + arrow_x1) / 2, ay - 0.45, LABELS[i],
            ha="center", va="center", fontsize=10,
            color=ARROW_COLORS[i], weight="bold", zorder=3)
    # 굵고 진한 chevron (수평)
    arr = FancyArrowPatch((arrow_x0, ay), (arrow_x1, ay),
                          arrowstyle="-|>,head_length=14,head_width=10",
                          mutation_scale=1.0,
                          color=ARROW_COLORS[i], linewidth=3.0, zorder=2)
    ax.add_patch(arr)

# ── 하단 CTA (얇은 pill) ──
cta_text = "→ 도시 전체 선제 스캔 + 개인 매물 위험도 예측"
pill_w, pill_h = 8.2, 0.6
pill_x = 8 - pill_w / 2
pill_y = 0.35
ax.add_patch(FancyBboxPatch((pill_x, pill_y), pill_w, pill_h,
                            boxstyle="round,pad=0.02,rounding_size=0.28",
                            linewidth=1.2, edgecolor=COLOR["ink900"],
                            facecolor="white", zorder=1))
ax.text(8, pill_y + pill_h / 2, cta_text,
        ha="center", va="center", fontsize=13, fontweight="bold",
        color=COLOR["ink900"], zorder=2)

save(fig, "fig_Problem_Stats")
