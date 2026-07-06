"""상세 스크린샷 — 시뮬레이터 결과 스크롤, 탭2 지도 영역 등"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(5)

        # === 탭1: 데모 프리셋 선택 후 전체 결과 (스크롤 포함) ===
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)

        # 데모 시나리오 "대학가 원룸" 선택
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        # 첫 번째 selectbox = 데모 시나리오
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 1:
                options.nth(1).click()  # "대학가 원룸 (안서동, 위험)"
                time.sleep(5)

        # 전체 페이지 스크롤 스크린샷
        page.screenshot(path=str(OUT / "detail_01_check_full.png"), full_page=True)
        print("detail_01_check_full.png — 매물체크 전체 (스크롤)")

        # 페이지 하단으로 스크롤
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        page.screenshot(path=str(OUT / "detail_01_check_bottom.png"))
        print("detail_01_check_bottom.png — 매물체크 하단")

        # === 탭2: 안전지도 — 지도+동 상세 전체 ===
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(5)  # folium 렌더 대기 충분히
        page.screenshot(path=str(OUT / "detail_02_map_full.png"), full_page=True)
        print("detail_02_map_full.png — 안전지도 전체")

        # 스크롤해서 레이더 차트 영역 확인
        page.evaluate("window.scrollTo(0, 800)")
        time.sleep(2)
        page.screenshot(path=str(OUT / "detail_02_map_mid.png"))
        print("detail_02_map_mid.png — 안전지도 중단 (지도 아래)")

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        page.screenshot(path=str(OUT / "detail_02_map_bottom.png"))
        print("detail_02_map_bottom.png — 안전지도 하단")

        # === 탭3: 예산별 추천 전체 ===
        tab_btn = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "detail_03_budget_full.png"), full_page=True)
        print("detail_03_budget_full.png — 예산추천 전체")

        # === 탭4: 계약 가이드 전체 ===
        tab_btn = page.locator('button[role="tab"]:has-text("✅ 계약 가이드")')
        tab_btn.first.click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "detail_04_guide_full.png"), full_page=True)
        print("detail_04_guide_full.png — 계약가이드 전체")

        # === 탭6: 데이터 더보기 전체 ===
        tab_btn = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "detail_06_data_full.png"), full_page=True)
        print("detail_06_data_full.png — 데이터 전체")

        browser.close()
        print("\nDone")

if __name__ == "__main__":
    main()
