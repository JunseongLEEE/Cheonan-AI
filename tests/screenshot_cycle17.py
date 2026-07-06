"""Cycle 17 — 계약 가이드 + 데이터 더보기 상세 + 매물 과거통계 expander 검증"""
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

        # 1) 계약 가이드 탭
        print("=== Tab4: 계약 가이드 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("✅ 계약 가이드")')
        tab_btn.first.click()
        time.sleep(3)

        # 체크박스 2개 클릭 (등기부등본, 임대인 확인)
        checkboxes = page.locator('input[type="checkbox"]')
        for i in range(min(2, checkboxes.count())):
            try:
                checkboxes.nth(i).click()
                time.sleep(0.5)
            except Exception:
                pass
        time.sleep(2)
        page.screenshot(path=str(OUT / "c17_04a_guide.png"))
        print("c17_04a_guide.png — 체크리스트 (2개 체크)")

        # 스크롤 다운 — 하단 항목들
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 2000;
            else window.scrollTo(0, 2000);
        """)
        time.sleep(1)
        page.screenshot(path=str(OUT / "c17_04b_guide_bottom.png"))
        print("c17_04b_guide_bottom.png — 하단 항목 + 링크")

        # 2) 매물 체크 — 과거 거래 통계 expander 열기
        print("=== Tab1: 매물 체크 — 과거 통계 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)

        # 프리셋 선택
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 2:
                options.nth(2).click()  # 3번째 프리셋 (원성동 위험)
                time.sleep(5)

        # 과거 거래 통계 expander 열기
        expanders = page.locator('details summary')
        for i in range(expanders.count()):
            try:
                text = expanders.nth(i).inner_text()
                if "과거 거래" in text or "거래 통계" in text:
                    expanders.nth(i).click()
                    time.sleep(2)
            except Exception:
                pass

        page.screenshot(path=str(OUT / "c17_01_trade_stats.png"))
        print("c17_01_trade_stats.png — 과거 거래 통계 expander")

        # 3) 데이터 더보기 — 전체 섹션 스크롤
        print("=== Tab6: 데이터 더보기 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("📊 데이터 더보기")')
        tab_btn.first.click()
        time.sleep(4)
        page.screenshot(path=str(OUT / "c17_06a_data_top.png"))
        print("c17_06a_data_top.png — 상단 요약 + 랭킹")

        # 스크롤하여 데이터프레임 랭킹 확인
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 800;
            else window.scrollTo(0, 800);
        """)
        time.sleep(1)
        page.screenshot(path=str(OUT / "c17_06b_data_ranking.png"))
        print("c17_06b_data_ranking.png — 랭킹 테이블")

        browser.close()
        print("\nCycle 17 screenshots done")

if __name__ == "__main__":
    main()
