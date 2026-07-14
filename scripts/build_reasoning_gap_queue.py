#!/usr/bin/env python3
"""Build a privacy-safe repair queue for weak reasoning-contract links.

The strict reasoning contract tells us *what* is weak (currently statute/action), but the data flywheel
needs a reproducible queue of *which prompt IDs* should be repaired or augmented next. This script reads
the train-split reasoning set from build_reasoning_targets.py and emits metadata only:

  * prompt_id and category
  * missing contract links and verifier booleans
  * citation-coherence metadata (mapped signals, cited/expected conventions)
  * Palermo/screening metadata
  * generic repair hints from reasoning_contract.py

It deliberately does NOT copy user prompts, assistant answers, raw traces, phone numbers, or case text into
the queue. To inspect a row, use the prompt_id locally against the gitignored training data.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_reasoning_gap_queue.py
    python scripts/build_reasoning_gap_queue.py --validate
    python scripts/build_reasoning_gap_queue.py --links statute action resources
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
from organize_training_data import CURATED_SET, FULL_SET, load_pid2cat  # noqa: E402
from palermo_screening import citation_coherence  # noqa: E402
from reasoning_contract import REASONING_SFT, STEPS, verify_reasoning  # noqa: E402

OUT = _ROOT / "reports" / "training" / "reasoning_gap_queue.json"
DEFAULT_TARGET_LINKS = ("statute", "action")
FORBIDDEN_FIELDS = frozenset({"messages", "prompt", "chosen", "rejected", "assistant", "text"})
QUEUE_ENTRY_FIELDS = frozenset({
    "prompt_id",
    "category",
    "priority",
    "missing_links",
    "target_missing_links",
    "chain_links",
    "n_steps",
    "order_ok",
    "citation_valid",
    "fragile",
    "palermo",
    "core_remedies",
    "citation",
    "violations",
    "repair_hint",
    "target_core_missing",
})
NESTED_QUEUE_FIELDS: dict[str, frozenset[str]] = {
    "chain_links": frozenset(STEPS),
    "fragile": frozenset({"phone", "money", "date"}),
    "palermo": frozenset({"triad_complete", "act", "means", "purpose", "screening_signals"}),
    "core_remedies": frozenset({"triggers", "required", "missing", "complete"}),
    "citation": frozenset({
        "mapped_signals",
        "cited_conventions",
        "expected_conventions",
        "matched",
        "coherent",
    }),
}
PII_SCAN_EXEMPT_FIELDS = frozenset({"prompt_id", "original_prompt_id", "base_prompt_id"})
VALID_TARGET_LINKS = frozenset(STEPS)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/#-]{1,160}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9 ._:/#-]{1,120}$")


def _has_sensitive_display_text(text: str) -> bool:
    return bool(_EMAIL.search(text) or _PHONE.search(text) or _LOCAL_PATH_HINT.search(text) or _LONG_DIGITS.search(text))


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
    if text and _SAFE_IDENTIFIER.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return ""


def _safe_category(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if text and _SAFE_LABEL.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return "unknown"


def _prompt_id(row: dict[str, Any]) -> str:
    return _safe_prompt_id(_meta_dict(row).get("prompt_id"))


def _priority(
    missing: list[str],
    target_missing: list[str],
    target_core_missing: list[str] | None = None,
) -> tuple[int, int]:
    """Lower is higher priority: both weak links, statute-only, action-only, core-remedy gaps, then other."""
    targets = set(target_missing)
    if {"statute", "action"} <= targets:
        return (0, len(missing))
    if "statute" in targets:
        return (1, len(missing))
    if "action" in targets:
        return (2, len(missing))
    if target_core_missing:
        return (3, len(missing))
    return (4, len(missing))


def _entry(
    row: dict[str, Any],
    *,
    pid2cat: dict[str, str],
    target_links: tuple[str, ...],
    require_core_remedies: bool = False,
) -> dict[str, Any] | None:
    text = _assistant_text(row)
    if not text:
        return None
    pid = _prompt_id(row)
    if not pid:
        return None
    verdict = verify_reasoning(text, require_core_remedies=require_core_remedies)
    if verdict.satisfied:
        return None
    missing = [s for s in STEPS if not verdict.steps.get(s)]
    target_missing = [s for s in missing if s in target_links]
    core = verdict.core_remedies
    target_core_missing = list(core.get("missing", [])) if require_core_remedies else []
    if not target_missing and not target_core_missing:
        return None
    pal = verdict.palermo
    return {
        "prompt_id": pid,
        "category": _safe_category(pid2cat.get(pid, "unknown")),
        "priority": _priority(missing, target_missing, target_core_missing)[0],
        "missing_links": missing,
        "target_missing_links": target_missing,
        "target_core_missing": target_core_missing,
        "chain_links": verdict.steps,
        "n_steps": verdict.n_steps,
        "order_ok": verdict.order_ok,
        "citation_valid": verdict.citation_valid,
        "fragile": verdict.fragile,
        "palermo": {
            "triad_complete": pal.get("triad_complete", False),
            "act": pal.get("act", []),
            "means": pal.get("means", []),
            "purpose": pal.get("purpose", []),
            "screening_signals": pal.get("screening_signals", []),
        },
        "core_remedies": {
            "triggers": core.get("triggers", []),
            "required": core.get("required", []),
            "missing": core.get("missing", []),
            "complete": core.get("complete", True),
        },
        "citation": citation_coherence(text),
        "violations": verdict.violations,
        "repair_hint": verdict.repair_hint,
    }


def _privacy_scan(value: Any, *, path: str = "$") -> dict[str, Any]:
    """Return metadata-only leak findings for a generated queue doc."""
    findings: dict[str, list[str]] = {
        "forbidden_field_paths": [],
        "unexpected_queue_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
    }

    def walk(v: Any, p: str) -> None:
        if isinstance(v, dict):
            if re.fullmatch(r"\$\.queue\[\d+\]", p):
                for key in v:
                    if str(key) not in QUEUE_ENTRY_FIELDS:
                        findings["unexpected_queue_field_paths"].append(f"{p}.{key}")
            nested = re.fullmatch(r"\$\.queue\[\d+\]\.([A-Za-z_][A-Za-z0-9_]*)", p)
            if nested and nested.group(1) in NESTED_QUEUE_FIELDS:
                allowed = NESTED_QUEUE_FIELDS[nested.group(1)]
                for key in v:
                    if str(key) not in allowed:
                        findings["unexpected_queue_field_paths"].append(f"{p}.{key}")
            for key, val in v.items():
                kp = f"{p}.{key}"
                if str(key) in FORBIDDEN_FIELDS:
                    findings["forbidden_field_paths"].append(kp)
                walk(val, kp)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                walk(item, f"{p}[{i}]")
        elif isinstance(v, str):
            field = p.rsplit(".", 1)[-1]
            if field in PII_SCAN_EXEMPT_FIELDS:
                return
            if _EMAIL.search(v):
                findings["email_like_paths"].append(p)
            if _PHONE.search(v):
                findings["phone_like_paths"].append(p)
            if _LONG_DIGITS.search(v):
                findings["long_digit_paths"].append(p)

    walk(value, path)
    counts = {k.replace("_paths", ""): len(v) for k, v in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _queue_manifest_issues(
    *,
    queue_entries: int,
    target_links: tuple[str, ...],
    metadata_only: bool,
    privacy_scan: dict[str, Any],
) -> list[str]:
    """Fail-closed metadata checks for a generated repair queue."""
    issues: list[str] = []
    if metadata_only is not True:
        issues.append("reasoning_gap_queue_metadata_only_not_true")
    if privacy_scan.get("ok") is not True:
        issues.append("reasoning_gap_queue_privacy_scan_not_ok")
    if not target_links:
        issues.append("reasoning_gap_queue_target_links_empty")
    invalid_links = sorted({link for link in target_links if link not in VALID_TARGET_LINKS})
    if invalid_links:
        issues.append("reasoning_gap_queue_target_links_invalid")
    if queue_entries < 0:
        issues.append("reasoning_gap_queue_count_invalid")
    return issues


def build_queue(
    rows: list[dict[str, Any]],
    *,
    pid2cat: dict[str, str] | None = None,
    target_links: tuple[str, ...] = DEFAULT_TARGET_LINKS,
    require_core_remedies: bool = False,
) -> dict[str, Any]:
    """Return {"queue", "manifest"} for contract gaps matching ``target_links``.

    Output is intentionally metadata-only; entries must not contain raw prompts or assistant text.
    """
    pid2cat = pid2cat or {}
    skipped: Counter[str] = Counter()
    queue: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            skipped["non_object_row"] += 1
            continue
        if _assistant_text(row) and not _prompt_id(row):
            skipped["missing_prompt_id"] += 1
            continue
        entry = _entry(
            row,
            pid2cat=pid2cat,
            target_links=target_links,
            require_core_remedies=require_core_remedies,
        )
        if entry:
            queue.append(entry)
    queue.sort(key=lambda e: (e["priority"], e["category"], e["prompt_id"]))

    by_missing: Counter[str] = Counter()
    by_target: Counter[str] = Counter()
    by_core_missing: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    core_triggered = 0
    for e in queue:
        by_missing.update(e["missing_links"])
        by_target.update(e["target_missing_links"])
        by_core_missing.update(e.get("target_core_missing", []))
        if e.get("core_remedies", {}).get("required"):
            core_triggered += 1
        by_category[e["category"]] += 1

    doc = {"queue": queue}
    privacy_scan = _privacy_scan(doc)
    metadata_only = True
    queue_manifest_issues = _queue_manifest_issues(
        queue_entries=len(queue),
        target_links=target_links,
        metadata_only=metadata_only,
        privacy_scan=privacy_scan,
    )
    manifest = {
        "input": len(rows),
        "queued": len(queue),
        "target_links": list(target_links),
        "require_core_remedies": require_core_remedies,
        "by_missing_link": {k: by_missing[k] for k in sorted(by_missing)},
        "by_target_missing_link": {k: by_target[k] for k in sorted(by_target)},
        "by_core_missing": {k: by_core_missing[k] for k in sorted(by_core_missing)},
        "core_triggered": core_triggered,
        "by_category": {k: by_category[k] for k in sorted(by_category)},
        "skipped": {k: skipped[k] for k in sorted(skipped)},
        "metadata_only": metadata_only,
        "forbidden_fields": sorted(FORBIDDEN_FIELDS),
        "queue_entry_fields": sorted(QUEUE_ENTRY_FIELDS),
        "nested_queue_fields": {k: sorted(v) for k, v in sorted(NESTED_QUEUE_FIELDS.items())},
        "privacy_scan": privacy_scan,
        "queue_manifest_issues": queue_manifest_issues,
        "safe_for_repair": not queue_manifest_issues,
        "actionable_for_repair": bool(queue),
        "note": ("Privacy-safe repair queue for reasoning-contract gaps. Entries identify prompt IDs and "
                 "structured verifier metadata only, so the data flywheel can target missing statute/action "
                 "links, and optionally mandatory core-remedy gaps, without copying raw prompts, answers, "
                 "or case text into the report."),
    }
    doc["manifest"] = manifest
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="train-split gold reasoning set")
    ap.add_argument("--links", nargs="+", default=list(DEFAULT_TARGET_LINKS), choices=list(STEPS),
                    help="contract links to queue for repair")
    ap.add_argument("--require-core-remedies", action="store_true",
                    help="also queue rows missing mandatory money-remedy/non-punishment guarantees")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[reasoning-gap-queue] no reasoning set at {_display_report_path(args.sft)} "
              "-- run build_reasoning_targets.py first")
        return 1
    doc = build_queue(
        rows,
        pid2cat=load_pid2cat(FULL_SET, CURATED_SET),
        target_links=tuple(args.links),
        require_core_remedies=args.require_core_remedies,
    )
    if args.validate:
        print(json.dumps(doc["manifest"], indent=2, ensure_ascii=False))
        return 0 if doc["manifest"]["safe_for_repair"] else 1
    if not doc["manifest"]["safe_for_repair"]:
        print(json.dumps(doc["manifest"], indent=2, ensure_ascii=False))
        print("[reasoning-gap-queue] queue manifest is unsafe; refusing to write queue")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    m = doc["manifest"]
    print(f"[reasoning-gap-queue] queued {m['queued']} / {m['input']} traces for {m['target_links']} "
          f"repair -> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
