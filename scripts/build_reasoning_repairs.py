#!/usr/bin/env python3
"""Build proposed repaired reasoning SFT rows from the metadata-only gap queue.

This is the next offline step after build_reasoning_gap_queue.py:

  1. read reports/training/reasoning_sft.jsonl (train split only)
  2. read reports/training/reasoning_gap_queue.json
  3. append deterministic repair sentences for missing statute/action links
     (and, when requested, mandatory core-remedy omissions)
  4. keep only rows whose repaired assistant answer satisfies the strict reasoning contract

The output is a SEPARATE gitignored proposal file, not a mutation of the source set:

  reports/training/reasoning_repaired_sft.jsonl
  reports/training/reasoning_repaired_sft_manifest.json

The JSONL contains repaired assistant text because it is proposed training data and stays under
gitignored reports/. The manifest is metadata-only and safe to inspect publicly.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_reasoning_repairs.py
    python scripts/build_reasoning_repairs.py --validate
    python scripts/build_reasoning_repairs.py --validate --require-core-remedies
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from build_reasoning_targets import _assistant_text, _load_jsonl, _meta_dict  # noqa: E402
from build_reasoning_gap_queue import _privacy_scan as _gap_queue_privacy_scan  # noqa: E402
from reasoning_contract import REASONING_SFT, STEPS, verify_reasoning  # noqa: E402

QUEUE = _ROOT / "reports" / "training" / "reasoning_gap_queue.json"
OUT = _ROOT / "reports" / "training" / "reasoning_repaired_sft.jsonl"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/#-]{1,160}$")
_SAFE_PROMPT_ID = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,180}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,120}$")
_PATH_REPORT_KEYS = frozenset({"path", "output_path", "manifest_path", "sft", "queue", "out"})


def manifest_path_for(out_path: pathlib.Path) -> pathlib.Path:
    return out_path.with_name(f"{out_path.stem}_manifest.json")


MANIFEST = manifest_path_for(OUT)


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or re.search(r"\b\d{9,}\b", text)
    )


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
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


def _safe_prompt_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if (
        text
        and _SAFE_PROMPT_ID.fullmatch(text)
        and not _EMAIL.search(text)
        and not _LOCAL_PATH_HINT.search(text)
    ):
        return text
    return ""


def _metadata_prompt_id_ok(value: Any) -> bool:
    """Prompt IDs are metadata keys; allow opaque numeric chunks but reject obvious contact/path content."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(
        text
        and _SAFE_PROMPT_ID.fullmatch(text)
        and not _EMAIL.search(text)
        and not _LOCAL_PATH_HINT.search(text)
    )


def _safe_category(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if text and _SAFE_LABEL.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return "unknown"


def _display_manifest(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: _display_manifest(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_display_manifest(item, key=key) for item in value]
    if isinstance(value, str) and (key in _PATH_REPORT_KEYS or key.endswith("_path")):
        return _display_report_path(value)
    if isinstance(value, str) and _has_sensitive_display_text(value):
        return "redacted"
    return value

CONVENTION_NAMES = {
    29: "Forced Labour",
    95: "Protection of Wages",
    97: "Migration for Employment",
    143: "Migrant Workers",
    181: "Private Employment Agencies",
    189: "Domestic Workers",
}
CONVENTION_PRIORITY = (29, 181, 95, 189, 97, 143)

ACTION_SENTENCE = (
    "Protective action: do not sign, pay, or hand over documents under pressure; keep copies of documents "
    "and receipts, ask for written terms, and pause the process until the worker can get independent help."
)
CORE_REMEDY_SENTENCES = {
    "compensation_damages": (
        "Core remedy: name compensation or damages as a possible right for the exploitation, separate from "
        "immediate safety support and without promising a payout."
    ),
    "non_punishment": (
        "Core remedy: state that a trafficked or forced worker should not be punished for offences, status "
        "issues, or acts they were compelled into."
    ),
    "unpaid_wage_recovery": (
        "Core remedy: name recovery of unpaid wages or wage arrears as a remedy and preserve pay records, "
        "contracts, receipts, and messages where safe."
    ),
    "fee_refund": (
        "Core remedy: name reimbursement of illegal recruitment fees and related costs as a remedy and "
        "preserve fee receipts or loan records where safe."
    ),
}
_VALID_QUEUE_LINKS = set(STEPS)
_VALID_CORE_REMEDIES = set(CORE_REMEDY_SENTENCES)


def _load_queue_doc(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "missing": True, "queue": [], "manifest": None}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"path": str(path), "error": "invalid JSON", "queue": [], "manifest": None}
    if isinstance(doc, dict):
        raw_rows = doc.get("queue", [])
        manifest = doc.get("manifest") if isinstance(doc.get("manifest"), dict) else None
        if raw_rows is None:
            raw_rows = []
        result = {"path": str(path), "queue": [], "manifest": manifest}
        if not isinstance(raw_rows, list):
            result["queue_not_list"] = True
            return result
        rows = [r for r in raw_rows if isinstance(r, dict)]
        result["queue"] = rows
        non_object_entries = len(raw_rows) - len(rows)
        if non_object_entries:
            result["non_object_entries"] = non_object_entries
        return result
    rows = doc if isinstance(doc, list) else []
    result = {"path": str(path), "legacy_list": True, "queue": [r for r in rows if isinstance(r, dict)],
              "manifest": None}
    non_object_entries = len(rows) - len(result["queue"])
    if non_object_entries:
        result["non_object_entries"] = non_object_entries
    return result


def _load_queue(path: pathlib.Path) -> list[dict[str, Any]]:
    """Backward-compatible queue loader for tests/ad hoc callers."""
    return _load_queue_doc(path)["queue"]


def _queue_manifest_issues(queue_doc: dict[str, Any], *, require_core_remedies: bool = False) -> list[str]:
    """Fail-closed checks proving the repair source is the metadata-only gap queue."""
    issues: list[str] = []
    queue = queue_doc.get("queue") or []
    manifest = queue_doc.get("manifest")
    if queue_doc.get("missing"):
        return ["reasoning_gap_queue_missing"]
    if queue_doc.get("error"):
        return ["reasoning_gap_queue_invalid_json"]
    if queue_doc.get("queue_not_list"):
        issues.append("reasoning_gap_queue_not_list")
    if queue_doc.get("non_object_entries"):
        issues.append("reasoning_gap_queue_non_object_entries")
    if manifest is None:
        issues.append("reasoning_gap_queue_manifest_missing")
        return issues
    if manifest.get("metadata_only") is not True:
        issues.append("reasoning_gap_queue_manifest_metadata_only_not_true")
    if manifest.get("safe_for_repair") is not True:
        issues.append("reasoning_gap_queue_manifest_not_safe_for_repair")
    if manifest.get("queue_manifest_issues"):
        issues.append("reasoning_gap_queue_manifest_issues_present")
    privacy_scan = manifest.get("privacy_scan") or {}
    if privacy_scan.get("ok") is not True:
        issues.append("reasoning_gap_queue_privacy_scan_not_ok")
    actual_privacy_scan = _gap_queue_privacy_scan({"queue": queue})
    if actual_privacy_scan.get("ok") is not True:
        issues.append("reasoning_gap_queue_actual_privacy_scan_not_ok")
    if _queue_shape_issues(queue):
        issues.append("reasoning_gap_queue_entry_shape_invalid")
    if manifest.get("queued") != len(queue):
        issues.append("reasoning_gap_queue_manifest_count_mismatch")
    if manifest.get("target_links") is None:
        issues.append("reasoning_gap_queue_manifest_missing_target_links")
    if require_core_remedies and manifest.get("require_core_remedies") is not True:
        issues.append("reasoning_gap_queue_manifest_core_remedies_not_enabled")
    return issues


def _queue_shape_issues(queue: list[dict[str, Any]]) -> list[str]:
    """Metadata-only shape checks for queue fields used by the deterministic repair builder."""
    issues: list[str] = []
    for idx, entry in enumerate(queue):
        prefix = f"queue[{idx}]"
        pid = entry.get("prompt_id")
        if not _metadata_prompt_id_ok(pid):
            issues.append(f"{prefix}.prompt_id")
        for field in ("missing_links", "target_missing_links"):
            links = entry.get(field)
            if not isinstance(links, list) or any(not isinstance(link, str) or link not in _VALID_QUEUE_LINKS
                                                  for link in links):
                issues.append(f"{prefix}.{field}")
        target_core_missing = entry.get("target_core_missing")
        if target_core_missing is not None:
            if not isinstance(target_core_missing, list) or any(
                not isinstance(item, str) or item not in _VALID_CORE_REMEDIES
                for item in target_core_missing
            ):
                issues.append(f"{prefix}.target_core_missing")
        core = entry.get("core_remedies")
        if core is not None:
            if not isinstance(core, dict):
                issues.append(f"{prefix}.core_remedies")
            else:
                for field in ("triggers", "required", "missing"):
                    values = core.get(field, [])
                    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                        issues.append(f"{prefix}.core_remedies.{field}")
                if not isinstance(core.get("complete", True), bool):
                    issues.append(f"{prefix}.core_remedies.complete")
        citation = entry.get("citation")
        if not isinstance(citation, dict):
            issues.append(f"{prefix}.citation")
            continue
        expected = citation.get("expected_conventions")
        if not isinstance(expected, list):
            issues.append(f"{prefix}.citation.expected_conventions")
            continue
        for item in expected:
            if isinstance(item, bool):
                issues.append(f"{prefix}.citation.expected_conventions")
                break
            try:
                int(item)
            except (TypeError, ValueError):
                issues.append(f"{prefix}.citation.expected_conventions")
                break
    return issues


def _repair_manifest_issues(
    *,
    queue_entries: int,
    repaired_rows: int,
    by_added: Counter[str],
    by_added_core: Counter[str],
    source_queue_issues: list[str],
) -> list[str]:
    issues: list[str] = []
    if source_queue_issues:
        issues.append("reasoning_repair_source_queue_issues")
    if queue_entries <= 0:
        issues.append("reasoning_repair_no_queue_entries")
    if repaired_rows <= 0:
        issues.append("reasoning_repair_no_repaired_rows")
    if repaired_rows > queue_entries:
        issues.append("reasoning_repair_rows_exceed_queue_entries")
    if repaired_rows > 0 and not by_added and not by_added_core:
        issues.append("reasoning_repair_missing_added_counts")
    return issues


def _prompt_id(row: dict[str, Any]) -> str:
    return _safe_prompt_id(_meta_dict(row).get("prompt_id"))


def _select_convention(entry: dict[str, Any]) -> int | None:
    expected: list[int] = []
    for candidate in (entry.get("citation") or {}).get("expected_conventions") or []:
        if isinstance(candidate, bool):
            continue
        try:
            expected.append(int(candidate))
        except (TypeError, ValueError):
            continue
    if not expected:
        return None
    for conv in CONVENTION_PRIORITY:
        if conv in expected:
            return conv
    return min(expected)


def _statute_sentence(entry: dict[str, Any]) -> str | None:
    conv = _select_convention(entry)
    if conv is None:
        return None
    label = CONVENTION_NAMES.get(conv)
    name = f" ({label})" if label else ""
    return (
        f"Legal grounding: ILO Convention No. {conv}{name} is a governing convention for the named "
        "forced-labour indicator, so the response should treat the risk as a legal protection issue, not "
        "as a private arrangement to optimize."
    )


def repair_text(text: str, entry: dict[str, Any]) -> tuple[str, list[str], list[str], list[str], list[str]]:
    """Return (repaired_text, added_links, skipped_links, added_core_remedies, skipped_core_remedies)."""
    target_missing = [s for s in entry.get("target_missing_links", []) if s in STEPS]
    target_core_missing = [
        str(item) for item in entry.get("target_core_missing", []) if str(item) in CORE_REMEDY_SENTENCES
    ]
    additions: list[str] = []
    added: list[str] = []
    skipped: list[str] = []
    added_core: list[str] = []
    skipped_core: list[str] = []
    if "statute" in target_missing:
        sent = _statute_sentence(entry)
        if sent:
            additions.append(sent)
            added.append("statute")
        else:
            skipped.append("statute")
    if "action" in target_missing:
        additions.append(ACTION_SENTENCE)
        added.append("action")
    for remedy in target_core_missing:
        sent = CORE_REMEDY_SENTENCES.get(remedy)
        if sent:
            additions.append(sent)
            added_core.append(remedy)
        else:
            skipped_core.append(remedy)
    if not additions:
        return text, added, skipped, added_core, skipped_core
    return text.rstrip() + "\n\n" + " ".join(additions), added, skipped, added_core, skipped_core


def _replace_assistant(row: dict[str, Any], content: str) -> dict[str, Any]:
    out = dict(row)
    raw_messages = row.get("messages") if isinstance(row, dict) else []
    messages = [dict(m) for m in raw_messages if isinstance(m, dict)] if isinstance(raw_messages, list) else []
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            msg["content"] = content
            break
    out["messages"] = messages
    return out


def build_repairs(
    rows: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    *,
    output_path: pathlib.Path = OUT,
    queue_manifest: dict[str, Any] | None = None,
    source_queue_issues: list[str] | None = None,
    require_core_remedies: bool = False,
) -> dict[str, Any]:
    """Build proposed repaired SFT rows. Returns {"rows", "manifest"}."""
    queue_by_pid: dict[str, dict[str, Any]] = {}
    for entry in queue:
        pid = _safe_prompt_id(entry.get("prompt_id"))
        if pid:
            queue_by_pid[pid] = entry
    repaired: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    by_added: Counter[str] = Counter()
    by_added_core: Counter[str] = Counter()
    by_category: Counter[str] = Counter()

    for row in rows:
        pid = _prompt_id(row)
        entry = queue_by_pid.get(pid)
        if not entry:
            continue
        original = _assistant_text(row)
        if not original:
            skipped["missing_assistant"] += 1
            continue
        repaired_text, added_links, skipped_links, added_core, skipped_core = repair_text(original, entry)
        for link in skipped_links:
            skipped[f"no_{link}_repair"] += 1
        for remedy in skipped_core:
            skipped[f"no_core_{remedy}_repair"] += 1
        if not added_links and not added_core:
            skipped["no_added_items"] += 1
            continue
        verdict = verify_reasoning(repaired_text, require_core_remedies=require_core_remedies)
        if not verdict.satisfied:
            skipped["verification_failed"] += 1
            continue
        out = _replace_assistant(row, repaired_text)
        meta = dict(out.get("_meta") or {})
        category = _safe_category(entry.get("category"))
        repair_meta = {
            "source": "reasoning_gap_queue",
            "original_prompt_id": pid,
            "category": category,
            "added_links": added_links,
            "original_missing_links": entry.get("missing_links", []),
            "original_target_missing_links": entry.get("target_missing_links", []),
            "repaired_chain_links": verdict.steps,
            "repaired_n_steps": verdict.n_steps,
            "selected_convention": _select_convention(entry) if "statute" in added_links else None,
        }
        if added_core or entry.get("target_core_missing"):
            repair_meta["added_core_remedies"] = added_core
            repair_meta["original_target_core_missing"] = entry.get("target_core_missing", [])
        meta["reasoning_repair"] = repair_meta
        out["_meta"] = meta
        repaired.append(out)
        by_added.update(added_links)
        by_added_core.update(added_core)
        by_category[category] += 1

    source_queue_issues = source_queue_issues or []
    repair_manifest_issues = _repair_manifest_issues(
        queue_entries=len(queue),
        repaired_rows=len(repaired),
        by_added=by_added,
        by_added_core=by_added_core,
        source_queue_issues=source_queue_issues,
    )
    manifest = {
        "input_rows": len(rows),
        "queue_entries": len(queue),
        "repaired_rows": len(repaired),
        "by_added_link": {k: by_added[k] for k in sorted(by_added)},
        "by_added_core_remedy": {k: by_added_core[k] for k in sorted(by_added_core)},
        "by_category": {k: by_category[k] for k in sorted(by_category)},
        "skipped": {k: skipped[k] for k in sorted(skipped)},
        "metadata_only": True,
        "output_contains_repaired_training_text": True,
        "source_queue": {
            "metadata_only": queue_manifest.get("metadata_only") if queue_manifest else None,
            "privacy_scan_ok": (queue_manifest.get("privacy_scan") or {}).get("ok") if queue_manifest else None,
            "safe_for_repair": queue_manifest.get("safe_for_repair") if queue_manifest else None,
            "actionable_for_repair": queue_manifest.get("actionable_for_repair") if queue_manifest else None,
            "queue_manifest_issues": queue_manifest.get("queue_manifest_issues") if queue_manifest else None,
            "queued": queue_manifest.get("queued") if queue_manifest else None,
            "target_links": queue_manifest.get("target_links") if queue_manifest else None,
            "require_core_remedies": queue_manifest.get("require_core_remedies") if queue_manifest else None,
            "by_core_missing": queue_manifest.get("by_core_missing") if queue_manifest else None,
        } if queue_manifest is not None else None,
        "require_core_remedies": require_core_remedies,
        "source_queue_issues": source_queue_issues,
        "repair_manifest_issues": repair_manifest_issues,
        "safe_to_train": not repair_manifest_issues,
        "output_path": _display_report_path(output_path),
        "manifest_path": _display_report_path(manifest_path_for(output_path)),
        "note": ("Proposed deterministic repairs for train-split reasoning rows. The JSONL output contains "
                 "repaired assistant text and stays under gitignored reports/; this manifest contains only "
                 "counts and metadata. Every emitted row re-verifies against the strict reasoning contract, "
                 "optionally including mandatory core-remedy enforcement, "
                 "and the source gap queue must have a passing metadata-only privacy manifest before the "
                 "CLI writes repaired training rows."),
    }
    return {"rows": repaired, "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="train-split gold reasoning set")
    ap.add_argument("--queue", type=pathlib.Path, default=QUEUE, help="metadata-only reasoning gap queue")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    ap.add_argument("--require-core-remedies", action="store_true",
                    help="consume a core-remedy queue and verify repaired rows with core-remedy enforcement")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    queue_doc = _load_queue_doc(args.queue)
    queue = queue_doc["queue"]
    if not rows:
        print(
            f"[reasoning-repairs] no reasoning set at {_display_report_path(args.sft)} "
            "-- run build_reasoning_targets.py first"
        )
        return 1
    source_issues = _queue_manifest_issues(queue_doc, require_core_remedies=args.require_core_remedies)
    if not queue and source_issues == ["reasoning_gap_queue_missing"]:
        print(
            f"[reasoning-repairs] no gap queue at {_display_report_path(args.queue)} "
            "-- run build_reasoning_gap_queue.py first"
        )
        return 1
    if not queue and not source_issues:
        print(
            f"[reasoning-repairs] no gap queue at {_display_report_path(args.queue)} "
            "-- run build_reasoning_gap_queue.py first"
        )
        return 1
    doc = build_repairs(
        rows,
        queue,
        output_path=args.out,
        queue_manifest=queue_doc.get("manifest"),
        source_queue_issues=source_issues,
        require_core_remedies=args.require_core_remedies,
    )
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(_display_manifest(m), indent=2, ensure_ascii=False))
        return 0 if m["safe_to_train"] else 1
    if not m["safe_to_train"]:
        print(json.dumps(_display_manifest(m), indent=2, ensure_ascii=False))
        print("[reasoning-repairs] source gap queue is unsafe; refusing to write repaired training JSONL")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in doc["rows"]), encoding="utf-8")
    manifest_path_for(args.out).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[reasoning-repairs] repaired {m['repaired_rows']} / {m['queue_entries']} queued traces "
          f"with added links {m['by_added_link']} and core remedies {m['by_added_core_remedy']} "
          f"-> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
