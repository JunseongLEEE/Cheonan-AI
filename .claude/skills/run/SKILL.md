---
description: "Run an experiment and capture results. Pass experiment path or name as argument (e.g., /run exp_001_baseline)."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# /run — Experiment Runner (천안 자취방 안전지도)

실험을 실행하고 모든 출력을 캡처한다.

## Arguments
- `$ARGUMENTS` — experiment name or path (e.g., "exp_001_baseline_lgbm")

## Execution Steps

### 1. Locate and Validate
```bash
ls experiments/*$0* 2>/dev/null || ls $ARGUMENTS 2>/dev/null
```

Check these exist before running:
- `config.yaml`
- `train.py`

### 2. Run Training

```bash
cd experiments/EXP_NAME && python train.py 2>&1 | tee run_output.txt
```

Monitor for:
- OOM errors → 즉시 보고
- NaN/Inf in outputs → CRITICAL, 중단
- API 키 관련 에러 → .env 확인 안내
- Runtime > 30min → 경고 플래그

### 3. Verify Outputs

```bash
ls -la train_log.json models/
# SHAP 출력 확인 (분류기 모델인 경우)
ls shap/ 2>/dev/null
```

### 4. Update EXPERIMENT_LOG.csv

```python
import csv, json
from datetime import datetime

with open('train_log.json') as f:
    results = json.load(f)

row = {
    'experiment_id': results['experiment_id'],
    'model_type': results.get('model_type', ''),
    'status': 'COMPLETED',
    'cv_score': results['cv_mean'],
    'cv_std': results['cv_std'],
    'metric': results.get('metric_name', ''),
    'seed': 42,
    'git_commit': GIT_HASH,
    'created_at': datetime.now().isoformat(),
    'notes': ''
}
```

### 5. Update SUMMARY.md Results

```markdown
## Results
| Metric | Score |
|--------|-------|
| CV Mean | {cv_mean} |
| CV Std | {cv_std} |
| CV Fold Scores | {fold scores} |
| SHAP | 생성됨/미생성 |
| Status | COMPLETED |
```

### 6. Rebuild Digest

```bash
python scripts/build_digest.py
```

### 7. Report Summary

```
========================================
EXPERIMENT COMPLETE: exp_NNN_name
========================================
Model Type: [gangton_classifier/safety_score/...]
CV Score: 0.XXXX ± 0.XXXX
Fold scores: [...]
Runtime: X분 XX초
SHAP: ✓/✗
Outputs: train_log.json ✓ | models/ ✓
SUMMARY.md: updated ✓

다음 단계: /eval exp_NNN_name
========================================
```

## Error Handling
- OOM: batch size 줄이기 또는 피처 수 줄이기 제안
- NaN: division by zero, log transform on negatives, 결측값 처리 확인
- Slow: 프로파일링 및 최적화 제안
- Crash: 부분 로그 저장, stack trace 보고, SUMMARY.md 상태를 FAILED로
