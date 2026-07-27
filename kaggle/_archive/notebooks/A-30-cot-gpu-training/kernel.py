#!/usr/bin/env python3
# ruff: noqa: E501
"""DueCare - Gemma 4 LoRA fine-tune on Kaggle GPU. GPU-adaptive, Gemma 4 ONLY (no Gemma 3 fallback).

Kaggle assigns either a T4 (sm_75) or a Pascal P100 (sm_60). Gemma 4 (E2B) is the Gemma 3n
architecture -- a multimodal MatFormer, not a plain text decoder -- so:

  * sm_70+ (T4 / V100): use Unsloth `FastModel`, which loads and LoRA-trains Gemma 3n natively
    (the project's proven path, as in kernel 01 / Gemma4Runtime). Needs modern torch, which Kaggle
    already ships and which supports these GPUs.
  * sm_60 (P100): modern torch / Unsloth dropped Pascal, so install a P100-compatible torch
    (2.5.1+cu121, which includes sm_60) and load Gemma 4 with the correct transformers Gemma3n class
    (`AutoModelForImageTextToText`), then LoRA the language tower and train with plain
    `transformers.Trainer` (no churny TRL).

If Gemma 4 will NOT load, the kernel FAILS LOUDLY with the exact reason (written to
gemma4_load_errors.txt) -- it never silently falls back to Gemma 3. On a P100 that cannot run
Gemma 3n, the honest recommendation is to select the "GPU T4 x2" accelerator, which uses the Unsloth
path above.

Kaggle settings (kernel-metadata.json): GPU on, Internet on, dataset
`taylorsamarel/duecare-cot-reasoning` attached. No HF token (ungated `unsloth/` mirror).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

GEMMA4 = "unsloth/gemma-4-e2b-it"  # ungated Gemma 4 E2B mirror
MAX_SEQ = 1024
MAX_STEPS = 30
TRAIN_SUBSET = 200
OUT = Path("/kaggle/working/cot_adapter")
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def _sh(cmd: list[str], timeout: int = 2400) -> None:
    print("  $", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or "")[-2500:], flush=True)
        raise SystemExit("install step failed")


def _find_train() -> tuple[Path, list[dict]]:
    inp = Path("/kaggle/input")
    print("mounted under /kaggle/input:", [p.name for p in inp.iterdir()] if inp.exists() else "none", flush=True)
    found = list(inp.rglob("cot_train.jsonl")) if inp.exists() else []
    if not found:
        raise SystemExit("cot_train.jsonl not found; attach taylorsamarel/duecare-cot-reasoning")
    train = found[0]
    rows = [json.loads(x) for x in train.read_text(encoding="utf-8").splitlines() if x.strip()][:TRAIN_SUBSET]
    hold_path = train.with_name("cot_holdout.jsonl")
    hold = [json.loads(x) for x in hold_path.read_text(encoding="utf-8").splitlines() if x.strip()][:1] if hold_path.exists() else []
    print(f"training data: {train} | rows {len(rows)} | holdout {len(hold)}", flush=True)
    return train, (rows, hold)


def _save_evidence(chosen: str, diag: str, dt: float, loss: float, before: str, after: str, n: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "run_evidence.json").write_text(json.dumps({
        "model": chosen, "gpu": diag, "path": "unsloth" if "unsloth-fastmodel" in chosen else "transformers",
        "train_rows": n, "steps": MAX_STEPS, "final_loss": round(float(loss), 4), "seconds": round(dt, 1),
        "before_chars": len(before), "after_chars": len(after), "behaviour_changed": before.strip() != after.strip(),
        "not_demonstrated": ["general legal quality", "real-world outcomes", "production readiness"],
    }, indent=2), encoding="utf-8")
    print(f"\nadapter + evidence saved -> {OUT} (model={chosen})", flush=True)
    print("DONE - Gemma 4 GPU training complete.", flush=True)


def run_unsloth(rows: list[dict], hold: list[dict], diag: str) -> None:
    """T4 / V100 path: Unsloth FastModel loads + LoRA-trains Gemma 4 (Gemma 3n) natively."""
    print("[path] sm_70+ -> Unsloth FastModel (Gemma 4 native)", flush=True)
    pip = [sys.executable, "-m", "pip", "install", "-q", "--no-input", "--disable-pip-version-check"]
    _sh(pip + ["torch>=2.8.0", "triton>=3.4.0", "torchvision", "bitsandbytes", "unsloth",
               "unsloth_zoo>=2026.4.6", "transformers==5.5.0", "timm", "datasets", "trl", "peft", "accelerate"])
    import torch
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template, train_on_responses_only

    model, tokenizer = FastModel.from_pretrained(model_name="unsloth/gemma-4-E2B-it", dtype=None,
                                                 max_seq_length=MAX_SEQ, load_in_4bit=True, full_finetuning=False)
    for tmpl in ("gemma-4-thinking", "gemma-3", "gemma"):
        try:
            tokenizer = get_chat_template(tokenizer, chat_template=tmpl); break
        except Exception:
            continue

    def gen(u: str) -> str:
        FastModel.for_inference(model)
        ids = tokenizer.apply_chat_template([{"role": "user", "content": u}], add_generation_prompt=True, return_tensors="pt").to("cuda")
        out = model.generate(input_ids=ids, max_new_tokens=180, temperature=1.0, top_p=0.95, top_k=64)
        return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    probe = hold[0]["messages"][0]["content"] if hold else None
    before = gen(probe) if probe else ""
    print("\n--- BEFORE ---\n", before[:700], flush=True)
    FastModel.for_training(model)
    model = FastModel.get_peft_model(model, r=16, lora_alpha=16, lora_dropout=0.0, bias="none",
                                     target_modules=TARGET_MODULES, use_gradient_checkpointing="unsloth", random_state=3407)
    from datasets import Dataset
    ds = Dataset.from_dict({"text": [tokenizer.apply_chat_template(r["messages"], tokenize=False) for r in rows]})
    trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=SFTConfig(
        dataset_text_field="text", per_device_train_batch_size=1, gradient_accumulation_steps=4, warmup_steps=5,
        max_steps=MAX_STEPS, learning_rate=2e-4, logging_steps=1, optim="adamw_8bit", weight_decay=0.01,
        lr_scheduler_type="linear", seed=3407, output_dir="/kaggle/working/trainer", report_to="none",
        fp16=not torch.cuda.is_bf16_supported(), bf16=torch.cuda.is_bf16_supported()))
    trainer = train_on_responses_only(trainer, instruction_part="<start_of_turn>user\n", response_part="<start_of_turn>model\n")
    t0 = time.time(); stats = trainer.train(); dt = time.time() - t0
    after = gen(probe) if probe else ""
    print("\n--- AFTER ---\n", after[:700], flush=True)
    model.save_pretrained(str(OUT)); tokenizer.save_pretrained(str(OUT))
    _save_evidence("unsloth/gemma-4-E2B-it [unsloth-fastmodel]", diag, dt, stats.training_loss, before, after, len(rows))


def run_transformers_p100(rows: list[dict], hold: list[dict], diag: str) -> None:
    """P100 path: P100-compatible torch + Gemma3n class + plain transformers Trainer (no TRL)."""
    print("[path] sm_60 (P100) -> transformers Gemma3n (no Unsloth)", flush=True)
    pip = [sys.executable, "-m", "pip", "install", "-q", "--no-input", "--disable-pip-version-check"]
    _sh(pip + ["torch==2.5.1", "torchvision==0.20.1", "--index-url", "https://download.pytorch.org/whl/cu121"])
    _sh(pip + ["transformers>=4.53", "peft", "datasets", "accelerate", "sentencepiece"])
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], capture_output=True, text=True)

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer,
                              DataCollatorForLanguageModeling, Trainer, TrainingArguments)

    tokenizer = AutoTokenizer.from_pretrained(GEMMA4)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Gemma 4 == Gemma 3n: it registers as image-text-to-text, not causal-LM. Try that class first.
    model, chosen, errs = None, None, []
    for cls_name, loader in (("AutoModelForImageTextToText", AutoModelForImageTextToText),
                             ("AutoModelForCausalLM", AutoModelForCausalLM)):
        try:
            print(f"loading Gemma 4 ({GEMMA4}) via {cls_name} ...", flush=True)
            model = loader.from_pretrained(GEMMA4, torch_dtype=torch.float16, device_map="auto")
            chosen = f"{GEMMA4} [{cls_name}]"
            print(f"loaded {chosen}", flush=True)
            break
        except Exception as exc:  # noqa: BLE001 - record the real reason for the loud failure below
            errs.append(f"{cls_name}: {type(exc).__name__}: {exc}")
            print(f"  {cls_name} failed: {exc}", flush=True)
    if model is None:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "gemma4_load_errors.txt").write_text("\n".join(errs), encoding="utf-8")
        raise SystemExit("Gemma 4 (gemma-4-e2b) could NOT load on this P100 via any class. Reasons:\n"
                         + "\n".join(errs) + "\n\nFor reliable Gemma 4, select the GPU T4 x2 accelerator (Unsloth path).")

    def gen(u: str) -> str:
        enc = tokenizer.apply_chat_template([{"role": "user", "content": u}], add_generation_prompt=True,
                                            return_tensors="pt", return_dict=True)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        n = enc["input_ids"].shape[1]
        out = model.generate(**enc, max_new_tokens=180, do_sample=True, temperature=1.0, top_p=0.95)
        return tokenizer.decode(out[0][n:], skip_special_tokens=True)

    probe = hold[0]["messages"][0]["content"] if hold else None
    before = gen(probe) if probe else ""
    print("\n--- BEFORE (base Gemma 4) ---\n", before[:700], flush=True)

    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=16, lora_dropout=0.0, bias="none",
                                             task_type="CAUSAL_LM", target_modules=TARGET_MODULES))
    model.print_trainable_parameters()

    def tok_fn(r: dict) -> dict:
        text = tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)
        return tokenizer(text, truncation=True, max_length=MAX_SEQ)

    ds = Dataset.from_list(rows).map(tok_fn, remove_columns=list(rows[0].keys()))
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    args = TrainingArguments(output_dir="/kaggle/working/trainer", per_device_train_batch_size=1,
                             gradient_accumulation_steps=4, warmup_steps=5, max_steps=MAX_STEPS, learning_rate=2e-4,
                             logging_steps=1, optim="adamw_torch", weight_decay=0.01, lr_scheduler_type="linear",
                             seed=3407, fp16=True, report_to="none", gradient_checkpointing=True)
    trainer = Trainer(model=model, args=args, train_dataset=ds, data_collator=collator)
    t0 = time.time(); stats = trainer.train(); dt = time.time() - t0
    after = gen(probe) if probe else ""
    print("\n--- AFTER (Gemma 4 + adapter) ---\n", after[:700], flush=True)
    model.save_pretrained(str(OUT)); tokenizer.save_pretrained(str(OUT))
    _save_evidence(chosen, diag, dt, stats.training_loss, before, after, len(rows))


def main() -> None:
    print("=" * 76, flush=True)
    print("DueCare Gemma 4 LoRA fine-tune - GPU-adaptive - Kaggle GPU", flush=True)
    print("=" * 76, flush=True)
    import torch as _bt  # Kaggle base torch, to detect the GPU BEFORE choosing the install path
    if not _bt.cuda.is_available():
        raise SystemExit("No CUDA GPU. In Kaggle set Settings -> Accelerator -> GPU.")
    cc = _bt.cuda.get_device_capability(0)
    diag = f"GPU={_bt.cuda.get_device_name(0)} sm_{cc[0]}{cc[1]} base_torch={_bt.__version__}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diag.txt").write_text(diag, encoding="utf-8")
    print(diag, flush=True)
    _, (rows, hold) = _find_train()
    if cc[0] >= 7:
        run_unsloth(rows, hold, diag)
    else:
        run_transformers_p100(rows, hold, diag)


if __name__ == "__main__":
    import traceback
    try:
        main()
    except BaseException as exc:  # noqa: BLE001 - capture any failure to a downloadable file
        tb = traceback.format_exc()
        print("\n!!! KERNEL ERROR !!!\n" + tb, flush=True)
        try:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n\n{tb}", encoding="utf-8")
        except Exception:
            Path("/kaggle/working/error.txt").write_text(tb, encoding="utf-8")
        raise
