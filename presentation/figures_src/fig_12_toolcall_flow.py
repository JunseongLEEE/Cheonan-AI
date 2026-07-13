"""Figure 12 — 천안세이프 LLM Tool-Calling 런타임 흐름
심사위원이 3초 안에 파악해야 할 메시지: LLM이 스스로 4개 도구를 골라 실행하고, 실측 수치에 근거해 답한다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

ax.text(8, 8.55, "Tool-Calling 에이전트 — LLM이 직접 도구를 선택·실행",
        ha="center", fontsize=22, fontweight="bold", color=COLOR["ink900"])
ax.text(8, 8.08, "규칙 기반 라우터 없이, 파인튜닝된 LLM이 질문 의도를 판단해 JSON 툴 호출을 생성",
        ha="center", fontsize=12.5, color=COLOR["ink400"], weight="semibold")


def card(x, y, w, h, fc="white", ec=None, lw=1.0, r=0.16, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0.02,rounding_size={r}",
                                linewidth=lw, edgecolor=ec or COLOR["line"],
                                facecolor=fc, zorder=z))


def arrow(x0, y0, x1, y1, color=None, lw=2.4, style="-|>,head_length=11,head_width=8"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                 arrowstyle=style, mutation_scale=1.0,
                                 color=color or COLOR["ink600"], linewidth=lw, zorder=4))


# ── ① 사용자 질문 ──
card(0.5, 5.6, 3.4, 1.7)
ax.text(2.2, 6.95, "① 사용자 질문", ha="center", fontsize=13, fontweight="bold", color=COLOR["ink900"])
ax.text(2.2, 6.35, '"불당동 8천만원\n33㎡ 전세 위험해?"', ha="center", va="center",
        fontsize=11, color=COLOR["ink600"], style="italic")

# ── ② LLM 중심부 ──
card(5.1, 4.9, 5.8, 3.1, fc=COLOR["soft"], lw=1.2)
ax.text(8.0, 7.55, "② 천안세이프 LLM (7B · 자체 파인튜닝)", ha="center",
        fontsize=14, fontweight="bold", color=COLOR["ink900"])
ax.text(8.0, 7.05, "의도 판단 → 도구 선택 → 인자 추출", ha="center",
        fontsize=10.5, color=COLOR["ink400"], weight="semibold")
card(5.5, 5.25, 5.0, 1.45, fc="white")
ax.text(8.0, 6.35, "<tool_call>", ha="center", fontsize=10.5,
        color="#8B5CF6", weight="bold", family="monospace")
ax.text(8.0, 5.92, '{"name": "simulator", "arguments":\n{"보증금_만원": 8000, "법정동명": "불당동", "전용면적": 33}}',
        ha="center", va="center", fontsize=8.8, color=COLOR["ink600"])

arrow(3.95, 6.45, 5.05, 6.45)

# ── ③ 4개 도구 ──
TOOLS = [
    ("simulator", "깡통전세 위험 진단", "LightGBM+SHAP · AUC 0.989", "#EF4444"),
    ("dong_lookup", "동네 안전 조회", "65개 동 8축 안전점수", "#F59E0B"),
    ("recommend", "안전매물 추천", "4-모델 앙상블 · 실거래", "#10B981"),
    ("news_search", "뉴스 검색", "Google News RSS 실시간", "#0EA5E9"),
]
tool_w, tool_h, gap = 3.5, 1.25, 0.25
ty0 = 0.7
tx = (16 - (4 * tool_w + 3 * gap)) / 2
ax.text(8, 3.35, "③ 도구 실행 — 전부 실측 시스템 값", ha="center",
        fontsize=13, fontweight="bold", color=COLOR["ink900"])
for i, (name, title, sub, accent) in enumerate(TOOLS):
    x = tx + i * (tool_w + gap)
    card(x, ty0, tool_w, tool_h + 0.7)
    ax.add_patch(Circle((x + 0.35, ty0 + tool_h + 0.32), 0.07,
                        facecolor=accent, edgecolor="none", zorder=3))
    ax.text(x + 0.55, ty0 + tool_h + 0.32, name, va="center", fontsize=11,
            color=accent, weight="bold")
    ax.text(x + 0.3, ty0 + tool_h - 0.12, title, fontsize=11.5,
            color=COLOR["ink900"], weight="semibold")
    ax.text(x + 0.3, ty0 + tool_h - 0.55, sub, fontsize=9.5, color=COLOR["ink400"])

# LLM → tools / tools → LLM 화살표
arrow(7.3, 4.85, 5.6, 2.75)
arrow(10.2, 2.75, 8.7, 4.85, color=COLOR["ink400"])
ax.text(5.7, 3.9, "호출", fontsize=10, color=COLOR["ink600"], weight="semibold", rotation=50)
ax.text(9.85, 3.85, "결과 반환", fontsize=10, color=COLOR["ink400"], weight="semibold", rotation=-52)

# ── ④ 최종 답변 ──
card(12.1, 5.6, 3.4, 1.7, fc="#FEF2F2", ec="#FECACA")
ax.text(13.8, 6.95, "④ 근거 기반 답변", ha="center", fontsize=13,
        fontweight="bold", color=COLOR["ink900"])
ax.add_patch(Circle((12.75, 6.52), 0.09, facecolor=COLOR["risk"], edgecolor="none", zorder=5))
ax.text(12.95, 6.52, "위험확률 84% — 계약 재고 권고", va="center",
        fontsize=10.5, color=COLOR["ink900"], weight="semibold")
ax.text(13.8, 6.1, "SHAP 근거 + 등기부 확인·HUG 보증 안내", ha="center", va="center",
        fontsize=9.5, color=COLOR["ink600"])

arrow(10.95, 6.45, 12.05, 6.45)

# 캡션
ax.text(8, 0.15, "학습된 판단: 정보가 부족하면 도구 대신 되묻고, 범위 밖 질문은 정중히 거절 — 데이터셋에 경계 케이스 포함",
        ha="center", fontsize=10.5, color=COLOR["ink400"], style="italic")

save(fig, "fig_ToolCall_Flow")
