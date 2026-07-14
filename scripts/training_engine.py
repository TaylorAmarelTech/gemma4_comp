#!/usr/bin/env python3
"""Phase-3 training engine -- one orchestrator for the data -> train -> eval -> register pipeline (g).

Chains the offline data-prep this session built, then the GPU train+eval, then records provenance:

  1. distill   build_lift_training_data.py   -> sft.jsonl + dpo.jsonl + manifest.json      [offline]
  2. organize  organize_training_data.py     -> {sft,dpo}_{train,heldout} (dedup + holdout) [offline]
  3. reason    build_reasoning_targets.py    -> reasoning_sft.jsonl (chain + citation gate) [offline]
  4. contract  build_contract_dpo.py          -> hard-negative DPO pairs                     [offline]
  5. dpo_mix   build_dpo_mix_variant.py       -> base+contract DPO comparison arm            [offline]
  6. gaps      build_reasoning_gap_queue.py   -> metadata-only repair queue                  [offline]
  7. repair    build_reasoning_repairs.py     -> proposed repaired reasoning SFT             [offline]
  8. variant   build_reasoning_sft_variant.py -> repaired-SFT training arm                   [offline]
 9. audit     audit_training_quality.py      -> quality_audit.json (overfit/shortcut guards)[offline]
10. corridor  build_corridor_expansion_plan.py -> metadata-only curation handoff            [offline]
11. train     train_lift_distill.py          -> LoRA adapter                                [GPU]
12. evaluate  four_arm_eval.py --run         -> internalisation + generalisation metrics    [GPU]
13. register  finetune_registry.py add       -> provenance row (model_id, data sha, eval)   [offline]

The audit (step 9) runs with --require-clean BEFORE the GPU train so overfitting / false-pattern /
fragile-fact / jurisdiction risks are caught in the data, not after training.  The GPU runner then
requires a manifest binding the selected SFT/DPO and validation/test artifacts, verifies their hashes,
proves held-out prompt and lineage isolation, and reruns the canonical package training contract before
loading any GPU dependency. Any failure prevents training, evaluation, and registration from running.

Without a GPU (the default on this box) it runs the OFFLINE data and audit steps and SKIPS the GPU steps
(11-12) with a clear log. If the strict audit passes, it also produces the corridor curation plan and
planned provenance row; otherwise it stops before those downstream steps. The GPU steps run unchanged
later in Taylor's Kaggle window (--with-gpu). --dry-run plans without executing.

Propose-only: each step is itself propose-only (writes to gitignored reports/training/); this only
sequences them, fail-fast, and writes a run log. No model and no network of its own.

    python scripts/training_engine.py               # offline steps now; GPU steps skipped (no GPU here)
    python scripts/training_engine.py --with-gpu     # also train + evaluate (Kaggle GPU host)
    python scripts/training_engine.py --with-gpu --sft-variant reasoning_repaired
    python scripts/training_engine.py --with-gpu --sft-variant reasoning_repaired_core
    python scripts/training_engine.py --with-gpu --dpo-variant contract
    python scripts/training_engine.py --with-gpu --dpo-variant base_plus_contract
    python scripts/training_engine.py --dry-run      # print the plan, execute nothing
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
TRAIN_DIR = _ROOT / "reports" / "training"
OUT = TRAIN_DIR / "training_engine_plan.json"
MANIFEST = TRAIN_DIR / "manifest.json"
SFT_TRAIN = TRAIN_DIR / "sft_train.jsonl"
SFT_REASONING_REPAIRED = TRAIN_DIR / "sft_train_reasoning_repaired.jsonl"
SFT_REASONING_REPAIRED_CORE = TRAIN_DIR / "sft_train_reasoning_repaired_core.jsonl"
DPO_TRAIN = TRAIN_DIR / "dpo_train.jsonl"
CONTRACT_DPO = TRAIN_DIR / "contract_dpo.jsonl"
DPO_TRAIN_PLUS_CONTRACT = TRAIN_DIR / "dpo_train_plus_contract.jsonl"
REASONING_GAP_QUEUE = TRAIN_DIR / "reasoning_gap_queue.json"
REASONING_GAP_QUEUE_CORE = TRAIN_DIR / "reasoning_gap_queue_core.json"
REASONING_REPAIRED = TRAIN_DIR / "reasoning_repaired_sft.jsonl"
REASONING_REPAIRED_CORE = TRAIN_DIR / "reasoning_repaired_core_sft.jsonl"
QUALITY_AUDIT = TRAIN_DIR / "quality_audit.json"
CORRIDOR_EXPANSION_PLAN = TRAIN_DIR / "corridor_expansion_plan.json"
ADAPTER = TRAIN_DIR / "adapter"
DEFAULT_MODEL_ID = "duecare-gemma-4-e4b-safetyjudge-v0.1.0"
DEFAULT_BASE = "google/gemma-4-E4B-it"
DEFAULT_BASE_REVISION = "0d5a7f9ba73eda1616e58344f7025fae44914675"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MODEL_ID = re.compile(r"^[A-Za-z0-9._\-]+$")
_PATH_FLAGS = frozenset({
    "--sft",
    "--dpo",
    "--out",
    "--audit",
    "--manifest-out",
    "--adapter",
    "--data-manifest",
    "--training-manifest",
    "--registry",
})

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from audit_training_quality import quality_audit_summary as _quality_audit_summary  # noqa: E402


def _contains_sensitive_text(value: str) -> bool:
    return bool(_EMAIL.search(value) or _PHONE.search(value) or re.search(r"\b\d{9,}\b", value))


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _contains_sensitive_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _display_model_id(model_id: Any) -> str:
    text = str(model_id or "")
    if _SAFE_MODEL_ID.fullmatch(text) and not _contains_sensitive_text(text):
        return text
    return "redacted"


def _looks_like_path(value: str) -> bool:
    try:
        if pathlib.Path(value).is_absolute():
            return True
    except (OSError, RuntimeError, ValueError):
        return False
    lowered = value.lower()
    return ("\\" in value or lowered.endswith((".exe", ".py", ".json", ".jsonl", ".md")))


def _display_cmd(cmd: list[Any]) -> list[str]:
    display: list[str] = []
    previous = ""
    for part in cmd:
        text = str(part)
        if previous == "--artifacts":
            display.append("<artifact_fingerprints_json>")
        elif previous == "--model-id":
            display.append(_display_model_id(text))
        elif previous in _PATH_FLAGS or _looks_like_path(text):
            display.append(_display_report_path(text))
        elif _contains_sensitive_text(text):
            display.append("redacted")
        else:
            display.append(text)
        previous = text
    return display


def _display_step_result(result: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in result.items():
        if key == "cmd" and isinstance(value, list):
            out["cmd"] = _display_cmd(value)
        elif key == "quality_audit":
            out[key] = value
        elif isinstance(value, str) and key == "model_id":
            out[key] = _display_model_id(value)
        elif isinstance(value, str) and (key.endswith("_path") or key in {"path", "file"}):
            out[key] = _display_report_path(value)
        else:
            out[key] = value
    return out


def gpu_available() -> bool:
    """True if a CUDA GPU is usable (torch path), else False. Never raises (no torch / no driver -> False)."""
    try:
        import torch  # noqa: PLC0415
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


def _sft_path(variant: str) -> pathlib.Path:
    if variant == "base":
        return SFT_TRAIN
    if variant == "reasoning_repaired":
        return SFT_REASONING_REPAIRED
    if variant == "reasoning_repaired_core":
        return SFT_REASONING_REPAIRED_CORE
    raise ValueError(f"unknown SFT variant: {variant}")


def _repair_mode_for_sft_variant(variant: str) -> str:
    if variant == "reasoning_repaired_core":
        return "core_remedies"
    return "default"


def _gap_queue_path(repair_mode: str) -> pathlib.Path:
    if repair_mode == "core_remedies":
        return REASONING_GAP_QUEUE_CORE
    return REASONING_GAP_QUEUE


def _repaired_rows_path(repair_mode: str) -> pathlib.Path:
    if repair_mode == "core_remedies":
        return REASONING_REPAIRED_CORE
    return REASONING_REPAIRED


def _dpo_path(variant: str) -> pathlib.Path:
    if variant == "base":
        return DPO_TRAIN
    if variant == "contract":
        return CONTRACT_DPO
    if variant == "base_plus_contract":
        return DPO_TRAIN_PLUS_CONTRACT
    raise ValueError(f"unknown DPO variant: {variant}")


def _variant_manifest_path(sft_path: pathlib.Path) -> pathlib.Path:
    return sft_path.with_name(f"{sft_path.stem}_manifest.json")


def _file_fingerprint(path: pathlib.Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    entry: dict[str, Any] = {"path": _display_report_path(path), "sha256": None, "bytes": None}
    try:
        data = path.read_bytes()
    except OSError:
        return entry
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    entry["bytes"] = len(data)
    return entry


def _registry_artifacts(
    sft_variant: str,
    dpo_variant: str,
    training_manifest: pathlib.Path | None = None,
) -> dict[str, Any]:
    sft_path = _sft_path(sft_variant)
    dpo_path = _dpo_path(dpo_variant)
    training_manifest = training_manifest or MANIFEST
    sft_manifest = _variant_manifest_path(sft_path) if sft_variant != "base" else None
    dpo_manifest = _variant_manifest_path(dpo_path) if dpo_variant != "base" else None
    repair_mode = _repair_mode_for_sft_variant(sft_variant)
    return {
        "sft_variant": sft_variant,
        "dpo_variant": dpo_variant,
        "reasoning_repair_mode": repair_mode,
        "sft_path": _display_report_path(sft_path),
        "dpo_path": _display_report_path(dpo_path),
        "training_bundle_manifest": _display_report_path(training_manifest),
        "reasoning_gap_queue_path": _display_report_path(_gap_queue_path(repair_mode)),
        "reasoning_repaired_rows_path": _display_report_path(_repaired_rows_path(repair_mode)),
        "contract_dpo_path": _display_report_path(CONTRACT_DPO),
        "contract_dpo_manifest": _display_report_path(_variant_manifest_path(CONTRACT_DPO)),
        "dpo_mix_path": _display_report_path(DPO_TRAIN_PLUS_CONTRACT),
        "dpo_mix_manifest": _display_report_path(_variant_manifest_path(DPO_TRAIN_PLUS_CONTRACT)),
        "quality_audit_path": _display_report_path(QUALITY_AUDIT),
        "corridor_expansion_plan_path": _display_report_path(CORRIDOR_EXPANSION_PLAN),
        "corridor_expansion_plan_manifest": _display_report_path(_variant_manifest_path(CORRIDOR_EXPANSION_PLAN)),
        "quality_audit_summary": _quality_audit_summary(QUALITY_AUDIT),
        "sft_variant_manifest": _display_report_path(sft_manifest) if sft_manifest is not None else None,
        "dpo_variant_manifest": _display_report_path(dpo_manifest) if dpo_manifest is not None else None,
        "artifact_files": {
            "data_manifest": _file_fingerprint(MANIFEST),
            "training_bundle_manifest": _file_fingerprint(training_manifest),
            "selected_sft": _file_fingerprint(sft_path),
            "selected_dpo": _file_fingerprint(dpo_path),
            "selected_sft_manifest": _file_fingerprint(sft_manifest),
            "selected_dpo_manifest": _file_fingerprint(dpo_manifest),
            "reasoning_gap_queue": _file_fingerprint(_gap_queue_path(repair_mode)),
            "reasoning_repaired_rows": _file_fingerprint(_repaired_rows_path(repair_mode)),
            "reasoning_repaired_rows_manifest": _file_fingerprint(_variant_manifest_path(_repaired_rows_path(repair_mode))),
            "contract_dpo": _file_fingerprint(CONTRACT_DPO),
            "contract_dpo_manifest": _file_fingerprint(_variant_manifest_path(CONTRACT_DPO)),
            "dpo_mix": _file_fingerprint(DPO_TRAIN_PLUS_CONTRACT),
            "dpo_mix_manifest": _file_fingerprint(_variant_manifest_path(DPO_TRAIN_PLUS_CONTRACT)),
            "quality_audit": _file_fingerprint(QUALITY_AUDIT),
            "corridor_expansion_plan": _file_fingerprint(CORRIDOR_EXPANSION_PLAN),
            "corridor_expansion_plan_manifest": _file_fingerprint(_variant_manifest_path(CORRIDOR_EXPANSION_PLAN)),
        },
    }


def _register_cmd(*, py: str, model_id: str, base: str, with_gpu: bool,
                  sft_variant: str, dpo_variant: str, base_revision: str = "",
                  training_manifest: pathlib.Path | None = None) -> list[str]:
    training_manifest = training_manifest or MANIFEST
    artifacts = _registry_artifacts(sft_variant, dpo_variant, training_manifest)
    artifacts["base_model_revision"] = base_revision or "unresolved"
    registry_artifacts = json.dumps(artifacts,
                                    sort_keys=True, separators=(",", ":"))
    return [py, str(_SCRIPTS / "finetune_registry.py"), "add", "--model-id", model_id, "--base", base,
            "--data-manifest", str(training_manifest), "--status", ("trained" if with_gpu else "planned"),
            "--artifacts", registry_artifacts]


def plan(
    *,
    model_id: str,
    base: str,
    with_gpu: bool,
    sft_variant: str = "base",
    dpo_variant: str = "base",
    base_revision: str = "",
    training_manifest: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """The ordered pipeline steps. Pure -- builds the command list and gpu-gating; executes nothing.
    GPU steps (train, evaluate) get will_run=False unless with_gpu, so an offline host still produces
    the training data + a provenance row."""
    py = sys.executable
    adapter = str(ADAPTER)
    train_sft = _sft_path(sft_variant)
    train_dpo = _dpo_path(dpo_variant)
    training_manifest = training_manifest or MANIFEST
    resolved_base_revision = base_revision.strip()
    if not resolved_base_revision and base == DEFAULT_BASE:
        resolved_base_revision = DEFAULT_BASE_REVISION
    repair_mode = _repair_mode_for_sft_variant(sft_variant)
    gap_queue = _gap_queue_path(repair_mode)
    repaired_rows = _repaired_rows_path(repair_mode)
    gap_cmd = [py, str(_SCRIPTS / "build_reasoning_gap_queue.py")]
    repair_cmd = [py, str(_SCRIPTS / "build_reasoning_repairs.py")]
    variant_cmd = [py, str(_SCRIPTS / "build_reasoning_sft_variant.py")]
    if repair_mode == "core_remedies":
        gap_cmd.extend(["--require-core-remedies", "--out", str(gap_queue)])
        repair_cmd.extend(["--queue", str(gap_queue), "--out", str(repaired_rows), "--require-core-remedies"])
        variant_cmd.extend(["--repaired", str(repaired_rows), "--out", str(train_sft)])
    steps: list[dict[str, Any]] = [
        {"name": "distill", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_lift_training_data.py")]},
        {"name": "organize", "gpu": False, "cmd": [py, str(_SCRIPTS / "organize_training_data.py")]},
        {"name": "reason", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_reasoning_targets.py")]},
        {"name": "contract", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_contract_dpo.py")]},
        {"name": "dpo_mix", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_dpo_mix_variant.py")]},
        {"name": "gaps", "gpu": False, "cmd": gap_cmd},
        {"name": "repair", "gpu": False, "cmd": repair_cmd},
        {"name": "variant", "gpu": False, "cmd": variant_cmd},
        {"name": "audit", "gpu": False,
         "cmd": [py, str(_SCRIPTS / "audit_training_quality.py"), "--require-clean"]},
        {"name": "corridor_plan", "gpu": False, "cmd": [py, str(_SCRIPTS / "build_corridor_expansion_plan.py")]},
        {"name": "train", "gpu": True,
         "cmd": [py, str(_SCRIPTS / "train_lift_distill.py"), "--base-model", base,
                 "--base-revision", resolved_base_revision,
                 "--sft", str(train_sft),
                 "--dpo", str(train_dpo),
                 "--training-manifest", str(training_manifest),
                 "--out", adapter]},
        {"name": "evaluate", "gpu": True,
         "cmd": [py, str(_SCRIPTS / "four_arm_eval.py"), "--run", "--base", base,
                 "--base-revision", resolved_base_revision,
                 "--adapter", adapter]},
        {"name": "register", "gpu": False,
         "cmd": _register_cmd(py=py, model_id=model_id, base=base, with_gpu=with_gpu,
                              sft_variant=sft_variant, dpo_variant=dpo_variant,
                              base_revision=resolved_base_revision,
                              training_manifest=training_manifest),
         "register_context": {"py": py, "model_id": model_id, "base": base, "with_gpu": with_gpu,
                              "sft_variant": sft_variant, "dpo_variant": dpo_variant,
                              "base_revision": resolved_base_revision,
                              "training_manifest": training_manifest}},
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
            results.append({"name": s["name"], "status": "skipped", "reason": s["skip_reason"], "cmd": s["cmd"]})
            print(f"[training-engine] SKIP {s['name']}: {s['skip_reason']}")
            continue
        if dry_run:
            if s["name"] == "register" and s.get("register_context"):
                s["cmd"] = _register_cmd(**s["register_context"])
            results.append({"name": s["name"], "status": "dry-run", "cmd": s["cmd"]})
            print(f"[training-engine] DRY-RUN {s['name']}: {' '.join(_display_cmd(s['cmd']))}")
            continue
        if s["name"] == "register" and s.get("register_context"):
            s["cmd"] = _register_cmd(**s["register_context"])
        print(f"[training-engine] RUN {s['name']}: {' '.join(_display_cmd(s['cmd']))}", flush=True)
        rc = subprocess.run(s["cmd"], cwd=str(_ROOT)).returncode
        result = {"name": s["name"], "status": ("ok" if rc == 0 else "failed"), "rc": rc}
        if s["name"] == "audit":
            summary = _quality_audit_summary(QUALITY_AUDIT)
            if summary is not None:
                result["quality_audit"] = summary
        results.append(result)
        if rc != 0:
            print(f"[training-engine] STOP: {s['name']} failed rc={rc} (downstream steps not run)")
            break
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    ap.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help="canonical base model ref used by training, evaluation, and the registry record",
    )
    ap.add_argument(
        "--base-revision",
        default="",
        help="immutable base-model commit; the canonical E4B default is pinned automatically",
    )
    ap.add_argument("--sft-variant", default="base",
                    choices=["base", "reasoning_repaired", "reasoning_repaired_core"],
                    help="SFT arm for GPU training: base uses sft_train.jsonl; reasoning_repaired uses the "
                         "default strict-contract repaired variant; reasoning_repaired_core uses the "
                         "core-remedy-enforced repaired variant generated with --require-core-remedies")
    ap.add_argument("--dpo-variant", default="base", choices=["base", "contract", "base_plus_contract"],
                    help="DPO arm for GPU training: base uses dpo_train.jsonl; contract uses the "
                         "hard-negative contract_dpo.jsonl; base_plus_contract uses the separate mixed "
                         "variant generated by build_dpo_mix_variant.py")
    ap.add_argument("--with-gpu", action="store_true", help="also run the GPU steps (train + evaluate)")
    ap.add_argument(
        "--training-manifest",
        type=pathlib.Path,
        default=None,
        help=(
            "manifest binding the selected SFT/DPO plus validation/test artifacts; the legacy generated "
            "reports/training/manifest.json is tried by default and fails closed until it meets the contract"
        ),
    )
    ap.add_argument("--dry-run", action="store_true", help="print the plan; execute nothing")
    args = ap.parse_args(argv)

    has_gpu = gpu_available()
    with_gpu = args.with_gpu and has_gpu
    if args.with_gpu and not has_gpu:
        print("[training-engine] --with-gpu requested but no CUDA GPU detected -> offline steps only")
    steps = plan(model_id=args.model_id, base=args.base, base_revision=args.base_revision, with_gpu=with_gpu,
                 sft_variant=args.sft_variant, dpo_variant=args.dpo_variant,
                 training_manifest=args.training_manifest)
    results = run_steps(steps, dry_run=args.dry_run)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gpu_available": has_gpu, "with_gpu": with_gpu, "dry_run": args.dry_run,
        "model_id": _display_model_id(args.model_id),
        "base_model_revision": (
            args.base_revision
            or (DEFAULT_BASE_REVISION if args.base == DEFAULT_BASE else "unresolved")
        ),
        "sft_variant": args.sft_variant,
        "dpo_variant": args.dpo_variant,
        "reasoning_repair_mode": _repair_mode_for_sft_variant(args.sft_variant),
        "steps": [_display_step_result(result) for result in results],
    }, indent=2) + "\n", encoding="utf-8")
    ran = [r["name"] for r in results if r["status"] in ("ok", "dry-run")]
    skipped = [r["name"] for r in results if r["status"] == "skipped"]
    failed = [r["name"] for r in results if r["status"] == "failed"]
    print(f"[training-engine] ran/planned={ran} skipped(GPU)={skipped} failed={failed} "
          f"-> {_display_report_path(OUT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
