# exp_006 — 다중모델 앙상블 + 안전매물 추천시스템

## 한 줄 요약
6개 이종 모델 비교 결과 XGBoost가 최고(AUC 0.9898), voting 앙상블(0.9895)을
추천시스템의 위험 점수원으로 채택 — 단일 모델 의존 탈피 + 추천 기능 신설.

## 설정
- 데이터/라벨: exp_004와 동일 (전세가율 ≥80% 위험 / ≤60% 안전, 60,412건)
- 5-fold Stratified CV, seed 42

## 결과
| 모델 | AUC | F1 | 학습시간 |
|---|---|---|---|
| LightGBM (exp_004 동급) | 0.9894 | 0.9686 | 8s |
| **XGBoost** | **0.9898** | **0.9743** | 7s |
| CatBoost | 0.9874 | 0.9675 | 26s |
| RandomForest | 0.9881 | 0.9719 | 6s |
| HistGB | 0.9888 | 0.9730 | 19s |
| LogisticReg (선형 기준선) | 0.9138 | 0.8949 | 6s |
| Ensemble(Voting 4모델) | 0.9895 | 0.9727 | — |
| Ensemble(Stacking 6모델) | 0.9893 | 0.9738 | — |

## 인사이트
- 부스팅 계열 4개가 0.987~0.990에 수렴 → 피처가 신호를 거의 소진 (exp_005 결론 재확인)
- XGBoost F1 +0.57pp — 위험/안전 경계(0.5) 분류가 가장 정확
- 선형모델 AUC 0.914 → 비선형 상호작용(보증금×노후도 등)이 ~7.6pp 기여 근거
- Voting은 최고 단일보다 AUC 미세 열세지만 fold 간 분산이 낮아 강건성 목적에 부합

## 산출물
- `models/ensemble_voting.joblib` — LGBM+XGB+CatBoost+HistGB 전체데이터 학습본
- `oof_predictions.parquet` — 라벨 데이터 OOF 확률 (figure/분석용)
- `data/processed/recommend_base.parquet` — 전 거래 102,671건 앙상블 위험확률
- `scripts/recommender.py` — 예산·면적·우선축·구 조건 → 동네 Top-k + 실거래 대표매물

## 추천시스템 설계
추천점수 = 0.5·(1−앙상블위험확률) + 0.3·종합안전점수 + 0.2·우선축점수
- 최근 18개월 실거래, 예산 ±25%, 표본 3건 미만 동 제외
- LLM(exp_007)의 `recommend` 툴로 노출
