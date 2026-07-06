---
description: "Show project dashboard — data pipeline progress, experiments, model scores, and current strategy at a glance."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Glob
---

# /status — Project Dashboard (천안 자취방 안전지도)

프로젝트 전체 진행 현황을 한눈에 보여준다.

## Display

### 1. Project Phase

!`cat logs/orchestrator_state.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Phase: {d[\"current_phase\"]} | Best: {d[\"best_cv\"]} ({d[\"best_experiment\"]}) | Stall: {d[\"stall_counter\"]}/5 | Cycles: {d[\"total_cycles\"]}')" 2>/dev/null || echo "No orchestrator state yet"`

### 2. Data Pipeline Status

!`cat logs/pipeline_status.json 2>/dev/null || echo "No pipeline status yet"`

```
DATA COLLECTION
────────────────────────────────────────
실거래가 (8 APIs):  ✓/△/✗  XX,XXX records
건축물대장:         ✓/△/✗  XX,XXX records
공시가격:           ✓/△/✗  XX,XXX records
CCTV:              ✓/△/✗  X,XXX records
상가정보:           ✓/△/✗  XX,XXX records
병원정보:           ✓/△/✗  X,XXX records
대기질:             ✓/△/✗  XXX records
SGIS:              ✓/△/✗  XX records
침수흔적:           ✓/△/✗  (WMS)
```

### 3. Experiment Summary

!`cat EXPERIMENT_LOG.csv 2>/dev/null || echo "No experiments yet"`

```
EXPERIMENTS                          Model Type       CV Score   Status
───────────────────────────────────────────────────────────────────────
exp_001_baseline_lgbm                gangton_clf      0.XXXX     COMPLETED
exp_002_pu_learning                  gangton_clf      0.XXXX     INTEGRATE
exp_003_safety_score                 safety_score     —          COMPLETED
```

### 4. 대회 타임라인

```
TIMELINE
────────────────────────────────────────
[████████░░░░░░░░░░░░] 40%
6/8 접수시작 ← NOW → 8/31 마감 → 9월 예선 → 10월 본선

남은 일수: XX일
현재 Phase: [phase]
다음 마일스톤: [milestone]
```

### 5. 평가축 커버리지

```
EVALUATION AXIS COVERAGE
────────────────────────────────────────
주제적합성:     ████████░░  80%  (천안 데이터 기반)
창의성:         ██████░░░░  60%  (신호등 지도 + SHAP)
기획력:         ████░░░░░░  40%  (기획서 미작성)
데이터적정성:   ████████░░  80%  (공공 API 기반)
활용가능성:     ██████░░░░  60%  (시뮬레이터 미완)
```

### 6. Quick Recommendations

현재 상태 기반 제안:
- 다음 작업 (1-2문장)
- 경고 (시간 부족, 미완성 기능 등)
- 남은 대회일 기준 우선순위

End with: "다음 행동: `/plan` (계획) | `/dev NAME` (구현) | `/eda` (데이터 분석) | `/present` (기획서)"
