"""공통 시각화 스타일 — design_template.md §1 준수.

Pretendard 폰트 등록 + rcParams + Semantic 컬러 팔레트.
모든 figure 스크립트 최상단에서 `from viz_style import apply_style, COLOR` 로 임포트.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

ASSETS = Path(__file__).resolve().parents[1] / "assets"
OUT_DIR = Path(__file__).resolve().parents[1] / "figures"
OUT_DIR.mkdir(exist_ok=True, parents=True)

COLOR = {
    "safe":     "#10B981",
    "caution":  "#F59E0B",
    "risk":     "#EF4444",
    "ink900":   "#0F172A",
    "ink600":   "#475569",
    "ink400":   "#94A3B8",
    "line":     "#E2E8F0",
    "soft":     "#F8FAFC",
    "risk_soft":"#FEF2F2",
}

# Progress bar / soft accents
COLOR["safe_soft"]    = "#ECFDF5"
COLOR["caution_soft"] = "#FFFBEB"


def _register_pretendard() -> str:
    """Pretendard TTF 등록 후 실제 폰트명을 반환.

    Pretendard가 없으면 시스템의 Apple SD Gothic Neo/AppleGothic으로 폴백.
    """
    registered = None
    for pattern in ("Pretendard-*.otf", "Pretendard-*.ttf"):
        for path in sorted(ASSETS.glob(pattern)):
            try:
                font_manager.fontManager.addfont(str(path))
                registered = "Pretendard"
            except Exception:
                pass

    if registered:
        return registered

    for candidate in ["Apple SD Gothic Neo", "AppleGothic", "Noto Sans KR", "Malgun Gothic"]:
        for f in font_manager.fontManager.ttflist:
            if candidate.lower() in f.name.lower():
                return f.name
    return mpl.rcParams["font.family"][0]


def apply_style():
    """rcParams 일괄 적용."""
    family = _register_pretendard()
    plt.rcParams.update({
        "font.family":       family,
        "axes.edgecolor":    COLOR["line"],
        "axes.linewidth":    0.8,
        "axes.labelcolor":   COLOR["ink600"],
        "axes.titlesize":    18,
        "axes.titleweight":  "600",
        "axes.titlecolor":   COLOR["ink900"],
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "xtick.color":       COLOR["ink400"],
        "ytick.color":       COLOR["ink400"],
        "xtick.labelsize":   11,
        "ytick.labelsize":   11,
        "grid.color":        "#F1F5F9",
        "grid.linewidth":    0.8,
        "figure.facecolor":  "white",
        "axes.facecolor":    "white",
        "savefig.dpi":       300,
        "savefig.bbox":      "tight",
        "savefig.facecolor": "white",
        "axes.unicode_minus": False,
    })
    return family


def save(fig, name: str, transparent: bool = False):
    """`presentation/figures/{name}.png` 로 저장."""
    path = OUT_DIR / f"{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight",
                facecolor="none" if transparent else "white")
    plt.close(fig)
    print(f"✓ {path.name}")
    return path
