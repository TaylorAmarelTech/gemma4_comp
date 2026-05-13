# <!-- duecare:kernel-intro -->
# DueCare — PrivacyRedactor LoRA fine-tune + eval
# Appendix notebook #A12 of 24 in the DueCare submission.
#
# Trains a Gemma 4 LoRA adapter (PrivacyRedactor) on A-10's synthetic
# composite intake + gold redaction plans, then benchmarks stock vs
# fine-tuned on a held-out split. Optional HF Hub push.
#
# What to look for after Run All:
#   - Open the printed cloudflared URL; summary tiles show training
#     loss + stock-vs-fine-tuned redaction accuracy delta.
#   - LoRA adapter saved to /kaggle/working/pii-redactor-<variant>-v1/.
#   - Eval bundle.zip downloads include the eval JSON + metadata.
#
# Demo path: Attach A-10 PII bundle as Kaggle Dataset -> Run All ->
# adapter trains in ~10 min on T4 -> push to HF Hub if HF_TOKEN set.
#
# Full README + cross-kernel index: see the README in this folder.

"""
============================================================================
  DUECARE A-12 PRIVACYREDACTOR FINE-TUNE + EVAL -- Kaggle notebook
============================================================================

  Per Taylor's 2026-05-11 experiment-ladder spec, A-11 trains the
  PrivacyRedactor LoRA adapter and benchmarks it against stock Gemma
  on a held-out PII redaction set.

  Pipeline:
    1. Install DueCare from GitHub (no Kaggle wheel datasets)
    2. Install Unsloth stack (FastModel + peft + trl SFT trainer)
    3. Load Gemma 4 base (default e2b-it for fast iteration)
    4. Discover A-10 gold JSONL files under /kaggle/input
    5. Split 80/20 train/holdout
    6. SFT train the LoRA adapter
    7. Eval: stock vs fine-tuned redaction label F1 on holdout
    8. Save adapter to /kaggle/working/pii-redactor-<variant>-v1/
    9. Optional HF Hub push if HF_TOKEN env present
   10. Workbench shell with eval summary + downloads

  Output: /kaggle/working
    pii-redactor-<variant>-v1/         LoRA adapter directory
    <run_id>_eval.json                  per-row + aggregate eval
    <run_id>_metadata.json              training config + duration
    <run_id>_bundle.zip                 manifest + eval + metadata

  Run-ID format: a11_pii_finetune_{variant}_{iso_ts}

  Requirements:
    - GPU: T4 (e2b-it default fits in 16GB 4-bit)
    - Internet: ON
    - Required Kaggle Dataset: attach A-10's PII bundle
    - Optional: HF_TOKEN secret for adapter push to
      TaylorScottAmarel/duecare-gemma-4-<variant>-pii-redactor-v1

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
GEMMA_MODEL_VARIANT = os.environ.get("DUECARE_GEMMA_VARIANT", "e2b-it")
GEMMA_LOAD_IN_4BIT  = True
GEMMA_MAX_SEQ_LEN   = 2048
PORT                = 8080
TUNNEL              = "cloudflared"

SFT_MAX_STEPS       = int(os.environ.get("DUECARE_SFT_MAX_STEPS", "200"))
SFT_LR              = float(os.environ.get("DUECARE_SFT_LR", "2e-4"))
SFT_BATCH_SIZE      = int(os.environ.get("DUECARE_SFT_BATCH", "2"))
SFT_GRAD_ACCUM      = int(os.environ.get("DUECARE_SFT_GRAD_ACCUM", "4"))
EVAL_HOLDOUT_PCT    = float(os.environ.get("DUECARE_HOLDOUT_PCT", "0.2"))
EVAL_MAX_HOLDOUT    = int(os.environ.get("DUECARE_EVAL_MAX_HOLDOUT", "50"))

HF_HUB_PUSH         = bool(int(os.environ.get("DUECARE_HF_PUSH", "1") or "1"))
HF_HUB_REPO         = os.environ.get(
    "DUECARE_HF_REPO",
    f"TaylorScottAmarel/duecare-gemma-4-{GEMMA_MODEL_VARIANT}-pii-redactor-v1",
)

OUTPUT_DIR  = Path("/kaggle/working")
ADAPTER_DIR = OUTPUT_DIR / f"pii-redactor-{GEMMA_MODEL_VARIANT}-v1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 0 -- Unsloth stack install
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_pii_finetune_unsloth_done")


def _install_unsloth_stack() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    if subprocess.run(["uv", "--version"],
                        capture_output=True).returncode == 0:
        installer = ["uv", "pip", "install", "-qqq", "--system"]
    else:
        installer = [sys.executable, "-m", "pip", "install",
                       "-q", "--no-input", "--disable-pip-version-check"]
    cmd = installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin,
        "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6",
        "transformers==5.5.0", "torchcodec", "timm",
        "trl>=0.12.0", "peft>=0.13.0", "datasets>=2.14.0",
    ]
    print(f"  $ {' '.join(cmd[:6])} ... (truncated)")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  INSTALL FAILED ({proc.returncode}): "
              f"{proc.stderr[-600:]}")
        return False
    print(f"  + Unsloth stack installed in {time.time() - t0:.0f}s")
    try:
        _UNSLOTH_MARKER.write_text(json.dumps(
            {"variant": GEMMA_MODEL_VARIANT,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    except Exception:
        pass
    return True


if _UNSLOTH_MARKER.exists():
    print("[phase 0] Unsloth marker present; skipping install")
    _UNSLOTH_OK = True
else:
    _UNSLOTH_OK = _install_unsloth_stack()


# ===========================================================================
# PHASE 1 -- DueCare from GitHub
# ===========================================================================
DUECARE_VERSION    = "0.1.0"
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES   = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    print("=" * 76)
    print("[install] DueCare packages from GitHub (no Kaggle wheel datasets)")
    print("=" * 76)
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for i, pkg in enumerate(DUECARE_PACKAGES, 1):
        wheel_name = (f"{pkg.replace('-', '_')}-{DUECARE_VERSION}"
                      f"-py3-none-any.whl")
        url = f"{base_url}/{wheel_name}"
        print(f"  > [{i}/{len(DUECARE_PACKAGES)}] release wheel: {wheel_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60", url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode == 0:
            success += 1
            print(f"  + installed {pkg} from release v{DUECARE_VERSION}")
        else:
            tail = (proc.stderr or "")[-200:]
            if "404" in tail or "Not Found" in tail:
                print(f"  - release wheel not found, falling back to source")
                break
            print(f"  - {pkg} release wheel failed: {tail}")
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}"
        for p in DUECARE_PACKAGES
    ]
    print(f"  > source install @ {DUECARE_COMMIT_SHA}")
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode == 0:
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        print(f"  + source install ok @ {DUECARE_COMMIT_SHA}")
        return True
    raise SystemExit(
        f"DueCare GitHub install failed: {(proc.stderr or '')[-300:]}")


print("\n" + "=" * 76)
print("[1/6] installing DueCare from GitHub")
print("=" * 76)
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-11-pii-fine-tune-eval")
except Exception:
    def dc_log(*a, **kw): return None  # type: ignore[no-redef]
    def set_kernel_id(*a, **kw): return None  # type: ignore[no-redef]


# ===========================================================================
# 2. DISCOVER A-10 GOLD JSONL FROM ATTACHED DATASETS
# ===========================================================================
print("\n" + "=" * 76)
print("[2/6] discovering A-10 PII gold JSONL files")
print("=" * 76)


def _find_gold_jsonl() -> list[Path]:
    roots = [Path("/kaggle/input")]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*_pii_gold.jsonl"):
            if p.is_file():
                found.append(p)
        for p in root.rglob("pii_gold.jsonl"):
            if p.is_file():
                found.append(p)
    return sorted(set(found))


_gold_paths = _find_gold_jsonl()
if not _gold_paths:
    raise SystemExit(
        "No A-10 *_pii_gold.jsonl found under /kaggle/input.\n"
        "Attach the A-10 bundle (kaggle/A-09-chat-playground-with-"
        "agentic-research/) as a Kaggle Dataset, then re-run.")

print(f"  found {len(_gold_paths)} gold JSONL file(s):")
for _p in _gold_paths:
    print(f"    {_p}")

_all_rows: list[dict] = []
for _p in _gold_paths:
    with _p.open("r", encoding="utf-8") as _fh:
        for _ln in _fh:
            _ln = _ln.strip()
            if not _ln:
                continue
            try:
                _row = json.loads(_ln)
            except json.JSONDecodeError:
                continue
            if "messages" in _row:
                _all_rows.append(_row)
print(f"  loaded {len(_all_rows)} composite/gold pairs")
if len(_all_rows) < 10:
    raise SystemExit(
        f"Too few gold pairs ({len(_all_rows)}) to train. Re-run A-10 "
        f"with DUECARE_N_PII_COMPOSITES=200 (or higher) first.")

import random as _random
_split_rnd = _random.Random(20260511)
_split_rnd.shuffle(_all_rows)
_split_idx = int(len(_all_rows) * (1 - EVAL_HOLDOUT_PCT))
_train_rows = _all_rows[:_split_idx]
_eval_rows = _all_rows[_split_idx:_split_idx + EVAL_MAX_HOLDOUT]
print(f"  split: {len(_train_rows)} train / {len(_eval_rows)} holdout")


# ===========================================================================
# 3. LOAD GEMMA 4 + ATTACH LoRA ADAPTER FOR TRAINING
# ===========================================================================
print("\n" + "=" * 76)
print(f"[3/6] loading Gemma 4 {GEMMA_MODEL_VARIANT} via Unsloth FastModel")
print("=" * 76)

from unsloth import FastModel
from unsloth.chat_templates import get_chat_template
import torch

_GEMMA_REPO = f"unsloth/gemma-4-{GEMMA_MODEL_VARIANT}-bnb-4bit"
_load_t0 = time.time()
model, tokenizer = FastModel.from_pretrained(
    model_name=_GEMMA_REPO,
    max_seq_length=GEMMA_MAX_SEQ_LEN,
    load_in_4bit=GEMMA_LOAD_IN_4BIT,
    dtype=None,
    full_finetuning=False,
)
print(f"  + base loaded in {time.time() - _load_t0:.0f}s")

tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")

model = FastModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=20260511,
)
print(f"  + LoRA adapter attached (r=16, alpha=16)")


# ===========================================================================
# 4. SFT TRAINING (PrivacyRedactor)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[4/6] SFT training ({SFT_MAX_STEPS} steps, lr={SFT_LR})")
print("=" * 76)

from trl import SFTTrainer, SFTConfig
from datasets import Dataset


def _format_row(example: dict) -> dict:
    text = tokenizer.apply_chat_template(
        example["messages"], tokenize=False,
        add_generation_prompt=False)
    return {"text": text}


_train_ds = Dataset.from_list(_train_rows).map(_format_row)

_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a11_pii_finetune_{GEMMA_MODEL_VARIANT}_{_run_ts}"
EVAL_PATH = OUTPUT_DIR / f"{RUN_ID}_eval.json"
META_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
print(f"  run_id: {RUN_ID}")

dc_log("a11.train.start", "PrivacyRedactor SFT beginning",
        run_id=RUN_ID, n_train=len(_train_rows), max_steps=SFT_MAX_STEPS)
_train_t0 = time.time()

_sft_args = SFTConfig(
    output_dir=str(OUTPUT_DIR / "sft_runs" / RUN_ID),
    per_device_train_batch_size=SFT_BATCH_SIZE,
    gradient_accumulation_steps=SFT_GRAD_ACCUM,
    warmup_steps=10,
    max_steps=SFT_MAX_STEPS,
    learning_rate=SFT_LR,
    logging_steps=10,
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="linear",
    seed=20260511,
    dataset_text_field="text",
    max_seq_length=GEMMA_MAX_SEQ_LEN,
    report_to="none",
    save_strategy="no",
)
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=_train_ds,
    args=_sft_args,
)
_train_stats = trainer.train()
_train_dur = time.time() - _train_t0
print(f"\n  + training complete in {_train_dur:.0f}s "
      f"(final loss={_train_stats.training_loss:.4f})")
dc_log("a11.train.done", "PrivacyRedactor SFT complete",
        run_id=RUN_ID, train_loss=float(_train_stats.training_loss),
        duration_s=int(_train_dur))


# ===========================================================================
# 5. EVAL: stock vs fine-tuned redaction accuracy on holdout
# ===========================================================================
print("\n" + "=" * 76)
print(f"[5/6] eval: stock vs fine-tuned on {len(_eval_rows)} holdout")
print("=" * 76)


def _redaction_score(predicted: str, gold: str) -> dict:
    """Smoke metric: count [LABEL] tag matches between predicted and gold.
    The production grader will score per-span correctness; this is a fast
    sanity check that fits in the eval budget."""
    import re
    gold_labels = re.findall(r"\[[A-Z_]+\]", gold)
    pred_labels = re.findall(r"\[[A-Z_]+\]", predicted)
    gold_counts: dict[str, int] = {}
    pred_counts: dict[str, int] = {}
    for label in gold_labels:
        gold_counts[label] = gold_counts.get(label, 0) + 1
    for label in pred_labels:
        pred_counts[label] = pred_counts.get(label, 0) + 1
    matched = sum(min(gold_counts.get(k, 0), pred_counts.get(k, 0))
                    for k in gold_counts)
    total = sum(gold_counts.values())
    label_recall = matched / total if total else 0.0
    label_precision = (matched / sum(pred_counts.values())
                        if pred_counts else 0.0)
    label_f1 = (2 * label_recall * label_precision /
                  (label_recall + label_precision)
                  if (label_recall + label_precision) else 0.0)
    return {
        "n_gold_labels": total,
        "n_pred_labels": sum(pred_counts.values()),
        "n_matched": matched,
        "label_recall": round(label_recall, 4),
        "label_precision": round(label_precision, 4),
        "label_f1": round(label_f1, 4),
    }


def _generate_redaction(messages_in: list[dict]) -> str:
    inputs = tokenizer.apply_chat_template(
        messages_in[:-1], add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = model.generate(
            **inputs, max_new_tokens=512,
            use_cache=True, temperature=0.0, do_sample=False)
    text = tokenizer.batch_decode(out)[0]
    if "<|turn>model" in text:
        text = text.split("<|turn>model", 1)[1]
    if "<channel|>" in text:
        text = text.split("<channel|>", 1)[1]
    text = text.split("<turn|>", 1)[0]
    return text.replace("<bos>", "").replace("<eos>", "").strip()


print(f"  scoring fine-tuned (adapter ON) on {len(_eval_rows)} prompts...")
_eval_t0 = time.time()
_finetuned_rows: list[dict] = []
for _i, _row in enumerate(_eval_rows, 1):
    _gold_text = _row["messages"][-1]["content"]
    try:
        _pred = _generate_redaction(_row["messages"])
        _score = _redaction_score(_pred, _gold_text)
        _finetuned_rows.append({
            "composite_id": _row.get("composite_id", f"eval_{_i:04d}"),
            "predicted": _pred,
            "gold": _gold_text,
            "score": _score,
        })
    except Exception as _e:
        _finetuned_rows.append({
            "composite_id": _row.get("composite_id", f"eval_{_i:04d}"),
            "predicted": "",
            "gold": _gold_text,
            "score": {"label_f1": 0.0, "error": str(_e)[:200]},
        })
    if _i % 5 == 0:
        print(f"    [{_i}/{len(_eval_rows)}] f1={_score.get('label_f1', 0):.3f}")
print(f"  fine-tuned eval done in {time.time() - _eval_t0:.0f}s")

print(f"\n  scoring stock baseline (adapter OFF) on same prompts...")
_stock_t0 = time.time()
_stock_rows: list[dict] = []
try:
    model.disable_adapter_layers()
    print("  + LoRA adapter disabled for stock eval")
except Exception as _e:
    print(f"  WARN: cannot disable adapter for stock eval ({_e})")
for _i, _row in enumerate(_eval_rows, 1):
    _gold_text = _row["messages"][-1]["content"]
    try:
        _pred = _generate_redaction(_row["messages"])
        _score = _redaction_score(_pred, _gold_text)
        _stock_rows.append({
            "composite_id": _row.get("composite_id", f"eval_{_i:04d}"),
            "predicted": _pred,
            "gold": _gold_text,
            "score": _score,
        })
    except Exception as _e:
        _stock_rows.append({
            "composite_id": _row.get("composite_id", f"eval_{_i:04d}"),
            "predicted": "",
            "gold": _gold_text,
            "score": {"label_f1": 0.0, "error": str(_e)[:200]},
        })
    if _i % 5 == 0:
        print(f"    [{_i}/{len(_eval_rows)}] f1={_score.get('label_f1', 0):.3f}")
try:
    model.enable_adapter_layers()
except Exception:
    pass
print(f"  stock eval done in {time.time() - _stock_t0:.0f}s")


def _mean(rows: list[dict], key: str) -> float:
    vals = [r["score"].get(key, 0.0) for r in rows
              if isinstance(r["score"].get(key), (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


_aggregate = {
    "n_holdout": len(_eval_rows),
    "fine_tuned": {
        "label_recall":    _mean(_finetuned_rows, "label_recall"),
        "label_precision": _mean(_finetuned_rows, "label_precision"),
        "label_f1":        _mean(_finetuned_rows, "label_f1"),
    },
    "stock": {
        "label_recall":    _mean(_stock_rows, "label_recall"),
        "label_precision": _mean(_stock_rows, "label_precision"),
        "label_f1":        _mean(_stock_rows, "label_f1"),
    },
}
_aggregate["lift"] = {
    "label_recall_pp":
        round(_aggregate["fine_tuned"]["label_recall"]
                - _aggregate["stock"]["label_recall"], 4),
    "label_precision_pp":
        round(_aggregate["fine_tuned"]["label_precision"]
                - _aggregate["stock"]["label_precision"], 4),
    "label_f1_pp":
        round(_aggregate["fine_tuned"]["label_f1"]
                - _aggregate["stock"]["label_f1"], 4),
}
print(f"\n  fine-tuned label_f1: {_aggregate['fine_tuned']['label_f1']:.4f}")
print(f"  stock      label_f1: {_aggregate['stock']['label_f1']:.4f}")
print(f"  delta:               {_aggregate['lift']['label_f1_pp']:+.4f}")


# ===========================================================================
# 6. SAVE ADAPTER + (optional) HF Hub push + emit eval bundle
# ===========================================================================
print("\n" + "=" * 76)
print(f"[6/6] saving LoRA adapter + emitting eval bundle")
print("=" * 76)

ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
try:
    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    print(f"  + adapter saved to {ADAPTER_DIR}")
except Exception as _e:
    print(f"  WARN: adapter save failed: {type(_e).__name__}: {_e}")

if HF_HUB_PUSH and (os.environ.get("HF_TOKEN")
                     or os.environ.get("HUGGINGFACE_HUB_TOKEN")):
    try:
        model.push_to_hub(HF_HUB_REPO, token=os.environ.get("HF_TOKEN"))
        tokenizer.push_to_hub(HF_HUB_REPO, token=os.environ.get("HF_TOKEN"))
        print(f"  + adapter pushed to HF Hub: {HF_HUB_REPO}")
    except Exception as _e:
        print(f"  WARN: HF Hub push failed: {type(_e).__name__}: {_e}")
else:
    print(f"  - HF Hub push skipped (no HF_TOKEN secret or DUECARE_HF_PUSH=0)")

_eval_payload = {
    "schema_version": "1.0",
    "kernel_id": "a-11-pii-fine-tune-eval",
    "run_id": RUN_ID,
    "config": {
        "model_variant": GEMMA_MODEL_VARIANT,
        "model_kind":    "pii-redactor-v1",
        "adapter_path":  str(ADAPTER_DIR),
        "hf_hub_repo":   HF_HUB_REPO if HF_HUB_PUSH else None,
        "sft": {
            "max_steps":         SFT_MAX_STEPS,
            "learning_rate":     SFT_LR,
            "batch_size":        SFT_BATCH_SIZE,
            "grad_accum_steps":  SFT_GRAD_ACCUM,
            "lora_r":            16,
            "lora_alpha":        16,
        },
        "eval": {
            "n_train":         len(_train_rows),
            "n_holdout":       len(_eval_rows),
            "holdout_pct":     EVAL_HOLDOUT_PCT,
            "max_new_tokens":  512,
            "temperature":     0.0,
        },
    },
    "metadata": {
        "started_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime(_train_t0)),
        "completed_at":     time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
        "train_duration_s": round(_train_dur, 1),
        "kaggle_kernel_id": "a-11-pii-fine-tune-eval",
        "host":             "kaggle" if Path("/kaggle").exists() else "local",
        "training_loss":    float(_train_stats.training_loss),
    },
    "summary": _aggregate,
    "aggregate": _aggregate,    # legacy alias (data_primitives.md 1.1)
    "results": (
        [{**r, "condition": "fine_tuned"} for r in _finetuned_rows]
        + [{**r, "condition": "stock"}      for r in _stock_rows]
    ),
    "results_by_condition": {        # legacy nested view; canonical is flat
        "fine_tuned": _finetuned_rows,
        "stock":      _stock_rows,
    },
}
EVAL_PATH.write_text(
    json.dumps(_eval_payload, indent=2, ensure_ascii=False),
    encoding="utf-8")
META_PATH.write_text(
    json.dumps({k: v for k, v in _eval_payload.items() if k != "results"},
                indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  + {EVAL_PATH.name}")
print(f"  + {META_PATH.name}")

with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.writestr("manifest.json", json.dumps({
        "schema_version": "1.0",
        "run_id": RUN_ID,
        "kernel_id": "a-11-pii-fine-tune-eval",
        "files": ["eval.json", "metadata.json"],
        "adapter_dir": str(ADAPTER_DIR),
    }, indent=2))
    _z.write(EVAL_PATH, "eval.json")
    _z.write(META_PATH, "metadata.json")
print(f"  + {BUNDLE_PATH.name} "
      f"({BUNDLE_PATH.stat().st_size // 1024} KB)")


# ===========================================================================
# 7. WORKBENCH SHELL UI
# ===========================================================================
print("\n" + "=" * 76)
print("[final] launching summary UI (workbench shell)")
print("=" * 76)

_SHUTDOWN_EVENT = threading.Event()
_CLOUDFLARED_PROC: dict = {"p": None}

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": (f"A-11 PrivacyRedactor LoRA "
                   f"({GEMMA_MODEL_VARIANT})"),
        "audience": "researcher",
        "lede": (f"Trained a LoRA adapter on {len(_train_rows)} A-10 "
                  f"composite intake/redaction pairs ({SFT_MAX_STEPS} "
                  f"SFT steps), then benchmarked stock vs fine-tuned "
                  f"on {len(_eval_rows)} holdout. The label_f1 lift "
                  f"is the headline number."),
        "results": [
            {"label": "Model", "value": f"{GEMMA_MODEL_VARIANT}"},
            {"label": "Train pairs", "value": str(len(_train_rows))},
            {"label": "Holdout", "value": str(len(_eval_rows))},
            {"label": "Stock label_f1",
             "value": f"{_aggregate['stock']['label_f1']:.3f}"},
            {"label": "Fine-tuned label_f1",
             "value": f"{_aggregate['fine_tuned']['label_f1']:.3f}"},
            {"label": "Lift",
             "value": f"{_aggregate['lift']['label_f1_pp']:+.3f}"},
            {"label": "Train wall time", "value": f"{_train_dur:.0f}s"},
            {"label": "Gold JSONL sources",
             "value": (
                 f"{len(_gold_paths)} file(s): "
                 + ", ".join(p.name for p in _gold_paths[:3])
                 + (" ..." if len(_gold_paths) > 3 else "")
             ) if _gold_paths else "none"},
        ],
        "artifacts": [
            {"name": BUNDLE_PATH.name, "path": str(BUNDLE_PATH)},
            {"name": EVAL_PATH.name,   "path": str(EVAL_PATH)},
            {"name": META_PATH.name,   "path": str(META_PATH)},
        ],
        "links": [
            ("Workbench (full)",
              "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
            ("Experiment ladder spec",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            f"LoRA adapter saved to {ADAPTER_DIR}.",
            (f"Pull from HF Hub: {HF_HUB_REPO}" if HF_HUB_PUSH
              else "Set HF_TOKEN secret + DUECARE_HF_PUSH=1 to push the "
                   "adapter to HF Hub on next run."),
            "Use the adapter in any A-06/A-07 baseline or harnessed "
            "runner by setting DUECARE_LORA_ADAPTER_PATH or _REPO + "
            "DUECARE_LORA_ADAPTER_SLUG=pii-redactor-v1.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-11-pii-fine-tune-eval",
        port=PORT,
    )
    if public_url:
        print(f"  ok UI available at {public_url}")
    print("\n" + "=" * 76)
    print("[done] A-11 PII FINE-TUNE + EVAL COMPLETE")
    print("=" * 76)
    if public_url:
        print(f"\n   UI:     {public_url}")
    print(f"   bundle: /kaggle/working/{BUNDLE_PATH.name}")
    print(f"   adapter: {ADAPTER_DIR}\n")
    print("=" * 76)
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutting down cleanly...")
try:
    if _CLOUDFLARED_PROC.get("p"):
        _CLOUDFLARED_PROC["p"].terminate()
except Exception:
    pass
print("  shutdown complete -- cell exiting.\n")
