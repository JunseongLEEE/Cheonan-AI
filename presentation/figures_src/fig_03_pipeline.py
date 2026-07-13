"""Figure 3 — 데이터 파이프라인
심사위원이 3초 안에 파악해야 할 메시지: 공공 API 100% → 정제 → AI 모델 → 시민 서비스, 4단계로 완성된 재현가능한 흐름.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

STAGES = [
    dict(no="01", title="수집",
         items=[("공공 API", "실거래·전월세"),
                ("공공포털",  "건축물대장·SGIS"),
                ("공공기관",  "치안·소방·교통")],
         accent="#0EA5E9",  # sky — intake
         note="수집 완료"),
    dict(no="02", title="정제·통합",
         items=[("법정동 매핑",  "65개 동 표준화"),
                ("전세가율",      "실거래 기반"),
                ("건물 노후도",  "연령·구조"),],
         accent="#10B981",  # emerald — cleaning
         note="정제 완료"),
    dict(no="03", title="AI 모델링",
         items=[("6모델 앙상블",  "XGBoost AUC 0.9898"),
                ("SHAP",          "설명력 확보"),
                ("천안세이프 LLM", "7B tool-calling 파인튜닝"),],
         accent="#8B5CF6",  # violet — modeling
         note="학습 완료"),
    dict(no="04", title="서비스",
         items=[("Streamlit 웹",   "인터랙티브 대시보드"),
                ("신호등 지도",     "65개 동 시각화"),
                ("LLM 챗봇·추천",  "자체 LLM이 툴 호출"),],
         accent="#F59E0B",  # amber — delivery
         note="배포 완료"),
]

# 16:6 히어로
fig, ax = plt.subplots(figsize=(16, 6), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 6); ax.axis("off")

# ── 타이틀 ──
ax.text(8, 5.55, "데이터 파이프라인 — 공공데이터 100% × 재현가능",
        ha="center", fontsize=22, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 5.10, "17종 공공 API + SGIS 6종 → 정제 → AI 모델 → 시민 서비스",
        ha="center", fontsize=12.5, color=COLOR["ink400"], weight="semibold")

# ── 4 카드 + 화살표 ──
card_w, card_h = 3.4, 3.1
gap = 0.4
total_w = 4 * card_w + 3 * gap
start_x = (16 - total_w) / 2
y_card  = 1.3

for i, s in enumerate(STAGES):
    x = start_x + i * (card_w + gap)
    # 카드 (흰 배경 + border)
    ax.add_patch(FancyBboxPatch((x, y_card), card_w, card_h,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor="white", zorder=1))
    # 상단 4px 액센트 바
    ax.add_patch(patches.Rectangle((x + 0.15, y_card + card_h - 0.08),
                                   card_w - 0.30, 0.08,
                                   facecolor=s["accent"], edgecolor="none", zorder=2))

    # 원형 번호 뱃지
    badge_cx = x + 0.55
    badge_cy = y_card + card_h - 0.55
    ax.add_patch(Circle((badge_cx, badge_cy), 0.30,
                        facecolor=COLOR["ink900"], edgecolor="none", zorder=3))
    ax.text(badge_cx, badge_cy, s["no"],
            ha="center", va="center", fontsize=12, fontweight="bold",
            color="white", zorder=4)
    # 단계 제목
    ax.text(x + 1.02, badge_cy, s["title"],
            ha="left", va="center", fontsize=17, fontweight="bold",
            color=COLOR["ink900"], zorder=3)

    # 항목 리스트 (아이콘 pair)
    item_y = y_card + card_h - 1.15
    for k, (label, sub) in enumerate(s["items"]):
        yy = item_y - k * 0.62
        # 왼쪽 dot
        ax.add_patch(Circle((x + 0.45, yy + 0.09), 0.06,
                            facecolor=s["accent"], edgecolor="none", zorder=3))
        ax.text(x + 0.65, yy + 0.16, label,
                fontsize=11.5, color=COLOR["ink900"], weight="semibold", zorder=3)
        ax.text(x + 0.65, yy - 0.10, sub,
                fontsize=10, color=COLOR["ink400"], zorder=3)

    # 하단 상태 라벨 (있으면)
    if s.get("note"):
        note_w = 1.5
        note_x = x + card_w - note_w - 0.2
        ax.add_patch(FancyBboxPatch((note_x, y_card + 0.15), note_w, 0.35,
                                    boxstyle="round,pad=0,rounding_size=0.16",
                                    facecolor=COLOR["soft"], edgecolor=COLOR["line"],
                                    linewidth=0.8, zorder=3))
        ax.text(note_x + note_w / 2, y_card + 0.325, s["note"],
                ha="center", va="center", fontsize=9.5,
                color=COLOR["ink600"], weight="semibold", zorder=4)

    # Chevron 화살표 (카드 사이)
    if i < len(STAGES) - 1:
        ax_x0 = x + card_w + 0.02
        ax_x1 = x + card_w + gap - 0.02
        ay    = y_card + card_h / 2
        arr = FancyArrowPatch((ax_x0, ay), (ax_x1, ay),
                              arrowstyle="-|>,head_length=14,head_width=10",
                              mutation_scale=1.0,
                              color=COLOR["ink600"], linewidth=3.0, zorder=2)
        ax.add_patch(arr)

# ── 하단 stat strip ──
stats = [("10만+", "실거래 거래"),
         ("65", "법정동 커버"),
         ("100%", "대회 규정 준수")]
strip_y = 0.55
strip_w = 8.4
strip_x = (16 - strip_w) / 2

ax.add_patch(FancyBboxPatch((strip_x, strip_y - 0.05), strip_w, 0.7,
                            boxstyle="round,pad=0.02,rounding_size=0.14",
                            linewidth=1.0, edgecolor=COLOR["line"],
                            facecolor=COLOR["soft"], zorder=1))
for j, (big, lab) in enumerate(stats):
    cx = strip_x + strip_w * (j + 0.5) / 3
    ax.text(cx, strip_y + 0.42, big,
            ha="center", va="center", fontsize=17, fontweight="bold",
            color=COLOR["ink900"], zorder=2)
    ax.text(cx, strip_y + 0.15, lab,
            ha="center", va="center", fontsize=10, color=COLOR["ink400"],
            weight="semibold", zorder=2)
    if j < 2:
        # divider
        dx = strip_x + strip_w * (j + 1) / 3
        ax.plot([dx, dx], [strip_y + 0.10, strip_y + 0.55],
                color=COLOR["line"], linewidth=0.9, zorder=2)

save(fig, "fig_Pipeline")
