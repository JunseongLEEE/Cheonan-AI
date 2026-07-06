"""수정 후 검증 스크린샷"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 3000})

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # 검증 1: 탭1 프리셋 → 동네 변경 + 대체 추천 카드
        print("=== Verify 1: Tab1 preset + alt recommendations ===")
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

        page.screenshot(path=str(OUT / "verify_01_check.png"))
        print("  verify_01_check.png")

        # 검증 2: 탭2 안전지도 — nan 수정 확인
        print("=== Verify 2: Tab2 map nan fix ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(5)
        page.screenshot(path=str(OUT / "verify_02_map.png"))
        print("  verify_02_map.png")

        # 검증 3: 탭6 데이터 더보기 — 랭킹 NaN 수정 확인
        print("=== Verify 3: Tab6 ranking NaN fix ===")
        tab_btn = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "verify_06_data.png"))
        print("  verify_06_data.png")

        browser.close()
        print("\nVerification done")

if __name__ == "__main__":
    main()
