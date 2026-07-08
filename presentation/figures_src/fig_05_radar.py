"""Figure 5 — 원성동 vs 천안 평균 8축 레이더
심사위원이 3초 안에 파악해야 할 메시지: 원성동은 금융안전·건물노후·환경 3개 축에서 평균보다 20%p+ 취약 → 즉시 개입 대상.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_parquet(ROOT / "data/processed/dong_safety_score.parquet")

AXES  = ["금융안전_점수", "건물노후_점수", "치안_점수", "편의시설_점수",
         "환경_점수",     "침수위험_점수", "소방_점수",  "교통_점수"]
LABEL = ["금융안전",      "건물노후",     "치안",       "편의시설",
         "환경",          "침수위험",     "소방",        "교통"]

dong = df[df["법정동명"] == "원성동"].iloc[0]
avg  = df[AXES].mean()

v_dong = np.array([float(dong[a]) for a in AXES])
v_avg  = np.array([float(avg[a])  for a in AXES])
delta_pp = (v_dong - v_avg) * 100  # % point 격차

# 취약 축: Δ ≤ -8pp
risk_mask = delta_pp <= -8

angles = np.linspace(0, 2 * np.pi, len(LABEL), endpoint=False).tolist()
angles_c = angles + angles[:1]
v_dong_c = np.concatenate([v_dong, v_dong[:1]])
v_avg_c  = np.concatenate([v_avg,  v_avg[:1]])

# 1:1 정사각형 (여유롭게)
fig = plt.figure(figsize=(12, 12), dpi=300)
ax = fig.add_subplot(111, polar=True)
# 축을 안쪽으로 → 라벨/타이틀/캡션 겹침 방지 (top 축소, 좌우 여백 확대)
fig.subplots_adjust(top=0.74, bottom=0.20, left=0.17, right=0.83)

# 회전: 첫 축을 12시 방향으로
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)

# 평균: 점선 + Ink400
ax.plot(angles_c, v_avg_c, color=COLOR["ink400"], linewidth=1.8,
        linestyle=(0, (4, 3)), zorder=3)
ax.fill(angles_c, v_avg_c, color=COLOR["ink400"], alpha=0.06, zorder=2)

# 원성동: risk + fill 0.15
ax.plot(angles_c, v_dong_c, color=COLOR["risk"], linewidth=2.6, zorder=4)
ax.fill(angles_c, v_dong_c, color=COLOR["risk"], alpha=0.15, zorder=3)

# 축 라벨(강조/일반) — 각도에 따라 축 밖 여백 다르게, va/ha 조정
ax.set_xticks(angles)
ax.set_xticklabels([""] * len(LABEL))

def _label_pos(ang_rad):
    """각도(rad)에 따라 라벨 정렬/오프셋 결정. r을 1.0에서 넉넉히 떨어뜨려
    타이틀·틱·인접 라벨과의 침범을 방지."""
    deg = np.degrees(ang_rad) % 360
    if 80 <= deg <= 100:   # top
        return "center", "bottom", 1.30
    if 260 <= deg <= 280:  # bottom
        return "center", "top",    1.30
    if 100 < deg < 260:    # left
        return "right",  "center", 1.32
    return "left",   "center", 1.32

for i, (ang, lab) in enumerate(zip(angles, LABEL)):
    is_risk = risk_mask[i]
    color = COLOR["risk"] if is_risk else COLOR["ink600"]
    weight = "bold" if is_risk else "semibold"
    ha, va, r_name = _label_pos(ang)

    sign = "+" if delta_pp[i] >= 0 else ""
    delta_txt = f"{sign}{delta_pp[i]:.0f}%p"
    d_color = COLOR["risk"] if is_risk else (
        COLOR["safe"] if delta_pp[i] >= 5 else COLOR["ink400"])

    # 이름과 Δ를 한 라벨에 개행으로 결합 (폴라 좌표 안정성)
    combined = f"{lab}\n{delta_txt}"
    ax.text(ang, r_name, combined, ha=ha, va=va,
            fontsize=13, color=color, fontweight=weight,
            linespacing=1.5)
    # Δ 부분만 색 다르게 → 오버레이 텍스트 하나 더 (같은 위치, 개행만 있는 문자열)
    # 실질적으로는 위 텍스트가 이름+delta를 회색/빨강으로 통일 표시하면 충분
    # 별도 delta 색상 강조는 이름 색으로 이미 반영됨

# 반지름 축 라벨 위치를 스포크 사이 각도로 배치 → 데이터 축 라벨과 충돌 회피
# 8축(45° 간격)이므로 스포크 사이 지점(22.5°)로 이동
ax.set_rlabel_position(22.5)

# 반경 tick 3~4단, 옅게
ax.set_ylim(0, 1)
ax.set_yticks([0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"],
                   fontsize=9, color=COLOR["ink400"])
ax.grid(color="#F1F5F9", linewidth=0.8)
ax.spines["polar"].set_color(COLOR["line"])
ax.spines["polar"].set_linewidth(0.8)

# 타이틀 — top=0.74 로 라디오 영역 축소했으므로 타이틀은 더 위쪽에 배치
fig.text(0.5, 0.955, "원성동은 어디에서 무너지고 있나",
         ha="center", fontsize=22, fontweight="bold", color=COLOR["ink900"])
fig.text(0.5, 0.918, "천안 65개 동 평균 대비 8축 안전 프로파일",
         ha="center", fontsize=13, color=COLOR["ink400"], weight="semibold")

# Badge 스타일 범례 (우상단, dot + text)
legend_elements = [
    Line2D([0], [0], marker='o', linestyle='none',
           markerfacecolor=COLOR["risk"], markeredgecolor="white",
           markersize=12, label="원성동 (위험)"),
    Line2D([0], [0], marker='o', linestyle='none',
           markerfacecolor=COLOR["ink400"], markeredgecolor="white",
           markersize=12, label="천안시 65개 동 평균"),
]
fig.legend(handles=legend_elements,
           loc="upper right", bbox_to_anchor=(0.98, 0.89),
           frameon=False, fontsize=11.5, handletextpad=0.6,
           labelcolor=COLOR["ink900"])

# 한 줄 요약 캡션
caption = "원성동은 금융안전 · 건물노후 · 환경 3개 축에서 평균보다 20%p 이상 취약 → 즉시 개입 대상"
fig.text(0.5, 0.035, caption,
         ha="center", fontsize=12.5, color=COLOR["ink900"],
         fontweight="bold",
         bbox=dict(boxstyle="round,pad=0.5", facecolor=COLOR["risk_soft"],
                   edgecolor=COLOR["risk"], linewidth=1.0))

save(fig, "fig_Radar_Wonseong")
