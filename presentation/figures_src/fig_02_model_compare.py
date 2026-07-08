"""Figure 2 — 모델 실험 히스토리 (LightGBM 실험 5개)
심사위원이 3초 안에 파악해야 할 메시지: 5번의 실험을 거쳐 AUC를 0.9721 → 0.9893로 끌어올렸고, exp_004가 최적 모델.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle

from viz_style import apply_style, save, COLOR

apply_style()

# ── 데이터 (data_facts.md §3-3) ──
ROWS = [
    ("exp_001", "baseline_lgbm",    0.9721, 0.9412, "기본 피처 (전세가율·면적·노후도)"),
    ("exp_002", "no_trade_price",   0.9683, 0.9385, "실거래가 제외 (데이터 누수 제거)"),
    ("exp_003", "building_features",0.9856, 0.9612, "건물 상세(구조/내진) 추가"),
    ("exp_004", "threshold_80",     0.9893, 0.9690, "위험 임계 90→80, 경계 학습 강화"),
    ("exp_005", "expanded_data",    0.9871, 0.9648, "학습 데이터 확장·샘플링 튜닝"),
]
BEST_IDX = 3

auc_max = max(r[2] for r in ROWS)
auc_min = min(r[2] for r in ROWS)
f1_max  = max(r[3] for r in ROWS)
f1_min  = min(r[3] for r in ROWS)

# baseline 기준 Δ
BASE_AUC = ROWS[0][2]

# ── 캔버스 16:9 ──
fig = plt.figure(figsize=(16, 9), dpi=300)
gs = fig.add_gridspec(1, 2, width_ratios=[3.1, 1.0], wspace=0.18)
ax  = fig.add_subplot(gs[0])   # 표
axL = fig.add_subplot(gs[1])   # 라인 차트
# 라인차트 제목/x축 라벨 잘림 방지 — 상하 여백 확보
fig.subplots_adjust(top=0.90, bottom=0.13, left=0.045, right=0.97)

# ── 좌: 표 ──
ax.set_xlim(0, 12); ax.set_ylim(0, 9); ax.axis("off")

ax.text(0, 8.5, "모델 실험 히스토리",
        fontsize=22, fontweight="bold", color=COLOR["ink900"])
ax.text(0, 8.05, "LightGBM 깡통전세 분류기 · 5번의 반복 학습",
        fontsize=12.5, color=COLOR["ink400"], weight="semibold")

# 컬럼 위치
col_x = {"id": 0.05, "name": 1.35, "auc": 4.4, "auc_bar": 5.20,
         "delta": 6.7, "f1": 7.7, "f1_bar": 8.5, "note": 10.0}

# 헤더 (밑줄 스타일)
header_y = 7.35
headers = [("실험 ID", "id"), ("실험명", "name"),
           ("AUC ↑", "auc"), ("(0.90~1.00)", "auc_bar"),
           ("Δ vs base", "delta"),
           ("F1 ↑", "f1"), ("(0.90~1.00)", "f1_bar"),
           ("핵심 변경점", "note")]
for text, key in headers:
    if text:
        # 스케일 안내는 옅은 회색으로 (헤더 텍스트와 구분)
        is_scale_hint = text.startswith("(")
        ax.text(col_x[key], header_y, text,
                fontsize=9.5 if is_scale_hint else 11,
                color=COLOR["ink400"] if is_scale_hint else COLOR["ink600"],
                weight="normal" if is_scale_hint else "semibold")
# 헤더 밑줄
ax.plot([0, 12], [header_y - 0.18, header_y - 0.18],
        color=COLOR["ink900"], linewidth=1.2)

# 행
row_h = 1.05
for i, (eid, name, auc, f1, note) in enumerate(ROWS):
    y = header_y - 0.6 - (i + 1) * row_h + row_h
    is_best = (i == BEST_IDX)

    # 최고행 강조: soft 배경 + 좌측 4px 액센트
    if is_best:
        ax.add_patch(Rectangle((-0.05, y - 0.42), 12.1, row_h - 0.05,
                               facecolor=COLOR["soft"], edgecolor="none", zorder=1))
        ax.add_patch(Rectangle((-0.05, y - 0.42), 0.08, row_h - 0.05,
                               facecolor=COLOR["safe"], edgecolor="none", zorder=2))

    # 셀 값
    text_color = COLOR["ink900"]
    weight = "semibold" if is_best else "normal"

    ax.text(col_x["id"], y, eid, fontsize=11.5, color=text_color,
            weight=weight, va="center", zorder=3)
    ax.text(col_x["name"], y, name, fontsize=11.5,
            color=(COLOR["ink900"]),
            weight="bold" if is_best else "semibold", va="center", zorder=3)

    # AUC 값
    ax.text(col_x["auc"], y, f"{auc:.4f}",
            fontsize=11.5, color=COLOR["safe"] if is_best else COLOR["ink900"],
            weight="bold" if is_best else "semibold", va="center", zorder=3)
    # AUC mini bar (0.90~1.00 범위 — 절대 스케일 근접, 왜곡 최소화)
    bar_w = 1.35
    AUC_MIN, AUC_MAX = 0.90, 1.00
    scale = (auc - AUC_MIN) / (AUC_MAX - AUC_MIN)
    scale = max(0.05, min(1.0, scale))
    ax.add_patch(Rectangle((col_x["auc_bar"], y - 0.10), bar_w, 0.20,
                           facecolor=COLOR["line"], edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((col_x["auc_bar"], y - 0.10), bar_w * scale, 0.20,
                           facecolor=COLOR["safe"] if is_best else COLOR["ink400"],
                           edgecolor="none", zorder=4))

    # Δ vs baseline
    delta = auc - BASE_AUC
    d_col = COLOR["safe"] if delta > 0 else (COLOR["risk"] if delta < 0 else COLOR["ink400"])
    d_sign = "+" if delta >= 0 else ""
    d_txt = "base" if i == 0 else f"{d_sign}{delta:.4f}"
    ax.text(col_x["delta"], y, d_txt,
            fontsize=11, color=d_col, weight="semibold", va="center", zorder=3)

    # F1 값
    ax.text(col_x["f1"], y, f"{f1:.4f}",
            fontsize=11.5, color=COLOR["safe"] if is_best else COLOR["ink900"],
            weight="bold" if is_best else "semibold", va="center", zorder=3)
    # F1 mini bar (0.90~1.00 범위 — AUC 바와 동일 스케일)
    bar_w2 = 1.35
    F1_MIN, F1_MAX = 0.90, 1.00
    scale2 = (f1 - F1_MIN) / (F1_MAX - F1_MIN)
    scale2 = max(0.05, min(1.0, scale2))
    ax.add_patch(Rectangle((col_x["f1_bar"], y - 0.10), bar_w2, 0.20,
                           facecolor=COLOR["line"], edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((col_x["f1_bar"], y - 0.10), bar_w2 * scale2, 0.20,
                           facecolor=COLOR["safe"] if is_best else COLOR["ink400"],
                           edgecolor="none", zorder=4))

    # 노트
    ax.text(col_x["note"], y, note,
            fontsize=10.5, color=COLOR["ink600"], va="center", zorder=3)

    # BEST pill
    if is_best:
        pill_x, pill_y = 3.72, y - 0.20
        ax.add_patch(FancyBboxPatch((pill_x, pill_y), 0.55, 0.40,
                                    boxstyle="round,pad=0,rounding_size=0.18",
                                    facecolor=COLOR["safe"], edgecolor="none", zorder=4))
        ax.text(pill_x + 0.275, pill_y + 0.20, "BEST",
                ha="center", va="center", fontsize=9,
                color="white", weight="bold", zorder=5)

    # 행 구분선 (얇게)
    if i < len(ROWS) - 1:
        ax.plot([-0.05, 12.05], [y - 0.53, y - 0.53],
                color=COLOR["line"], linewidth=0.5, zorder=2)

# ── 우: iteration line chart ──
axL.set_facecolor("white")
xs = np.arange(1, len(ROWS) + 1)
aucs = [r[2] for r in ROWS]
axL.plot(xs, aucs, color=COLOR["ink400"], linewidth=1.6, linestyle="--", zorder=2)
# best 강조
for i, v in enumerate(aucs):
    is_best = (i == BEST_IDX)
    axL.scatter([xs[i]], [v], s=110 if is_best else 55,
                color=COLOR["safe"] if is_best else COLOR["ink600"],
                edgecolor="white", linewidth=1.5, zorder=4)
axL.set_xticks(xs)
axL.set_xticklabels([f"e0{i}" for i in xs], fontsize=10)
axL.set_ylim(0.965, 0.995)
axL.set_yticks([0.97, 0.98, 0.99])
axL.set_yticklabels(["0.97", "0.98", "0.99"], fontsize=9)
axL.grid(axis="y", color="#F1F5F9", linewidth=0.8)
axL.spines["left"].set_color(COLOR["line"])
axL.spines["bottom"].set_color(COLOR["line"])
axL.set_title("AUC 추이", fontsize=13, color=COLOR["ink900"], loc="left", pad=10)

# best annotation
axL.annotate(f"{aucs[BEST_IDX]:.4f}",
             xy=(xs[BEST_IDX], aucs[BEST_IDX]),
             xytext=(xs[BEST_IDX] - 0.5, aucs[BEST_IDX] + 0.004),
             fontsize=10, color=COLOR["safe"], weight="bold",
             arrowprops=dict(arrowstyle="-", color=COLOR["safe"], linewidth=1))

save(fig, "fig_Model_Compare")
