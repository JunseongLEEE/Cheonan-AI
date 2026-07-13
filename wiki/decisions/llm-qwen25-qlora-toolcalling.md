---
id: llm-qwen25-qlora-toolcalling
type: decision
created: 2026-07-08
updated: 2026-07-08
tags: [llm, tool-calling, qlora, exp_007, chatbot]
related: [[multimodel-ensemble-voting]], [[gpu-contention-wait-and-train]]
summary: 챗봇 LLM을 GPT API에서 자체 파인튜닝 Qwen2.5-7B(QLoRA+tool-calling)로 대체
---

## Context
- 기존 챗봇은 OpenAI gpt-5-mini 의존 → API 비용, 외부 의존, 대회 차별성 부족
- 사용자 요구: 3090×2에서 깡통전세 전문 LLM을 직접 학습, 데이터·LightGBM·뉴스 툴 자동 호출
- 대회 어필 포인트: "AI 모델 개발" 분야에서 예측모델+LLM 에이전트 결합은 상위 차별성

## Decision
1. **베이스**: Qwen/Qwen2.5-7B-Instruct — 한국어 성능 + Hermes-형 네이티브 tool-calling 템플릿 + 24GB QLoRA 적합 + vLLM 0.7.3 hermes parser 지원
2. **학습**: 4-bit NF4 QLoRA (r16/α32, 전 프로젝션), assistant 턴만 loss (prefix-render diff 마스킹), max_len 2600, 2 epoch, effective batch 32, 2GPU DDP
3. **데이터**: 8종 intent 6,850 대화. 툴 출력은 전부 실측값(exp_004 LightGBM 실예측, 65동 안전점수, exp_006 추천 실호출). 되묻기/범위밖 거절 케이스 포함 → 환각 툴콜 방지
4. **서빙**: LoRA 머지 → vLLM OpenAI-호환 서버(port 8008, GPU 1장) → `scripts/llm/local_llm.py` 에이전트 루프
5. **통합**: rag_chatbot.answer() 우선순위 로컬 → OpenAI → rule-based (무중단 폴백 유지)

## Consequences
- (+) 외부 API 비용 0, 발표 시연에서 "자체 LLM" 어필, 규칙 라우터 없이 LLM이 툴 결정
- (+) 툴 스키마 단일 소스(scripts/llm/tools_schema.py)로 학습·서빙 일관성
- (−) GPU 1장을 서빙에 상시 점유, 로컬 서버 기동 필요 (미기동 시 자동 폴백)
- (−) Streamlit Cloud 배포본은 로컬 LLM 접근 불가 → OpenAI 폴백으로 동작
