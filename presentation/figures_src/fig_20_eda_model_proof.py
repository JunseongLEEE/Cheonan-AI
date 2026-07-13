"""Figure 20 — EDA 근거 ④: 매매가 없이도 위험이 복원된다 (최종 입증)
심사위원이 3초 안에 파악해야 할 메시지: 매매가·전세가율을 피처에서 빼고도 AUC 0.99 — 계약 전 매물 진단이 성립한다.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
oof = pd.read_parquet(ROOT / "experiments" / "exp_006_multimodel_ensemble" / "oof_predictions.parquet")
y = oof["위험라벨"].astype(int)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5), dpi=300)
fig.suptitle("근거 ④ 위험의 복원 — 매매가 없이 전세가율 위험을 AUC 0.99로 재구성",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.07, ha="left", y=0.985)
fig.text(0.07, 0.92,
         "라벨은 매매가 기반(전세가율), 피처는 매매가 미포함 — '시세를 모르는 매물'이라는 실서비스 조건의 5-fold 교차검증",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# ── 좌: ROC 곡선 ──
MODELS = [("XGBoost", COLOR["safe"], 2.4), ("LightGBM", COLOR["caution"], 1.6),
          ("HistGB", "#8B5CF6", 1.6), ("CatBoost", "#0EA5E9", 1.6),
          ("RandomForest", "#F97316", 1.6), ("LogisticReg", COLOR["ink400"], 1.8)]
for name, color, lw in MODELS:
    probs = oof[f"oof_{name}"]
    fpr, tpr, _ = roc_curve(y, probs)
    auc = roc_auc_score(y, probs)
    style = "--" if name == "LogisticReg" else "-"
    label = f"{name}  {auc:.3f}" + ("  (선형 한계)" if name == "LogisticReg" else "")
    ax1.plot(fpr, tpr, color=color, linewidth=lw, linestyle=style, label=label, zorder=3)
ax1.plot([0, 1], [0, 1], color=COLOR["line"], linewidth=1.2, zorder=2)
ax1.text(0.52, 0.44, "무작위 추측 (AUC 0.5)", fontsize=10, color=COLOR["ink400"], rotation=38)
ax1.set_title("ROC 곡선 — 6개 모델 5-fold OOF (60,412건)", loc="left", fontsize=13.5, pad=10)
ax1.set_xlabel("위양성률 (안전을 위험으로 오판)")
ax1.set_ylabel("재현율 (위험을 위험으로 탐지)")
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1.02)
ax1.grid(axis="both")
ax1.legend(frameon=False, fontsize=10.5, loc="lower right", title="모델  AUC ↑",
           title_fontsize=10.5)

# ── 우: 앙상블 확률 분포 분리 ──
probs = oof["앙상블_위험확률"]
for label, color, name in [(0, COLOR["safe"], "안전 그룹 (14,328건)"),
                           (1, COLOR["risk"], "위험 그룹 (46,084건)")]:
    ax2.hist(probs[y == label], bins=50, range=(0, 1), density=True,
             alpha=0.6, color=color, label=name, zorder=3)
ax2.axvline(0.5, color=COLOR["ink900"], linewidth=1.4, linestyle="--", zorder=4)
ax2.text(0.505, 0.72, " 판정 임계 0.5", transform=ax2.get_xaxis_transform(),
         fontsize=10.5, color=COLOR["ink900"], weight="semibold")
ax2.set_title("앙상블 위험확률 분포 — 두 그룹의 분리", loc="left", fontsize=13.5, pad=10)
ax2.set_xlabel("모델이 산출한 위험확률")
ax2.set_yticks([])
ax2.set_yscale("log")
ax2.grid(axis="y")
ax2.legend(frameon=False, fontsize=11, loc="upper center",
           bbox_to_anchor=(0.35, 1.0))
ax2.annotate("안전 중앙값 0.017", xy=(0.03, 0.55), xycoords=("data", "axes fraction"),
             fontsize=11.5, fontweight="bold", color=COLOR["safe"])
ax2.annotate("위험 중앙값 0.992", xy=(0.70, 0.55), xycoords=("data", "axes fraction"),
             fontsize=11.5, fontweight="bold", color=COLOR["risk"])

fig.text(0.5, 0.012,
         "임계 0.5에서 재현율 97.0% · 정밀도 97.6% — 관측 가능한 27개 피처만으로 깡통 위험이 사실상 완전 복원됨 (y축 log)",
         ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.035, 1, 0.89])
save(fig, "fig_EDA_ModelProof")
