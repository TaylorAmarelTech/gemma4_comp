#!/usr/bin/env python3
"""Phase 3 training runner -- Unsloth LoRA (SFT then DPO) on the harness-lift distilled data.

Consumes the vetted training data from build_lift_training_data.py:
  reports/training/sft.jsonl : {"messages": [user, {"role":"assistant", harnessed reply}]}
  reports/training/dpo.jsonl : {"prompt", "chosen": harnessed reply, "rejected": baseline reply}

and fine-tunes a Gemma 4 base with the canonical Unsloth recipe (FastModel -> get_peft_model ->
get_chat_template "gemma-4-thinking" -> SFTTrainer + train_on_responses_only, then an optional DPO
pass) so the model internalises the harness's stable behaviours -- arm C of the 4-arm eval in
docs/phase3_training_framework.md. The recipe mirrors the A-00 kernel's training block.

GPU-bound: the training step imports unsloth/trl/torch and needs a CUDA GPU (Kaggle T4/A100). On a
machine without them use --validate to check the data + config + plan WITHOUT the heavy deps (CPU-safe).

    python scripts/train_lift_distill.py --validate                       # CPU: check data + print plan
    python scripts/train_lift_distill.py --test-run                       # GPU: ~20-step smoke (E2B)
    python scripts/train_lift_distill.py --base-model unsloth/gemma-4-E4B-it --epochs 2   # GPU: full

Prereqs (Kaggle): pip install "unsloth" "unsloth_zoo" trl peft accelerate bitsandbytes
Design: docs/phase3_training_framework.md  .  Special Technology Track: Unsloth
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
SFT_DEFAULT = _ROOT / "reports" / "training" / "sft.jsonl"
DPO_DEFAULT = _ROOT / "reports" / "training" / "dpo.jsonl"
OUT_DEFAULT = _ROOT / "reports" / "training" / "adapter"
DEFAULT_BASE = "unsloth/gemma-4-E2B-it"   # T4-friendly proof base; use E4B for the quality run
CHAT_TEMPLATE = "gemma-4-thinking"
INSTRUCTION_PART = "<|turn>user\n"
RESPONSE_PART = "<|turn>model\n"


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


def normalize_messages(messages: list[dict]) -> list[dict]:
    """assistant->model; string content -> [{type:text,text}] (the gemma-4 chat-template shape)."""
    out: list[dict] = []
    for msg in messages:
        item = dict(msg)
        if item.get("role") == "assistant":
            item["role"] = "model"
        content = item.get("content")
        if isinstance(content, str):
            item["content"] = [{"type": "text", "text": content}]
        out.append(item)
    return out


def validate(sft: list[dict], dpo: list[dict]) -> dict[str, Any]:
    """CPU-safe schema check + stats. Returns {ok, sft_valid, dpo_valid, issues, ...}."""
    issues: list[str] = []
    sft_ok = 0
    for r in sft:
        msgs = r.get("messages") or []
        roles = [m.get("role") for m in msgs]
        if "user" in roles and ("assistant" in roles or "model" in roles) and all(m.get("content") for m in msgs):
            sft_ok += 1
    dpo_ok = 0
    for r in dpo:
        if (str(r.get("prompt", "")).strip() and str(r.get("chosen", "")).strip()
                and str(r.get("rejected", "")).strip()):
            dpo_ok += 1
    if sft and sft_ok == 0:
        issues.append("no valid SFT rows (need messages with a user + assistant turn)")
    if dpo and dpo_ok == 0:
        issues.append("no valid DPO rows (need non-empty prompt/chosen/rejected)")
    if not sft and not dpo:
        issues.append("no training data -- run scripts/build_lift_training_data.py first")
    return {"ok": not issues, "sft_rows": len(sft), "sft_valid": sft_ok,
            "dpo_rows": len(dpo), "dpo_valid": dpo_ok, "issues": issues}


def render_sft(rows: list[dict], apply_chat_template: Callable[[list[dict]], str]) -> list[dict]:
    """Render {messages} -> {text} via a chat-template fn (testable; the GPU path passes the tokenizer's)."""
    out: list[dict] = []
    for r in rows:
        msgs = normalize_messages(r.get("messages") or [])
        if not msgs:
            continue
        out.append({"text": apply_chat_template(msgs).removeprefix("<bos>")})
    return out


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """The training plan (CPU-safe; printed by --validate)."""
    return {
        "base_model": args.base_model, "chat_template": CHAT_TEMPLATE, "max_seq_length": args.max_seq,
        "lora": {"r": args.lora_r, "alpha": args.lora_alpha, "dropout": 0.0},
        "sft": {"file": str(args.sft), "epochs": (1 if args.test_run else args.epochs),
                "max_steps": (20 if args.test_run else args.max_steps),
                "per_device_batch": args.batch, "grad_accum": args.grad_accum, "lr": args.lr},
        "dpo": {"enabled": (not args.skip_dpo), "file": str(args.dpo), "beta": args.dpo_beta,
                "max_steps": (10 if args.test_run else args.dpo_max_steps), "lr": args.dpo_lr,
                "rpo_alpha": args.rpo_alpha, "max_length": args.max_seq,
                "max_prompt_length": args.max_seq // 2},
        "output_dir": str(args.out), "gguf": bool(args.gguf), "test_run": bool(args.test_run),
    }


def train(plan: dict[str, Any], sft: list[dict], dpo: list[dict]) -> str:
    """The GPU path: SFT then (optionally) DPO via Unsloth. Heavy deps imported lazily."""
    try:
        from unsloth import FastModel
        from unsloth.chat_templates import get_chat_template, train_on_responses_only
        from datasets import Dataset
        from trl import SFTTrainer, SFTConfig
        import torch
    except ImportError as exc:
        raise SystemExit(
            f"Unsloth/trl/torch not available ({exc}). The training step needs a CUDA GPU "
            "(Kaggle T4/A100). On this machine run with --validate. Install on Kaggle:\n"
            '  pip install "unsloth" "unsloth_zoo" trl peft accelerate bitsandbytes')
    import inspect

    out_dir = plan["output_dir"]
    print(f"[train] loading {plan['base_model']} (4-bit) ...", flush=True)
    model, tokenizer = FastModel.from_pretrained(
        model_name=plan["base_model"], max_seq_length=plan["max_seq_length"],
        dtype=None, load_in_4bit=True, full_finetuning=False,
    )
    lc = plan["lora"]
    model = FastModel.get_peft_model(
        model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=lc["r"], lora_alpha=lc["alpha"], lora_dropout=lc["dropout"], bias="none", random_state=42,
    )
    tokenizer = get_chat_template(tokenizer, chat_template=plan["chat_template"])
    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())

    # ---- SFT stage ----
    def _apply(msgs: list[dict]) -> str:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)

    sft_text = render_sft(sft, _apply)
    print(f"[train] SFT on {len(sft_text)} examples (bf16={bf16})", flush=True)
    s = plan["sft"]
    sft_args = SFTConfig(
        dataset_text_field="text", per_device_train_batch_size=s["per_device_batch"],
        gradient_accumulation_steps=s["grad_accum"], warmup_steps=5,
        num_train_epochs=s["epochs"], max_steps=s["max_steps"], learning_rate=s["lr"],
        fp16=not bf16, bf16=bf16, logging_steps=5, save_strategy="no", output_dir=out_dir,
        optim="adamw_8bit", weight_decay=0.001, lr_scheduler_type="linear", seed=42, report_to="none",
    )
    kw = {"model": model, "train_dataset": Dataset.from_list(sft_text), "args": sft_args}
    sig = inspect.signature(SFTTrainer.__init__)
    if "tokenizer" in sig.parameters:
        kw["tokenizer"] = tokenizer
    elif "processing_class" in sig.parameters:
        kw["processing_class"] = tokenizer
    trainer = SFTTrainer(**kw)
    trainer = train_on_responses_only(trainer, instruction_part=INSTRUCTION_PART, response_part=RESPONSE_PART)
    trainer.train()
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"[train] SFT adapter saved to {out_dir}", flush=True)

    # ---- DPO stage (prefer the harnessed reply over the baseline) ----
    d = plan["dpo"]
    if d["enabled"] and dpo:
        try:
            from trl import DPOConfig, DPOTrainer
        except ImportError:
            print("[train] trl DPOTrainer unavailable; skipping DPO", flush=True)
        else:
            def _fmt_prompt(p: str) -> str:
                return tokenizer.apply_chat_template(
                    normalize_messages([{"role": "user", "content": p}]),
                    tokenize=False, add_generation_prompt=True).removeprefix("<bos>")

            dpo_rows = [{"prompt": _fmt_prompt(str(r["prompt"])), "chosen": str(r["chosen"]),
                         "rejected": str(r["rejected"])}
                        for r in dpo if r.get("prompt") and r.get("chosen") and r.get("rejected")]
            print(f"[train] DPO on {len(dpo_rows)} pairs (beta={d['beta']})", flush=True)
            # Set max_length/max_prompt_length explicitly: trl's small default silently truncates the
            # long grounded `chosen` while the short `rejected` survives -> a pure length-bias confound.
            # Filter to the params THIS trl version's DPOConfig accepts (these + rpo_alpha vary by version).
            dpo_cfg_kw = dict(
                per_device_train_batch_size=s["per_device_batch"], gradient_accumulation_steps=s["grad_accum"],
                warmup_steps=5, max_steps=d["max_steps"], learning_rate=d["lr"], beta=d["beta"],
                fp16=not bf16, bf16=bf16, logging_steps=5, save_strategy="no",
                output_dir=out_dir + "-dpo", optim="adamw_8bit", seed=42, report_to="none",
                max_length=d["max_length"], max_prompt_length=d["max_prompt_length"],
            )
            if d.get("rpo_alpha"):
                dpo_cfg_kw["rpo_alpha"] = d["rpo_alpha"]
            _dpo_params = set(inspect.signature(DPOConfig.__init__).parameters)
            dpo_args = DPOConfig(**{k: v for k, v in dpo_cfg_kw.items() if k in _dpo_params})
            dkw = {"model": model, "args": dpo_args, "train_dataset": Dataset.from_list(dpo_rows)}
            dsig = inspect.signature(DPOTrainer.__init__)
            if "tokenizer" in dsig.parameters:
                dkw["tokenizer"] = tokenizer
            elif "processing_class" in dsig.parameters:
                dkw["processing_class"] = tokenizer
            DPOTrainer(**dkw).train()
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)
            print(f"[train] DPO-refined adapter saved to {out_dir}", flush=True)

    # ---- GGUF export for on-device (LiteRT / llama.cpp) ----
    if plan.get("gguf"):
        try:
            model.save_pretrained_gguf(out_dir + "-gguf", tokenizer, quantization_method="q4_k_m")
            print(f"[train] GGUF saved to {out_dir}-gguf", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[train] GGUF export skipped: {type(exc).__name__}: {exc}", flush=True)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-model", default=DEFAULT_BASE, help="Unsloth Gemma 4 base (E2B for T4, E4B for quality)")
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_DEFAULT)
    ap.add_argument("--dpo", type=pathlib.Path, default=DPO_DEFAULT)
    ap.add_argument("--out", type=pathlib.Path, default=OUT_DEFAULT)
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=-1, help="overrides epochs when > 0")
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=16)
    ap.add_argument("--skip-dpo", action="store_true", help="SFT only (skip the preference pass)")
    ap.add_argument("--dpo-beta", type=float, default=0.1)
    ap.add_argument("--dpo-max-steps", type=int, default=200)
    ap.add_argument("--dpo-lr", type=float, default=5e-6, help="DPO learning rate (keep < SFT --lr)")
    ap.add_argument("--rpo-alpha", type=float, default=1.0,
                    help="RPO regularizer (NLL-on-chosen inside DPO; anti-degeneration). 0 disables")
    ap.add_argument("--gguf", action="store_true", help="also export a q4_k_m GGUF for on-device")
    ap.add_argument("--test-run", action="store_true", help="GPU smoke: ~20 SFT + ~10 DPO steps")
    ap.add_argument("--validate", action="store_true",
                    help="CPU-safe: check the data + print the plan, no training")
    args = ap.parse_args(argv)

    sft = load_jsonl(args.sft)
    dpo = load_jsonl(args.dpo)
    v = validate(sft, dpo)
    plan = build_plan(args)
    print("[plan]", json.dumps(plan, indent=2))
    print("[data]", json.dumps(v, indent=2))
    if not v["ok"]:
        print("[validate] FAILED: " + "; ".join(v["issues"]))
        return 1
    if args.validate:
        print("[validate] OK -- data + plan valid. Run on a GPU (drop --validate) to train.")
        return 0
    out = train(plan, sft, dpo)
    print(f"[train] done -> {out}. Next: 4-arm eval (stock vs this adapter, harness off/on).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
