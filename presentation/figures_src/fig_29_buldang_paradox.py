"""Figure 29 — 불당동 역설 해소: 안전점수 vs 이상거래율 (Tier2-G)
심사위원이 3초 안에 파악해야 할 메시지: 두 지표는 다른 것을 본다 — 동네 구조는 안전해도 거래 행태는 이상할 수 있다.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
safety = pd.read_parquet(ROOT / "data" / "processed" / "dong_safety_score.parquet")
anom = pd.read_parquet(ROOT / "data" / "processed" / "dong_anomaly_rate.parquet")
df = safety.merge(anom, on="법정동명", how="inner")
df = df[df["총거래"] >= 100]

fig, ax = plt.subplots(figsize=(14.5, 8), dpi=300)
fig.suptitle("두 개의 렌즈 — 동네 안전점수 × 이상거래율",
             fontsize=20, fontweight="bold", color=COLOR["ink900"], x=0.08, ha="left", y=0.965)
fig.text(0.08, 0.90, "안전점수 = 동네의 '구조' (노후·전세가율·인프라) · 이상거래율 = 개별 거래의 '행태' (Isolation Forest) — 서로 다른 위험을 잡는다",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

x_mid, y_mid = 60, 0.05
sizes = (df["총거래"] / df["총거래"].max()) * 900 + 60

def quad_color(r):
    if r["종합안전점수"] >= x_mid and r["이상비율"] >= y_mid:
        return "#8B5CF6"     # 구조 안전 + 행태 이상 (불당동 사분면)
    if r["종합안전점수"] < x_mid and r["이상비율"] >= y_mid:
        return COLOR["risk"]
    if r["종합안전점수"] < x_mid:
        return COLOR["caution"]
    return COLOR["safe"]

ax.scatter(df["종합안전점수"], df["이상비율"], s=sizes,
           c=df.apply(quad_color, axis=1), alpha=0.75,
           edgecolors="white", linewidths=1.2, zorder=3)

ax.axvline(x_mid, color=COLOR["ink400"], linewidth=1.1, linestyle="--", zorder=2)
ax.axhline(y_mid, color=COLOR["ink400"], linewidth=1.1, linestyle="--", zorder=2)

# 사분면 라벨
ax.text(74.5, 0.145, "구조 안전 · 행태 이상\n→ 신축 깡통 패턴 감시 구역", fontsize=11.5,
        fontweight="bold", color="#6D28D9", ha="center")
ax.text(47, 0.145, "구조 취약 · 행태 이상\n→ 즉시 개입", fontsize=11.5,
        fontweight="bold", color=COLOR["risk"], ha="center")
ax.text(47, -0.004, "구조 취약 · 행태 정상", fontsize=10.5, color="#92400E", ha="center")
ax.text(74.5, -0.004, "구조·행태 모두 양호", fontsize=10.5, color="#065F46", ha="center")

# 핵심 동 주석
FOCUS = {"불당동": ((-38, 14), "#6D28D9",
                  "불당동 — 안전점수 71.5(초록)인데\n이상거래율 15.6% 1위:\n신축 다세대 고보증금 반복 계약"),
         "원성동": ((16, 26), COLOR["risk"], "원성동 — 구조 위험(44.9)이 주원인,\n이상거래도 평균 이상(9.2%)"),
         "쌍용동": ((-52, -26), COLOR["ink600"], "쌍용동 (거래 2.1만)"),
         "두정동": ((14, -30), COLOR["ink600"], "두정동")}
for dong, ((dx, dy), c, label) in FOCUS.items():
    row = df[df["법정동명"] == dong]
    if len(row):
        r = row.iloc[0]
        ax.annotate(label, (r["종합안전점수"], r["이상비율"]),
                    xytext=(dx, dy), textcoords="offset points",
                    fontsize=10.5, fontweight="bold", color=c,
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.2))

ax.set_xlabel("종합 안전점수 (동네 구조, 0~100)")
ax.set_ylabel("이상거래율 (Isolation Forest)")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.set_xlim(42, 80); ax.set_ylim(-0.012, 0.175)
ax.grid(axis="both")

fig.text(0.5, 0.015,
         "버블 크기 = 거래량 · 두 지표를 함께 쓰면 '안전한 동네의 위험 매물'(불당동형)과 '위험한 동네'(원성동형)를 구분해 대응",
         ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.035, 1, 0.87])
save(fig, "fig_Buldang_Paradox")
