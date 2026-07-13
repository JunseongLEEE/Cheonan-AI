---
id: pip-scripts-namespace-collision
type: lesson
created: 2026-07-08
updated: 2026-07-08
tags: [python, imports, debugging]
related: []
summary: pip 패키지가 'scripts' 네임스페이스를 선점해 프로젝트 scripts/ 하위 모듈 import 실패
---

## Symptom
`from scripts.llm.tools_schema import ...` → `ModuleNotFoundError: No module named 'scripts.llm'`
(기존 `from scripts.simulator import ...`는 정상 동작)

## Root cause
dist-packages에 `scripts`라는 이름의 외부 패키지가 설치되어 있어
(/usr/local/lib/python3.10/dist-packages/scripts) 네임스페이스 패키지 해석이 그쪽을 우선함.
기존 단일 모듈은 우연히 동작했지만 신규 서브패키지(scripts/llm)는 탐색 실패.

## Fix
`scripts/__init__.py` + `scripts/llm/__init__.py` 생성 → 정규 패키지로 승격,
sys.path 앞에 프로젝트 루트가 있으면 정규 패키지가 외부 네임스페이스보다 우선.

## Generalization
공용 이름(scripts, utils, tools)의 프로젝트 패키지는 반드시 __init__.py를 두어
정규 패키지로 만들 것. 새 서브패키지 추가 시 import 스모크 테스트를 즉시 실행.
