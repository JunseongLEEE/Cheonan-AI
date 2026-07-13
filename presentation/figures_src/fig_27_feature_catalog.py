"""Figure 27 — 27개 피처 카탈로그 (Tier2-E)
심사위원이 3초 안에 파악해야 할 메시지: 27개 피처 전부 매매가 없이 계약 전 관측 가능 — 4축으로 위험을 본다.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
from viz_style import apply_style, save, COLOR

apply_style()

# (그룹, 액센트, [(피처, 설명)]) — scripts/simulator.py FEATURE_COLS 27개 전부
GROUPS = [
    ("가격·면적 — 매물 자체 (4)", "#0EA5E9", [
        ("보증금_만원", "계약서의 보증금"),
        ("보증금_log", "로그 변환 (분포 안정화)"),
        ("㎡당_보증금", "단위면적당 보증금 — SHAP 3위"),
        ("전용면적", "㎡"),
    ]),
    ("지역·시점 (5)", "#F59E0B", [
        ("동남구", "구도심 여부 (0/1)"),
        ("거래연도", "계약 연도"),
        ("연도별_동_위험도", "동네 과거 위험 누적 — SHAP 1위"),
        ("동_평균보증금", "동네 시세 수준"),
        ("동_거래건수", "동네 유동성"),
    ]),
    ("건물 — 건축물대장 (13)", "#8B5CF6", [
        ("건물연령", "준공 후 연수 — SHAP 2위"),
        ("동_평균건물연령 · 동_건물연령_std", "동네 연령 분포"),
        ("동_노후비율 · 동_심각노후비율", "25년+/35년+ 비중"),
        ("동_내진비율", "내진설계 비중"),
        ("동_건물수 · 동_평균세대수", "주거 밀도"),
        ("동_평균총면적 · 동_평균지상층", "건물 규모"),
        ("동_철근콘크리트/벽돌/목구조비율", "구조 분포 3종"),
    ]),
    ("상대 비교·교차 (5)", "#10B981", [
        ("보증금_동평균_비율", "동네 평균 대비 배율"),
        ("보증금_구평균_비율", "구 평균 대비 배율"),
        ("면적_구평균_비율", "구 평균 면적 대비"),
        ("건물연령_동평균차", "동네 대비 연식 차"),
        ("보증금_노후도_교차", "고보증금×노후 결합 신호"),
    ]),
]

fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")

ax.text(0.35, 8.6, "27개 피처 카탈로그 — 4개 축, 전부 계약 전 관측 가능",
        fontsize=21, fontweight="bold", color=COLOR["ink900"])
ax.text(0.35, 8.16, "매매가·전세가율·공시가 의존 피처 0개 — '시세를 모르는 세입자' 조건 그대로 · 출처: 실거래 API + 건축물대장",
        fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# 2×2 카드
POS = [(0.35, 4.45), (8.25, 4.45), (0.35, 0.55), (8.25, 0.55)]
CW, CH = 7.4, 3.5
for (x, y), (gname, accent, feats) in zip(POS, GROUPS):
    ax.add_patch(FancyBboxPatch((x, y), CW, CH,
                                boxstyle="round,pad=0.02,rounding_size=0.16",
                                facecolor="white", edgecolor=COLOR["line"], linewidth=1.0))
    ax.add_patch(patches.Rectangle((x + 0.12, y + CH - 0.07), CW - 0.24, 0.07,
                                   facecolor=accent, edgecolor="none"))
    ax.text(x + 0.3, y + CH - 0.42, gname, fontsize=13.5, fontweight="bold",
            color=COLOR["ink900"])
    row_h = (CH - 0.75) / max(len(feats), 1)
    for k, (feat, desc) in enumerate(feats):
        yy = y + CH - 0.85 - k * row_h
        ax.add_patch(plt.Circle((x + 0.42, yy), 0.045, color=accent))
        ax.text(x + 0.6, yy, feat, fontsize=10.2, color=COLOR["ink900"],
                weight="semibold", va="center")
        ax.text(x + CW - 0.3, yy, desc, fontsize=9.3, color=COLOR["ink400"],
                va="center", ha="right")

ax.text(8, 0.13, "SHAP 상위 3개(동 위험 이력·건물연령·㎡당 보증금)가 HUG 심사 관점(지역 이력·담보 건전성·가격 적정성)과 일치",
        ha="center", fontsize=11, color=COLOR["ink400"], style="italic")

save(fig, "fig_Feature_Catalog")
