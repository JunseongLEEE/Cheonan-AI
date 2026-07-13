# exp_007 — 천안세이프 LLM (깡통전세 전문 Tool-Calling sLLM)

## 한 줄 요약
Qwen2.5-7B를 실데이터 기반 tool-calling 대화 6,850건으로 QLoRA 파인튜닝하여
챗봇의 GPT API(gpt-5-mini)를 자체 온프레미스 LLM으로 대체.

## 상태 — 전부 완료 (2026-07-08 ~ 07-09)
- [x] 데이터셋 생성: 8 intent, train 6,302 / eval 548 (토큰 mean 1,527 / max 2,089)
- [x] QLoRA 학습: 394 스텝 / 3h52m / final train_loss 0.074 / eval_loss 0.043→0.0052 단조 수렴
- [x] 평가 (held-out 300건): **베이스 vs 파인튜닝**
  | 지표 | 베이스 | 천안세이프 | Δ |
  |---|---|---|---|
  | 툴 호출 여부 판단 | 79.7% | **100%** | +20.3pp |
  | 툴 이름 선택 | 88.6% | **100%** | +11.4pp |
  | 인자 JSON 유효율 | 100% | 100% | — |
  | 인자 추출 F1 | 73.6% | **99.9%** | +26.2pp |
  - 베이스 취약 intent: recommend 55.9%, dong_lookup 65.1% → 파인튜닝 후 전 intent 100%
- [x] LoRA 머지 → /opt/models/cheonan-safeguard-7b (15GB bf16)
- [x] vLLM 서빙 (port 8008, hermes parser) + rag_chatbot 통합 → **gpt-5-mini 대체 완료**
- [x] e2e 스모크: simulator/dong_lookup/recommend/news_search(실시간 RSS)/clarify/out_of_scope 통과

## 대화 프로브 개선 사이클 (2026-07-09, 5 라운드)
- `scripts/llm/chat_probe.py` — 18개 실전 시나리오 (멀티턴/구어체/오타/감정/인젝션/정책)
- 발견→수정 (재학습 없이 서빙단 가드, [[llm-serving-guards]]):
  | 문제 | 해결 |
  |---|---|
  | 오타·미등록 동 오진 ("불당둥"→안전 3.8%) | 툴 실행기 fuzzy 검증·교정 + 읍/면 후보 안내 |
  | HUG 조건 창작, 제도 환각 | KB 문자-bigram 검색 → 시스템 프롬프트 주입 |
  | 중국어/태국어 혼입 | temperature 0.2→0 (greedy) |
  | 인젝션 시 가짜 안전점수 (원성동 95/100) | 그라운딩 가드: 강제 dong_lookup 후 실데이터(44.9)로 반박 |
  | 후속 턴 수치 변조 (15.57→35.21%) | 수치 이력 대조 가드: 미확인 수치 재작성 요구 |
- 최종 회귀: 18/18 시나리오 안정 (멀티턴 문맥·평→㎡ 환산·2연속 툴 비교 포함)
- 대화 캡처 figure: fig_Chat_Multiturn.png / fig_Chat_Guardrail.png (실로그 원문)

## 운영 노트
- 공유 GPU 경합: [[gpu-contention-wait-and-train]] — VRAM 20GB 선예약 + idle 워처로 해결
- 재기동: `bash scripts/llm/serve.sh` (서버), 미기동 시 챗봇은 OpenAI→rule-based 자동 폴백

## 설계
- 베이스: Qwen/Qwen2.5-7B-Instruct (한국어 + Hermes tool-calling 템플릿)
- QLoRA: 4-bit NF4, r16/α32, 전 프로젝션, assistant 턴만 loss, max_len 2600
- 학습: 2 epoch, effective batch 32 (2×8×2GPU), lr 1e-4 cosine, RTX 3090×2 DDP
- 툴 4종: simulator(exp_004 LGBM+SHAP) / dong_lookup(65동 8축) / recommend(exp_006 앙상블) / news_search
- 데이터 원칙: 툴 출력 100% 실측값, 되묻기·범위밖 거절 케이스 포함

## 파이프라인 파일
| 단계 | 파일 |
|---|---|
| 툴 스키마(단일 소스) | scripts/llm/tools_schema.py |
| 데이터셋 생성 | scripts/llm/build_dataset.py |
| 학습 | scripts/llm/train_qlora.py (torchrun 2 GPU) |
| 평가 | scripts/llm/eval_toolcall.py --model base|tuned |
| 머지 | scripts/llm/merge_lora.py → /opt/models/cheonan-safeguard-7b |
| 서빙 | scripts/llm/serve.sh (vLLM port 8008, hermes parser) |
| 에이전트 클라이언트 | scripts/llm/local_llm.py |
| 챗봇 통합 | scripts/rag_chatbot.py answer() 최우선 경로 |
| 자동화 | wait_and_train.sh → wait_for_train_end.sh → post_train.sh |

## 결과 (학습 후 기입)
- train/eval loss: TBD (train_history.json)
- tool-calling 평가: TBD (eval/toolcall_base.json vs toolcall_tuned.json)
