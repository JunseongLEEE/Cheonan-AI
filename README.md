# 천안 청년 자취방 안전지도 — Agentic Workflow

2026 천안시 AI·데이터 기반 정책 아이디어 경진대회 출품작.
Compound Engineering 80/20 원칙 기반 실험 관리 시스템.

## Philosophy

- **Two-phase**: plan first (80%), then execute (20%)
- **Compound Knowledge**: 매 세션 시작 시 wiki 검색, 종료 시 지식 축적
- **Isolation**: 실험별 독립 폴더, 재현 가능
- **공공 데이터 Only**: 민간 크롤링 금지, 출처 명기

## Quick Start

```bash
# 1. 데이터 수집 파이프라인 실행
python collector/99_run_all.py

# 2. EDA
/eda

# 3. 실험 계획
/plan

# 4. 실험 구현
/dev baseline_lgbm

# 5. 실험 실행
/run exp_001_baseline_lgbm

# 6. 결과 평가
/eval exp_001_baseline_lgbm

# 7. 현황 확인
/status

# 8. 기획서 생성
/present
```

## Multi-Agent Workflow

| Agent | Role | When to Use |
|-------|------|-------------|
| `orchestrator` | 프로젝트 전략 수립, 실험 계획 | 세션 시작, 결과 리뷰 후 |
| `model_developer` | 모델 구현 (분류기/안전점수/이상탐지) | 계획 수립 후 |
| `experiment_runner` | 실험 실행, 결과 캡처 | 코드 구현 후 |
| `evaluator` | 결과 평가, 도메인 적합성 체크 | 실험 완료 후 |
| `presenter` | 기획서·발표자료 생성 | Phase 6 |
| `component_selector` | 최종 서비스 기능 우선순위 | 통합 전 |

## Directory Structure

```
Agentic_field_competition/
├── CLAUDE.md                    # Core 시스템 아키텍처
├── RULES.md                     # 대회 규정 & 제약
├── EXPERIMENT_GOAL.md           # 전략 & 가설 백로그
├── EXPERIMENT_LOG.csv           # 실험 트래커
├── Competition_desription.md    # 대회 설명
├── agents/                      # Agent 역할 정의
├── .claude/skills/              # Slash command skills
├── scripts/                     # Python 유틸리티
├── collector/                   # 데이터 수집 파이프라인
├── experiments/                 # 실험 폴더 (exp_001/, ...)
├── data/                        # 수집 데이터 (gitignored)
├── docs/                        # 기획서 & 발표자료
├── logs/                        # Bridge files
└── wiki/                        # LLM Wiki (Compound Knowledge)
```

## Project Phases

1. **Data Collection** (6월) — 17개 공공 API + SGIS 수집
2. **EDA & ETL** (6~7월) — 전세가율 산출, H3 격자 집계
3. **Model Dev** (7월) — 깡통전세 분류기, 안전점수, 이상탐지
4. **Visualization** (7~8월) — 신호등 지도, 시뮬레이터, 대시보드
5. **Integration** (8월) — FastAPI + Next.js + RAG 챗봇
6. **Presentation** (8월 말) — 기획서 + PT 발표 준비

## Key Principles

1. **공공 데이터만 사용** — 출처 URL·컬럼·시점 명기
2. **실험 격리** — 각 실험은 독립적이고 재현 가능
3. **설명 가능성** — SHAP으로 "왜 위험한가" 전달
4. **평가축 매핑** — 모든 기능이 대회 5대 평가축에 기여
5. **Compound** — 세션 종료 전 반드시 /compound로 지식 축적
