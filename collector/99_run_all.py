#!/usr/bin/env python3
"""
99. 전체 데이터 수집 스크립트 순차 실행
========================================
모든 collector 스크립트를 순서대로 실행하고,
각 스크립트의 성공/실패 결과를 요약 출력한다.

실패한 스크립트가 있어도 다음 스크립트를 계속 실행한다.
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = [
    "01_realestate.py",
    "02_building.py",
    "03_housing_price.py",
    "04_flood.py",
    "05_cctv.py",
    "06_commerce.py",
    "07_medical.py",
    "08_air_quality.py",
    "09_sgis.py",
]

COLLECTOR_DIR = Path(__file__).resolve().parent


def main() -> None:
    """모든 수집 스크립트를 순차 실행한다."""
    results: list[tuple[str, bool, float]] = []  # (script, success, elapsed)
    python = sys.executable

    print("=" * 60)
    print("  천안 청년 자취방 안전지도 — 데이터 수집 파이프라인")
    print("=" * 60)
    print()

    for script in SCRIPTS:
        script_path = COLLECTOR_DIR / script

        if not script_path.exists():
            print(f"[SKIP] {script} — 파일 없음")
            results.append((script, False, 0.0))
            continue

        print(f"[START] {script}")
        t0 = time.time()

        try:
            proc = subprocess.run(
                [python, str(script_path)],
                cwd=str(COLLECTOR_DIR),
                capture_output=False,
                timeout=3600,  # 1시간 타임아웃
            )
            elapsed = time.time() - t0
            success = proc.returncode == 0

            status = "OK" if success else f"FAIL (exit {proc.returncode})"
            print(f"[{status}] {script} — {elapsed:.1f}s")
            results.append((script, success, elapsed))

        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"[TIMEOUT] {script} — {elapsed:.1f}s (1시간 초과)")
            results.append((script, False, elapsed))

        except Exception as e:
            elapsed = time.time() - t0
            print(f"[ERROR] {script} — {e}")
            results.append((script, False, elapsed))

        print()

    # ── 요약 ──────────────────────────────────────────────────
    print("=" * 60)
    print("  수집 결과 요약")
    print("=" * 60)
    print(f"{'스크립트':<25} {'상태':<10} {'소요시간':>10}")
    print("-" * 50)

    total_ok = 0
    total_time = 0.0

    for script, success, elapsed in results:
        status = "OK" if success else "FAIL"
        total_ok += int(success)
        total_time += elapsed
        print(f"{script:<25} {status:<10} {elapsed:>8.1f}s")

    print("-" * 50)
    print(
        f"총 {len(results)}개 중 {total_ok}개 성공, "
        f"{len(results) - total_ok}개 실패 — "
        f"총 소요시간 {total_time:.1f}s"
    )

    if total_ok < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
