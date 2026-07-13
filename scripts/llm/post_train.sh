#!/usr/bin/env bash
# 학습 완료 후 자동 후처리: 평가(tuned/base) → LoRA 머지 → vLLM 서빙 → 스모크 테스트 → figure
# 사용: wait_for_train_end.sh가 자동 호출
set -u
cd /root/Cheonan-AI
export HF_HOME=/opt/hf_cache
LOG_TAG="[post_train]"
EXP=experiments/exp_007_cheonan_llm

echo "$LOG_TAG 시작: $(date)"

if [ ! -d "$EXP/checkpoints/qlora_v1/final" ]; then
  echo "$LOG_TAG 어댑터 없음 — 학습 실패로 판단, 중단"
  exit 1
fi

echo "$LOG_TAG 1/6 tuned 평가"
python3 scripts/llm/eval_toolcall.py --model tuned --limit 300 \
  > "$EXP/eval/eval_tuned_stdout.log" 2>&1 || echo "$LOG_TAG tuned 평가 실패"

echo "$LOG_TAG 2/6 base 평가"
python3 scripts/llm/eval_toolcall.py --model base --limit 300 \
  > "$EXP/eval/eval_base_stdout.log" 2>&1 || echo "$LOG_TAG base 평가 실패"

echo "$LOG_TAG 3/6 LoRA 머지"
python3 scripts/llm/merge_lora.py > "$EXP/merge_stdout.log" 2>&1 || {
  echo "$LOG_TAG 머지 실패 — 중단"; exit 1; }

echo "$LOG_TAG 4/6 vLLM 서버 기동 (GPU 0)"
CUDA_VISIBLE_DEVICES=0 nohup setsid bash scripts/llm/serve.sh \
  > "$EXP/vllm_server.log" 2>&1 &

# 서버 준비 대기 (최대 10분)
for i in $(seq 1 60); do
  if curl -s http://localhost:8008/v1/models 2>/dev/null | grep -q cheonan-safeguard-7b; then
    echo "$LOG_TAG vLLM 서버 준비 완료"
    break
  fi
  sleep 10
done

echo "$LOG_TAG 5/6 엔드투엔드 스모크 테스트"
python3 scripts/llm/local_llm.py > "$EXP/e2e_smoke.log" 2>&1 || echo "$LOG_TAG 스모크 실패"

echo "$LOG_TAG 6/6 figure 렌더링"
(cd presentation/figures_src && python3 fig_15_train_loss.py && python3 fig_16_llm_eval.py) \
  > "$EXP/figures_stdout.log" 2>&1 || echo "$LOG_TAG figure 실패"

echo "$LOG_TAG 완료: $(date)"
echo "POST_TRAIN_DONE"
