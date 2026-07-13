#!/usr/bin/env bash
# 머지 모델 재구축 + HF 업로드 체인
set -u
cd /root/Cheonan-AI
export HF_HOME=/opt/hf_cache
export HF_HUB_ENABLE_HF_TRANSFER=1
LOG_TAG="[rebuild_upload]"

echo "$LOG_TAG 1/4 베이스 모델 다운로드: $(date)"
hf download Qwen/Qwen2.5-7B-Instruct > /dev/null 2>&1 || { echo "$LOG_TAG 다운로드 실패"; exit 1; }
echo "$LOG_TAG 다운로드 완료"

echo "$LOG_TAG 2/4 LoRA 머지 (CPU): $(date)"
/opt/venv-hf/bin/python scripts/llm/merge_lora.py || { echo "$LOG_TAG 머지 실패"; exit 1; }

echo "$LOG_TAG 3/4 모델 카드 복사"
cp /tmp/claude-0/-root-Cheonan-AI/59a4bc6b-1c29-4570-bef9-ee9a79cde18e/scratchpad/README_merged.md /opt/models/cheonan-safeguard-7b/README.md

echo "$LOG_TAG 4/4 HF 업로드 (15GB): $(date)"
hf upload JunseongLEEE/cheonan-safeguard-7b /opt/models/cheonan-safeguard-7b . --repo-type model --private \
  || { echo "$LOG_TAG 업로드 실패"; exit 1; }
echo "$LOG_TAG UPLOAD_DONE: $(date)"
