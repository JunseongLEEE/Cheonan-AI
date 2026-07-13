"""Cinematic dark-cosmos theme for the 천안 자취방 안전지도 Streamlit app.

Benchmark: "새벽 4시의 서울" (https://web-lime-nine-77.vercel.app/)
- Deep-space background with nebula radial gradients + twinkling stars
- Pretendard Variable font, purple/amber semantic palette
- CSS-only chapter-in / bar-draw / score-slide-up / letter-in animations
- Streamlit widget overrides (metric, tabs, expander, buttons, sliders)
"""
from __future__ import annotations
import streamlit as st

# ── Palette (from vercel benchmark CSS analysis) ──────────────────
COLOR = {
    "bg":            "#0A0908",
    "bg_deep":       "#040308",
    "bg_nebula":     "#0A1428",
    "surface":       "#141019",
    "surface_hi":    "#1B1526",
    "line":          "#2A2233",
    "fg":            "#F3F4F6",
    "fg_muted":      "#9CA3AF",
    "fg_subtle":     "#6B7280",
    "primary":       "#5B8CE8",   # 천안 블루 — 시 심벌 청색(#0047A0)의 다크 대비 상향
    "primary_soft":  "#8FB4F5",
    "primary_glow":  "rgba(91,140,232,0.35)",
    "caution":       "#F59E0B",
    "caution_soft":  "#FCD34D",
    "risk":          "#EF4444",
    "risk_strong":   "#FF6B7A",   # 태극 적색(#CD2E3A) 명도 상향
    "safe":          "#10B981",
    "safe_soft":     "#34D399",
    "highlight":     "#FFE9A8",
    "cyan":          "#06B6D4",
}


def _theme_css() -> str:
    """Massive CSS block — palette, background, keyframes, widget overrides."""
    C = COLOR
    return f"""
    <style>
    /* ── Font ───────────────────────────────────── */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
    html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {{
        font-family: 'Pretendard Variable', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-feature-settings: 'ss03', 'tnum';
    }}

    /* ── Cosmic background ─────────────────────── */
    .stApp {{
        background:
            radial-gradient(ellipse 900px 700px at 15% 12%, rgba(124,58,237,0.16), transparent 60%),
            radial-gradient(ellipse 800px 600px at 88% 85%, rgba(110,143,230,0.14), transparent 60%),
            radial-gradient(ellipse 700px 500px at 50% 55%, rgba(245,158,11,0.08), transparent 60%),
            radial-gradient(ellipse at 50% 30%, {C['bg_nebula']} 0%, {C['bg_deep']} 90%);
        background-attachment: fixed;
        color: {C['fg']};
    }}

    /* Twinkling star layer (pure CSS via multiple radial-gradients) */
    .stApp::before {{
        content: "";
        position: fixed; inset: 0; z-index: 0; pointer-events: none;
        background-image:
            radial-gradient(1.2px 1.2px at 20% 12%, rgba(255,255,255,0.9), transparent),
            radial-gradient(1px 1px at 62% 24%, rgba(255,255,255,0.7), transparent),
            radial-gradient(1.5px 1.5px at 85% 8%, rgba(143,180,245,0.95), transparent),
            radial-gradient(1px 1px at 12% 55%, rgba(255,255,255,0.65), transparent),
            radial-gradient(1.2px 1.2px at 45% 78%, rgba(255,255,255,0.8), transparent),
            radial-gradient(1px 1px at 78% 62%, rgba(255,233,168,0.75), transparent),
            radial-gradient(1.3px 1.3px at 32% 88%, rgba(255,255,255,0.7), transparent),
            radial-gradient(1px 1px at 92% 42%, rgba(143,180,245,0.85), transparent),
            radial-gradient(1.4px 1.4px at 8% 32%, rgba(255,255,255,0.6), transparent),
            radial-gradient(1px 1px at 55% 5%, rgba(255,255,255,0.7), transparent);
        animation: star-twinkle 4.5s ease-in-out infinite;
        opacity: 0.75;
    }}

    @keyframes star-twinkle {{
        0%, 100% {{ opacity: 0.75; }}
        50%      {{ opacity: 0.35; }}
    }}

    /* Sidebar / header dark */
    section[data-testid="stSidebar"] {{ background: rgba(20,16,25,0.7) !important; backdrop-filter: blur(12px); }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    div[data-testid="stToolbar"] {{ background: transparent !important; }}

    /* ── Cinematic entrance animations ────────── */
    @keyframes chapter-in {{
        0%   {{ opacity: 0; transform: translateY(32px) scale(0.988); filter: blur(14px); }}
        100% {{ opacity: 1; transform: translateY(0) scale(1);        filter: blur(0);    }}
    }}
    @keyframes detail-slide-up {{
        0%   {{ opacity: 0; transform: translateY(28px) scale(0.985); filter: blur(10px); }}
        100% {{ opacity: 1; transform: translateY(0) scale(1);        filter: blur(0);    }}
    }}
    @keyframes score-slide-up {{
        0%   {{ opacity: 0; transform: translateY(44px); filter: blur(16px); }}
        100% {{ opacity: 1; transform: translateY(0);    filter: blur(0);    }}
    }}
    @keyframes score-pop {{
        0%   {{ transform: scale(1); }}
        50%  {{ transform: scale(1.08); }}
        100% {{ transform: scale(1); }}
    }}
    @keyframes score-sweep {{
        0%   {{ transform: scaleX(0); transform-origin: left; }}
        100% {{ transform: scaleX(1); transform-origin: left; }}
    }}
    @keyframes bar-draw {{
        0%   {{ transform: scaleX(0); transform-origin: left; }}
        100% {{ transform: scaleX(1); transform-origin: left; }}
    }}
    @keyframes letter-in {{
        0%   {{ opacity: 0; transform: translateY(18px); filter: blur(6px); }}
        100% {{ opacity: 1; transform: translateY(0);    filter: blur(0);    }}
    }}
    @keyframes glow-pulse {{
        0%, 100% {{ text-shadow: 0 0 24px rgba(143,180,245,0.35), 0 0 48px rgba(91,140,232,0.15); }}
        50%      {{ text-shadow: 0 0 36px rgba(143,180,245,0.6),  0 0 72px rgba(91,140,232,0.35); }}
    }}
    @keyframes nebula-drift {{
        0%, 100% {{ transform: translate(0, 0) scale(1); opacity: 0.7; }}
        50%      {{ transform: translate(20px, -14px) scale(1.06); opacity: 1; }}
    }}
    @keyframes hint-pulse {{
        0%, 100% {{ opacity: 0.55; transform: scale(1); }}
        50%      {{ opacity: 1; transform: scale(1.02); }}
    }}
    @keyframes persona-card-in {{
        0%   {{ opacity: 0; transform: scale(0.93) translateY(24px); filter: blur(12px); }}
        100% {{ opacity: 1; transform: scale(1) translateY(0);       filter: blur(0);    }}
    }}

    /* ── Utility classes ──────────────────────── */
    .cinema-fade     {{ animation: chapter-in 0.85s cubic-bezier(.16,1,.3,1) both; }}
    .cinema-detail   {{ animation: detail-slide-up 0.7s cubic-bezier(.16,1,.3,1) both; }}
    .cinema-score    {{ animation: score-slide-up 0.9s cubic-bezier(.16,1,.3,1) both; }}
    .cinema-persona  {{ animation: persona-card-in 0.7s cubic-bezier(.16,1,.3,1) both; }}
    .stagger-1 {{ animation-delay: 0.08s; }}
    .stagger-2 {{ animation-delay: 0.18s; }}
    .stagger-3 {{ animation-delay: 0.30s; }}
    .stagger-4 {{ animation-delay: 0.44s; }}
    .stagger-5 {{ animation-delay: 0.60s; }}

    /* ── Streamlit widget re-skin ─────────────── */
    /* Headings */
    h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: {C['fg']} !important;
        letter-spacing: -0.02em;
        text-shadow: 0 0 32px rgba(143,180,245,0.15);
        animation: detail-slide-up 0.7s cubic-bezier(.16,1,.3,1) both;
    }}
    h1 {{ font-weight: 800; }}
    h2 {{ font-weight: 700; }}
    h3 {{ font-weight: 600; color: {C['primary_soft']} !important; }}

    /* Metric cards */
    div[data-testid="stMetric"] {{
        background: linear-gradient(140deg, rgba(27,21,38,0.7), rgba(20,16,25,0.5));
        border: 1px solid rgba(91,140,232,0.18);
        border-radius: 14px;
        padding: 1.0rem 1.1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
        backdrop-filter: blur(6px);
        animation: score-slide-up 0.85s cubic-bezier(.16,1,.3,1) both;
        transition: transform 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-3px);
        border-color: rgba(143,180,245,0.42);
        box-shadow: 0 12px 40px rgba(124,58,237,0.25), inset 0 1px 0 rgba(255,255,255,0.06);
    }}
    div[data-testid="stMetricValue"] {{
        color: {C['fg']} !important;
        font-weight: 800;
        font-size: 1.85rem;
        text-shadow: 0 0 24px rgba(143,180,245,0.25);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {C['fg_muted']} !important;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.02em;
    }}
    div[data-testid="stMetricDelta"] {{ font-weight: 700; }}

    /* Tabs */
    div[data-testid="stTabs"] > div > div[role="tablist"] {{
        gap: 6px;
        border-bottom: 1px solid {C['line']};
        padding-bottom: 6px;
    }}
    button[role="tab"] {{
        background: rgba(27,21,38,0.5) !important;
        border: 1px solid transparent !important;
        border-radius: 999px !important;
        color: {C['fg_muted']} !important;
        padding: 0.45rem 1.05rem !important;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.28s cubic-bezier(.16,1,.3,1);
    }}
    button[role="tab"]:hover {{
        background: rgba(91,140,232,0.10) !important;
        color: {C['primary_soft']} !important;
    }}
    button[role="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, rgba(91,140,232,0.22), rgba(124,58,237,0.14)) !important;
        border-color: rgba(143,180,245,0.4) !important;
        color: {C['fg']} !important;
        box-shadow: 0 0 24px rgba(91,140,232,0.28), inset 0 1px 0 rgba(255,255,255,0.06);
    }}

    /* Expander */
    div[data-testid="stExpander"] {{
        background: rgba(20,16,25,0.55);
        border: 1px solid {C['line']};
        border-radius: 12px;
        backdrop-filter: blur(6px);
    }}
    div[data-testid="stExpander"] summary {{ color: {C['primary_soft']} !important; font-weight: 600; }}

    /* Buttons */
    button[kind="primary"], .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(135deg, {C['primary']}, #7C3AED) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em;
        padding: 0.55rem 1.4rem !important;
        box-shadow: 0 6px 24px rgba(91,140,232,0.35), inset 0 1px 0 rgba(255,255,255,0.15);
        transition: all 0.28s cubic-bezier(.16,1,.3,1);
    }}
    button[kind="primary"]:hover, .stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 34px rgba(91,140,232,0.55), inset 0 1px 0 rgba(255,255,255,0.2);
    }}

    /* Inputs */
    input, textarea, .stTextInput input, .stNumberInput input, .stTextArea textarea,
    div[data-baseweb="select"] > div, div[data-baseweb="input"] input {{
        background: rgba(20,16,25,0.75) !important;
        border: 1px solid {C['line']} !important;
        color: {C['fg']} !important;
        border-radius: 10px !important;
    }}
    input:focus, textarea:focus,
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {C['primary']} !important;
        box-shadow: 0 0 0 3px rgba(91,140,232,0.18) !important;
    }}
    label, .stCheckbox label, .stRadio label {{ color: {C['fg']} !important; }}

    /* Slider */
    div[data-baseweb="slider"] div[role="slider"] {{
        background: {C['primary']} !important;
        box-shadow: 0 0 16px rgba(91,140,232,0.6);
    }}

    /* Alert / info boxes */
    div[data-testid="stAlert"] {{
        background: rgba(91,140,232,0.08) !important;
        border-left: 3px solid {C['primary']} !important;
        border-radius: 10px !important;
        color: {C['fg']} !important;
    }}

    /* Progress bar → cinematic sweep */
    div[data-testid="stProgress"] > div > div > div {{
        background: linear-gradient(90deg, {C['primary']}, {C['caution_soft']}) !important;
        animation: score-sweep 0.9s cubic-bezier(.65,0,.35,1) 0.1s both;
        box-shadow: 0 0 12px rgba(91,140,232,0.5);
    }}

    /* DataFrame */
    div[data-testid="stDataFrame"] {{
        background: rgba(20,16,25,0.6);
        border-radius: 12px;
        border: 1px solid {C['line']};
    }}

    /* Divider */
    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(91,140,232,0.35), transparent);
        margin: 2rem 0;
    }}

    /* ── Custom cinematic components ──────────── */
    .hero-cosmic {{
        position: relative;
        padding: 1.7rem 2.2rem 1.5rem;
        border-radius: 24px;
        border: 1px solid rgba(143,180,245,0.15);
        background:
            radial-gradient(ellipse 700px 400px at 20% 30%, rgba(91,140,232,0.18), transparent 60%),
            radial-gradient(ellipse 600px 400px at 85% 75%, rgba(245,158,11,0.10), transparent 60%),
            linear-gradient(140deg, rgba(27,21,38,0.85), rgba(10,9,8,0.9));
        overflow: hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
        animation: chapter-in 1.1s cubic-bezier(.16,1,.3,1) both;
        margin-bottom: 1.6rem;
    }}
    .hero-cosmic .hero-eyebrow {{
        font-family: 'JetBrains Mono', 'SF Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.3em;
        color: {C['primary_soft']};
        text-transform: uppercase;
        margin-bottom: 1.2rem;
        opacity: 0.9;
        animation: letter-in 0.9s cubic-bezier(.22,1,.36,1) 0.3s both;
    }}
    .hero-cosmic .hero-title {{
        font-size: 2.05rem;
        line-height: 1.18;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: {C['fg']};
        margin: 0 0 0.9rem 0;
        text-shadow: 0 0 40px rgba(143,180,245,0.25);
        animation: letter-in 1.1s cubic-bezier(.22,1,.36,1) 0.5s both, glow-pulse 5s ease-in-out 1.6s infinite;
    }}
    .hero-cosmic .hero-title em {{
        font-style: normal;
        background: linear-gradient(135deg, {C['primary_soft']}, {C['highlight']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .hero-cosmic .hero-sub {{
        font-size: 1.05rem;
        color: {C['fg_muted']};
        max-width: 640px;
        line-height: 1.75;
        margin-bottom: 1.6rem;
        animation: detail-slide-up 0.9s cubic-bezier(.16,1,.3,1) 0.75s both;
    }}
    .hero-cosmic .hero-pills {{
        display: flex; flex-wrap: wrap; gap: 8px;
        animation: detail-slide-up 0.9s cubic-bezier(.16,1,.3,1) 0.95s both;
    }}
    .hero-cosmic .pill {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px;
        border-radius: 999px;
        background: rgba(91,140,232,0.12);
        border: 1px solid rgba(143,180,245,0.28);
        color: {C['fg']};
        font-size: 12.5px;
        font-weight: 600;
        letter-spacing: 0.01em;
        backdrop-filter: blur(4px);
        transition: all 0.28s cubic-bezier(.16,1,.3,1);
    }}
    .hero-cosmic .pill:hover {{
        background: rgba(91,140,232,0.22);
        transform: translateY(-1px);
    }}
    .hero-cosmic .pill.risk    {{ background: rgba(239,68,68,0.14); border-color: rgba(248,113,113,0.4); color: {C['risk_strong']}; }}
    .hero-cosmic .pill.caution {{ background: rgba(245,158,11,0.14); border-color: rgba(252,211,77,0.4); color: {C['caution_soft']}; }}
    .hero-cosmic .pill.safe    {{ background: rgba(16,185,129,0.14); border-color: rgba(52,211,153,0.4); color: {C['safe_soft']}; }}
    .hero-cosmic .hero-hint {{
        margin-top: 1.4rem;
        color: {C['fg_subtle']};
        font-size: 0.85rem;
        letter-spacing: 0.02em;
        animation: hint-pulse 2.4s ease-in-out infinite, detail-slide-up 0.9s cubic-bezier(.16,1,.3,1) 1.1s both;
    }}

    /* Chapter divider */
    .chapter-tag {{
        display: flex; align-items: baseline; gap: 14px;
        margin: 2.4rem 0 1.4rem;
        animation: chapter-in 0.85s cubic-bezier(.16,1,.3,1) both;
    }}
    .chapter-tag .num {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.28em;
        color: {C['primary_soft']};
        opacity: 0.85;
    }}
    .chapter-tag .title {{
        color: {C['fg']};
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.015em;
    }}
    .chapter-tag .rule {{
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(143,180,245,0.35), transparent);
    }}

    /* Score bar (used in matching cards) */
    .score-bar-wrap {{
        background: rgba(255,255,255,0.06);
        border-radius: 999px;
        overflow: hidden;
        height: 8px;
        margin: 6px 0;
    }}
    .score-bar-fill {{
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, {C['primary']}, {C['caution_soft']});
        animation: bar-draw 0.9s cubic-bezier(.16,1,.3,1) 0.25s both;
        box-shadow: 0 0 12px rgba(91,140,232,0.5);
    }}

    /* Grade pill (신호등) */
    .grade-pill {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12.5px; font-weight: 700;
        letter-spacing: 0.02em;
    }}
    .grade-pill.safe    {{ background: rgba(16,185,129,0.16);  color: {C['safe_soft']};    border: 1px solid rgba(52,211,153,0.35); }}
    .grade-pill.caution {{ background: rgba(245,158,11,0.16);  color: {C['caution_soft']}; border: 1px solid rgba(252,211,77,0.35); }}
    .grade-pill.risk    {{ background: rgba(239,68,68,0.18);   color: {C['risk_strong']};  border: 1px solid rgba(248,113,113,0.4);  }}

    /* Reduce motion */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
        }}
    }}
    </style>
    """


def inject_theme() -> None:
    """Inject the full cinematic dark-cosmos CSS. Call once at top of app.py."""
    st.markdown(_theme_css(), unsafe_allow_html=True)


# ── Component helpers ────────────────────────────────────────────

def hero(title_html: str,
         subtitle: str,
         eyebrow: str = "CHEONAN YOUTH · HOUSING SAFETY",
         pills: list[tuple[str, str]] | None = None,
         hint: str = "매물 체크 → 안전지도 → 예산별 추천 → 계약 가이드 → AI 상담",
         mascot_uri: str | None = None,
         cert_line: str | None = None) -> None:
    """Cinematic hero banner.
    - title_html can contain <em>…</em> for gradient accent
    - pills is list of (variant, text) where variant ∈ {'', 'risk', 'caution', 'safe'}
    """
    pills = pills or []
    pills_html = "".join(
        f'<span class="pill {v}">{t}</span>' for v, t in pills
    )
    mascot_html = ""
    if mascot_uri:
        mascot_html = (
            f'<img src="{mascot_uri}" alt="천안시 마스코트 나랑이" '
            f'style="position:absolute;right:28px;bottom:10px;height:170px;'
            f'filter:drop-shadow(0 0 24px rgba(91,140,232,0.40));pointer-events:none;"/>')
    cert_html = ""
    if cert_line:
        cert_html = (f'<div style="margin-top:10px;font-size:0.72rem;color:#6B7280;'
                     f'letter-spacing:0.02em;">{cert_line}</div>')
    _html = (
        f'<div class="hero-cosmic" style="position:relative;">'
        f'{mascot_html}'
        f'<div class="hero-eyebrow">{eyebrow}</div>'
        f'<div class="hero-title">{title_html}</div>'
        f'<div class="hero-sub">{subtitle}</div>'
        f'<div class="hero-pills">{pills_html}</div>'
        f'<div class="hero-hint">↓ {hint}</div>'
        f'{cert_html}'
        f'</div>')
    st.markdown(_html, unsafe_allow_html=True)


def chapter_divider(num: str, title: str) -> None:
    """Ch. 01 style divider with numbered eyebrow + title + gradient rule."""
    st.markdown(f"""
    <div class="chapter-tag">
        <span class="num">CH. {num}</span>
        <span class="title">{title}</span>
        <span class="rule"></span>
    </div>
    """, unsafe_allow_html=True)


def score_bar(value: float, max_value: float = 100.0) -> None:
    """Animated horizontal score bar (0..max_value)."""
    pct = max(0.0, min(1.0, value / max_value)) * 100
    st.markdown(f"""
    <div class="score-bar-wrap">
        <div class="score-bar-fill" style="width:{pct:.1f}%"></div>
    </div>
    """, unsafe_allow_html=True)


def grade_pill(grade: str) -> str:
    """Return HTML for a 신호등 pill. grade ∈ {'빨강','노랑','초록'} or {'risk','caution','safe'}."""
    mapping = {"빨강": ("risk", "위험"), "노랑": ("caution", "주의"), "초록": ("safe", "안전"),
               "risk": ("risk", "위험"), "caution": ("caution", "주의"), "safe": ("safe", "안전")}
    variant, label = mapping.get(grade, ("caution", grade))
    return f'<span class="grade-pill {variant}">● {label}</span>'
