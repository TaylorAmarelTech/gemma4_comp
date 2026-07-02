#!/usr/bin/env python3
"""Build a source-channel matrix for the global protections sister project.

The project needs source discipline before it needs more prompts. This command
turns the charter's target jurisdiction families into a curator work matrix for
official, public-interest, informal-publication, and expert-review source
channels. It does not fetch sources, verify law, create source rows, or
authorize scoring.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_global_protections_project_plan as project_plan_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_source_channel_matrix.json"
MD_OUT = OUT_DIR / "global_protections_source_channel_matrix.md"

SOURCE_CHANNELS = [
    {
        "id": "official_gazette_or_law_portal",
        "label": "Official gazette or law portal",
        "source_role": "primary_official_law",
        "authority_tier": "primary_legal_authority",
        "claim_use": "may_support_legal_claim_after_source_path_privacy_and_expert_review",
        "priority": 10,
        "evidence_status": "candidate_until_dated_archived_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "issuing authority",
            "jurisdiction",
            "publication date or access date",
            "archive status",
            "language",
            "legal scope note",
        ],
        "review_gates": ["source_path_review", "privacy_review", "expert_review"],
        "corroboration_required": [
            "dated archive",
            "jurisdiction scope",
            "expert review",
        ],
        "rejection_triggers": [
            "undated extract",
            "private or paywalled case row",
            "missing jurisdiction scope",
        ],
    },
    {
        "id": "labour_or_migration_ministry_notice",
        "label": "Labour or migration ministry notice",
        "source_role": "official_administrative_rule",
        "authority_tier": "official_administrative_authority",
        "claim_use": "may_support_legal_claim_after_source_path_privacy_and_expert_review",
        "priority": 20,
        "evidence_status": "candidate_until_dated_archived_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "ministry or agency authority",
            "jurisdiction",
            "notice date or access date",
            "archive status",
            "affected worker group",
            "legal scope note",
        ],
        "review_gates": ["source_path_review", "privacy_review", "expert_review"],
        "corroboration_required": [
            "dated issuer page",
            "affected worker group scope",
            "expert review",
        ],
        "rejection_triggers": [
            "unattributed repost",
            "stale policy without date",
            "broad corridor label without forum scope",
        ],
    },
    {
        "id": "regulator_registry_or_license_list",
        "label": "Regulator registry or license list",
        "source_role": "official_status_or_forum_locator",
        "authority_tier": "official_registry_authority",
        "claim_use": "locator_or_status_only_needs_primary_law_source_for_normative_claim",
        "priority": 30,
        "evidence_status": "candidate_until_dated_archived_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "registry authority",
            "jurisdiction",
            "access date",
            "archive status",
            "entity type covered",
            "status-field explanation",
        ],
        "review_gates": ["source_path_review", "privacy_review", "expert_review"],
        "corroboration_required": [
            "dated registry snapshot",
            "status-field interpretation",
            "privacy review",
        ],
        "rejection_triggers": [
            "raw complainant row",
            "private address or phone field",
            "license status without access date",
        ],
    },
    {
        "id": "court_or_tribunal_index",
        "label": "Court or tribunal index",
        "source_role": "public_adjudication_context",
        "authority_tier": "public_adjudication_record",
        "claim_use": "adjudication_context_only_needs_primary_law_source_for_normative_claim",
        "priority": 40,
        "evidence_status": "candidate_until_privacy_redacted_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "court or tribunal",
            "jurisdiction",
            "decision date or access date",
            "archive status",
            "case anonymization status",
            "issue scope note",
        ],
        "review_gates": ["privacy_review", "source_path_review", "expert_review"],
        "corroboration_required": [
            "redacted public-interest record",
            "issue-scope note",
            "expert review",
        ],
        "rejection_triggers": [
            "named worker or complainant",
            "private household identifier",
            "case-level row without public-interest redaction",
        ],
    },
    {
        "id": "ombuds_or_rights_commission_report",
        "label": "Ombuds or rights commission report",
        "source_role": "public_accountability_context",
        "authority_tier": "public_accountability_body",
        "claim_use": "accountability_context_only_needs_primary_law_source_for_normative_claim",
        "priority": 50,
        "evidence_status": "candidate_until_dated_archived_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "public body",
            "jurisdiction",
            "publication date or access date",
            "archive status",
            "population covered",
            "finding scope note",
        ],
        "review_gates": ["privacy_review", "source_path_review", "expert_review"],
        "corroboration_required": [
            "dated report",
            "population-scope note",
            "local-law source for legal rule",
        ],
        "rejection_triggers": [
            "individual complaint details",
            "small-community identifier",
            "undated excerpt",
        ],
    },
    {
        "id": "consular_or_embassy_advisory",
        "label": "Consular or embassy advisory",
        "source_role": "cross_border_remedy_context",
        "authority_tier": "official_cross_border_advisory",
        "claim_use": "remedy_context_only_needs_primary_law_source_for_normative_claim",
        "priority": 60,
        "evidence_status": "candidate_until_dated_archived_and_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "issuing mission",
            "origin or destination jurisdiction",
            "advisory date or access date",
            "archive status",
            "covered worker group",
            "remedy scope note",
        ],
        "review_gates": ["source_path_review", "privacy_review", "expert_review"],
        "corroboration_required": [
            "issuing mission",
            "origin-destination scope",
            "versioned advisory source",
        ],
        "rejection_triggers": [
            "hotline number without versioned source object",
            "informal repost without issuer",
            "unclear origin or destination scope",
        ],
    },
    {
        "id": "social_channel_notice_or_scanned_circular",
        "label": "Social-channel notice or scanned circular",
        "source_role": "informal_publication_lead",
        "authority_tier": "informal_publication_lead",
        "claim_use": "lead_only_never_standalone_legal_claim",
        "priority": 70,
        "evidence_status": "lead_only_until_archived_dated_and_public_interest_reviewed",
        "informal_publication": True,
        "required_metadata": [
            "publisher identity class",
            "jurisdiction or forum",
            "posted date or capture date",
            "archive status",
            "language",
            "official-source follow-up target",
        ],
        "review_gates": [
            "source_path_review",
            "privacy_review",
            "public_interest_review",
            "expert_review",
        ],
        "corroboration_required": [
            "publisher identity class",
            "archived dated capture",
            "official-source follow-up",
        ],
        "rejection_triggers": [
            "names or private messages",
            "complaint thread",
            "unarchived screenshot",
            "no official-source follow-up path",
        ],
    },
    {
        "id": "ngo_ilo_iom_un_public_interest_report",
        "label": "NGO, ILO, IOM, or UN public-interest report",
        "source_role": "public_interest_context",
        "authority_tier": "public_interest_context",
        "claim_use": "context_only_needs_primary_law_source_for_normative_claim",
        "priority": 80,
        "evidence_status": "context_only_until_local_law_source_is_present",
        "informal_publication": False,
        "required_metadata": [
            "publisher",
            "jurisdiction or corridor scope",
            "publication date",
            "archive status",
            "methodology note",
            "local-law dependency note",
        ],
        "review_gates": ["privacy_review", "source_path_review", "expert_review"],
        "corroboration_required": [
            "dated methodology",
            "local-law dependency",
            "privacy review",
        ],
        "rejection_triggers": [
            "case narrative with identifying details",
            "international anchor treated as local law",
            "no dated methodology",
        ],
    },
    {
        "id": "local_language_news_or_archive",
        "label": "Local-language news or public archive",
        "source_role": "corroborating_public_context",
        "authority_tier": "public_media_context",
        "claim_use": "corroboration_only_needs_official_or_expert_source_for_normative_claim",
        "priority": 90,
        "evidence_status": "corroboration_only_until_official_or_expert_reviewed",
        "informal_publication": False,
        "required_metadata": [
            "publisher",
            "jurisdiction",
            "publication date or access date",
            "archive status",
            "language",
            "claim-to-source mapping note",
        ],
        "review_gates": ["privacy_review", "source_path_review", "expert_review"],
        "corroboration_required": [
            "dated publisher record",
            "claim-to-source mapping",
            "official or expert corroboration",
        ],
        "rejection_triggers": [
            "victim-identifying report",
            "rumor or unattributed quotation",
            "no date",
        ],
    },
    {
        "id": "practitioner_or_expert_review_note",
        "label": "Practitioner or expert review note",
        "source_role": "review_gate_not_standalone_source",
        "authority_tier": "expert_review_gate",
        "claim_use": "review_gate_only_not_source_claim",
        "priority": 100,
        "evidence_status": "review_gate_only_not_source_claim",
        "informal_publication": False,
        "required_metadata": [
            "reviewer role class",
            "jurisdiction competence note",
            "review date",
            "conflict note",
            "source rows reviewed",
            "limits of review",
        ],
        "review_gates": ["privacy_review", "expert_review"],
        "corroboration_required": [
            "reviewer competence note",
            "source rows reviewed",
            "conflict note",
        ],
        "rejection_triggers": [
            "private legal advice",
            "unconsented identity detail",
            "unsupported claim without source row",
        ],
    },
]
DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]


def legal_claim_anchor_source_channel_ids() -> list[str]:
    """Return source-channel IDs allowed to anchor legal claims after review."""
    return [
        str(channel["id"])
        for channel in SOURCE_CHANNELS
        if str(channel.get("claim_use", "")).startswith("may_support_legal_claim")
        and channel.get("informal_publication") is False
    ]


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
        return path.as_posix()


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _slug_family(value: str, index: int) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:54] if slug else f"jurisdiction_family_{index:02d}"


def _project_doc_from_config(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    config = _load_json(config_path)
    if config is None:
        raise ValueError(f"unreadable global protections project config: {config_path}")
    registry = _load_json(registry_path)
    catalog = _load_json(regulatory_catalog_path)
    return project_plan_builder.build_project_plan(
        config,
        config_path=config_path,
        registry=registry,
        regulatory_catalog=catalog,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _matrix_row(family: str, family_index: int, channel: dict[str, Any]) -> dict[str, Any]:
    family_slug = _slug_family(family, family_index)
    channel_id = str(channel["id"])
    informal = bool(channel["informal_publication"])
    authenticity_controls = [
        "publisher or issuer identity reviewed",
        "capture provenance recorded",
        "dated archive or access record captured",
    ]
    volatility_controls = [
        "source path stability noted",
        "change or deletion risk marked",
        "currentness window recorded",
    ]
    if informal:
        authenticity_controls = [
            "publisher identity class reviewed",
            "original-vs-repost status marked",
            "capture provenance and hash recorded",
            "screenshot or scanned-document custody noted",
        ]
        volatility_controls = [
            "archived dated capture required",
            "deletion or post-edit risk marked",
            "official-source follow-up target recorded",
            "not promoted from screenshot alone",
        ]
    return {
        "id": f"GPSC-{family_index:02d}-{channel_id}",
        "jurisdiction_family": family,
        "jurisdiction_family_id": family_slug,
        "source_channel_id": channel_id,
        "source_channel_label": channel["label"],
        "source_role": channel["source_role"],
        "authority_tier": channel["authority_tier"],
        "claim_use": channel["claim_use"],
        "priority": channel["priority"],
        "evidence_status": channel["evidence_status"],
        "informal_publication": channel["informal_publication"],
        "required_metadata": list(channel["required_metadata"]),
        "review_gates": list(channel["review_gates"]),
        "corroboration_required": list(channel["corroboration_required"]),
        "rejection_triggers": list(channel["rejection_triggers"]),
        "authenticity_controls_required": authenticity_controls,
        "volatility_controls_required": volatility_controls,
        "authenticity_volatility_status": "not_started",
        "informal_publication_claim_boundary": (
            "lead_only_until_authenticity_volatility_and_official_follow_up_review"
            if informal
            else "not_applicable"
        ),
        "ready_for_manifest_promotion": False,
        "ready_for_prompt_generation": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
        "blocks": [
            "manifest_promotion",
            "prompt_generation",
            "training_use",
            "public_claims",
            "worker_facing_use",
            "comparable_scoring",
        ],
        "next_step": (
            "collect public, dated, archived metadata for this channel and keep it out of "
            "scoring until privacy and expert review pass"
        ),
    }


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def build_source_channel_matrix(
    *,
    project_doc: dict[str, Any] | None = None,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
) -> dict[str, Any]:
    """Return a non-fetching source-channel matrix for the project charter."""
    project_doc = project_doc or _project_doc_from_config(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    project_summary = project_doc["summary"]
    families = list(project_doc["scope"]["target_jurisdiction_families"])
    rows = [
        _matrix_row(family, family_index, channel)
        for family_index, family in enumerate(families, start=1)
        for channel in SOURCE_CHANNELS
    ]
    ready_flags = {
        "manifest_promotion": any(row["ready_for_manifest_promotion"] for row in rows),
        "prompt_generation": any(row["ready_for_prompt_generation"] for row in rows),
        "training_use": any(row["ready_for_training_use"] for row in rows),
        "public_claims": any(row["ready_for_public_claims"] for row in rows),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in rows),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in rows),
    }
    row_counts_by_channel = {
        channel["id"]: sum(1 for row in rows if row["source_channel_id"] == channel["id"])
        for channel in SOURCE_CHANNELS
    }
    informal_rows = [row for row in rows if row["informal_publication"]]
    lead_only_rows = [
        row for row in rows if "lead_only" in str(row["evidence_status"])
    ]
    legal_claim_anchor_rows = [
        row for row in rows if str(row["claim_use"]).startswith("may_support_legal_claim")
    ]
    legal_claim_anchor_channels = legal_claim_anchor_source_channel_ids()
    authenticity_volatility_rows = [
        row
        for row in rows
        if row["authenticity_controls_required"] and row["volatility_controls_required"]
    ]
    informal_authenticity_volatility_rows = [
        row
        for row in informal_rows
        if row["informal_publication_claim_boundary"]
        == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
    ]
    authority_tiers = sorted({str(row["authority_tier"]) for row in rows})
    summary = {
        "consistency_ok": False,
        "safe_for_project_planning": project_summary["safe_for_project_planning"],
        "jurisdiction_family_count": len(families),
        "source_channel_count": len(SOURCE_CHANNELS),
        "authority_tier_count": len(authority_tiers),
        "matrix_row_count": len(rows),
        "informal_publication_rows": len(informal_rows),
        "lead_only_rows": len(lead_only_rows),
        "legal_claim_anchor_rows": len(legal_claim_anchor_rows),
        "legal_claim_anchor_source_channel_count": len(legal_claim_anchor_channels),
        "legal_claim_anchor_source_channel_ids": list(legal_claim_anchor_channels),
        "authenticity_volatility_control_rows": len(authenticity_volatility_rows),
        "informal_authenticity_volatility_control_rows": len(
            informal_authenticity_volatility_rows
        ),
        "ready_for_manifest_promotion": ready_flags["manifest_promotion"],
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This matrix is a source-discovery scaffold only. Informal publications are leads, "
            "not source-verified law. No row is ready for manifest promotion, prompt generation, "
            "training use, public claims, worker-facing use, or comparable scoring."
        ),
    }
    checks = [
        _check(
            "project_plan_safe",
            project_summary["safe_for_project_planning"] is True,
            expected=True,
            actual=project_summary["safe_for_project_planning"],
        ),
        _check(
            "source_channel_rows_present",
            bool(rows),
            expected="non-empty matrix",
            actual=len(rows),
        ),
        _check(
            "each_family_has_each_source_channel",
            all(count == len(families) for count in row_counts_by_channel.values()),
            expected=len(families),
            actual=row_counts_by_channel,
        ),
        _check(
            "informal_publication_rows_are_lead_only",
            all("lead_only" in row["evidence_status"] for row in informal_rows),
            expected="lead_only evidence status for every informal row",
            actual=[row["evidence_status"] for row in informal_rows],
        ),
        _check(
            "informal_publications_never_anchor_legal_claims",
            all(row["claim_use"] == "lead_only_never_standalone_legal_claim" for row in informal_rows),
            expected="lead_only_never_standalone_legal_claim",
            actual={row["id"]: row["claim_use"] for row in informal_rows},
        ),
        _check(
            "legal_claim_anchors_are_primary_or_admin_official",
            all(
                row["source_channel_id"] in legal_claim_anchor_channels
                for row in legal_claim_anchor_rows
            ),
            expected=legal_claim_anchor_channels,
            actual=sorted({row["source_channel_id"] for row in legal_claim_anchor_rows}),
        ),
        _check(
            "all_readiness_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
        _check(
            "metadata_fields_present",
            all(len(row["required_metadata"]) >= 5 for row in rows),
            expected="at least 5 metadata fields per row",
            actual=min((len(row["required_metadata"]) for row in rows), default=0),
        ),
        _check(
            "authority_and_corroboration_fields_present",
            all(
                row["authority_tier"]
                and row["claim_use"]
                and len(row["corroboration_required"]) >= 3
                for row in rows
            ),
            expected="authority_tier, claim_use, and at least 3 corroboration requirements",
            actual=min((len(row["corroboration_required"]) for row in rows), default=0),
        ),
        _check(
            "all_rows_have_authenticity_and_volatility_controls",
            len(authenticity_volatility_rows) == len(rows),
            expected=len(rows),
            actual=len(authenticity_volatility_rows),
        ),
        _check(
            "informal_publications_require_authenticity_volatility_and_official_followup",
            all(
                "capture provenance and hash recorded" in row["authenticity_controls_required"]
                and "official-source follow-up target recorded" in row["volatility_controls_required"]
                and row["informal_publication_claim_boundary"]
                == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
                for row in informal_rows
            ),
            expected=(
                "informal publications remain lead-only until authenticity, volatility, "
                "capture, and official-source follow-up review"
            ),
            actual={
                row["id"]: {
                    "authenticity_controls_required": row["authenticity_controls_required"],
                    "volatility_controls_required": row["volatility_controls_required"],
                    "informal_publication_claim_boundary": row[
                        "informal_publication_claim_boundary"
                    ],
                }
                for row in informal_rows
            },
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_source_channel_matrix.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "source-channel matrix; not legal advice, not source verification, not prompt "
                "generation, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "source_channels": [
            {
                "id": channel["id"],
                "label": channel["label"],
                "source_role": channel["source_role"],
                "authority_tier": channel["authority_tier"],
                "claim_use": channel["claim_use"],
                "priority": channel["priority"],
                "evidence_status": channel["evidence_status"],
                "informal_publication": channel["informal_publication"],
            }
            for channel in SOURCE_CHANNELS
        ],
        "matrix_rows": rows,
        "counts_by_source_channel": row_counts_by_channel,
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("matrix_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown source-channel matrix."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Source-Channel Matrix",
        "",
        (
            "This matrix turns the charter's target jurisdiction families into source-discovery "
            "work. It is not legal advice, not source verification, not prompt generation, and "
            "not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Safe for project planning | {str(bool(summary['safe_for_project_planning'])).lower()} |",
        f"| Jurisdiction families | {summary['jurisdiction_family_count']} |",
        f"| Source channels | {summary['source_channel_count']} |",
        f"| Authority tiers | {summary['authority_tier_count']} |",
        f"| Matrix rows | {summary['matrix_row_count']} |",
        f"| Informal publication rows | {summary['informal_publication_rows']} |",
        f"| Lead-only rows | {summary['lead_only_rows']} |",
        f"| Legal-claim anchor rows | {summary['legal_claim_anchor_rows']} |",
        (
            "| Legal-claim anchor source channels "
            f"| {summary['legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Legal-claim anchor source channel IDs "
            f"| `{_md_cell(', '.join(summary['legal_claim_anchor_source_channel_ids']))}` |"
        ),
        (
            "| Authenticity/volatility control rows "
            f"| {summary['authenticity_volatility_control_rows']} |"
        ),
        (
            "| Informal authenticity/volatility control rows "
            f"| {summary['informal_authenticity_volatility_control_rows']} |"
        ),
        f"| Ready for manifest promotion | {str(bool(summary['ready_for_manifest_promotion'])).lower()} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Source Channels",
        "",
        "| Priority | Channel | Authority tier | Claim use | Evidence status | Informal |",
        "|---:|---|---|---|---|---:|",
    ]
    for channel in doc["source_channels"]:
        lines.append(
            f"| {channel['priority']} "
            f"| `{_md_cell(channel['id'])}` "
            f"| {_md_cell(channel['authority_tier'])} "
            f"| {_md_cell(channel['claim_use'])} "
            f"| {_md_cell(channel['evidence_status'])} "
            f"| {str(bool(channel['informal_publication'])).lower()} |"
        )
    lines.extend([
        "",
        "## Matrix Rows",
        "",
        "| ID | Jurisdiction family | Source channel | Authority tier | Claim use | Evidence status |",
        "|---|---|---|---|---|---|",
    ])
    for row in doc["matrix_rows"]:
        lines.append(
            f"| `{_md_cell(row['id'])}` "
            f"| {_md_cell(row['jurisdiction_family'])} "
            f"| `{_md_cell(row['source_channel_id'])}` "
            f"| {_md_cell(row['authority_tier'])} "
            f"| {_md_cell(row['claim_use'])} "
            f"| {_md_cell(row['evidence_status'])} |"
        )
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.extend([
        "",
        "## Non-Scoring Rule",
        "",
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown matrix report")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_source_channel_matrix(
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
    )
    summary = doc["summary"]
    if args.validate:
        print(json.dumps({"summary": summary}, indent=2, ensure_ascii=False))
        return 0 if summary["consistency_ok"] else 1
    if not summary["consistency_ok"]:
        print(json.dumps({"summary": summary, "checks": doc["checks"]}, indent=2, ensure_ascii=False))
        print("[global-protections-source-channel-matrix] matrix is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-source-channel-matrix] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['jurisdiction_family_count']} jurisdiction families; "
        f"{summary['source_channel_count']} source channels; "
        f"{summary['matrix_row_count']} rows; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
