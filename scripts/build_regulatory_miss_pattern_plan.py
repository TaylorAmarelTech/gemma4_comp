#!/usr/bin/env python3
"""Build a source-gated expansion plan for adjacent regulatory-miss domains.

The input catalog is propose-only. It lists industries where LLMs can miss
local protections, cross-border rules, informal publication channels, or safe
remedy routing. This builder turns that catalog into a compact research plan
without adding source URLs, raw cases, worker details, or legal claims.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_regulatory_miss_pattern_plan.py
    python scripts/build_regulatory_miss_pattern_plan.py --validate
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = _ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json"
OUT = _ROOT / "reports" / "benchmark" / "regulatory_miss_pattern_plan.json"
MD_OUT = _ROOT / "reports" / "benchmark" / "regulatory_miss_pattern_plan.md"

REQUIRED_PATTERN_FIELDS = frozenset({
    "id",
    "display_name",
    "candidate_status",
    "industry_scope",
    "legal_dimensions",
    "source_channels",
    "model_miss_patterns",
    "prompt_families",
    "source_gates",
    "do_not_score_until",
})
ALLOWED_PATTERN_FIELDS = REQUIRED_PATTERN_FIELDS | frozenset({"active_domain"})
SAFE_STATUS = frozenset({"active_seed", "candidate", "defer"})
SENSITIVE_FIELD_NAMES = frozenset({
    "name",
    "names",
    "phone",
    "email",
    "contact",
    "contacts",
    "address",
    "addresses",
    "case_text",
    "case_file",
    "worker",
    "workers",
    "complainant",
    "complainants",
    "raw_text",
    "prompt_text",
    "source_url",
    "url",
})
_SLUG = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
_SAFE_TEXT = re.compile(r"^[A-Za-z0-9 .,/()&:+#'_-]{1,220}$")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LONG_DIGITS = re.compile(r"\b\d{9,}\b")
_URL = re.compile(r"\b(?:https?://|www\.)", re.I)
_LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])", re.I)
PRIORITY_SIGNAL_TERMS = {
    "cross_border_scope": (
        "cross-border",
        "origin",
        "destination",
        "flag",
        "port",
        "crew nationality",
        "migration",
        "migrant",
        "forum",
        "regulator jurisdiction",
        "jurisdiction",
    ),
    "informal_publication": (
        "facebook",
        "whatsapp",
        "telegram",
        "social",
        "app-store",
        "registry",
        "community notices",
        "school social-media",
        "informal",
        "public notices",
    ),
    "privacy_or_retaliation": (
        "privacy",
        "retaliation",
        "unsafe disclosure",
        "small-community",
        "crew names",
        "contacts",
        "case-specific",
        "private",
        "immigration",
    ),
    "ordinary_protection_breadth": (
        "wage",
        "deduction",
        "debt",
        "fee",
        "housing",
        "tenancy",
        "injury",
        "occupational",
        "repatriation",
        "refund",
        "consumer",
        "education",
        "safety",
    ),
    "source_fragmentation": (
        "circular",
        "notice",
        "registry",
        "guidance",
        "license",
        "cadastre",
        "authority",
        "ministry",
        "ombuds",
        "court",
        "legal-aid",
        "public-interest",
    ),
}


def _safe_text(value: Any, *, fallback: str = "unknown") -> str:
    if not isinstance(value, str):
        return fallback
    text = value.strip()
    if text and _SAFE_TEXT.fullmatch(text) and not _has_sensitive_text(text):
        return text
    return fallback


def _safe_slug(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    if _SLUG.fullmatch(text):
        return text
    return "unknown"


def _has_sensitive_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LONG_DIGITS.search(text)
        or _URL.search(text)
        or _LOCAL_PATH.search(text)
        or "\\" in text
    )


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_text(item) for item in value if isinstance(item, str)]


def _scan_privacy(value: Any, *, path: str = "$") -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "sensitive_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
        "url_like_paths": [],
        "local_path_like_paths": [],
    }

    def walk(item: Any, current: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                child_path = f"{current}.{key}"
                if str(key).lower() in SENSITIVE_FIELD_NAMES:
                    findings["sensitive_field_paths"].append(child_path)
                walk(child, child_path)
        elif isinstance(item, list):
            for idx, child in enumerate(item):
                walk(child, f"{current}[{idx}]")
        elif isinstance(item, str):
            if _EMAIL.search(item):
                findings["email_like_paths"].append(current)
            if _PHONE.search(item):
                findings["phone_like_paths"].append(current)
            if _LONG_DIGITS.search(item):
                findings["long_digit_paths"].append(current)
            if _URL.search(item):
                findings["url_like_paths"].append(current)
            if _LOCAL_PATH.search(item) or "\\" in item:
                findings["local_path_like_paths"].append(current)

    walk(value, path)
    counts = {key.replace("_paths", ""): len(paths) for key, paths in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _pattern_issues(raw: Any, seen_ids: set[str]) -> list[str]:
    issues: list[str] = []
    if not isinstance(raw, dict):
        return ["pattern_not_object"]
    missing = sorted(REQUIRED_PATTERN_FIELDS - set(raw))
    if missing:
        issues.append("pattern_required_fields_missing")
    unknown = sorted(set(raw) - ALLOWED_PATTERN_FIELDS)
    if unknown:
        issues.append("pattern_unexpected_fields")
    if any(str(key).lower() in SENSITIVE_FIELD_NAMES for key in raw):
        issues.append("pattern_sensitive_fields_present")
    pattern_id = raw.get("id")
    if not isinstance(pattern_id, str) or not _SLUG.fullmatch(pattern_id):
        issues.append("pattern_id_not_safe_slug")
    elif pattern_id in seen_ids:
        issues.append("pattern_id_duplicate")
    status = raw.get("candidate_status")
    if status not in SAFE_STATUS:
        issues.append("pattern_candidate_status_invalid")
    for field in (
        "industry_scope",
        "legal_dimensions",
        "source_channels",
        "model_miss_patterns",
        "prompt_families",
        "source_gates",
        "do_not_score_until",
    ):
        value = raw.get(field)
        if not isinstance(value, list) or not value:
            issues.append(f"{field}_empty_or_not_list")
        elif any(not isinstance(item, str) or not _SAFE_TEXT.fullmatch(item) or _has_sensitive_text(item) for item in value):
            issues.append(f"{field}_contains_unsafe_text")
    for field in ("display_name", "active_domain"):
        if field in raw and (not isinstance(raw.get(field), str) or _safe_text(raw.get(field)) == "unknown"):
            issues.append(f"{field}_unsafe")
    return sorted(set(issues))


def _next_step(status: str) -> str:
    if status == "active_seed":
        return "continue source-object curation and keep comparable scoring blocked until local-law coverage is verified"
    if status == "candidate":
        return "create a propose-only domain seed only after a curator approves scope and source gates"
    return "park until the scope has a clear public-interest use case and source path"


def _priority_signal_counts(entry: dict[str, Any]) -> dict[str, int]:
    values: list[str] = [
        str(entry.get("display_name", "")),
        str(entry.get("candidate_status", "")),
        str(entry.get("active_domain", "")),
    ]
    for field in (
        "industry_scope",
        "legal_dimensions",
        "source_channels",
        "model_miss_patterns",
        "prompt_families",
        "source_gates",
        "do_not_score_until",
    ):
        values.extend(str(item) for item in entry.get(field, []))
    haystack = " ".join(values).lower()
    return {
        signal: sum(haystack.count(term) for term in terms)
        for signal, terms in PRIORITY_SIGNAL_TERMS.items()
    }


def _priority_score(entry: dict[str, Any], signals: list[str], signal_counts: dict[str, int]) -> int:
    signal_hit_count = sum(signal_counts.values())
    return (
        len(entry["legal_dimensions"]) * 4
        + len(entry["source_channels"]) * 3
        + len(entry["model_miss_patterns"]) * 4
        + len(entry["source_gates"]) * 5
        + len(entry["do_not_score_until"]) * 3
        + len(signals) * 6
        + min(signal_hit_count, 40) * 2
    )


def _priority_band(status: str, rank: int | None) -> str:
    if status == "active_seed":
        return "active_seed_followup"
    if status == "defer":
        return "deferred_until_scope_path_exists"
    if rank is None:
        return "candidate_unranked"
    if rank <= 2:
        return "priority_1_seed_after_curator_approval"
    if rank <= 4:
        return "priority_2_research_backlog"
    return "priority_3_watchlist"


def _attach_priority(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for entry in entries:
        signal_counts = _priority_signal_counts(entry)
        signals = sorted(signal for signal, count in signal_counts.items() if count)
        entry["expansion_priority"] = {
            "rank": None,
            "score": _priority_score(entry, signals, signal_counts),
            "band": _priority_band(entry["candidate_status"], None),
            "signals": signals,
            "signal_hit_count": sum(signal_counts.values()),
            "rationale": (
                "Prioritize candidates with broad legal dimensions, multiple source channels, "
                "many model-miss patterns, strict source gates, and recurring low-documentation signals."
            ),
            "ready_for_domain_seed": False,
            "ready_for_prompt_generation": False,
            "ready_for_comparable_scoring": False,
        }
    candidates = [
        entry for entry in entries
        if entry["candidate_status"] == "candidate"
    ]
    candidates.sort(key=lambda item: (-item["expansion_priority"]["score"], item["id"]))
    for rank, entry in enumerate(candidates, start=1):
        priority = entry["expansion_priority"]
        priority["rank"] = rank
        priority["band"] = _priority_band(entry["candidate_status"], rank)
    for entry in entries:
        if entry["candidate_status"] != "candidate":
            entry["expansion_priority"]["band"] = _priority_band(entry["candidate_status"], None)
    return entries


def _expansion_queue(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "rank": entry["expansion_priority"]["rank"],
            "pattern_id": entry["id"],
            "display_name": entry["display_name"],
            "priority_score": entry["expansion_priority"]["score"],
            "priority_band": entry["expansion_priority"]["band"],
            "signals": entry["expansion_priority"]["signals"],
            "required_source_gate_count": len(entry["source_gates"]),
            "next_step": entry["next_step"],
            "ready_for_domain_seed": False,
            "ready_for_prompt_generation": False,
            "ready_for_comparable_scoring": False,
        }
        for entry in entries
        if entry["candidate_status"] == "candidate"
    ]
    rows.sort(key=lambda item: (item["rank"] or 9999, item["pattern_id"]))
    return rows


def _plan_entry(raw: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    status = _safe_text(raw.get("candidate_status"))
    return {
        "id": _safe_slug(raw.get("id")),
        "display_name": _safe_text(raw.get("display_name")),
        "candidate_status": status,
        "active_domain": _safe_slug(raw.get("active_domain")) if raw.get("active_domain") else "",
        "industry_scope": _safe_list(raw.get("industry_scope")),
        "legal_dimensions": _safe_list(raw.get("legal_dimensions")),
        "source_channels": _safe_list(raw.get("source_channels")),
        "model_miss_patterns": _safe_list(raw.get("model_miss_patterns")),
        "prompt_families": _safe_list(raw.get("prompt_families")),
        "source_gates": _safe_list(raw.get("source_gates")),
        "do_not_score_until": _safe_list(raw.get("do_not_score_until")),
        "next_step": _next_step(status),
        "ready_for_comparable_scoring": False,
        "issues": issues,
    }


def build_plan(config: dict[str, Any]) -> dict[str, Any]:
    patterns = config.get("patterns") if isinstance(config, dict) else []
    raw_patterns = patterns if isinstance(patterns, list) else []
    seen_ids: set[str] = set()
    entries: list[dict[str, Any]] = []
    issue_counts: Counter[str] = Counter()

    if not isinstance(patterns, list):
        issue_counts["patterns_not_list"] += 1

    for raw in raw_patterns:
        issues = _pattern_issues(raw, seen_ids)
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            seen_ids.add(raw["id"])
            entries.append(_plan_entry(raw, issues))
        else:
            entries.append(_plan_entry({}, issues))
        issue_counts.update(issues)

    entries = _attach_priority(entries)
    entries.sort(key=lambda item: (item["candidate_status"], item["id"]))
    expansion_queue = _expansion_queue(entries)
    by_status = Counter(entry["candidate_status"] for entry in entries)
    legal_dimensions = sorted({dim for entry in entries for dim in entry["legal_dimensions"]})
    source_channels = sorted({channel for entry in entries for channel in entry["source_channels"]})
    priority_signals = sorted({
        signal for entry in entries for signal in entry["expansion_priority"]["signals"]
    })
    doc = {
        "manifest": {},
        "patterns": entries,
        "expansion_queue": expansion_queue,
        "coverage_summary": {
            "legal_dimensions": legal_dimensions,
            "source_channels": source_channels,
            "model_miss_pattern_count": sum(len(entry["model_miss_patterns"]) for entry in entries),
            "prompt_family_count": sum(len(entry["prompt_families"]) for entry in entries),
            "source_gate_count": sum(len(entry["source_gates"]) for entry in entries),
            "priority_signals": priority_signals,
            "priority_signal_count": len(priority_signals),
        },
    }
    privacy_scan = _scan_privacy(doc["patterns"])
    if privacy_scan.get("ok") is not True:
        issue_counts["privacy_scan_not_ok"] += 1
    manifest = {
        "schema_version": "regulatory_miss_pattern_plan.v1",
        "source_catalog": "configs/duecare/benchmarks/regulatory_miss_patterns.json",
        "catalog_status": ((config.get("_meta") or {}).get("status") if isinstance(config, dict) else None),
        "pattern_count": len(entries),
        "by_status": {key: by_status[key] for key in sorted(by_status)},
        "active_seed_count": by_status.get("active_seed", 0),
        "candidate_count": by_status.get("candidate", 0),
        "defer_count": by_status.get("defer", 0),
        "candidate_queue_count": len(expansion_queue),
        "top_candidate_id": expansion_queue[0]["pattern_id"] if expansion_queue else "",
        "safe_for_research_planning": not issue_counts,
        "ready_for_comparable_scoring": False,
        "privacy_scan": privacy_scan,
        "issues": {key: issue_counts[key] for key in sorted(issue_counts)},
        "note": (
            "This plan identifies adjacent benchmark candidates only. It does not verify law, fetch "
            "sources, add prompts, or authorize comparable scores. Each candidate must go through "
            "dated source-object curation, privacy review, and expert review first."
        ),
    }
    doc["manifest"] = manifest
    return doc


def render_markdown(doc: dict[str, Any]) -> str:
    manifest = doc["manifest"]
    lines = [
        "# Regulatory Miss Pattern Plan",
        "",
        "This is a propose-only sister-benchmark expansion plan. It is not legal advice, not source verification, and not comparable benchmark evidence.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Pattern count | {manifest['pattern_count']} |",
        f"| Active seeds | {manifest['active_seed_count']} |",
        f"| Candidate domains | {manifest['candidate_count']} |",
        f"| Deferred domains | {manifest['defer_count']} |",
        f"| Ranked candidate queue | {manifest['candidate_queue_count']} |",
        f"| Priority signals | {doc['coverage_summary']['priority_signal_count']} |",
        f"| Safe for research planning | {str(manifest['safe_for_research_planning']).lower()} |",
        f"| Ready for comparable scoring | {str(manifest['ready_for_comparable_scoring']).lower()} |",
        "",
        "## Candidate Patterns",
        "",
        "| ID | Status | Rank | Score | Priority band | Source gates | Next step |",
        "|---|---|---:|---:|---|---:|---|",
    ]
    for entry in doc["patterns"]:
        priority = entry["expansion_priority"]
        rank = priority["rank"] if priority["rank"] is not None else "n/a"
        lines.append(
            f"| `{entry['id']}` | {entry['candidate_status']} | {rank} | "
            f"{priority['score']} | {priority['band']} | {len(entry['source_gates'])} | {entry['next_step']} |"
        )
    lines.extend([
        "",
        "## Expansion Queue",
        "",
        "| Rank | Candidate | Score | Signals | Source gates |",
        "|---:|---|---:|---:|---:|",
    ])
    for row in doc["expansion_queue"]:
        lines.append(
            f"| {row['rank']} | `{row['pattern_id']}` | {row['priority_score']} | "
            f"{len(row['signals'])} | {row['required_source_gate_count']} |"
        )
    if not doc["expansion_queue"]:
        lines.append("| n/a | n/a | 0 | 0 | 0 |")
    lines.extend([
        "",
        "## Coverage Summary",
        "",
        f"- Legal dimensions: {len(doc['coverage_summary']['legal_dimensions'])}",
        f"- Source channel types: {len(doc['coverage_summary']['source_channels'])}",
        f"- Model-miss checks: {doc['coverage_summary']['model_miss_pattern_count']}",
        f"- Prompt-family sketches: {doc['coverage_summary']['prompt_family_count']}",
        f"- Source gates: {doc['coverage_summary']['source_gate_count']}",
        f"- Priority signals: {doc['coverage_summary']['priority_signal_count']}",
        "",
        "## Non-Scoring Rule",
        "",
        "Every pattern remains blocked for comparable scoring until concrete jurisdictions, source objects, privacy review, and expert review prove the local-law coverage required by the prompt.",
        "",
    ])
    if manifest["issues"]:
        lines.extend([
            "## Issues",
            "",
        ])
        for key, count in manifest["issues"].items():
            lines.append(f"- `{key}`: {count}")
        lines.append("")
    return "\n".join(lines)


def _load_config(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    config = _load_config(args.config)
    if config is None:
        print(f"[regulatory-miss-pattern-plan] unreadable config: {args.config}")
        return 1
    doc = build_plan(config)
    if args.validate:
        print(json.dumps(doc["manifest"], indent=2, ensure_ascii=False))
        return 0 if doc["manifest"]["safe_for_research_planning"] else 1
    if not doc["manifest"]["safe_for_research_planning"]:
        print(json.dumps(doc["manifest"], indent=2, ensure_ascii=False))
        print("[regulatory-miss-pattern-plan] config is unsafe; refusing to write plan")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(doc), encoding="utf-8")
    print(
        "[regulatory-miss-pattern-plan] "
        f"{doc['manifest']['pattern_count']} patterns "
        f"({doc['manifest']['candidate_count']} candidates) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
