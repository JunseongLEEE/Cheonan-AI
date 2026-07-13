#!/usr/bin/env python3
"""
exp_007 — 천안 깡통전세 전문 LLM QLoRA 파인튜닝 (RTX 3090 × 2)

베이스: Qwen/Qwen2.5-7B-Instruct (한국어 우수 + 네이티브 tool-calling 템플릿)
방법: 4-bit NF4 QLoRA (r=16), assistant 턴만 loss 계산 (프롬프트/툴결과 마스킹)

실행:
  torchrun --nproc_per_node=2 scripts/llm/train_qlora.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HOME", "/opt/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from torch.utils.data import Dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.llm.tools_schema import TOOLS  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
EXP_DIR = PROJECT_ROOT / "experiments" / "exp_007_cheonan_llm"
DATA_DIR = EXP_DIR / "data"
OUT_DIR = EXP_DIR / "checkpoints" / "qlora_v1"
MAX_LEN = 2600
SEED = 42


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class ToolCallDataset(Dataset):
    """chat template 렌더링 + assistant 스팬만 라벨 유지 (디스크 캐시 지원)."""

    def __init__(self, convos: list[dict], tokenizer, cache_path: Path | None = None):
        import pickle

        self.tokenizer = tokenizer
        if cache_path is not None and cache_path.exists():
            with open(cache_path, "rb") as f:
                self.examples = pickle.load(f)
            print(f"  (캐시 로드: {cache_path.name}, {len(self.examples):,}건)")
            return

        self.examples = []
        header_ids = tokenizer("<|im_start|>assistant\n", add_special_tokens=False)["input_ids"]
        self.header_len = len(header_ids)
        skipped = 0
        for c in convos:
            ex = self._encode(c["messages"])
            if ex is None:
                skipped += 1
                continue
            self.examples.append(ex)
        if skipped:
            print(f"  (길이 초과 등으로 {skipped}건 제외)")
        if cache_path is not None and int(os.environ.get("LOCAL_RANK", 0)) == 0:
            tmp = cache_path.with_suffix(".tmp")
            with open(tmp, "wb") as f:
                pickle.dump(self.examples, f)
            tmp.rename(cache_path)
            print(f"  (캐시 저장: {cache_path.name})")

    def _render(self, messages: list[dict]) -> list[int]:
        return self.tokenizer.apply_chat_template(
            messages, tools=TOOLS, tokenize=True, add_generation_prompt=False,
        )

    def _encode(self, messages: list[dict]):
        full_ids = self._render(messages)
        if len(full_ids) > MAX_LEN:
            return None
        labels = [-100] * len(full_ids)
        # assistant 턴마다 prefix 렌더 diff로 스팬 계산
        for i, msg in enumerate(messages):
            if msg["role"] != "assistant":
                continue
            prev_ids = self._render(messages[:i])
            cur_ids = self._render(messages[:i + 1])
            start = len(prev_ids) + self.header_len  # 헤더는 마스킹 유지
            end = len(cur_ids)
            for j in range(start, min(end, len(full_ids))):
                labels[j] = full_ids[j]
        if all(l == -100 for l in labels):
            return None
        return {"input_ids": full_ids, "labels": labels}

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


def collate(batch, pad_id: int):
    max_len = max(len(b["input_ids"]) for b in batch)
    input_ids, labels, attn = [], [], []
    for b in batch:
        n = len(b["input_ids"])
        pad = max_len - n
        input_ids.append(b["input_ids"] + [pad_id] * pad)
        labels.append(b["labels"] + [-100] * pad)
        attn.append([1] * n + [0] * pad)
    return {
        "input_ids": torch.tensor(input_ids),
        "labels": torch.tensor(labels),
        "attention_mask": torch.tensor(attn),
    }


def main():
    from functools import partial

    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(SEED)
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    is_main = local_rank == 0

    # ── 공유 GPU 경합 대응: 시작 즉시 VRAM 대량 선예약 ──
    # 할당 후 del 해도 PyTorch 캐싱 할당자 풀에 남아 타 프로세스가 침범 불가.
    # 예약 실패(타 작업 선점) 시 즉시 종료 → 워처가 재대기.
    torch.cuda.set_device(local_rank)
    try:
        _reserve = torch.empty(
            int(20.0 * 1024 ** 3) // 2, dtype=torch.bfloat16,
            device=f"cuda:{local_rank}",
        )
        del _reserve
        print(f"[rank{local_rank}] VRAM 20GB 선예약 완료")
    except torch.OutOfMemoryError:
        print(f"[rank{local_rank}] VRAM 선예약 실패 — 타 작업 점유, 즉시 종료")
        sys.exit(2)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    # GPU 선점을 위해 모델을 '먼저' 로드한다 (공유 GPU 경합 대응).
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb,
        torch_dtype=torch.bfloat16,
        device_map={"": local_rank},
        attn_implementation="sdpa",
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    if is_main:
        model.print_trainable_parameters()

    # 모델이 GPU를 점유한 뒤 데이터 토크나이징 (첫 실행 후 캐시 재사용)
    if is_main:
        print("데이터 로드...")
    train_data = ToolCallDataset(load_jsonl(DATA_DIR / "train.jsonl"), tokenizer,
                                 cache_path=DATA_DIR / "tokcache_train.pkl")
    eval_data = ToolCallDataset(load_jsonl(DATA_DIR / "eval.jsonl"), tokenizer,
                                cache_path=DATA_DIR / "tokcache_eval.pkl")
    if is_main:
        print(f"train {len(train_data):,} / eval {len(eval_data):,}")
        lens = [len(e["input_ids"]) for e in train_data.examples]
        import numpy as np
        print(f"token len: mean {np.mean(lens):.0f}, p95 {np.percentile(lens, 95):.0f}, max {max(lens)}")

    args = TrainingArguments(
        output_dir=str(OUT_DIR),
        num_train_epochs=2,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=8,   # effective 2*8*2GPU = 32
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="epoch",
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to=[],
        seed=SEED,
        ddp_find_unused_parameters=False,
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        data_collator=partial(collate, pad_id=tokenizer.pad_token_id),
    )
    trainer.train()

    if is_main:
        trainer.save_model(str(OUT_DIR / "final"))
        tokenizer.save_pretrained(str(OUT_DIR / "final"))
        # loss history 저장 (figure용)
        with open(EXP_DIR / "train_history.json", "w", encoding="utf-8") as f:
            json.dump(trainer.state.log_history, f, ensure_ascii=False, indent=2)
        print(f"✓ 어댑터 저장: {OUT_DIR / 'final'}")


if __name__ == "__main__":
    main()
