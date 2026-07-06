# Competition Agentic Field — 천안 청년 자취방 안전지도

## Philosophy: Compound Engineering 80/20

이 시스템은 **Compound Engineering** 원칙을 따른다:
- **80%** — Plan & Review (brainstorm → plan → evaluate → compound)
- **20%** — Work (implement → run)

모든 작업은 과거 지식을 먼저 검색하고, 끝나면 새 지식을 축적한다.
새 세션은 bridge files + wiki 검색으로 즉시 컨텍스트를 복구한다.

---

## Project Overview

**2026 천안시 AI·데이터 기반 정책 아이디어 경진대회** (AI 모델 개발 분야) 출품작.
청년이 자취방 계약 전 깡통전세·건물 노후·침수·치안·교통·편의시설 등 종합 안전성을 한눈에 진단받을 수 있는 **AI 기반 지도 서비스**.

**과제 매핑**: 지역균형발전 — 구도심 청년 주거안전 격차 해소
**핵심 차별점**: HUG 안심전세는 '1채 진단' → 우리는 도시 전체 선제 스캔 + 종합 안전성(전세사기+침수+치안+교통) 통합

---

## 대회 규정 (CRITICAL)

### 일정
- 접수: 2026.6.8 ~ 8.31
- 예선 서면심사: 9월 중
- 본선 오프라인 PT(10분): 10월 중 (상위 10팀)
- 시상식: 10월 말
- 총상금: 1,000만원 (대상 500만/최우수 200만/우수 100만×3팀)

### 평가기준
**예선 (각 20점)**:
1. 주제적합성 — 천안시 행정 개선·시민 편익 기여
2. 창의성 — 기존 사고를 넘는 새로운 접근
3. 아이디어기획력 — 논리적 구성과 실현 가능성
4. 데이터이해/분석적정성 — 데이터 활용의 적절성
5. 활용가능성 — 실제 정책/서비스로 활용 가능 여부

**본선 (100점)**:
- 논리성·타당성 30 / 발표전달력 30 / 활용가능성 20 / 주제적합성 10 / 창의성 10

### 데이터 규정 (매우 중요)
- 정식 API 또는 공공포털 등 **합법 수집 데이터만 허용**
- 수집시점·범위·주요컬럼·출처 URL 기재 필수
- 제3자 라이선스 침해·상업적 민간데이터 무단사용 **엄격 금지**
- 직방/다방/네이버부동산 크롤링 → **금지로 간주**
- 공공 실거래가·건축물대장 중심 설계가 안전

### 제출 형식
DACON 코드 제출이 아님. **서면 기획서(예선) + 오프라인 PT 10분(본선)**.
- 기획서: 문제정의, 데이터 파이프라인, AI 모델 아키텍처, 시각화, 시연, 기대효과
- 발표: 실제 작동 데모 + SHAP 설명 + 시뮬레이터 시연

---

## Directory Structure
```
.claude/skills/  — Slash command skills
scripts/         — Python utility scripts (데이터 수집, ETL, 모델, 시각화)
experiments/     — One folder per experiment (exp_001/, exp_002/, ...)
  └── exp_NNN/
      ├── config.yaml       # 모든 파라미터
      ├── train.py          # 학습 + 평가
      ├── features.py       # 피처 엔지니어링
      ├── model.py          # 모델 정의
      ├── SUMMARY.md        # 실험 메모리 카드
      └── train_log.json    # 결과 기록
data/
  ├── raw/                  # API 수집 원본 (자동 생성)
  ├── manual/               # 수동 다운로드 파일
  ├── processed/            # ETL 처리 결과
  └── h3/                   # H3 헥사곤 격자 집계 데이터
collector/                  # 데이터 수집 파이프라인 스크립트
  ├── _common.py
  ├── 01_realestate.py ~ 09_sgis.py
  └── 99_run_all.py
wiki/            — LLM Wiki (Compound Knowledge Base)
  ├── _meta/
  │   ├── conventions.md
  │   └── index.md
  ├── entities/
  ├── decisions/
  ├── lessons/
  ├── context/
  └── sessions/
logs/            — Bridge files for agent communication
  ├── orchestrator_state.json
  ├── experiment_digest.md
  ├── pipeline_status.json
  ├── insights.jsonl
  ├── cycle_history.jsonl
  └── agent_messages.jsonl
docs/            — 기획서 및 발표자료
agents/          — Agent role definitions
```

---

## Compound Workflow (핵심 사이클)

모든 작업은 이 사이클을 따른다:

```
┌─────────────────────────────────────────────────┐
│  1. SEARCH  — wiki + bridge files에서 과거 지식 검색  │
│  2. BRAINSTORM — 과거 컨텍스트 기반으로 아이디어 탐색   │
│  3. PLAN    — 실험/작업 계획 (80% 시간)               │
│  4. WORK    — 구현 + 실행 (20% 시간)                  │
│  5. REVIEW  — 결과 평가 + 품질 체크 (80% 시간)         │
│  6. COMPOUND — 결정/교훈/컨텍스트를 wiki에 적재        │
└─────────────────────────────────────────────────┘
```

### Session Start Protocol
새 세션이 시작되면 반드시:
1. `logs/orchestrator_state.json` 읽어 현재 전략 상태 파악
2. `logs/experiment_digest.md` 읽어 전체 실험 현황 파악
3. `logs/pipeline_status.json` 읽어 데이터 수집 진행 상황 파악
4. `wiki/` 에서 관련 decisions/lessons 검색하여 과거 컨텍스트 주입

### Session End Protocol
작업 종료 시 `/compound` 실행하여:
1. 이 세션의 결정/교훈/새 개념을 wiki에 적재
2. bridge files 업데이트
3. experiment_digest.md 갱신

---

## Workflow Rules
1. **공공 API 데이터만 사용** — 민간 크롤링 금지, 출처 URL 필수 명기.
2. **One experiment = one folder** — self-contained with config, code, and SUMMARY.md.
3. **Reproducibility** — seed, config, git commit hash, 평가 점수 기록.
4. **평가축 중심 개발** — 모든 기능이 대회 5대 평가축 중 하나 이상에 기여해야 함.
5. **Experiment memory** — every experiment has SUMMARY.md for instant context recovery.
6. **Compound before close** — 세션 종료 전 반드시 /compound로 지식 축적.
7. **Search before plan** — 새 실험 계획 전 반드시 wiki에서 과거 교훈 검색.
8. **데이터 신선도 주의** — 실거래 신고지연, 공시가 연1회 등 갱신주기 인지.

---

## Project Phases (전략 단계)

```
Phase 1: data_collection (6월)
  → 17개 공공 API + SGIS 6개 데이터 수집 파이프라인
  → collector/ 스크립트 작성 및 실행

Phase 2: eda_etl (6~7월)
  → 수집 데이터 EDA, 품질 검증
  → ETL: 정제, 통합, H3 격자 집계
  → 전세가율 산출, 건물 노후도 계산

Phase 3: model_dev (7월)
  → 깡통전세 분류기 (LightGBM + PU러닝 + SHAP)
  → 8축 종합 안전점수
  → Isolation Forest 이상탐지
  → 임대인-건물 그래프 탐지

Phase 4: visualization (7~8월)
  → 신호등 지도 (H3 헥사곤 + 매물 핀)
  → "이 조건 계약 시 위험도?" 시뮬레이터
  → 행정 대시보드 (위험 핫스팟 히트맵)

Phase 5: integration (8월)
  → FastAPI 백엔드
  → Next.js + Mapbox/deck.gl 프론트엔드
  → RAG 정책 챗봇

Phase 6: presentation (8월 말)
  → 기획서 작성
  → 발표자료 + 시연 데모 준비
```

---

## AI Model Stack

### 핵심 모델 (임팩트 우선순위)
1. **깡통전세 분류기** (LightGBM/XGBoost + SHAP) — 핵심 차별성
   - 피처: 전세가율, 공시가×1.26 대비 보증금, 건물연령, 전용면적, 세대수, 동네평균 등
   - 라벨 부족 → PU러닝 + 휴리스틱 약지도
2. **8축 종합 안전점수** — 금융·노후·침수·치안·소방·교통·편의·환경 가중합
3. **이상탐지** — Isolation Forest, HDBSCAN (동일 임대인 다물건 패턴)
4. **시계열 예측** — Prophet/LSTM (동네별 전세가율 추세)
5. **추천** — 사용자 조건 기반 안전 매물 추천

### 보조 모델
- 임대인-건물 그래프 (GNN)
- 등기부 OCR + 위험조항 탐지
- RAG 정책 챗봇

---

## Skills (Slash Commands)

### Compound workflow (지식 축적)
```
/compound         — 세션의 결정/교훈/컨텍스트를 wiki에 적재
```

### Manual workflow (step by step)
```
/eda              — 데이터 탐색 (수집 후)
/plan             — 실험 계획 수립 (wiki 검색 → 과거 교훈 반영)
/dev baseline     — 실험 구현 (모델 + 파이프라인)
/run exp_001      — 실험 실행 + SUMMARY.md 업데이트
/eval exp_001     — 결과 평가 + 도메인 적합성 체크
/present          — 기획서 초안 + 발표자료 생성
/rank             — 모델/기능 우선순위 매기기
/status           — 전체 현황 대시보드
```

### Autonomous mode (자동 파이프라인)
```
/auto             — 5사이클 자동 실행 (search→plan→dev→run→eval→compound 반복)
/auto 10          — 10사이클
```

### Guardrails
- 5회 연속 개선 없으면 자동 중단
- NaN/Inf 발생하면 즉시 중단
- 모든 실험은 EXPERIMENT_LOG.csv + SUMMARY.md에 기록
- 공공 API 외 데이터 사용 시 경고

---

## 천안 핵심 상수

```python
# 법정동코드
CHEONAN_DONGNAM = "44131"  # 동남구
CHEONAN_SEOBUK = "44133"   # 서북구
LAWD_CDS = [CHEONAN_DONGNAM, CHEONAN_SEOBUK]

# 청년 통계
YOUTH_POPULATION = 197_572  # 18~39세 (2025.5)
TOTAL_POPULATION = 661_615
YOUTH_HOMEOWNERSHIP = 0.139  # 13.9% → 86% 무주택

# 전세사기 실태
FRAUD_HOUSEHOLDS = 288      # 피해 세대 수
FRAUD_AMOUNT_BILLION = 145  # 피해액 (억원)

# 깡통전세 임계
JEONSE_RATE_SAFE = 0.60
JEONSE_RATE_CAUTION = 0.75
JEONSE_RATE_DANGER = 0.80
JEONSE_RATE_CRITICAL = 0.90
HUG_126_RULE = 1.26  # 공시가 × 126%
```

---

## LLM Wiki Conventions

### Frontmatter (모든 wiki 페이지 필수)
```yaml
---
id: <kebab-case-slug>
type: entity | decision | lesson | context | session
created: <ISO date>
updated: <ISO date>
tags: [topic1, topic2]
related: [[other-page-id]]
summary: <한 줄 요약>
---
```

### Page Types
- **entity**: `## Definition / ## Why it matters / ## Related / ## History`
- **decision**: ADR 포맷 — `## Context / ## Decision / ## Consequences`
- **lesson**: `## Symptom / ## Root cause / ## Fix / ## Generalization`
- **context**: 프로젝트 스냅샷 — 자유 형식
- **session**: compound 원본 — 자동 생성

### Conflict Rule
기존 페이지와 충돌하면 새 페이지 만들지 말고 기존 페이지에 `## Conflict yyyy-mm-dd` 섹션 추가.

---

## Bridge Files (Agent Context Recovery)
새 세션에서 /auto 실행 시 이 파일들로 상태 복구:
- `logs/orchestrator_state.json` — 현재 전략, best score, phase
- `logs/experiment_digest.md` — 모든 실험 요약 테이블
- `logs/pipeline_status.json` — 데이터 수집 진행 상태
- `logs/insights.jsonl` — 모델 성능 패턴 (최근 5개만 로드)
- `logs/cycle_history.jsonl` — 최근 N 사이클 reasoning

---

## Conventions
- Config files: YAML format with seed, model params, data paths
- CV: 5-fold stratified by default (깡통전세는 PU러닝 고려)
- Metrics: 모델별 적합 메트릭 (분류 F1/AUC, 회귀 RMSE, 점수 일관성)
- Naming: exp_NNN_short_description (e.g., exp_001_baseline_lgbm)
- 모든 데이터 출처 URL·컬럼·시점 명시
- 한국어 주석 + docstring OK

---

## QMD Integration (Optional)

QMD가 설치되어 있으면 wiki를 하이브리드 검색(BM25 + 벡터 + LLM 리랭킹)으로 조회할 수 있다.

### Setup
```bash
npm install -g @tobi/qmd
qmd collection add wiki/ --name wiki --pattern "**/*.md"
qmd index wiki
```

QMD 없이도 wiki는 직접 파일 읽기/Grep으로 검색 가능. QMD는 검색 품질을 높이는 선택적 레이어.
