#!/usr/bin/env python3
"""LoRA 어댑터를 베이스에 머지 → vLLM 서빙용 단일 모델 저장."""

import os
from pathlib import Path

os.environ.setdefault("HF_HOME", "/opt/hf_cache")

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ADAPTER = PROJECT_ROOT / "experiments" / "exp_007_cheonan_llm" / "checkpoints" / "qlora_v1" / "final"
OUT = Path("/opt/models/cheonan-safeguard-7b")

print("베이스 모델 로드 (bf16)...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.bfloat16, device_map="cpu",
)
print("어댑터 머지...")
model = PeftModel.from_pretrained(model, str(ADAPTER))
model = model.merge_and_unload()

OUT.mkdir(parents=True, exist_ok=True)
model.save_pretrained(str(OUT), safe_serialization=True)
AutoTokenizer.from_pretrained(BASE_MODEL).save_pretrained(str(OUT))
print(f"✓ 머지 완료: {OUT}")
