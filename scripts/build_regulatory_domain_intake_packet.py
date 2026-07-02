#!/usr/bin/env python3
"""Build a blank intake packet for regulatory-miss domain candidates.

This is the operational handoff after ``build_regulatory_miss_pattern_plan``.
It turns each safe candidate pattern into a curator-facing intake row for
deciding whether a new propose-only benchmark domain should be created.

The packet is deliberately blank where human judgment is required. It does not
verify law, fetch sources, create prompt rows, edit the domain registry, or mark
anything ready for comparable scoring.

Offline + deterministic. No model, no network, no credits.

    python scripts/build_regulatory_domain_intake_packet.py
    python scripts/build_regulatory_domain_intake_packet.py --validate
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

import build_regulatory_miss_pattern_plan as pattern_plan

_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = _ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json"
OUT = _ROOT / "reports" / "benchmark" / "regulatory_domain_intake_packet.json"
MD_OUT = _ROOT / "reports" / "benchmark" / "regulatory_domain_intake_packet.md"

SCHEMA_VERSION = "regulatory_domain_intake_packet.v1"


def _file_sha256(path: pathlib.Path | None) -> str | None:
    if path is None:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return "external"


def _load_config(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _candidate_intake_row(pattern: dict[str, Any]) -> dict[str, Any]:
    return {
        "pattern_id": pattern["id"],
        "display_name": pattern["display_name"],
        "candidate_status": pattern["candidate_status"],
        "expansion_priority": pattern.get("expansion_priority", {}),
        "industry_scope": pattern["industry_scope"],
        "legal_dimensions": pattern["legal_dimensions"],
        "source_channel_requirements": pattern["source_channels"],
        "model_miss_patterns": pattern["model_miss_patterns"],
        "prompt_family_sketches": pattern["prompt_families"],
        "required_source_gates": pattern["source_gates"],
        "do_not_score_until": pattern["do_not_score_until"],
        "curator_scope": {
            "scope_decision": "needs_review",
            "proposed_domain_id": "",
            "approved_scope_statement": "",
            "concrete_jurisdiction_strategy": "",
            "primary_public_interest_use_case": "",
        },
        "required_artifacts": {
            "scheme_pack_path": "",
            "grounding_manifest_path": "",
            "source_research_plan_path": "",
            "source_review_packet_path": "",
            "expert_review_evidence": "",
        },
        "review_gates": {
            "privacy_review_status": "not_started",
            "source_path_review_status": "not_started",
            "expert_review_status": "not_started",
            "domain_registry_review_status": "not_started",
        },
        "readiness": {
            "ready_for_domain_seed": False,
            "ready_for_prompt_generation": False,
            "ready_for_comparable_scoring": False,
        },
    }


def _priority_rank(row: dict[str, Any]) -> int:
    priority = row.get("expansion_priority") if isinstance(row.get("expansion_priority"), dict) else {}
    rank = priority.get("rank")
    return rank if isinstance(rank, int) and rank > 0 else 9999


def _active_seed_row(pattern: dict[str, Any]) -> dict[str, Any]:
    return {
        "pattern_id": pattern["id"],
        "display_name": pattern["display_name"],
        "active_domain": pattern["active_domain"],
        "expansion_priority": pattern.get("expansion_priority", {}),
        "next_step": pattern["next_step"],
        "outstanding_source_gates": pattern["source_gates"],
        "do_not_score_until": pattern["do_not_score_until"],
        "ready_for_comparable_scoring": False,
    }


def _blank_field_audit(packet: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for idx, row in enumerate(packet.get("candidate_domain_intake") or []):
        prefix = f"candidate_domain_intake[{idx}]"
        curator_scope = row.get("curator_scope") or {}
        required_artifacts = row.get("required_artifacts") or {}
        review_gates = row.get("review_gates") or {}
        readiness = row.get("readiness") or {}
        if curator_scope.get("scope_decision") != "needs_review":
            issues.append(f"{prefix}.scope_decision_not_needs_review")
        for key in (
            "proposed_domain_id",
            "approved_scope_statement",
            "concrete_jurisdiction_strategy",
            "primary_public_interest_use_case",
        ):
            if curator_scope.get(key) != "":
                issues.append(f"{prefix}.curator_scope.{key}_not_blank")
        for key in (
            "scheme_pack_path",
            "grounding_manifest_path",
            "source_research_plan_path",
            "source_review_packet_path",
            "expert_review_evidence",
        ):
            if required_artifacts.get(key) != "":
                issues.append(f"{prefix}.required_artifacts.{key}_not_blank")
        for key in (
            "privacy_review_status",
            "source_path_review_status",
            "expert_review_status",
            "domain_registry_review_status",
        ):
            if review_gates.get(key) != "not_started":
                issues.append(f"{prefix}.review_gates.{key}_not_not_started")
        for key in (
            "ready_for_domain_seed",
            "ready_for_prompt_generation",
            "ready_for_comparable_scoring",
        ):
            if readiness.get(key) is not False:
                issues.append(f"{prefix}.readiness.{key}_not_false")
    return {
        "ok": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def _privacy_scan_view(packet: dict[str, Any]) -> dict[str, Any]:
    view = json.loads(json.dumps(packet))
    meta = view.get("_meta") if isinstance(view, dict) else {}
    if isinstance(meta, dict) and meta.get("source_catalog_sha256"):
        meta["source_catalog_sha256"] = "sha256-redacted-for-privacy-scan"
    return view


def build_intake_packet(config: dict[str, Any], *, config_path: pathlib.Path | None = None) -> dict[str, Any]:
    plan = pattern_plan.build_plan(config)
    plan_manifest = plan["manifest"]
    active_rows = [
        _active_seed_row(pattern)
        for pattern in plan["patterns"]
        if pattern.get("candidate_status") == "active_seed"
    ]
    candidate_rows = [
        _candidate_intake_row(pattern)
        for pattern in plan["patterns"]
        if pattern.get("candidate_status") == "candidate"
    ]
    candidate_rows.sort(key=lambda row: (_priority_rank(row), row["pattern_id"]))
    packet = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "source_catalog": _display_path(config_path) if config_path else plan_manifest["source_catalog"],
            "source_catalog_sha256": _file_sha256(config_path),
            "source_plan_schema": plan_manifest["schema_version"],
            "status": (
                "blank curator intake; non-mutating; not legal advice; not source verification; "
                "not comparable benchmark evidence"
            ),
        },
        "active_seed_followups": active_rows,
        "candidate_domain_intake": candidate_rows,
    }
    blank_audit = _blank_field_audit(packet)
    privacy_scan = pattern_plan._scan_privacy(_privacy_scan_view(packet))
    issues: list[str] = []
    if plan_manifest.get("safe_for_research_planning") is not True:
        issues.append("source_pattern_plan_not_safe")
    if privacy_scan.get("ok") is not True:
        issues.append("intake_packet_privacy_scan_not_ok")
    if blank_audit.get("ok") is not True:
        issues.append("intake_packet_blank_field_audit_not_ok")
    if len(candidate_rows) != plan_manifest.get("candidate_count"):
        issues.append("candidate_count_mismatch")
    packet["_meta"].update({
        "pattern_count": plan_manifest["pattern_count"],
        "active_seed_count": len(active_rows),
            "candidate_count": len(candidate_rows),
            "candidate_queue_count": plan_manifest["candidate_queue_count"],
            "top_candidate_id": plan_manifest["top_candidate_id"],
            "ready_for_domain_seed_count": 0,
        "ready_for_prompt_generation_count": 0,
        "ready_for_comparable_scoring_count": 0,
        "safe_for_curator_intake": not issues,
        "issues": issues,
        "privacy_scan": privacy_scan,
        "blank_field_audit": blank_audit,
        "note": (
            "Fill this packet only with scoped, public-interest, non-PII curation decisions. "
            "Do not add source URLs, contact details, raw case text, or legal claims here; "
            "those belong in a source-review packet after privacy and expert review gates."
        ),
    })
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    meta = packet["_meta"]
    lines = [
        "# Regulatory Domain Intake Packet",
        "",
        "This is a blank curator intake packet for deciding which regulatory-miss candidates should become propose-only benchmark domain seeds.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Pattern count | {meta['pattern_count']} |",
        f"| Active seed followups | {meta['active_seed_count']} |",
        f"| Candidate intake rows | {meta['candidate_count']} |",
        f"| Ranked candidate queue | {meta['candidate_queue_count']} |",
        f"| Ready for domain seed | {meta['ready_for_domain_seed_count']} |",
        f"| Ready for prompt generation | {meta['ready_for_prompt_generation_count']} |",
        f"| Ready for comparable scoring | {meta['ready_for_comparable_scoring_count']} |",
        f"| Safe for curator intake | {str(meta['safe_for_curator_intake']).lower()} |",
        "",
        "## Candidate Intake Rows",
        "",
        "| Pattern | Status | Rank | Score | Legal dimensions | Source gates |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in packet["candidate_domain_intake"]:
        priority = row.get("expansion_priority") if isinstance(row.get("expansion_priority"), dict) else {}
        rank = priority.get("rank") if priority.get("rank") is not None else "n/a"
        lines.append(
            f"| `{row['pattern_id']}` | {row['curator_scope']['scope_decision']} | "
            f"{rank} | {priority.get('score', 0)} | "
            f"{len(row['legal_dimensions'])} | {len(row['required_source_gates'])} |"
        )
    lines.extend([
        "",
        "## Active Seed Followups",
        "",
        "| Pattern | Active domain | Ready for comparable scoring |",
        "|---|---|---:|",
    ])
    for row in packet["active_seed_followups"]:
        lines.append(
            f"| `{row['pattern_id']}` | `{row['active_domain']}` | "
            f"{str(row['ready_for_comparable_scoring']).lower()} |"
        )
    lines.extend([
        "",
        "## Intake Rule",
        "",
        "Every candidate starts with blank curator fields, review gates set to `not_started`, and readiness flags set to `false`.",
        "",
    ])
    if meta["issues"]:
        lines.extend(["## Issues", ""])
        for issue in meta["issues"]:
            lines.append(f"- `{issue}`")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--validate", action="store_true", help="print the packet manifest only; write nothing")
    args = ap.parse_args(argv)

    config = _load_config(args.config)
    if config is None:
        print(f"[regulatory-domain-intake] unreadable config: {args.config}")
        return 1
    packet = build_intake_packet(config, config_path=args.config)
    meta = packet["_meta"]
    if args.validate:
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        return 0 if meta["safe_for_curator_intake"] else 1
    if not meta["safe_for_curator_intake"]:
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        print("[regulatory-domain-intake] intake packet is unsafe; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(packet), encoding="utf-8")
    print(
        "[regulatory-domain-intake] "
        f"{meta['candidate_count']} candidate rows; {meta['active_seed_count']} active followups -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
