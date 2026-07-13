"""Figure 15 — 천안세이프 LLM 학습 곡선
심사위원이 3초 안에 파악해야 할 메시지: loss가 안정적으로 수렴 — 과적합 없이 도메인 툴콜 능력을 습득.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib.pyplot as plt
from viz_style import apply_style, save, COLOR

apply_style()

HIST = Path(__file__).resolve().parents[2] / "experiments" / "exp_007_cheonan_llm" / "train_history.json"
with open(HIST, encoding="utf-8") as f:
    hist = json.load(f)

train_pts = [(h["step"], h["loss"]) for h in hist if "loss" in h and "eval_loss" not in h]
eval_pts = [(h["step"], h["eval_loss"]) for h in hist if "eval_loss" in h]

fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
fig.suptitle("QLoRA 파인튜닝 학습 곡선 — Qwen2.5-7B · RTX 3090×2",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.123, ha="left", y=0.97)
fig.text(0.123, 0.905, "assistant 턴만 loss 계산 · 4-bit NF4 · LoRA r=16 · effective batch 32 · log 스케일",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

xs, ys = zip(*train_pts)
ax.plot(xs, ys, color=COLOR["caution"], linewidth=2.2, label="train loss", zorder=3)
if eval_pts:
    ex, ey = zip(*eval_pts)
    ax.plot(ex, ey, color=COLOR["safe"], linewidth=2.4, marker="o", markersize=6,
            label="eval loss", zorder=4)
    ax.annotate(f"최종 eval {ey[-1]:.4f}", (ex[-1], ey[-1]),
                textcoords="offset points", xytext=(-6, 16),
                fontsize=12.5, fontweight="bold", color=COLOR["safe"], ha="right")
    ax.annotate(f"step 50: {ey[0]:.3f}", (ex[0], ey[0]),
                textcoords="offset points", xytext=(12, 4),
                fontsize=11, color=COLOR["ink400"])

ax.set_yscale("log")
ax.set_xlabel("학습 스텝")
ax.set_ylabel("loss (log)")
ax.grid(axis="y")
ax.legend(frameon=False, fontsize=12.5, loc="upper right")

plt.tight_layout(rect=[0, 0.01, 1, 0.87])
save(fig, "fig_LLM_Loss")
