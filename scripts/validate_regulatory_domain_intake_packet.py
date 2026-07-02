#!/usr/bin/env python3
"""Validate a curator-filled regulatory domain intake packet.

The blank intake packet is intentionally conservative. This validator is the
non-mutating gate for rows that a curator has filled in and marked ready for a
new propose-only domain seed.

Accepted rows become domain-seed proposals only. They still do not create files,
edit ``configs/duecare/benchmarks/domains/registry.json``, generate prompts, or
authorize comparable benchmark scoring.

Offline + deterministic. No model, no network, no credits.

    python scripts/validate_regulatory_domain_intake_packet.py
    python scripts/validate_regulatory_domain_intake_packet.py --validate
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any

import build_regulatory_domain_intake_packet as intake_builder
import build_regulatory_miss_pattern_plan as pattern_plan

_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PACKET = _ROOT / "reports" / "benchmark" / "regulatory_domain_intake_packet.json"
DEFAULT_REGISTRY = _ROOT / "configs" / "duecare" / "benchmarks" / "domains" / "registry.json"
OUT = _ROOT / "reports" / "benchmark" / "regulatory_domain_intake_validation.json"
MD_OUT = _ROOT / "reports" / "benchmark" / "regulatory_domain_intake_validation.md"

SCHEMA_VERSION = "regulatory_domain_intake_validation.v1"
SAFE_DOMAIN_ID = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
APPROVED_DECISION = "approved_for_seed"
PASSIVE_DECISIONS = frozenset({"needs_review", "deferred", "rejected"})
APPROVED_REVIEW_STATUS = "approved"
REVIEW_GATE_KEYS = (
    "privacy_review_status",
    "source_path_review_status",
    "expert_review_status",
    "domain_registry_review_status",
)
SCOPE_KEYS = (
    "approved_scope_statement",
    "concrete_jurisdiction_strategy",
    "primary_public_interest_use_case",
)
ARTIFACT_KEYS = (
    "scheme_pack_path",
    "grounding_manifest_path",
    "source_research_plan_path",
    "source_review_packet_path",
    "expert_review_evidence",
)


def _load_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return "external"


def _safe_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    date_redacted = ISO_DATE.sub("date", text)
    return bool(text and pattern_plan._SAFE_TEXT.fullmatch(text) and not pattern_plan._has_sensitive_text(date_redacted))


def _safe_nonblank_text(value: Any) -> bool:
    return _safe_text(value) and bool(value.strip())


def _registry_domain_ids(path: pathlib.Path) -> set[str]:
    registry = _load_json(path)
    domains = registry.get("domains") if isinstance(registry, dict) else {}
    return set(domains) if isinstance(domains, dict) else set()


def _canonical_artifact_path(domain_id: str, key: str) -> str:
    if key == "scheme_pack_path":
        return f"configs/duecare/benchmarks/domains/{domain_id}/scheme_prompts.jsonl"
    if key == "grounding_manifest_path":
        return f"configs/duecare/benchmarks/domains/{domain_id}/grounding_sources.json"
    if key == "source_research_plan_path":
        return f"reports/benchmark/{domain_id}_source_research_plan.json"
    if key == "source_review_packet_path":
        return f"reports/benchmark/{domain_id}_source_review_packet.json"
    raise KeyError(key)


def _privacy_scan_view(packet: dict[str, Any]) -> dict[str, Any]:
    view = intake_builder._privacy_scan_view(packet)
    meta = view.get("_meta") if isinstance(view, dict) else {}
    if isinstance(meta, dict):
        for key in ("source_packet_sha256", "source_catalog_sha256"):
            if meta.get(key):
                meta[key] = "sha256-redacted-for-privacy-scan"

    def redact_dates(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: redact_dates(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact_dates(item) for item in value]
        if isinstance(value, str):
            return ISO_DATE.sub("date-redacted", value)
        return value

    view = redact_dates(view)
    return view


def _validate_approved_row(row: dict[str, Any], existing_domains: set[str]) -> tuple[list[str], dict[str, Any] | None]:
    issues: list[str] = []
    scope = row.get("curator_scope") if isinstance(row.get("curator_scope"), dict) else {}
    artifacts = row.get("required_artifacts") if isinstance(row.get("required_artifacts"), dict) else {}
    gates = row.get("review_gates") if isinstance(row.get("review_gates"), dict) else {}
    readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}

    domain_id = scope.get("proposed_domain_id", "")
    if not isinstance(domain_id, str) or not SAFE_DOMAIN_ID.fullmatch(domain_id):
        issues.append("proposed_domain_id_not_safe")
        domain_id = ""
    elif domain_id in existing_domains:
        issues.append("proposed_domain_id_conflicts_existing_domain")

    for key in SCOPE_KEYS:
        if not _safe_nonblank_text(scope.get(key)):
            issues.append(f"{key}_missing_or_unsafe")
    for key in REVIEW_GATE_KEYS:
        if gates.get(key) != APPROVED_REVIEW_STATUS:
            issues.append(f"{key}_not_approved")
    for key in ("scheme_pack_path", "grounding_manifest_path", "source_research_plan_path", "source_review_packet_path"):
        expected = _canonical_artifact_path(domain_id, key) if domain_id else ""
        if artifacts.get(key) != expected:
            issues.append(f"{key}_not_canonical")
    if not _safe_nonblank_text(artifacts.get("expert_review_evidence")):
        issues.append("expert_review_evidence_missing_or_unsafe")
    if readiness.get("ready_for_domain_seed") is not True:
        issues.append("ready_for_domain_seed_not_true")
    if readiness.get("ready_for_prompt_generation") is not False:
        issues.append("ready_for_prompt_generation_must_remain_false")
    if readiness.get("ready_for_comparable_scoring") is not False:
        issues.append("ready_for_comparable_scoring_must_remain_false")

    if issues:
        return issues, None
    proposal = {
        "pattern_id": row["pattern_id"],
        "proposed_domain_id": domain_id,
        "display_name": row.get("display_name", ""),
        "scheme_pack_path": artifacts["scheme_pack_path"],
        "grounding_manifest_path": artifacts["grounding_manifest_path"],
        "source_research_plan_path": artifacts["source_research_plan_path"],
        "source_review_packet_path": artifacts["source_review_packet_path"],
        "source_gates": row.get("required_source_gates", []),
        "do_not_score_until": row.get("do_not_score_until", []),
        "ready_for_prompt_generation": False,
        "ready_for_comparable_scoring": False,
    }
    return [], proposal


def _validate_candidate_row(row: Any, existing_domains: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "pattern_id": "unknown",
            "proposed_domain_id": "",
            "scope_decision": "unknown",
            "validation_status": "invalid",
            "accepted_for_domain_seed_proposal": False,
            "issues": ["row_not_object"],
        }

    issues: list[str] = []
    pattern_id = row.get("pattern_id", "")
    if not isinstance(pattern_id, str) or not SAFE_DOMAIN_ID.fullmatch(pattern_id):
        issues.append("pattern_id_not_safe")
        pattern_id = "unknown"
    scope = row.get("curator_scope") if isinstance(row.get("curator_scope"), dict) else {}
    readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}
    decision = scope.get("scope_decision", "unknown")
    domain_id = scope.get("proposed_domain_id", "") if isinstance(scope, dict) else ""
    proposal = None

    if decision == APPROVED_DECISION:
        approved_issues, proposal = _validate_approved_row(row, existing_domains)
        issues.extend(approved_issues)
    elif decision in PASSIVE_DECISIONS:
        if readiness.get("ready_for_domain_seed") is not False:
            issues.append("passive_row_claims_ready_for_domain_seed")
        if readiness.get("ready_for_prompt_generation") is not False:
            issues.append("ready_for_prompt_generation_must_remain_false")
        if readiness.get("ready_for_comparable_scoring") is not False:
            issues.append("ready_for_comparable_scoring_must_remain_false")
    else:
        issues.append("scope_decision_invalid")

    if readiness.get("ready_for_prompt_generation") is True:
        issues.append("prompt_generation_claim_not_allowed")
    if readiness.get("ready_for_comparable_scoring") is True:
        issues.append("comparable_scoring_claim_not_allowed")

    accepted = proposal is not None and not issues
    if accepted:
        status = "accepted_for_domain_seed_proposal"
    elif issues:
        status = "invalid"
    else:
        status = "pending_or_deferred"
    return {
        "pattern_id": pattern_id,
        "proposed_domain_id": domain_id if isinstance(domain_id, str) else "",
        "scope_decision": decision,
        "validation_status": status,
        "accepted_for_domain_seed_proposal": accepted,
        "issues": sorted(set(issues)),
        "proposal": proposal,
    }


def validate_intake_packet(
    packet: dict[str, Any],
    *,
    packet_path: pathlib.Path | None = None,
    registry_path: pathlib.Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    existing_domains = _registry_domain_ids(registry_path)
    candidate_rows = packet.get("candidate_domain_intake")
    rows = [
        _validate_candidate_row(row, existing_domains)
        for row in (candidate_rows if isinstance(candidate_rows, list) else [])
    ]
    issues: list[str] = []
    if (packet.get("_meta") or {}).get("schema_version") != intake_builder.SCHEMA_VERSION:
        issues.append("packet_schema_version_unexpected")
    if not isinstance(candidate_rows, list):
        issues.append("candidate_domain_intake_not_list")
    privacy_scan = pattern_plan._scan_privacy(_privacy_scan_view(packet))
    if privacy_scan.get("ok") is not True:
        issues.append("packet_privacy_scan_not_ok")
    row_issue_count = sum(len(row["issues"]) for row in rows)
    if row_issue_count:
        issues.append("candidate_row_validation_issues")
    proposals = [row["proposal"] for row in rows if row.get("proposal")]
    report = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "source_packet_path": _display_path(packet_path) if packet_path else "n/a",
            "registry_path": _display_path(registry_path),
            "source_packet_schema": (packet.get("_meta") or {}).get("schema_version"),
            "candidate_count": len(rows),
            "accepted_for_domain_seed_proposal_count": len(proposals),
            "pending_or_deferred_count": sum(row["validation_status"] == "pending_or_deferred" for row in rows),
            "invalid_count": sum(row["validation_status"] == "invalid" for row in rows),
            "ready_for_prompt_generation_count": 0,
            "ready_for_comparable_scoring_count": 0,
            "validation_ok": not issues,
            "issues": sorted(set(issues)),
            "privacy_scan": privacy_scan,
            "note": (
                "Accepted rows are only proposals for a future propose-only domain seed. "
                "This report does not create domain files, edit the registry, generate prompts, "
                "or authorize comparable scoring."
            ),
        },
        "candidate_rows": [{k: v for k, v in row.items() if k != "proposal"} for row in rows],
        "domain_seed_proposals": proposals,
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    meta = report["_meta"]
    lines = [
        "# Regulatory Domain Intake Validation",
        "",
        "This report validates curator-filled intake rows. Accepted rows are proposals only; they are not domain registry updates or benchmark scores.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Candidate rows | {meta['candidate_count']} |",
        f"| Accepted domain-seed proposals | {meta['accepted_for_domain_seed_proposal_count']} |",
        f"| Pending or deferred rows | {meta['pending_or_deferred_count']} |",
        f"| Invalid rows | {meta['invalid_count']} |",
        f"| Ready for prompt generation | {meta['ready_for_prompt_generation_count']} |",
        f"| Ready for comparable scoring | {meta['ready_for_comparable_scoring_count']} |",
        f"| Validation OK | {str(meta['validation_ok']).lower()} |",
        "",
        "## Candidate Rows",
        "",
        "| Pattern | Decision | Status | Issues |",
        "|---|---|---|---:|",
    ]
    for row in report["candidate_rows"]:
        lines.append(
            f"| `{row['pattern_id']}` | {row['scope_decision']} | "
            f"{row['validation_status']} | {len(row['issues'])} |"
        )
    lines.extend([
        "",
        "## Domain-Seed Proposals",
        "",
        "| Pattern | Proposed domain | Prompt generation | Comparable scoring |",
        "|---|---|---:|---:|",
    ])
    for proposal in report["domain_seed_proposals"]:
        lines.append(
            f"| `{proposal['pattern_id']}` | `{proposal['proposed_domain_id']}` | "
            f"{str(proposal['ready_for_prompt_generation']).lower()} | "
            f"{str(proposal['ready_for_comparable_scoring']).lower()} |"
        )
    if not report["domain_seed_proposals"]:
        lines.append("| n/a | n/a | false | false |")
    if meta["issues"]:
        lines.extend(["", "## Issues", ""])
        for issue in meta["issues"]:
            lines.append(f"- `{issue}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packet", type=pathlib.Path, default=DEFAULT_PACKET)
    ap.add_argument("--registry", type=pathlib.Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--markdown-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--validate", action="store_true", help="print the validation manifest only; write nothing")
    args = ap.parse_args(argv)

    packet = _load_json(args.packet)
    if packet is None:
        print(f"[regulatory-domain-intake-validation] unreadable packet: {args.packet}")
        return 1
    report = validate_intake_packet(packet, packet_path=args.packet, registry_path=args.registry)
    meta = report["_meta"]
    if args.validate:
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        return 0 if meta["validation_ok"] else 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(
        "[regulatory-domain-intake-validation] "
        f"{meta['accepted_for_domain_seed_proposal_count']} accepted; "
        f"{meta['invalid_count']} invalid -> {args.out}"
    )
    return 0 if meta["validation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
