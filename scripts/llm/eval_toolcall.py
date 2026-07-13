#!/usr/bin/env python3
"""
exp_007 — Tool-Calling 정확도 평가 (베이스 vs 파인튜닝 비교)

eval.jsonl의 각 대화에서 '첫 assistant 결정 지점'을 재현:
  시스템+유저 프롬프트 → 모델 생성 → <tool_call> 파싱

지표:
  - decision_acc : 툴 호출 여부 판단 정확도 (호출해야 할 때 호출 / 말아야 할 때 직접 답변)
  - name_acc     : 호출한 툴 이름 정확도 (호출 정답 케이스 한정)
  - args_valid   : tool_call JSON 파싱 성공률
  - args_f1      : 인자 key-value 일치 F1 (수치는 ±5% 허용)

사용:
  python3 scripts/llm/eval_toolcall.py --model base
  python3 scripts/llm/eval_toolcall.py --model tuned
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HF_HOME", "/opt/hf_cache")

import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.llm.tools_schema import TOOLS  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
EXP_DIR = PROJECT_ROOT / "experiments" / "exp_007_cheonan_llm"
ADAPTER = EXP_DIR / "checkpoints" / "qlora_v1" / "final"

TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def parse_tool_call(text: str):
    """생성 텍스트에서 첫 tool_call 파싱 → (name, args) or None."""
    m = TOOL_CALL_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
        args = obj.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        return obj.get("name"), args
    except Exception:
        return "PARSE_ERROR", None


def args_match(pred: dict, gold: dict) -> tuple[int, int, int]:
    """(일치 수, pred 수, gold 수) — 수치는 ±5% 허용."""
    if not isinstance(pred, dict):
        return 0, 0, len(gold)
    hit = 0
    for k, gv in gold.items():
        if k not in pred:
            continue
        pv = pred[k]
        if isinstance(gv, (int, float)) and isinstance(pv, (int, float)):
            if abs(pv - gv) <= max(abs(gv) * 0.05, 1e-9):
                hit += 1
        elif str(pv).strip() == str(gv).strip():
            hit += 1
    return hit, len(pred), len(gold)


def first_decision(messages: list[dict]):
    """첫 assistant 턴 전까지의 프롬프트와 정답(툴콜 or 직접답변)을 반환."""
    for i, m in enumerate(messages):
        if m["role"] == "assistant":
            gold_call = None
            if m.get("tool_calls"):
                fc = m["tool_calls"][0]["function"]
                gold_call = (fc["name"], fc["arguments"])
            return messages[:i], gold_call
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["base", "tuned"], default="tuned")
    ap.add_argument("--limit", type=int, default=300)
    args = ap.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=bnb,
        torch_dtype=torch.bfloat16, device_map="cuda:0",
    )
    if args.model == "tuned":
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(ADAPTER))
    model.eval()

    convos = []
    with open(EXP_DIR / "data" / "eval.jsonl", encoding="utf-8") as f:
        for line in f:
            convos.append(json.loads(line))
    convos = convos[: args.limit]

    n = 0
    decision_hit = 0
    name_hit = name_total = 0
    valid = valid_total = 0
    f1s = []
    per_intent: dict[str, list[int]] = {}

    for c in convos:
        prompt_msgs, gold_call = first_decision(c["messages"])
        if prompt_msgs is None:
            continue
        n += 1
        ids = tokenizer.apply_chat_template(
            prompt_msgs, tools=TOOLS, tokenize=True,
            add_generation_prompt=True, return_tensors="pt",
        ).to(model.device)
        with torch.no_grad():
            out = model.generate(
                ids, max_new_tokens=256, do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        text = tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=False)
        pred = parse_tool_call(text)

        should_call = gold_call is not None
        did_call = pred is not None
        ok = should_call == did_call
        if ok:
            decision_hit += 1
        per_intent.setdefault(c["intent"], []).append(int(ok))

        if should_call and did_call:
            valid_total += 1
            if pred[0] != "PARSE_ERROR":
                valid += 1
                name_total += 1
                if pred[0] == gold_call[0]:
                    name_hit += 1
                    hit, np_, ng = args_match(pred[1], gold_call[1])
                    p = hit / np_ if np_ else 0
                    r = hit / ng if ng else 1
                    f1s.append(2 * p * r / (p + r) if p + r else 0.0)

    result = {
        "model": args.model,
        "n_eval": n,
        "decision_acc": round(decision_hit / n, 4) if n else None,
        "name_acc": round(name_hit / name_total, 4) if name_total else None,
        "args_valid_rate": round(valid / valid_total, 4) if valid_total else None,
        "args_f1": round(sum(f1s) / len(f1s), 4) if f1s else None,
        "per_intent_decision_acc": {
            k: round(sum(v) / len(v), 4) for k, v in sorted(per_intent.items())
        },
    }
    out_path = EXP_DIR / "eval" / f"toolcall_{args.model}.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
