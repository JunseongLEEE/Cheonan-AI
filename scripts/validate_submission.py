#!/usr/bin/env python3
"""Validate data sources and compliance with competition rules.
천안 청년 자취방 안전지도 — 공공데이터 규정 준수 검증.

대회 규정:
- 정식 API 또는 공공포털 등 합법 수집 데이터만 허용
- 수집시점·범위·주요컬럼·출처 URL 기재 필수
- 민간 크롤링 금지 (직방/다방/네이버부동산)
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

# 허용된 공공 데이터 소스
ALLOWED_SOURCES = {
    "realestate": "국토교통부 실거래가 API (data.go.kr)",
    "building": "건축HUB 건축물대장 API (data.go.kr)",
    "housing_price": "국토교통부 공시가격 (data.go.kr)",
    "cctv": "전국CCTV표준데이터 (data.go.kr)",
    "commerce": "소상공인 상가정보 API (data.go.kr)",
    "medical": "건강보험심사평가원 병원정보 (data.go.kr)",
    "air_quality": "에어코리아 대기오염 (data.go.kr)",
    "sgis": "통계지리정보서비스 SGIS (sgisapi.kostat.go.kr)",
    "flood": "행정안전부 침수흔적도 (data.go.kr)",
    "taas": "TAAS 교통사고 GIS (taas.koroad.or.kr)",
}

# 금지된 소스 패턴
FORBIDDEN_PATTERNS = [
    "zigbang", "직방",
    "dabang", "다방",
    "naver.com/realestate", "네이버부동산",
    "부동산플래닛", "bdsplanet",
    "peterpan", "피터팬",
]


def check_data_directory():
    """Check data directory for compliance."""
    issues = []
    warnings = []

    if not DATA_DIR.exists():
        issues.append("data/ 디렉토리가 존재하지 않습니다")
        return issues, warnings

    # Check raw data
    raw_dir = DATA_DIR / "raw"
    if raw_dir.exists():
        categories = [d.name for d in raw_dir.iterdir() if d.is_dir()]
        print(f"수집된 데이터 카테고리: {categories}")

        for cat in categories:
            if cat not in ALLOWED_SOURCES and cat not in ("manual",):
                warnings.append(f"알 수 없는 데이터 카테고리: {cat} — 출처 확인 필요")
    else:
        warnings.append("data/raw/ 디렉토리 없음 — 아직 수집 전")

    return issues, warnings


def check_experiment_sources():
    """Check experiments for forbidden data sources."""
    issues = []

    for exp_dir in sorted(EXPERIMENTS_DIR.glob("exp_*")):
        # Check train.py for forbidden patterns
        train_py = exp_dir / "train.py"
        if train_py.exists():
            content = train_py.read_text()
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.lower() in content.lower():
                    issues.append(f"{exp_dir.name}/train.py: 금지된 데이터 소스 패턴 '{pattern}' 발견")

        # Check train_log.json data_sources
        train_log = exp_dir / "train_log.json"
        if train_log.exists():
            with open(train_log) as f:
                data = json.load(f)
            sources = data.get("data_sources", [])
            if not sources:
                issues.append(f"{exp_dir.name}: data_sources 미기재 — 출처 명기 필수")

    return issues


def check_privacy():
    """Check for potential privacy issues."""
    issues = []

    for exp_dir in sorted(EXPERIMENTS_DIR.glob("exp_*")):
        for py_file in exp_dir.glob("*.py"):
            content = py_file.read_text()
            # Check for personal info patterns
            if "임대인" in content and ("이름" in content or "성명" in content):
                if "익명" not in content and "마스킹" not in content:
                    issues.append(f"{exp_dir.name}/{py_file.name}: 임대인 개인정보 노출 위험 — 마스킹 필요")

    return issues


def validate():
    """Run all validation checks."""
    print("천안 자취방 안전지도 — 데이터 규정 준수 검증")
    print(f"{'='*60}")

    all_issues = []
    all_warnings = []

    # 1. Data directory check
    print("\n1. 데이터 디렉토리 검사")
    issues, warnings = check_data_directory()
    all_issues.extend(issues)
    all_warnings.extend(warnings)

    # 2. Experiment source check
    print("\n2. 실험 데이터 소스 검사")
    exp_issues = check_experiment_sources()
    all_issues.extend(exp_issues)

    # 3. Privacy check
    print("\n3. 개인정보 보호 검사")
    priv_issues = check_privacy()
    all_issues.extend(priv_issues)

    # Results
    print(f"\n{'='*60}")
    if all_issues:
        print("ISSUES (반드시 수정):")
        for issue in all_issues:
            print(f"  [X] {issue}")
    if all_warnings:
        print("WARNINGS (확인 필요):")
        for warning in all_warnings:
            print(f"  [!] {warning}")
    if not all_issues and not all_warnings:
        print("VALIDATION PASSED — 모든 규정 준수 확인")
    elif not all_issues:
        print("VALIDATION PASSED (경고 있음)")
    else:
        print("VALIDATION FAILED — 이슈 수정 필요")

    # Show allowed sources reference
    print(f"\n{'='*60}")
    print("허용된 공공 데이터 소스:")
    for key, desc in ALLOWED_SOURCES.items():
        print(f"  - {key}: {desc}")

    return len(all_issues) == 0


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
