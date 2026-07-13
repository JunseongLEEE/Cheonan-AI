#!/usr/bin/env bash
# 천안세이프 LLM vLLM 서빙 (GPU 0, port 8008)
# 사용: bash scripts/llm/serve.sh [모델경로]
set -e
MODEL_PATH="${1:-/opt/models/cheonan-safeguard-7b}"
export HF_HOME=/opt/hf_cache
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

exec python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name cheonan-safeguard-7b \
  --port 8008 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --disable-log-requests
