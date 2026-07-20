#!/usr/bin/env python3
# ruff: noqa: E501
"""DueCare - Gemma 4 E2B LoRA fine-tune on the chain-of-thought dataset (Kaggle GPU / T4).

Headless batch training kernel (no server, no UI): it installs the proven Unsloth training stack,
loads the published `duecare-cot-reasoning` rows, LoRA-fine-tunes gemma-4-E2B in 4-bit on the Kaggle
GPU, generates before/after on a held-out prompt, and saves the adapter + run evidence. Real,
end-to-end training - no placeholders.

Kaggle settings required (the kernel-metadata.json already declares them):
  * Accelerator = GPU (T4 x2 or P100), Internet = ON
  * Attach dataset: taylorsamarel/duecare-cot-reasoning
No Hugging Face token is needed - the Unsloth 4-bit model is ungated.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

MODEL = "unsloth/gemma-4-e2b-it"  # non-quantized; fp16 on T4 avoids the bitsandbytes 4-bit CUDA-arch mismatch
LOAD_IN_4BIT = False     # 4-bit (bitsandbytes) hit cudaErrorNoKernelImageForDevice on Kaggle T4
MAX_SEQ = 1024
MAX_STEPS = 30           # a fast, real smoke; raise for a fuller run
TRAIN_SUBSET = 200       # rows sampled from cot_train.jsonl for the smoke
DATASET_DIR = Path("/kaggle/input/duecare-cot-reasoning")
OUT = Path("/kaggle/working/cot_adapter")


def _sh(cmd: list[str]) -> None:
    print("  $", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or "")[-2500:], flush=True)
        raise SystemExit("install step failed")


def install_stack() -> None:
    """A-00's proven Gemma 4 + LoRA training stack."""
    print("=" * 76, flush=True)
    print("[phase 0] installing Gemma 4 + LoRA training stack", flush=True)
    try:
        import numpy as _np
        import PIL as _pil
        np_pin, pil_pin = f"numpy=={_np.__version__}", f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    uv = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    installer = (["uv", "pip", "install", "-qqq", "--system"] if uv.returncode == 0
                 else [sys.executable, "-m", "pip", "install", "-q", "--no-input", "--disable-pip-version-check"])
    _sh(installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin, "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6", "transformers==5.5.0", "torchcodec", "timm",
        "datasets", "trl", "peft", "accelerate",
    ])


def _load_rows(path: Path, limit: int | None = None) -> list[dict]:
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows


def main() -> None:
    print("=" * 76, flush=True)
    print("DueCare CoT LoRA fine-tune - Gemma 4 E2B - Kaggle GPU", flush=True)
    print("=" * 76, flush=True)

    install_stack()

    import torch
    if not torch.cuda.is_available():
        raise SystemExit("No CUDA GPU. In Kaggle set Settings -> Accelerator -> GPU.")
    print(f"GPU: {torch.cuda.get_device_name(0)} | torch {torch.__version__}", flush=True)

    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template, train_on_responses_only

    inp = Path("/kaggle/input")
    if inp.exists():
        print("mounted under /kaggle/input:", [p.name for p in inp.iterdir()], flush=True)
    train_path = DATASET_DIR / "cot_train.jsonl"
    if not train_path.exists():
        # the dataset may mount under a different directory name; find the file anywhere.
        found = list(inp.rglob("cot_train.jsonl")) if inp.exists() else []
        if not found:
            present = [str(p) for p in inp.rglob("*.jsonl")][:10] if inp.exists() else "nothing mounted"
            raise SystemExit(
                "cot_train.jsonl not found under /kaggle/input; attach dataset "
                f"taylorsamarel/duecare-cot-reasoning. Present jsonl: {present}")
        train_path = found[0]
    hold_path = train_path.with_name("cot_holdout.jsonl")
    print(f"training data: {train_path}", flush=True)
    rows = _load_rows(train_path, TRAIN_SUBSET)
    hold = _load_rows(hold_path, 1) if hold_path.exists() else []
    print(f"train rows: {len(rows)} (subset of the published stream) | holdout probe: {len(hold)}", flush=True)

    model, tokenizer = FastModel.from_pretrained(
        model_name=MODEL, dtype=None, max_seq_length=MAX_SEQ, load_in_4bit=LOAD_IN_4BIT, full_finetuning=False)
    print("model loaded; applying chat template", flush=True)
    for tmpl in ("gemma-4-thinking", "gemma-3", "gemma"):
        try:
            tokenizer = get_chat_template(tokenizer, chat_template=tmpl)
            print(f"chat template: {tmpl}", flush=True)
            break
        except Exception as exc:  # noqa: BLE001 - probe the available template names
            print(f"  template '{tmpl}' unavailable ({exc})", flush=True)
    else:
        raise SystemExit("no known gemma chat template available in this unsloth build")

    def generate(user_content: str) -> str:
        FastModel.for_inference(model)
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": user_content}], add_generation_prompt=True, return_tensors="pt").to("cuda")
        out = model.generate(input_ids=ids, max_new_tokens=200, temperature=1.0, top_p=0.95, top_k=64)
        return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    probe = hold[0]["messages"][0]["content"] if hold else None
    before = generate(probe) if probe else ""
    print("\n--- BEFORE (base model) on the held-out prompt ---\n", before[:700], flush=True)

    FastModel.for_training(model)
    model = FastModel.get_peft_model(
        model, r=16, lora_alpha=16, lora_dropout=0.0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407)

    def to_text(r: dict) -> str:
        return tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)

    dataset = Dataset.from_dict({"text": [to_text(r) for r in rows]})

    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=dataset, eval_dataset=None,
        args=SFTConfig(
            dataset_text_field="text", per_device_train_batch_size=1, gradient_accumulation_steps=4,
            warmup_steps=5, max_steps=MAX_STEPS, learning_rate=2e-4, logging_steps=1, optim="adamw_torch",
            weight_decay=0.01, lr_scheduler_type="linear", seed=3407, output_dir="/kaggle/working/trainer",
            fp16=not torch.cuda.is_bf16_supported(), bf16=torch.cuda.is_bf16_supported(),
            report_to="none", max_seq_length=MAX_SEQ))
    trainer = train_on_responses_only(
        trainer, instruction_part="<start_of_turn>user\n", response_part="<start_of_turn>model\n")

    t0 = time.time()
    stats = trainer.train()
    dt = time.time() - t0
    print(f"\ntrained {MAX_STEPS} steps in {dt:.0f}s | final loss {stats.training_loss:.4f}", flush=True)

    after = generate(probe) if probe else ""
    print("\n--- AFTER (with adapter) on the same held-out prompt ---\n", after[:700], flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    (OUT / "run_evidence.json").write_text(json.dumps({
        "model": MODEL, "train_rows": len(rows), "steps": MAX_STEPS,
        "final_loss": round(float(stats.training_loss), 4), "seconds": round(dt, 1),
        "before_chars": len(before), "after_chars": len(after),
        "behaviour_changed": before.strip() != after.strip(),
        "not_demonstrated": ["general legal quality", "real-world outcomes", "production readiness"],
    }, indent=2), encoding="utf-8")
    print(f"\nadapter + evidence saved -> {OUT}", flush=True)
    print("DONE - GPU training complete.", flush=True)


if __name__ == "__main__":
    # Headless Kaggle runs sometimes return an empty execution log, so capture any failure to a
    # downloadable output file (`kaggle kernels output`) with the full traceback.
    import traceback
    try:
        main()
    except BaseException as exc:  # noqa: BLE001 - we want the traceback for any failure
        tb = traceback.format_exc()
        print("\n!!! KERNEL ERROR !!!\n" + tb, flush=True)
        try:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n\n{tb}", encoding="utf-8")
        except Exception:
            Path("/kaggle/working/error.txt").write_text(tb, encoding="utf-8")
        raise
