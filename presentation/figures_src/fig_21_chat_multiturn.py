"""Figure 21 — 대화 캡처 ①: 멀티턴 문맥 유지 + 툴 그라운딩
심사위원이 3초 안에 파악해야 할 메시지: '거기서'를 이해하고, 25평을 ㎡로 환산해 스스로 도구를 부른다 — 실제 응답 로그.
"""
from __future__ import annotations
import textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

# 실제 chat_probe 로그 그대로 (chat_probe_round4.jsonl)
CHAT = [
    ("user", "불당동 안전한 동네야?", None),
    ("bot", "불당동 종합 안전점수는 71.5/100 (초록)입니다.\n"
            "평균 전세가율은 70%로 주의권입니다.\n"
            "강점은 건물노후(0.94), 약점은 침수위험(0.50)입니다.\n"
            "최근 전세가율 69%, 6개월 추세 -1.7% (하락)입니다.\n"
            "다만 안전한 동네에도 위험 매물은 있으니 개별 진단은 챙기세요.",
     "dong_lookup — 65개 동 실데이터 조회"),
    ("user", "그럼 거기서 보증금 9000만원에 25평 전세면 어때? 2018년식이야.", None),
    ("bot", "AI 진단 결과 안전 등급입니다.\n"
            "불당동 보증금 9,000만원 · 80㎡ · 2018년식 기준,\n"
            "AI 위험확률은 7.86% (안전)입니다.\n"
            "위험을 높인 요인: 거래 연도(+1.87).\n"
            "반대로 건물 연식(-2.59)는 위험을 낮췄습니다.\n"
            "그래도 등기부등본 확인과 전입신고+확정일자는 기본으로 챙기세요.",
     "simulator — LightGBM 실예측 + SHAP"),
]

HIGHLIGHTS = [
    "\"거기서\" → 이전 턴의 불당동으로 문맥 유지",
    "\"25평\" → 80㎡ 자동 환산 후 인자 전달",
    "수치는 전부 도구 결과에서만 인용 (환각 없음)",
]

fig, ax = plt.subplots(figsize=(14, 9.5), dpi=300)
ax.set_xlim(0, 14); ax.set_ylim(0, 9.5); ax.axis("off")

ax.text(0.4, 9.15, "실제 대화 캡처 ① — 멀티턴 문맥 유지와 도구 호출",
        fontsize=20, fontweight="bold", color=COLOR["ink900"])
ax.text(0.4, 8.72, "천안세이프 LLM 응답 로그 원문 (2026-07-09 · temperature 0 · 후편집 없음)",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")


def bubble(y_top, role, text, tool):
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=48) or [""]
    h = 0.34 * len(lines) + 0.42
    if role == "user":
        w = min(max(len(l) for l in lines) * 0.148 + 0.5, 7.2)
        x = 13.6 - w
        ax.add_patch(FancyBboxPatch((x, y_top - h), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.16",
                                    facecolor="#E0F2FE", edgecolor="#BAE6FD", linewidth=1))
        for i, l in enumerate(lines):
            ax.text(x + 0.25, y_top - 0.38 - i * 0.34, l, fontsize=11.5,
                    color=COLOR["ink900"], va="center")
        ax.text(x - 0.15, y_top - 0.30, "청년 사용자", fontsize=9, ha="right",
                color=COLOR["ink400"], weight="semibold")
    else:
        w = 8.6
        x = 0.4
        if tool:
            ax.add_patch(FancyBboxPatch((x, y_top - 0.34), 0.16 + len(tool) * 0.125, 0.36,
                                        boxstyle="round,pad=0.02,rounding_size=0.14",
                                        facecolor="#F5F3FF", edgecolor="#DDD6FE", linewidth=1))
            ax.text(x + 0.14, y_top - 0.16, f"[TOOL] {tool}", fontsize=9.5,
                    color="#7C3AED", weight="bold", va="center")
            y_top -= 0.52
        ax.add_patch(FancyBboxPatch((x, y_top - h), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.16",
                                    facecolor="white", edgecolor=COLOR["line"], linewidth=1.1))
        ax.plot([x + 0.03, x + 0.03], [y_top - h + 0.15, y_top - 0.15],
                color=COLOR["safe"], linewidth=3, solid_capstyle="round")
        for i, l in enumerate(lines):
            ax.text(x + 0.3, y_top - 0.38 - i * 0.34, l, fontsize=11.5,
                    color=COLOR["ink600"], va="center")
        ax.text(x + 0.3, y_top + 0.06, "천안세이프 (자체 7B)", fontsize=9,
                color=COLOR["safe"], weight="bold")
    return h + (0.75 if role == "bot" and tool else 0.28)


y = 8.35
for role, text, tool in CHAT:
    y -= bubble(y, role, text, tool)

# 우측 하이라이트 패널
px, py, pw = 9.5, 3.1, 4.1
ax.add_patch(FancyBboxPatch((px, py - 2.7), pw, 2.7,
                            boxstyle="round,pad=0.02,rounding_size=0.16",
                            facecolor=COLOR["soft"], edgecolor=COLOR["line"], linewidth=1))
ax.text(px + 0.25, py - 0.42, "포인트", fontsize=13, fontweight="bold", color=COLOR["ink900"])
for i, hl in enumerate(HIGHLIGHTS):
    wrapped = textwrap.wrap(hl, width=26)
    yy = py - 0.85 - i * 0.62
    ax.add_patch(plt.Circle((px + 0.33, yy + 0.02), 0.05, color=COLOR["safe"]))
    for j, l in enumerate(wrapped):
        ax.text(px + 0.52, yy - j * 0.26, l, fontsize=10.5, color=COLOR["ink600"], va="center")

save(fig, "fig_Chat_Multiturn")
