#!/usr/bin/env python3
"""Fine-tune Gemma 4 E4B with Unsloth for the DueCare safety judge.

This is Phase 3 of the DueCare pipeline. It takes training data
produced by prepare_training_data.py and fine-tunes Gemma 4 using
Unsloth's 2x faster LoRA implementation.

Prerequisites:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps trl peft accelerate bitsandbytes

Usage:
    # On a GPU with 16GB+ VRAM (Kaggle T4 x2, Colab A100, local 3090+)
    python scripts/finetune_unsloth.py

    # With custom config
    python scripts/finetune_unsloth.py --config configs/duecare/training/unsloth_e4b.yaml

    # Quick test (1 epoch, 10 steps)
    python scripts/finetune_unsloth.py --test-run

Special Technology Track: Unsloth ($10K)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "duecare" / "training" / "unsloth_e4b.yaml"


def load_config(config_path: Path) -> dict:
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Training config YAML")
    parser.add_argument("--test-run", action="store_true", help="Quick test: 1 epoch, 10 steps")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    print(f"Config: {args.config}")
    print(f"Base model: {cfg['base_model']}")
    print(f"Output dir: {cfg['output_dir']}")

    # ── Check dependencies ──
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: Unsloth not installed.")
        print("Install with:")
        print('  pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
        print("  pip install --no-deps trl peft accelerate bitsandbytes")
        return 1

    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
    import torch

    # ── Load model with Unsloth ──
    lora_cfg = cfg["lora"]
    train_cfg = cfg["training"]

    print(f"\nLoading {cfg['base_model']} with Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["base_model"],
        max_seq_length=train_cfg["max_seq_length"],
        dtype=torch.bfloat16 if train_cfg.get("bf16") else None,
        load_in_4bit=True,
    )

    # ── Apply LoRA ──
    print(f"Applying LoRA (r={lora_cfg['r']}, alpha={lora_cfg['alpha']})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        bias=lora_cfg["bias"],
        use_gradient_checkpointing="unsloth",
    )

    # ── Load training data ──
    ds_cfg = cfg["dataset"]
    train_path = REPO_ROOT / ds_cfg["train_file"]
    val_path = REPO_ROOT / ds_cfg["val_file"]

    if not train_path.exists():
        print(f"ERROR: {train_path} not found. Run scripts/prepare_training_data.py first.")
        return 1

    def load_jsonl(path: Path) -> Dataset:
        examples = [json.loads(line) for line in path.open("r", encoding="utf-8")]
        return Dataset.from_list(examples)

    train_ds = load_jsonl(train_path)
    val_ds = load_jsonl(val_path) if val_path.exists() else None

    print(f"Train: {len(train_ds)} examples")
    if val_ds:
        print(f"Val:   {len(val_ds)} examples")

    # ── Training arguments ──
    output_dir = REPO_ROOT / cfg["output_dir"]

    if args.test_run:
        max_steps = 10
        num_epochs = 1
        save_steps = 5
        eval_steps = 5
        logging_steps = 1
    else:
        max_steps = -1
        num_epochs = train_cfg["num_epochs"]
        save_steps = train_cfg["save_steps"]
        eval_steps = train_cfg["eval_steps"]
        logging_steps = train_cfg["logging_steps"]

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        max_steps=max_steps,
        per_device_train_batch_size=train_cfg["per_device_batch_size"],
        gradient_accumulation_steps=train_cfg["gradient_accumulation_steps"],
        learning_rate=train_cfg["learning_rate"],
        weight_decay=train_cfg["weight_decay"],
        warmup_ratio=train_cfg["warmup_ratio"],
        lr_scheduler_type=train_cfg["lr_scheduler"],
        fp16=train_cfg.get("fp16", False),
        bf16=train_cfg.get("bf16", True),
        logging_steps=logging_steps,
        save_strategy=train_cfg.get("save_strategy", "steps"),
        save_steps=save_steps,
        eval_strategy=train_cfg.get("eval_strategy", "steps") if val_ds else "no",
        eval_steps=eval_steps if val_ds else None,
        optim=train_cfg.get("optim", "adamw_8bit"),
        report_to="none",
        seed=42,
    )

    # ── Train ──
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=train_cfg["max_seq_length"],
        packing=False,
    )

    print(f"\nStarting training...")
    print(f"  Epochs: {num_epochs}")
    print(f"  Batch size: {train_cfg['per_device_batch_size']} x {train_cfg['gradient_accumulation_steps']} = {train_cfg['per_device_batch_size'] * train_cfg['gradient_accumulation_steps']}")
    print(f"  Learning rate: {train_cfg['learning_rate']}")
    print(f"  Output: {output_dir}")

    result = trainer.train()
    print(f"\nTraining complete.")
    print(f"  Loss: {result.training_loss:.4f}")
    print(f"  Steps: {result.global_step}")

    # ── Save ──
    print(f"\nSaving to {output_dir}...")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # ── Export to GGUF ──
    export_cfg = cfg.get("export", {})
    gguf_cfg = export_cfg.get("gguf", {})
    if gguf_cfg.get("enabled", False):
        gguf_dir = REPO_ROOT / gguf_cfg["output_dir"]
        gguf_dir.mkdir(parents=True, exist_ok=True)
        for quant in gguf_cfg.get("quantizations", ["Q4_K_M"]):
            print(f"\nExporting GGUF ({quant})...")
            model.save_pretrained_gguf(
                str(gguf_dir / f"duecare-gemma4-e4b-{quant.lower()}"),
                tokenizer,
                quantization_method=quant.replace("_", "").lower(),
            )
            print(f"  Saved: {gguf_dir / f'duecare-gemma4-e4b-{quant.lower()}'}")

    # ── Push to HF Hub ──
    hf_cfg = export_cfg.get("hf_hub", {})
    if hf_cfg.get("enabled", False):
        repo_id = hf_cfg["repo_id"]
        print(f"\nPushing to HuggingFace Hub: {repo_id}...")
        model.push_to_hub(repo_id, private=hf_cfg.get("private", True))
        tokenizer.push_to_hub(repo_id, private=hf_cfg.get("private", True))
        print(f"  Pushed: https://huggingface.co/{repo_id}")

    print("\nDone. Next: run evaluation to compare stock vs fine-tuned.")
    print(f"  python scripts/run_local_gemma.py --model {output_dir} --graded-only")

    return 0


if __name__ == "__main__":
    sys.exit(main())
