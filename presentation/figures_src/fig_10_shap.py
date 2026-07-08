"""Figure 10 — SHAP 상위 5개 피처 (모델 설명력)
심사위원이 3초 안에 파악해야 할 메시지: 모델은 "동네가 위험한가", "건물이 낡았는가", "가격이 동네 평균 대비 비싼가" 세 축으로 결정을 내린다.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(ROOT / "experiments/exp_004_threshold_80/shap/shap_importance.csv")
top = df.head(5).iloc[::-1].reset_index(drop=True)

# 피처 그룹 색: 지역(risk), 건물(caution), 가격/시점(ink900)
GROUP = {
    "연도별_동_위험도":   ("지역·시점 신호", COLOR["risk"]),
    "건물연령":           ("건물 노후 신호",  COLOR["caution"]),
    "㎡당_보증금":         ("가격 신호",       COLOR["ink900"]),
    "거래연도":           ("지역·시점 신호", COLOR["risk"]),
    "건물연령_동평균차": ("건물 노후 신호",  COLOR["caution"]),
}

# 16:9
fig, ax = plt.subplots(figsize=(16, 8.4), dpi=300)

fig.text(0.06, 0.95, "모델은 무엇을 보고 위험이라 판단하는가",
         fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.06, 0.913,
         "LightGBM exp_004 · SHAP TreeExplainer · 상위 5개 피처",
         fontsize=13, color=COLOR["ink400"], weight="semibold")

ys = range(len(top))
labels = top["feature"].tolist()
vals = top["mean_abs_shap"].values
colors = [GROUP.get(f, ("기타", COLOR["ink400"]))[1] for f in labels]

bars = ax.barh(ys, vals, color=colors, edgecolor="none",
               height=0.55, zorder=3)

for i, (b, v, f) in enumerate(zip(bars, vals, labels)):
    ax.text(v + 0.04, b.get_y() + b.get_height() / 2,
            f"{v:.2f}", va="center", fontsize=13,
            weight="bold", color=COLOR["ink900"], zorder=4)
    # 왼쪽 카테고리 pill
    grp_lab, grp_col = GROUP.get(f, ("기타", COLOR["ink400"]))
    ax.text(-0.03, b.get_y() + b.get_height() / 2, f,
            ha="right", va="center", fontsize=13,
            color=COLOR["ink900"], weight="semibold", zorder=4)

ax.set_yticks([])
ax.set_xlim(-0.7, max(vals) * 1.18)
ax.set_xlabel("mean |SHAP value|  (예측 기여도)",
              fontsize=12, color=COLOR["ink600"], weight="semibold")
ax.grid(axis="x", color="#F1F5F9", linewidth=0.8, zorder=1)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_color(COLOR["line"])
ax.set_xticks([0, 0.5, 1.0, 1.5, 2.0])

# 우측 카테고리 범례 (dot + text)
legend_items = [
    ("지역·시점 신호", COLOR["risk"]),
    ("건물 노후 신호",  COLOR["caution"]),
    ("가격 신호",       COLOR["ink900"]),
]
for k, (lab, col) in enumerate(legend_items):
    y = 4.1 - k * 0.5
    ax.scatter([1.80], [y], s=90, color=col, edgecolor="white",
               linewidth=1.5, zorder=5)
    ax.text(1.87, y, lab, va="center", fontsize=11.5,
            color=COLOR["ink900"], weight="semibold", zorder=5)

# 하단 인사이트 pill
insight = ("모델이 자동으로 발견한 세 축 — 지역, 건물, 가격 — 은 "
           "HUG 안심전세(단순 규칙)가 잡지 못하는 '동네 평균 대비 비정상' 패턴을 학습")
fig.text(0.5, 0.04, insight, ha="center", fontsize=11.5,
         color=COLOR["ink900"], weight="semibold",
         bbox=dict(boxstyle="round,pad=0.5", facecolor=COLOR["soft"],
                   edgecolor=COLOR["line"], linewidth=1))

save(fig, "fig_SHAP_Top5")
