#!/usr/bin/env python3
"""Validate DueCare's canonical outstanding-work register without network calls."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import build_deferred_work_register as builder

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs" / "duecare" / "deferred_work.json"
DOCUMENT_PATH = ROOT / "docs" / "DEFERRED_WORK.md"

STATUSES = frozenset(builder.STATUS_LABELS)
PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
MODEL_POLICIES = frozenset({"zero_only", "nonzero_requires_owner_approval"})
NETWORK_POLICIES = frozenset(
    {"offline_only", "private_read_only", "read_only_verification", "owner_authorized_write"}
)
REQUIRED_ITEM_FIELDS = frozenset(
    {
        "id",
        "title",
        "priority",
        "status",
        "owner_role",
        "target",
        "reason",
        "model_credit_policy",
        "network_policy",
        "depends_on",
        "prerequisites",
        "next_actions",
        "acceptance_gates",
        "evidence",
    }
)
PLACEHOLDER_PATTERNS = {
    "todo": re.compile(r"\bTODO\b", re.IGNORECASE),
    "tbd": re.compile(r"\bTBD\b", re.IGNORECASE),
    "coming_soon": re.compile(r"\bcoming soon\b", re.IGNORECASE),
    "angle_token": re.compile(r"<[A-Za-z][^>]{0,80}>", re.IGNORECASE),
    "double_brace_token": re.compile(r"\{\{[^{}]+\}\}"),
    "fill_later": re.compile(r"\bfill (?:this |it )?in later\b", re.IGNORECASE),
    "unknown_owner": re.compile(r"\bunknown owner\b", re.IGNORECASE),
}


def _strings(value: Any, path: str = "root") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}")


def _cycle_findings(dependencies: dict[str, list[str]]) -> list[str]:
    findings: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str, trail: tuple[str, ...]) -> None:
        if item_id in visiting:
            findings.append("dependency cycle: " + " -> ".join((*trail, item_id)))
            return
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in dependencies.get(item_id, []):
            visit(dependency, (*trail, item_id))
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in dependencies:
        visit(item_id, ())
    return sorted(set(findings))


def validate_registry(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    """Return safe, payload-free finding labels for invalid registry data."""
    findings: list[str] = []
    if data.get("schema_version") != "duecare.deferred-work.v1":
        findings.append("schema_version invalid")
    try:
        date.fromisoformat(str(data.get("as_of", "")))
    except ValueError:
        findings.append("as_of is not an ISO date")
    posture = data.get("maintenance_posture")
    if not isinstance(posture, str) or not posture.strip():
        findings.append("maintenance_posture missing")

    policy = data.get("policy")
    policy_fields = {"completion_rule", "claim_rule", "cost_rule", "privacy_rule"}
    if not isinstance(policy, dict) or set(policy) != policy_fields:
        findings.append("policy fields invalid")
    elif any(
        not isinstance(policy[field], str) or not policy[field].strip()
        for field in policy_fields
    ):
        findings.append("policy contains an empty rule")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        findings.append("items must be a non-empty list")
        return findings

    identifiers: list[str] = []
    dependencies: dict[str, list[str]] = {}
    for index, item in enumerate(items):
        label = f"item[{index}]"
        if not isinstance(item, dict):
            findings.append(f"{label} is not an object")
            continue
        missing = REQUIRED_ITEM_FIELDS - set(item)
        extra = set(item) - REQUIRED_ITEM_FIELDS
        if missing:
            findings.append(f"{label} missing fields: {','.join(sorted(missing))}")
        if extra:
            findings.append(f"{label} unexpected fields: {','.join(sorted(extra))}")
        if missing:
            continue

        item_id = item["id"]
        if not isinstance(item_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item_id):
            findings.append(f"{label} id invalid")
            item_id = label
        identifiers.append(item_id)
        for field in ("title", "owner_role", "target", "reason"):
            if not isinstance(item[field], str) or not item[field].strip():
                findings.append(f"{item_id} {field} empty")
        if not isinstance(item["priority"], str) or item["priority"] not in PRIORITIES:
            findings.append(f"{item_id} priority invalid")
        if not isinstance(item["status"], str) or item["status"] not in STATUSES:
            findings.append(f"{item_id} status invalid")
        if (
            not isinstance(item["model_credit_policy"], str)
            or item["model_credit_policy"] not in MODEL_POLICIES
        ):
            findings.append(f"{item_id} model_credit_policy invalid")
        if (
            not isinstance(item["network_policy"], str)
            or item["network_policy"] not in NETWORK_POLICIES
        ):
            findings.append(f"{item_id} network_policy invalid")

        for field in ("prerequisites", "next_actions", "acceptance_gates", "evidence"):
            values = item[field]
            if not isinstance(values, list) or not values:
                findings.append(f"{item_id} {field} must be non-empty")
            elif any(not isinstance(value, str) or not value.strip() for value in values):
                findings.append(f"{item_id} {field} contains an empty value")
        depends_on = item["depends_on"]
        if not isinstance(depends_on, list) or any(
            not isinstance(value, str) for value in depends_on
        ):
            findings.append(f"{item_id} depends_on invalid")
            depends_on = []
        dependencies[item_id] = depends_on

        if item["status"] == "ready_local" and (
            item["model_credit_policy"] != "zero_only" or item["network_policy"] != "offline_only"
        ):
            findings.append(f"{item_id} ready_local boundary invalid")
        if item["status"] == "deferred_budget" and (
            item["model_credit_policy"] != "nonzero_requires_owner_approval"
            or item["network_policy"] != "owner_authorized_write"
        ):
            findings.append(f"{item_id} deferred_budget boundary invalid")
        if item["status"] == "blocked_private_access" and item["network_policy"] == "offline_only":
            findings.append(f"{item_id} private-access boundary invalid")

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
                findings.append(f"{item_id} evidence path missing: {evidence}")

    duplicate_ids = sorted(item_id for item_id, count in Counter(identifiers).items() if count > 1)
    if duplicate_ids:
        findings.append("duplicate ids: " + ",".join(duplicate_ids))
    known_ids = set(identifiers)
    for item_id, item_dependencies in dependencies.items():
        for dependency in item_dependencies:
            if dependency == item_id:
                findings.append(f"{item_id} depends on itself")
            elif dependency not in known_ids:
                findings.append(f"{item_id} dependency missing: {dependency}")
    findings.extend(_cycle_findings(dependencies))

    for path, value in _strings(data):
        if not value.strip():
            findings.append(f"empty string at {path}")
            continue
        for category, pattern in PLACEHOLDER_PATTERNS.items():
            if pattern.search(value):
                findings.append(f"unresolved token category={category} path={path}")

    return sorted(set(findings))


def validate(
    registry_path: Path = REGISTRY_PATH,
    document_path: Path = DOCUMENT_PATH,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return a JSON-serializable validation receipt."""
    try:
        data = builder.load_registry(registry_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {"ok": False, "items": 0, "findings": ["registry unreadable or invalid JSON"]}
    findings = validate_registry(data, root)
    if not findings:
        rendered = builder.render_registry(data)
        try:
            current = document_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            current = ""
        if current != rendered:
            findings.append("generated document is missing or stale")
    status_counts = Counter(
        item.get("status")
        for item in data.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("status"), str)
    )
    return {
        "ok": not findings,
        "items": len(data.get("items", [])),
        "status_counts": dict(sorted(status_counts.items())),
        "findings": sorted(set(findings)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    result = validate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        state = "PASS" if result["ok"] else "FAIL"
        print(f"Deferred-work register: {state} items={result['items']}")
        print("Status counts: " + ", ".join(
            f"{key}={value}" for key, value in result.get("status_counts", {}).items()
        ))
        for finding in result["findings"]:
            print(f"- {finding}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
