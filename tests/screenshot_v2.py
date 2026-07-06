"""스크린샷 v2 — 긴 뷰포트 + 내부 스크롤로 Streamlit 전체 캡처"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def capture_tab(page, tab_text, prefix, scroll_positions=None):
    """탭 클릭 → 여러 스크롤 위치에서 스크린샷"""
    tab_btn = page.locator(f'button[role="tab"]:has-text("{tab_text}")')
    if tab_btn.count() == 0:
        print(f"  WARN: Tab '{tab_text}' not found")
        return
    tab_btn.first.click()
    time.sleep(4)

    if scroll_positions is None:
        scroll_positions = [0]

    for i, pos in enumerate(scroll_positions):
        # Streamlit 메인 컨테이너 내부 스크롤
        page.evaluate(f"""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = {pos};
            else window.scrollTo(0, {pos});
        """)
        time.sleep(1.5)
        suffix = f"_{i}" if len(scroll_positions) > 1 else ""
        path = str(OUT / f"{prefix}{suffix}.png")
        page.screenshot(path=path)
        print(f"  {prefix}{suffix}.png (scroll={pos})")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 긴 뷰포트로 더 많은 콘텐츠 캡처
        page = browser.new_page(viewport={"width": 1400, "height": 3000})

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # 탭1: 매물 체크 — 데모 프리셋 선택
        print("=== Tab 1: 매물 체크 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)

        # 데모 시나리오 선택
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 1:
                options.nth(1).click()
                time.sleep(5)

        page.screenshot(path=str(OUT / "v2_01_check.png"))
        print("  v2_01_check.png")

        # 탭2: 안전지도
        print("=== Tab 2: 안전지도 ===")
        capture_tab(page, "🗺️ 안전지도", "v2_02_map")

        # 탭3: 예산별 추천
        print("=== Tab 3: 예산별 추천 ===")
        capture_tab(page, "💰 예산별 추천", "v2_03_budget")

        # 탭4: 계약 가이드
        print("=== Tab 4: 계약 가이드 ===")
        capture_tab(page, "✅ 계약 가이드", "v2_04_guide")

        # 탭5: AI 상담
        print("=== Tab 5: AI 상담 ===")
        capture_tab(page, "💬 AI 상담", "v2_05_chat")

        # 탭6: 데이터 더보기
        print("=== Tab 6: 데이터 더보기 ===")
        capture_tab(page, "📊 데이터 더보기", "v2_06_data")

        browser.close()
        print("\nDone — all v2 screenshots saved")

if __name__ == "__main__":
    main()
