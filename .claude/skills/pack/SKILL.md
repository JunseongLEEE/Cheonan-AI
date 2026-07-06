---
description: "Generate proposal document and presentation materials for the competition. Maps all components to evaluation criteria."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
---

# /present — 기획서·발표자료 생성 (천안 자취방 안전지도)

대회 제출용 기획서와 본선 PT 발표자료를 생성한다.

## Arguments
- `$ARGUMENTS` — optional: "proposal" (기획서만), "slides" (발표만), or both (default)

## Step 1: 현황 파악

```
Read: EXPERIMENT_LOG.csv — 완료된 실험 목록
Read: logs/experiment_digest.md — 실험 결과 요약
Read: SUBMISSION_CANDIDATES.md — 선정된 컴포넌트
Read: Competition_desription.md — 대회 정보
Read: RULES.md — 대회 규정
```

## Step 2: 기획서 작성

`docs/proposal_v1.md` 작성. 아래 목차를 따른다:

### 목차
1. **문제정의** — 천안 청년 주거위기 데이터
   - 청년 19.7만명 중 86% 무주택
   - 3년간 전세사기 288세대 145억원
   - 동남구 구도심 노후 다가구 밀집
   
2. **비전·차별점** — HUG 안심전세 vs 우리 서비스
3. **페르소나** — 단국대 새내기 / 사회초년생 / 대학원생
4. **시나리오** — B2C + B2G 사용 시나리오
5. **기술 아키텍처** — 전체 시스템 구성도
6. **AI 모델 파이프라인** — 각 모델 설명 + SHAP
7. **데이터 ETL** — 출처·컬럼·시점 표 (규정 준수)
8. **UI/UX** — 화면 설계 + 스크린샷
9. **6~8월 WBS** — 마일스톤 + 진행률
10. **평가기준 매핑** — 5대 평가축별 대응
11. **기대효과·시정반영** — 정량적 임팩트
12. **위험·대응** — 데이터 한계, 윤리

### 평가축 매핑 (CRITICAL)
모든 섹션에서 어떤 평가축에 기여하는지 명시:
- 🎯 주제적합성
- 💡 창의성
- 📋 기획력
- 📊 데이터적정성
- 🔧 활용가능성

## Step 3: 발표 구성안

`docs/presentation_outline.md` 작성.

```
[0:00~1:30] 문제 제기 — 천안 청년 데이터 임팩트
[1:30~3:00] 솔루션 개요 — 데모 화면
[3:00~5:00] AI 모델 — SHAP 설명, 안전점수
[5:00~6:30] 시연 — 매물 검색 → 진단 → 추천
[6:30~8:00] B2G — 행정 대시보드, 정책 연계
[8:00~9:00] 기술·데이터 — 아키텍처, API 출처
[9:00~10:00] 정리 — 임팩트, Q&A
```

## Step 4: 시연 시나리오

`docs/demo_scenario.md` 작성:
- 시나리오 1: 단국대 새내기가 안서동 원룸 검색
- 시나리오 2: 사회초년생이 두정동 오피스텔 전세 계약 전 진단
- 시나리오 3: 천안시 공무원이 위험 핫스팟 점검

## Step 5: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRESENTATION MATERIALS GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기획서:     docs/proposal_v1.md ✓
발표구성안: docs/presentation_outline.md ✓
시연시나리오: docs/demo_scenario.md ✓

다음: 기획서 검토 후 수정 → 최종본 확정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
