# 수동 다운로드 가이드

아래 4개 데이터는 공식 API가 없거나 비효율적이라 수동으로 다운로드해야 합니다.
다운로드 후 이 디렉토리(`data/manual/`)에 저장하세요.

---

## 1. TAAS 교통사고 GIS 데이터

1. https://taas.koroad.or.kr/web/shp/sbm/initGisAnals.do 접속
2. 지역 선택: **충청남도 → 천안시 동남구**, **충청남도 → 천안시 서북구**
3. 기간: **2014~2024**
4. 사고유형: 보행자, 어린이, 노인 각각 다운로드
5. SHP 파일을 `data/manual/taas/` 에 저장

## 2. 빈집애 누리집 — 천안 빈집 현황

1. https://binzibe.kr/ 접속
2. 지역 검색: **천안**
3. 현황 데이터 다운로드 (CSV/Excel)
4. `data/manual/binzip/` 에 저장

## 3. 2035 천안도시기본계획 PDF

1. 직접 다운로드: https://files-scs.pstatic.net/2024/05/29/5dHo3r8gGj/2035%20천안도시기본계획.pdf
2. `data/manual/city_plan/2035_천안도시기본계획.pdf` 로 저장
3. (LLM RAG 소스로 활용 예정)

## 4. 천안시 청년정책 페이지

1. https://www.cheonan.go.kr/go_now/contents/dwelling-policy 접속
2. 페이지 내용을 텍스트로 복사하여 `data/manual/youth_policy/dwelling_policy.txt` 로 저장
3. 또는 웹페이지를 PDF로 저장
4. (RAG 챗봇 지식베이스용)

---

## 저장 구조

```
data/manual/
├── README.md          (이 파일)
├── taas/              교통사고 GIS (SHP)
├── binzip/            빈집 현황
├── city_plan/         천안도시기본계획 PDF
└── youth_policy/      청년정책 텍스트
```
