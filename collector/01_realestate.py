"""
01_realestate.py — 부동산 실거래가 8종 수집
=============================================
공공데이터포털 국토교통부 실거래가 API 8종을 천안시(동남구·서북구) 대상으로 수집한다.

수집 유형:
  1. 아파트 매매 / 전월세
  2. 오피스텔 매매 / 전월세
  3. 연립다세대 매매 / 전월세
  4. 단독/다가구 매매 / 전월세  ← 주의: 개인정보 보호로 부분 주소만 제공됨

저장 경로: ../data/raw/realestate/{type_name}/{lawd_cd}_{YYYYMM}.xml
"""

import time
from pathlib import Path

from tqdm import tqdm

from _common import (
    load_env,
    get_api_key,
    setup_logger,
    make_request,
    ensure_dir,
    generate_months,
    is_already_fetched,
    FatalAPIError,
    TransientAPIError,
    LAWD_CDS,
    TRADE_START_YEAR,
    RENT_START_YEAR,
    SLEEP_BETWEEN_CALLS,
    DATA_RAW_DIR,
)

logger = setup_logger("realestate")

# ── API 엔드포인트 정의 ───────────────────────────────────────
# (type_name, url, start_year)
ENDPOINTS = [
    # 아파트
    (
        "apt_trade",
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
        TRADE_START_YEAR,
    ),
    (
        "apt_rent",
        "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        RENT_START_YEAR,
    ),
    # 오피스텔
    (
        "offi_trade",
        "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
        TRADE_START_YEAR,
    ),
    (
        "offi_rent",
        "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
        RENT_START_YEAR,
    ),
    # 연립다세대
    (
        "rh_trade",
        "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        TRADE_START_YEAR,
    ),
    (
        "rh_rent",
        "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent",
        RENT_START_YEAR,
    ),
    # 단독/다가구
    # NOTE: 단독/다가구는 개인정보 보호 정책상 부분 주소(읍면동 수준)만 제공됨.
    #       정확한 위치 매핑이 어려울 수 있으므로 분석 시 유의할 것.
    (
        "sh_trade",
        "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",
        TRADE_START_YEAR,
    ),
    (
        "sh_rent",
        "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
        RENT_START_YEAR,
    ),
]

OUTPUT_BASE = DATA_RAW_DIR / "realestate"


def fetch_all(service_key: str) -> dict:
    """
    8종 × 2구 × 월별 전체를 순회하며 XML 파일로 저장한다.

    Returns:
        {"total": int, "skipped": int, "downloaded": int, "errors": int}
    """
    stats = {"total": 0, "skipped": 0, "downloaded": 0, "errors": 0}

    # 작업 목록 생성 (진행률 표시를 위해 미리 계산)
    tasks: list[tuple[str, str, int, str, str]] = []
    for type_name, url, start_year in ENDPOINTS:
        months = generate_months(start_year)
        for lawd_cd in LAWD_CDS:
            for ym in months:
                tasks.append((type_name, url, start_year, lawd_cd, ym))

    stats["total"] = len(tasks)
    logger.info("수집 대상: %d건 (8종 × 2구 × 월별)", stats["total"])

    with tqdm(total=len(tasks), desc="부동산 실거래가", unit="req") as pbar:
        for type_name, url, _start_year, lawd_cd, ym in tasks:
            out_dir = ensure_dir(OUTPUT_BASE / type_name)
            out_file = out_dir / f"{lawd_cd}_{ym}.xml"

            pbar.set_postfix_str(f"{type_name}/{lawd_cd}_{ym}")

            # 이미 다운로드된 파일은 건너뜀 (resume 지원)
            if is_already_fetched(out_file):
                stats["skipped"] += 1
                pbar.update(1)
                continue

            params = {
                "serviceKey": service_key,
                "LAWD_CD": lawd_cd,
                "DEAL_YMD": ym,
                "numOfRows": "9999",
                "pageNo": "1",
            }

            try:
                resp = make_request(url, params)
            except (FatalAPIError, TransientAPIError, Exception) as e:
                logger.error("수집 실패: %s %s_%s — %s", type_name, lawd_cd, ym, e)
                stats["errors"] += 1
                pbar.update(1)
                continue

            if resp is None:
                logger.error("수집 실패: %s %s_%s", type_name, lawd_cd, ym)
                stats["errors"] += 1
                pbar.update(1)
                continue

            # XML 응답 저장
            out_file.write_bytes(resp.content)
            stats["downloaded"] += 1

            pbar.update(1)
            time.sleep(SLEEP_BETWEEN_CALLS)

    return stats


def main() -> None:
    load_env()
    service_key = get_api_key()

    logger.info("=== 부동산 실거래가 8종 수집 시작 ===")
    logger.info("대상 지역: 천안 동남구(%s), 서북구(%s)", *LAWD_CDS)
    logger.info(
        "수집 기간: 매매 %d-01 ~ 현재 / 전월세 %d-01 ~ 현재",
        TRADE_START_YEAR,
        RENT_START_YEAR,
    )

    stats = fetch_all(service_key)

    logger.info("=== 수집 완료 ===")
    logger.info(
        "총 %d건 | 신규 다운로드 %d | 기존 스킵 %d | 오류 %d",
        stats["total"],
        stats["downloaded"],
        stats["skipped"],
        stats["errors"],
    )

    if stats["errors"] > 0:
        logger.warning(
            "오류가 %d건 발생했습니다. 재실행하면 실패한 파일만 다시 시도합니다.",
            stats["errors"],
        )


if __name__ == "__main__":
    main()
