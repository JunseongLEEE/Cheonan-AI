---
description: "Record evaluation results and extract insights. Updates experiment memory and tracks progress across models. Usage: /submit-result exp_001 0.8234"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# /submit-result — Record Result & Extract Insights (천안 자취방 안전지도)

실험 결과를 기록하고 인사이트를 추출한다. 이 대회는 온라인 리더보드가 아닌 서면/PT 평가이므로,
내부 실험 간 비교와 도메인 적합성 평가에 초점을 맞춘다.

## Arguments
- `$ARGUMENTS` — format: `<experiment_name> <score>` (e.g., "exp_001_baseline 0.8234")

## Step 1: Parse & Validate

Extract experiment name and score from arguments.
Find the experiment directory and load its results.

## Step 2: Load Experiment Data

```python
import json
from pathlib import Path

exp_dir = Path(f'experiments/{exp_name}')
train_log = json.load(open(exp_dir / 'train_log.json'))
cv_mean = train_log['cv_mean']
cv_std = train_log['cv_std']
model_type = train_log.get('model_type', 'unknown')
```

## Step 3: Analyze & Compare

```python
import csv
# Load all experiments for comparison
with open('EXPERIMENT_LOG.csv') as f:
    history = list(csv.DictReader(f))

# Same model type comparison
same_type = [r for r in history if r.get('model_type') == model_type]

# Best score across all
best_overall = max((float(r['cv_score']) for r in history if r.get('cv_score')), default=0)
```

**Insight extraction:**

| Pattern | Insight |
|---------|---------|
| Best score for this model type | "New best for {model_type}" |
| Significant improvement > 5% | "Major breakthrough — investigate what changed" |
| Score regression | "Regression — check data/feature changes" |
| High CV std | "Unstable — consider simpler model or more data" |
| SHAP top features changed | "Feature importance shift — review domain validity" |

## Step 4: Update Files

### 4a. Update experiment SUMMARY.md
Add result and insight to Results section.

### 4b. Append to `logs/insights.jsonl`
```python
insight_record = {
    "date": "YYYY-MM-DD",
    "experiment": exp_name,
    "model_type": model_type,
    "cv_score": cv_mean,
    "cv_std": cv_std,
    "vs_best": cv_mean - best_overall,
    "insight": "generated insight",
    "actionable": "next experiment suggestion"
}
```

### 4c. Update EXPERIMENT_LOG.csv

### 4d. Rebuild digest
```bash
python scripts/build_digest.py
```

## Step 5: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESULT RECORDED: exp_NNN_name
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Model Type:    {model_type}
CV Score:      0.XXXX ± 0.XXXX
vs Best:       {+/-}0.XXXX
vs Same Type:  {+/-}0.XXXX

INSIGHT: {what we learned}
ACTION: {what to do next}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
