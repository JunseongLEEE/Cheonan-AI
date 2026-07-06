"""
05_cctv.py — 전국 CCTV 표준데이터 수집 (천안시 필터)
=====================================================
데이터: https://www.data.go.kr/data/15013094/standard.do (CSV 표준데이터)

전국 공공 CCTV 표준데이터는 REST API가 아닌 CSV 파일 형태로 제공된다.
공공데이터포털에서 CSV를 직접 다운로드하거나, 파일데이터 다운로드 URL을 시도한다.
다운로드 후 천안시 데이터만 필터링하여 저장한다.
"""

import csv
import io
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
    HEADERS,
    FatalAPIError,
    TransientAPIError,
)

logger = setup_logger("cctv")

# ── 설정 ──────────────────────────────────────────────────────────
# CSV 표준데이터 다운로드 URL (공공데이터포털 파일데이터)
CSV_DOWNLOAD_URL = (
    "https://www.data.go.kr/data/15013094/standard.do"
)
# 파일데이터 API 다운로드 시도 URL (data.go.kr 파일데이터 형식)
FILE_DATA_URL = (
    "https://apis.data.go.kr/B553701/publicCCTVInfo/getPublicCCTVInfo"
)
OUT_DIR = DATA_RAW_DIR / "cctv"

NUM_OF_ROWS = 1000

# 천안시 필터 조건
FILTER_SIDO = "충청남도"
FILTER_SIGUNGU = "천안"


def try_download_csv(service_key: str) -> str | None:
    """CSV 파일 다운로드를 시도한다. 성공하면 텍스트를 반환."""
    # 파일데이터 API를 통한 다운로드 시도
    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": NUM_OF_ROWS,
        "type": "json",
    }
    try:
        resp = make_request(FILE_DATA_URL, params, timeout=30)
        if resp and resp.status_code == 200:
            # JSON 응답이면 API가 작동하는 것
            try:
                data = resp.json()
                return data
            except Exception:
                pass
            # CSV 텍스트인 경우
            text = resp.text.strip()
            if "," in text and len(text) > 100:
                return text
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.warning("API 다운로드 시도 실패: %s", e)

    return None


def fetch_cctv_page(service_key: str, page_no: int) -> dict | None:
    """CCTV 목록 1페이지를 조회한다."""
    params = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": NUM_OF_ROWS,
        "type": "json",
    }
    try:
        resp = make_request(FILE_DATA_URL, params, timeout=30)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error("make_request 실패: page=%d — %s", page_no, e)
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
            ["response", "body", "items", "item"],
            ["body", "items", "item"],
            ["response", "body", "items"],
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
            ["response", "body", "totalCount"],
            ["body", "totalCount"],
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


def is_cheonan(item: dict) -> bool:
    """
    아이템이 천안시 데이터인지 판별한다.
    가능한 필드명: 관리기관명, 시도명, 시군구명, 설치장소(도로명)주소 등
    """
    text = json.dumps(item, ensure_ascii=False)
    # 1) 관리기관명에 "천안" 포함
    if "천안" in text:
        return True
    return False


def load_manual_csv() -> list[dict] | None:
    """수동 다운로드된 CSV 파일이 있으면 로드한다."""
    import glob
    csv_patterns = [
        OUT_DIR / "*.csv",
        DATA_RAW_DIR / "cctv*.csv",
    ]
    for pattern in csv_patterns:
        files = glob.glob(str(pattern))
        if files:
            csv_path = files[0]
            logger.info("수동 다운로드 CSV 발견: %s", csv_path)
            items = []
            for encoding in ["utf-8", "cp949", "euc-kr"]:
                try:
                    with open(csv_path, "r", encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        items = [row for row in reader]
                    break
                except (UnicodeDecodeError, csv.Error):
                    continue
            if items:
                logger.info("CSV 로드 완료: %d건", len(items))
                return items
    return None


def main():
    load_env()
    try:
        service_key = get_api_key()
    except EnvironmentError:
        service_key = None
    ensure_dir(OUT_DIR)

    logger.info("=== 전국 CCTV 표준데이터 수집 시작 (천안시 필터) ===")
    logger.info(
        "참고: CCTV 표준데이터(15013094)는 CSV 파일데이터입니다.\n"
        "  REST API가 동작하지 않으면 아래 URL에서 CSV를 직접 다운로드하세요:\n"
        "  https://www.data.go.kr/data/15013094/standard.do\n"
        "  다운로드 후 %s 에 저장하면 자동으로 로드합니다.", OUT_DIR
    )

    # 0) 수동 다운로드 CSV 확인
    manual_items = load_manual_csv()
    if manual_items:
        cheonan_items = [it for it in manual_items if is_cheonan(it)]
        logger.info("CSV에서 천안 CCTV %d건 필터링 (전체 %d건)", len(cheonan_items), len(manual_items))
        if cheonan_items:
            merged_path = OUT_DIR / "cheonan_cctv.json"
            with open(merged_path, "w", encoding="utf-8") as f:
                json.dump(cheonan_items, f, ensure_ascii=False, indent=2)
            logger.info("저장: %s (%d건)", merged_path, len(cheonan_items))
        logger.info("=== CCTV 수집 완료 (CSV) ===")
        return

    # 1) API 시도 (작동하지 않을 수 있음)
    if not service_key:
        logger.error(
            "API 키가 없고, 수동 CSV 파일도 없습니다.\n"
            "https://www.data.go.kr/data/15013094/standard.do 에서\n"
            "CSV 파일을 다운로드하여 %s 에 저장하세요.", OUT_DIR
        )
        return

    first_page_file = OUT_DIR / "page_001.json"
    if is_already_fetched(first_page_file):
        logger.info("첫 페이지 이미 수집됨 — 로드")
        with open(first_page_file, "r", encoding="utf-8") as f:
            first_data = json.load(f)
    else:
        first_data = fetch_cctv_page(service_key, 1)
        if first_data is None:
            logger.error(
                "API 조회 실패. CCTV 표준데이터(15013094)는 CSV 파일데이터이므로\n"
                "REST API가 제공되지 않을 수 있습니다.\n"
                "다운로드 URL: https://www.data.go.kr/data/15013094/standard.do\n"
                "CSV 파일을 다운로드하여 %s 에 저장하세요.", OUT_DIR
            )
            return

        if "_raw_xml" in first_data:
            xml_path = OUT_DIR / "page_001.xml"
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(first_data["_raw_xml"])
            logger.info("XML 원본 저장: %s", xml_path)
            logger.info("type=json 파라미터가 무시되었을 수 있습니다. XML 파싱이 필요합니다.")
            return

        with open(first_page_file, "w", encoding="utf-8") as f:
            json.dump(first_data, f, ensure_ascii=False, indent=2)

    # 2) 전체 건수 확인
    total_count = get_total_count(first_data)
    if total_count <= 0:
        logger.warning("전체 건수를 파악할 수 없습니다. 첫 페이지 결과만 처리합니다.")
        items = extract_items(first_data)
        cheonan_items = [it for it in items if is_cheonan(it)]
        logger.info("1페이지: 전체 %d건 중 천안 %d건", len(items), len(cheonan_items))
        if cheonan_items:
            out_path = OUT_DIR / "cheonan_cctv.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(cheonan_items, f, ensure_ascii=False, indent=2)
            logger.info("저장: %s", out_path)
        return

    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    logger.info("전체 %d건, %d페이지 수집 예정", total_count, total_pages)

    # 3) 전체 페이지 수집 + 천안 필터링
    all_cheonan_items = []

    # 첫 페이지
    items_p1 = extract_items(first_data)
    all_cheonan_items.extend([it for it in items_p1 if is_cheonan(it)])

    for page_no in tqdm(range(2, total_pages + 1), desc="CCTV 수집"):
        page_file = OUT_DIR / f"page_{page_no:03d}.json"

        if is_already_fetched(page_file):
            with open(page_file, "r", encoding="utf-8") as f:
                page_data = json.load(f)
        else:
            time.sleep(SLEEP_BETWEEN_CALLS)
            page_data = fetch_cctv_page(service_key, page_no)
            if page_data is None:
                logger.warning("페이지 %d 수집 실패 — 건너뜀", page_no)
                continue
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

        items = extract_items(page_data)
        all_cheonan_items.extend([it for it in items if is_cheonan(it)])

    # 4) 천안 CCTV 통합 저장
    if all_cheonan_items:
        merged_path = OUT_DIR / "cheonan_cctv.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(all_cheonan_items, f, ensure_ascii=False, indent=2)
        logger.info(
            "천안 CCTV 통합 저장: %s (%d건)", merged_path, len(all_cheonan_items)
        )
    else:
        logger.warning(
            "천안시 CCTV 데이터가 없습니다.\n"
            "대안: https://www.data.go.kr/data/15013094/standard.do 에서\n"
            "CSV를 다운로드한 후 '천안'으로 필터링하세요."
        )

    logger.info("=== CCTV 수집 완료 ===")


if __name__ == "__main__":
    main()
