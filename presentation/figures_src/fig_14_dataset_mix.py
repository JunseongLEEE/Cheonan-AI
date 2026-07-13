"""Figure 14 — 천안세이프 LLM 학습 데이터셋 구성
심사위원이 3초 안에 파악해야 할 메시지: 6,850개 대화 전부 실측 시스템 값 기반 — 8종 시나리오로 툴 선택·거절·되묻기까지 학습.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

STATS = Path(__file__).resolve().parents[2] / "experiments" / "exp_007_cheonan_llm" / "data" / "dataset_stats.json"
with open(STATS, encoding="utf-8") as f:
    stats = json.load(f)
by = stats["by_intent"]

META = [
    ("simulator",   "매물 위험 진단", "LightGBM+SHAP 실예측 호출", "#EF4444", True),
    ("dong_lookup", "동네 안전 조회", "65개 동 8축 점수 실값", "#F59E0B", True),
    ("kb_qa",       "정책·개념 QA", "HUG·전입신고·체크리스트 (툴 없음)", "#64748B", False),
    ("news",        "뉴스 검색·요약", "각주 인용 형식 학습", "#0EA5E9", True),
    ("recommend",   "예산별 추천", "exp_006 앙상블 실호출", "#10B981", True),
    ("multi_tool",  "복합 질의", "동네 조회+뉴스 순차 2-툴", "#8B5CF6", True),
    ("clarify",     "정보부족 되묻기", "환각 호출 방지 학습", "#94A3B8", False),
    ("out_of_scope","범위 밖 거절", "주식·타지역 등 정중 거절", "#CBD5E1", False),
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=300,
                               gridspec_kw={"width_ratios": [1, 1.25]})
fig.suptitle("천안세이프 LLM 학습 데이터셋 — 8종 시나리오 6,850 대화",
             fontsize=20, fontweight="bold", color=COLOR["ink900"], y=0.99)
fig.text(0.5, 0.925, "툴 출력은 전부 실제 시스템 값 (모델 실예측·실데이터 조회) · 툴을 '안 부르는 법'까지 학습",
         ha="center", fontsize=12, color=COLOR["ink400"], weight="semibold")

# ── 왼쪽: 도넛 ──
sizes = [by[k] for k, *_ in META]
colors = [c for *_, c, _ in META]
wedges, _ = ax1.pie(
    sizes, colors=colors, startangle=90, counterclock=False,
    wedgeprops=dict(width=0.28, edgecolor="white", linewidth=2),
)
ax1.text(0, 0.12, f"{stats['total']:,}", ha="center", fontsize=30,
         fontweight="bold", color=COLOR["ink900"])
ax1.text(0, -0.14, "대화 (train 6,302)", ha="center", fontsize=11, color=COLOR["ink400"])
ax1.text(0, -0.34, f"eval {stats['eval']}건 층화", ha="center", fontsize=10.5,
         color=COLOR["safe"], weight="semibold")
ax1.set_aspect("equal")

# ── 오른쪽: 항목 리스트 (수평 바) ──
ax2.axis("off")
ax2.set_xlim(0, 10); ax2.set_ylim(0, 8.4)
max_n = max(sizes)
for i, (key, title, sub, color, uses_tool) in enumerate(META):
    y = 7.6 - i * 0.98
    n = by[key]
    ax2.add_patch(plt.Circle((0.25, y + 0.12), 0.09, color=color))
    ax2.text(0.55, y + 0.22, title, fontsize=12.5, weight="semibold", color=COLOR["ink900"])
    tag = "TOOL" if uses_tool else "직접답변"
    ax2.text(3.15, y + 0.22, tag, fontsize=8.5, weight="bold",
             color="white" if uses_tool else COLOR["ink600"],
             bbox=dict(boxstyle="round,pad=0.25",
                       facecolor="#8B5CF6" if uses_tool else COLOR["line"],
                       edgecolor="none"))
    ax2.text(0.55, y - 0.12, sub, fontsize=9.5, color=COLOR["ink400"])
    # 미니 바
    bar_x, bar_w = 4.6, 3.6
    ax2.add_patch(FancyBboxPatch((bar_x, y), bar_w, 0.22,
                                 boxstyle="round,pad=0,rounding_size=0.08",
                                 facecolor="#F1F5F9", edgecolor="none"))
    ax2.add_patch(FancyBboxPatch((bar_x, y), bar_w * n / max_n, 0.22,
                                 boxstyle="round,pad=0,rounding_size=0.08",
                                 facecolor=color, edgecolor="none"))
    ax2.text(bar_x + bar_w + 0.2, y + 0.11, f"{n:,}", va="center",
             fontsize=11, fontweight="bold", color=COLOR["ink900"])

fig.text(0.5, 0.015,
         "금액 표기 다양화(1억2천/5천만 원/8000만원) · 인자 생략 시 기본값 학습 · assistant 턴만 loss 계산",
         ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

plt.tight_layout(rect=[0, 0.04, 1, 0.90])
save(fig, "fig_LLM_Dataset")
