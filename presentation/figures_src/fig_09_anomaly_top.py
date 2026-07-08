"""Figure 9 — 이상거래율 상위 10개 동네 (EDA·당위성)
심사위원이 3초 안에 파악해야 할 메시지: 이상거래는 랜덤이 아니라 특정 동네에 집중된다 — 우리 모델이 사각지대를 정확히 짚어낼 수 있는 증거.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
r = pd.read_parquet(ROOT / "data/processed/anomaly_results.parquet")
grp = r.groupby("법정동명").agg(
    n=("이상", "count"),
    n_anom=("이상", "sum"),
).reset_index()
grp["rate"] = grp["n_anom"] / grp["n"] * 100
# 최소 표본 100건 이상
grp = grp[grp["n"] >= 100].sort_values("rate", ascending=False).head(10)
grp = grp.iloc[::-1]  # barh에서 위→아래 정렬을 위해 뒤집기

overall = r["이상"].mean() * 100

# 16:9
fig, ax = plt.subplots(figsize=(16, 8.6), dpi=300)

fig.text(0.07, 0.955, "이상거래는 랜덤이 아니다 — 상위 10개 동네",
         fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.07, 0.92,
         "Isolation Forest 기반 이상탐지 결과 · 최소 표본 100건 이상 동만 집계",
         fontsize=13, color=COLOR["ink400"], weight="semibold")

ys = np.arange(len(grp))
# 색상: TOP 3는 risk, 나머지는 caution
colors = [COLOR["risk"] if i >= len(grp) - 3 else COLOR["caution"]
          for i in range(len(grp))]
bars = ax.barh(ys, grp["rate"].values, color=colors, edgecolor="none",
               height=0.66, zorder=3)

# 값 라벨
for i, (bar, rate, n, name) in enumerate(zip(
        bars, grp["rate"].values, grp["n"].values, grp["법정동명"].values)):
    ax.text(rate + 0.25, ys[i], f"{rate:.1f}%",
            va="center", fontsize=12,
            color=colors[i], weight="bold", zorder=4)
    ax.text(rate + 2.5, ys[i], f"(n={int(n):,})",
            va="center", fontsize=10, color=COLOR["ink400"], zorder=4)

# 동네 이름 (Y축)
ax.set_yticks(ys)
ax.set_yticklabels(grp["법정동명"].values,
                   fontsize=12.5, color=COLOR["ink900"], weight="semibold")

# 전체 평균선
ax.axvline(overall, color=COLOR["ink900"], linewidth=1.4,
           linestyle="--", zorder=2)
ax.text(overall + 0.15, len(grp) - 0.5, f"천안 전체 평균  {overall:.1f}%",
        color=COLOR["ink900"], fontsize=10.5, weight="semibold", va="bottom")

# X축
ax.set_xlim(0, max(grp["rate"].max() * 1.20, 20))
ax.set_xticks(np.arange(0, 20, 5))
ax.set_xticklabels([f"{x}%" for x in np.arange(0, 20, 5)])
ax.set_xlabel("이상거래 비율", fontsize=12,
              color=COLOR["ink600"], weight="semibold")
ax.grid(axis="x", color="#F1F5F9", linewidth=0.8, zorder=1)

# 우측 인사이트 박스
insight_lines = [
    ("15.6%", "불당동 이상거래율\n(평균의 3배)", COLOR["risk"]),
    ("5,134건", "탐지된 이상거래\n(전체 5.0%)", COLOR["ink900"]),
    ("102,671건", "분석된 전세 실거래\n(2011~2026)", COLOR["ink900"]),
]
box_x = 22.5
box_w = 4.5
box_h = 2.2
for k, (big, lab, col) in enumerate(insight_lines):
    box_y = len(grp) - 1.5 - k * (box_h + 0.4)
    ax.add_patch(FancyBboxPatch((box_x, box_y - box_h + 0.4), box_w, box_h,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor=COLOR["soft"], clip_on=False, zorder=5))
    ax.text(box_x + box_w / 2, box_y - 0.15, big,
            ha="center", va="center", fontsize=18, weight="bold",
            color=col, clip_on=False, zorder=6)
    ax.text(box_x + box_w / 2, box_y - 1.05, lab,
            ha="center", va="center", fontsize=10.5,
            color=COLOR["ink400"], weight="semibold", clip_on=False, zorder=6)

ax.set_xlim(0, 28)

# 하단 캡션
fig.text(0.5, 0.03,
         "→ 특정 동네·시기에 위험 매물이 몰려 있다는 통계적 증거 · "
         "AI 모델의 지역별 예측 필요성을 뒷받침",
         ha="center", fontsize=11.5, color=COLOR["ink900"], weight="semibold",
         bbox=dict(boxstyle="round,pad=0.5", facecolor=COLOR["soft"],
                   edgecolor=COLOR["line"], linewidth=1))

save(fig, "fig_Anomaly_Top")
