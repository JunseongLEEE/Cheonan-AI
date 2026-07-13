"""Figure 16 — Tool-Calling 정확도: 베이스 vs 파인튜닝
심사위원이 3초 안에 파악해야 할 메시지: 파인튜닝으로 툴 선택·인자 추출이 크게 개선 — 도메인 특화의 실증 효과.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from viz_style import apply_style, save, COLOR

apply_style()

EVAL_DIR = Path(__file__).resolve().parents[2] / "experiments" / "exp_007_cheonan_llm" / "eval"
with open(EVAL_DIR / "toolcall_base.json", encoding="utf-8") as f:
    base = json.load(f)
with open(EVAL_DIR / "toolcall_tuned.json", encoding="utf-8") as f:
    tuned = json.load(f)

METRICS = [
    ("decision_acc", "툴 호출 여부 판단"),
    ("name_acc", "툴 이름 선택"),
    ("args_valid_rate", "인자 JSON 유효율"),
    ("args_f1", "인자 추출 F1"),
]

labels = [l for _, l in METRICS]
base_v = [base.get(k) or 0 for k, _ in METRICS]
tuned_v = [tuned.get(k) or 0 for k, _ in METRICS]

x = np.arange(len(labels))
w = 0.36

fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
fig.suptitle("Tool-Calling 정확도 — Qwen2.5-7B 베이스 vs 천안세이프 파인튜닝",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.123, ha="left", y=0.97)
fig.text(0.123, 0.905,
         f"held-out {tuned['n_eval']}건 · 동일 프롬프트/툴 스키마 · greedy decoding",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

b1 = ax.bar(x - w / 2, base_v, w, color=COLOR["ink400"], label="베이스 (zero-shot)", zorder=3)
b2 = ax.bar(x + w / 2, tuned_v, w, color=COLOR["safe"], label="천안세이프 (파인튜닝)", zorder=3)

for bars, vals in [(b1, base_v), (b2, tuned_v)]:
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.015, f"{v:.1%}",
                ha="center", fontsize=11.5,
                fontweight="bold" if vals is tuned_v else "normal",
                color=COLOR["ink900"] if vals is tuned_v else COLOR["ink600"], zorder=4)

# 개선폭 주석
for i, (bv, tv) in enumerate(zip(base_v, tuned_v)):
    if tv > bv:
        ax.annotate(f"+{(tv - bv) * 100:.0f}pp", (x[i] + w / 2, tv + 0.065),
                    ha="center", fontsize=11, fontweight="bold", color=COLOR["safe"])

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=12.5)
ax.set_ylim(0, 1.16)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.grid(axis="y")
ax.legend(frameon=False, fontsize=12.5, loc="lower right",
          bbox_to_anchor=(1.0, 1.0), ncol=2)

plt.tight_layout(rect=[0, 0.01, 1, 0.87])
save(fig, "fig_LLM_Eval")
