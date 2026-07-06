#!/usr/bin/env python3
"""
08. 에어코리아 대기오염 + 측정소 수집
======================================
API 2종:
  1) 측정소정보 — 충남 전체 → 천안 필터
  2) 대기오염 실시간 측정 — 천안 측정소별 3개월치

출처: https://www.data.go.kr/data/15073861/openapi.do (측정소)
      https://www.data.go.kr/data/15073877/openapi.do (대기오염)
"""

import json
import time
from pathlib import Path

from tqdm import tqdm

from _common import (
    DATA_RAW_DIR,
    SLEEP_BETWEEN_CALLS,
    ensure_dir,
    get_api_key,
    is_already_fetched,
    load_env,
    make_request,
    setup_logger,
)

logger = setup_logger("air_quality")

# ── API URLs ──────────────────────────────────────────────────
STATION_URL = (
    "https://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
)
AIR_QUALITY_URL = (
    "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc2/"
    "getMsrstnAcctoRltmMesureDnsty"
)

# ── 저장 경로 ─────────────────────────────────────────────────
OUT_DIR = DATA_RAW_DIR / "air_quality"


def fetch_cheonan_stations(service_key: str) -> list[dict]:
    """충남 측정소 목록을 조회하고 천안 측정소만 필터링하여 반환한다."""
    out_path = ensure_dir(OUT_DIR) / "stations.json"

    if is_already_fetched(out_path):
        logger.info("stations.json 이미 존재 — 로드")
        with open(out_path, "r", encoding="utf-8") as f:
            return json.load(f)

    params = {
        "serviceKey": service_key,
        "addr": "충남",
        "returnType": "json",
        "numOfRows": 100,
        "pageNo": 1,
    }

    resp = make_request(STATION_URL, params, logger)
    if resp is None:
        logger.error("측정소 목록 조회 실패")
        return []

    data = resp.json()

    try:
        items = data["response"]["body"]["items"]
    except (KeyError, TypeError):
        logger.error("측정소 응답 파싱 실패: %s", data)
        return []

    # 천안 필터: addr 에 '천안' 포함
    cheonan_stations = [
        item for item in items if "천안" in item.get("addr", "")
    ]
    logger.info(
        "충남 측정소 %d개 중 천안 %d개 필터링",
        len(items),
        len(cheonan_stations),
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cheonan_stations, f, ensure_ascii=False, indent=2)

    return cheonan_stations


def fetch_station_air_quality(
    service_key: str, station_name: str
) -> dict | None:
    """특정 측정소의 최근 3개월 대기오염 데이터를 수집한다."""
    safe_name = station_name.replace("/", "_").replace(" ", "_")
    out_path = ensure_dir(OUT_DIR) / f"{safe_name}.json"

    if is_already_fetched(out_path):
        logger.info("%s — 이미 수집 완료, 스킵", station_name)
        return None

    params = {
        "serviceKey": service_key,
        "stationName": station_name,
        "returnType": "json",
        "numOfRows": 100,
        "dataTerm": "3MONTH",
    }

    resp = make_request(AIR_QUALITY_URL, params, logger)
    if resp is None:
        logger.error("%s 대기오염 데이터 조회 실패", station_name)
        return None

    data = resp.json()

    try:
        items = data["response"]["body"]["items"]
    except (KeyError, TypeError):
        logger.error("%s 응답 파싱 실패: %s", station_name, data)
        return None

    result = {
        "stationName": station_name,
        "dataTerm": "3MONTH",
        "totalCount": len(items),
        "items": items,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("%s — %d건 저장 완료", station_name, len(items))
    return result


def main() -> None:
    """에어코리아 대기오염 + 측정소 데이터 수집 메인."""
    load_env()
    service_key = get_api_key("DATA_GO_KR_KEY")
    ensure_dir(OUT_DIR)

    # 1) 천안 측정소 목록
    logger.info("=== 천안 측정소 목록 수집 ===")
    stations = fetch_cheonan_stations(service_key)

    if not stations:
        logger.error("천안 측정소를 찾을 수 없습니다.")
        return

    station_names = [s.get("stationName", "") for s in stations if s.get("stationName")]
    logger.info("천안 측정소: %s", ", ".join(station_names))

    # 2) 각 측정소별 대기오염 데이터
    logger.info("=== 측정소별 대기오염 데이터 수집 ===")
    for name in tqdm(station_names, desc="대기오염"):
        fetch_station_air_quality(service_key, name)
        time.sleep(SLEEP_BETWEEN_CALLS)

    logger.info("=== 대기오염 수집 완료 ===")


if __name__ == "__main__":
    main()
