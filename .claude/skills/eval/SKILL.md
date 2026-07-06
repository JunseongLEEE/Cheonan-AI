---
description: "Evaluate experiment results — checks domain validity, model quality, and competition evaluation axis contribution. Pass experiment name as argument."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# /eval — Experiment Evaluator (천안 자취방 안전지도)

실험 결과의 품질, 도메인 적합성, 대회 평가축 기여도를 평가한다.

## Arguments
- `$ARGUMENTS` — experiment name (e.g., "exp_001_baseline_lgbm")

## Step 1: Load Results

Read from experiment directory:
- `train_log.json` — CV scores, feature importance
- `config.yaml` — model config, seed
- `SUMMARY.md` — hypothesis

Also load:
- `EXPERIMENT_LOG.csv` — baseline 비교용

## Step 2: Run Checks

### A. Score Comparison
- 현재 실험 CV score vs baseline
- 개선 폭 계산

### B. Stability Analysis
- CV std: < 0.005 = A, < 0.01 = B, < 0.02 = C, >= 0.02 = D
- 단일 fold > 3σ → 의심 플래그

### C. Domain Validity (천안 특화)
- [ ] 천안 법정동코드(44131, 44133) 데이터만 사용
- [ ] 전세가율 계산 정확 (전세금 ÷ 매매가)
- [ ] 공시가 연계 정확 (HUG 126% 룰)
- [ ] 건물연령 = 현재연도 - 사용승인년도
- [ ] 공공 API 데이터만 사용 (출처 명기)
- [ ] 개인정보 노출 위험 없음

### D. SHAP Check (분류기 모델)
- SHAP 출력 존재 여부
- 상위 피처가 도메인 지식과 일치하는가
- 전세가율이 상위 피처에 포함되는가

### E. 평가축 기여도
| 평가축 | 기여 | 근거 |
|--------|------|------|
| 주제적합성 | HIGH/MEDIUM/LOW | ... |
| 창의성 | HIGH/MEDIUM/LOW | ... |
| 데이터적정성 | HIGH/MEDIUM/LOW | ... |
| 활용가능성 | HIGH/MEDIUM/LOW | ... |

## Step 3: Recommendation

| Condition | Decision |
|-----------|----------|
| 도메인 체크 실패 | REJECT |
| CV worse than baseline | REJECT |
| CV std grade D | REVIEW |
| SHAP 누락 (분류기) | REVIEW |
| Score up + all checks pass | INTEGRATE |

## Step 4: Save & Report

Save `evaluation.json` in experiment directory.
Update experiment status in EXPERIMENT_LOG.csv.

```
========================================
EVALUATION: exp_NNN_name
========================================
CV Score:      0.XXXX ± 0.XXXX (baseline: 0.XXXX)
Improvement:   +0.XXXX
Stability:     A
Domain Check:  PASS
SHAP:          Available ✓
평가축 기여:    주제적합성 HIGH, 활용가능성 HIGH

→ INTEGRATE ✓
다음 단계: /dev (다음 실험) 또는 /present (기획서 준비)
========================================
```
