"""
Streamlit 앱 자동 캡처 스크립트 — PPT용 스크린샷 생성
─────────────────────────────────────────────────
사용:
    # 1) 사전에 앱 실행 (별도 터미널)
    streamlit run app.py --server.port 8502

    # 2) 캡처 실행
    .venv/bin/python presentation/capture_screenshots.py

출력: presentation/screenshots/*.png
"""
from __future__ import annotations
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

APP_URL = "http://localhost:8502"
VIEWPORT = {"width": 1600, "height": 1000}


def _click_tab(page, label: str):
    page.locator(f'button[role="tab"]:has-text("{label}")').first.click()
    time.sleep(1.5)


def _wait_ready(page, timeout_s: float = 15):
    """Streamlit 로딩(spinner + running) 완료 대기."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            spin = page.locator('div[data-testid="stSpinner"]').count()
            running = page.locator('div[data-testid="stStatusWidget"]').count()
            if spin == 0 and running == 0:
                break
        except Exception:
            break
        time.sleep(0.4)
    time.sleep(0.8)


def _scroll_to_bottom_then_top(page):
    """페이지 전체를 훑어 lazy 컴포넌트(folium, plotly)를 강제로 렌더."""
    page.evaluate("""
        () => new Promise(r => {
            let y = 0;
            const step = 400;
            const timer = setInterval(() => {
                window.scrollBy(0, step);
                y += step;
                if (y > document.body.scrollHeight + 2000) {
                    clearInterval(timer);
                    window.scrollTo(0, 0);
                    r();
                }
            }, 120);
        })
    """)
    time.sleep(1.5)


def _scroll_to(page, y: int):
    page.evaluate(f"window.scrollTo(0, {y})")
    time.sleep(0.6)


def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(APP_URL, wait_until="networkidle", timeout=60_000)
        _wait_ready(page)

        # ── 0. Hero ──
        _scroll_to(page, 0)
        page.screenshot(path=str(OUT / "fig_Hero.png"))
        print("✓ fig_Hero.png")

        # ── 1. Tab: 내 매물 체크 ──
        _click_tab(page, "내 매물 체크")
        _wait_ready(page)
        # 예시 시나리오 선택 (자동 실행)
        try:
            preset = page.locator('div[data-testid="stSelectbox"]:has-text("예시 시나리오")').first
            preset.click(timeout=3000)
            time.sleep(0.6)
            # Streamlit 드롭다운 옵션 (role=option) 우선
            opt = page.locator('div[role="option"]:has-text("대학가 원룸")').first
            if opt.count() == 0:
                opt = page.locator('li:has-text("대학가 원룸")').first
            opt.click(timeout=4000)
            time.sleep(3.5)
        except Exception as e:
            print(f"  (프리셋 skip: {e})")
        # 위험도 체크 버튼 명시 클릭 (프리셋 자동실행이 안 되는 경우 대비)
        try:
            btn = page.locator('button:has-text("위험도 체크")').first
            if btn.count() > 0:
                btn.click(timeout=3000)
                time.sleep(4.0)
        except Exception:
            pass
        _wait_ready(page, timeout_s=25)
        _scroll_to_bottom_then_top(page)
        page.screenshot(path=str(OUT / "fig_Tab1_Simulator.png"), full_page=True)
        print("✓ fig_Tab1_Simulator.png")

        # ── 2. Tab: 안전지도 ──
        _click_tab(page, "안전지도")
        _wait_ready(page)
        # folium iframe 로딩 대기 (st_folium은 iframe 안에 folium 렌더)
        page.wait_for_function(
            "() => document.querySelectorAll('iframe').length > 0",
            timeout=15_000,
        )
        time.sleep(3.0)
        # 전체 스크롤로 lazy 요소 강제 렌더
        _scroll_to_bottom_then_top(page)
        # 지도가 위쪽에 오도록 스크롤
        _scroll_to(page, 700)
        time.sleep(2.5)  # 타일 로드 여유
        page.screenshot(path=str(OUT / "fig_Tab2_SafetyMap.png"))
        print("✓ fig_Tab2_SafetyMap.png (지도 뷰)")

        # 동네 상세 (Google Roadmap 포함) — selectbox 우클릭
        try:
            # 아래로 스크롤 해서 "동네 선택" selectbox 를 뷰포트에 노출
            _scroll_to(page, 1600)
            time.sleep(0.8)
            sel = page.locator('div[data-testid="stSelectbox"]:has(label:has-text("동네 선택"))').first
            if sel.count() == 0:
                sel = page.locator('div[data-testid="stSelectbox"]:has-text("동네 선택")').last
            sel.scroll_into_view_if_needed(timeout=3000)
            time.sleep(0.3)
            sel.click(timeout=4000)
            time.sleep(0.8)
            # listbox 오픈 대기
            page.wait_for_selector('div[role="listbox"]', timeout=4000)
            opt = page.locator('div[role="option"]:has-text("두정동")').first
            opt.click(timeout=4000)
            # rerun 대기
            _wait_ready(page, timeout_s=8)
            time.sleep(4.0)  # Google Maps iframe 로딩
            _scroll_to_bottom_then_top(page)
            # 동 상세 영역이 보이는 y로
            _scroll_to(page, 1900)
            time.sleep(2.0)
            page.screenshot(path=str(OUT / "fig_Tab2_DongDetail.png"))
            print("✓ fig_Tab2_DongDetail.png (동 상세+Google Map)")
        except Exception as e:
            print(f"  (동 상세 skip: {e})")
        _scroll_to(page, 0)

        # ── 3. Tab: 예산별 추천 ──
        try:
            _click_tab(page, "예산별 추천")
            _wait_ready(page)
            _scroll_to_bottom_then_top(page)
            page.screenshot(path=str(OUT / "fig_Tab3_Budget.png"), full_page=True)
            print("✓ fig_Tab3_Budget.png")
        except Exception as e:
            print(f"× 예산별 추천 skip: {e}")

        # ── 4. Tab: 계약 가이드 ──
        try:
            _click_tab(page, "계약 가이드")
            _wait_ready(page)
            _scroll_to_bottom_then_top(page)
            page.screenshot(path=str(OUT / "fig_Tab4_Guide.png"), full_page=True)
            print("✓ fig_Tab4_Guide.png")
        except Exception as e:
            print(f"× 계약 가이드 skip: {e}")

        # ── 5. Tab: AI 상담 (RAG 챗봇) ──
        _click_tab(page, "AI 상담")
        _wait_ready(page)
        try:
            page.locator('summary:has-text("챗봇 아키텍처")').first.click(timeout=3000)
            time.sleep(0.6)
        except Exception:
            pass
        _scroll_to_bottom_then_top(page)
        page.screenshot(path=str(OUT / "fig_Tab5_ChatbotArchitecture.png"), full_page=True)
        print("✓ fig_Tab5_ChatbotArchitecture.png")

        # 실제 질문 → 응답 대기 → 캡처
        try:
            chat_input = page.locator('div[data-testid="stChatInput"] textarea').first
            chat_input.click()
            chat_input.fill("두정동 이 지역이 왜 위험한거야? 최근에 뭐 이슈있나")
            time.sleep(0.3)
            page.keyboard.press("Enter")
            # 응답 완료 대기: '검색·추론 중...' spinner가 없어질 때까지
            deadline = time.time() + 60
            while time.time() < deadline:
                spin_txt = page.locator('text=검색·추론 중').count()
                if spin_txt == 0:
                    break
                time.sleep(1.0)
            # 그리고 뉴스 링크 렌더 여유
            time.sleep(3.0)
            _scroll_to_bottom_then_top(page)
            page.screenshot(path=str(OUT / "fig_Tab5_ChatbotAnswer.png"), full_page=True)
            print("✓ fig_Tab5_ChatbotAnswer.png (뉴스 인용)")
        except Exception as e:
            print(f"× 챗봇 답변 캡처 실패: {e}")

        browser.close()


if __name__ == "__main__":
    print(f"[capture] target = {APP_URL}")
    print(f"[capture] output = {OUT}")
    capture_all()
    print("\n완료. 스크린샷을 확인하세요.")
