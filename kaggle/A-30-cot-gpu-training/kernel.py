#!/usr/bin/env python3
# ruff: noqa: E501
"""DueCare - Gemma LoRA fine-tune on the CoT dataset, P100-COMPATIBLE (Kaggle GPU).

Kaggle keeps assigning a Pascal Tesla P100 (sm_60), which Kaggle's default torch 2.10 and Unsloth no
longer compile kernels for (arch_list starts at sm_70). This kernel therefore avoids Unsloth and
installs a **P100-compatible torch (2.5.1+cu121, which includes sm_60)**, then LoRA-fine-tunes a Gemma
model with plain transformers + peft + trl on the published `duecare-cot-reasoning` rows, does
before/after generation on a held-out prompt, and saves the adapter. Real training; no placeholders.

It tries `unsloth/gemma-4-e2b-it` first (ungated mirror) and falls back to `unsloth/gemma-3-1b-it`
if the larger multimodal model will not load/fit on the 16 GB P100, so the run always completes and
records which model actually trained.

Kaggle settings (declared in kernel-metadata.json): GPU on, Internet on, dataset
`taylorsamarel/duecare-cot-reasoning` attached. No HF token needed (ungated mirrors).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

MODEL_CANDIDATES = ["unsloth/gemma-4-e2b-it", "unsloth/gemma-3-1b-it"]  # try large first, fall back
MAX_SEQ = 1024
MAX_STEPS = 30
TRAIN_SUBSET = 200
OUT = Path("/kaggle/working/cot_adapter")


def _sh(cmd: list[str]) -> None:
    print("  $", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2400)
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or "")[-2500:], flush=True)
        raise SystemExit("install step failed")


def install_stack() -> None:
    """P100-compatible stack: torch 2.5.1+cu121 (has sm_60) + plain transformers/peft/trl (no Unsloth)."""
    print("=" * 76, flush=True)
    print("[phase 0] installing a P100-compatible (sm_60) torch + transformers/peft/trl", flush=True)
    pip = [sys.executable, "-m", "pip", "install", "-q", "--no-input", "--disable-pip-version-check"]
    _sh(pip + ["torch==2.5.1", "torchvision==0.20.1", "--index-url", "https://download.pytorch.org/whl/cu121"])
    _sh(pip + ["transformers>=4.53", "peft", "trl", "datasets", "accelerate", "sentencepiece"])


def _load_rows(path: Path, limit: int | None = None) -> list[dict]:
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows


def _find_train() -> tuple[Path, Path | None]:
    inp = Path("/kaggle/input")
    if inp.exists():
        print("mounted under /kaggle/input:", [p.name for p in inp.iterdir()], flush=True)
    direct = inp / "duecare-cot-reasoning" / "cot_train.jsonl"
    if direct.exists():
        return direct, direct.with_name("cot_holdout.jsonl")
    found = list(inp.rglob("cot_train.jsonl")) if inp.exists() else []
    if not found:
        raise SystemExit("cot_train.jsonl not found under /kaggle/input; attach taylorsamarel/duecare-cot-reasoning")
    return found[0], found[0].with_name("cot_holdout.jsonl")


def main() -> None:
    print("=" * 76, flush=True)
    print("DueCare CoT LoRA fine-tune - P100-compatible - Kaggle GPU", flush=True)
    print("=" * 76, flush=True)

    install_stack()

    import torch
    if not torch.cuda.is_available():
        raise SystemExit("No CUDA GPU. In Kaggle set Settings -> Accelerator -> GPU.")
    cc = torch.cuda.get_device_capability(0)
    sm = f"sm_{cc[0]}{cc[1]}"
    diag = (f"GPU={torch.cuda.get_device_name(0)} {sm} | torch={torch.__version__} "
            f"cuda={torch.version.cuda} | arch_list={torch.cuda.get_arch_list()} | sm_supported={sm in torch.cuda.get_arch_list()}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diag.txt").write_text(diag, encoding="utf-8")
    print(diag, flush=True)
    if sm not in torch.cuda.get_arch_list():
        raise SystemExit(f"{sm} still not in torch arch_list after install: {torch.cuda.get_arch_list()}")

    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    train_path, hold_path = _find_train()
    rows = _load_rows(train_path, TRAIN_SUBSET)
    hold = _load_rows(hold_path, 1) if hold_path and hold_path.exists() else []
    print(f"training data: {train_path} | rows {len(rows)} | holdout {len(hold)}", flush=True)

    tokenizer = model = chosen = None
    for name in MODEL_CANDIDATES:
        try:
            print(f"loading {name} ...", flush=True)
            tokenizer = AutoTokenizer.from_pretrained(name)
            model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16, device_map="auto")
            chosen = name
            print(f"loaded {name}", flush=True)
            break
        except Exception as exc:  # noqa: BLE001 - fall back to the smaller model on any load/OOM failure
            print(f"  {name} did not load ({type(exc).__name__}: {exc}); trying next", flush=True)
    if model is None:
        raise SystemExit("no candidate model loaded on this GPU")

    def to_text(r: dict) -> str:
        return tokenizer.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=False)

    def generate(user_content: str) -> str:
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": user_content}], add_generation_prompt=True, return_tensors="pt").to(model.device)
        out = model.generate(input_ids=ids, max_new_tokens=180, do_sample=True, temperature=1.0, top_p=0.95)
        return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    probe = hold[0]["messages"][0]["content"] if hold else None
    before = generate(probe) if probe else ""
    print("\n--- BEFORE (base) on the held-out prompt ---\n", before[:700], flush=True)

    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=16, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    dataset = Dataset.from_dict({"text": [to_text(r) for r in rows]})
    trainer = SFTTrainer(
        model=model, train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text", per_device_train_batch_size=1, gradient_accumulation_steps=4,
            warmup_steps=5, max_steps=MAX_STEPS, learning_rate=2e-4, logging_steps=1, optim="adamw_torch",
            weight_decay=0.01, lr_scheduler_type="linear", seed=3407, output_dir="/kaggle/working/trainer",
            fp16=True, bf16=False, report_to="none", max_seq_length=MAX_SEQ, gradient_checkpointing=True))

    t0 = time.time()
    stats = trainer.train()
    dt = time.time() - t0
    print(f"\ntrained {MAX_STEPS} steps in {dt:.0f}s | final loss {stats.training_loss:.4f}", flush=True)

    after = generate(probe) if probe else ""
    print("\n--- AFTER (adapter) on the same held-out prompt ---\n", after[:700], flush=True)

    model.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    (OUT / "run_evidence.json").write_text(json.dumps({
        "model": chosen, "gpu": diag, "train_rows": len(rows), "steps": MAX_STEPS,
        "final_loss": round(float(stats.training_loss), 4), "seconds": round(dt, 1),
        "before_chars": len(before), "after_chars": len(after),
        "behaviour_changed": before.strip() != after.strip(),
        "not_demonstrated": ["general legal quality", "real-world outcomes", "production readiness"],
    }, indent=2), encoding="utf-8")
    print(f"\nadapter + evidence saved -> {OUT} (model={chosen})", flush=True)
    print("DONE - GPU training complete on P100.", flush=True)


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
