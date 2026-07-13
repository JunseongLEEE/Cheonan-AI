#!/usr/bin/env bash
# GPU 2대가 모두 비면 QLoRA 학습 시작. 실패(OOM 등) 시 다시 대기·재시도.
# 성공 시 post_train.sh(평가→머지→서빙→figure)까지 자동 실행.
# 사용: nohup setsid bash scripts/llm/wait_and_train.sh > experiments/exp_007_cheonan_llm/watcher.log 2>&1 &
set -u
cd /root/Cheonan-AI
LOG_TAG="[wait_and_train]"
EXP=experiments/exp_007_cheonan_llm
MAX_ATTEMPTS=20

echo "$LOG_TAG 감시 시작: $(date)"

attempt=0
while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  # ── 두 GPU 모두 <1000MiB 사용이 2회 연속(30초)이면 idle — 빠른 선점 ──
  consecutive=0
  while [ "$consecutive" -lt 2 ]; do
    busy=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 >= 1000 {c++} END {print c+0}')
    if [ "$busy" -eq 0 ]; then
      consecutive=$((consecutive + 1))
    else
      consecutive=0
    fi
    sleep 15
  done

  attempt=$((attempt + 1))
  echo "$LOG_TAG GPU 확보 — 학습 시도 #$attempt: $(date)"
  export HF_HOME=/opt/hf_cache
  export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
  echo "=== ATTEMPT $attempt $(date) ===" >> "$EXP/train_stdout.log"
  torchrun --nproc_per_node=2 --master_port=29617 scripts/llm/train_qlora.py \
    >> "$EXP/train_stdout.log" 2>&1
  rc=$?
  echo "$LOG_TAG 학습 종료 (exit $rc): $(date)"

  if [ "$rc" -eq 0 ]; then
    echo "TRAIN_EXIT_CODE=0" >> "$EXP/train_stdout.log"
    echo "$LOG_TAG 학습 성공 → 후처리 시작"
    bash scripts/llm/post_train.sh
    echo "$LOG_TAG 전체 완료: $(date)"
    exit 0
  fi
  echo "$LOG_TAG 실패 → GPU 재대기 (다른 작업 점유 추정)"
  sleep 60
done

echo "$LOG_TAG 최대 시도 횟수 초과 — 중단: $(date)"
exit 1
