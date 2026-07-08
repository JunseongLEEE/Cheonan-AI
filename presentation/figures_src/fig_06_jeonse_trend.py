"""Figure 6 — 천안 전세가율 15년 추이 (EDA·당위성)
심사위원이 3초 안에 파악해야 할 메시지: 천안 전세가율은 15년 새 0.64 → 0.82로 상승했고, 위험선(0.80) 이상 매물이 이제 절반이다.
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
r["연도"] = pd.to_datetime(r["거래일"]).dt.year
r = r[(r["연도"] >= 2011) & (r["연도"] <= 2025)]
r = r[(r["전세가율"] > 0.2) & (r["전세가율"] < 2.5)]  # 극단치 필터
grp = r.groupby("연도")["전세가율"].agg(
    median="median",
    ratio_80=lambda s: (s >= 0.80).mean(),
    n="count",
).reset_index()

years = grp["연도"].values
med   = grp["median"].values * 100    # %
r80   = grp["ratio_80"].values * 100

# 16:9
fig = plt.figure(figsize=(16, 8.6), dpi=300)
gs = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.0], hspace=0.35)
ax  = fig.add_subplot(gs[0])
axB = fig.add_subplot(gs[1])

# ── Title ──
fig.text(0.09, 0.96, "왜 지금인가 — 천안 전세가율 15년 추이",
         fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.09, 0.925, "중위값이 0.64 → 0.82로 상승, 위험선(0.80) 이상 매물이 절반을 넘어섰다",
         fontsize=13, color=COLOR["ink400"], weight="semibold")

# ── Upper: median line + risk zone band ──
ax.axhspan(90, 105, facecolor=COLOR["risk_soft"], edgecolor="none", zorder=1,
           label="_hidden")
ax.axhspan(80, 90,  facecolor=COLOR["caution_soft"], edgecolor="none", zorder=1)
ax.axhspan(0,  80,  facecolor=COLOR["safe_soft"], alpha=0.35, edgecolor="none", zorder=1)

# 위험선
ax.axhline(80, color=COLOR["risk"], linewidth=1.2, linestyle="--", zorder=2)
ax.text(years[-1] + 0.15, 80, "위험선 80%",
        color=COLOR["risk"], fontsize=10.5, weight="semibold", va="center")
ax.axhline(90, color=COLOR["risk"], linewidth=0.8, linestyle=":", alpha=0.6, zorder=2)
ax.text(years[-1] + 0.15, 90, "깡통 임계 90%",
        color=COLOR["risk"], fontsize=10, weight="semibold", va="center", alpha=0.75)

# median line
ax.plot(years, med, color=COLOR["ink900"], linewidth=2.6, zorder=4)
ax.scatter(years, med, s=45, color=COLOR["ink900"],
           edgecolor="white", linewidth=1.8, zorder=5)

# 시작/끝 강조
ax.annotate(f"{med[0]:.1f}%", xy=(years[0], med[0]),
            xytext=(years[0] - 0.2, med[0] - 6),
            fontsize=13, weight="bold", color=COLOR["safe"], ha="center")
ax.annotate(f"{med[-1]:.1f}%", xy=(years[-1], med[-1]),
            xytext=(years[-1] + 0.05, med[-1] + 3),
            fontsize=13, weight="bold", color=COLOR["risk"], ha="center")

ax.set_ylim(55, 100)
ax.set_yticks([60, 70, 80, 90])
ax.set_yticklabels(["60%", "70%", "80%", "90%"])
ax.set_xticks(years)
ax.set_xticklabels(years, rotation=0)
ax.set_ylabel("전세가율 중위값", fontsize=12, color=COLOR["ink600"], weight="semibold")
ax.grid(axis="y", color="#F1F5F9", linewidth=0.8, zorder=1)

# ── Lower: 위험 매물 비율(≥80%) 막대 ──
axB.bar(years, r80, color=COLOR["caution"], edgecolor="none",
        width=0.6, zorder=3)
# 최근 3개년 강조
for i in range(len(years) - 3, len(years)):
    axB.bar(years[i], r80[i], color=COLOR["risk"], width=0.6, zorder=4)
axB.set_ylim(0, 75)
axB.set_yticks([0, 25, 50])
axB.set_yticklabels(["0%", "25%", "50%"])
axB.set_xticks(years); axB.set_xticklabels([])
axB.set_ylabel("위험선 이상\n매물 비율", fontsize=10, color=COLOR["ink600"],
               weight="semibold")
axB.grid(axis="y", color="#F1F5F9", linewidth=0.8, zorder=1)

# 최근 3년 평균 라벨
recent_avg = r80[-3:].mean()
axB.text(years[-2], 62, f"최근 3년 평균 {recent_avg:.0f}%",
         ha="center", fontsize=10.5, color=COLOR["risk"], weight="bold")

# ── 요약 캡션 (하단) ──
cap = (f"15년간 전세거래 {int(grp['n'].sum()):,}건 분석 · "
       f"중위 전세가율 +{med[-1]-med[0]:.1f}%p 상승 · "
       "청년 세입자는 시장 평균보다 낡고 저렴한 매물에 노출")
fig.text(0.5, 0.02, cap, ha="center", fontsize=11.5,
         color=COLOR["ink900"], weight="semibold",
         bbox=dict(boxstyle="round,pad=0.5", facecolor=COLOR["soft"],
                   edgecolor=COLOR["line"], linewidth=1))

save(fig, "fig_Jeonse_Trend")
