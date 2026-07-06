"""Cycle 16 — 전체 탭 + 챗봇 인터랙션 + 예산 버튼 검증"""
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

        # 1) 랜딩 페이지 (히어로 배너 + "왜 필요한가" 확인)
        page.screenshot(path=str(OUT / "c16_00_landing.png"))
        print("c16_00_landing.png")

        # 2) Tab5 AI 상담 — 빠른 질문 버튼 클릭 검증
        print("=== Tab5: AI 상담 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("💬 AI 상담")')
        tab_btn.first.click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "c16_05a_chat_init.png"))
        print("c16_05a_chat_init.png — 초기 상태")

        # 빠른 질문 클릭: "불당동 안전한가요?"
        quick_btns = page.locator('button:has-text("불당동 안전한가요?")')
        if quick_btns.count() > 0:
            quick_btns.first.click()
            time.sleep(3)
            page.screenshot(path=str(OUT / "c16_05b_chat_dong.png"))
            print("c16_05b_chat_dong.png — 동 분석 응답")

        # 직접 입력: 매물 분석
        chat_input = page.locator('textarea[data-testid="stChatInputTextArea"]')
        if chat_input.count() > 0:
            chat_input.fill("원성동 3000만원 20㎡ 1990년")
            chat_input.press("Enter")
            time.sleep(4)
            page.screenshot(path=str(OUT / "c16_05c_chat_sim.png"))
            print("c16_05c_chat_sim.png — 시뮬레이터 연동 응답")

        # 3) Tab3 예산별 추천 — 빠른 예산 버튼 검증
        print("=== Tab3: 예산별 추천 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("💰 예산별 추천")')
        tab_btn.first.click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "c16_03a_budget_init.png"))
        print("c16_03a_budget_init.png — 초기 상태")

        # 예산 슬라이더 or 입력 확인
        # 빠른 예산 버튼 (3천/5천/1억) 클릭
        budget_btns = page.locator('button:has-text("5천만")')
        if budget_btns.count() > 0:
            budget_btns.first.click()
            time.sleep(3)
            page.screenshot(path=str(OUT / "c16_03b_budget_5000.png"))
            print("c16_03b_budget_5000.png — 5천만원 검색")
        else:
            print("  WARN: 빠른 예산 버튼 없음")

        # 4) Tab1 매물 체크 — 비교 모드 검증
        print("=== Tab1: 매물 체크 비교 모드 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab_btn.first.click()
        time.sleep(2)

        # 데모 프리셋 선택
        selectboxes = page.locator('div[data-testid="stSelectbox"]')
        if selectboxes.count() > 0:
            selectboxes.nth(0).click()
            time.sleep(1)
            options = page.locator('li[role="option"]')
            if options.count() > 1:
                options.nth(1).click()
                time.sleep(5)

        page.screenshot(path=str(OUT / "c16_01a_check.png"))
        print("c16_01a_check.png — 매물 체크 결과")

        # 스크롤 다운하여 하단 카드 확인
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 1500;
            else window.scrollTo(0, 1500);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "c16_01b_check_scroll.png"))
        print("c16_01b_check_scroll.png — 하단 (대체 동네 카드)")

        # 5) Tab2 안전지도 — 동 선택 + 상세패널
        print("=== Tab2: 안전지도 ===")
        tab_btn = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab_btn.first.click()
        time.sleep(4)

        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 0;
            else window.scrollTo(0, 0);
        """)
        time.sleep(1)
        page.screenshot(path=str(OUT / "c16_02a_map.png"))
        print("c16_02a_map.png — 안전지도 상단")

        # 스크롤하여 레이더 차트 / 비교 섹션
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 1200;
            else window.scrollTo(0, 1200);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "c16_02b_map_detail.png"))
        print("c16_02b_map_detail.png — 안전지도 하단")

        browser.close()
        print("\nCycle 16 screenshots done")

if __name__ == "__main__":
    main()
