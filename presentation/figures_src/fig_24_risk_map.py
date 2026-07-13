"""Figure 24 — 천안시 안전 신호등 지도 (Tier1-B, choropleth)
심사위원이 3초 안에 파악해야 할 메시지: 도시 전체를 미리 스캔했다 — 구도심(동남)에 주의·위험이 집중된다.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Patch
from matplotlib.collections import PatchCollection
from viz_style import apply_style, save, COLOR

apply_style()

ROOT = Path(__file__).resolve().parents[2]
geo = json.load(open(ROOT / "data" / "manual" / "cheonan_emd_2013.geojson", encoding="utf-8"))
safety = pd.read_parquet(ROOT / "data" / "processed" / "dong_safety_score.parquet")

# ── 법정동(65) → 행정동 폴리곤(30) 매핑 (천안시 관할 기준) ──
ADM_TO_LEGAL = {
    "중앙동": ["대흥동", "오룡동", "사직동", "영성동"],
    "문성동": ["문화동", "성황동"],
    "원성1동": ["원성동"], "원성2동": ["원성동"],
    "봉명동": ["봉명동"],
    "일봉동": ["다가동", "용곡동"],
    "신방동": ["신방동"],
    "청룡동": ["청당동", "구룡동", "구성동", "삼룡동", "청수동"],
    "신안동": ["안서동", "유량동", "신부동"],
    "성정1동": ["성정동", "와촌동"], "성정2동": ["성정동"],
    "쌍용1동": ["쌍용동"], "쌍용2동": ["쌍용동"], "쌍용3동": ["쌍용동"],
    "백석동": ["백석동"], "불당동": ["불당동"],
    "부성1동": ["두정동", "성성동"],
    "부성2동": ["두정동", "부대동", "업성동", "신당동", "차암동"],
}
score_map = dict(zip(safety["법정동명"], safety["종합안전점수"]))

def adm_score(adm_name: str):
    # 읍·면: 하위 리 점수 평균
    if adm_name.endswith(("읍", "면")):
        vals = [v for k, v in score_map.items() if k.startswith(adm_name + " ")]
        return float(np.mean(vals)) if vals else None
    legals = ADM_TO_LEGAL.get(adm_name, [])
    vals = [score_map[l] for l in legals if l in score_map]
    return float(np.mean(vals)) if vals else None

def grade_color(s):
    if s is None:
        return "#EDF1F5"
    if s >= 60:
        return COLOR["safe"]
    if s >= 45:
        return COLOR["caution"]
    return COLOR["risk"]

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=300,
                              gridspec_kw={"width_ratios": [1.35, 1]})
fig.suptitle("천안시 안전 신호등 지도 — 도시 전체 선제 스캔",
             fontsize=21, fontweight="bold", color=COLOR["ink900"],
             x=0.07, ha="left", y=0.97)
fig.text(0.07, 0.915, "65개 법정동 종합 안전점수를 행정동 관할로 집계 · HUG '1채 진단'과의 차별점 = 지도 한 장",
         fontsize=11.5, color=COLOR["ink400"], weight="semibold")

# ── choropleth ──
label_pts = {}
for f in geo["features"]:
    name = f["properties"]["name"]
    s = adm_score(name)
    color = grade_color(s)
    geom = f["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    all_xy = []
    for poly in polys:
        ring = np.array(poly[0])
        ax.add_patch(MplPolygon(ring, closed=True, facecolor=color,
                                edgecolor="white", linewidth=1.1, zorder=2))
        all_xy.append(ring)
    pts = np.vstack(all_xy)
    label_pts[name] = (pts[:, 0].mean(), pts[:, 1].mean(), s)

ax.set_aspect("equal"); ax.axis("off")
xs = [p[0] for p in label_pts.values()]; ys = [p[1] for p in label_pts.values()]
ax.set_xlim(min(xs) - 0.03, max(xs) + 0.03)
ax.set_ylim(min(ys) - 0.03, max(ys) + 0.03)

# 핵심 동 라벨
CALLOUTS = {
    "원성1동": ("원성동 44.9\n(유일 위험)", COLOR["risk"], (0.075, -0.055)),
    "불당동": ("불당동 71.5", "#065F46", (-0.055, 0.004)),
    "백석동": ("백석동 70.6", "#065F46", (-0.055, 0.012)),
    "중앙동": ("구도심(동남구)\n주의 밀집", "#92400E", (-0.045, 0.075)),
}
for adm, (label, color, (dx, dy)) in CALLOUTS.items():
    if adm in label_pts:
        x, y0, _ = label_pts[adm]
        ax.annotate(label, xy=(x, y0), xytext=(x + dx, y0 + dy),
                    fontsize=10.5, fontweight="bold", color=color,
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.0),
                    ha="center", zorder=5)

legend = [Patch(color=COLOR["safe"], label="안전 (60점+)"),
          Patch(color=COLOR["caution"], label="주의 (45~60)"),
          Patch(color=COLOR["risk"], label="위험 (45 미만)"),
          Patch(color="#EDF1F5", label="거래표본 부족")]
ax.legend(handles=legend, loc="lower left", frameon=False, fontsize=10.5)

# ── 우측: 등급 분포 + 하위 동 랭킹 ──
ax2.axis("off"); ax2.set_xlim(0, 10); ax2.set_ylim(0, 10)
ax2.text(0.2, 9.6, "법정동 신호등 분포 (65개)", fontsize=14, fontweight="bold", color=COLOR["ink900"])
dist = [("초록 · 안전", (safety["신호등"] == "초록").sum(), COLOR["safe"]),
        ("노랑 · 주의", (safety["신호등"] == "노랑").sum(), COLOR["caution"]),
        ("빨강 · 위험", (safety["신호등"] == "빨강").sum(), COLOR["risk"])]
for i, (lab, n, c) in enumerate(dist):
    yy = 8.9 - i * 0.75
    ax2.barh([yy], [n / 65 * 7.5], left=1.9, height=0.42, color=c, zorder=3)
    ax2.text(1.7, yy, lab, ha="right", va="center", fontsize=11, color=COLOR["ink600"])
    ax2.text(2.05 + n / 65 * 7.5, yy, f"{n}", va="center", fontsize=11.5,
             fontweight="bold", color=COLOR["ink900"])

ax2.text(0.2, 6.3, "안전점수 하위 5개 동", fontsize=14, fontweight="bold", color=COLOR["ink900"])
worst = safety.nsmallest(5, "종합안전점수")
for i, (_, r) in enumerate(worst.iterrows()):
    yy = 5.6 - i * 0.72
    c = COLOR["risk"] if r["종합안전점수"] < 45 else COLOR["caution"]
    ax2.barh([yy], [r["종합안전점수"] / 100 * 7.0], left=2.4, height=0.4, color=c, zorder=3)
    ax2.text(2.2, yy, r["법정동명"], ha="right", va="center", fontsize=10.5, color=COLOR["ink600"])
    ax2.text(2.55 + r["종합안전점수"] / 100 * 7.0, yy, f"{r['종합안전점수']:.1f}",
             va="center", fontsize=10.5, fontweight="bold", color=COLOR["ink900"])
ax2.text(0.2, 1.4, "동남구 평균 위험거래율 37.2%\n> 서북구 30.8%", fontsize=12,
         color=COLOR["ink600"], weight="semibold")
ax2.text(0.2, 0.55, "행정동 경계: 통계청 KOSTAT (SGIS 공개)", fontsize=9, color=COLOR["ink400"])

plt.tight_layout(rect=[0, 0.01, 1, 0.90])
save(fig, "fig_Risk_Map")
