"""페르소나 프로필 카드 3종 — PPT ACT 도입부용 인물 figure.
심사위원이 3초 안에 파악해야 할 메시지: 이 청년이 누구고, 뭘 원하고, 어떤 순서로 서비스를 쓰는가.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.brand_assets import mascot_uri as _mascot_uri
import base64, io
from viz_style import apply_style, COLOR

def _mascot_img(pose):
    uri = _mascot_uri(pose)
    if not uri:
        return None
    b = base64.b64decode(uri.split(",", 1)[1])
    return mpimg.imread(io.BytesIO(b), format="png")

apply_style()

OUT = Path(__file__).resolve().parents[1] / "figures" / "figures_v3_persona"
OUT.mkdir(parents=True, exist_ok=True)

SKY = "#2E86E6"

PERSONAS = [
    dict(pid="P1", name="김가성", age=26, emoji="가", pose="기본", accent="#F59E0B",
         tag="가성비형 · 취준생",
         quote="위치는 안 좋아도\n싸고 넓은 집이면 돼요",
         traits=[("예산", "~5,000만원"), ("우선순위", "가격 > 면적 > 위치"),
                 ("걱정", "싼 집 = 위험한 집?")],
         journey=["매물 탐색\n저가 검색", "내 매물 체크\nAI 진단", "안전지도\n동네 확인"]),
    dict(pid="P2", name="박안심", age=29, emoji="안", pose="기본", accent="#10B981",
         tag="안전최우선형 · 사회초년생",
         quote="KTX로 서울 출퇴근해요.\n치안이 제일 중요해요",
         traits=[("예산", "~1억"), ("우선순위", "치안 > 교통 > 가격"),
                 ("걱정", "여성 1인 가구 안전")],
         journey=["예산별 추천\n1억 랭킹", "매물 탐색\nKTX 프리셋", "AI 상담\n치안 질문"]),
    dict(pid="P3", name="이새내", age=20, emoji="새", pose="안내", accent="#8B5CF6",
         tag="대학새내기형 · 단국대 신입생",
         quote="엄마, 이 집 괜찮은지\nAI한테 물어봤어",
         traits=[("예산", "~5,000만원 (부모 지원)"), ("우선순위", "대학 도보권"),
                 ("걱정", "첫 자취 · 계약 무지")],
         journey=["AI 상담\n첫 질문", "매물 탐색\n단국대 프리셋", "계약 가이드\n정책 연결"]),
]

for p in PERSONAS:
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=300)
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.6); ax.axis("off")

    # 카드 프레임
    ax.add_patch(FancyBboxPatch((0.15, 0.15), 9.7, 5.3,
                                boxstyle="round,pad=0.02,rounding_size=0.25",
                                facecolor="white", edgecolor=SKY, linewidth=2.2))
    ax.add_patch(FancyBboxPatch((0.15, 4.55), 9.7, 0.9,
                                boxstyle="round,pad=0.02,rounding_size=0.25",
                                facecolor="#EAF3FD", edgecolor="none"))
    ax.text(0.55, 5.0, f"PERSONA {p['pid']}", fontsize=13, fontweight="bold",
            color=SKY, va="center", family="monospace")
    ax.text(9.55, 5.0, p["tag"], fontsize=12.5, fontweight="bold",
            color="#16233A", va="center", ha="right")

    # 아바타 — 천안 마스코트 나랑이 + 이니셜 배지
    ax.add_patch(Circle((1.7, 2.95), 1.1, facecolor=p["accent"], alpha=0.12,
                        edgecolor=p["accent"], linewidth=2.5))
    _img = _mascot_img(p["pose"])
    if _img is not None:
        ax.add_artist(AnnotationBbox(OffsetImage(_img, zoom=0.42), (1.7, 3.0),
                                     frameon=False))
    ax.add_patch(Circle((2.42, 3.62), 0.32, facecolor=p["accent"], edgecolor="white", linewidth=2))
    ax.text(2.42, 3.6, p["emoji"], fontsize=17, ha="center", va="center",
            fontweight="bold", color="white")
    ax.text(1.7, 1.5, f"{p['name']} ({p['age']})", fontsize=15, fontweight="bold",
            color="#16233A", ha="center")

    # 인용
    ax.text(3.3, 3.85, f"“{p['quote']}”", fontsize=14.5, color="#16233A",
            fontweight="bold", va="top", linespacing=1.5)

    # 특성
    for i, (k, v) in enumerate(p["traits"]):
        y = 2.7 - i * 0.52
        ax.add_patch(Circle((3.45, y + 0.02), 0.05, color=p["accent"]))
        ax.text(3.65, y, f"{k}", fontsize=11, color="#8494A9", va="center")
        ax.text(5.1, y, v, fontsize=11.5, color="#16233A", weight="semibold", va="center")

    # 여정 스트립
    jy = 0.72
    ax.text(0.55, 1.18, "서비스 여정", fontsize=10.5, color="#8494A9", weight="semibold")
    xw = 2.65
    for i, step in enumerate(p["journey"]):
        x = 0.55 + i * (xw + 0.55)
        ax.add_patch(FancyBboxPatch((x, jy - 0.38), xw, 0.82,
                                    boxstyle="round,pad=0.02,rounding_size=0.14",
                                    facecolor="#F2F7FD", edgecolor="#C9D8EC", linewidth=1))
        ax.text(x + xw / 2, jy + 0.03, step, fontsize=10, color="#16233A",
                ha="center", va="center", weight="semibold", linespacing=1.3)
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + xw + 0.06, jy + 0.03), (x + xw + 0.5, jy + 0.03),
                                         arrowstyle="-|>,head_length=8,head_width=6",
                                         mutation_scale=1.0, color=SKY, linewidth=2))

    fig.savefig(OUT / f"{p['pid']}_00_페르소나_프로필.png", dpi=300,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"✓ {p['pid']}_00_페르소나_프로필.png")
