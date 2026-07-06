"""
06_commerce.py — 소상공인 상가정보 수집 (천안시)
================================================
API: https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong
divId=signguCd, key=44131(동남구) / 44133(서북구)

천안시 동남구·서북구의 상가(소상공인) 정보를 페이지네이션하여 수집한다.
storeListInDong (행정동 기반 조회)를 사용한다.
"""

import json
import time
from pathlib import Path

from tqdm import tqdm

from _common import (
    load_env,
    get_api_key,
    setup_logger,
    make_request,
    ensure_dir,
    is_already_fetched,
    LAWD_CDS,
    SLEEP_BETWEEN_CALLS,
    DATA_RAW_DIR,
    FatalAPIError,
    TransientAPIError,
)

logger = setup_logger("commerce")

# ── 설정 ──────────────────────────────────────────────────────────
BASE_URL = (
    "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
)
OUT_DIR = DATA_RAW_DIR / "commerce"

NUM_OF_ROWS = 1000
MAX_PAGES = 500  # 안전 상한 (무한루프 방지)

# 시군구코드: 천안 동남구 44131, 서북구 44133
SIGUNGU_CODES = {
    "44131": "동남구",
    "44133": "서북구",
}


def fetch_commerce_page(
    service_key: str, sigungu_cd: str, page_no: int
) -> dict | None:
    """상가정보 1페이지를 조회한다."""
    params = {
        "serviceKey": service_key,
        "divId": "signguCd",
        "key": sigungu_cd,
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
        "type": "json",
    }
    try:
        resp = make_request(BASE_URL, params, timeout=30)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error(
            "make_request 실패: sigungu=%s page=%d — %s",
            sigungu_cd, page_no, e,
        )
        return None
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        text = resp.text.strip()
        if text.startswith("<?xml") or text.startswith("<"):
            return {"_raw_xml": text}
        logger.warning("알 수 없는 응답: %s", text[:200])
        return None


def extract_items(data: dict) -> list:
    """API 응답에서 item 리스트를 추출한다."""
    if data is None:
        return []
    try:
        for path in [
            ["body", "items"],
            ["response", "body", "items"],
            ["body", "items", "item"],
            ["response", "body", "items", "item"],
            ["data"],
            ["row"],
        ]:
            node = data
            for k in path:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    node = None
                    break
            if node is not None:
                return node if isinstance(node, list) else [node]
    except Exception:
        pass
    return []


def get_total_count(data: dict) -> int:
    """응답에서 전체 건수를 추출한다."""
    if data is None:
        return -1
    try:
        for path in [
            ["body", "totalCount"],
            ["response", "body", "totalCount"],
            ["body", "total_count"],
            ["totalCnt"],
            ["list_total_count"],
        ]:
            node = data
            for k in path:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    node = None
                    break
            if node is not None:
                return int(node)
    except Exception:
        pass
    return -1


def collect_sigungu(service_key: str, sigungu_cd: str, name: str):
    """한 시군구의 전체 상가정보를 수집한다."""
    logger.info("--- %s(%s) 수집 시작 ---", name, sigungu_cd)

    sigungu_dir = ensure_dir(OUT_DIR)

    # 1) 첫 페이지
    first_file = sigungu_dir / f"{sigungu_cd}_page_001.json"
    if is_already_fetched(first_file):
        logger.info("첫 페이지 이미 수집됨 — 로드")
        with open(first_file, "r", encoding="utf-8") as f:
            first_data = json.load(f)
    else:
        first_data = fetch_commerce_page(service_key, sigungu_cd, 1)
        if first_data is None:
            logger.error("%s 첫 페이지 조회 실패", name)
            return 0

        if "_raw_xml" in first_data:
            xml_path = sigungu_dir / f"{sigungu_cd}_page_001.xml"
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(first_data["_raw_xml"])
            logger.warning("XML 응답 수신 — %s", xml_path)
            return 0

        with open(first_file, "w", encoding="utf-8") as f:
            json.dump(first_data, f, ensure_ascii=False, indent=2)

    # 2) 전체 건수 파악
    total_count = get_total_count(first_data)
    items_p1 = extract_items(first_data)

    if total_count <= 0:
        # totalCount를 못 읽었으면 빈 페이지가 올 때까지 수집
        logger.info(
            "totalCount 미확인. 빈 페이지가 올 때까지 수집합니다. "
            "(1페이지 %d건)", len(items_p1)
        )
        total_pages = MAX_PAGES
    else:
        total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
        logger.info(
            "%s: 전체 %d건, %d페이지", name, total_count, total_pages
        )

    collected = len(items_p1)

    # 3) 나머지 페이지
    for page_no in tqdm(
        range(2, total_pages + 1),
        desc=f"{name} 상가정보",
        initial=1,
        total=total_pages,
    ):
        page_file = sigungu_dir / f"{sigungu_cd}_page_{page_no:03d}.json"

        if is_already_fetched(page_file):
            with open(page_file, "r", encoding="utf-8") as f:
                page_data = json.load(f)
        else:
            time.sleep(SLEEP_BETWEEN_CALLS)
            page_data = fetch_commerce_page(service_key, sigungu_cd, page_no)
            if page_data is None:
                logger.warning("페이지 %d 수집 실패 — 건너뜀", page_no)
                continue
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

        items = extract_items(page_data)
        if not items:
            logger.info("페이지 %d: 빈 결과 — 수집 종료", page_no)
            break

        collected += len(items)

    logger.info("%s 수집 완료: 약 %d건", name, collected)
    return collected


def main():
    load_env()
    service_key = get_api_key()
    ensure_dir(OUT_DIR)

    logger.info("=== 소상공인 상가정보 수집 시작 (천안시) ===")

    grand_total = 0
    for sigungu_cd, name in SIGUNGU_CODES.items():
        count = collect_sigungu(service_key, sigungu_cd, name)
        grand_total += count

    logger.info(
        "=== 상가정보 수집 완료: 천안시 총 약 %d건 ===", grand_total
    )


if __name__ == "__main__":
    main()
