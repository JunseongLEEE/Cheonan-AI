"""Cycle 18 — 유사 거래 + 구도심 비교 차트 + 최소 거래 필터 검증"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 4000}, color_scheme="dark")

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # 1) 매물 체크 — 과거 거래 + 유사 거래 expander
        print("=== Tab1: 매물 체크 — 유사 거래 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)

        # 프리셋 선택 (원성동 위험)
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 2:
                options.nth(2).click()
                time.sleep(5)

        # 과거 거래 통계 expander 열기
        expanders = page.locator('details summary')
        for i in range(expanders.count()):
            try:
                text = expanders.nth(i).inner_text()
                if "과거 거래" in text or "유사 거래" in text:
                    expanders.nth(i).click()
                    time.sleep(2)
            except Exception:
                pass

        page.screenshot(path=str(OUT / "c18_01_similar_trades.png"))
        print("c18_01_similar_trades.png")

        # 2) 안전지도 — 구도심 vs 신도심 비교 차트
        print("=== Tab2: 구도심 vs 신도심 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(4)

        # 구도심 vs 신도심 expander 열기
        expanders = page.locator('details summary')
        for i in range(expanders.count()):
            try:
                text = expanders.nth(i).inner_text()
                if "구도심" in text:
                    expanders.nth(i).click()
                    time.sleep(2)
            except Exception:
                pass

        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 1500;
            else window.scrollTo(0, 1500);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "c18_02_district_compare.png"))
        print("c18_02_district_compare.png")

        # 3) 예산 추천 — 최소 거래 필터 확인
        print("=== Tab3: 예산 추천 — 필터 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
        tab_btn.first.click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "c18_03_budget_filter.png"))
        print("c18_03_budget_filter.png")

        browser.close()
        print("\nCycle 18 screenshots done")

if __name__ == "__main__":
    main()
