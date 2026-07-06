#!/usr/bin/env python3
"""Generate proposal document and presentation outline.
천안 청년 자취방 안전지도 — 대회 제출용 기획서 생성.

이 대회는 코드 제출이 아닌 서면 기획서 + 오프라인 PT 형식.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"


def gather_experiment_results():
    """Gather all completed experiment results."""
    results = []
    for exp_dir in sorted(EXPERIMENTS_DIR.glob("exp_*")):
        train_log = exp_dir / "train_log.json"
        eval_json = exp_dir / "evaluation.json"
        if train_log.exists():
            with open(train_log) as f:
                data = json.load(f)
            if eval_json.exists():
                with open(eval_json) as f:
                    data["evaluation"] = json.load(f)
            results.append(data)
    return results


def generate_proposal():
    """Generate proposal document skeleton."""
    DOCS_DIR.mkdir(exist_ok=True)

    results = gather_experiment_results()
    today = datetime.now().strftime("%Y-%m-%d")

    proposal = f"""# 천안 청년 자취방 안전지도 — 기획서

> 2026 천안시 AI·데이터 기반 정책 아이디어 경진대회
> 과제: 지역균형발전 — 구도심 청년 주거안전 격차 해소
> 작성일: {today}

---

## 1. 문제정의

### 천안 청년 주거위기
- 청년(18~39세) 19만7,572명 — 전체 인구의 29.9%
- 청년 주택소유율 **13.9%** → 약 86%가 무주택 임차 중심
- 세대주 청년 중 65.4%가 1인세대주
- 3년간 전세사기 피해: **288세대, 145억원**

### 구도심 vs 신도심 격차
- 동남구(안서동 대학가): 노후 다가구·빌라 밀집, 청년 자취 위험 핵심 지대
- 서북구(불당·백석): 신도심, 상대적 안전

### 기존 서비스의 한계
- HUG 안심전세앱: "내가 입력한 한 채" 진단만 가능, 도시 전체 스캔 불가
- 등기부: 건당 유료, 벌크 API 없음
- 직방/다방: 중개 부가서비스, 중립적 위험평가 아님

---

## 2. 비전·차별점

**도시 전체를 선제 스캔하는 AI 기반 종합 안전지도**

| 기존 | 우리 서비스 |
|------|------------|
| 1채 진단 (HUG) | 도시 전체 H3 격자 선제 스캔 |
| 전세사기만 | 전세사기 + 침수 + 치안 + 교통 + 편의 종합 |
| 수치만 제공 | SHAP으로 "왜 위험한가" 설명 |
| B2C만 | B2C(청년) + B2G(행정) 동시 |

---

## 3. 페르소나

1. **김대학** (21, 단국대 새내기) — 안서동 원룸 첫 자취
2. **이초년** (27, 사회초년생) — 두정동 오피스텔 전세 계약
3. **박연구** (32, 대학원생) — 가족과 서북구 이주 고려

---

## 4. AI 모델 파이프라인

"""

    # 실험 결과 추가
    if results:
        proposal += "### 모델 실험 결과\n\n"
        proposal += "| 실험 | 모델 유형 | CV Score | Metric | 비고 |\n"
        proposal += "|------|----------|----------|--------|------|\n"
        for r in results:
            proposal += (
                f"| {r.get('experiment_id', '')} | {r.get('model_type', '')} | "
                f"{r.get('cv_mean', 0):.4f} | {r.get('metric_name', '')} | |\n"
            )
        proposal += "\n"

    proposal += """
## 5. 데이터 ETL

### 공공 API 데이터 출처 (전부 합법 수집)
| # | 데이터 | 출처 | 형식 |
|---|--------|------|------|
| 1 | 아파트 매매 실거래가 | data.go.kr/15126469 | XML |
| 2 | 아파트 전월세 실거래가 | data.go.kr/15126474 | XML |
| 3 | 오피스텔 매매/전월세 | data.go.kr/15126464, 15126475 | XML |
| 4 | 연립다세대 매매/전월세 | data.go.kr/15126467, 15126473 | XML |
| 5 | 단독다가구 매매/전월세 | data.go.kr/15126465, 15126472 | XML |
| 6 | 건축물대장 | data.go.kr/15134735 | JSON |
| 7 | 공동주택 공시가격 | data.go.kr/15124003 | WFS |
| 8 | CCTV | data.go.kr/15013094 | CSV |
| 9 | 상가정보 | data.go.kr/15012005 | JSON |
| 10 | 병원정보 | data.go.kr/15001698 | JSON |
| 11 | 대기오염 | data.go.kr/15073861 | JSON |
| 12 | SGIS 인구/가구/주택 | sgisapi.kostat.go.kr | JSON |

---

## 6. 평가기준 매핑

| 평가축 | 점수 | 대응 |
|--------|------|------|
| 주제적합성 (20) | 천안 고유 데이터로 출발, 안심계약 서비스의 디지털 확장 |
| 창의성 (20) | HUG 1채→도시 전체 스캔, 종합 안전성 통합 |
| 기획력 (20) | 체계적 WBS, 실현 가능한 아키텍처 |
| 데이터적정성 (20) | 전 데이터 출처 URL·시점 명시, 공공 API만 사용 |
| 활용가능성 (20) | SHAP 설명, 시뮬레이터, B2G 대시보드 |

---

## 7. 기대효과

- 청년 1명의 보증금 방어 = 수천만원 경제적 가치
- 30대 주거이탈 억제 (35~39세 43.2%가 주택 사유 전출) → 인구 유지
- 행정 위험 핫스팟 사전 점검 → 예산 효율 배분

---

## 8. 위험·대응

| 위험 | 대응 |
|------|------|
| 등기부 벌크 API 부재 | 사용자 업로드 OCR 방식 |
| 단독/다가구 지번 일부만 제공 | 행정동 단위 집계로 폴백 |
| 라벨 부족 (사기 확정 사례 극소수) | PU러닝 + 휴리스틱 약지도 |
| 개인정보/명예훼손 | "참고용" 면책, 실명 미노출 |
"""

    proposal_path = DOCS_DIR / "proposal_v1.md"
    proposal_path.write_text(proposal)
    print(f"기획서 생성: {proposal_path}")

    return proposal_path


def generate_presentation_outline():
    """Generate PT outline."""
    DOCS_DIR.mkdir(exist_ok=True)

    outline = """# 발표 구성안 — 천안 청년 자취방 안전지도 (10분)

## [0:00~1:30] 문제 제기
- 천안 청년 데이터로 임팩트 강조
- "288세대, 145억원" → 슬라이드 1장으로 충격
- 구도심 vs 신도심 격차 시각화

## [1:30~3:00] 솔루션 개요
- 신호등 지도 스크린샷 (빨강/노랑/초록)
- "한눈에 보는 안전지도" 컨셉
- HUG 안심전세 vs 우리 서비스 비교표

## [3:00~5:00] AI 모델
- 깡통전세 분류기 아키텍처
- SHAP 막대그래프: "이 매물이 위험한 이유"
- 8축 안전점수 레이더차트

## [5:00~6:30] 시연
- 시나리오: 단국대 새내기가 안서동 원룸 검색
- 매물 선택 → 위험도 진단 → 대체 추천
- 시뮬레이터: "보증금 X만원이면?"

## [6:30~8:00] B2G (행정 활용)
- 위험 핫스팟 히트맵
- 동별 노후 다가구 밀집지 대시보드
- 청년정책 효과 매핑 (행복주택·월세지원)

## [8:00~9:00] 기술·데이터
- 시스템 아키텍처 1장
- 공공 API 데이터 출처 표
- 확장 가능성 (타 지자체)

## [9:00~10:00] 정리
- 핵심 메시지: "보증금 1건 방어 = 수천만원"
- Q&A 유도 질문 준비

---

## 시연 백업
- 실시간 데모 불가 시 녹화 영상 준비
- 오프라인 환경 대비 로컬 데모 세팅
"""

    outline_path = DOCS_DIR / "presentation_outline.md"
    outline_path.write_text(outline)
    print(f"발표 구성안 생성: {outline_path}")

    return outline_path


def main():
    print("Generating presentation materials...")
    print(f"{'='*50}")

    proposal = generate_proposal()
    outline = generate_presentation_outline()

    print(f"\n{'='*50}")
    print(f"기획서:     {proposal}")
    print(f"발표구성안: {outline}")
    print(f"\n다음: 기획서 검토 후 수정 → 최종본 확정")


if __name__ == "__main__":
    main()
