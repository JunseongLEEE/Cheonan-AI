"""
_common.py — 천안 청년 자취방 안전지도 데이터 수집 공통 모듈

모든 수집 스크립트가 공유하는 상수, 유틸리티, API 헬퍼를 제공한다.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import xmltodict
from dotenv import load_dotenv
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# 경로 상수
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent          # collector/
PROJECT_ROOT = _THIS_DIR.parent                      # 프로젝트 루트
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"

# ---------------------------------------------------------------------------
# 법정동코드 (5자리)
# ---------------------------------------------------------------------------
CHEONAN_DONGNAM = "44131"   # 천안시 동남구
CHEONAN_SEOBUK = "44133"    # 천안시 서북구
LAWD_CDS = [CHEONAN_DONGNAM, CHEONAN_SEOBUK]

# ---------------------------------------------------------------------------
# 실거래가 수집 기간
# ---------------------------------------------------------------------------
TRADE_START_YEAR = 2006
TRADE_START_MONTH = 1
RENT_START_YEAR = 2011
RENT_START_MONTH = 1

# ---------------------------------------------------------------------------
# API 호출 간격 (초)
# ---------------------------------------------------------------------------
SLEEP_BETWEEN_CALLS = 0.1

# ---------------------------------------------------------------------------
# 환경변수 키 이름
# ---------------------------------------------------------------------------
DATA_GO_KR_KEY_ENV = "DATA_GO_KR_KEY"
SGIS_CONSUMER_KEY_ENV = "SGIS_CONSUMER_KEY"
SGIS_SECRET_KEY_ENV = "SGIS_SECRET_KEY"

# ---------------------------------------------------------------------------
# 공통 HTTP 헤더 (공공데이터포털 WAF 우회)
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


# ===================================================================
# 에러 클래스
# ===================================================================

class APIError(Exception):
    """API 응답에서 발생하는 일반 에러."""
    pass


class FatalAPIError(APIError):
    """재시도해도 해결되지 않는 에러 (인증 실패, 권한 거부 등)."""
    pass


class TransientAPIError(APIError):
    """재시도로 해결 가능한 일시적 에러."""
    pass


# 재시도 불필요한 치명적 에러 메시지 목록
_FATAL_ERROR_MESSAGES = [
    "SERVICE KEY IS NOT REGISTERED",
    "SERVICE ACCESS DENIED",
    "DEADLINE_HAS_EXPIRED",
]


# ===================================================================
# 환경 설정
# ===================================================================

def load_env() -> None:
    """프로젝트 루트 또는 collector/ 의 .env 파일을 로드한다."""
    # collector/.env 우선, 없으면 프로젝트 루트/.env
    dotenv_path = _THIS_DIR / ".env"
    if not dotenv_path.exists():
        dotenv_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)


def get_api_key(name: str = "DATA_GO_KR_KEY") -> str:
    """환경변수에서 API 키를 가져온다.

    Parameters
    ----------
    name : str
        환경변수 이름 (예: DATA_GO_KR_KEY)

    Returns
    -------
    str
        API 키 값

    Raises
    ------
    EnvironmentError
        환경변수가 설정되지 않았거나 플레이스홀더 값인 경우
    """
    load_env()
    value = os.environ.get(name)
    if not value or value.strip() == "" or value.strip() == "your_key_here":
        raise EnvironmentError(
            f"환경변수 '{name}'이(가) 설정되지 않았습니다. "
            f"collector/.env 파일을 확인하세요. "
            f"(참고: collector/.env.example)"
        )
    return value.strip()


# ===================================================================
# 로깅
# ===================================================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """콘솔 + 파일 로거를 생성한다.

    로그 파일은 ``../logs/{name}.log`` 에 저장된다.

    Parameters
    ----------
    name : str
        로거 이름 (파일명으로도 사용)
    level : int
        로그 레벨 (기본 INFO)

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정된 경우 중복 생성 방지
    if logger.handlers:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 파일 핸들러
    ensure_dir(LOGS_DIR)
    fh = logging.FileHandler(LOGS_DIR / f"{name}.log", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ===================================================================
# 파일시스템 유틸
# ===================================================================

def ensure_dir(path) -> Path:
    """디렉토리가 없으면 생성하고 Path 객체를 반환한다."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_already_fetched(filepath) -> bool:
    """파일이 존재하고 비어있지 않으면 True (이어받기 로직용)."""
    p = Path(filepath)
    return p.exists() and p.stat().st_size > 0


# ===================================================================
# 기간 생성
# ===================================================================

def generate_months(
    start_year: int,
    start_month: int = 1,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
) -> List[str]:
    """start부터 end(기본: 현재 월)까지 ``YYYYMM`` 문자열 리스트를 생성한다.

    Parameters
    ----------
    start_year, start_month : int
        시작 연월
    end_year, end_month : int, optional
        종료 연월. None이면 현재 연월 사용

    Returns
    -------
    list[str]
        예: ["200601", "200602", ..., "202606"]
    """
    now = datetime.now()
    if end_year is None:
        end_year = now.year
    if end_month is None:
        end_month = now.month

    months: List[str] = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


# ===================================================================
# HTTP / API 호출
# ===================================================================

# tenacity 로깅용 내부 로거
_http_logger = logging.getLogger("_common.http")


def _check_fatal(text: str) -> None:
    """응답 본문에 치명적 에러가 포함되어 있으면 FatalAPIError를 발생시킨다."""
    for msg in _FATAL_ERROR_MESSAGES:
        if msg in text:
            raise FatalAPIError(f"치명적 API 에러: {msg}")


@retry(
    retry=retry_if_exception_type((TransientAPIError, requests.RequestException)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    before_sleep=before_sleep_log(_http_logger, logging.WARNING),
    reraise=True,
)
def make_request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 5,
    timeout: int = 30,
) -> requests.Response:
    """HTTP GET 요청을 보내고, 재시도 로직이 적용된 응답을 반환한다.

    재시도 정책
    -----------
    - 네트워크 에러, HTTP 5xx → 지수 백오프 재시도 (최대 5회, 2~30초)
    - SERVICE KEY IS NOT REGISTERED, SERVICE ACCESS DENIED → 즉시 FatalAPIError
    - SGIS errCd != 0 → TransientAPIError (재시도) 또는 FatalAPIError (인증 에러)

    Parameters
    ----------
    url : str
        요청 URL
    params : dict, optional
        쿼리 파라미터
    max_retries : int
        인터페이스 호환용 (tenacity 데코레이터가 실제 제어)
    timeout : int
        요청 타임아웃 (초)

    Returns
    -------
    requests.Response

    Raises
    ------
    FatalAPIError
        인증 실패 등 재시도 불가 에러
    TransientAPIError
        일시적 에러 (재시도 소진 시)
    requests.RequestException
        네트워크 에러 (재시도 소진 시)
    """
    resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)

    # HTTP 5xx → 재시도
    if resp.status_code >= 500:
        raise TransientAPIError(f"HTTP {resp.status_code}: {url}")

    # HTTP 4xx → 본문 확인 후 치명적/일반 에러 판별
    if resp.status_code >= 400:
        _check_fatal(resp.text)
        raise FatalAPIError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    # 본문 내 치명적 에러 메시지 검사
    _check_fatal(resp.text)

    # SGIS JSON 응답 에러 코드 검사
    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type or "sgisapi.kostat.go.kr" in url:
        try:
            data = resp.json()
            err_cd = data.get("errCd")
            err_msg = data.get("errMsg", "")
            if err_cd is not None and str(err_cd) != "0":
                # 인증 관련 에러는 치명적 (-401: 인증 실패, -402: 토큰 만료)
                if str(err_cd) in ("-401", "-402", "-403"):
                    raise FatalAPIError(
                        f"SGIS 인증 에러 (errCd={err_cd}): {err_msg}"
                    )
                # -100: 검색결과 없음 — 데이터 없음이므로 정상 응답 취급
                if str(err_cd) == "-100":
                    return resp
                raise TransientAPIError(
                    f"SGIS 에러 (errCd={err_cd}): {err_msg}"
                )
        except (ValueError, AttributeError):
            # JSON 파싱 실패는 무시 (XML 응답일 수 있음)
            pass

    return resp


# ===================================================================
# XML 파싱
# ===================================================================

def parse_xml_response(text: str) -> Dict[str, Any]:
    """XML 응답을 파싱하고 에러 여부를 검증한다.

    data.go.kr 공공데이터포털 API의 두 가지 에러 형식을 처리한다:
    1. ``OpenAPI_ServiceResponse/cmmMsgHeader`` — 인증/권한 에러
    2. ``response/header/resultCode`` — 비즈니스 에러

    Parameters
    ----------
    text : str
        XML 문자열

    Returns
    -------
    dict
        파싱된 응답 딕셔너리

    Raises
    ------
    FatalAPIError
        인증/권한 에러
    TransientAPIError
        일시적 에러
    APIError
        파싱 실패 또는 기타 에러
    """
    try:
        parsed = xmltodict.parse(text)
    except Exception as e:
        raise APIError(f"XML 파싱 실패: {e}\n응답 앞부분: {text[:500]}")

    # 형식 1: OpenAPI_ServiceResponse (인증/서비스 에러)
    svc_resp = parsed.get("OpenAPI_ServiceResponse")
    if svc_resp:
        header = svc_resp.get("cmmMsgHeader", {})
        auth_msg = header.get("returnAuthMsg", "")
        reason = header.get("returnReasonCode", "")
        _check_fatal(auth_msg)
        raise APIError(f"API 에러: {auth_msg} (code={reason})")

    # 형식 2: response/header/resultCode (정상 응답 구조)
    response = parsed.get("response", parsed)
    header = response.get("header", {})
    result_code = header.get("resultCode")

    if result_code and str(result_code) != "00":
        result_msg = header.get("resultMsg", "알 수 없는 에러")
        _check_fatal(result_msg)
        # 대부분의 비정상 코드는 치명적 (잘못된 파라미터 등)
        if str(result_code) in (
            "01", "02", "10", "11", "12", "20", "21", "22", "30", "31",
        ):
            raise FatalAPIError(
                f"API 에러 (code={result_code}): {result_msg}"
            )
        raise TransientAPIError(
            f"API 일시 에러 (code={result_code}): {result_msg}"
        )

    return parsed


# ===================================================================
# SGIS 토큰 관리
# ===================================================================

class SGISTokenManager:
    """SGIS(통계지리정보서비스) 액세스 토큰을 관리한다.

    - 최초 호출 시 토큰을 발급받는다.
    - ``../logs/sgis_token.json`` 에 캐싱하여 불필요한 재발급을 방지한다.
    - 토큰 유효기간(4시간) 만료 5분 전에 자동 갱신한다.

    Usage
    -----
    >>> mgr = SGISTokenManager()
    >>> token = mgr.get_token()
    """

    TOKEN_URL = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
    TOKEN_LIFETIME_SECONDS = 4 * 60 * 60       # 4시간
    RENEWAL_BUFFER_SECONDS = 300                # 만료 5분 전에 갱신

    def __init__(self, cache_path: Optional[Path] = None):
        self._cache_path = (
            Path(cache_path) if cache_path else LOGS_DIR / "sgis_token.json"
        )
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0  # unix timestamp
        self._logger = logging.getLogger("sgis_token")
        self._load_cached_token()

    # ---- 캐시 관리 ----

    def _load_cached_token(self) -> None:
        """캐시 파일에서 토큰을 로드한다."""
        if not self._cache_path.exists():
            return
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            token = data.get("accessToken")
            expires_at = data.get("expiresAt", 0)
            if token and time.time() < expires_at - self.RENEWAL_BUFFER_SECONDS:
                self._access_token = token
                self._expires_at = expires_at
                self._logger.info(
                    "캐시된 SGIS 토큰 로드 완료 (만료: %s)",
                    datetime.fromtimestamp(expires_at).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self._logger.warning("SGIS 토큰 캐시 로드 실패: %s", e)

    def _save_cached_token(self) -> None:
        """토큰을 캐시 파일에 저장한다."""
        ensure_dir(self._cache_path.parent)
        payload = {
            "accessToken": self._access_token,
            "expiresAt": self._expires_at,
            "createdAt": datetime.now().isoformat(),
        }
        with open(self._cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # ---- 토큰 유효성 ----

    def _is_token_valid(self) -> bool:
        """토큰이 유효한지 확인한다 (만료 5분 전이면 무효 처리)."""
        if not self._access_token:
            return False
        return time.time() < self._expires_at - self.RENEWAL_BUFFER_SECONDS

    # ---- 토큰 발급 ----

    def _acquire_token(self) -> str:
        """SGIS API에서 새 토큰을 발급받는다."""
        consumer_key = get_api_key(SGIS_CONSUMER_KEY_ENV)
        secret_key = get_api_key(SGIS_SECRET_KEY_ENV)

        self._logger.info("SGIS 토큰 발급 요청 중...")
        resp = requests.get(
            self.TOKEN_URL,
            params={
                "consumer_key": consumer_key,
                "consumer_secret": secret_key,
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        err_cd = data.get("errCd")
        if str(err_cd) != "0":
            err_msg = data.get("errMsg", "알 수 없는 에러")
            raise FatalAPIError(
                f"SGIS 토큰 발급 실패 (errCd={err_cd}): {err_msg}"
            )

        result = data.get("result", {})
        token = result.get("accessToken")
        if not token:
            raise FatalAPIError(
                f"SGIS 토큰 응답에 accessToken이 없습니다: {data}"
            )

        # 만료 시각: 응답의 accessTimeout(ms 단위 unix timestamp) 또는 기본 4시간
        timeout_ms = result.get("accessTimeout")
        if timeout_ms:
            self._expires_at = float(timeout_ms) / 1000.0
        else:
            self._expires_at = time.time() + self.TOKEN_LIFETIME_SECONDS

        self._access_token = token
        self._save_cached_token()
        self._logger.info(
            "SGIS 토큰 발급 완료 (만료: %s)",
            datetime.fromtimestamp(self._expires_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        return token

    # ---- 공개 인터페이스 ----

    def get_token(self) -> str:
        """유효한 SGIS 액세스 토큰을 반환한다. 필요 시 자동 갱신한다.

        Returns
        -------
        str
            SGIS 액세스 토큰
        """
        if self._is_token_valid():
            return self._access_token
        return self._acquire_token()

    def invalidate(self) -> None:
        """현재 토큰을 무효화하여 다음 호출 시 재발급하도록 한다."""
        self._access_token = None
        self._expires_at = 0.0
        if self._cache_path.exists():
            self._cache_path.unlink()
        self._logger.info("SGIS 토큰 무효화 완료")
