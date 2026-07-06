---
description: "Rank model components and recommend which to include in final service and presentation. Shows composite score considering performance, evaluation axis coverage, and demo impact."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# /rank — Component Selector (천안 자취방 안전지도)

완료된 실험/컴포넌트를 순위 매기고 최종 서비스·발표에 포함할 항목을 추천한다.

## Process

### 1. Gather Components

EVALUATED 이상 상태의 모든 실험을 수집:

```bash
for dir in experiments/exp_*; do
  if [ -f "$dir/train_log.json" ]; then
    echo "=== $dir ==="
    python3 -c "import json; d=json.load(open('$dir/train_log.json')); print(d.get('model_type','?'), d.get('cv_mean','?'))" 2>/dev/null
  fi
done
```

### 2. Rank by Composite Score

```
composite = 0.3 × model_performance
          + 0.3 × evaluation_axis_coverage
          + 0.2 × demo_impact
          + 0.2 × implementation_readiness
```

### 3. Evaluation Axis Coverage

5대 평가축 중 몇 개에 기여하는가:
- 주제적합성: 천안 고유 문제 해결
- 창의성: 기존 서비스와 차별점
- 기획력: 논리적 흐름
- 데이터적정성: 공공 데이터 활용
- 활용가능성: 실제 정책/서비스로 가능

### 4. Selection Rules

**필수 포함 (MUST)**:
- 깡통전세 분류기 + SHAP (핵심 차별성)
- 신호등 지도 (시각적 임팩트)

**권장 포함 (SHOULD)**:
- 위험도 시뮬레이터
- 행정 대시보드 (B2G 활용가능성)

**선택 포함 (NICE_TO_HAVE)**:
- RAG 정책 챗봇
- 이상탐지 결과
- 추천 시스템

### 5. Update SUBMISSION_CANDIDATES.md

| 순위 | 컴포넌트 | 성능 | 평가축 | 시연 임팩트 | 완성도 | 우선순위 |
|------|----------|------|--------|-------------|--------|----------|
| 1 | 깡통전세 분류기+SHAP | F1=0.XX | 3/5 | HIGH | ✓ | MUST |
| 2 | 신호등 지도 | - | 2/5 | HIGH | ✓ | MUST |
| ... | | | | | | |

### 6. Report

```
========================================
COMPONENT RANKING (YYYY-MM-DD)
========================================
MUST:
  1. 깡통전세 분류기+SHAP    F1: 0.XX  [핵심 차별성]
  2. 신호등 지도 (H3)         —         [시각 임팩트]

SHOULD:
  3. 위험도 시뮬레이터        —         [인터랙티브]
  4. 행정 대시보드            —         [B2G 활용]

NICE_TO_HAVE:
  5. RAG 정책 챗봇            —         [창의성 가점]
  6. 이상탐지 (IF)            —         [빌라왕 탐지]

PT 10분 구성에 MUST + SHOULD 포함 권장
========================================
```
