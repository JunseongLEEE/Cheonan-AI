"""Figure 17 — EDA 근거 ①: 전세가율 분포와 깡통전세의 실재
심사위원이 3초 안에 파악해야 할 메시지: 깡통전세는 가설이 아니라 실거래 10.3만 건 중 4,847건(4.7%)으로 실재한다.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
base = pd.read_parquet(ROOT / "data" / "processed" / "recommend_base.parquet")
r = base["전세가율"].dropna()
r_clip = r.clip(upper=1.6)

fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
fig.suptitle("근거 ① 깡통전세의 실재 — 실거래 전세가율 분포",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.123, ha="left", y=0.97)
fig.text(0.123, 0.905,
         f"국토부 실거래 {len(r):,}건 (전세 ↔ 매매 실거래 매칭) · 공공데이터만 사용",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

bins = np.arange(0, 1.65, 0.05)
zones = [(0, 0.60, COLOR["safe"]), (0.60, 0.80, COLOR["caution"]),
         (0.80, 1.00, COLOR["risk"]), (1.00, 1.65, "#991B1B")]
counts, edges = np.histogram(r_clip, bins=bins)
for c, e in zip(counts, edges):
    color = next(col for lo, hi, col in zones if lo <= e < hi)
    ax.bar(e, c, width=0.048, align="edge", color=color, zorder=3)

# 구간 라벨
n = len(r)
zone_info = [
    ("안전\n≤60%", 0.30, (r <= 0.60).sum(), COLOR["safe"]),
    ("주의\n60~80%", 0.70, ((r > 0.60) & (r < 0.80)).sum(), COLOR["caution"]),
    ("위험\n80~100%", 0.90, ((r >= 0.80) & (r < 1.00)).sum(), COLOR["risk"]),
    ("깡통\n≥100%", 1.28, (r >= 1.00).sum(), "#991B1B"),
]
ymax = counts.max()
for label, cx, cnt, col in zone_info:
    ax.text(cx, ymax * 1.06, label, ha="center", fontsize=12.5,
            fontweight="bold", color=col)
    ax.text(cx, ymax * 0.955, f"{cnt:,}건 ({cnt / n:.1%})", ha="center",
            fontsize=11, color=COLOR["ink600"], weight="semibold")

for x in [0.60, 0.80, 1.00]:
    ax.axvline(x, color=COLOR["ink400"], linewidth=1.0, linestyle="--", zorder=2)

med = r.median()
ax.axvline(med, color=COLOR["ink900"], linewidth=1.6, zorder=4)
ax.text(med + 0.012, ymax * 0.72, f"중앙값 {med:.0%}\n(전국 평균 상회)",
        fontsize=11, color=COLOR["ink900"], weight="semibold")

# 깡통 콜아웃
ax.annotate("보증금이 매매가를 초과 —\n경매 시 보증금 전액 손실 위험",
            xy=(1.28, ymax * 0.10), xytext=(1.02, ymax * 0.42),
            fontsize=11.5, color="#991B1B", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#991B1B", lw=1.6))

ax.set_xlim(0, 1.62)
ax.set_ylim(0, ymax * 1.18)
ax.set_xlabel("전세가율 (전세보증금 ÷ 매매가)")
ax.set_ylabel("거래 건수")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.grid(axis="y")

fig.text(0.5, 0.012,
         "위험(80%+) 46,084건 · 깡통(100%+) 4,847건 — 천안 전세사기 288세대·145억 피해의 데이터적 실체",
         ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.04, 1, 0.87])
save(fig, "fig_EDA_JeonseRate")
