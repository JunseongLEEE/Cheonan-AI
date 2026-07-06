"""Cycle 19 — AI 모델 설명 + 데이터 출처 + 랜딩 개선 검증"""
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

        # 1) 랜딩 — 직접 입력 초기 안내
        print("=== Tab1: 랜딩 초기 안내 ===")
        page.screenshot(path=str(OUT / "c19_01_landing.png"))
        print("c19_01_landing.png")

        # 2) AI 모델 & 데이터 출처 expander
        print("=== AI 모델 & 데이터 출처 ===")
        # 스크롤 맨 아래
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = main.scrollHeight;
            else window.scrollTo(0, document.body.scrollHeight);
        """)
        time.sleep(2)

        # AI 모델 expander 열기
        expanders = page.locator('details summary')
        for i in range(expanders.count()):
            try:
                text = expanders.nth(i).inner_text()
                if "AI 모델" in text or "데이터 출처" in text:
                    expanders.nth(i).click()
                    time.sleep(2)
            except Exception:
                pass

        time.sleep(1)
        page.screenshot(path=str(OUT / "c19_02_ai_model.png"))
        print("c19_02_ai_model.png")

        # 스크롤 down more to see data sources table
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = main.scrollHeight;
            else window.scrollTo(0, document.body.scrollHeight);
        """)
        time.sleep(1)
        page.screenshot(path=str(OUT / "c19_03_data_sources.png"))
        print("c19_03_data_sources.png")

        browser.close()
        print("\nCycle 19 screenshots done")

if __name__ == "__main__":
    main()
