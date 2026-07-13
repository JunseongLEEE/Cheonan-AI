---
id: multimodel-ensemble-voting
type: decision
created: 2026-07-08
updated: 2026-07-08
tags: [ensemble, xgboost, recommender, exp_006]
related: [[llm-qwen25-qlora-toolcalling]]
summary: 깡통전세 분류를 6모델 비교 후 Voting 앙상블 채택, 추천시스템 위험점수원으로 사용
---

## Context
- exp_004 LightGBM 단일 모델(AUC 0.9893) 의존 → 강건성·차별성 보강 필요
- 추천시스템(예산→안전 동네·매물)을 위해 전 거래 위험확률 배치 예측 필요

## Decision
- exp_006: LightGBM/XGBoost/CatBoost/RF/HistGB/LogReg 5-fold 공정 비교 (exp_004 동일 파이프라인)
- 결과: XGBoost 최고 (AUC 0.9898/F1 0.9743), Voting(LGBM+XGB+Cat+HistGB) 0.9895
- **Voting 앙상블을 추천시스템 위험점수원으로 채택** (단일 최고치보다 fold 분산 낮음)
- 추천점수 = 0.5·(1−위험확률) + 0.3·안전점수 + 0.2·우선축, 최근 18개월·예산±25% 필터

## Consequences
- (+) "여러 모델을 만들어 비교·앙상블" 요구 충족, 비선형 기여 근거(선형 0.914 vs 부스팅 0.99) 확보
- (+) recommend_base.parquet(102,671건)로 추천 API가 밀리초 응답
- (−) 부스팅 4개 모델 유지보수 비용, 성능 향상은 미미(+0.0004) → 발표에서는 '강건성 검증' 프레임으로 설명
