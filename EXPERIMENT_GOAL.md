# Experiment Goals — 천안 청년 자취방 안전지도

## Competition Objective
- **Competition**: 2026 천안시 AI·데이터 기반 정책 아이디어 경진대회
- **분야**: AI 모델 개발 (예측·분류·추천)
- **과제**: 지역균형발전 — 구도심 청년 주거안전 격차 해소
- **제출**: 기획서(8/31) → 예선 서면(9월) → 본선 PT 10분(10월)
- **핵심 메트릭**: 깡통전세 분류 F1/AUC, 안전점수 일관성, 사용자 체감 유용성

## Current Strategy

### Phase 1: Data Collection (6월)
- [ ] 공공데이터포털 17개 API 수집 파이프라인 구축
- [ ] SGIS 6개 API 수집 (인구/가구/주택/사업체/격자/경계)
- [ ] 수동 다운로드 4건 가이드 작성
- [ ] 수집 데이터 무결성 검증

### Phase 2: EDA & ETL (6~7월)
- [ ] 수집 데이터 EDA (분포, 결측, 이상치)
- [ ] 실거래가 매매-전세 매칭 → 전세가율 산출
- [ ] 건축물대장 사용승인일 → 건물연령/노후도
- [ ] 공시가격 연계 → HUG 126% 룰 계산
- [ ] H3 헥사곤 격자 집계
- [ ] 안전 변수별 정규화

### Phase 3: Model Development (7월)
- [ ] 깡통전세 분류기 baseline (LightGBM + 휴리스틱 라벨)
- [ ] PU러닝 적용 (Elkan & Noto two-step)
- [ ] SHAP 설명력 검증
- [ ] 8축 종합 안전점수 가중합 설계
- [ ] Isolation Forest 이상탐지 (동일 임대인 패턴)
- [ ] 추천 시스템 (안전 대체 매물)

### Phase 4: Visualization & Service (7~8월)
- [ ] 신호등 지도 (H3 + Mapbox/deck.gl)
- [ ] "이 조건 계약 시 위험도?" 시뮬레이터
- [ ] 행정 대시보드 (위험 핫스팟 히트맵)
- [ ] RAG 정책 챗봇 (천안 청년주거정책)

### Phase 5: Integration (8월)
- [ ] FastAPI 백엔드
- [ ] Next.js 프론트엔드 (모바일 우선)
- [ ] 등기부 OCR 업로드 플로우
- [ ] 전체 시스템 통합 테스트

### Phase 6: Presentation (8월 말)
- [ ] 기획서 초안 작성 (대회 평가축 매핑)
- [ ] 발표자료 제작 (10분 PT)
- [ ] 시연 데모 안정화
- [ ] 임팩트 스토리 정리

## Hypotheses Backlog

| Priority | Hypothesis | Expected Impact | Phase | Status |
|----------|-----------|-----------------|-------|--------|
| HIGH | 전세가율 80%+ 단일 피처만으로 깡통 1차 필터링 가능 | baseline 확립 | 3 | PLANNED |
| HIGH | 공시가×1.26 대비 보증금 비율이 전세가율보다 설명력 높음 | +F1 개선 | 3 | PLANNED |
| HIGH | PU러닝이 휴리스틱 라벨보다 recall 향상 | +recall | 3 | PLANNED |
| MEDIUM | 건물연령+구조+세대수가 노후 위험 핵심 피처 | 안전점수 정확도 | 3 | PLANNED |
| MEDIUM | 동일 임대인 다물건 패턴이 Isolation Forest로 탐지 가능 | 사기패턴 발견 | 3 | PLANNED |
| MEDIUM | H3 격자 집계가 동 단위보다 공간 해상도 우수 | 시각화 품질 | 2 | PLANNED |
| LOW | 시계열 Prophet으로 동네별 전세가율 추세 예측 가능 | 조기경보 | 3 | PLANNED |
| LOW | 매물사진 CLIP/ViT로 곰팡이/누수 탐지 | 시연 임팩트 | 4 | PLANNED |

## 핵심 벤치마크/전환 트리거
- 단독·다가구 지번 매칭률 <60% → 행정동 단위 집계로 전환
- 사기 positive 라벨 <50건 → 분류기보다 이상탐지+규칙 비중 높이기
- 등기부 자동수집 불가 확정 → 사용자 업로드 OCR 플로우를 메인으로
