"""Figure 8 — 천안 65개 법정동 종합안전점수 랭킹 (EDA·당위성)
심사위원이 3초 안에 파악해야 할 메시지: 65개 동의 안전점수 격차는 30점(44.9~75.5) — 청년이 사는 곳에 따라 위험 노출이 극단적으로 갈린다.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle

from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_parquet(ROOT / "data/processed/dong_safety_score.parquet")
df = df.sort_values("종합안전점수", ascending=True).reset_index(drop=True)

# 신호등 → 색
color_map = {"빨강": COLOR["risk"], "노랑": COLOR["caution"], "초록": COLOR["safe"]}
colors = df["신호등"].map(color_map).tolist()

# 16:9
fig, ax = plt.subplots(figsize=(16, 9), dpi=300)

# Title
fig.text(0.06, 0.955, "천안 65개 법정동 종합안전점수 랭킹",
         fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.06, 0.923,
         "8축(금융안전·건물노후·치안·소방·교통·편의·환경·침수) 통합 · 신호등 3등급 자동 산출",
         fontsize=12.5, color=COLOR["ink400"], weight="semibold")

ys = np.arange(len(df))
bars = ax.barh(ys, df["종합안전점수"].values, color=colors,
               edgecolor="none", height=0.72, zorder=3)

# 매우 조밀 → 라벨은 상/하 5개만 표기
show_top = 5
show_bottom = 5
for i in range(len(df)):
    is_head = i < show_bottom
    is_tail = i >= len(df) - show_top
    if is_head or is_tail:
        v = df["종합안전점수"].iloc[i]
        name = df["법정동명"].iloc[i]
        # 좌측: 동네명 (label opposite)
        ax.text(v + 0.6, ys[i], f"{name}  {v:.1f}",
                va="center", fontsize=10, weight="semibold",
                color=colors[i], zorder=5)

# 원성동 강조 (스토리 hook)
one_idx = df.index[df["법정동명"] == "원성동"].tolist()
if one_idx:
    idx = one_idx[0]
    ax.text(-1.2, ys[idx], "원성동",
            ha="right", va="center", fontsize=13,
            weight="bold", color=COLOR["risk"], zorder=5)
    ax.annotate("", xy=(df["종합안전점수"].iloc[idx] + 0.1, ys[idx]),
                xytext=(-0.8, ys[idx]),
                arrowprops=dict(arrowstyle="->", color=COLOR["risk"], lw=1.5),
                zorder=5)

# 위험/주의/안전 배경 컬럼 표시 (얇은 세로 밴드)
ax.axvspan(0, 55, facecolor=COLOR["risk_soft"], alpha=0.35, zorder=1)
ax.axvspan(55, 65, facecolor=COLOR["caution_soft"], alpha=0.35, zorder=1)
ax.axvspan(65, 100, facecolor=COLOR["safe_soft"], alpha=0.35, zorder=1)

# 등급 경계선
for x in (55, 65):
    ax.axvline(x, color=COLOR["ink400"], linewidth=0.8,
               linestyle=(0, (3, 3)), zorder=2)

# X 축
ax.set_xlim(-4, 82)
ax.set_xticks([45, 55, 65, 75])
ax.set_xticklabels(["45", "55", "65", "75"])
ax.set_yticks([])
ax.set_xlabel("종합안전점수 (0~100)", fontsize=12,
              color=COLOR["ink600"], weight="semibold")
ax.grid(axis="x", color="#F1F5F9", linewidth=0.8, zorder=1)
ax.set_ylim(-1, len(df))
ax.invert_yaxis()

# 상단 라벨(zone)
for x, lab, col in [(50, "위험", COLOR["risk"]),
                    (60, "주의", COLOR["caution"]),
                    (72, "안전", COLOR["safe"])]:
    ax.text(x, -0.7, lab, ha="center", fontsize=11,
            color=col, weight="bold")

# 우측 통계 카드
mean = df["종합안전점수"].mean()
mn   = df["종합안전점수"].min()
mx   = df["종합안전점수"].max()
gap  = mx - mn

# 카드 3개
card_specs = [
    (f"{gap:.1f}점", "안전점수 격차 (최고-최저)", COLOR["risk"]),
    (f"{mean:.1f}", "천안시 평균 안전점수", COLOR["ink900"]),
    (f"{df['신호등'].value_counts().get('빨강', 0)}개",
     "위험 등급 동네 수", COLOR["risk"]),
]
for k, (big, lab, col) in enumerate(card_specs):
    cx = 92 + 0  # data 좌표 밖으로 절대 위치 사용
    cy = 4 + k * 10
    # data-coord 넘어가는 영역: 직접 계산
    ax.add_patch(FancyBboxPatch((85, k * 22 + 5), 26, 15,
                                boxstyle="round,pad=0.02,rounding_size=0.5",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor=COLOR["soft"], zorder=6, clip_on=False))
    ax.text(98, k * 22 + 15, big,
            ha="center", va="center", fontsize=20, weight="bold",
            color=col, zorder=7, clip_on=False)
    ax.text(98, k * 22 + 8, lab,
            ha="center", va="center", fontsize=10.5,
            color=COLOR["ink400"], weight="semibold", zorder=7, clip_on=False)

ax.set_xlim(-4, 112)  # 카드 자리 확보

save(fig, "fig_Dong_Ranking")
