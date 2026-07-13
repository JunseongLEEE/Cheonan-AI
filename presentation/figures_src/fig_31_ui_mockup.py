"""Figure 31 — 서비스 UI 목업: 계약 전 3초 진단 (Tier3-I)
심사위원이 3초 안에 파악해야 할 메시지: 슬로건이 화면으로 존재한다 — 입력 4개 → 신호등 + 이유 + 다음 행동.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

ax.text(0.4, 8.6, "\"계약 전 3초\" — 시민이 보는 화면",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.4, 8.16, "실제 Streamlit 서비스 흐름을 모바일 목업으로 재구성 · 89.0%는 실제 모델 출력 — 성정동(서북구 구도심 인접, 주의)은 성성동(75.4 안전)과 다른 동네",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")


def phone(x, y, w, h):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.35",
                                facecolor="white", edgecolor=COLOR["ink900"], linewidth=2.2))
    ax.add_patch(FancyBboxPatch((x + w / 2 - 0.5, y + h - 0.28), 1.0, 0.12,
                                boxstyle="round,pad=0.01,rounding_size=0.06",
                                facecolor=COLOR["line"], edgecolor="none"))


# ── 좌: 입력 화면 ──
px, py, pw, ph = 1.2, 0.7, 3.9, 6.8
phone(px, py, pw, ph)
ax.text(px + pw / 2, py + ph - 0.65, "내 매물 체크", ha="center", fontsize=13,
        fontweight="bold", color=COLOR["ink900"])
fields = [("동네", "성정동"), ("보증금", "8,000만원"), ("면적", "59㎡ (18평)"), ("건축년도", "2010년")]
for i, (lab, val) in enumerate(fields):
    yy = py + ph - 1.35 - i * 0.95
    ax.text(px + 0.35, yy + 0.28, lab, fontsize=9.5, color=COLOR["ink400"], weight="semibold")
    ax.add_patch(FancyBboxPatch((px + 0.3, yy - 0.32), pw - 0.6, 0.52,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=COLOR["soft"], edgecolor=COLOR["line"], linewidth=0.9))
    ax.text(px + 0.5, yy - 0.06, val, fontsize=11, color=COLOR["ink900"], va="center")
ax.add_patch(FancyBboxPatch((px + 0.3, py + 0.55), pw - 0.6, 0.62,
                            boxstyle="round,pad=0.02,rounding_size=0.16",
                            facecolor=COLOR["ink900"], edgecolor="none"))
ax.text(px + pw / 2, py + 0.86, "AI 위험 진단하기", ha="center", va="center",
        fontsize=11.5, fontweight="bold", color="white")

# 화살표
ax.annotate("", xy=(6.4, 4.1), xytext=(5.4, 4.1),
            arrowprops=dict(arrowstyle="-|>,head_length=12,head_width=9",
                            color=COLOR["ink600"], lw=2.6))
ax.text(5.9, 4.4, "3초", ha="center", fontsize=12, fontweight="bold", color=COLOR["ink900"])

# ── 우: 결과 화면 ──
qx, qy, qw, qh = 6.6, 0.7, 4.6, 6.8
phone(qx, qy, qw, qh)
ax.text(qx + qw / 2, qy + qh - 0.65, "진단 결과", ha="center", fontsize=13,
        fontweight="bold", color=COLOR["ink900"])
# 신호등 카드
ax.add_patch(FancyBboxPatch((qx + 0.35, qy + qh - 2.75), qw - 0.7, 1.85,
                            boxstyle="round,pad=0.02,rounding_size=0.18",
                            facecolor="#FEF2F2", edgecolor="#FECACA", linewidth=1.2))
ax.add_patch(Circle((qx + 1.05, qy + qh - 1.8), 0.33, facecolor=COLOR["risk"], edgecolor="none"))
ax.text(qx + 1.7, qy + qh - 1.62, "위험", fontsize=16, fontweight="bold", color="#991B1B")
ax.text(qx + 1.7, qy + qh - 2.02, "위험확률 89.0%", fontsize=12, color=COLOR["ink900"], weight="semibold")
ax.text(qx + 0.55, qy + qh - 2.5, "동네 평균 대비 높은 보증금 · 과거 위험 이력",
        fontsize=9.3, color=COLOR["ink600"])
# SHAP 미니
ax.text(qx + 0.45, qy + qh - 3.15, "왜 위험한가요? (SHAP)", fontsize=10.5,
        fontweight="bold", color=COLOR["ink900"])
shap_items = [("동네 과거 위험 이력", 0.86, COLOR["risk"]),
              ("동네 평균 보증금 수준", 0.55, COLOR["risk"]),
              ("㎡당 보증금 (완화 요인)", 0.38, COLOR["safe"])]
for i, (lab, v, c) in enumerate(shap_items):
    yy = qy + qh - 3.55 - i * 0.52
    ax.text(qx + 0.5, yy + 0.13, lab, fontsize=9.2, color=COLOR["ink600"])
    ax.add_patch(FancyBboxPatch((qx + 0.5, yy - 0.12), (qw - 1.4) * v, 0.16,
                                boxstyle="round,pad=0.01,rounding_size=0.07",
                                facecolor=c, edgecolor="none"))
# CTA 2개
for j, (label, fc, tc) in enumerate([("안심계약 도움서비스 신청", COLOR["ink900"], "white"),
                                     ("이 예산 안전 동네 추천받기", COLOR["soft"], None)]):
    yy = qy + 1.35 - j * 0.75
    ax.add_patch(FancyBboxPatch((qx + 0.35, yy - 0.3), qw - 0.7, 0.58,
                                boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor=fc, edgecolor=COLOR["line"], linewidth=0.9))
    ax.text(qx + qw / 2, yy - 0.01, label, ha="center", va="center", fontsize=10.5,
            fontweight="bold", color=tc or COLOR["ink900"])

# ── 우측: 흐름 설명 패널 ──
ex, ey, ew = 12.0, 1.2, 3.6
ax.text(ex, 7.0, "화면 뒤에서 일어나는 일", fontsize=13.5, fontweight="bold", color=COLOR["ink900"])
steps = [
    ("LightGBM 27피처 실예측", "위험확률·신호등"),
    ("SHAP 상위 요인 한글화", "'왜'를 3줄로"),
    ("위험 시 정책 연결", "안심계약·HUG 보증 안내"),
    ("추천 CTA", "같은 예산 안전 동네 Top-k"),
]
for i, (t, s) in enumerate(steps):
    yy = 6.35 - i * 0.95
    ax.add_patch(Circle((ex + 0.12, yy + 0.05), 0.06, color=COLOR["safe"]))
    ax.text(ex + 0.35, yy + 0.16, t, fontsize=11, weight="semibold", color=COLOR["ink900"])
    ax.text(ex + 0.35, yy - 0.14, s, fontsize=9.5, color=COLOR["ink400"])
ax.text(ex, 1.7, "동일 기능이 LLM 채팅으로도:\n\"성정동 팔천에 전세 들어가도 돼?\"",
        fontsize=10.5, color=COLOR["ink600"], style="italic")

save(fig, "fig_UI_Mockup")
