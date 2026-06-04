#!/usr/bin/env python3
"""Build an explicit rejection ledger for OSINT-adjacent tool profiles.

This script does not install, import, or run OSINT tools. It reads the public
tool evaluation matrix and writes a deterministic ledger explaining why each
OSINT-adjacent profile is a design caution only, not an operational provider.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
LEDGER_SCHEMA_VERSION = "public_osint_rejection_ledger.v1"
SUMMARY_SCHEMA_VERSION = "public_osint_rejection_summary.v1"

BLOCKED_CAPABILITIES = {
    "pagodo": [
        "automated_offensive_dork_execution",
        "provider_terms_sensitive_query_automation",
        "targeted_sensitive_source_discovery",
    ],
    "photon": [
        "target_enumeration_crawling",
        "subdomain_or_endpoint_discovery",
        "high_entropy_string_extraction",
    ],
    "theharvester": [
        "people_email_domain_reconnaissance",
        "multi_source_contact_harvesting",
        "credential_or_infrastructure_discovery",
    ],
    "metagoofil": [
        "document_metadata_harvesting",
        "person_or_internal_path_metadata_exposure",
        "unreviewed_public_document_downloads",
    ],
}

ALLOWED_DESIGN_LESSONS = {
    "pagodo": [
        "safe_dork_taxonomy_labels",
        "query_metadata_fields",
        "manual_review_queue_separation",
    ],
    "photon": [
        "denylist_url_filtering_patterns",
        "crawl_depth_limits",
        "high_entropy_string_redaction_tests",
    ],
    "theharvester": [
        "provider_boundary_documentation",
        "clear_non_goals_for_people_search",
        "remote_query_privacy_review_prompts",
    ],
    "metagoofil": [
        "metadata_strip_requirements",
        "download_manifest_review_fields",
        "public_document_redaction_checks",
    ],
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
            count += 1
    return count


def rejected_rows(matrix_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for row in sorted(matrix_rows, key=lambda item: item.get("tool_id", "")):
        if row.get("adoption_decision") != "reject_operational_use_inspiration_only":
            continue
        tool_id = row["tool_id"]
        rows.append(
            {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "tool_id": tool_id,
                "tool_name": row.get("tool_name", tool_id),
                "category": row.get("category", ""),
                "repo_url": row.get("repo_url", ""),
                "docs_url": row.get("docs_url", ""),
                "license": row.get("license", ""),
                "fit_score": row.get("fit_score", 0),
                "operational_status": "rejected_design_reference_only",
                "provider_registry_allowed": False,
                "adapters_allowed": False,
                "network_execution_allowed": False,
                "private_case_ingestion_allowed": False,
                "blocked_capabilities": BLOCKED_CAPABILITIES.get(tool_id, ["operational_osint_harvesting"]),
                "allowed_design_lessons": ALLOWED_DESIGN_LESSONS.get(tool_id, ["document_why_rejected"]),
                "rejection_reason": row.get("rejection_reason", ""),
                "source_matrix_decision": row.get("adoption_decision", ""),
                "source_matrix_registries": row.get("registries", []),
                "privacy": {
                    "raw_private_cases_ingested": False,
                    "private_case_terms_allowed": False,
                    "remote_private_queries_allowed": False,
                    "people_email_or_contact_harvesting_allowed": False,
                    "subdomain_or_credential_harvesting_allowed": False,
                    "stealth_evasion_or_proxy_rotation_allowed": False,
                },
            }
        )
    return rows


def run_pipeline(out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    rows = rejected_rows(read_jsonl(out_dir / "tool_evaluation_matrix.jsonl"))
    count = write_jsonl(out_dir / "rejected_operational_tools.jsonl", rows)
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "rejected_operational_tools": count,
        "tool_ids": [row["tool_id"] for row in rows],
        "privacy": {
            "raw_private_cases_ingested": False,
            "private_case_terms_allowed": False,
            "remote_private_queries_allowed": False,
            "people_email_or_contact_harvesting_allowed": False,
            "subdomain_or_credential_harvesting_allowed": False,
            "stealth_evasion_or_proxy_rotation_allowed": False,
        },
    }
    (out_dir / "osint_rejection_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_pipeline(Path(args.out_dir))
    print(
        "public-osint-rejection-ledger: "
        f"rejected={summary['rejected_operational_tools']} "
        f"tools={','.join(summary['tool_ids'])}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
