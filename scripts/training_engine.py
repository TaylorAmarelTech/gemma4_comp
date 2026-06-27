#!/usr/bin/env python3
"""Phase-3 training engine -- one orchestrator for the data -> train -> eval -> register pipeline (g).

Chains the offline data-prep this session built, then the GPU train+eval, then records provenance:

  1. distill   build_lift_training_data.py   -> sft.jsonl + dpo.jsonl + manifest.json      [offline]
  2. organize  organize_training_data.py     -> {sft,dpo}_{train,heldout} (dedup + holdout) [offline]
  3. reason    build_reasoning_targets.py    -> reasoning_sft.jsonl (chain gate)            [offline]
  4. audit     audit_training_quality.py     -> quality_audit.json (overfit/shortcut guards)[offline]
  5. train     train_lift_distill.py         -> LoRA adapter                                [GPU]
  6. evaluate  four_arm_eval.py --run        -> internalisation + generalisation metrics    [GPU]
  7. register  finetune_registry.py add      -> provenance row (model_id, data sha, eval)   [offline]

The audit (step 4) runs BEFORE the GPU train so overfitting / false-pattern / fragile-fact / jurisdiction
risks are caught in the data, not after training; it fail-fasts only if the splits are missing (rc != 0),
and otherwise logs its risk flags without blocking (the corridor-coverage flag is informational).

Without a GPU (the default on this box) it runs the OFFLINE steps (1-4, 7) and SKIPS the GPU steps
(5-6) with a clear log -- so the training DATA + audit + a provenance row are produced and ready, and the
GPU steps run unchanged later in Taylor's Kaggle window (--with-gpu). --dry-run plans without executing.

Propose-only: each step is itself propose-only (writes to gitignored reports/training/); this only
sequences them, fail-fast, and writes a run log. No model and no network of its own.

    python scripts/training_engine.py               # offline steps now; GPU steps skipped (no GPU here)
    python scripts/training_engine.py --with-gpu     # also train + evaluate (Kaggle GPU host)
    python scripts/training_engine.py --dry-run      # print the plan, execute nothing
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
OUT = _ROOT / "reports" / "training" / "training_engine_plan.json"
MANIFEST = _ROOT / "reports" / "training" / "manifest.json"
ADAPTER = _ROOT / "reports" / "training" / "adapter"
DEFAULT_MODEL_ID = "duecare-gemma-4-e4b-safetyjudge-v0.1.0"
DEFAULT_BASE = "google/gemma-4-e4b-it"


def gpu_available() -> bool:
    """True if a CUDA GPU is usable (torch path), else False. Never raises (no torch / no driver -> False)."""
    try:
        import torch  # noqa: PLC0415
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


def plan(*, model_id: str, base: str, with_gpu: bool) -> list[dict[str, Any]]:
    """The ordered pipeline steps. Pure -- builds the command list and gpu-gating; executes nothing.
    GPU steps (train, evaluate) get will_run=False unless with_gpu, so an offline host still produces
    the training data + a provenance row."""
    py = sys.executable
    adapter = str(ADAPTER)
    steps: list[dict[str, Any]] = [
        {"name": "distill", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_lift_training_data.py")]},
        {"name": "organize", "gpu": False, "cmd": [py, str(_SCRIPTS / "organize_training_data.py")]},
        {"name": "reason", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_reasoning_targets.py")]},
        {"name": "audit", "gpu": False, "cmd": [py, str(_SCRIPTS / "audit_training_quality.py")]},
        {"name": "train", "gpu": True, "cmd": [py, str(_SCRIPTS / "train_lift_distill.py"), "--out", adapter]},
        {"name": "evaluate", "gpu": True,
         "cmd": [py, str(_SCRIPTS / "four_arm_eval.py"), "--run", "--adapter", adapter]},
        {"name": "register", "gpu": False,
         "cmd": [py, str(_SCRIPTS / "finetune_registry.py"), "add", "--model-id", model_id, "--base", base,
                 "--data-manifest", str(MANIFEST), "--status", ("trained" if with_gpu else "planned")]},
    ]
    for s in steps:
        s["will_run"] = with_gpu or not s["gpu"]
        s["skip_reason"] = None if s["will_run"] else "GPU required; run with --with-gpu on a GPU host"
    return steps


def run_steps(steps: list[dict], *, dry_run: bool) -> list[dict]:
    """Execute each will_run step in order (subprocess). Fail-fast: stop on the first rc != 0 so a broken
    upstream step never feeds garbage downstream. Returns a per-step result list."""
    results: list[dict] = []
    for s in steps:
        if not s["will_run"]:
            results.append({"name": s["name"], "status": "skipped", "reason": s["skip_reason"]})
            print(f"[training-engine] SKIP {s['name']}: {s['skip_reason']}")
            continue
        if dry_run:
            results.append({"name": s["name"], "status": "dry-run", "cmd": s["cmd"]})
            print(f"[training-engine] DRY-RUN {s['name']}: {' '.join(s['cmd'])}")
            continue
        print(f"[training-engine] RUN {s['name']}: {' '.join(s['cmd'])}", flush=True)
        rc = subprocess.run(s["cmd"], cwd=str(_ROOT)).returncode
        results.append({"name": s["name"], "status": ("ok" if rc == 0 else "failed"), "rc": rc})
        if rc != 0:
            print(f"[training-engine] STOP: {s['name']} failed rc={rc} (downstream steps not run)")
            break
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    ap.add_argument("--base", default=DEFAULT_BASE, help="base model ref for the registry record")
    ap.add_argument("--with-gpu", action="store_true", help="also run the GPU steps (train + evaluate)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; execute nothing")
    args = ap.parse_args(argv)

    has_gpu = gpu_available()
    with_gpu = args.with_gpu and has_gpu
    if args.with_gpu and not has_gpu:
        print("[training-engine] --with-gpu requested but no CUDA GPU detected -> offline steps only")
    steps = plan(model_id=args.model_id, base=args.base, with_gpu=with_gpu)
    results = run_steps(steps, dry_run=args.dry_run)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gpu_available": has_gpu, "with_gpu": with_gpu, "dry_run": args.dry_run,
        "model_id": args.model_id, "steps": results,
    }, indent=2) + "\n", encoding="utf-8")
    ran = [r["name"] for r in results if r["status"] in ("ok", "dry-run")]
    skipped = [r["name"] for r in results if r["status"] == "skipped"]
    failed = [r["name"] for r in results if r["status"] == "failed"]
    print(f"[training-engine] ran/planned={ran} skipped(GPU)={skipped} failed={failed} -> {OUT}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
