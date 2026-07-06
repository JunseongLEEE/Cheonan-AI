---
id: cycle20-30-plan
type: context
created: 2026-06-15
tags: [auto, visualization_polish, ux]
summary: Cycle 20~30 자동 개선 루프 계획
---

# Cycle 20~30 계획 (스크린샷 기반)

## 식별된 문제점/개선점

### Cycle 20: 안전지도 기본 동 "데이터 없음" 수정
- 기본 선택 동(구룡동)의 전세가율/거래수가 "데이터 없음"
- 기본 동을 데이터가 풍부한 동(불당동)으로 변경

### Cycle 21: 챗봇 "안전한 동네 추천" 응답 강화
- 현재 동 이름 + 점수만 나열 → 예산 조건 연동 + 신호등 아이콘 추가

### Cycle 22: 비교모드 하단 비교 차트 가독성 개선
- 비교 bar chart 라벨이 작음 → 텍스트 크기 + 색상 대비 강화

### Cycle 23: deprecation warning 수정
- use_container_width → width 마이그레이션 (Streamlit 최신 API)

### Cycle 24: 예산 추천 결과 요약 문장 자동 생성
- "5천만원 예산으로 가장 안전한 동네는 부대동입니다" 식 한줄 요약

### Cycle 25: 계약 가이드 체크박스 상태 저장 + 인쇄용 PDF 링크
- session_state로 체크 상태 유지 + "체크리스트 인쇄" 안내

### Cycle 26: 히어로 배너 통계 업데이트 + 애니메이션 효과
- 숫자 카운터 CSS 또는 st.metric 활용

### Cycle 27: SHAP waterfall chart (현재 horizontal bar → waterfall 변경)
- 더 직관적인 개별 예측 설명

### Cycle 28: 데이터 더보기 랭킹 테이블에 sparkline 미니차트
- 각 동 행에 전세가율 추이 미니 그래프

### Cycle 29: 전체 앱 접근성 개선 + 모바일 반응형
- 좁은 화면 대응, aria-label, 색맹 대비

### Cycle 30: orchestrator state + wiki compound + 최종 검증
- bridge files 업데이트, wiki 축적, 전체 스크린샷 최종 검증
