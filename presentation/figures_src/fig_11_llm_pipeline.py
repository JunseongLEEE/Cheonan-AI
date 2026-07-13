"""Figure 11 — 천안세이프 LLM 학습 파이프라인
심사위원이 3초 안에 파악해야 할 메시지: 실데이터 기반 학습셋 → QLoRA 자체 학습 → 로컬 서빙, 외부 API 없는 완전 자체 LLM.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

STAGES = [
    dict(no="01", title="학습셋 구축",
         items=[("실데이터 툴 실행", "LightGBM·안전점수·추천"),
                ("8종 대화 유형", "진단·조회·뉴스·되묻기"),
                ("6,800+ 대화", "intent 층화 분할")],
         accent="#0EA5E9", note="합성+실값"),
    dict(no="02", title="QLoRA 파인튜닝",
         items=[("Qwen2.5-7B", "한국어+툴콜 베이스"),
                ("4-bit NF4 · r16", "assistant 턴만 학습"),
                ("RTX 3090 × 2", "DDP 분산 학습")],
         accent="#8B5CF6", note="자체 GPU"),
    dict(no="03", title="이중 평가",
         items=[("툴 선택 정확도", "base vs tuned 비교"),
                ("인자 추출 F1", "±5% 수치 허용"),
                ("경계 케이스", "되묻기·범위밖 거절")],
         accent="#F59E0B", note="held-out 8%"),
    dict(no="04", title="로컬 서빙",
         items=[("LoRA 머지", "단일 bf16 모델"),
                ("vLLM 서버", "hermes tool parser"),
                ("OpenAI 호환 API", "GPU 1장, port 8008")],
         accent="#10B981", note="외부 API 0"),
    dict(no="05", title="챗봇 대체",
         items=[("gpt-5-mini 대체", "천안세이프 7B 우선"),
                ("에이전트 루프", "툴 선택→실행→답변"),
                ("3단 폴백", "로컬→OpenAI→rule")],
         accent="#EF4444", note="무중단"),
]

fig, ax = plt.subplots(figsize=(16, 6), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 6); ax.axis("off")

ax.text(8, 5.55, "천안세이프 LLM — 깡통전세 전문 sLLM 자체 구축 파이프라인",
        ha="center", fontsize=22, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 5.10, "Qwen2.5-7B + 도메인 Tool-Calling QLoRA — 외부 API 의존 없는 온프레미스 AI 상담원",
        ha="center", fontsize=12.5, color=COLOR["ink400"], weight="semibold")

card_w, card_h = 2.82, 3.1
gap = 0.32
total_w = 5 * card_w + 4 * gap
start_x = (16 - total_w) / 2
y_card = 1.3

for i, s in enumerate(STAGES):
    x = start_x + i * (card_w + gap)
    ax.add_patch(FancyBboxPatch((x, y_card), card_w, card_h,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                linewidth=1.0, edgecolor=COLOR["line"],
                                facecolor="white", zorder=1))
    ax.add_patch(patches.Rectangle((x + 0.13, y_card + card_h - 0.08),
                                   card_w - 0.26, 0.08,
                                   facecolor=s["accent"], edgecolor="none", zorder=2))
    badge_cx, badge_cy = x + 0.48, y_card + card_h - 0.52
    ax.add_patch(Circle((badge_cx, badge_cy), 0.27,
                        facecolor=COLOR["ink900"], edgecolor="none", zorder=3))
    ax.text(badge_cx, badge_cy, s["no"], ha="center", va="center",
            fontsize=11, fontweight="bold", color="white", zorder=4)
    ax.text(x + 0.88, badge_cy, s["title"], ha="left", va="center",
            fontsize=14.5, fontweight="bold", color=COLOR["ink900"], zorder=3)

    item_y = y_card + card_h - 1.10
    for k, (label, sub) in enumerate(s["items"]):
        yy = item_y - k * 0.60
        ax.add_patch(Circle((x + 0.38, yy + 0.09), 0.055,
                            facecolor=s["accent"], edgecolor="none", zorder=3))
        ax.text(x + 0.56, yy + 0.16, label, fontsize=10.5,
                color=COLOR["ink900"], weight="semibold", zorder=3)
        ax.text(x + 0.56, yy - 0.10, sub, fontsize=9,
                color=COLOR["ink400"], zorder=3)

    note_w = 1.35
    note_x = x + card_w - note_w - 0.15
    ax.add_patch(FancyBboxPatch((note_x, y_card + 0.13), note_w, 0.33,
                                boxstyle="round,pad=0,rounding_size=0.15",
                                facecolor=COLOR["soft"], edgecolor=COLOR["line"],
                                linewidth=0.8, zorder=3))
    ax.text(note_x + note_w / 2, y_card + 0.295, s["note"],
            ha="center", va="center", fontsize=9,
            color=COLOR["ink600"], weight="semibold", zorder=4)

    if i < len(STAGES) - 1:
        ay = y_card + card_h / 2
        arr = FancyArrowPatch((x + card_w + 0.02, ay), (x + card_w + gap - 0.02, ay),
                              arrowstyle="-|>,head_length=12,head_width=9",
                              mutation_scale=1.0,
                              color=COLOR["ink600"], linewidth=2.6, zorder=2)
        ax.add_patch(arr)

stats = [("7B", "자체 파인튜닝 모델"),
         ("4종", "네이티브 툴 호출"),
         ("2×3090", "온프레미스 학습·서빙"),
         ("0원", "외부 API 비용")]
strip_w, strip_y = 10.4, 0.5
strip_x = (16 - strip_w) / 2
ax.add_patch(FancyBboxPatch((strip_x, strip_y - 0.05), strip_w, 0.7,
                            boxstyle="round,pad=0.02,rounding_size=0.14",
                            linewidth=1.0, edgecolor=COLOR["line"],
                            facecolor=COLOR["soft"], zorder=1))
for j, (big, lab) in enumerate(stats):
    cx = strip_x + strip_w * (j + 0.5) / 4
    ax.text(cx, strip_y + 0.42, big, ha="center", va="center",
            fontsize=16, fontweight="bold", color=COLOR["ink900"], zorder=2)
    ax.text(cx, strip_y + 0.15, lab, ha="center", va="center",
            fontsize=9.5, color=COLOR["ink400"], weight="semibold", zorder=2)
    if j < 3:
        dx = strip_x + strip_w * (j + 1) / 4
        ax.plot([dx, dx], [strip_y + 0.10, strip_y + 0.55],
                color=COLOR["line"], linewidth=0.9, zorder=2)

save(fig, "fig_LLM_Pipeline")
