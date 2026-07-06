---
description: "Implement an experiment — creates isolated experiment directory with model/pipeline code. Pass experiment name or plan reference as argument."
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

# /dev — Model Developer (천안 자취방 안전지도)

You implement experiments for the 천안 청년 자취방 안전지도 프로젝트. Each experiment is self-contained in its own directory.

## Arguments
- `$ARGUMENTS` — experiment name or description (e.g., "baseline_lgbm", "safety_score_v1", "anomaly_if")

## Experiment Directory Structure

```
experiments/exp_NNN_name/
├── config.yaml          # 모든 파라미터
├── train.py             # 학습 + 평가 스크립트
├── features.py          # 피처 엔지니어링 (필요 시)
├── model.py             # 모델 정의 (커스텀 시)
├── requirements.txt     # 추가 의존성
├── SUMMARY.md           # 실험 메모리 카드
└── README.md            # 가설, 접근법
```

## Step 1: Read Context

Before implementing, read:
```
logs/experiment_digest.md    — 시도된 실험, 결과
EXPERIMENT_GOAL.md           — 현재 전략, 가설 백로그
Competition_desription.md    — 대회 정보
```

## Step 2: Create Experiment Directory

```bash
python scripts/create_experiment.py --name "$0" --hypothesis "$ARGUMENTS"
```

Or create manually if script doesn't fit.

## Step 3: Implement train.py

The training script MUST:

1. **Load config.yaml** for all parameters
2. **Set seeds** everywhere (numpy, random, sklearn, etc.)
3. **데이터 로드**: `../../data/processed/` 에서 처리된 데이터 로드
4. **모델별 학습**:
   - 깡통전세 분류기: CV loop + SHAP 출력
   - 안전점수: 가중합 로직 + 정규화
   - 이상탐지: fit + 이상 점수 출력
   - 추천: 유사도 계산 + 순위
5. **Save outputs**:
   - `train_log.json` — 구조화된 결과
   - `models/` — 학습된 모델
   - `shap/` — SHAP 시각화 (분류기 모델)
6. **Be runnable** with: `cd experiments/exp_NNN && python train.py`

### train_log.json Format (MUST follow)

```json
{
  "experiment_id": "exp_NNN_name",
  "model_type": "gangton_classifier|safety_score|anomaly_detection|recommender",
  "cv_scores": [0.XX, 0.XX, 0.XX, 0.XX, 0.XX],
  "cv_mean": 0.XXXX,
  "cv_std": 0.XXXX,
  "metric_name": "f1|auc|rmse|precision|recall",
  "runtime_seconds": 123.4,
  "n_features": 50,
  "feature_importance": {"feat1": 0.1, "feat2": 0.05},
  "shap_generated": true,
  "data_sources": ["realestate", "building", "housing_price"],
  "cheonan_codes": ["44131", "44133"]
}
```

## Step 4: Create SUMMARY.md

Copy from `experiments/TEMPLATE_SUMMARY.md` and fill in Setup section.

## Step 5: Verify

```bash
# 문법 검증
python -m py_compile train.py

# 데이터 경로 확인
ls ../../data/processed/
```

## After Implementation

```
Experiment: exp_NNN_name
Files created:
  ✓ config.yaml
  ✓ train.py
  ✓ requirements.txt
  ✓ SUMMARY.md

Ready to run: /run exp_NNN_name
```

Do NOT run the experiment — that's `/run`'s job.
