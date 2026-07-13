#!/usr/bin/env bash
# QLoRA 학습 분리 실행 런처 (nohup용)
cd /root/Cheonan-AI
export HF_HOME=/opt/hf_cache
exec torchrun --nproc_per_node=2 --master_port=29617 scripts/llm/train_qlora.py
