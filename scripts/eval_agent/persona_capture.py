#!/usr/bin/env python3
"""페르소나 시나리오별 웹 화면 캡처 v3 — PPT용 '핵심 영역 타이트 크롭'.

원칙 (PPT 사이클 1 반영):
- 풀샷 금지: 각 컷은 시나리오의 결정적 요소들만 담은 크롭 (min 860×360)
- 강조(빨간 박스)는 결정 수치·버튼에만, 크롭 범위는 crop_targets로 별도 지정
- 상태 검증: 예산 버튼 등은 클릭 후 화면 텍스트로 확인, 실패 시 재클릭
출력: presentation/screenshots/persona/{P}/{step}.png
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "presentation" / "screenshots" / "persona"
URL = "http://localhost:8501"
VW, VH = 1920, 1080

TAB = {"체크": 0, "지도": 1, "탐색": 2, "추천": 3, "가이드": 4, "상담": 5, "데이터": 6}


def _loc(page, kind: str, value: str):
    if kind == "text":
        return page.get_by_text(re.compile(value)).last
    if kind == "button":
        return page.get_by_role("button", name=re.compile(value)).first
    if kind == "css_last":
        return page.locator(value).last
    return page.locator(value).first


def _box_of(page, kind: str, value: str, pad: int = 14, grow_w: int = 0, grow_h: int = 0):
    try:
        b = _loc(page, kind, value).bounding_box(timeout=4000)
        if not b:
            return None
        x0 = max(0, b["x"] - pad); y0 = max(0, b["y"] - pad)
        x1 = min(VW - 2, b["x"] + b["width"] + pad + grow_w)
        y1 = min(VH - 2, b["y"] + b["height"] + pad + grow_h)
        if x1 - x0 < 10 or y1 - y0 < 10:
            return None
        return (x0, y0, x1, y1)
    except Exception as e:
        print(f"  (박스 '{value}' 실패: {type(e).__name__})", file=sys.stderr)
        return None


def annotate(path: Path, boxes: list[tuple]):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert("RGB")
    dr = ImageDraw.Draw(im)
    RED = (232, 28, 46)
    try:
        font = ImageFont.truetype(str(ROOT / "presentation/assets/Pretendard-Bold.otf"), 26)
    except Exception:
        font = ImageFont.load_default()
    for i, bx in enumerate([b for b in boxes if b], 1):
        x0, y0, x1, y1 = bx
        for w_off, col in [(8, (255, 120, 130)), (0, RED)]:
            dr.rounded_rectangle([x0 - w_off/2, y0 - w_off/2, x1 + w_off/2, y1 + w_off/2],
                                 radius=14, outline=col, width=5 if w_off == 0 else 3)
        cx, cy = x0 + 4, max(22, y0 - 4)
        dr.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=RED)
        dr.text((cx, cy - 2), str(i), fill="white", font=font, anchor="mm")
    im.save(path)


def shot(page, folder: Path, name: str,
         highlights: list[tuple] | None = None,
         crop_targets: list[tuple] | None = None,
         full_width: bool = False, crop_left: int | None = None,
         crop_pad: int = 42, min_w: int = 860, min_h: int = 360):
    folder.mkdir(parents=True, exist_ok=True)
    time.sleep(1.2)
    hl = [b for b in (_box_of(page, *s[:2], **(s[2] if len(s) > 2 else {}))
                      for s in (highlights or [])) if b]
    ct = [b for b in (_box_of(page, *s[:2], **(s[2] if len(s) > 2 else {}))
                      for s in (crop_targets or [])) if b]
    allb = hl + ct
    path = folder / f"{name}.png"
    page.screenshot(path=str(path))
    if hl:
        annotate(path, hl)
    if allb:
        from PIL import Image
        x0 = min(b[0] for b in allb) - crop_pad
        y0 = min(b[1] for b in allb) - crop_pad
        x1 = max(b[2] for b in allb) + crop_pad
        y1 = max(b[3] for b in allb) + crop_pad
        if full_width:
            x0, x1 = 60, VW - 60
        if crop_left is not None:
            x0 = crop_left; x1 = VW - 60
        x0 = max(0, x0); y0 = max(0, y0); x1 = min(VW, x1); y1 = min(VH, y1)
        if x1 - x0 < min_w:
            x0 = max(0, x1 - min_w) if x0 > 0 else x0
            x1 = min(VW, x0 + min_w)
        if y1 - y0 < min_h:
            y0 = max(0, y1 - min_h) if y0 > 0 else y0
            y1 = min(VH, y0 + min_h)
        im = Image.open(path)
        im.crop((int(x0), int(y0), int(x1), int(y1))).save(path)
        print(f"  ✓ {name}.png ({int(x1-x0)}×{int(y1-y0)})")
    else:
        print(f"  ✓ {name}.png (풀샷 — 크롭 타깃 전부 실패!)", file=sys.stderr)


def dismiss_dialog(page):
    """첫 로드 시 뜨는 안내 모달 닫기 (탭 클릭 가로챔 방지)."""
    try:
        if page.locator("[data-testid=stDialog]").count() > 0:
            page.keyboard.press("Escape"); time.sleep(0.5)
            for sel in ("[data-testid=stDialog] button[aria-label='Close']",
                        "[data-testid=stDialog] button"):
                loc = page.locator(sel)
                if loc.count() > 0:
                    loc.first.click(timeout=2000); time.sleep(0.6); break
    except Exception:
        pass


def goto_tab(page, key: str, wait: float = 7):
    for _ in range(3):
        dismiss_dialog(page)
        try:
            page.get_by_role("tab").nth(TAB[key]).click(timeout=5000)
            break
        except Exception:
            time.sleep(1.5)
    time.sleep(wait)


def scroll_to(page, text: str, up_px: int = 120) -> bool:
    try:
        el = page.get_by_text(re.compile(text)).last
        el.scroll_into_view_if_needed(timeout=5000)
        page.evaluate(
            "(px) => { const m = document.querySelector('[data-testid=stMain]');"
            " if (m) m.scrollBy(0, -px); }", up_px)
        time.sleep(1.0)
        return True
    except Exception as e:
        print(f"  (스크롤 '{text}' 실패: {type(e).__name__})", file=sys.stderr)
        return False


def scroll_top(page):
    page.evaluate("() => { const m = document.querySelector('[data-testid=stMain]'); if (m) m.scrollTo(0, 0); }")
    time.sleep(0.8)


def click_verified(page, btn: str, expect: str, wait: float = 9, retries: int = 2) -> bool:
    """버튼 클릭 후 기대 텍스트가 나타날 때까지 재시도 (Streamlit rerun 레이스 방지)."""
    for _ in range(retries):
        try:
            page.get_by_role("button", name=re.compile(btn)).first.click(timeout=5000)
        except Exception as e:
            print(f"  (버튼 '{btn}' 클릭 실패: {type(e).__name__})", file=sys.stderr)
        time.sleep(wait)
        try:
            page.get_by_text(re.compile(expect)).first.wait_for(timeout=4000)
            return True
        except Exception:
            continue
    print(f"  (상태검증 '{expect}' 실패)", file=sys.stderr)
    return False


def chat_ask(page, question: str, wait: float = 40):
    box = page.locator("textarea").last
    box.fill(question)
    box.press("Enter")
    time.sleep(wait)


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ══ P1 김가성 ══
        pg = browser.new_page(viewport={"width": VW, "height": VH})
        pg.goto(URL, wait_until="domcontentloaded", timeout=90000); time.sleep(10); dismiss_dialog(pg)
        d = OUT / "P1_김가성_가성비형"
        scroll_top(pg)
        shot(pg, d, "01_홈_히어로_첫인상",
             highlights=[("css", ".hero-pills"), ("css", "img[alt='천안시']", {"pad": 10})],
             crop_targets=[("css", ".hero-cosmic", {"pad": 6})])
        goto_tab(pg, "탐색")
        try:
            _inp = pg.locator("input[aria-label='단지·동네 검색']")
            _inp.fill("성환"); _inp.press("Enter"); time.sleep(6)
        except Exception:
            pass
        scroll_to(pg, r"개 단지", up_px=60)
        shot(pg, d, "02_매물탐색_외곽_저가검색",
             highlights=[("css", "input[aria-label='단지·동네 검색']"),
                         ("text", r"개 단지", {"pad": 8, "grow_w": 120})],
             crop_targets=[("text", r"개 단지", {"grow_h": 560})], full_width=True)
        goto_tab(pg, "체크")
        # SHAP 차트(=왜)가 결과 하단이므로 그 캡션까지 보이게 스크롤·크롭
        scroll_to(pg, r"빨간 막대.*위험", up_px=470)
        shot(pg, d, "03_내매물체크_진단결과",
             highlights=[("text", r"주의 — 위험확률 44", {"pad": 10, "grow_w": 240}),
                         ("text", r"위험/안전 판단 근거", {"pad": 12, "grow_w": 980, "grow_h": 300})],
             crop_targets=[("text", r"주의 — 위험확률 44", {"grow_w": 900}),
                           ("text", r"빨간 막대.*위험", {"grow_w": 300})],
             full_width=True, min_h=430)
        goto_tab(pg, "지도")
        scroll_to(pg, r"천안시 동네별 안전지도", up_px=40)
        shot(pg, d, "04_안전지도_동네확인",
             highlights=[("text", r"원성동 일대", {"pad": 22, "grow_w": 70, "grow_h": 34})],
             crop_targets=[("text", r"천안시 동네별 안전지도", {"grow_h": 880})],
             full_width=True, min_h=700)
        pg.close()

        # ══ P2 박안심 ══
        pg = browser.new_page(viewport={"width": VW, "height": VH})
        pg.goto(URL, wait_until="domcontentloaded", timeout=90000); time.sleep(10); dismiss_dialog(pg)
        d = OUT / "P2_박안심_안전통근형"
        goto_tab(pg, "추천")
        click_verified(pg, "1억", r"1억 예산")
        scroll_to(pg, r"1억 예산", up_px=60)
        # 좌측 '내 조건'(슬라이더 5000) 배제 → 우측 추천 패널만 크롭 (예산모순 시각 제거)
        _rc = _box_of(pg, "text", r"추천 동네", pad=8)
        _rx0 = int(_rc[0]) if _rc else 600
        shot(pg, d, "01_예산별추천_1억_랭킹",
             highlights=[("text", r"1억 예산으로 가장 안전", {"pad": 12, "grow_w": 40}),
                         ("text", r"최고 추천", {"pad": 22, "grow_w": 1000, "grow_h": 26}),
                         ("text", r"개 동을 추천에서 제외", {"pad": 10, "grow_w": 120})],
             crop_targets=[("text", r"추천 동네", {"pad": 12}),
                           ("text", r"개 동을 추천에서 제외", {"grow_w": 200})],
             crop_left=_rx0 - 20, min_h=560)
        goto_tab(pg, "탐색")
        click_verified(pg, "KTX", r"프리셋 필터 적용")
        # 안전최우선 페르소나: 신호등 필터를 초록·노랑만 (심각/위험 태그 해제)
        try:
            for lab in ("심각", "위험"):
                tag = pg.locator(f"[data-baseweb=tag]:has-text('{lab}')").first
                if tag.count() > 0:
                    tag.locator("span[role=presentation], svg").last.click(timeout=2500); time.sleep(2)
        except Exception as e:
            print(f"  (신호등 해제 실패: {type(e).__name__})", file=__import__('sys').stderr)
        time.sleep(3)
        scroll_to(pg, r"프리셋 필터 적용", up_px=120)
        shot(pg, d, "02_매물탐색_KTX프리셋",
             highlights=[("button", "KTX", {"pad": 8}),
                         ("text", r"프리셋 필터 적용", {"pad": 10, "grow_w": 260})],
             crop_targets=[("text", r"위험확률 .*%", {"grow_h": 120})], full_width=True)
        goto_tab(pg, "상담")
        chat_ask(pg, "불당동 치안이랑 안전점수 어때? KTX로 서울 출퇴근할 예정이야")
        scroll_to(pg, r"불당동의 동네 종합|치안", up_px=60)
        shot(pg, d, "03_AI상담_치안질문_실응답",
             highlights=[("text", r"치안 축 점수는 80\.8|80\.8/100", {"pad": 9, "grow_w": 30}),
                         ("text", r"종합안전점수는 71\.5|71\.5/100", {"pad": 9, "grow_w": 30})],
             crop_targets=[("css_last", "[data-testid=stChatMessage]", {"pad": 8})],
             full_width=False, min_w=1200, min_h=380)
        goto_tab(pg, "가이드")
        scroll_to(pg, r"천안시 안심계약 도움서비스|안심계약 도움서비스", up_px=140)
        shot(pg, d, "04_계약가이드_체크리스트",
             highlights=[("text", r"안심계약 도움서비스", {"pad": 14, "grow_w": 40})],
             crop_targets=[("text", r"HUG 전세보증금 반환보증", {"pad": 14, "grow_w": 40}),
                           ("text", r"청년월세지원", {"pad": 14, "grow_w": 40})],
             full_width=True, min_h=300)
        pg.close()

        # ══ P3 이새내 ══
        pg = browser.new_page(viewport={"width": VW, "height": VH})
        pg.goto(URL, wait_until="domcontentloaded", timeout=90000); time.sleep(10); dismiss_dialog(pg)
        d = OUT / "P3_이새내_대학새내기형"
        goto_tab(pg, "상담")
        click_verified(pg, "안서동 5000만원", r"안서동 보증금|안서동.*위험확률", wait=48, retries=2)
        scroll_to(pg, r"안서동 보증금|안서동.*위험확률|안서동", up_px=60)
        shot(pg, d, "01_AI상담_안서동진단",
             highlights=[("text", r"위험확률은 7\d\.\d?%", {"pad": 8, "grow_w": 120}),
                         ("text", r"신호등.*빨강.*위험", {"pad": 8, "grow_w": 60})],
             crop_targets=[("css_last", "[data-testid=stChatMessage]", {"pad": 10})],
             full_width=False, min_h=360)
        goto_tab(pg, "탐색")
        click_verified(pg, "단국대", r"프리셋 필터 적용")
        scroll_to(pg, r"프리셋 필터 적용", up_px=120)
        shot(pg, d, "02_매물탐색_대학가프리셋",
             highlights=[("button", "단국대", {"pad": 8}),
                         ("text", r"프리셋 필터 적용", {"pad": 10, "grow_w": 260})],
             crop_targets=[("text", r"위험확률 .*%", {"grow_h": 120})], full_width=True)
        goto_tab(pg, "추천")
        click_verified(pg, "5천만", r"5,000만원 예산")
        scroll_to(pg, r"5,000만원 예산", up_px=60)
        shot(pg, d, "03_예산추천_5천만",
             highlights=[("button", "5천만", {"pad": 8}),
                         ("text", r"최고 추천", {"pad": 22, "grow_w": 1000, "grow_h": 26}),
                         ("text", r"개 동을 추천에서 제외", {"pad": 10, "grow_w": 120})],
             crop_targets=[("text", r"5,000만원 예산", {"pad": 18, "grow_w": 500}),
                           ("text", r"개 동을 추천에서 제외", {"grow_w": 200})],
             full_width=True, min_h=560)
        goto_tab(pg, "가이드")
        scroll_to(pg, r"천안시 안심계약 도움서비스|안심계약 도움서비스", up_px=140)
        shot(pg, d, "04_계약가이드_정책CTA",
             highlights=[("text", r"청년월세지원", {"pad": 14, "grow_w": 40}),
                         ("text", r"안심계약 도움서비스", {"pad": 14, "grow_w": 40})],
             crop_targets=[("text", r"HUG 전세보증금 반환보증", {"pad": 14, "grow_w": 40})],
             full_width=True, min_h=300)
        pg.close()

        browser.close()
    print("완료 →", OUT)


if __name__ == "__main__":
    main()
