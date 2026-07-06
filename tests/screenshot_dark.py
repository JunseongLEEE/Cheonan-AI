"""다크모드 스크린샷 검증"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1400, "height": 3000},
            color_scheme="dark",
        )

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # 탭1 프리셋
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 1:
                options.nth(1).click()
                time.sleep(5)
        page.screenshot(path=str(OUT / "dark_01_check.png"))
        print("dark_01_check.png")

        # 탭2 안전지도
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "dark_02_map.png"))
        print("dark_02_map.png")

        # 탭3 예산별 추천
        tab_btn = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "dark_03_budget.png"))
        print("dark_03_budget.png")

        # 탭4 계약 가이드
        tab_btn = page.locator('button[role="tab"]:has-text("✅ 계약 가이드")')
        tab_btn.first.click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "dark_04_guide.png"))
        print("dark_04_guide.png")

        # 탭6 데이터 더보기
        tab_btn = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "dark_06_data.png"))
        print("dark_06_data.png")

        browser.close()
        print("\nDark mode verification done")

if __name__ == "__main__":
    main()
