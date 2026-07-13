"""Figure 18 — EDA 근거 ②: 관측 가능한 피처의 판별 신호
심사위원이 3초 안에 파악해야 할 메시지: 매매가 없이도 위험/안전 그룹이 피처 분포에서 갈라진다 — 단독 AUC 최고 0.75, 결합 시 0.99.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
oof = pd.read_parquet(ROOT / "experiments" / "exp_006_multimodel_ensemble" / "oof_predictions.parquet")
bldg = pd.read_parquet(ROOT / "data" / "processed" / "building_residential.parquet")

df = oof.copy()
df["건물연령"] = df["거래일"].dt.year - df["건축년도"]
df.loc[(df["건물연령"] < 0) | (df["건물연령"] > 100), "건물연령"] = np.nan
df["㎡당_보증금"] = df["보증금_만원"] / df["전용면적_㎡"].replace(0, np.nan)
df["보증금_동평균_비율"] = df["보증금_만원"] / df.groupby("법정동명")["보증금_만원"].transform("mean")
dong_old = bldg.groupby("법정동명")["건물연령"].apply(lambda x: (x >= 25).mean())
df["동_노후비율"] = df["법정동명"].map(dong_old)
y = df["위험라벨"].astype(int)

PANELS = [
    ("건물연령", "건물연령 (년)", (0, 45)),
    ("㎡당_보증금", "㎡당 보증금 (만원/㎡)", (0, 700)),
    ("보증금_동평균_비율", "동 평균 대비 보증금 배율", (0.2, 2.2)),
    ("동_노후비율", "동네 노후건물 비율", (0, 0.75)),
]

fig, axes = plt.subplots(2, 2, figsize=(15, 8.5), dpi=300)
fig.suptitle("근거 ② 판별 신호의 존재 — 위험 vs 안전 그룹의 피처 분포",
             fontsize=20, fontweight="bold", color=COLOR["ink900"],
             x=0.07, ha="left", y=0.985)
fig.text(0.07, 0.925,
         "매매가·전세가율을 쓰지 않은 관측 가능 피처만으로 두 그룹이 분리 — 계약 전 매물에도 그대로 적용 가능",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

for ax, (feat, xlabel, xlim) in zip(axes.flat, PANELS):
    m = df[feat].notna()
    auc = roc_auc_score(y[m], df.loc[m, feat])
    auc = max(auc, 1 - auc)
    for label, color, name in [(0, COLOR["safe"], "안전 (전세가율≤60%)"),
                               (1, COLOR["risk"], "위험 (전세가율≥80%)")]:
        vals = df.loc[m & (y == label), feat].clip(*xlim)
        ax.hist(vals, bins=48, range=xlim, density=True, alpha=0.55,
                color=color, label=name, zorder=3)
        ax.axvline(vals.median(), color=color, linewidth=1.8, linestyle="--", zorder=4)
    ax.set_xlabel(xlabel, fontsize=11.5)
    ax.set_yticks([])
    ax.set_xlim(*xlim)
    ax.grid(axis="y")
    ax.text(0.985, 0.90, f"단독 AUC {auc:.2f}", transform=ax.transAxes,
            ha="right", fontsize=12.5, fontweight="bold",
            color=COLOR["ink900"],
            bbox=dict(boxstyle="round,pad=0.35", facecolor=COLOR["soft"],
                      edgecolor=COLOR["line"]))

axes[0, 0].legend(frameon=False, fontsize=11, loc="upper right",
                  bbox_to_anchor=(0.995, 0.82))

fig.text(0.5, 0.012,
         "점선 = 그룹별 중앙값 · 개별 신호(0.53~0.75)는 약하지만 27개 피처의 비선형 결합으로 AUC 0.99 달성 (근거 ④)",
         ha="center", fontsize=11.5, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.035, 1, 0.90])
save(fig, "fig_EDA_Signal")
