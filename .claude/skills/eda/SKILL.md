---
description: "Quick EDA on collected data — analyzes shape, distributions, missing values, data quality, and key patterns for 천안 자취방 안전지도."
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# /eda — Exploratory Data Analysis (천안 자취방 안전지도)

수집된 공공 데이터에 대한 구조화된 EDA. 실행 가능한 인사이트를 빠르게 추출한다.

## Arguments
- `$ARGUMENTS` — optional: 특정 데이터셋 (e.g., "realestate", "building", "cctv", "all")

## Step 1: Data Overview

```python
import pandas as pd
import numpy as np
from pathlib import Path

data_dir = Path('data/raw')
processed_dir = Path('data/processed')

# 수집된 데이터 목록
print("=== 수집 데이터 현황 ===")
for category in sorted(data_dir.iterdir()):
    if category.is_dir():
        files = list(category.rglob('*'))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"{category.name}: {len(files)} files, {total_size/1024/1024:.1f} MB")
```

## Step 2: 실거래가 분석 (깡통전세 핵심)

```python
# 매매가 vs 전세가 매칭 가능성
# 전세가율 분포
# 동남구 vs 서북구 비교
# 단독/다가구 지번 매칭률
# 시계열 추세 (연도별 전세가율 변화)
```

핵심 지표:
- 전세가율 > 80% 비율
- 전세가율 > 90% 비율
- 동남구 vs 서북구 전세가율 평균
- 매매-전세 매칭률 (특히 단독/다가구)

## Step 3: 건축물대장 분석

```python
# 건물연령 분포 (사용승인일 기준)
# 구조별 분포 (철근콘크리트, 조적, 목조 등)
# 층수 분포
# 세대수 분포
# 반지하(지하층) 비율
```

## Step 4: 안전 데이터 분석

```python
# CCTV 밀도 (동별)
# 편의시설 밀도 (편의점/마트/세탁소)
# 병원/약국 접근성
# 대기질 (PM10/PM2.5 평균)
# 침수 이력
```

## Step 5: 공간 분석

```python
# H3 헥사곤 격자별 데이터 밀도
# 대학가(안서동) vs 신도심(불당·백석) 비교
# 동별 청년 밀집도 (SGIS 데이터)
```

## Step 6: Report

Write findings to `logs/eda_report.md`:

```markdown
# EDA Report — YYYY-MM-DD

## 데이터 수집 현황
| 카테고리 | 파일 수 | 용량 | 기간 | 품질 |
|----------|---------|------|------|------|
| 실거래가 | N | XX MB | 2006~현재 | ✓/△/✗ |
| 건축물대장 | N | XX MB | - | ✓/△/✗ |
| ... | | | | |

## 핵심 발견
1. [가장 중요한 발견]
2. [두 번째 발견]
3. [세 번째 발견]

## 깡통전세 관련
- 전세가율 > 80% 비율: XX%
- 동남구 vs 서북구 차이: ...
- 매칭률 한계: ...

## 모델링 권장
- 추천 모델: [...]
- 핵심 피처: [...]
- CV 전략: [...]
- 주의사항: [...]

## Action Items
- [ ] [첫 번째 액션]
- [ ] [두 번째 액션]
```

Then print: "EDA 완료. `/plan`으로 실험 계획을 세우세요."
