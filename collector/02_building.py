"""
02_building.py — 건축HUB 건축물대장 (표제부) 수집
=================================================
API: 국토교통부 건축물대장정보 서비스
     https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo

천안시 동남구(44131) / 서북구(44133)의 건축물대장 표제부 전체를 수집한다.
- 시군구코드만으로 페이지네이션하여 전체 조회 시도
- 실패 시 법정동코드별로 반복 조회
- XML 원본을 페이지 단위로 저장
- Resume 지원 (이미 저장된 페이지는 스킵)
"""

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from tqdm import tqdm

# _common 모듈 임포트
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

# ── 설정 ──────────────────────────────────────────────────────────
API_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
NUM_OF_ROWS = 100
OUT_DIR = DATA_RAW_DIR / "building"

# 천안시 법정동코드 (5자리 시군구 + 5자리 법정동)
# 동남구(44131), 서북구(44133) 내 주요 법정동코드 목록
# 출처: 행정표준코드관리시스템 (https://www.code.go.kr)
BJDONG_CODES: dict[str, list[str]] = {
    "44131": [
        "10100",  # 봉명동
        "10200",  # 다가동
        "10300",  # 대흥동
        "10400",  # 사직동
        "10500",  # 오룡동
        "10600",  # 원성동
        "10700",  # 청룡동
        "10800",  # 문화동
        "10900",  # 신부동
        "11000",  # 쌍용동
        "11100",  # 영성동
        "11200",  # 성황동
        "11300",  # 유량동
        "11400",  # 삼룡동
        "11500",  # 구성동
        "11600",  # 신방동
        "11700",  # 용곡동
        "11800",  # 청당동
        "11900",  # 구룡동
        "12000",  # 목천읍
        "25000",  # 풍세면
        "25300",  # 광덕면
        "25600",  # 북면
        "25900",  # 성남면
        "26200",  # 수신면
        "26500",  # 병천면
        "26800",  # 동면
    ],
    "44133": [
        "10100",  # 와촌동
        "10200",  # 쌍용동 (서북)
        "10300",  # 불당동
        "10400",  # 백석동
        "10500",  # 두정동
        "10600",  # 성정동
        "10700",  # 차암동
        "10800",  # 업성동
        "10900",  # 신당동
        "11000",  # 부성동
        "11100",  # 성성동
        "11200",  # 아산만방조제
        "12000",  # 직산읍
        "25000",  # 성환읍
        "25300",  # 성거읍
        "25600",  # 입장면
    ],
}

logger = setup_logger("building")


def parse_total_count(xml_text: str) -> int | None:
    """XML 응답에서 totalCount를 파싱한다."""
    try:
        root = ET.fromstring(xml_text)
        # 네임스페이스 없는 단순 태그 검색
        tc = root.find(".//totalCount")
        if tc is not None and tc.text:
            return int(tc.text)
        # body/totalCount 경로도 시도
        tc = root.find(".//body/totalCount")
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


def fetch_building_page(
    service_key: str,
    sigungu_cd: str,
    bjdong_cd: str,
    page_no: int,
) -> tuple[str | None, int | None]:
    """
    건축물대장 1페이지를 가져온다.
    Returns: (xml_text, total_count) — 실패 시 (None, None)
    """
    params = {
        "serviceKey": service_key,
        "sigunguCd": sigungu_cd,
        "bjdongCd": bjdong_cd,
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
    }
    try:
        resp = make_request(API_URL, params)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error(
            "make_request 실패: sigungu=%s bjdong=%s page=%d — %s",
            sigungu_cd, bjdong_cd, page_no, e,
        )
        return None, None
    if resp is None:
        return None, None

    xml_text = resp.text
    result_code = parse_result_code(xml_text)
    if result_code and result_code != "00":
        logger.debug(
            "sigungu=%s bjdong=%s resultCode=%s (데이터 없음 가능)",
            sigungu_cd, bjdong_cd, result_code,
        )
        return xml_text, 0

    total_count = parse_total_count(xml_text)
    return xml_text, total_count


def collect_sigungu_only(service_key: str, sigungu_cd: str) -> bool:
    """
    bjdongCd 없이 시군구코드만으로 조회를 시도한다.
    데이터가 반환되면 True, 아니면 False.
    """
    logger.info("시군구코드 단독 조회 시도: %s", sigungu_cd)
    xml_text, total_count = fetch_building_page(service_key, sigungu_cd, "", 1)

    if total_count and total_count > 0:
        logger.info(
            "시군구 단독 조회 성공! sigungu=%s totalCount=%d", sigungu_cd, total_count
        )
        return True
    else:
        logger.info(
            "시군구 단독 조회 불가 (totalCount=%s). 법정동별 조회로 전환.",
            total_count,
        )
        return False


def collect_by_sigungu(service_key: str, sigungu_cd: str) -> int:
    """시군구코드만으로 전체 페이지를 수집한다. 저장된 파일 수 반환."""
    out_dir = ensure_dir(OUT_DIR / sigungu_cd)
    saved = 0

    # 첫 페이지로 totalCount 파악
    first_path = out_dir / f"page_{1:04d}.xml"
    if is_already_fetched(first_path):
        with open(first_path, "r", encoding="utf-8") as f:
            total_count = parse_total_count(f.read())
        logger.info("Resume: 첫 페이지에서 totalCount=%s 복원", total_count)
    else:
        xml_text, total_count = fetch_building_page(service_key, sigungu_cd, "", 1)
        if xml_text and total_count and total_count > 0:
            first_path.write_text(xml_text, encoding="utf-8")
            saved += 1
        time.sleep(SLEEP_BETWEEN_CALLS)

    if not total_count or total_count == 0:
        return saved

    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    logger.info(
        "sigungu=%s totalCount=%d → %d pages", sigungu_cd, total_count, total_pages
    )

    for page_no in tqdm(range(1, total_pages + 1), desc=f"건축물대장 {sigungu_cd}"):
        out_path = out_dir / f"page_{page_no:04d}.xml"
        if is_already_fetched(out_path):
            saved += 1
            continue

        xml_text, _ = fetch_building_page(service_key, sigungu_cd, "", page_no)
        if xml_text:
            out_path.write_text(xml_text, encoding="utf-8")
            saved += 1
        time.sleep(SLEEP_BETWEEN_CALLS)

    return saved


def collect_by_bjdong(service_key: str, sigungu_cd: str) -> int:
    """법정동코드별로 반복 조회하여 수집한다. 저장된 파일 수 반환."""
    bjdong_list = BJDONG_CODES.get(sigungu_cd, [])
    if not bjdong_list:
        logger.warning("법정동코드 목록 없음: sigungu=%s", sigungu_cd)
        return 0

    saved_total = 0

    for bjdong_cd in tqdm(bjdong_list, desc=f"법정동 {sigungu_cd}"):
        out_dir = ensure_dir(OUT_DIR / sigungu_cd / bjdong_cd)

        # 첫 페이지로 totalCount 파악
        first_path = out_dir / "page_0001.xml"
        if is_already_fetched(first_path):
            with open(first_path, "r", encoding="utf-8") as f:
                total_count = parse_total_count(f.read())
        else:
            xml_text, total_count = fetch_building_page(
                service_key, sigungu_cd, bjdong_cd, 1
            )
            if xml_text and total_count and total_count > 0:
                first_path.write_text(xml_text, encoding="utf-8")
                saved_total += 1
            elif total_count == 0 or total_count is None:
                logger.debug(
                    "데이터 없음: sigungu=%s bjdong=%s", sigungu_cd, bjdong_cd
                )
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue
            time.sleep(SLEEP_BETWEEN_CALLS)

        if not total_count or total_count == 0:
            continue

        total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
        logger.info(
            "sigungu=%s bjdong=%s totalCount=%d → %d pages",
            sigungu_cd, bjdong_cd, total_count, total_pages,
        )

        for page_no in range(1, total_pages + 1):
            out_path = out_dir / f"page_{page_no:04d}.xml"
            if is_already_fetched(out_path):
                saved_total += 1
                continue

            xml_text, _ = fetch_building_page(
                service_key, sigungu_cd, bjdong_cd, page_no
            )
            if xml_text:
                out_path.write_text(xml_text, encoding="utf-8")
                saved_total += 1
            time.sleep(SLEEP_BETWEEN_CALLS)

    return saved_total


def main() -> None:
    load_env()
    service_key = get_api_key()
    ensure_dir(OUT_DIR)

    grand_total = 0

    for sigungu_cd in LAWD_CDS:
        logger.info("=" * 60)
        logger.info("수집 시작: 시군구 %s", sigungu_cd)
        logger.info("=" * 60)

        # 먼저 시군구코드만으로 시도
        if collect_sigungu_only(service_key, sigungu_cd):
            count = collect_by_sigungu(service_key, sigungu_cd)
        else:
            # 법정동별로 반복 조회
            count = collect_by_bjdong(service_key, sigungu_cd)

        logger.info("시군구 %s 저장 파일 수: %d", sigungu_cd, count)
        grand_total += count

    logger.info("=" * 60)
    logger.info("건축물대장 수집 완료. 총 저장 파일: %d", grand_total)
    logger.info("저장 경로: %s", OUT_DIR)


if __name__ == "__main__":
    main()
