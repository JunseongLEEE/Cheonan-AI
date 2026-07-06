"""전체 탭 종합 스크린샷 — 모든 인터랙션 포함"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 5000}, color_scheme="dark")

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # Tab1 — 프리셋 결과 + 스크롤
        tab = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab.first.click()
        time.sleep(2)
        sb = page.locator('div[data-testid="stSelectbox"]')
        if sb.count() > 0:
            sb.nth(0).click(); time.sleep(1)
            opts = page.locator('li[role="option"]')
            if opts.count() > 1: opts.nth(1).click(); time.sleep(5)
        page.screenshot(path=str(OUT / "full_01.png"))
        print("full_01.png")

        # Tab2 — 안전지도
        tab = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab.first.click(); time.sleep(4)
        page.screenshot(path=str(OUT / "full_02.png"))
        print("full_02.png")

        # Tab3 — 예산
        tab = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
        tab.first.click(); time.sleep(3)
        page.screenshot(path=str(OUT / "full_03.png"))
        print("full_03.png")

        # Tab4 — 가이드
        tab = page.locator('button[role="tab"]:has-text("✅ 계약 가이드")')
        tab.first.click(); time.sleep(3)
        page.screenshot(path=str(OUT / "full_04.png"))
        print("full_04.png")

        # Tab5 — 챗봇 + 빠른질문
        tab = page.locator('button[role="tab"]:has-text("💬 AI 상담")')
        tab.first.click(); time.sleep(3)
        qb = page.locator('button:has-text("안전한 동네 추천")')
        if qb.count() > 0: qb.first.click(); time.sleep(3)
        page.screenshot(path=str(OUT / "full_05.png"))
        print("full_05.png")

        # Tab6 — 데이터
        tab = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab.first.click(); time.sleep(4)
        page.screenshot(path=str(OUT / "full_06.png"))
        print("full_06.png")

        # Tab1 비교모드
        tab = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab.first.click(); time.sleep(2)
        radio = page.locator('label:has-text("비교 분석")')
        if radio.count() > 0:
            radio.first.click(); time.sleep(2)
            cmp_btn = page.locator('button:has-text("비교 분석")')
            if cmp_btn.count() > 0:
                cmp_btn.first.click(); time.sleep(5)
        page.screenshot(path=str(OUT / "full_01_cmp.png"))
        print("full_01_cmp.png")

        browser.close()
        print("\nFull screenshots done")

if __name__ == "__main__":
    main()
