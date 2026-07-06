"""
04_flood.py — 침수흔적도 데이터 수집
====================================
API: 행정안전부 침수흔적 소규모 서비스
https://apis.data.go.kr/1741000/FloodedTraceSmallService/getFloodedTraceSmallList

침수흔적 이력(위치, 침수심, 침수일시 등)을 REST 방식으로 조회하여 저장한다.
WMS(지도 타일)만 제공되는 경우 메타데이터와 안내를 남긴다.
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
    SLEEP_BETWEEN_CALLS,
    DATA_RAW_DIR,
    FatalAPIError,
    TransientAPIError,
)

logger = setup_logger("flood")

# ── 설정 ──────────────────────────────────────────────────────────
BASE_URL = (
    "https://apis.data.go.kr/1741000/FloodedTraceSmallService"
    "/getFloodedTraceSmallList"
)
OUT_DIR = DATA_RAW_DIR / "flood"

# 천안시 관련 검색 키워드 (API가 지역 파라미터를 지원하지 않을 수 있음)
CHEONAN_KEYWORDS = ["천안", "동남구", "서북구"]

NUM_OF_ROWS = 1000  # 한 페이지당 최대 행 수


def fetch_flood_page(service_key: str, page_no: int) -> dict | None:
    """침수흔적 목록 1페이지를 조회한다."""
    params = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": NUM_OF_ROWS,
        "type": "json",
    }
    try:
        resp = make_request(BASE_URL, params, timeout=30)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error("make_request 실패: page=%d — %s", page_no, e)
        return None
    if resp is None:
        return None

    # JSON 파싱 시도
    try:
        data = resp.json()
        return data
    except Exception:
        pass

    # XML일 수 있음
    text = resp.text.strip()
    if text.startswith("<?xml") or text.startswith("<"):
        logger.info("XML 응답 수신 — XML 원본 저장")
        return {"_raw_xml": text}

    logger.warning("알 수 없는 응답 형식: %s", text[:200])
    return {"_raw_text": text}


def extract_items(data: dict) -> list:
    """API 응답에서 item 리스트를 추출한다 (공공데이터포털 공통 구조)."""
    try:
        body = data.get("FloodedTraceSmallService", data)
        if isinstance(body, dict):
            # 여러 가능한 구조를 탐색
            for key_path in [
                ["body", "items", "item"],
                ["response", "body", "items", "item"],
                ["row"],
                ["data"],
            ]:
                node = body
                for k in key_path:
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
    try:
        body = data.get("FloodedTraceSmallService", data)
        if isinstance(body, dict):
            for path in [
                ["body", "totalCount"],
                ["response", "body", "totalCount"],
                ["totalCnt"],
                ["list_total_count"],
            ]:
                node = body
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


def filter_cheonan(items: list) -> list:
    """천안시 관련 레코드만 필터링한다."""
    filtered = []
    for item in items:
        text = json.dumps(item, ensure_ascii=False)
        if any(kw in text for kw in CHEONAN_KEYWORDS):
            filtered.append(item)
    return filtered


def main():
    load_env()
    service_key = get_api_key()
    ensure_dir(OUT_DIR)

    logger.info("=== 침수흔적도 데이터 수집 시작 ===")

    # 1) 첫 페이지 조회로 전체 건수 파악
    first_page_file = OUT_DIR / "page_001.json"
    if is_already_fetched(first_page_file):
        logger.info("첫 페이지 이미 수집됨 — 로드하여 totalCount 확인")
        with open(first_page_file, "r", encoding="utf-8") as f:
            first_data = json.load(f)
    else:
        first_data = fetch_flood_page(service_key, 1)
        if first_data is None:
            logger.error(
                "첫 페이지 조회 실패. API 키 또는 URL을 확인하세요.\n"
                "참고: 이 API가 WMS(지도 타일) 전용이면 REST 조회가 불가능합니다.\n"
                "그 경우 https://www.data.go.kr 에서 직접 다운로드하세요."
            )
            # WMS 전용인 경우를 위한 메타데이터 저장
            meta = {
                "api_name": "침수흔적 소규모 서비스",
                "api_url": BASE_URL,
                "note": "REST 조회 실패 — WMS 전용 서비스일 수 있음. "
                        "국가공간정보포털(data.nsdi.go.kr)에서 SHP 다운로드 권장.",
                "alternative_sources": [
                    "https://www.data.go.kr/data/15048634/fileData.do",
                    "https://data.nsdi.go.kr — 침수흔적도 검색",
                    "https://www.safekorea.go.kr — 재난안전포털 침수흔적 지도",
                ],
            }
            meta_path = OUT_DIR / "_metadata_wms_note.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            logger.info("WMS 안내 메타데이터 저장: %s", meta_path)
            return

        # 원본 저장
        if "_raw_xml" in first_data:
            xml_path = OUT_DIR / "page_001.xml"
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(first_data["_raw_xml"])
            logger.info("XML 원본 저장: %s", xml_path)
            # XML이면 json 파싱 안 되므로 메타데이터 남기고 종료
            meta = {
                "api_name": "침수흔적 소규모 서비스",
                "note": "XML 응답 수신됨. XML 파싱 또는 type=json 파라미터 확인 필요.",
                "saved_file": str(xml_path),
            }
            meta_path = OUT_DIR / "_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            return

        with open(first_page_file, "w", encoding="utf-8") as f:
            json.dump(first_data, f, ensure_ascii=False, indent=2)

    # 2) 전체 건수 확인
    total_count = get_total_count(first_data)
    if total_count <= 0:
        logger.warning(
            "전체 건수를 파악할 수 없습니다 (totalCount=%s). "
            "1페이지 데이터만 저장합니다.", total_count
        )
        # 천안 필터링 결과 저장
        items = extract_items(first_data)
        cheonan_items = filter_cheonan(items)
        logger.info(
            "1페이지: 전체 %d건 중 천안 관련 %d건", len(items), len(cheonan_items)
        )
        if cheonan_items:
            ca_path = OUT_DIR / "cheonan_flood.json"
            with open(ca_path, "w", encoding="utf-8") as f:
                json.dump(cheonan_items, f, ensure_ascii=False, indent=2)
            logger.info("천안 침수흔적 저장: %s (%d건)", ca_path, len(cheonan_items))
        return

    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    logger.info("전체 %d건, %d페이지 수집 예정", total_count, total_pages)

    # 3) 나머지 페이지 수집
    all_cheonan_items = []

    # 첫 페이지 천안 필터
    items_p1 = extract_items(first_data)
    all_cheonan_items.extend(filter_cheonan(items_p1))

    for page_no in tqdm(range(2, total_pages + 1), desc="침수흔적 수집"):
        page_file = OUT_DIR / f"page_{page_no:03d}.json"
        if is_already_fetched(page_file):
            with open(page_file, "r", encoding="utf-8") as f:
                page_data = json.load(f)
        else:
            time.sleep(SLEEP_BETWEEN_CALLS)
            page_data = fetch_flood_page(service_key, page_no)
            if page_data is None:
                logger.warning("페이지 %d 수집 실패 — 건너뜀", page_no)
                continue
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

        items = extract_items(page_data)
        all_cheonan_items.extend(filter_cheonan(items))

    # 4) 천안 데이터 통합 저장
    if all_cheonan_items:
        merged_path = OUT_DIR / "cheonan_flood.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(all_cheonan_items, f, ensure_ascii=False, indent=2)
        logger.info(
            "천안 침수흔적 통합 저장: %s (%d건)", merged_path, len(all_cheonan_items)
        )
    else:
        logger.warning("천안시 관련 침수흔적 데이터가 없습니다.")

    logger.info("=== 침수흔적도 수집 완료 ===")


if __name__ == "__main__":
    main()
