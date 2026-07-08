"""
PPT 오프라인 그림 생성 스크립트 (Light 테마 통일).
─────────────────────────────────────────
출력: presentation/figures/*.png
    - fig_SHAP_Top5.png       상위 5개 SHAP 피처 중요도
    - fig_Radar_Wonseong.png  원성동 vs 천안 평균 8축 레이더
    - fig_Grade_Donut.png     신호등 분포 도넛
    - fig_Pipeline.png        데이터 파이프라인 다이어그램
    - fig_Model_Compare.png   실험 비교 표(이미지)
    - fig_Problem_Stats.png   문제 통계 인포그래픽
"""
from __future__ import annotations
from pathlib import Path
import json

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

# ── 스타일 (light) ──
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.edgecolor": "#1a1f2e",
    "axes.labelcolor": "#1a1f2e",
    "xtick.color": "#1a1f2e",
    "ytick.color": "#1a1f2e",
    "text.color": "#1a1f2e",
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
})
BLUE = "#2E86DE"
GREEN = "#26C281"
YELLOW = "#F6C244"
RED = "#E74C3C"
NAVY = "#1a1f2e"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "figures"
OUT.mkdir(exist_ok=True, parents=True)


def fig_shap_top5():
    df = pd.read_csv(ROOT / "experiments/exp_004_threshold_80/shap/shap_importance.csv")
    top = df.head(5).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=180)
    bars = ax.barh(top["feature"], top["mean_abs_shap"], color=BLUE, edgecolor="none")
    for b, v in zip(bars, top["mean_abs_shap"]):
        ax.text(v + 0.05, b.get_y() + b.get_height() / 2,
                f"{v:.2f}", va="center", fontsize=11, color=NAVY)
    ax.set_xlabel("mean |SHAP value|  (모델 예측 기여도)", fontsize=11)
    ax.set_title("깡통전세 분류기 — 상위 5개 피처 중요도 (SHAP)",
                 fontsize=13, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT / "fig_SHAP_Top5.png", dpi=180)
    plt.close()
    print("✓ fig_SHAP_Top5.png")


def fig_radar_wonseong():
    df = pd.read_parquet(ROOT / "data/processed/dong_safety_score.parquet")
    axes = ["금융안전_점수", "건물노후_점수", "치안_점수", "편의시설_점수",
            "환경_점수", "침수위험_점수", "소방_점수", "교통_점수"]
    labels = ["금융안전", "건물노후", "치안", "편의시설", "환경", "침수위험", "소방", "교통"]
    dong = df[df["법정동명"] == "원성동"].iloc[0]
    avg = df[axes].mean()
    v_dong = [float(dong[a]) for a in axes]
    v_avg = [float(avg[a]) for a in axes]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    v_dong += v_dong[:1]; v_avg += v_avg[:1]; angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.8, 6.8), dpi=180, subplot_kw=dict(polar=True))
    ax.plot(angles, v_avg, color="#94a3b8", linewidth=2, label="천안시 65개 동 평균")
    ax.fill(angles, v_avg, color="#94a3b8", alpha=0.15)
    ax.plot(angles, v_dong, color=RED, linewidth=2.5, label="원성동 (위험)")
    ax.fill(angles, v_dong, color=RED, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=9, color="#64748b")
    ax.grid(alpha=0.3)
    ax.set_title("원성동 vs 천안시 평균 — 8축 안전 프로파일", fontsize=13,
                 fontweight="bold", pad=22)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=10, frameon=False)
    plt.tight_layout()
    plt.savefig(OUT / "fig_Radar_Wonseong.png", dpi=180, bbox_inches="tight")
    plt.close()
    print("✓ fig_Radar_Wonseong.png")


def fig_grade_donut():
    df = pd.read_parquet(ROOT / "data/processed/dong_safety_score.parquet")
    counts = df["신호등"].value_counts()
    order = ["초록", "노랑", "빨강"]
    vals = [int(counts.get(k, 0)) for k in order]
    colors = [GREEN, YELLOW, RED]
    labels = [f"{k}  {v}개 동" for k, v in zip(order, vals)]

    fig, ax = plt.subplots(figsize=(6.5, 5.2), dpi=180)
    wedges, _ = ax.pie(vals, colors=colors, startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=3))
    ax.text(0, 0.15, f"{sum(vals)}", ha="center", va="center",
            fontsize=42, fontweight="bold", color=NAVY)
    ax.text(0, -0.22, "총 동네", ha="center", va="center", fontsize=13, color="#64748b")
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.05, 0.5),
              fontsize=12, frameon=False)
    ax.set_title("천안시 65개 동 안전 신호등 분포", fontsize=13,
                 fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(OUT / "fig_Grade_Donut.png", dpi=180, bbox_inches="tight")
    plt.close()
    print("✓ fig_Grade_Donut.png")


def fig_pipeline():
    fig, ax = plt.subplots(figsize=(14, 5.5), dpi=180)
    ax.set_xlim(0, 14); ax.set_ylim(0, 5.5); ax.axis("off")

    boxes = [
        (0.3,  "1. 수집",         "공공 API + 공공데이터포털\n· 실거래가·전세  · 건축물대장\n· 지진관측  · SGIS 통계\n· 상권/치안/소방/교통"),
        (3.7,  "2. ETL",          "정제 · 이상치 · 조인\n· 법정동 매핑\n· 전세가율·건물연령\n· 65개 동 안전점수"),
        (7.1,  "3. 모델링",       "LightGBM 분류기 (exp_004)\nAUC 0.9893 / F1 0.9690\nSHAP 설명력\nIsolation Forest"),
        (10.5, "4. 서비스",       "Streamlit 인터랙티브 웹\n· 매물 시뮬레이터\n· 신호등 지도\n· RAG 챗봇 (뉴스 근거)"),
    ]
    palette = [BLUE, "#3D9970", "#8E44AD", "#E67E22"]
    W, H, Y = 3.1, 2.6, 1.4
    for i, (x, title, body) in enumerate(boxes):
        rect = patches.FancyBboxPatch((x, Y), W, H,
                                      boxstyle="round,pad=0.02,rounding_size=0.15",
                                      linewidth=2, edgecolor=palette[i],
                                      facecolor="white")
        ax.add_patch(rect)
        ax.text(x + W/2, Y + H - 0.35, title, ha="center", va="center",
                fontsize=14, fontweight="bold", color=palette[i])
        ax.text(x + W/2, Y + H/2 - 0.35, body, ha="center", va="center",
                fontsize=10.5, color=NAVY, linespacing=1.6)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x + W + 0.28, Y + H/2), xytext=(x + W + 0.02, Y + H/2),
                        arrowprops=dict(arrowstyle="->", color="#64748b", lw=2))

    ax.text(7, 4.7, "데이터 파이프라인 — 공공데이터 100% × 재현가능",
            ha="center", fontsize=15, fontweight="bold", color=NAVY)
    ax.text(7, 0.7, "10만+ 실거래 · 65개 법정동 · 대회 규정 100% 준수",
            ha="center", fontsize=11, color="#64748b", style="italic")
    plt.tight_layout()
    plt.savefig(OUT / "fig_Pipeline.png", dpi=180, bbox_inches="tight")
    plt.close()
    print("✓ fig_Pipeline.png")


def fig_model_compare():
    rows = [
        ("exp_001", "baseline_lgbm",       0.9721, 0.9412, "기본 피처 (전세가율, 면적, 노후도)"),
        ("exp_002", "no_trade_price",      0.9683, 0.9385, "실거래가 컬럼 제외 (누수 제거)"),
        ("exp_003", "building_features",   0.9856, 0.9612, "건물 상세 피처 추가 (구조/내진)"),
        ("exp_004", "threshold_80 ★",      0.9893, 0.9690, "위험 임계 90→80, 경계 학습 강화"),
        ("exp_005", "expanded_data",       0.9871, 0.9648, "학습 데이터 확장 (샘플링 튜닝)"),
    ]
    fig, ax = plt.subplots(figsize=(12, 4.2), dpi=180)
    ax.axis("off")

    ax.text(6, 3.9, "모델 실험 히스토리 — LightGBM 깡통전세 분류기",
            ha="center", fontsize=14, fontweight="bold", color=NAVY)

    headers = ["ID", "실험명", "AUC", "F1", "핵심 변경점"]
    x_pos = [0.4, 1.9, 5.6, 6.8, 8.0]
    y_h = 3.15
    for x, h in zip(x_pos, headers):
        ax.text(x, y_h, h, fontsize=11, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=NAVY, edgecolor="none"))

    for i, r in enumerate(rows):
        y = 2.5 - i * 0.5
        is_best = "★" in r[1]
        bg = "#EAF3FD" if is_best else ("white" if i % 2 == 0 else "#F5F7FA")
        ax.add_patch(patches.Rectangle((0.2, y - 0.2), 11.4, 0.45,
                                       facecolor=bg, edgecolor="none"))
        ax.text(x_pos[0], y, r[0], fontsize=10.5, color=NAVY, va="center")
        ax.text(x_pos[1], y, r[1], fontsize=10.5,
                fontweight="bold" if is_best else "normal",
                color=BLUE if is_best else NAVY, va="center")
        ax.text(x_pos[2], y, f"{r[2]:.4f}", fontsize=10.5,
                fontweight="bold" if is_best else "normal",
                color=GREEN if is_best else NAVY, va="center")
        ax.text(x_pos[3], y, f"{r[3]:.4f}", fontsize=10.5,
                fontweight="bold" if is_best else "normal",
                color=GREEN if is_best else NAVY, va="center")
        ax.text(x_pos[4], y, r[4], fontsize=10, color=NAVY, va="center")

    ax.set_xlim(0, 12); ax.set_ylim(-0.2, 4.2)
    plt.tight_layout()
    plt.savefig(OUT / "fig_Model_Compare.png", dpi=180, bbox_inches="tight")
    plt.close()
    print("✓ fig_Model_Compare.png")


def fig_problem_stats():
    fig, ax = plt.subplots(figsize=(13, 5.5), dpi=180)
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.5); ax.axis("off")

    ax.text(6.5, 4.9, "천안시 청년 주거 안전 — 위기의 3가지 숫자",
            ha="center", fontsize=15, fontweight="bold", color=NAVY)
    ax.text(6.5, 4.35, "청년 인구는 늘어나는데, 안전한 자취방 정보는 부재",
            ha="center", fontsize=11.5, color="#64748b", style="italic")

    stats = [
        (2.1, "19.7만명",  "18~39세 청년 인구",       "천안시 전체의 30%",              BLUE),
        (6.5, "86%",       "청년 무주택 비율",         "10명 중 8~9명이 세입자",        YELLOW),
        (10.9,"288세대",   "전세사기 피해 (2024)",    "피해액 145억원 · 원성동 집중",   RED),
    ]
    for x, big, title, sub, color in stats:
        ax.add_patch(patches.FancyBboxPatch((x - 1.6, 1.2), 3.2, 2.8,
                                            boxstyle="round,pad=0.02,rounding_size=0.2",
                                            linewidth=2, edgecolor=color, facecolor="white"))
        ax.text(x, 3.2, big, ha="center", fontsize=30, fontweight="bold", color=color)
        ax.text(x, 2.35, title, ha="center", fontsize=13, fontweight="bold", color=NAVY)
        ax.text(x, 1.75, sub, ha="center", fontsize=10.5, color="#64748b")

    ax.text(6.5, 0.5, "→ 도시 전체 선제 스캔 + 개인 매물 위험도 예측 = 우리의 솔루션",
            ha="center", fontsize=12, color=NAVY, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig_Problem_Stats.png", dpi=180, bbox_inches="tight")
    plt.close()
    print("✓ fig_Problem_Stats.png")


if __name__ == "__main__":
    fig_shap_top5()
    fig_radar_wonseong()
    fig_grade_donut()
    fig_pipeline()
    fig_model_compare()
    fig_problem_stats()
    print(f"\n완료 → {OUT}")
