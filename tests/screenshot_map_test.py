"""Test map rendering on Tab 2"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
URL = "http://localhost:8501"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 2000}, color_scheme="dark")

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(6)

        # Tab2 — 안전지도
        tab = page.locator('button[role="tab"]:has-text("🗺️ 안전지도")')
        tab.first.click()
        time.sleep(5)  # extra wait for map

        page.screenshot(path=str(OUT / "map_test.png"))
        print("map_test.png saved")

        # Check for iframes (folium maps render in iframes)
        iframes = page.locator("iframe")
        print(f"iframes count: {iframes.count()}")
        for i in range(min(iframes.count(), 5)):
            try:
                src = iframes.nth(i).get_attribute("src") or ""
                h = iframes.nth(i).get_attribute("height") or ""
                print(f"  iframe {i}: src={src[:80]}... height={h}")
            except:
                pass

        browser.close()

if __name__ == "__main__":
    main()
