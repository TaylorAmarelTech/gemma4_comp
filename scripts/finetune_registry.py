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
    python scripts/finetune_registry.py verify duecare-gemma-4-e4b-safetyjudge-v0.1.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = _ROOT / "reports" / "training" / "finetune_registry.jsonl"
STATUSES = ("planned", "trained", "evaluated", "exported", "published")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(r"(?i)(?:^[A-Za-z]:[\\/]|[\\/]Users[\\/]|[\\/]home[\\/]|[\\/]tmp[\\/])")
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MODEL_ID = re.compile(r"^[A-Za-z0-9._\-]+$")
_SAFE_FIELD_KEY = re.compile(r"^[A-Za-z0-9_. \-]{1,80}$")
_SAFE_HASHLIKE = re.compile(r"^[0-9a-fA-F]{7,128}$")
_SAFE_CREATED_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_PATH_KEYS = frozenset({
    "path",
    "manifest_path",
    "sft_path",
    "dpo_path",
    "contract_dpo_path",
    "contract_dpo_manifest",
    "dpo_mix_path",
    "dpo_mix_manifest",
    "quality_audit_path",
    "corridor_expansion_plan_path",
    "corridor_expansion_plan_manifest",
    "sft_variant_manifest",
    "dpo_variant_manifest",
})
_KNOWN_ARTIFACT_FILES = frozenset({
    "data_manifest",
    "selected_sft",
    "selected_sft_manifest",
    "selected_dpo",
    "selected_dpo_manifest",
    "reasoning_gap_queue",
    "reasoning_repaired_rows",
    "reasoning_repaired_rows_manifest",
    "contract_dpo",
    "contract_dpo_manifest",
    "dpo_mix",
    "dpo_mix_manifest",
    "quality_audit",
    "corridor_expansion_plan",
    "corridor_expansion_plan_manifest",
})
_SAFE_ARTIFACT_ISSUES = frozenset({
    "fingerprint_mismatch",
    "malformed",
    "materialized_without_fingerprint",
    "missing_file",
    "unreadable_file",
    "unverifiable_path",
})
_UNVERIFIABLE_ARTIFACT_PATHS = frozenset({"external", "redacted", "n/a"})


def _contains_sensitive_text(value: str) -> bool:
    return bool(
        _EMAIL.search(value)
        or _PHONE.search(value)
        or _LONG_DIGITS.search(value)
        or _LOCAL_PATH_HINT.search(value)
        or "\\" in value
    )


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


def _display_base_model(base_model: Any) -> str:
    text = str(base_model or "")
    if not text:
        return "unknown"
    return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(text).as_posix()))


def _display_status(status: Any) -> str:
    text = str(status or "")
    return text if text in STATUSES else "redacted"


def _display_hashlike(value: Any) -> str:
    if value is None:
        return "n/a"
    text = str(value or "").strip()
    if _SHA256_RE.fullmatch(text):
        return text
    if text.isdigit() and _LONG_DIGITS.search(text):
        return "redacted"
    return text if _SAFE_HASHLIKE.fullmatch(text) else "redacted"


def _display_created_utc(value: Any) -> str:
    if value is None:
        return "n/a"
    text = str(value or "").strip()
    return text if _SAFE_CREATED_UTC.fullmatch(text) else "redacted"


def _display_nonnegative_int(value: Any) -> Any:
    if isinstance(value, bool):
        return "redacted"
    if isinstance(value, int):
        return value if value >= 0 else "redacted"
    if value is None:
        return None
    return "redacted"


def _is_safe_field_key(key: Any) -> bool:
    text = str(key)
    return bool(_SAFE_FIELD_KEY.fullmatch(text) and not _contains_sensitive_text(text))


def _display_artifact_name(name: Any, *, unknown_index: int) -> str:
    text = str(name or "?")
    if text in _KNOWN_ARTIFACT_FILES:
        return text
    return f"additional_artifact_{unknown_index}"


def _safe_issue_name(value: Any) -> str:
    text = str(value or "issue")
    return text if text in _SAFE_ARTIFACT_ISSUES else "issue"


def _display_key(key: Any, *, unknown_index: int) -> str:
    text = str(key)
    return text if _is_safe_field_key(text) else f"additional_field_{unknown_index}"


def _display_value(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        if key == "artifact_files":
            return _display_artifact_files(value)
        out: dict[str, Any] = {}
        unknown_count = 0
        for item_key, item_value in value.items():
            if not _is_safe_field_key(item_key):
                unknown_count += 1
                display_key = _display_key(item_key, unknown_index=unknown_count)
            else:
                display_key = str(item_key)
            out[display_key] = _display_value(item_value, key=display_key)
        return out
    if isinstance(value, list):
        return [_display_value(item, key=key) for item in value]
    if isinstance(value, str):
        if key == "created_utc":
            return _display_created_utc(value)
        if key == "status":
            return _display_status(value)
        if key == "model_id":
            return _display_model_id(value)
        if key == "base_model":
            return _display_base_model(value)
        if key in {"git_sha", "manifest_sha256", "sha256", "expected_sha256", "actual_sha256"}:
            return _display_hashlike(value)
        if key in _PATH_KEYS or key.endswith("_path"):
            return _display_report_path(value)
        if _contains_sensitive_text(value):
            return "redacted"
    if key in {"bytes", "expected_bytes", "actual_bytes", "sft_examples", "dpo_examples", "selected_pairs"}:
        return _display_nonnegative_int(value)
    return value


def _display_artifact_files(artifact_files: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    unknown_count = 0
    for name, entry in artifact_files.items():
        if name not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        display_name = _display_artifact_name(name, unknown_index=unknown_count)
        out[display_name] = _display_value(entry, key=display_name)
    return out


def _display_record(record: dict[str, Any]) -> dict[str, Any]:
    return _display_value(record)


def _display_verification_issues(issues: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    unknown_count = 0
    for issue in issues:
        if not isinstance(issue, dict):
            unknown_count += 1
            out.append({"artifact": f"additional_artifact_{unknown_count}", "issue": "issue"})
            continue
        artifact = issue.get("artifact")
        if artifact not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        safe_issue: dict[str, Any] = {
            "artifact": _display_artifact_name(artifact, unknown_index=unknown_count),
            "issue": _safe_issue_name(issue.get("issue")),
        }
        if issue.get("path"):
            safe_issue["path"] = _display_report_path(issue.get("path"))
        for key in ("expected_sha256", "actual_sha256"):
            value = issue.get(key)
            if isinstance(value, str) and _SHA256_RE.fullmatch(value):
                safe_issue[key] = value
        for key in ("expected_bytes", "actual_bytes"):
            value = issue.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                safe_issue[key] = value
        if issue.get("detail"):
            safe_issue["detail"] = "redacted"
        out.append(safe_issue)
    return out


def _display_verification_result(result: dict[str, Any]) -> dict[str, Any]:
    out = {key: _display_value(value, key=key) for key, value in result.items() if key != "issues"}
    out["issues"] = _display_verification_issues(result.get("issues") or [])
    return out


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


def _validate_artifacts(artifacts: Any) -> dict[str, Any]:
    """Validate the structured artifact-fingerprint payload while preserving legacy artifact keys."""
    if artifacts is None:
        return {}
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be a JSON object")
    artifact_files = artifacts.get("artifact_files")
    if artifact_files is None:
        return artifacts
    if not isinstance(artifact_files, dict):
        raise ValueError("artifacts.artifact_files must be a JSON object")
    unknown_count = 0
    for name, entry in artifact_files.items():
        if name not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        display_name = _display_artifact_name(name, unknown_index=unknown_count)
        if not isinstance(name, str) or not name:
            raise ValueError("artifacts.artifact_files keys must be non-empty strings")
        if entry is None:
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"artifact_files.{display_name} must be an object or null")
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(path, str) or not path:
            raise ValueError(f"artifact_files.{display_name}.path must be a non-empty string")
        if sha256 is None and byte_count is None:
            continue
        if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
            raise ValueError(f"artifact_files.{display_name}.sha256 must be a 64-character hex digest or null")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise ValueError(f"artifact_files.{display_name}.bytes must be a non-negative integer or null")
    return artifacts


def _storage_safe_artifacts(artifacts: dict[str, Any]) -> dict[str, Any]:
    return _display_value(artifacts, key="artifacts")


def _resolve_artifact_path(raw_path: str) -> pathlib.Path:
    path = pathlib.Path(raw_path)
    return path if path.is_absolute() else _ROOT / path


def verify_record_artifacts(record: dict[str, Any]) -> dict[str, Any]:
    """Verify recorded artifact fingerprints against files currently available on disk."""
    result: dict[str, Any] = {
        "model_id": _display_model_id(record.get("model_id")),
        "created_utc": _display_created_utc(record.get("created_utc")),
        "status": _display_status(record.get("status")),
        "checked": 0,
        "matched": 0,
        "pending": 0,
        "legacy_without_artifact_files": False,
        "issues": [],
        "ok": True,
    }
    artifacts = record.get("artifacts") or {}
    try:
        artifacts = _validate_artifacts(artifacts)
    except ValueError as exc:
        result["issues"].append({"artifact": "artifact_files", "issue": "malformed", "detail": str(exc)})
        result["ok"] = False
        return result

    artifact_files = artifacts.get("artifact_files")
    if artifact_files is None:
        result["legacy_without_artifact_files"] = True
        return result

    unknown_count = 0
    for name, entry in artifact_files.items():
        if name not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        display_name = _display_artifact_name(name, unknown_index=unknown_count)
        if entry is None:
            result["pending"] += 1
            continue
        expected_sha = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        raw_path = entry["path"]
        if raw_path in _UNVERIFIABLE_ARTIFACT_PATHS:
            if expected_sha is None and expected_bytes is None:
                result["pending"] += 1
            else:
                result["issues"].append({
                    "artifact": display_name,
                    "issue": "unverifiable_path",
                    "path": _display_report_path(raw_path),
                })
            continue
        path = _resolve_artifact_path(raw_path)
        if expected_sha is None and expected_bytes is None:
            if path.exists():
                result["issues"].append({
                    "artifact": display_name,
                    "issue": "materialized_without_fingerprint",
                    "path": _display_report_path(path),
                })
            else:
                result["pending"] += 1
            continue
        result["checked"] += 1
        if not path.exists():
            result["issues"].append({
                "artifact": display_name,
                "issue": "missing_file",
                "path": _display_report_path(path),
            })
            continue
        try:
            data = path.read_bytes()
        except OSError:
            result["issues"].append({
                "artifact": display_name,
                "issue": "unreadable_file",
                "path": _display_report_path(path),
                "detail": "redacted",
            })
            continue
        actual_sha = hashlib.sha256(data).hexdigest()
        actual_bytes = len(data)
        if actual_sha != expected_sha or actual_bytes != expected_bytes:
            result["issues"].append({
                "artifact": display_name,
                "issue": "fingerprint_mismatch",
                "path": _display_report_path(path),
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
                "expected_bytes": expected_bytes,
                "actual_bytes": actual_bytes,
            })
            continue
        result["matched"] += 1
    result["ok"] = not result["issues"]
    return result


def make_record(*, model_id: str, base_model: str, status: str, created_utc: str,
                git: "str | None" = None, data_manifest: "pathlib.Path | None" = None,
                eval_scores: "dict | None" = None, artifacts: "dict | None" = None,
                notes: str = "") -> dict[str, Any]:
    """Build one provenance record. Pure -- the caller supplies created_utc + git so it is testable."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {_display_status(status)}")
    artifacts = _storage_safe_artifacts(_validate_artifacts(artifacts))
    data = {"manifest_path": _display_report_path(data_manifest) if data_manifest else None,
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
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
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
        if not isinstance(r, dict):
            continue
        mid = r.get("model_id")
        if mid:
            out[str(mid)] = r
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY, help="registry JSONL path")
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
    v = sub.add_parser("verify", help="verify latest recorded artifact fingerprints against local files")
    v.add_argument("model_id", nargs="?", help="model_id to verify; default verifies latest row for every model")
    v.add_argument("--history", action="store_true", help="verify all matching history rows instead of latest only")
    v.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        rec = make_record(
            model_id=args.model_id, base_model=args.base, status=args.status,
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), git=git_sha(),
            data_manifest=args.data_manifest,
            eval_scores=json.loads(args.eval) if args.eval else None,
            artifacts=json.loads(args.artifacts) if args.artifacts else None, notes=args.notes)
        append(rec, args.registry)
        print(f"[finetune-registry] +{_display_status(rec['status'])} {_display_model_id(rec['model_id'])} "
              f"(base={_display_base_model(rec['base_model'])}, "
              f"data_sha={_display_hashlike(rec['data']['manifest_sha256'])}, "
              f"git={_display_hashlike(rec['git_sha'])}) -> {_display_report_path(args.registry)}")
        return 0

    records = load(args.registry)
    if args.cmd == "list":
        latest = latest_by_id(records)
        if not latest:
            print("[finetune-registry] empty -- add a run with `add`")
            return 0
        for mid, r in sorted(latest.items()):
            safe_eval = _display_value(r.get("eval") or {}, key="eval")
            safe_status = _display_status(r.get("status"))
            safe_data_sha = _display_hashlike((r.get("data") or {}).get("manifest_sha256"))
            print(f"  {safe_status:10} {_display_model_id(mid):46} "
                  f"base={_display_base_model(r.get('base_model')):22} "
                  f"data_sha={safe_data_sha} eval={safe_eval}")
        return 0
    if args.cmd == "show":
        hist = [r for r in records if r.get("model_id") == args.model_id]
        if not hist:
            print(f"[finetune-registry] no record for {_display_model_id(args.model_id)}")
            return 1
        print(json.dumps([_display_record(r) for r in hist], indent=2))
        return 0
    if args.cmd == "verify":
        if args.history:
            selected = [r for r in records if not args.model_id or r.get("model_id") == args.model_id]
        else:
            latest = latest_by_id(records)
            if args.model_id:
                selected = [latest[args.model_id]] if args.model_id in latest else []
            else:
                selected = list(latest.values())
        if args.model_id and not selected:
            print(f"[finetune-registry] no record for {_display_model_id(args.model_id)}")
            return 1
        results = [verify_record_artifacts(r) for r in selected]
        if args.json:
            print(json.dumps([_display_verification_result(result) for result in results], indent=2))
        else:
            for res in results:
                display_res = _display_verification_result(res)
                state = "OK" if res["ok"] else "FAIL"
                legacy = " legacy-no-artifact-files" if res["legacy_without_artifact_files"] else ""
                print(f"[finetune-registry] {state} {display_res['model_id']} "
                      f"created={display_res['created_utc']} checked={display_res['checked']} "
                      f"matched={display_res['matched']} pending={display_res['pending']}{legacy}")
                for issue in display_res["issues"]:
                    artifact = issue.get("artifact", "?")
                    detail = issue.get("issue", "issue")
                    path = issue.get("path")
                    print(f"  - {artifact}: {detail}{' ' + path if path else ''}")
        return 0 if all(r["ok"] for r in results) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
