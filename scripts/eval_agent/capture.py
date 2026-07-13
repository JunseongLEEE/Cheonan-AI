#!/usr/bin/env python3
"""웹사이트 시각 캡처 — 평가 에이전트용 탭별 풀페이지 스크린샷.

사용: /root/venvs/app/bin/python scripts/eval_agent/capture.py [--url http://localhost:8501]
출력: presentation/screenshots/eval/{NN}_{탭이름}.png
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "presentation" / "screenshots" / "eval"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--width", type=int, default=1440)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": 900})
        page.goto(args.url, wait_until="networkidle", timeout=90000)
        time.sleep(8)  # Streamlit 초기 렌더 (모델 캐시 로드 포함)

        tabs = page.get_by_role("tab").all()
        names = [t.inner_text().strip() for t in tabs]
        print(f"발견한 탭 {len(tabs)}개: {names}")

        for i, (tab, name) in enumerate(zip(tabs, names)):
            slug = re.sub(r"[^\w가-힣]+", "_", name).strip("_") or f"tab{i}"
            try:
                tab.click()
                time.sleep(8)  # 탭 콘텐츠 렌더 (websocket 스트리밍이라 networkidle 대기 불가)
                # Streamlit은 내부 컨테이너가 스크롤됨 → 콘텐츠 전체 높이로 뷰포트 확장
                content_h = page.evaluate(
                    "() => { for (const sel of ['[data-testid=stMainBlockContainer]', '[data-testid=stMain]', 'section.main']) {"
                    "  const el = document.querySelector(sel);"
                    "  if (el && el.scrollHeight > 300) return Math.min(el.scrollHeight + 250, 6000); }"
                    " return 3000; }"
                )
                page.set_viewport_size({"width": args.width, "height": max(900, int(content_h))})
                time.sleep(2)
                path = OUT / f"{i:02d}_{slug}.png"
                page.screenshot(path=str(path))
                page.set_viewport_size({"width": args.width, "height": 900})
                print(f"✓ {path.name} (h={content_h})")
            except Exception as e:
                print(f"✗ {name}: {type(e).__name__} {e}", file=sys.stderr)

        browser.close()
    print(f"완료 → {OUT}")


if __name__ == "__main__":
    main()
