#!/usr/bin/env python3
"""
09. SGIS 통계지리정보 수집 (6개 API)
=====================================
SGIS (통계지리정보서비스) 에서 천안시 읍면동 단위 통계를 수집한다.

API 6종:
  1) 인구통계        (population)
  2) 가구통계        (household)
  3) 주택통계        (house)
  4) 사업체통계      (company)
  5) 격자별 인구     (searchpopulation) — 500m 격자
  6) 행정구역 경계   (hadmarea)         — GeoJSON

인증: consumer_key + consumer_secret → accessToken (SGISTokenManager)

출처: https://sgis.kostat.go.kr/developer/html/openApi/api_main.html
"""

import json
import time
from pathlib import Path

from tqdm import tqdm

from _common import (
    DATA_RAW_DIR,
    SLEEP_BETWEEN_CALLS,
    FatalAPIError,
    SGISTokenManager,
    TransientAPIError,
    ensure_dir,
    is_already_fetched,
    load_env,
    make_request,
    setup_logger,
)

# SGIS 행정동코드 (법정동코드 44131/44133과 다름!)
SGIS_CHEONAN_DONGNAM = "34011"
SGIS_CHEONAN_SEOBUK = "34012"

logger = setup_logger("sgis")

# ── SGIS API Base URLs ────────────────────────────────────────
SGIS_BASE = "https://sgisapi.kostat.go.kr/OpenAPI3"

STATS_APIS = {
    "population": f"{SGIS_BASE}/stats/population.json",
    "household": f"{SGIS_BASE}/stats/household.json",
    "house": f"{SGIS_BASE}/stats/house.json",
    "company": f"{SGIS_BASE}/stats/company.json",
}

GRID_POPULATION_URL = f"{SGIS_BASE}/stats/searchpopulation.json"
BOUNDARY_URL = f"{SGIS_BASE}/boundary/hadmarea.geojson"

# ── 천안 UTMK 좌표 범위 (격자 인구용) ────────────────────────
CHEONAN_UTMK = {
    "x_min": 176000,
    "y_min": 348000,
    "x_max": 215000,
    "y_max": 382000,
}

STATS_YEAR = "2023"

# ── 저장 경로 ─────────────────────────────────────────────────
OUT_DIR = DATA_RAW_DIR / "sgis"


def discover_sub_areas(
    token_mgr: SGISTokenManager, parent_cd: str
) -> list[dict]:
    """상위 행정구역의 하위 읍면동 코드를 조회한다."""
    cache_path = ensure_dir(OUT_DIR / "admin_codes") / f"{parent_cd}.json"

    if is_already_fetched(cache_path):
        logger.info("하위 행정구역 캐시 로드: %s", parent_cd)
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 행정구역 코드 조회를 위해 stats API 중 하나를 사용하여 하위 목록 파악
    # SGIS 는 low_search=1 로 하위 목록을 반환
    url = STATS_APIS["population"]
    params = {
        "accessToken": token_mgr.get_token(),
        "year": STATS_YEAR,
        "adm_cd": parent_cd,
        "low_search": "1",
    }

    try:
        resp = make_request(url, params)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error("하위 행정구역 조회 실패: %s — %s", parent_cd, e)
        return []
    if resp is None:
        logger.error("하위 행정구역 조회 실패: %s", parent_cd)
        return []

    data = resp.json()
    result = data.get("result", [])

    if not result:
        logger.warning("하위 행정구역 없음: %s — %s", parent_cd, data)
        return []

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("%s 하위 행정구역 %d개 발견", parent_cd, len(result))
    return result


def fetch_stats(
    token_mgr: SGISTokenManager,
    api_name: str,
    adm_cd: str,
    adm_nm: str = "",
) -> dict | None:
    """특정 통계 API 에서 읍면동 단위 데이터를 수집한다."""
    api_dir = ensure_dir(OUT_DIR / api_name)
    out_path = api_dir / f"{adm_cd}.json"

    if is_already_fetched(out_path):
        logger.debug("%s/%s 이미 수집 완료", api_name, adm_cd)
        return None

    url = STATS_APIS[api_name]
    params = {
        "accessToken": token_mgr.get_token(),
        "year": STATS_YEAR,
        "adm_cd": adm_cd,
        "low_search": "1",
    }

    try:
        resp = make_request(url, params)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error("%s — %s(%s) 조회 실패: %s", api_name, adm_nm, adm_cd, e)
        return None
    if resp is None:
        logger.error("%s — %s(%s) 조회 실패", api_name, adm_nm, adm_cd)
        return None

    data = resp.json()
    result = data.get("result", data)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    count = len(result) if isinstance(result, list) else 1
    logger.info("%s — %s(%s): %d건 저장", api_name, adm_nm, adm_cd, count)
    return result


def fetch_grid_population(token_mgr: SGISTokenManager) -> dict | None:
    """격자별 인구 데이터를 수집한다 (500m 격자, lv=2)."""
    grid_dir = ensure_dir(OUT_DIR / "searchpopulation")
    out_path = grid_dir / "cheonan_grid.json"

    if is_already_fetched(out_path):
        logger.info("격자별 인구 이미 수집 완료")
        return None

    params = {
        "accessToken": token_mgr.get_token(),
        "year": STATS_YEAR,
        "lv": "2",
        "x_min": str(CHEONAN_UTMK["x_min"]),
        "y_min": str(CHEONAN_UTMK["y_min"]),
        "x_max": str(CHEONAN_UTMK["x_max"]),
        "y_max": str(CHEONAN_UTMK["y_max"]),
    }

    try:
        resp = make_request(GRID_POPULATION_URL, params, timeout=60)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.warning("격자별 인구 조회 실패: %s", e)
        resp = None
    if resp is None:
        logger.warning("격자별 인구 조회 실패 — 권한 미부여 가능성")
        # Fallback: 읍면동 단위로 이미 수집했으므로 스킵
        fallback_msg = {"error": "격자별 인구 API 접근 실패 (권한 미부여 가능)", "fallback": "읍면동 단위 인구통계 사용"}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fallback_msg, f, ensure_ascii=False, indent=2)
        return None

    data = resp.json()

    if data.get("errCd") and data["errCd"] != 0:
        logger.warning("격자별 인구 API 오류: %s — 읍면동 단위로 대체", data.get("errMsg", ""))
        fallback_msg = {"error": data.get("errMsg", "Unknown"), "errCd": data.get("errCd"), "fallback": "읍면동 단위 인구통계 사용"}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fallback_msg, f, ensure_ascii=False, indent=2)
        return None

    result = data.get("result", data)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    count = len(result) if isinstance(result, list) else 1
    logger.info("격자별 인구: %d건 저장", count)
    return result


def fetch_boundary(
    token_mgr: SGISTokenManager, adm_cd: str
) -> dict | None:
    """행정구역 경계 GeoJSON 을 수집한다."""
    bnd_dir = ensure_dir(OUT_DIR / "boundary")
    out_path = bnd_dir / f"{adm_cd}.geojson"

    if is_already_fetched(out_path):
        logger.info("경계 %s 이미 수집 완료", adm_cd)
        return None

    params = {
        "accessToken": token_mgr.get_token(),
        "year": STATS_YEAR,
        "adm_cd": adm_cd,
        "low_search": "1",
    }

    try:
        resp = make_request(BOUNDARY_URL, params, timeout=60)
    except (FatalAPIError, TransientAPIError, Exception) as e:
        logger.error("경계 GeoJSON 조회 실패: %s — %s", adm_cd, e)
        return None
    if resp is None:
        logger.error("경계 GeoJSON 조회 실패: %s", adm_cd)
        return None

    # GeoJSON 은 JSON 형태로 반환
    try:
        data = resp.json()
    except Exception:
        # GeoJSON 텍스트 그대로 저장
        data = resp.text
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(data)
        logger.info("경계 %s 저장 완료 (raw text)", adm_cd)
        return data

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("경계 %s 저장 완료", adm_cd)
    return data


def main() -> None:
    """SGIS 통계지리정보 데이터 수집 메인."""
    load_env()
    ensure_dir(OUT_DIR)

    token_mgr = SGISTokenManager()

    # ── 1. 천안 하위 읍면동 코드 탐색 ─────────────────────────
    logger.info("=== 천안 하위 읍면동 코드 탐색 ===")
    all_sub_areas: list[dict] = []

    for gu_cd in [SGIS_CHEONAN_DONGNAM, SGIS_CHEONAN_SEOBUK]:
        time.sleep(SLEEP_BETWEEN_CALLS)
        subs = discover_sub_areas(token_mgr, gu_cd)
        all_sub_areas.extend(subs)

    if not all_sub_areas:
        logger.error("천안 하위 읍면동을 찾을 수 없습니다.")
        return

    # adm_cd 키 추출 (API 응답 구조에 따라 조정)
    sub_codes = []
    for area in all_sub_areas:
        code = area.get("adm_cd") or area.get("code") or area.get("adm_cd_no")
        name = area.get("adm_nm") or area.get("name") or area.get("adm_nm_ko") or str(code)
        if code:
            sub_codes.append((str(code), name))

    logger.info("천안 읍면동 %d개: %s", len(sub_codes), ", ".join(n for _, n in sub_codes[:5]) + "...")

    # ── 2. 4종 통계 API 수집 ──────────────────────────────────
    for api_name in STATS_APIS:
        logger.info("=== %s 수집 시작 ===", api_name)

        # 구 단위도 수집
        for gu_cd in [SGIS_CHEONAN_DONGNAM, SGIS_CHEONAN_SEOBUK]:
            fetch_stats(token_mgr, api_name, gu_cd, gu_cd)
            time.sleep(SLEEP_BETWEEN_CALLS)

        # 읍면동 단위
        for adm_cd, adm_nm in tqdm(sub_codes, desc=api_name):
            fetch_stats(token_mgr, api_name, adm_cd, adm_nm)
            time.sleep(SLEEP_BETWEEN_CALLS)

    # ── 3. 격자별 인구 ────────────────────────────────────────
    logger.info("=== 격자별 인구 수집 ===")
    fetch_grid_population(token_mgr)
    time.sleep(SLEEP_BETWEEN_CALLS)

    # ── 4. 행정구역 경계 GeoJSON ──────────────────────────────
    logger.info("=== 행정구역 경계 GeoJSON 수집 ===")
    for gu_cd in [SGIS_CHEONAN_DONGNAM, SGIS_CHEONAN_SEOBUK]:
        fetch_boundary(token_mgr, gu_cd)
        time.sleep(SLEEP_BETWEEN_CALLS)

    logger.info("=== SGIS 데이터 수집 완료 ===")


if __name__ == "__main__":
    main()
