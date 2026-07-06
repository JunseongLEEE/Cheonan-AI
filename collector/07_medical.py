"""
07_medical.py — 병원 및 약국 정보 수집 (천안시)
================================================
병원 API: https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList
약국 API: https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList

충청남도(sidoCd=34) 천안시 병원·약국 목록을 수집한다.
시군구코드는 API별로 다를 수 있어 여러 코드를 시도한다.
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

logger = setup_logger("medical")

# ── 설정 ──────────────────────────────────────────────────────────
HOSPITAL_URL = (
    "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
)
PHARMACY_URL = (
    "https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList"
)
OUT_DIR = DATA_RAW_DIR / "medical"

NUM_OF_ROWS = 1000

# 충청남도 시도코드
SIDO_CD = "340000"

# 천안시 시군구코드 후보 (건강보험심사평가원 API 코드 체계)
# 이 API는 법정동코드(44131)가 아닌 자체 코드를 사용할 수 있음
SGGU_CANDIDATES = [
    ("340010", "천안시(통합)"),
    ("340011", "천안시 동남구"),
    ("340012", "천안시 서북구"),
    # 다른 가능한 코드 형태
    ("34010", "천안(5자리)"),
    ("34011", "동남구(5자리)"),
    ("34012", "서북구(5자리)"),
]


def fetch_page(
    service_key: str,
    base_url: str,
    sido_cd: str,
    sggu_cd: str,
    page_no: int,
) -> dict | None:
    """병원/약국 목록 1페이지를 조회한다."""
    params = {
        "serviceKey": service_key,
        "sidoCd": sido_cd,
        "sgguCd": sggu_cd,
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
    }
    try:
        resp = make_request(base_url, params, timeout=30)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error(
            "make_request 실패: %s sggu=%s page=%d — %s",
            base_url.split("/")[-1], sggu_cd, page_no, e,
        )
        return None
    if resp is None:
        return None

    text = resp.text.strip()

    # JSON 시도
    try:
        return resp.json()
    except Exception:
        pass

    # XML 응답 (이 API는 기본 XML)
    if text.startswith("<?xml") or text.startswith("<"):
        return {"_raw_xml": text, "_content_type": "xml"}

    logger.warning("알 수 없는 응답: %s", text[:200])
    return None


def parse_xml_items(xml_text: str) -> tuple[list[dict], int]:
    """
    간단한 XML 파싱으로 item 목록과 totalCount를 추출한다.
    xml.etree 사용.
    """
    import xml.etree.ElementTree as ET

    items = []
    total_count = 0

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("XML 파싱 오류: %s", e)
        return items, total_count

    # totalCount
    tc_elem = root.find(".//totalCount")
    if tc_elem is not None and tc_elem.text:
        total_count = int(tc_elem.text)

    # items
    for item_elem in root.findall(".//item"):
        item = {}
        for child in item_elem:
            item[child.tag] = child.text
        if item:
            items.append(item)

    return items, total_count


def detect_working_sggu(service_key: str, base_url: str) -> str | None:
    """
    여러 시군구코드 후보를 시도하여 데이터가 반환되는 코드를 찾는다.
    """
    logger.info("시군구코드 자동 탐색 중...")

    for sggu_cd, label in SGGU_CANDIDATES:
        params = {
            "serviceKey": service_key,
            "sidoCd": SIDO_CD,
            "sgguCd": sggu_cd,
            "numOfRows": 1,
            "pageNo": 1,
        }
        try:
            resp = make_request(base_url, params, timeout=15)
        except (FatalAPIError, TransientAPIError, Exception) as e:
            logger.warning("시군구코드 탐색 실패: sggu=%s — %s", sggu_cd, e)
            continue
        if resp is None:
            continue

        text = resp.text.strip()
        if "<totalCount>" in text:
            import re
            match = re.search(r"<totalCount>(\d+)</totalCount>", text)
            if match and int(match.group(1)) > 0:
                logger.info(
                    "유효한 코드 발견: sgguCd=%s (%s), totalCount=%s",
                    sggu_cd, label, match.group(1),
                )
                return sggu_cd

        # JSON 응답인 경우
        try:
            data = resp.json()
            tc = data.get("response", {}).get("body", {}).get("totalCount", 0)
            if int(tc) > 0:
                logger.info(
                    "유효한 코드 발견: sgguCd=%s (%s), totalCount=%s",
                    sggu_cd, label, tc,
                )
                return sggu_cd
        except Exception:
            pass

        time.sleep(0.2)

    # 시도코드만으로 조회 시도 (sgguCd 없이)
    logger.info("시군구코드 없이 시도코드만으로 조회 시도...")
    return ""  # 빈 문자열 = sgguCd 파라미터 생략


def collect_facilities(
    service_key: str,
    base_url: str,
    facility_type: str,
    sggu_cd: str,
):
    """병원 또는 약국 데이터를 수집한다."""
    type_dir = ensure_dir(OUT_DIR / facility_type)
    logger.info("--- %s 수집 시작 (sgguCd=%s) ---", facility_type, sggu_cd or "전체충남")

    # 1) 첫 페이지 조회
    first_file = type_dir / "page_001.xml"
    first_json_file = type_dir / "page_001.json"

    if is_already_fetched(first_file) or is_already_fetched(first_json_file):
        logger.info("첫 페이지 이미 수집됨")
        if is_already_fetched(first_file):
            with open(first_file, "r", encoding="utf-8") as f:
                xml_text = f.read()
            items_p1, total_count = parse_xml_items(xml_text)
        else:
            with open(first_json_file, "r", encoding="utf-8") as f:
                first_data = json.load(f)
            items_p1 = []
            total_count = 0
    else:
        result = fetch_page(service_key, base_url, SIDO_CD, sggu_cd, 1)
        if result is None:
            logger.error("%s 첫 페이지 조회 실패", facility_type)
            return

        if "_raw_xml" in result:
            xml_text = result["_raw_xml"]
            with open(first_file, "w", encoding="utf-8") as f:
                f.write(xml_text)
            items_p1, total_count = parse_xml_items(xml_text)
        else:
            with open(first_json_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            items_p1 = []
            total_count = 0

    if total_count <= 0 and not items_p1:
        logger.warning(
            "%s: 데이터가 없습니다. 시군구코드를 확인하세요.", facility_type
        )
        return

    total_pages = max(1, (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS)
    logger.info("%s: 전체 %d건, %d페이지", facility_type, total_count, total_pages)

    all_items = list(items_p1)

    # 2) 나머지 페이지
    for page_no in tqdm(
        range(2, total_pages + 1),
        desc=f"{facility_type} 수집",
        initial=1,
        total=total_pages,
    ):
        page_file = type_dir / f"page_{page_no:03d}.xml"

        if is_already_fetched(page_file):
            with open(page_file, "r", encoding="utf-8") as f:
                xml_text = f.read()
        else:
            time.sleep(SLEEP_BETWEEN_CALLS)
            result = fetch_page(service_key, base_url, SIDO_CD, sggu_cd, page_no)
            if result is None:
                logger.warning("페이지 %d 수집 실패 — 건너뜀", page_no)
                continue

            if "_raw_xml" in result:
                xml_text = result["_raw_xml"]
                with open(page_file, "w", encoding="utf-8") as f:
                    f.write(xml_text)
            else:
                json_file = type_dir / f"page_{page_no:03d}.json"
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                continue

        items, _ = parse_xml_items(xml_text)
        if not items:
            logger.info("페이지 %d: 빈 결과 — 수집 종료", page_no)
            break
        all_items.extend(items)

    # 3) 천안 필터링 (시도코드만으로 조회한 경우)
    if not sggu_cd:
        cheonan_items = [
            it for it in all_items
            if any(
                "천안" in str(it.get(field, ""))
                for field in ["addr", "yadmNm", "sgguCdNm", "sidoCdNm", "hospUrl"]
            ) or "천안" in json.dumps(it, ensure_ascii=False)
        ]
        logger.info(
            "충남 전체 %d건 중 천안 %d건 필터링",
            len(all_items), len(cheonan_items),
        )
        all_items = cheonan_items

    # 4) 통합 저장
    if all_items:
        merged_path = type_dir / f"cheonan_{facility_type}.json"
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        logger.info(
            "%s 통합 저장: %s (%d건)", facility_type, merged_path, len(all_items)
        )
    else:
        logger.warning("%s: 천안시 데이터가 없습니다.", facility_type)

    return len(all_items)


def main():
    load_env()
    service_key = get_api_key()
    ensure_dir(OUT_DIR)

    logger.info("=== 병원·약국 정보 수집 시작 (천안시) ===")

    # 병원 시군구코드 탐색
    hosp_sggu = detect_working_sggu(service_key, HOSPITAL_URL)
    if hosp_sggu is None:
        logger.error(
            "병원 API에서 유효한 시군구코드를 찾지 못했습니다.\n"
            "SIDO_CD, SGGU_CANDIDATES를 확인하세요."
        )
    else:
        collect_facilities(service_key, HOSPITAL_URL, "hospital", hosp_sggu)

    # 약국
    logger.info("")
    pharm_sggu = detect_working_sggu(service_key, PHARMACY_URL)
    if pharm_sggu is None:
        logger.error("약국 API에서 유효한 시군구코드를 찾지 못했습니다.")
    else:
        collect_facilities(service_key, PHARMACY_URL, "pharmacy", pharm_sggu)

    logger.info("=== 병원·약국 수집 완료 ===")


if __name__ == "__main__":
    main()
