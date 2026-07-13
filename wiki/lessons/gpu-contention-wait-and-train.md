---
id: gpu-contention-wait-and-train
type: lesson
created: 2026-07-08
updated: 2026-07-08
tags: [gpu, training, ops, exp_007]
related: [[llm-qwen25-qlora-toolcalling]]
summary: 공유 GPU 서버에서 타 작업 점유 시 kill 대신 idle-감지 자동 시작 워처 사용
---

## Symptom
torchrun 기동 시 port 29500 EADDRINUSE + 학습 즉시 실패.
nvidia-smi 확인 결과 다른 프로젝트(/root/kaggle) 학습이 GPU 2대 점유 중(19.9/23.4GB).

## Root cause
같은 머신에서 병렬로 돌던 다른 세션의 학습과 GPU·기본 rendezvous 포트 충돌.

## Fix
1. 타 작업은 죽이지 않음 (남의 진행 중 작업 파괴 금지)
2. `scripts/llm/wait_and_train.sh`: 두 GPU 메모리 <2GB가 3회 연속(3분)이면 자동 torchrun
3. nohup+setsid로 분리 실행 (Claude 백그라운드 Bash 10분 제한 회피)
4. master_port를 29617로 고정해 재충돌 방지
5. `pkill -f`는 자기 명령줄도 매칭해 self-kill 위험 → `pkill -x` 또는 PID 지정

## Generalization
공유 GPU에서는 (a) 실행 전 nvidia-smi 점유 확인, (b) 비표준 master_port 사용,
(c) 장기 작업은 detach+로그 파일+워처 패턴, (d) 타 프로세스 종료는 최후 수단.
