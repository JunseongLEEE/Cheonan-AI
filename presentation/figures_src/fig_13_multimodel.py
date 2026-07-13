"""Figure 13 — 다중모델 앙상블 성능 비교 (exp_006)
심사위원이 3초 안에 파악해야 할 메시지: 6개 이종 모델이 AUC 0.99에 수렴 — 신호가 견고하며, XGBoost·앙상블이 최고.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

LOG = Path(__file__).resolve().parents[2] / "experiments" / "exp_006_multimodel_ensemble" / "train_log.json"
with open(LOG, encoding="utf-8") as f:
    log = json.load(f)
res = log["results"]

ORDER = ["LogisticReg", "CatBoost", "RandomForest", "HistGB", "LightGBM",
         "Ensemble(Stacking)", "Ensemble(Voting)", "XGBoost"]
LABEL = {
    "LogisticReg": "Logistic (선형 기준선)", "CatBoost": "CatBoost",
    "RandomForest": "Random Forest", "HistGB": "HistGB",
    "LightGBM": "LightGBM (기존 채택)", "Ensemble(Stacking)": "Stacking 앙상블",
    "Ensemble(Voting)": "Voting 앙상블 (추천시스템 채택)", "XGBoost": "XGBoost",
}

names = [LABEL[k] for k in ORDER]
aucs = [res[k]["auc"] for k in ORDER]
f1s = [res[k]["f1"] for k in ORDER]
best = max(ORDER, key=lambda k: res[k]["auc"])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=300,
                               gridspec_kw={"width_ratios": [1.15, 1]})
fig.suptitle("깡통전세 분류 — 6개 이종 모델 + 2개 앙상블 (5-fold CV, 60,412건)",
             fontsize=20, fontweight="bold", color=COLOR["ink900"], y=0.99)
fig.text(0.5, 0.925, "부스팅 계열 전부 AUC 0.987+ 수렴 → 피처 신호 견고성 입증 · Voting 앙상블을 추천시스템 위험점수원으로 채택",
         ha="center", fontsize=12, color=COLOR["ink400"], weight="semibold")

for ax, vals, title, xlim in [
    (ax1, aucs, "AUC ↑", (0.90, 1.0)),
    (ax2, f1s, "F1 ↑", (0.88, 1.0)),
]:
    colors = []
    for k in ORDER:
        if k == best:
            colors.append(COLOR["safe"])
        elif k.startswith("Ensemble"):
            colors.append("#8B5CF6")
        elif k == "LogisticReg":
            colors.append(COLOR["ink400"])
        else:
            colors.append(COLOR["caution"])
    bars = ax.barh(names, vals, color=colors, height=0.62, zorder=3)
    ax.set_xlim(*xlim)
    ax.set_title(title, loc="left", fontsize=15, pad=12)
    ax.grid(axis="x", zorder=0)
    ax.tick_params(axis="y", labelsize=11.5)
    for bar, v, k in zip(bars, vals, ORDER):
        ax.text(v + (xlim[1] - xlim[0]) * 0.008, bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", fontsize=10.5,
                fontweight="bold" if k == best else "normal",
                color=COLOR["ink900"] if k == best else COLOR["ink600"], zorder=4)
    if ax is ax2:
        ax.set_yticklabels([])

# BEST pill
ax1.text(0.9, len(ORDER) - 0.62, " BEST ", fontsize=10, fontweight="bold",
         color="white", ha="center",
         bbox=dict(boxstyle="round,pad=0.35", facecolor=COLOR["safe"], edgecolor="none"),
         transform=ax1.get_yaxis_transform())

fig.text(0.5, 0.015,
         f"최고 단일 {best} AUC {res[best]['auc']:.4f} · Voting(LGBM+XGB+Cat+HistGB) {res['Ensemble(Voting)']['auc']:.4f}"
         " · 선형모델 0.914 → 비선형 상호작용이 +7.6pp 기여",
         ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.04, 1, 0.90])
save(fig, "fig_MultiModel_Compare")
