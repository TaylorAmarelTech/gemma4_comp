#!/usr/bin/env python3
"""Fine-tune run registry -- a provenance ledger for DueCare safety-judge adapters (backlog item f).

The hackathon's "real, not faked" invariant requires every published model number to be reproducible
from (git_sha, dataset_version). This is that ledger: one APPEND-ONLY JSONL record per fine-tune run,
linking a model_id to its base model, the EXACT training data (sha256 of the data manifest), the eval
scores, the git commit, and the export/publish artifacts -- so a reviewer can trace any published
adapter back to the data + code that produced it.

NOT to be confused with duecare.models.model_registry (which registers inference model BACKENDS); this
tracks fine-tune RUNS + their provenance. Append-only: a status change appends a new row and queries
collapse to the latest per model_id, so the full history is never destroyed. Pure stdlib; no model,
no network.

    python scripts/finetune_registry.py add --model-id duecare-gemma-4-e4b-safetyjudge-v0.1.0 \
        --base google/gemma-4-e4b-it --data-manifest reports/training/manifest.json --status trained
    python scripts/finetune_registry.py list
    python scripts/finetune_registry.py show duecare-gemma-4-e4b-safetyjudge-v0.1.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = _ROOT / "reports" / "training" / "finetune_registry.jsonl"
STATUSES = ("planned", "trained", "evaluated", "exported", "published")


def file_sha256(path: "pathlib.Path | None") -> "str | None":
    """Short sha256 of a file's bytes (the dataset-version fingerprint), or None if absent."""
    if not path:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def git_sha() -> "str | None":
    """Current repo commit (short), or None if git is unavailable -- the code-version fingerprint."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(_ROOT),
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _manifest_counts(manifest_path: "pathlib.Path | None") -> dict:
    """Pull example counts from a build_lift_training_data manifest, if present (best-effort)."""
    if not manifest_path or not manifest_path.exists():
        return {}
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: m[k] for k in ("sft_examples", "dpo_examples", "selected_pairs") if k in m}


def make_record(*, model_id: str, base_model: str, status: str, created_utc: str,
                git: "str | None" = None, data_manifest: "pathlib.Path | None" = None,
                eval_scores: "dict | None" = None, artifacts: "dict | None" = None,
                notes: str = "") -> dict[str, Any]:
    """Build one provenance record. Pure -- the caller supplies created_utc + git so it is testable."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    data = {"manifest_path": str(data_manifest) if data_manifest else None,
            "manifest_sha256": file_sha256(data_manifest), **_manifest_counts(data_manifest)}
    return {
        "model_id": model_id, "base_model": base_model, "status": status,
        "created_utc": created_utc, "git_sha": git,
        "data": data, "eval": eval_scores or {}, "artifacts": artifacts or {}, "notes": notes,
    }


def load(path: pathlib.Path = REGISTRY) -> list[dict]:
    """All records in the registry, oldest-first (append order)."""
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def append(record: dict, path: pathlib.Path = REGISTRY) -> None:
    """Append one record -- append-only, never rewrites prior history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def latest_by_id(records: list[dict]) -> dict[str, dict]:
    """The most-recent record per model_id (last write wins -- the current status of each run)."""
    out: dict[str, dict] = {}
    for r in records:
        mid = r.get("model_id")
        if mid:
            out[str(mid)] = r
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="append a fine-tune run record")
    a.add_argument("--model-id", required=True)
    a.add_argument("--base", required=True, help="base model ref (e.g. google/gemma-4-e4b-it)")
    a.add_argument("--status", default="planned", choices=STATUSES)
    a.add_argument("--data-manifest", type=pathlib.Path, default=None,
                   help="training data manifest (e.g. reports/training/manifest.json) for the dataset sha")
    a.add_argument("--eval", type=str, default=None, help="JSON of eval scores")
    a.add_argument("--artifacts", type=str, default=None, help="JSON of artifact locations (hf_repo, gguf, ...)")
    a.add_argument("--notes", default="")
    sub.add_parser("list", help="latest record per model_id")
    s = sub.add_parser("show", help="full history for one model_id")
    s.add_argument("model_id")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        rec = make_record(
            model_id=args.model_id, base_model=args.base, status=args.status,
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), git=git_sha(),
            data_manifest=args.data_manifest,
            eval_scores=json.loads(args.eval) if args.eval else None,
            artifacts=json.loads(args.artifacts) if args.artifacts else None, notes=args.notes)
        append(rec)
        print(f"[finetune-registry] +{rec['status']} {rec['model_id']} (base={rec['base_model']}, "
              f"data_sha={rec['data']['manifest_sha256']}, git={rec['git_sha']}) -> {REGISTRY}")
        return 0

    records = load()
    if args.cmd == "list":
        latest = latest_by_id(records)
        if not latest:
            print("[finetune-registry] empty -- add a run with `add`")
            return 0
        for mid, r in sorted(latest.items()):
            print(f"  {r['status']:10} {mid:46} base={r['base_model']:22} "
                  f"data_sha={(r.get('data') or {}).get('manifest_sha256')} eval={r.get('eval') or {}}")
        return 0
    if args.cmd == "show":
        hist = [r for r in records if r.get("model_id") == args.model_id]
        if not hist:
            print(f"[finetune-registry] no record for {args.model_id}")
            return 1
        print(json.dumps(hist, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
