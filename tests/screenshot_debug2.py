"""Debug Tab1 with tall viewport to see all content"""
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

        # Tab1 — select preset
        tab = page.locator('button[role="tab"]:has-text("🔍 내 매물 체크")')
        tab.first.click()
        time.sleep(2)
        sb = page.locator('div[data-testid="stSelectbox"]')
        if sb.count() > 0:
            sb.nth(0).click(); time.sleep(1)
            opts = page.locator('li[role="option"]')
            if opts.count() > 1: opts.nth(1).click(); time.sleep(5)

        page.screenshot(path=str(OUT / "debug_tab1_full.png"))
        print("debug_tab1_full.png")

        # Check for any errors in the console
        errors = page.evaluate("() => { return document.querySelectorAll('.stException').length; }")
        print(f"stException elements: {errors}")

        # Check any alert/error elements
        err_els = page.locator('.stAlert')
        print(f"Alert elements count: {err_els.count()}")
        for i in range(min(err_els.count(), 5)):
            try:
                text = err_els.nth(i).inner_text()[:100]
                print(f"  Alert {i}: {text}")
            except:
                pass

        browser.close()

if __name__ == "__main__":
    main()
