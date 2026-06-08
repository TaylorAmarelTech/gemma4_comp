"""train_qlora_moe.py -- portable 4-bit QLoRA SFT for the MoE negative-result arms.

Unlike scripts/finetune_unsloth.py (Unsloth + Gemma E4B, needs 16GB+), this is a plain
transformers+peft+trl QLoRA trainer that runs on the local 8GB RTX 4060 (Windows) and
works for any causal LM -- the MoE (OLMoE) and the dense control (OLMo) arms in
docs/research/moe_negative_result_experiment_design.md.

The naive-vs-router-aware distinction is operationalised through --target-modules:
  * naive arm        : include the router gate + experts (routing CAN drift)
      --target-modules q_proj,k_proj,v_proj,o_proj,gate,gate_proj,up_proj,down_proj
  * router-aware arm : attention only, router/gate FROZEN (routing held)
      --target-modules q_proj,k_proj,v_proj,o_proj   (the default)

Pair with scripts/analyze_routing.py (snapshot before + after) to measure routing drift.

Usage (training venv, HF_HOME outside OneDrive):
    python scripts/train_qlora_moe.py --model allenai/OLMoE-1B-7B-0924 \
        --data data/training/train.jsonl --out reports/adapters/olmoe_naive \
        --target-modules q_proj,k_proj,v_proj,o_proj,gate --max-steps 200
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _row_to_text(o: dict, tok) -> str | None:
    """Accept the project's rows (rendered `text` or `messages`) or generic
    prompt+response / instruction+output."""
    if isinstance(o.get("text"), str) and o["text"].strip():
        return o["text"]
    msgs = o.get("messages")
    if isinstance(msgs, list) and msgs:
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        except Exception:  # noqa: BLE001
            return "\n".join(f"{m.get('role','')}: {m.get('content','')}" for m in msgs)
    p = o.get("prompt") or o.get("instruction") or o.get("input")
    r = o.get("response") or o.get("output") or o.get("completion")
    if p and r:
        try:
            return tok.apply_chat_template(
                [{"role": "user", "content": p}, {"role": "assistant", "content": r}],
                tokenize=False, add_generation_prompt=False)
        except Exception:  # noqa: BLE001
            return f"{p}\n{r}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True, help="training JSONL (text|messages|prompt+response)")
    ap.add_argument("--out", required=True, help="adapter output dir")
    ap.add_argument("--target-modules", default="q_proj,k_proj,v_proj,o_proj",
                    help="LoRA targets; add gate/experts for the naive arm")
    ap.add_argument("--max-steps", type=int, default=200)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None, help="cap training rows (smoke)")
    ap.add_argument("--no-4bit", dest="bit4", action="store_false")
    args = ap.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    rows = []
    for line in Path(args.data).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        t = _row_to_text(json.loads(line), tok)
        if t:
            rows.append({"text": t})
        if args.limit and len(rows) >= args.limit:
            break
    if not rows:
        print("no usable training rows")
        return 1
    print(f"training rows: {len(rows)}  | model: {args.model}  | 4bit: {args.bit4}")
    ds = Dataset.from_list(rows)

    load_kw: dict = {"torch_dtype": "auto"}
    if args.bit4:
        load_kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        load_kw["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(args.model, **load_kw)
    model.config.use_cache = False

    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=[m.strip() for m in args.target_modules.split(",") if m.strip()])

    cfg = SFTConfig(
        output_dir=args.out,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        max_steps=args.max_steps,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        logging_steps=1,
        save_strategy="no",
        bf16=torch.cuda.is_available(),
        gradient_checkpointing=True,
        max_length=args.max_len,
        report_to=[],
        dataset_text_field="text",
    )
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=lora)
    trainer.train()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(out))
    tok.save_pretrained(str(out))
    print(f"saved adapter -> {out}  (targets: {args.target_modules})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
