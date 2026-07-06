"""Debug Tab1 rendering issue"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900}, color_scheme="dark")

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # Tab1 — select preset
        tab = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab.first.click()
        time.sleep(2)
        sb = page.locator('div[data-testid="stSelectbox"]')
        if sb.count() > 0:
            sb.nth(0).click(); time.sleep(1)
            opts = page.locator('li[role="option"]')
            if opts.count() > 1: opts.nth(1).click(); time.sleep(5)

        # Screenshot top part
        page.screenshot(path=str(OUT / "debug_01_top.png"))
        print("debug_01_top.png")

        # Scroll down to see SHAP and below
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 800;
            else window.scrollTo(0, 800);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "debug_02_mid.png"))
        print("debug_02_mid.png")

        # Scroll down more
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = 1600;
            else window.scrollTo(0, 1600);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "debug_03_bot.png"))
        print("debug_03_bot.png")

        # Scroll to bottom
        page.evaluate("""
            const main = document.querySelector('section.main');
            if (main) main.scrollTop = main.scrollHeight;
            else window.scrollTo(0, document.body.scrollHeight);
        """)
        time.sleep(2)
        page.screenshot(path=str(OUT / "debug_04_end.png"))
        print("debug_04_end.png")

        browser.close()
        print("\nDebug screenshots done")

if __name__ == "__main__":
    main()
