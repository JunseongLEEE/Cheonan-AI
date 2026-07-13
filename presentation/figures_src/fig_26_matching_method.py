"""Figure 26 — 전세↔매매 실거래 매칭 방법론 (Tier1-D)
심사위원이 3초 안에 파악해야 할 메시지: 전세가율 라벨은 동일 단지·동일 월의 실거래끼리 결합해 만든다 — 추정치가 아니다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

STEPS = [
    ("01", "매매 실거래 수집", "270,307건 (2019~2026)",
     ["국토부 실거래 API 4종", "단지·월별 거래금액 중앙값", "이상치에 강한 중앙값 채택"], "#0EA5E9"),
    ("02", "전세 실거래 필터", "전월세 371,612 → 전세 188,184건",
     ["전월세 API 4종 수집", "월세 매물 제외 (전세만)", "단지·월별 보증금 중앙값"], "#8B5CF6"),
    ("03", "3중 키 정확 결합", "(법정동, 단지명, 연월)",
     ["같은 단지 · 같은 달만 매칭", "면적대·연식 상이 단지 미혼입", "전세가율 = 전세금 ÷ 매매가"], "#F59E0B"),
    ("04", "개별 거래 라벨링", "102,671건 (매칭률 54.6%)",
     ["단지·월 전세가율을 개별 거래에 부여", "≥80% 위험 / ≤60% 안전", "미매칭 46%는 예측 대상으로만"], "#10B981"),
]

fig, ax = plt.subplots(figsize=(16, 6.6), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 6.6); ax.axis("off")

ax.text(8, 6.15, "전세가율 라벨 구축 — 전세 ↔ 매매 실거래 매칭 방법론",
        ha="center", fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 5.70, "감정가·호가·추정 시세를 쓰지 않는다 — 실제 체결된 거래끼리만 결합",
        ha="center", fontsize=12, color=COLOR["ink400"], weight="semibold")

card_w, card_h, gap = 3.55, 3.15, 0.35
start_x = (16 - (4 * card_w + 3 * gap)) / 2
y_card = 1.55

for i, (no, title, stat, items, accent) in enumerate(STEPS):
    x = start_x + i * (card_w + gap)
    ax.add_patch(FancyBboxPatch((x, y_card), card_w, card_h,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                linewidth=1.0, edgecolor=COLOR["line"], facecolor="white"))
    ax.add_patch(patches.Rectangle((x + 0.14, y_card + card_h - 0.08), card_w - 0.28, 0.08,
                                   facecolor=accent, edgecolor="none"))
    ax.add_patch(Circle((x + 0.48, y_card + card_h - 0.52), 0.27,
                        facecolor=COLOR["ink900"], edgecolor="none"))
    ax.text(x + 0.48, y_card + card_h - 0.52, no, ha="center", va="center",
            fontsize=11, fontweight="bold", color="white")
    ax.text(x + 0.9, y_card + card_h - 0.52, title, va="center",
            fontsize=13.5, fontweight="bold", color=COLOR["ink900"])
    ax.text(x + 0.3, y_card + card_h - 1.02, stat, fontsize=11,
            fontweight="bold", color=accent)
    for k, item in enumerate(items):
        yy = y_card + card_h - 1.50 - k * 0.48
        ax.add_patch(Circle((x + 0.42, yy + 0.02), 0.045, color=accent))
        ax.text(x + 0.62, yy, item, fontsize=9.6, color=COLOR["ink600"], va="center")
    if i < 3:
        ay = y_card + card_h / 2
        ax.add_patch(FancyArrowPatch((x + card_w + 0.02, ay), (x + card_w + gap - 0.02, ay),
                                     arrowstyle="-|>,head_length=12,head_width=9",
                                     mutation_scale=1.0, color=COLOR["ink600"], linewidth=2.6))

ax.text(8, 0.85, "흐름: 전월세 371,612 → 전세 188,184 → 전세가율 테이블 27,348 단지·월 → 개별 거래 102,671건 라벨 (매칭률 54.6%)",
        ha="center", fontsize=11.5, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 0.42, "매칭 불가 사유: 해당 월 매매 거래 부재(단독·다가구 다수) — 이 46%는 학습에서 제외하되 진단 서비스는 동·구 통계 피처로 커버",
        ha="center", fontsize=10.5, color=COLOR["ink400"], style="italic")

save(fig, "fig_Matching_Method")
