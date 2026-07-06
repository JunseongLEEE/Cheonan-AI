"""
03_housing_price.py — 공동주택가격 + 개별공시지가 수집
=====================================================
두 가지 API를 수집한다:

1. 공동주택가격 (국토교통부 공동주택공시가격 서비스)
   https://apis.data.go.kr/1613000/AptPriceService/getAptPriceInfo
   - 시군구코드 + 법정동코드 + 기준연도 기반 조회

2. 개별공시지가 (국토교통부 개별공시지가 서비스)
   https://apis.data.go.kr/1613000/IndvdLandPriceService/getIndvdLandPriceAttr
   - 시군구코드 + 법정동코드 + 기준연도 기반 조회

천안시 동남구(44131) / 서북구(44133) 전 법정동을 대상으로 수집.
XML 원본을 페이지 단위로 저장. Resume 지원.
"""

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    LAWD_CDS,
    SLEEP_BETWEEN_CALLS,
    DATA_RAW_DIR,
    load_env,
    get_api_key,
    setup_logger,
    ensure_dir,
    is_already_fetched,
    make_request,
    FatalAPIError,
    TransientAPIError,
)

# ── 동일 법정동코드 목록 (02_building.py와 공유) ──────────────────
BJDONG_CODES: dict[str, list[str]] = {
    "44131": [
        "10100", "10200", "10300", "10400", "10500",
        "10600", "10700", "10800", "10900", "11000",
        "11100", "11200", "11300", "11400", "11500",
        "11600", "11700", "11800", "11900", "12000",
        "25000", "25300", "25600", "25900", "26200",
        "26500", "26800",
    ],
    "44133": [
        "10100", "10200", "10300", "10400", "10500",
        "10600", "10700", "10800", "10900", "11000",
        "11100", "11200", "12000", "25000", "25300",
        "25600",
    ],
}

# ── API 설정 ──────────────────────────────────────────────────────
# 공동주택공시가격 — 신규 v2 서비스 우선, 구 서비스 폴백
APT_PRICE_URLS = [
    "https://apis.data.go.kr/1613000/AptPriceNewSvc/getLandPriceApt",
    "https://apis.data.go.kr/1613000/AptPriceService/getAptPriceInfo",
    "https://apis.data.go.kr/1613000/AptBasisOfficialPrice/getAptBasisOfficialPriceDetail",
]
# 개별공시지가
LAND_PRICE_URLS = [
    "https://apis.data.go.kr/1613000/IndvdLandPriceService/getIndvdLandPriceAttr",
    "https://apis.data.go.kr/1613000/IndvdLandPriceNewSvc/getIndvdLandPriceAttr",
]

APT_PRICE_URL = APT_PRICE_URLS[0]
LAND_PRICE_URL = LAND_PRICE_URLS[0]

NUM_OF_ROWS = 100

# 조회 연도 범위 — 공시가격은 매년 1월 1일 기준 공시
# 최근 5년 정도면 충분 (오래된 공시가는 실효성 낮음)
CURRENT_YEAR = datetime.now().year
PRICE_YEARS = list(range(CURRENT_YEAR - 4, CURRENT_YEAR + 1))  # 최근 5년

APT_PRICE_DIR = DATA_RAW_DIR / "housing_price"
LAND_PRICE_DIR = DATA_RAW_DIR / "land_price"

logger = setup_logger("housing_price")


def discover_working_url(
    service_key: str,
    url_candidates: list[str],
    test_params: dict,
    label: str,
) -> str | None:
    """여러 URL 후보 중 작동하는 엔드포인트를 찾는다."""
    for url in url_candidates:
        logger.info("%s 엔드포인트 테스트: %s", label, url)
        params = {"serviceKey": service_key, "numOfRows": 1, "pageNo": 1, **test_params}
        try:
            resp = make_request(url, params, timeout=15)
            text = resp.text
            rc = parse_result_code(text)
            if rc in ("00", "0", None):
                tc = parse_total_count(text)
                logger.info("%s 엔드포인트 작동 확인 (resultCode=%s, totalCount=%s): %s", label, rc, tc, url)
                return url
            else:
                rm = parse_result_msg(text) or ""
                logger.warning("%s 엔드포인트 실패 (resultCode=%s, msg=%s): %s", label, rc, rm, url)
        except (FatalAPIError, TransientAPIError, Exception) as e:
            logger.warning("%s 엔드포인트 에러: %s — %s", label, url, e)
    return None


# ── XML 파싱 헬퍼 ────────────────────────────────────────────────

def parse_total_count(xml_text: str) -> int | None:
    """XML 응답에서 totalCount를 파싱한다."""
    try:
        root = ET.fromstring(xml_text)
        for tag in [".//totalCount", ".//body/totalCount"]:
            tc = root.find(tag)
            if tc is not None and tc.text:
                return int(tc.text)
    except ET.ParseError:
        pass
    return None


def parse_result_code(xml_text: str) -> str | None:
    """XML 응답에서 resultCode를 파싱한다."""
    try:
        root = ET.fromstring(xml_text)
        rc = root.find(".//resultCode")
        if rc is not None and rc.text:
            return rc.text
    except ET.ParseError:
        pass
    return None


def parse_result_msg(xml_text: str) -> str | None:
    """XML 응답에서 resultMsg를 파싱한다."""
    try:
        root = ET.fromstring(xml_text)
        rm = root.find(".//resultMsg")
        if rm is not None and rm.text:
            return rm.text
    except ET.ParseError:
        pass
    return None


# ── 공통 수집 함수 ────────────────────────────────────────────────

def fetch_page(
    api_url: str,
    service_key: str,
    params_extra: dict,
    page_no: int,
) -> tuple[str | None, int | None]:
    """
    API 1페이지를 가져온다.
    Returns: (xml_text, total_count) — 실패 시 (None, None)
    """
    params = {
        "serviceKey": service_key,
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
        **params_extra,
    }
    try:
        resp = make_request(api_url, params)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error(
            "make_request 실패: page=%d params=%s — %s",
            page_no, params_extra, e,
        )
        return None, None
    if resp is None:
        return None, None

    xml_text = resp.text
    result_code = parse_result_code(xml_text)

    if result_code and result_code not in ("00", "0"):
        result_msg = parse_result_msg(xml_text) or "알 수 없음"
        logger.debug(
            "resultCode=%s msg=%s params=%s",
            result_code, result_msg, params_extra,
        )
        return xml_text, 0

    total_count = parse_total_count(xml_text)
    return xml_text, total_count


def collect_paginated(
    api_url: str,
    service_key: str,
    params_extra: dict,
    out_dir: Path,
    label: str,
) -> int:
    """
    페이지네이션하며 XML을 저장한다.
    Returns: 저장된 파일 수.
    """
    ensure_dir(out_dir)
    saved = 0

    # 첫 페이지로 totalCount 파악
    first_path = out_dir / "page_0001.xml"
    if is_already_fetched(first_path):
        with open(first_path, "r", encoding="utf-8") as f:
            total_count = parse_total_count(f.read())
        saved += 1
    else:
        xml_text, total_count = fetch_page(api_url, service_key, params_extra, 1)
        if xml_text and total_count and total_count > 0:
            first_path.write_text(xml_text, encoding="utf-8")
            saved += 1
        elif total_count == 0 or total_count is None:
            return 0
        time.sleep(SLEEP_BETWEEN_CALLS)

    if not total_count or total_count == 0:
        return saved

    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS

    if total_pages > 1:
        logger.info("%s: totalCount=%d → %d pages", label, total_count, total_pages)

    for page_no in range(2, total_pages + 1):
        out_path = out_dir / f"page_{page_no:04d}.xml"
        if is_already_fetched(out_path):
            saved += 1
            continue

        xml_text, _ = fetch_page(api_url, service_key, params_extra, page_no)
        if xml_text:
            out_path.write_text(xml_text, encoding="utf-8")
            saved += 1
        time.sleep(SLEEP_BETWEEN_CALLS)

    return saved


# ── 공동주택가격 수집 ─────────────────────────────────────────────

def collect_apt_prices(service_key: str) -> int:
    """공동주택공시가격을 시군구/법정동/연도별로 수집한다."""
    logger.info("=" * 60)
    logger.info("공동주택가격 수집 시작")
    logger.info("=" * 60)

    total_saved = 0

    for sigungu_cd in LAWD_CDS:
        bjdong_list = BJDONG_CODES.get(sigungu_cd, [])
        combos = [(bjdong_cd, year) for bjdong_cd in bjdong_list for year in PRICE_YEARS]

        pbar = tqdm(combos, desc=f"공동주택 {sigungu_cd}")
        for bjdong_cd, year in pbar:
            pbar.set_postfix(dong=bjdong_cd, year=year)

            out_dir = APT_PRICE_DIR / sigungu_cd / bjdong_cd / str(year)
            params_extra = {
                "sigunguCd": sigungu_cd,
                "bjdongCd": bjdong_cd,
                "stdrYear": str(year),
            }
            count = collect_paginated(
                APT_PRICE_URL, service_key, params_extra, out_dir,
                label=f"apt {sigungu_cd}/{bjdong_cd}/{year}",
            )
            total_saved += count

    logger.info("공동주택가격 수집 완료. 저장 파일: %d", total_saved)
    return total_saved


# ── 개별공시지가 수집 ─────────────────────────────────────────────

def collect_land_prices(service_key: str) -> int:
    """개별공시지가를 시군구/법정동/연도별로 수집한다."""
    logger.info("=" * 60)
    logger.info("개별공시지가 수집 시작")
    logger.info("=" * 60)

    total_saved = 0

    for sigungu_cd in LAWD_CDS:
        bjdong_list = BJDONG_CODES.get(sigungu_cd, [])
        combos = [(bjdong_cd, year) for bjdong_cd in bjdong_list for year in PRICE_YEARS]

        pbar = tqdm(combos, desc=f"공시지가 {sigungu_cd}")
        for bjdong_cd, year in pbar:
            pbar.set_postfix(dong=bjdong_cd, year=year)

            out_dir = LAND_PRICE_DIR / sigungu_cd / bjdong_cd / str(year)
            params_extra = {
                "sigunguCd": sigungu_cd,
                "bjdongCd": bjdong_cd,
                "stdrYear": str(year),
            }
            count = collect_paginated(
                LAND_PRICE_URL, service_key, params_extra, out_dir,
                label=f"land {sigungu_cd}/{bjdong_cd}/{year}",
            )
            total_saved += count

    logger.info("개별공시지가 수집 완료. 저장 파일: %d", total_saved)
    return total_saved


# ── 메인 ──────────────────────────────────────────────────────────

def main() -> None:
    global APT_PRICE_URL, LAND_PRICE_URL

    load_env()
    service_key = get_api_key()

    ensure_dir(APT_PRICE_DIR)
    ensure_dir(LAND_PRICE_DIR)

    # 엔드포인트 자동 탐색
    test_params_apt = {
        "sigunguCd": "44131",
        "bjdongCd": "10100",
        "stdrYear": str(CURRENT_YEAR - 1),
    }
    found_apt = discover_working_url(service_key, APT_PRICE_URLS, test_params_apt, "공동주택")
    if found_apt:
        APT_PRICE_URL = found_apt
    else:
        logger.warning(
            "공동주택공시가격 API 작동 엔드포인트를 찾지 못했습니다. "
            "기본 URL로 시도합니다: %s", APT_PRICE_URL
        )

    test_params_land = {
        "sigunguCd": "44131",
        "bjdongCd": "10100",
        "stdrYear": str(CURRENT_YEAR - 1),
    }
    found_land = discover_working_url(service_key, LAND_PRICE_URLS, test_params_land, "공시지가")
    if found_land:
        LAND_PRICE_URL = found_land
    else:
        logger.warning(
            "개별공시지가 API 작동 엔드포인트를 찾지 못했습니다. "
            "기본 URL로 시도합니다: %s", LAND_PRICE_URL
        )

    # 1) 공동주택가격
    apt_count = collect_apt_prices(service_key)

    # 2) 개별공시지가
    land_count = collect_land_prices(service_key)

    logger.info("=" * 60)
    logger.info(
        "전체 수집 완료. 공동주택: %d / 공시지가: %d / 합계: %d",
        apt_count, land_count, apt_count + land_count,
    )
    logger.info("공동주택 저장 경로: %s", APT_PRICE_DIR)
    logger.info("공시지가 저장 경로: %s", LAND_PRICE_DIR)


if __name__ == "__main__":
    main()
