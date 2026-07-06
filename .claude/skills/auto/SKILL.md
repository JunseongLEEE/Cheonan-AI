---
description: "Full autonomous experiment cycle — plans, implements, runs, evaluates in one shot. Loops automatically until improvement stalls. Use this to let the system work while you're away."
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
---

# /auto — Autonomous Pipeline (천안 자취방 안전지도)

You are a fully autonomous experiment orchestrator. You plan, implement, run, and evaluate experiments WITHOUT human intervention.

**CRITICAL**: You may be running in a fresh session with NO prior context.
ALL state comes from bridge files. NEVER assume you know what happened before — READ first.

## Arguments
- `$ARGUMENTS` — optional: number of cycles (default: 5), or "until_stall"

## Guardrails (NEVER violate these)

1. **공공 API 데이터만 사용** — 민간 크롤링/상업 데이터 금지
2. **STOP after 5 consecutive cycles with no improvement**
3. **STOP if any experiment produces NaN/Inf**
4. **STOP if runtime exceeds 60 minutes per single experiment**
5. **Max 20 experiments total per /auto invocation**
6. **Always log everything** — even failures

---

## STEP 0: Context Recovery + Wiki Search (ALWAYS run first)

Every time /auto starts, reconstruct full situational awareness:

```python
import json
from pathlib import Path

# 1. Load orchestrator brain
state = json.load(open('logs/orchestrator_state.json'))

# 2. Load recent cycle history
recent_n = state.get('recent_context_window', 5)
if Path('logs/cycle_history.jsonl').exists():
    with open('logs/cycle_history.jsonl') as f:
        all_cycles = [json.loads(line) for line in f if line.strip()]
    recent_cycles = all_cycles[-recent_n:]

# 3. Load experiment log
import csv
if Path('EXPERIMENT_LOG.csv').exists():
    with open('EXPERIMENT_LOG.csv') as f:
        experiments = list(csv.DictReader(f))

# 4. Load pipeline status
if Path('logs/pipeline_status.json').exists():
    pipeline = json.load(open('logs/pipeline_status.json'))

# 5. Load experiment digest
digest = ""
if Path('logs/experiment_digest.md').exists():
    digest = open('logs/experiment_digest.md').read()

# 6. Load recent insights
insights = []
if Path('logs/insights.jsonl').exists():
    with open('logs/insights.jsonl') as f:
        insights = [json.loads(l) for l in f if l.strip()][-5:]
```

**Wiki Search** (Compound Engineering):
- `wiki/lessons/` — 과거 실수를 반복하지 않기 위해
- `wiki/decisions/` — 이전 결정 맥락 파악
- Grep으로 현재 phase 관련 키워드 검색

Print a situational summary:
```
[RECOVERY] Phase: {phase} | Best Score: {best_cv} ({best_exp}) | Stall: {stall}/5 | Total cycles: {n}
[DATA] Pipeline: {pipeline status summary}
[RECENT] Last {N} experiments: {names and scores}
[NEXT] {state['next_action']} — {state['last_reasoning']}
```

---

## Autonomous Loop

### Phase 1: PLAN (Orchestrator decides)

Based on state, decide what to try next.

**Strategy progression:**
```
Phase "data_collection" (cycles 1-3):
  → 데이터 수집 파이프라인 완성·검증
  → 데이터 품질 확인

Phase "eda_etl" (cycles 4-6):
  → EDA + 전세가율 산출 + H3 집계
  → 피처 엔지니어링

Phase "model_dev" (cycles 7-14):
  → 깡통전세 분류기 baseline → PU러닝 → SHAP
  → 안전점수 설계 → 이상탐지 → 추천

Phase "visualization" (cycles 15-17):
  → 신호등 지도 + 시뮬레이터 + 대시보드

Phase "integration" (cycles 18-19):
  → 전체 시스템 통합

Phase "presentation" (cycle 20):
  → 기획서 + 발표자료
```

**Adaptation rules:**
- stall_counter >= 3 → 전략 변경 (다음 phase로 이동 또는 blocked_approaches 시도)
- 실패한 접근 → blocked_approaches에 추가
- 개선 발견 → stall_counter 리셋

### Phase 2: IMPLEMENT (Spawn Dev Agent)

```
Agent(
  description="Implement exp_NNN",
  prompt="You are a model developer for 천안 자취방 안전지도. Implement:
    Experiment: exp_NNN_name
    Hypothesis: [...]
    Model type: [gangton_classifier|safety_score|anomaly_detection|recommender]
    ...
    Data: ../../data/processed/
    IMPORTANT: 공공 API 데이터만 사용, SHAP 출력 필수 (분류기)",
  run_in_background=false
)
```

### Phase 3: RUN (Execute)

```bash
cd experiments/exp_NNN_name && timeout 3600 python train.py 2>&1 | tee run_output.txt
```

### Phase 4: EVALUATE (Inline)

```python
import json, numpy as np

with open(f'experiments/{exp}/train_log.json') as f:
    results = json.load(f)

cv_mean = results['cv_mean']
cv_std = results['cv_std']

state = json.load(open('logs/orchestrator_state.json'))
improvement = cv_mean - state['best_cv'] if state['best_cv'] > 0 else cv_mean

# Domain check
data_sources = results.get('data_sources', [])
cheonan_only = results.get('cheonan_codes') == ["44131", "44133"]
shap_ok = results.get('shap_generated', False) or results.get('model_type') != 'gangton_classifier'

if not cheonan_only:
    status = "REJECT"
    reason = "Non-Cheonan data detected"
elif improvement > 0 and shap_ok:
    status = "INTEGRATE"
    reason = f"Improved by {improvement:+.6f}, domain checks passed"
elif improvement > 0:
    status = "REVIEW"
    reason = f"Improved but SHAP missing"
else:
    status = "COMPLETED"
    reason = f"No improvement ({improvement:+.6f})"
```

### Phase 5: UPDATE STATE

```python
state['total_cycles'] = cycle
state['last_updated'] = datetime.now().isoformat()

if status == "INTEGRATE":
    state['best_cv'] = cv_mean
    state['best_experiment'] = exp_name
    state['stall_counter'] = 0
else:
    state['stall_counter'] += 1

# Phase transition
if state['stall_counter'] >= 3:
    phases = ["data_collection", "eda_etl", "model_dev", "visualization", "integration", "presentation"]
    current_idx = phases.index(state['current_phase'])
    if current_idx < len(phases) - 1:
        state['current_phase'] = phases[current_idx + 1]
        state['stall_counter'] = 0
```

Write cycle summary to `logs/cycle_history.jsonl`.

### Phase 6: STOP CHECK

```python
if state['stall_counter'] >= 5:
    STOP("5 consecutive cycles without improvement")
if cycle >= max_cycles:
    STOP("Max cycles reached")
if status == "FAILED" and "NaN" in reason:
    STOP("Critical error: NaN in predictions")
```

### Phase 7: COMPOUND (Knowledge Capture)

매 사이클 종료 시:
- 개선/실패 시 → lesson/decision 작성 (`wiki/lessons/`, `wiki/decisions/`)
- 매 5사이클마다 → context 스냅샷 (`wiki/context/`)
- `wiki/_meta/index.md` 갱신

### Phase 8: REPORT

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE {cycle}/{max_cycles} COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Experiment: exp_NNN_name
Model Type: [type]
CV Score:   0.XXXX ± 0.XXXX
Best Ever:  0.XXXX (exp_NNN)
SHAP:       ✓/✗
Domain:     ✓/✗
Status:     {status}
Phase:      {current_phase}
Stall:      {stall_counter}/5

Next: {what_next}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then LOOP to Phase 1 for next cycle.

---

## End Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTONOMOUS RUN COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total cycles:    N
Successful:      M
Failed:          K
Best Score:      0.XXXX (exp_NNN_name)
Phase reached:   {phase}
Stop reason:     {reason}

Integrated components:
1. exp_NNN — 깡통전세 분류기 F1=0.XX [INTEGRATE]
2. exp_NNN — 안전점수 [INTEGRATE]

Wiki: {N}개 lesson, {M}개 decision 축적됨

다음: /rank (컴포넌트 우선순위) 또는 /present (기획서)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
