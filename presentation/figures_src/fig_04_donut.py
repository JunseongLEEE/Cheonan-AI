"""Figure 4 — 안전 신호등 도넛 + 등급별 대표 동네
심사위원이 3초 안에 파악해야 할 메시지: 65개 동 중 위험 1.5%(원성동) — 우리 서비스는 이 지역을 정확히 짚어낸다.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_parquet(ROOT / "data/processed/dong_safety_score.parquet")

order = ["초록", "노랑", "빨강"]
colors = [COLOR["safe"], COLOR["caution"], COLOR["risk"]]
labels = ["안전", "주의", "위험"]
counts = [int((df["신호등"] == k).sum()) for k in order]
total = sum(counts)
pct = [c / total * 100 for c in counts]

# 등급별 대표 동네 top 3 (종합안전점수 기준)
top_map = {}
for k, lab in zip(order, labels):
    sub = df[df["신호등"] == k].sort_values("종합안전점수", ascending=(k == "빨강"))
    top_map[lab] = sub["법정동명"].head(3).tolist()

# ── 캔버스 16:9 ──
fig = plt.figure(figsize=(16, 9), dpi=300)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.1], wspace=0.02)
ax_l = fig.add_subplot(gs[0])
ax_r = fig.add_subplot(gs[1])

# ── 좌: 도넛 ──
ax_l.set_aspect("equal")
ax_l.axis("off")

# 도넛 얇게(0.28), gap 2px
wedges, _ = ax_l.pie(
    counts, colors=colors, startangle=90, counterclock=False,
    wedgeprops=dict(width=0.28, edgecolor="white", linewidth=3),
)

# 중앙 텍스트
ax_l.text(0, 0.18, f"{total}", ha="center", va="center",
          fontsize=54, fontweight="bold", color=COLOR["ink900"])
ax_l.text(0, -0.02, "총 법정동", ha="center", va="center",
          fontsize=12, color=COLOR["ink400"], weight="semibold")

# sub-metric: 위험 1.5%
risk_pct = counts[2] / total * 100
ax_l.text(0, -0.28, f"위험 {risk_pct:.1f}%", ha="center", va="center",
          fontsize=14, color=COLOR["risk"], fontweight="bold")

# leader line + 외부 라벨
def polar_to_xy(theta, r):
    return r * np.cos(np.deg2rad(theta)), r * np.sin(np.deg2rad(theta))

start_angle = 90
for i, (w, c, lab, cnt) in enumerate(zip(wedges, colors, labels, counts)):
    a1, a2 = w.theta1, w.theta2
    mid = (a1 + a2) / 2
    span_pct = pct[i]
    is_tiny = span_pct < 3.0  # 극소 웨지 (위험 1개 ≈ 1.5%) — 리더를 곧게 옆으로

    if is_tiny:
        # 극소 웨지: 리더를 옆으로 곧게 뽑아 다른 라벨과 세로 간섭 방지
        x0, y0 = polar_to_xy(mid, 0.86)
        # 웨지가 어느 반쪽인지에 따라 좌/우로 강제 확장
        side_right = np.cos(np.deg2rad(mid)) >= 0
        x2 = 1.32 if side_right else -1.32
        y1 = y0  # 수평 유지 → 완전히 곧은 리더
        # 다른 라벨과 겹치지 않도록 세로 오프셋 (아래로 살짝 내림)
        y1 -= 0.10
        ha = "left" if side_right else "right"
        ax_l.plot([x0, x2 * 0.85, x2], [y0, y1, y1],
                  color=c, linewidth=1.1)
    else:
        # 리더 라인 시작(도넛 바깥) ~ 끝
        x0, y0 = polar_to_xy(mid, 0.86)
        x1, y1 = polar_to_xy(mid, 1.05)
        x2 = 1.22 if x1 > 0 else -1.22
        ha = "left" if x1 > 0 else "right"
        ax_l.plot([x0, x1, x2], [y0, y1, y1],
                  color=COLOR["ink400"], linewidth=0.9)

    ax_l.text(x2, y1 + 0.05, f"{cnt}개 · {pct[i]:.1f}%",
              ha=ha, va="bottom", fontsize=12,
              color=c if is_tiny else COLOR["ink900"],
              fontweight="bold")
    ax_l.text(x2, y1 - 0.06, lab,
              ha=ha, va="top", fontsize=10.5, color=c, weight="semibold")

ax_l.set_xlim(-1.6, 1.6); ax_l.set_ylim(-1.4, 1.4)

# ── 우: 등급별 대표 동네 리스트 ──
ax_r.axis("off")
ax_r.set_xlim(0, 10); ax_r.set_ylim(0, 10)

ax_r.text(0.4, 9.4, "천안시 65개 법정동 안전 등급 분포",
          fontsize=20, fontweight="bold", color=COLOR["ink900"])
ax_r.text(0.4, 8.85, "각 등급의 대표 동네 (Top 3)",
          fontsize=12, color=COLOR["ink400"], weight="semibold")

# 3개 카드 (안전/주의/위험) — 이모지 대신 컬러 dot 도형 사용
card_specs = [
    ("안전", COLOR["safe"], COLOR["safe_soft"]),
    ("주의", COLOR["caution"], COLOR["caution_soft"]),
    ("위험", COLOR["risk"], COLOR["risk_soft"]),
]
card_h = 2.2
card_gap = 0.35
top_y = 7.9

for i, (lab, col, soft) in enumerate(card_specs):
    y = top_y - i * (card_h + card_gap)
    ax_r.add_patch(patches.FancyBboxPatch(
        (0.3, y - card_h), 9.4, card_h,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        linewidth=1.0, edgecolor=COLOR["line"], facecolor="white"))
    # 좌측 4px 액센트
    ax_r.add_patch(patches.Rectangle((0.3, y - card_h + 0.15), 0.08, card_h - 0.30,
                                     facecolor=col, edgecolor="none"))

    # 등급 dot + 라벨 (개수는 왼쪽 도넛 leader에 이미 표시되어 중복 pill 제거)
    ax_r.add_patch(patches.Circle((0.9, y - 0.5), 0.16,
                                  facecolor=col, edgecolor="none"))
    ax_r.text(1.25, y - 0.5, f"{lab}",
              fontsize=17, fontweight="bold", color=COLOR["ink900"], va="center")

    # 대표 동네
    dongs = top_map[lab]
    dong_txt = "  ·  ".join(dongs) if dongs else "-"
    ax_r.text(0.7, y - 1.15, "대표 동네",
              fontsize=10, color=COLOR["ink400"], weight="semibold")
    ax_r.text(0.7, y - 1.65, dong_txt,
              fontsize=13, color=COLOR["ink900"], weight="semibold")

# 하단 캡션
ax_r.text(0.4, 0.4,
          "LightGBM 위험도 + 8축 안전점수를 통합해 자동 산출된 결과",
          fontsize=10.5, color=COLOR["ink400"], style="italic")

save(fig, "fig_Grade_Donut")
