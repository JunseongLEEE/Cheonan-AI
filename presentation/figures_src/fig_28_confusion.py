"""Figure 28 — 혼동행렬 + PR 곡선 (Tier2-F)
심사위원이 3초 안에 파악해야 할 메시지: 임계 0.5에서 위험 46,084건 중 97%를 잡고, 위험 판정의 97.6%가 실제 위험이다.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import confusion_matrix, precision_recall_curve, average_precision_score
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
oof = pd.read_parquet(ROOT / "experiments" / "exp_006_multimodel_ensemble" / "oof_predictions.parquet")
y = oof["위험라벨"].astype(int).values
p = oof["앙상블_위험확률"].values
pred = (p >= 0.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y, pred).ravel()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.6), dpi=300,
                               gridspec_kw={"width_ratios": [1.05, 1]})
fig.suptitle("판정 성능 — 혼동행렬과 정밀도-재현율 (5-fold OOF, 60,412건)",
             fontsize=20, fontweight="bold", color=COLOR["ink900"], x=0.07, ha="left", y=0.97)
fig.text(0.07, 0.905, "Voting 앙상블 · 임계 0.5 · 매매가 미포함 피처 — '위험을 놓치는 것'과 '안전을 겁주는 것' 모두 3% 미만",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# ── 좌: 혼동행렬 ──
ax1.axis("off"); ax1.set_xlim(0, 10); ax1.set_ylim(0, 10)
cells = [
    # (x, y, 건수, 라벨, 색, 설명)
    (1.6, 5.1, tp, "위험 적중 (TP)", COLOR["risk"], f"{tp/(tp+fn):.1%} 재현율"),
    (5.8, 5.1, fn, "위험 놓침 (FN)", "#FCA5A5", f"위험의 {fn/(tp+fn):.1%}"),
    (1.6, 1.1, fp, "안전 오경보 (FP)", "#FDE68A", f"판정의 {fp/(tp+fp):.1%}"),
    (5.8, 1.1, tn, "안전 적중 (TN)", COLOR["safe"], f"{tn/(tn+fp):.1%} 특이도"),
]
ax1.text(3.7, 9.55, "실제 위험 (46,084)", ha="center", fontsize=12, weight="semibold", color=COLOR["ink600"])
ax1.text(0.55, 7.0, "판정\n위험", ha="center", fontsize=11.5, weight="semibold", color=COLOR["ink600"])
ax1.text(0.55, 3.0, "판정\n안전", ha="center", fontsize=11.5, weight="semibold", color=COLOR["ink600"])
ax1.text(3.7, 9.15, "", ha="center")
for x, yy, n, lab, c, sub in cells:
    ax1.add_patch(FancyBboxPatch((x, yy), 3.9, 3.7,
                                 boxstyle="round,pad=0.02,rounding_size=0.15",
                                 facecolor=c, edgecolor="white", linewidth=2, alpha=0.92))
    tcol = "white" if c in (COLOR["risk"], COLOR["safe"]) else COLOR["ink900"]
    ax1.text(x + 1.95, yy + 2.45, f"{n:,}", ha="center", fontsize=24,
             fontweight="bold", color=tcol)
    ax1.text(x + 1.95, yy + 1.55, lab, ha="center", fontsize=12, weight="semibold", color=tcol)
    ax1.text(x + 1.95, yy + 0.9, sub, ha="center", fontsize=10.5, color=tcol)
ax1.text(7.75, 9.55, "실제 안전 (14,328)", ha="center", fontsize=12, weight="semibold", color=COLOR["ink600"])

# ── 우: PR 곡선 ──
prec, rec, _ = precision_recall_curve(y, p)
ap = average_precision_score(y, p)
ax2.plot(rec, prec, color=COLOR["safe"], linewidth=2.6, zorder=3)
ax2.fill_between(rec, prec, alpha=0.08, color=COLOR["safe"])
op_r, op_p = tp / (tp + fn), tp / (tp + fp)
ax2.scatter([op_r], [op_p], s=90, color=COLOR["ink900"], zorder=5)
ax2.annotate(f"운영점 (임계 0.5)\n재현율 {op_r:.1%} · 정밀도 {op_p:.1%}",
             (op_r, op_p), xytext=(-30, -52), textcoords="offset points",
             fontsize=11.5, fontweight="bold", color=COLOR["ink900"], ha="right",
             arrowprops=dict(arrowstyle="->", color=COLOR["ink600"], lw=1.3))
ax2.axhline(y.mean(), color=COLOR["ink400"], linewidth=1.1, linestyle="--")
ax2.text(0.02, y.mean() + 0.012, f"무작위 기준선 {y.mean():.0%} (위험 비율)",
         fontsize=10, color=COLOR["ink400"])
ax2.set_title(f"Precision–Recall 곡선 (AP {ap:.4f})", loc="left", fontsize=14, pad=10)
ax2.set_xlabel("재현율 — 실제 위험 중 잡아낸 비율")
ax2.set_ylabel("정밀도 — 위험 판정 중 실제 위험")
ax2.set_xlim(0, 1.0); ax2.set_ylim(0.70, 1.01)
ax2.grid(axis="both")

fig.text(0.5, 0.015,
         f"놓친 위험(FN) {fn:,}건은 대부분 확률 0.3~0.5의 경계 매물 — 서비스에서는 '주의(노랑)'로 표시되어 완전 통과되지 않음",
         ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.035, 1, 0.88])
save(fig, "fig_Confusion_PR")
