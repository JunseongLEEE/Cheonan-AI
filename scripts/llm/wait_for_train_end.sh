#!/usr/bin/env bash
# train_stdout.log에 TRAIN_EXIT_CODE가 찍히면 post_train.sh 실행
set -u
cd /root/Cheonan-AI
LOG=experiments/exp_007_cheonan_llm/train_stdout.log
echo "[wait_for_train_end] 감시 시작: $(date)"
while true; do
  if [ -f "$LOG" ] && grep -q "TRAIN_EXIT_CODE=" "$LOG"; then
    rc=$(grep -o "TRAIN_EXIT_CODE=[0-9]*" "$LOG" | tail -1 | cut -d= -f2)
    echo "[wait_for_train_end] 학습 종료 감지 (exit $rc): $(date)"
    if [ "$rc" = "0" ]; then
      bash scripts/llm/post_train.sh
    else
      echo "[wait_for_train_end] 학습 실패 → 후처리 생략"
    fi
    break
  fi
  sleep 120
done
