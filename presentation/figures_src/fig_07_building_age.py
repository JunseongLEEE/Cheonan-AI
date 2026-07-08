"""Figure 7 — 천안 건축물 노후 분포 (EDA·당위성)
심사위원이 3초 안에 파악해야 할 메시지: 20,708채 중 30% 이상이 30년을 넘긴 노후 주택 — 청년 자취방 시장의 구조적 위험 요인.
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
b = pd.read_parquet(ROOT / "data/processed/building_residential.parquet")
b["year"] = pd.to_datetime(b["useAprDay"].astype(str), errors="coerce",
                            format="%Y%m%d").dt.year
b = b.dropna(subset=["year"])
b = b[(b["year"] >= 1920) & (b["year"] <= 2025)]
b["age"] = 2025 - b["year"]

bins = [0, 10, 20, 30, 40, 50, 200]
labels = ["0~10", "11~20", "21~30", "31~40", "41~50", "50년+"]
b["age_bin"] = pd.cut(b["age"], bins=bins, labels=labels, include_lowest=True)
counts = b["age_bin"].value_counts().reindex(labels)
total = int(counts.sum())
pct = counts / total * 100

# 위험 구간(30년+): risk 색상, 나머지는 ink 그라데이션
segment_colors = [
    "#CBD5E1", "#94A3B8", "#64748B",   # 0~30년 (ink 계열)
    COLOR["caution"], "#F97316", COLOR["risk"],  # 30~40, 40~50, 50+
]

# 16:9
fig, ax = plt.subplots(figsize=(16, 8.4), dpi=300)
ax.set_facecolor("white")

# Title
fig.text(0.09, 0.94, "천안 주거용 건축물 20,708채, 노후는 얼마나 심각한가",
         fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.09, 0.905,
         "건물연령 30년 초과 = 노후 · 40년 초과 = 재난 취약 (건축법 기준)",
         fontsize=13, color=COLOR["ink400"], weight="semibold")

xs = np.arange(len(labels))
bars = ax.bar(xs, counts.values, width=0.62,
              color=segment_colors, edgecolor="none", zorder=3)

# 데이터 라벨 (n + %)
for i, (bar, v, p) in enumerate(zip(bars, counts.values, pct.values)):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 90,
            f"{int(v):,}", ha="center", fontsize=12,
            weight="bold", color=COLOR["ink900"], zorder=4)
    ax.text(bar.get_x() + bar.get_width() / 2, v + 40,
            f"{p:.1f}%", ha="center", fontsize=10.5,
            color=COLOR["ink400"], weight="semibold", zorder=4)

# x tick
ax.set_xticks(xs)
ax.set_xticklabels([f"{l}년" if not l.endswith("+") else l for l in labels],
                   fontsize=12, color=COLOR["ink600"], weight="semibold")
ax.set_ylabel("건축물 수 (동)", fontsize=12, color=COLOR["ink600"], weight="semibold")
ax.grid(axis="y", color="#F1F5F9", linewidth=0.8, zorder=1)
ax.set_ylim(0, counts.max() * 1.20)
ax.set_yticks(np.arange(0, counts.max() * 1.2, 1000))
ax.set_yticklabels([f"{int(y):,}" for y in np.arange(0, counts.max() * 1.2, 1000)])
ax.spines["left"].set_color(COLOR["line"])
ax.spines["bottom"].set_color(COLOR["line"])

# 노후 강조 브래킷(30년+)
brk_x0 = xs[3] - 0.35
brk_x1 = xs[-1] + 0.35
brk_y = counts.max() * 1.05
ax.plot([brk_x0, brk_x0, brk_x1, brk_x1],
        [brk_y - 60, brk_y, brk_y, brk_y - 60],
        color=COLOR["risk"], linewidth=1.6, zorder=5)
noh_n = int(counts[["31~40", "41~50", "50년+"]].sum())
noh_pct = counts[["31~40", "41~50", "50년+"]].sum() / total * 100
ax.text((brk_x0 + brk_x1) / 2, brk_y + 240,
        f"노후 주택 (30년+)   {noh_n:,}채 · {noh_pct:.1f}%",
        ha="center", fontsize=13, color=COLOR["risk"], weight="bold", zorder=5)

# 좌하단 stat pill
stats = [("30.1년", "평균 건물연령"),
         (f"{noh_pct:.0f}%", "30년+ 노후 비율"),
         (f"{int(counts['50년+']):,}채", "50년 이상 재난 취약")]
box_y = -0.4  # data coords
for k, (big, lab) in enumerate(stats):
    x = 0.15 + k * 2.0
    ax.add_patch(FancyBboxPatch((x, -counts.max() * 0.20), 1.75, counts.max() * 0.13,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor=COLOR["soft"], zorder=2, clip_on=False))
    ax.text(x + 0.87, -counts.max() * 0.12, big,
            ha="center", fontsize=16, weight="bold",
            color=COLOR["ink900"], zorder=3, clip_on=False)
    ax.text(x + 0.87, -counts.max() * 0.175, lab,
            ha="center", fontsize=10, color=COLOR["ink400"],
            weight="semibold", zorder=3, clip_on=False)

# 여백 확보
ax.set_ylim(-counts.max() * 0.22, counts.max() * 1.24)

save(fig, "fig_Building_Age")
