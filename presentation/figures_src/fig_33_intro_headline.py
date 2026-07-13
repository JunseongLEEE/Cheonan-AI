"""Figure 33 — 인트로 앵커: 천안에서 실제 벌어진 일
심사위원이 3초 안에 파악해야 할 메시지: 통계 이전에 사건 — 중개사·법무사·은행까지 공모해 시세를 부풀렸다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

fig, ax = plt.subplots(figsize=(16, 8.4), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 8.4); ax.axis("off")

# 메인 헤드라인
ax.add_patch(FancyBboxPatch((0.4, 6.1), 15.2, 1.75,
                            boxstyle="round,pad=0.02,rounding_size=0.2",
                            facecolor="#FEF2F2", edgecolor="#FECACA", linewidth=1.3))
ax.add_patch(patches.Rectangle((0.75, 6.35), 0.16, 1.25, color=COLOR["risk"]))
ax.text(1.25, 7.32, "“천안 원룸 세입자 28명, 보증금 15억 증발 — 중개사·법무사·금고 지점장까지 공모”",
        fontsize=17.5, fontweight="bold", color=COLOR["ink900"])
ax.text(1.25, 6.78, "대전지검 천안지청, 전세사기 일당 13명 무더기 기소 (2024.7) — 시세를 25억 불법대출로 부풀린 새마을금고 지점장 포함",
        fontsize=11.5, color=COLOR["ink600"])
ax.text(1.25, 6.38, "출처: 뉴시스·서울신문 보도", fontsize=9, color=COLOR["ink400"])

# 사건 카드 2개
cases = [
    ("건물주 1명이 142세대 보유", "다가구·오피스텔 대량 매입 후\n고보증금 계약 반복 — 대형 의심 신고",
     "노컷뉴스"),
    ("직산 임대아파트 전세사기 의혹", "피해주택 50건 대출사기 매입 정황\n— 구도심·읍면 지역까지 확산",
     "중도일보·대전일보"),
]
for j, (t, s, src) in enumerate(cases):
    cx = 0.4 + j * 5.3
    ax.add_patch(FancyBboxPatch((cx, 3.35), 5.0, 2.3,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                facecolor="white", edgecolor=COLOR["line"], linewidth=1.1))
    ax.add_patch(patches.Rectangle((cx + 0.3, 5.28), 0.12, 0.22, color=COLOR["caution"]))
    ax.text(cx + 0.6, 5.38, t, fontsize=13.5, fontweight="bold", color=COLOR["ink900"], va="center")
    ax.text(cx + 0.35, 4.55, s, fontsize=10.8, color=COLOR["ink600"], va="center")
    ax.text(cx + 0.35, 3.62, f"출처: {src}", fontsize=9, color=COLOR["ink400"])

# 우측: 연도별 피해 미니 차트
bx = 11.2
ax.add_patch(FancyBboxPatch((bx, 3.35), 4.4, 2.3,
                            boxstyle="round,pad=0.02,rounding_size=0.18",
                            facecolor=COLOR["soft"], edgecolor=COLOR["line"], linewidth=1.1))
ax.text(bx + 0.3, 5.32, "천안 전세사기 피해 (공식 집계)", fontsize=12,
        fontweight="bold", color=COLOR["ink900"])
data = [("2022", 31, 42), ("2023", 229, 79), ("2024", 28, 23)]
max_h = max(d[1] for d in data)
for k, (yr, hh, amt) in enumerate(data):
    xx = bx + 0.75 + k * 1.25
    bar_h = 1.05 * hh / max_h + 0.08
    ax.add_patch(FancyBboxPatch((xx, 3.85), 0.62, bar_h,
                                boxstyle="round,pad=0.01,rounding_size=0.06",
                                facecolor=COLOR["risk"], edgecolor="none",
                                alpha=0.55 + 0.45 * hh / max_h))
    ax.text(xx + 0.31, 3.85 + bar_h + 0.13, f"{hh}세대", ha="center", fontsize=9.5,
            fontweight="bold", color=COLOR["ink900"])
    ax.text(xx + 0.31, 3.66, yr, ha="center", fontsize=9, color=COLOR["ink400"])
ax.text(bx + 0.3, 3.62, "", fontsize=8)

# 하단 브릿지
ax.add_patch(FancyBboxPatch((0.4, 0.9), 15.2, 1.9,
                            boxstyle="round,pad=0.02,rounding_size=0.2",
                            facecolor=COLOR["ink900"], edgecolor="none"))
ax.text(8, 2.22, "누적 288세대 · 145억원 — 피해는 다가구·오피스텔, 청년 밀집 주거에 집중",
        ha="center", fontsize=14, fontweight="bold", color="white")
ax.text(8, 1.62, "제도권 전문가들이 '시세'를 부풀려 청년을 노렸다",
        ha="center", fontsize=16, fontweight="bold", color="#FCA5A5")
ax.text(8, 1.14, "→ 그래서 이 서비스는 시세를 몰라도 위험을 판별하도록 설계되었다 (근거 ④)",
        ha="center", fontsize=12.5, color="#E2E8F0")

save(fig, "fig_Intro_Headline")
