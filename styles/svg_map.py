"""Cinematic SVG choropleth of 천안 31개 행정동.

Benchmark: "새벽 4시의 서울" district map — hand-drawn SVG paths, breathing/glow
animations, hover glow, semantic risk colors on top of a starfield.

Data:
- data/raw/sgis/boundary/34011.geojson  (동남구 17개 행정동)
- data/raw/sgis/boundary/34012.geojson  (서북구 14개 행정동)
- data/processed/dong_safety_score.parquet (65개 법정동 안전점수)

We roll up the legal-dong safety scores to each admin-dong (median), then color the
polygon by its 신호등 등급. Because SGIS boundary polygons come from EPSG:5179 (or
sometimes reprojected to WGS84 depending on export), we auto-detect and fit to the
bounding box of the aggregated feature set.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from styles.cinematic import COLOR

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_BOUNDARY_DIR = _ROOT / "data" / "raw" / "sgis" / "boundary"


# ── Legal-dong → admin-dong bridge ────────────────────────────
# When we only have 행정동 polygons (31), we roll up the 65-legal-dong scores
# by matching the leading token (읍/면 or "(구) + 동" prefix). Anything unmatched
# falls back to the admin-dong that shares the last common name segment.
_ADMIN_TO_LEGAL_HINT = {
    # 동남구 시가지 행정동 → 대표 법정동 (근사 매칭)
    "중앙동":   ["원성동", "사직동", "영성동", "문화동", "구성동"],
    "문성동":   ["문화동", "성황동", "와촌동"],
    "원성1동":  ["원성동"],
    "원성2동":  ["원성동", "봉명동"],
    "봉명동":   ["봉명동"],
    "일봉동":   ["봉명동", "청수동"],
    "신방동":   ["신방동"],
    "청룡동":   ["청당동", "구룡동", "삼룡동", "오룡동", "용곡동"],
    "신안동":   ["안서동", "신부동"],
    # 서북구 시가지
    "성정1동":  ["성정동"],
    "성정2동":  ["성정동"],
    "쌍용1동":  ["쌍용동"],
    "쌍용2동":  ["쌍용동"],
    "쌍용3동":  ["쌍용동"],
    "백석동":   ["백석동"],
    "불당1동":  ["불당동"],
    "불당2동":  ["불당동"],
    "부성1동":  ["부대동", "차암동", "성성동"],
    "부성2동":  ["두정동", "성정동"],
    # 읍/면
    "성환읍":   ["성환읍 송덕리", "성환읍 매주리", "성환읍 성월리", "성환읍 수향리", "성환읍 율금리"],
    "성거읍":   ["성거읍 송남리", "성거읍 요방리", "성거읍 문덕리", "성거읍 신월리",
                "성거읍 오목리", "성거읍 저리", "성거읍 천흥리"],
    "직산읍":   ["직산읍 군서리", "직산읍 삼은리", "직산읍 군동리", "직산읍 모시리",
                "직산읍 부송리", "직산읍 상덕리", "직산읍 수헐리"],
    "입장면":   ["입장면 기로리", "입장면 도림리", "입장면 신덕리", "입장면 하장리"],
    "목천읍":   ["목천읍 삼성리", "목천읍 신계리", "목천읍 서리", "목천읍 운전리", "목천읍 응원리"],
    "북면":     ["북면 상동리", "북면 연춘리"],
    "성남면":   ["성남면 석곡리"],
    "병천면":   ["병천면 병천리", "병천면 가전리", "병천면 탑원리"],
    "풍세면":   ["풍세면 보성리"],
    "광덕면":   [],
    "수신면":   [],
    "동면":     [],
}


def _short_name(adm_nm: str) -> str:
    """'충청남도 천안시 동남구 목천읍' → '목천읍'."""
    return adm_nm.split()[-1]


def _load_features() -> list[dict]:
    feats = []
    for gu_code in ("34011", "34012"):
        path = _BOUNDARY_DIR / f"{gu_code}.geojson"
        if not path.exists():
            continue
        data = json.load(open(path, encoding="utf-8"))
        for f in data.get("features", []):
            f["_gu"] = "동남구" if gu_code == "34011" else "서북구"
            feats.append(f)
    if feats:
        return feats
    # 폴백: 통합 경계 파일 (data/manual/cheonan_emd_2013.geojson, KOSTAT 30개 행정동)
    combined = _ROOT / "data" / "manual" / "cheonan_emd_2013.geojson"
    if combined.exists():
        data = json.load(open(combined, encoding="utf-8"))
        for f in data.get("features", []):
            props = f.setdefault("properties", {})
            code = str(props.get("code", ""))
            # KOSTAT 파일은 'name' 키 사용 → SGIS 포맷('adm_nm')으로 정규화
            props.setdefault("adm_nm", props.get("name", ""))
            f["_gu"] = "동남구" if code.startswith("34011") else "서북구"
            feats.append(f)
    return feats


def _polygon_coords(geom: dict) -> list[list[tuple[float, float]]]:
    """Return list of rings (outer + holes). Handles Polygon / MultiPolygon."""
    t = geom.get("type")
    if t == "Polygon":
        return geom["coordinates"]
    if t == "MultiPolygon":
        rings: list[list[tuple[float, float]]] = []
        for poly in geom["coordinates"]:
            rings.extend(poly)
        return rings
    return []


def _project(x: float, y: float, bounds: tuple[float, float, float, float],
             view_w: int, view_h: int, pad: int = 30) -> tuple[float, float]:
    """Map source (x,y) to SVG viewbox with y-flip."""
    x0, y0, x1, y1 = bounds
    sx = (view_w - 2 * pad) / (x1 - x0)
    sy = (view_h - 2 * pad) / (y1 - y0)
    scale = min(sx, sy)
    # centered
    off_x = pad + ((view_w - 2 * pad) - (x1 - x0) * scale) / 2
    off_y = pad + ((view_h - 2 * pad) - (y1 - y0) * scale) / 2
    return (off_x + (x - x0) * scale,
            off_y + (y1 - y) * scale)


def _ring_to_path(ring: list[tuple[float, float]],
                  bounds: tuple[float, float, float, float],
                  view_w: int, view_h: int) -> str:
    parts = []
    for i, (x, y) in enumerate(ring):
        px, py = _project(x, y, bounds, view_w, view_h)
        parts.append(f"{'M' if i == 0 else 'L'}{px:.1f} {py:.1f}")
    parts.append("Z")
    return " ".join(parts)


def _score_color(score: float) -> tuple[str, str, str]:
    """안전점수 연속 그라데이션: 40(빨강) → 55(주황) → 62(호박) → 72(초록)."""
    stops = [(40, (239, 68, 68)), (52, (249, 115, 22)), (60, (245, 158, 11)), (72, (16, 185, 129))]
    s = max(stops[0][0], min(stops[-1][0], score))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if s <= b:
            t = (s - a) / (b - a) if b > a else 0
            rgb = tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))
            fill = "#%02X%02X%02X" % rgb
            return (fill, fill, f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.45)")
    return ("#10B981", "#10B981", "rgba(16,185,129,0.45)")


def _grade_color(grade: str) -> tuple[str, str, str]:
    """Return (fill, stroke, glow) hex for a 신호등 grade."""
    if grade == "빨강":
        return (COLOR["risk"], COLOR["risk_strong"], "rgba(239,68,68,0.55)")
    if grade == "노랑":
        return (COLOR["caution"], COLOR["caution_soft"], "rgba(245,158,11,0.45)")
    if grade == "초록":
        return (COLOR["safe"], COLOR["safe_soft"], "rgba(16,185,129,0.45)")
    return ("#D7E0EC", "#B9C7DB", "rgba(148,163,184,0.18)")


def _roll_up_scores(dong_scores: pd.DataFrame) -> dict[str, dict]:
    """Aggregate legal-dong scores → per-admin-dong dict.
    key: short admin name  ('원성동', '성환읍', …)
    val: {'score': float, 'grade': str, 'legals': [names], 'top_risk_legal': str}
    """
    result: dict[str, dict] = {}
    by_name = dong_scores.set_index("법정동명")
    for adm_short, legals in _ADMIN_TO_LEGAL_HINT.items():
        matched = [l for l in legals if l in by_name.index]
        if not matched:
            # fallback: any legal dong whose name contains the admin name (읍/면)
            matched = [n for n in by_name.index if adm_short.replace("1동", "동").replace("2동", "동").replace("3동", "동") in n]
        if not matched:
            continue
        sub = by_name.loc[matched]
        score = float(sub["종합안전점수"].median())
        # grade: worst grade among matches (risk > caution > safe)
        grades = sub["신호등"].tolist()
        if "빨강" in grades:
            grade = "빨강"
        elif "노랑" in grades:
            grade = "노랑"
        else:
            grade = "초록"
        top_risk = sub.sort_values("종합안전점수").index[0]
        result[adm_short] = dict(
            score=score, grade=grade,
            legals=matched, top_risk_legal=top_risk,
            n_legal=len(matched),
        )
    return result


def _city_outline_svg(features, bounds, vw, vh, stroke="#2E86E6") -> str:
    """천안시 전체 실루엣 외곽선 — 폴리곤 union의 exterior만 추출 (shapely, 실패 시 생략)."""
    try:
        from shapely.geometry import Polygon as ShPoly
        from shapely.ops import unary_union

        polys = []
        for f in features:
            for ring in _polygon_coords(f["geometry"]):
                if len(ring) >= 4:
                    polys.append(ShPoly(ring).buffer(0))
        merged = unary_union(polys).buffer(0.0008).buffer(-0.0008)
        geoms = getattr(merged, "geoms", [merged])
        out = []
        for g in geoms:
            pts = [_project(x, y, bounds, vw, vh) for x, y in g.exterior.coords]
            d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
            out.append(
                f'<path d="{d}" style="fill:none;stroke:{stroke};stroke-width:1.6;'
                f'filter:drop-shadow(0 0 8px rgba(46,134,230,0.55));opacity:0.9;"></path>')
        return "".join(out)
    except Exception:
        return ""


def render_cinematic_map(dong_scores: pd.DataFrame,
                          view_w: int = 1000, view_h: int = 720,
                          height_px: int = 640) -> None:
    """Render the SVG choropleth into the current Streamlit column."""
    features = _load_features()
    if not features:
        st.warning("행정동 경계 GeoJSON을 찾을 수 없습니다.")
        return

    # 1) find global bounding box across all coordinates
    all_x, all_y = [], []
    for f in features:
        for ring in _polygon_coords(f["geometry"]):
            for x, y in ring:
                all_x.append(x); all_y.append(y)
    bounds = (min(all_x), min(all_y), max(all_x), max(all_y))

    # 2) roll up scores per admin dong
    rollup = _roll_up_scores(dong_scores)

    # 3) build <path> elements
    paths_svg = []
    labels_svg = []
    _risk_anchor = []  # 구도심 위험 폴리곤 중심 (통합 주석용)
    n_polys = len(features)
    for idx, f in enumerate(features):
        adm_short = _short_name(f["properties"]["adm_nm"])
        info = rollup.get(adm_short)
        if info:
            fill, stroke, glow = _score_color(info["score"])
            score_txt = f"{info['score']:.1f}점"
            grade_txt = info["grade"]
            tip = (f"{adm_short}\\n종합안전점수 {score_txt}\\n"
                   f"등급 {grade_txt}\\n포함 법정동 {info['n_legal']}개\\n"
                   f"최취약 {info['top_risk_legal']}")
        else:
            fill, stroke, glow = _grade_color("")
            tip = f"{adm_short}\\n(데이터 없음)"

        # build path (concatenate all rings — outer + holes drawn as sub-paths)
        rings = _polygon_coords(f["geometry"])
        d = " ".join(_ring_to_path(r, bounds, view_w, view_h) for r in rings)

        delay_ms = 60 + idx * 45  # stagger
        breathe = "district-breathe" if info and info["grade"] == "빨강" else "none"

        paths_svg.append(
            f'<path class="district" d="{d}" '
            f'style="fill:{fill}; stroke:{stroke}; '
            f'animation: district-cell-in 0.9s cubic-bezier(.16,1,.3,1) {delay_ms}ms both,'
            f' {breathe} 3.2s ease-in-out {delay_ms + 900}ms infinite;'
            f' --glow:{glow}" '
            f'data-name="{adm_short}" data-tip="{tip}"></path>'
        )

        # label — 위험동은 항상, 그 외는 폴리곤이 충분히 클 때만 (도심 라벨 겹침 방지)
        outer = rings[0]
        _xs = [p[0] for p in outer]; _ys = [p[1] for p in outer]
        _span = (max(_xs) - min(_xs)) * (max(_ys) - min(_ys))
        big_enough = _span > 0.0006  # 경위도 면적 근사 임계
        # 구도심 밀집 소형 동은 개별 라벨 생략 → 아래에서 단일 주석으로 통합
        _OLD_TOWN_CLUSTER = {"원성1동", "원성2동", "중앙동", "문성동", "일봉동", "성정1동", "성정2동"}
        if info and adm_short in _OLD_TOWN_CLUSTER:
            if info["grade"] == "빨강":
                cx = sum(p[0] for p in outer) / len(outer)
                cy = sum(p[1] for p in outer) / len(outer)
                _risk_anchor.append(_project(cx, cy, bounds, view_w, view_h))
        elif info and (info["grade"] == "빨강" or (info["grade"] == "노랑" and big_enough)):
            cx = sum(p[0] for p in outer) / len(outer)
            cy = sum(p[1] for p in outer) / len(outer)
            lx, ly = _project(cx, cy, bounds, view_w, view_h)
            weight = 700 if info["grade"] == "빨강" else 600
            color = COLOR["risk_strong"] if info["grade"] == "빨강" else COLOR["highlight"]
            label_delay = delay_ms + 500
            labels_svg.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                f'style="font-family:Pretendard Variable, sans-serif; '
                f'font-size:12px; font-weight:{weight}; fill:{color}; '
                f'text-shadow: 0 0 6px rgba(255,255,255,0.95), 0 0 12px rgba(255,255,255,0.8); '
                f'animation: detail-slide-up 0.6s cubic-bezier(.16,1,.3,1) {label_delay}ms both; '
                f'pointer-events:none;">{adm_short}</text>'
            )

    labels_svg.insert(0, _city_outline_svg(features, bounds, view_w, view_h))

    if _risk_anchor:
        _ax = sum(p[0] for p in _risk_anchor) / len(_risk_anchor)
        _ay = sum(p[1] for p in _risk_anchor) / len(_risk_anchor)
        _tx, _ty = min(_ax + 150, view_w - 210), max(_ay - 68, 40)
        labels_svg.append(
            f'<line x1="{_ax:.0f}" y1="{_ay:.0f}" x2="{_tx - 6:.0f}" y2="{_ty + 14:.0f}" '
            f'style="stroke:{COLOR["risk_strong"]};stroke-width:1.4;stroke-dasharray:4 3;"></line>'
            f'<text x="{_tx:.0f}" y="{_ty:.0f}" style="font-size:14px;font-weight:800;'
            f'fill:{COLOR["risk_strong"]};paint-order:stroke;stroke:rgba(255,255,255,0.95);stroke-width:4px;">'
            f'원성동 일대 (구도심)</text>'
            f'<text x="{_tx:.0f}" y="{_ty + 17:.0f}" style="font-size:11px;font-weight:600;'
            f'fill:#C2414F;paint-order:stroke;stroke:rgba(255,255,255,0.95);stroke-width:3px;">'
            f'전세사기 288세대 피해 진앙 · 8축 위험 1개 동</text>')

    C = COLOR
    html = f"""
    <div class="cinema-map-wrap" style="position:relative;">
      <!-- header row (legend) -->
      <div style="display:flex; align-items:center; justify-content:space-between;
                  margin-bottom:12px; padding: 0 4px;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:11px;
                    letter-spacing:0.28em; color:{C['primary_soft']}; opacity:0.85;">
          CH. 02 · SAFETY MAP — 천안 31개 행정동
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <span style="font-size:10px; color:#94A3B8;">위험 40점</span>
          <span style="width:120px; height:10px; border-radius:5px; display:inline-block;
                background:linear-gradient(90deg,#EF4444,#F97316,#F59E0B,#10B981);"></span>
          <span style="font-size:10px; color:#94A3B8;">72점 안전</span>
          <span style="width:12px; height:12px; border-radius:3px; display:inline-block;
                background:#D7E0EC; margin-left:6px;"></span>
          <span style="font-size:10px; color:#94A3B8;">거래표본 부족</span>
        </div>
      </div>

      <!-- map canvas -->
      <div style="position:relative; border-radius:20px; overflow:hidden;
                  border:1px solid rgba(110,168,232,0.18);
                  box-shadow: 0 12px 36px rgba(23,64,133,0.10);
                  background:
                    radial-gradient(ellipse 700px 500px at 25% 30%, rgba(46,134,230,0.16), transparent 60%),
                    radial-gradient(ellipse 600px 400px at 80% 75%, rgba(245,158,11,0.05), transparent 60%),
                    radial-gradient(ellipse at 50% 50%, {C['bg_nebula']} 0%, {C['bg_deep']} 90%);">

        <!-- star layer -->
        <div style="position:absolute; inset:0; opacity:0.5; pointer-events:none;
          background-image:
            radial-gradient(1.2px 1.2px at 12% 18%, rgba(255,255,255,0.9), transparent),
            radial-gradient(1px 1px at 55% 12%, rgba(110,168,232,0.85), transparent),
            radial-gradient(1.4px 1.4px at 82% 22%, rgba(255,233,168,0.75), transparent),
            radial-gradient(1px 1px at 22% 68%, rgba(255,255,255,0.7), transparent),
            radial-gradient(1.3px 1.3px at 68% 82%, rgba(110,168,232,0.8), transparent),
            radial-gradient(1px 1px at 90% 55%, rgba(255,255,255,0.65), transparent);
          animation: star-twinkle 4.5s ease-in-out infinite;"></div>

        <svg viewBox="0 0 {view_w} {view_h}" preserveAspectRatio="xMidYMid meet"
             style="width:100%; height:{height_px}px; display:block;">
          <defs>
            <filter id="district-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>
          <style>
            .district {{
              stroke-width: 1.2;
              opacity: 0.92;
              transition: fill 0.35s ease, filter 0.35s ease,
                          stroke 0.35s ease, transform 0.35s cubic-bezier(.16,1,.3,1);
              cursor: pointer;
              transform-box: fill-box;
              transform-origin: center;
            }}
            .district:hover {{
              filter: drop-shadow(0 0 12px var(--glow));
              stroke: {C['primary_soft']};
              stroke-width: 2;
              transform: scale(1.02);
            }}
          </style>
          {''.join(paths_svg)}
          {''.join(labels_svg)}
        </svg>

        <!-- floating tooltip -->
        <div id="cinema-tip" style="position:absolute; pointer-events:none;
             padding:10px 14px; border-radius:12px; opacity:0;
             background: rgba(20,16,25,0.94); backdrop-filter: blur(8px);
             border:1px solid rgba(110,168,232,0.35);
             color:{C['fg']}; font-size:12.5px; font-weight:500; line-height:1.55;
             white-space:pre-line; box-shadow: 0 12px 32px rgba(0,0,0,0.5);
             transition: opacity 0.18s ease, transform 0.2s cubic-bezier(.16,1,.3,1);
             transform: translateY(4px); z-index:10;">동네 hover</div>
      </div>

      <div style="text-align:center; margin-top:14px; color:{C['fg_subtle']};
                  font-size:12px; letter-spacing:0.04em;">
        65개 법정동 안전점수를 행정동 단위로 집계 · 국토부 실거래 10.3만 건(102,671건) + 건축물대장 기반
        · 붉게 맥동하는 곳이 위험 동네입니다
      </div>
    </div>

    <script>
      (function() {{
        const tip = document.getElementById('cinema-tip');
        const svg = document.querySelector('.cinema-map-wrap svg');
        if (!tip || !svg) return;
        svg.querySelectorAll('.district').forEach(el => {{
          el.addEventListener('mousemove', (e) => {{
            const rect = svg.getBoundingClientRect();
            tip.style.left = (e.clientX - rect.left + 14) + 'px';
            tip.style.top  = (e.clientY - rect.top  + 14) + 'px';
            tip.style.opacity = 1;
            tip.style.transform = 'translateY(0)';
            tip.textContent = el.getAttribute('data-tip').replace(/\\\\n/g, '\\n');
          }});
          el.addEventListener('mouseleave', () => {{
            tip.style.opacity = 0;
            tip.style.transform = 'translateY(4px)';
          }});
        }});
      }})();
    </script>
    """

    # Streamlit's st.markdown sanitizer strips <script> and mangles <style> inside
    # <svg>. Render inside components.html (iframe) so the SVG paths + inline
    # style + JS tooltip all survive intact.
    full_doc = f"""<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" as="style" crossorigin
      href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<style>
  html, body {{
    margin:0; padding:0; background: transparent;
    font-family: 'Pretendard Variable', -apple-system, sans-serif;
    color: {COLOR['fg']};
  }}
  @keyframes district-cell-in {{
    from {{ opacity: 0; transform: translateY(8px) scale(0.985); }}
    to   {{ opacity: 0.92; transform: none; }}
  }}
  @keyframes district-breathe {{
    0%, 100% {{ filter: drop-shadow(0 0 0px var(--glow)); }}
    50%      {{ filter: drop-shadow(0 0 14px var(--glow)); }}
  }}
  @keyframes detail-slide-up {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: none; }}
  }}
  @keyframes star-twinkle {{
    0%, 100% {{ opacity: 0.5; }} 50% {{ opacity: 0.8; }}
  }}
  .grade-pill {{
    padding: 4px 10px; border-radius: 999px; font-size: 11px;
    letter-spacing: 0.06em; font-weight: 600;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(20,16,25,0.7);
  }}
  .grade-pill.safe    {{ color: {COLOR['safe']}; }}
  .grade-pill.caution {{ color: {COLOR['caution']}; }}
  .grade-pill.risk    {{ color: {COLOR['risk']}; }}
</style>
</head><body>
{html}
</body></html>"""

    components.html(full_doc, height=height_px + 120, scrolling=False)


def render_reco_svg(selected: list[dict], height_px: int = 430) -> None:
    """예산별 추천용 오프라인 SVG 지도 — 추천 동만 하이라이트 (타일 CDN 무의존).

    selected: [{"법정동명", "rank"(1~), "score", "grade"(신호등)}]
    """
    import streamlit as st

    features = _load_features()
    if not features:
        st.info("경계 데이터를 찾을 수 없어 지도를 생략합니다.")
        return

    all_x, all_y = [], []
    for f in features:
        for ring in _polygon_coords(f["geometry"]):
            for x, y in ring:
                all_x.append(x); all_y.append(y)
    bounds = (min(all_x), min(all_y), max(all_x), max(all_y))
    vw, vh = 1000, 640

    def _match(adm_short: str, legal: str) -> bool:
        base = adm_short.replace("1동", "동").replace("2동", "동").replace("3동", "동")
        if adm_short.endswith(("읍", "면")):
            return legal.startswith(adm_short)
        return base in legal or legal in base

    sel_by_admin: dict[str, dict] = {}
    for f in features:
        adm = _short_name(f["properties"]["adm_nm"])
        for it in selected:
            if _match(adm, it["법정동명"]) and adm not in sel_by_admin:
                sel_by_admin[adm] = it

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    paths, labels = [], []
    for f in features:
        adm = _short_name(f["properties"]["adm_nm"])
        rings = _polygon_coords(f["geometry"])
        d = " ".join(_ring_to_path(r, bounds, vw, vh) for r in rings)
        hit = sel_by_admin.get(adm)
        if hit:
            fill, _, glow = _grade_color(hit.get("grade", "초록"))
            paths.append(f'<path d="{d}" style="fill:{fill};stroke:#fff;stroke-width:1.4;'
                         f'filter:drop-shadow(0 0 10px {glow});"></path>')
            outer = rings[0]
            cx = sum(p[0] for p in outer) / len(outer)
            cy = sum(p[1] for p in outer) / len(outer)
            lx, ly = _project(cx, cy, bounds, vw, vh)
            tag = medals.get(hit["rank"], f"{hit['rank']}위")
            _dy = -12 if hit["rank"] % 2 == 0 else 0  # 인접 라벨 세로 엇갈림
            labels.append(
                f'<text x="{lx:.0f}" y="{ly + _dy:.0f}" text-anchor="middle" style="font-size:15px;'
                f'font-weight:800;fill:#16233A;paint-order:stroke;stroke:#fff;stroke-width:3.5px;">'
                f'{tag} {hit["법정동명"].split()[-1]}</text>'
                f'<text x="{lx:.0f}" y="{ly + _dy + 18:.0f}" text-anchor="middle" style="font-size:12.5px;'
                f'font-weight:800;fill:#16233A;paint-order:stroke;stroke:#fff;stroke-width:3.5px;">'
                f'{hit["score"]:.0f}점</text>')
        else:
            paths.append(f'<path d="{d}" style="fill:#E3EBF6;stroke:#C7D4E6;stroke-width:0.8;"></path>')

    outline = _city_outline_svg(features, bounds, vw, vh)
    html = (f'<div style="border-radius:16px;overflow:hidden;border:1px solid #C9D8EC;'
            f'background:#F2F7FD;">'
            f'<svg viewBox="0 0 {vw} {vh}" style="width:100%;height:{height_px}px;display:block;">'
            + "".join(paths) + outline + "".join(labels) + "</svg></div>")
    st.markdown(html, unsafe_allow_html=True)
