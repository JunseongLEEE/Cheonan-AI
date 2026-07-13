"""Figure 32 — B2G 도입 효과: 조사 대상 깔때기 (Tier3-J)
심사위원이 3초 안에 파악해야 할 메시지: 10만 건을 다 볼 수 없다 — AI가 조사 대상을 99% 줄여 행정력을 집중시킨다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from viz_style import apply_style, save, COLOR

apply_style()

STAGES = [
    ("전체 전세 거래", 102671, "매칭 실거래 전수", COLOR["ink400"], "—"),
    ("AI 이상거래 탐지", 5134, "Isolation Forest 5.0%", "#8B5CF6", "95% 축소"),
    ("깡통 후보 (이상+가율 100%+)", 1129, "교차 필터 1.1%", "#F59E0B", "99% 축소"),
    ("위험 경보 동", 19, "가율 80%+ & 상승 추세", COLOR["risk"], "동 단위 타격"),
]

fig, ax = plt.subplots(figsize=(16, 8.2), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 8.2); ax.axis("off")

ax.text(0.4, 7.8, "B2G 도입 효과 — 조사 대상 99% 축소, 행정력 집중",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.4, 7.36, "천안시 주거복지과 관점: 전수 조사 불가능한 10만 건을 AI가 우선순위 깔때기로 전환",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# ── 깔때기 (가로) ──
max_w = 13.0
y0 = 5.85
for i, (title, n, sub, c, badge) in enumerate(STAGES):
    frac = max(n / STAGES[0][1], 0.045)
    w = max_w * (frac ** 0.42)  # 시각 보정 (로그 느낌)
    x = 0.9
    yy = y0 - i * 1.16
    ax.add_patch(FancyBboxPatch((x, yy - 0.46), w, 0.92,
                                boxstyle="round,pad=0.02,rounding_size=0.16",
                                facecolor=c, edgecolor="none", alpha=0.92))
    inside = w > 4.2
    tx = x + 0.35 if inside else x + w + 0.3
    tc = "white" if inside else COLOR["ink900"]
    ax.text(tx, yy + 0.13, f"{title} — {n:,}건" if n > 50 else f"{title} — {n}개",
            fontsize=13, fontweight="bold", color=tc, va="center")
    ax.text(tx, yy - 0.22, sub, fontsize=10, color=tc if inside else COLOR["ink600"],
            va="center", alpha=0.95)
    # 우측 뱃지
    ax.add_patch(FancyBboxPatch((14.15, yy - 0.28), 1.55, 0.56,
                                boxstyle="round,pad=0.02,rounding_size=0.14",
                                facecolor=COLOR["soft"], edgecolor=COLOR["line"], linewidth=0.9))
    ax.text(14.925, yy, badge, ha="center", va="center", fontsize=10.5,
            fontweight="bold", color=COLOR["ink900"])
    if i < 3:
        ax.add_patch(FancyArrowPatch((2.6, yy - 0.50), (2.6, yy - 0.66),
                                     arrowstyle="-|>,head_length=9,head_width=7",
                                     mutation_scale=1.0, color=COLOR["ink600"], linewidth=2.2))

# ── 하단: 행정 활용 3열 ──
uses = [
    ("선제 점검", "경보 19개 동에 점검 인력\n우선 배치 (입장면·봉명동 등)"),
    ("연계 행정", "위험 판정 시민에게 안심계약\n도움서비스·HUG 보증 자동 안내"),
    ("정책 모니터링", "월 단위 전세가율 추세로\n대책 효과를 정량 추적"),
]
uy = 0.45
for j, (t, s) in enumerate(uses):
    cx = 0.9 + j * 4.95
    ax.add_patch(FancyBboxPatch((cx, uy), 4.6, 1.15,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor="white", edgecolor=COLOR["line"], linewidth=1.0))
    ax.text(cx + 0.3, uy + 0.82, t, fontsize=12, fontweight="bold", color=COLOR["ink900"])
    ax.text(cx + 0.3, uy + 0.36, s, fontsize=9.8, color=COLOR["ink600"], va="center")

ax.text(8, 0.14, "전 파이프라인이 전국 표준 공공 API 기반 — 충남 15개 시·군 동일 구조로 이식 가능",
        ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

save(fig, "fig_B2G_Effect")
