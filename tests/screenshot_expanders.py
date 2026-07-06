"""데이터 더보기 탭 expander 내부 검증"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 3000}, color_scheme="dark")

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # 탭6: 데이터 더보기
        tab_btn = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab_btn.first.click()
        time.sleep(4)

        # Expander 열기: "전세가율 분포 분석"
        expanders = page.locator('details summary')
        for i in range(expanders.count()):
            try:
                text = expanders.nth(i).inner_text()
                if "전세가율" in text or "추세" in text or "이상거래" in text or "연도별" in text:
                    expanders.nth(i).click()
                    time.sleep(2)
            except Exception:
                pass

        time.sleep(3)
        page.screenshot(path=str(OUT / "dark_06_expanders.png"))
        print("dark_06_expanders.png — expanders opened")

        # 탭2 안전지도: 비교 동네 선택
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "dark_02_compare.png"))
        print("dark_02_compare.png — map with compare select")

        browser.close()
        print("\nDone")

if __name__ == "__main__":
    main()
