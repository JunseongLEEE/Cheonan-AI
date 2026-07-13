"""Figure 25 — Leakage 방어 도식 (Tier1-C)
심사위원이 3초 안에 파악해야 할 메시지: 라벨은 매매가로 만들지만, 모델은 매매가를 본 적이 없다 — 실서비스 조건 그대로.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from viz_style import apply_style, save, COLOR

apply_style()

fig, ax = plt.subplots(figsize=(16, 8), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 8); ax.axis("off")

ax.text(0.4, 7.6, "라벨 ↔ 피처 완전 분리 — 데이터 누수(Leakage) 방어 설계",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.4, 7.15, "'매매가 없이 AUC 0.99'가 성립하는 구조적 이유 — 세입자는 계약 현장에서 시세를 모른다",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")


def card(x, y, w, h, fc="white", ec=None, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.18",
                                facecolor=fc, edgecolor=ec or COLOR["line"], linewidth=lw))


# ── 좌: 라벨 생성 (학습 시에만) ──
card(0.4, 2.4, 5.6, 4.0, fc="#FEF2F2", ec="#FECACA")
ax.text(0.75, 5.95, "라벨 생성 — 학습 시에만 사용", fontsize=14.5,
        fontweight="bold", color="#991B1B")
label_steps = [
    "매매 실거래 270,307건 → 단지·월 중앙값",
    "전세가율 = 보증금 ÷ 매매가 중앙값",
    "규정 임계 적용 (HUG·국토부)",
    "≥80% → 위험(46,084) · ≤60% → 안전(14,328)",
]
for i, s in enumerate(label_steps):
    yy = 5.35 - i * 0.62
    ax.add_patch(Circle((1.0, yy), 0.05, color="#991B1B"))
    ax.text(1.25, yy, s, fontsize= 11.5, color=COLOR["ink600"], va="center")
ax.text(0.75, 2.72, "※ 매매가·전세가율은 정답표에만 존재", fontsize=10.5,
        color="#991B1B", weight="semibold")

# ── 중앙: 차단벽 ──
ax.plot([7.0, 7.0], [2.2, 6.6], color=COLOR["ink900"], linewidth=3.5,
        linestyle=(0, (4, 2)), zorder=3)
ax.add_patch(FancyBboxPatch((5.95, 4.15), 2.1, 0.62,
                            boxstyle="round,pad=0.02,rounding_size=0.2",
                            facecolor=COLOR["ink900"], edgecolor="none", zorder=4))
ax.text(7.0, 4.46, "누수 차단", ha="center", va="center", fontsize=12.5,
        fontweight="bold", color="white", zorder=5)
ax.text(7.0, 1.95, "학습·검증·서비스 전 구간에서\n매매가 계열 피처 반입 금지", ha="center",
        fontsize=10, color=COLOR["ink400"], weight="semibold")

# ── 우: 피처 (모델이 보는 것) ──
card(8.0, 2.4, 7.6, 4.0, fc="#ECFDF5", ec="#A7F3D0")
ax.text(8.35, 5.95, "모델 입력 27개 피처 — 계약 전 관측 가능한 것만", fontsize=14.5,
        fontweight="bold", color="#065F46")
feat_groups = [
    ("가격·면적 (4)", "보증금, log보증금, ㎡당 보증금, 전용면적"),
    ("건물 (13)", "건물연령, 동 노후·내진·구조 비율, 세대수 …"),
    ("지역·시점 (5)", "동남구, 거래연도, 동 평균보증금, 과거 위험 이력 …"),
    ("상대 비교 (5)", "동/구 평균 대비 배율, 연령차, 보증금×노후 교차"),
]
for i, (g, items) in enumerate(feat_groups):
    yy = 5.35 - i * 0.66
    ax.add_patch(Circle((8.6, yy), 0.05, color="#065F46"))
    ax.text(8.85, yy + 0.13, g, fontsize=11.5, color=COLOR["ink900"], weight="semibold")
    ax.text(8.85, yy - 0.17, items, fontsize=9.8, color=COLOR["ink600"])
ax.text(8.35, 2.72, "✗ 매매가 ✗ 전세가율 ✗ 공시가 — 단 하나도 미포함", fontsize=10.5,
        color="#065F46", weight="semibold")

# ── 하단: 실험 증거 스트립 ──
strip_y = 0.55
card(0.4, strip_y, 15.2, 1.0, fc=COLOR["soft"])
evid = [
    ("exp_001", "매매가비율 포함", "AUC 0.9984", "누수 확인 → 폐기", COLOR["risk"]),
    ("exp_002", "매매가 계열 전부 제거", "AUC 0.9929", "성능 유지 → 신호는 구조에 있음", COLOR["safe"]),
    ("exp_004", "규정 임계 80% 채택", "AUC 0.9893", "최종 채택 (5-fold OOF)", COLOR["safe"]),
]
for j, (eid, what, auc, verdict, c) in enumerate(evid):
    cx = 0.4 + 15.2 * (j + 0.5) / 3
    ax.text(cx, strip_y + 0.72, f"{eid} — {what}", ha="center", fontsize=10.5,
            color=COLOR["ink600"], weight="semibold")
    ax.text(cx, strip_y + 0.30, f"{auc}  ·  {verdict}", ha="center", fontsize=10.5,
            fontweight="bold", color=c)
    if j < 2:
        dx = 0.4 + 15.2 * (j + 1) / 3
        ax.plot([dx, dx], [strip_y + 0.18, strip_y + 0.82], color=COLOR["line"], linewidth=0.9)

save(fig, "fig_Leakage_Guard")
