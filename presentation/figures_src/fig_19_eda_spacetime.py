"""Figure 19 — EDA 근거 ③: 위험의 공간·시간 구조성
심사위원이 3초 안에 파악해야 할 메시지: 위험거래율이 동별 1.5%~84%로 극단 분산 + 시기별 패턴 — 무작위가 아니라 예측 가능한 구조다.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
base = pd.read_parquet(ROOT / "data" / "processed" / "recommend_base.parquet")
b = base.dropna(subset=["전세가율"]).copy()
b["위험거래"] = (b["전세가율"] >= 0.80).astype(int)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5), dpi=300,
                               gridspec_kw={"width_ratios": [1.15, 1]})
fig.suptitle("근거 ③ 위험의 구조성 — 공간·시간에 집중된 패턴",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.07, ha="left", y=0.985)
fig.text(0.07, 0.92,
         "위험이 무작위라면 학습이 불가능 — 동네·시기별로 뚜렷이 갈리므로 모델이 패턴을 포착할 수 있다",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# ── 좌: 동별 위험거래율 (거래 100건+) ──
dong = (b.groupby("법정동명")
        .agg(위험률=("위험거래", "mean"), 거래수=("위험거래", "count"), 동남구=("동남구", "max")))
dong = dong[dong["거래수"] >= 100].sort_values("위험률")
top = pd.concat([dong.head(6), dong.tail(8)])
colors = ["#B45309" if g == 1 else "#0369A1" for g in top["동남구"]]
bars = ax1.barh([f"{d}" for d in top.index], top["위험률"], color=colors, height=0.62, zorder=3)
for bar, (d, row) in zip(bars, top.iterrows()):
    ax1.text(row["위험률"] + 0.012, bar.get_y() + bar.get_height() / 2,
             f"{row['위험률']:.0%}", va="center", fontsize=10.5,
             color=COLOR["ink900"], fontweight="bold", zorder=4)
ax1.set_title("동별 위험거래율 — 상위 8 / 하위 6 (거래 100건 이상 38개 동)",
              loc="left", fontsize=13.5, pad=10)
ax1.set_xlim(0, 0.98)
ax1.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax1.grid(axis="x")
ax1.tick_params(axis="y", labelsize=10.5)
ax1.axvline(b["위험거래"].mean(), color=COLOR["ink400"], linestyle="--", linewidth=1.2)
ax1.text(b["위험거래"].mean() + 0.01, 0.3, f"전체 평균 {b['위험거래'].mean():.0%}",
         fontsize=10, color=COLOR["ink400"], rotation=90, va="bottom")
ax1.legend(handles=[Patch(color="#B45309", label="동남구 (구도심)"),
                    Patch(color="#0369A1", label="서북구 (신도심)")],
           frameon=False, fontsize=11, loc="lower right")

# ── 우: 연도별 위험비율 추이 ──
b["연도"] = b["거래일"].dt.year
yearly = b[b["연도"].between(2019, 2026)].groupby("연도").agg(
    위험비율=("위험거래", "mean"), 거래수=("위험거래", "count"))
ax2.plot(yearly.index, yearly["위험비율"], color=COLOR["risk"], linewidth=2.6,
         marker="o", markersize=7, zorder=4)
for yy, row in yearly.iterrows():
    dy = 0.022 if yy not in (2021, 2026) else 0.028
    ax2.annotate(f"{row['위험비율']:.0%}", (yy, row["위험비율"]),
                 textcoords="offset points", xytext=(0, 10),
                 ha="center", fontsize=10.5, fontweight="bold", color=COLOR["ink900"])
ax2.set_title("연도별 위험거래(전세가율 80%+) 비율", loc="left", fontsize=13.5, pad=10)
ax2.set_ylim(0.30, 0.70)
ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax2.grid(axis="y")
ax2.annotate("2021 갭투자 피크", xy=(2021, yearly.loc[2021, "위험비율"]),
             xytext=(2019.3, 0.655), fontsize=11, color=COLOR["ink600"],
             arrowprops=dict(arrowstyle="->", color=COLOR["ink400"], lw=1.3))
ax2.annotate("2026 재상승 경보", xy=(2026, yearly.loc[2026, "위험비율"]),
             xytext=(2023.8, 0.63), fontsize=11, fontweight="bold", color=COLOR["risk"],
             arrowprops=dict(arrowstyle="->", color=COLOR["risk"], lw=1.3))

fig.text(0.5, 0.012,
         "동별 위험률 1.5%~84% 극단 분산 · 동남구 평균 37.2% > 서북구 30.8% · '연도별 동 위험도'가 SHAP 1위 피처인 이유",
         ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.035, 1, 0.89])
save(fig, "fig_EDA_SpaceTime")
