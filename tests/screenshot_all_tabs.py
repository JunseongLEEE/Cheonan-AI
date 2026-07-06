"""모든 탭 스크린샷 캡처 — Playwright 기반 자동 테스트"""
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

        # 초기 로딩
        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(5)  # Streamlit 렌더링 대기

        # 전체 페이지 (히어로 배너 + 첫 탭)
        page.screenshot(path=str(OUT / "00_landing.png"), full_page=True)
        print("00_landing.png captured")

        # 탭 목록
        tabs = [
            ("🔍 내 매물 체크", "01_tab_check"),
            ("🗺️ 안전지도", "02_tab_map"),
            ("💰 예산별 추천", "03_tab_budget"),
            ("✅ 계약 가이드", "04_tab_guide"),
            ("💬 AI 상담", "05_tab_chat"),
            ("📊 데이터 더보기", "06_tab_data"),
        ]

        for tab_text, filename in tabs:
            try:
                # 탭 버튼 클릭
                tab_btn = page.locator(f'button[role="tab"]:has-text("{tab_text}")')
                if tab_btn.count() > 0:
                    tab_btn.first.click()
                    time.sleep(3)  # 탭 콘텐츠 렌더 대기
                    page.screenshot(path=str(OUT / f"{filename}.png"), full_page=True)
                    print(f"{filename}.png captured")
                else:
                    print(f"WARNING: Tab '{tab_text}' not found")
            except Exception as e:
                print(f"ERROR capturing {filename}: {e}")

        # 탭1 시뮬레이터 — 데모 프리셋 선택 후 결과 확인
        try:
            tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
            tab_btn.first.click()
            time.sleep(2)

            # 데모 시나리오 선택 (두 번째 옵션 = 대학가 원룸)
            preset_select = page.locator('div[data-testid="stSelectbox"]').nth(0)
            if preset_select.count() > 0:
                preset_select.click()
                time.sleep(1)
                # 리스트에서 두 번째 옵션 선택
                options = page.locator('li[role="option"]')
                if options.count() > 1:
                    options.nth(1).click()
                    time.sleep(4)  # 결과 렌더 대기
                    page.screenshot(path=str(OUT / "01b_tab_check_result.png"), full_page=True)
                    print("01b_tab_check_result.png captured (with demo preset)")
        except Exception as e:
            print(f"ERROR capturing demo result: {e}")

        # 탭3 예산별 추천 — 슬라이더 조작 후 결과 확인
        try:
            tab_btn = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
            tab_btn.first.click()
            time.sleep(4)
            page.screenshot(path=str(OUT / "03b_tab_budget_loaded.png"), full_page=True)
            print("03b_tab_budget_loaded.png captured")
        except Exception as e:
            print(f"ERROR capturing budget: {e}")

        browser.close()
        print(f"\nAll screenshots saved to {OUT}")

if __name__ == "__main__":
    main()
