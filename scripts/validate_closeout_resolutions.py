#!/usr/bin/env python3
"""Validate the 2026-07-28 closeout decisions without model or network calls."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import build_closeout_resolution_receipt as builder

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = ROOT / "configs" / "duecare" / "closeout_resolutions.json"
DEFERRED_PATH = ROOT / "configs" / "duecare" / "deferred_work.json"
DOCUMENT_PATH = ROOT / "docs" / "CLOSEOUT_RESOLUTIONS_2026_07_28.md"

EXPECTED_IDS = (
    "provider-usage-reconciliation",
    "private-platform-transfer",
    "release-disposition",
    "first-package-publication",
    "corridor-curation",
    "training-provenance-refresh",
    "bounded-model-smoke",
    "per-dimension-judging",
    "optional-kaggle-reruns",
    "human-gold-calibration",
    "source-freshness-maintenance",
)
OUTCOMES = frozenset(builder.OUTCOME_LABELS)
ITEM_FIELDS = frozenset({
    "id", "title", "outcome", "decision", "rationale", "verification",
    "claim_boundary", "reversible", "reopen_conditions", "evidence",
})
POSTURE_FIELDS = frozenset({
    "effective_on", "public_surfaces", "model_posture", "publication_posture",
    "claim_posture", "next_freshness_review",
})
PLACEHOLDERS = {
    "todo": re.compile(r"\bTODO\b", re.IGNORECASE),
    "tbd": re.compile(r"\bTBD\b", re.IGNORECASE),
    "coming_soon": re.compile(r"\bcoming soon\b", re.IGNORECASE),
    "double_brace": re.compile(r"\{\{[^{}]+\}\}"),
}


def _strings(value: Any, path: str = "root"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}")


def validate_receipt(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    if data.get("schema_version") != "duecare.closeout-resolutions.v1":
        findings.append("schema_version invalid")
    for field in ("closed_on",):
        try:
            date.fromisoformat(str(data.get(field, "")))
        except ValueError:
            findings.append(f"{field} invalid")
    for field in ("scope", "authority"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            findings.append(f"{field} missing")

    posture = data.get("maintenance_mode")
    if not isinstance(posture, dict) or set(posture) != POSTURE_FIELDS:
        findings.append("maintenance_mode fields invalid")
    else:
        for field in POSTURE_FIELDS:
            if not isinstance(posture[field], str) or not posture[field].strip():
                findings.append(f"maintenance_mode.{field} missing")
        for field in ("effective_on", "next_freshness_review"):
            try:
                date.fromisoformat(str(posture.get(field, "")))
            except ValueError:
                findings.append(f"maintenance_mode.{field} invalid")

    items = data.get("items")
    if not isinstance(items, list):
        findings.append("items must be a list")
        return sorted(set(findings))
    ids = tuple(item.get("id") for item in items if isinstance(item, dict))
    if ids != EXPECTED_IDS:
        findings.append("item ids or order do not match the inherited 11-item scope")

    for index, item in enumerate(items):
        label = f"item[{index}]"
        if not isinstance(item, dict):
            findings.append(f"{label} is not an object")
            continue
        if set(item) != ITEM_FIELDS:
            findings.append(f"{label} fields invalid")
            continue
        item_id = item["id"] if isinstance(item["id"], str) else label
        for field in ("id", "title", "decision", "rationale", "verification", "claim_boundary"):
            if not isinstance(item[field], str) or not item[field].strip():
                findings.append(f"{item_id} {field} missing")
        if not isinstance(item["outcome"], str) or item["outcome"] not in OUTCOMES:
            findings.append(f"{item_id} outcome invalid")
        if not isinstance(item["reversible"], bool):
            findings.append(f"{item_id} reversible invalid")
        for field in ("reopen_conditions", "evidence"):
            values = item[field]
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                findings.append(f"{item_id} {field} invalid")
        for evidence in item["evidence"] if isinstance(item["evidence"], list) else []:
            if not isinstance(evidence, str) or not evidence.strip():
                continue
            candidate = (root / evidence).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                findings.append(f"{item_id} evidence escapes repository")
                continue
            if not candidate.is_file():
                findings.append(f"{item_id} evidence missing: {evidence}")

    for path, value in _strings(data):
        if not value.strip():
            findings.append(f"empty string at {path}")
        for category, pattern in PLACEHOLDERS.items():
            if pattern.search(value):
                findings.append(f"unresolved token category={category} path={path}")
    return sorted(set(findings))


def validate(
    receipt_path: Path = RECEIPT_PATH,
    deferred_path: Path = DEFERRED_PATH,
    document_path: Path = DOCUMENT_PATH,
    root: Path = ROOT,
) -> dict[str, Any]:
    try:
        data = builder.load_receipt(receipt_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {"ok": False, "items": 0, "findings": ["receipt unreadable or invalid JSON"]}
    findings = validate_receipt(data, root)
    if not findings:
        try:
            deferred = json.loads(deferred_path.read_text(encoding="utf-8"))
            outstanding = deferred.get("items", []) if isinstance(deferred, dict) else None
        except (OSError, UnicodeError, json.JSONDecodeError):
            outstanding = None
        if not isinstance(outstanding, list):
            findings.append("deferred-work registry unreadable")
        else:
            outstanding_ids = {
                item.get("id")
                for item in outstanding
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            overlap = sorted(
                set(EXPECTED_IDS).intersection(outstanding_ids)
            )
            if overlap:
                findings.append("resolved item remains in outstanding register")
    if not findings:
        rendered = builder.render_receipt(data)
        try:
            current = document_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            current = ""
        if current != rendered:
            findings.append("generated closeout document is missing or stale")
    return {"ok": not findings, "items": len(data.get("items", [])), "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = validate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        state = "PASS" if result["ok"] else "FAIL"
        print(f"Closeout resolutions: {state} items={result['items']}")
        for finding in result["findings"]:
            print(f"- {finding}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
