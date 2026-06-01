#!/usr/bin/env python3
"""Create a large deterministic queue for iterative public-source research.

The queue is a no-network artifact. It ranks public domains, existing source
profiles, deep dorks, sitemap dorks, and coverage gaps into review leads that
future spiders or human reviewers can process without private case text.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
QUEUE_SCHEMA_VERSION = "public_branching_research_queue.v1"
SUMMARY_SCHEMA_VERSION = "public_branching_research_summary.v1"

LEAD_TYPE_BY_INTENT = {
    "case_digest_evidence": "court_or_prosecution_case_search",
    "prosecution_case": "court_or_prosecution_case_search",
    "annual_report_recent": "official_report_or_guidance_search",
    "pdf_report_exact_signal": "official_report_or_guidance_search",
    "indicator_guidance": "indicator_guidance_search",
    "non_html_artifacts": "dataset_or_training_artifact_search",
    "supply_chain_documents": "supply_chain_document_search",
    "migration_status_controls": "immigration_control_search",
    "language_variant": "cross_jurisdiction_language_variant_search",
    "negative_noise_filter": "noise_reduced_public_search",
    "title_terms": "topical_title_search",
}

WORK_PRODUCTS_BY_TYPE = {
    "source_profile_review": ["source_profile", "knowledge_object", "corroboration_link"],
    "court_or_prosecution_case_search": ["source_candidate", "case_fact_card", "dimension_candidate", "prompt_candidate"],
    "official_report_or_guidance_search": ["source_candidate", "knowledge_object", "verified_knowledge_object"],
    "indicator_guidance_search": ["dimension_candidate", "test_candidate", "applicability_seed"],
    "dataset_or_training_artifact_search": ["source_candidate", "extractor_fixture", "fallback_test"],
    "supply_chain_document_search": ["knowledge_object", "hybrid_scenario_prompt", "corroboration_link"],
    "immigration_control_search": ["dimension_candidate", "multi_turn_conversation", "referral_gap_test"],
    "cross_jurisdiction_language_variant_search": ["search_query", "source_profile", "applicability_seed"],
    "noise_reduced_public_search": ["manual_search_fallback", "rejected_source_or_retry_strategy"],
    "topical_title_search": ["source_candidate", "prompt_candidate"],
    "sitemap_discovery_search": ["sitemap_probe", "domain_crawl_policy_update"],
    "coverage_gap_branch": ["source_gap_query", "dimension_gap_test", "hybrid_scenario_prompt"],
}


def stable_hash(value: str, *, n: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:n]


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def lead_privacy() -> dict:
    return {
        "public_source_metadata_only": True,
        "raw_private_cases_ingested": False,
        "private_case_terms_allowed": False,
        "pii_redaction_required_before_publish": True,
        "no_people_search_or_contact_harvesting": True,
    }


def verification_steps() -> list[str]:
    return [
        "Open only the public URL or public search result page.",
        "Record source title, publisher, source type, and publication/update date.",
        "Paraphrase facts; do not copy names, contact details, document numbers, or private case text.",
        "Mark whether the source supports facts, allegations, legal standards, statistics, or search leads.",
        "Create benchmark prompts only with placeholders and dated source limits.",
    ]


def profile_leads(profiles: list[dict]) -> list[dict]:
    rows = []
    for profile in sorted(profiles, key=lambda p: (-len(p.get("signals", [])), p.get("id", ""))):
        lead_key = "profile|" + profile.get("id", "")
        rows.append(
            {
                "schema_version": QUEUE_SCHEMA_VERSION,
                "id": f"BRANCH-LEAD-{stable_hash(lead_key).upper()}",
                "lead_type": "source_profile_review",
                "priority": 95 + min(len(profile.get("signals", [])), 5),
                "source_profile_id": profile.get("id"),
                "source_candidate_id": profile.get("source_candidate_id"),
                "source_url": profile.get("url"),
                "source_family": profile.get("source_family"),
                "jurisdictions": profile.get("jurisdictions", []),
                "signals": profile.get("signals", []),
                "sector_or_domain_hint": "from_existing_source_profile",
                "query": "",
                "work_products_requested": WORK_PRODUCTS_BY_TYPE["source_profile_review"],
                "scenario_hooks": [
                    "turn source context into a dated knowledge object",
                    "mix with aggregate private pattern IDs only",
                    "generate one worker-support conversation and one evaluator prompt",
                ],
                "verification": verification_steps(),
                "privacy": lead_privacy(),
            }
        )
    return rows


def dork_leads(dorks: list[dict], *, source: str) -> list[dict]:
    rows = []
    for dork in sorted(dorks, key=lambda d: (-int(d.get("priority", 0)), d.get("id", ""), d.get("query", ""))):
        intent = dork.get("intent", "")
        lead_type = "sitemap_discovery_search" if source == "sitemap" else LEAD_TYPE_BY_INTENT.get(intent, "public_search_branch")
        lead_key = f"{source}|{dork.get('id', '')}|{dork.get('query', '')}"
        rows.append(
            {
                "schema_version": QUEUE_SCHEMA_VERSION,
                "id": f"BRANCH-LEAD-{stable_hash(lead_key).upper()}",
                "lead_type": lead_type,
                "priority": int(dork.get("priority", 0)) or 50,
                "source_profile_id": "",
                "source_candidate_id": "",
                "source_url": "",
                "source_family": dork.get("family", ""),
                "jurisdictions": [],
                "signals": dork.get("expected_signals") or dork.get("top_signals") or [],
                "sector_or_domain_hint": dork.get("domain") or dork.get("site_filter", ""),
                "query": dork.get("query", ""),
                "provider_fallback_urls": {
                    key: dork[key]
                    for key in ("google_manual", "bing_web", "duckduckgo_html")
                    if dork.get(key)
                },
                "work_products_requested": WORK_PRODUCTS_BY_TYPE.get(lead_type, ["source_candidate", "knowledge_object"]),
                "scenario_hooks": [
                    "extract new search terms from each result title/snippet",
                    "branch into court case, report, indicator, and sector variants",
                    "create multi-turn and hybrid prompts only after public-source review",
                ],
                "verification": verification_steps(),
                "privacy": lead_privacy(),
            }
        )
    return rows


def coverage_gap_leads(coverage: dict) -> list[dict]:
    gaps = coverage.get("gaps", {})
    rows = []
    for kind, values in (
        ("missing_signal", gaps.get("missing_signals", [])),
        ("sparse_signal", gaps.get("sparse_signals", [])),
        ("missing_sector", gaps.get("missing_sectors", [])),
        ("sparse_sector", gaps.get("sparse_sectors", [])),
    ):
        for value in values:
            lead_key = f"gap|{kind}|{value}"
            rows.append(
                {
                    "schema_version": QUEUE_SCHEMA_VERSION,
                    "id": f"BRANCH-LEAD-{stable_hash(lead_key).upper()}",
                    "lead_type": "coverage_gap_branch",
                    "priority": 70 if kind.startswith("missing") else 60,
                    "source_profile_id": "",
                    "source_candidate_id": "",
                    "source_url": "",
                    "source_family": "coverage_gap",
                    "jurisdictions": [],
                    "signals": [value] if "signal" in kind else [],
                    "sector_or_domain_hint": value if "sector" in kind else "",
                    "query": f"Find public official or court sources for {kind.replace('_', ' ')}: {value}",
                    "work_products_requested": WORK_PRODUCTS_BY_TYPE["coverage_gap_branch"],
                    "scenario_hooks": [
                        "turn the gap into three dorks across official, court, and intergovernmental sources",
                        "create a test that proves the gap stays visible until covered",
                    ],
                    "verification": verification_steps(),
                    "privacy": lead_privacy(),
                }
            )
    return rows


def queue_rows(out_dir: Path, *, target_count: int = 1000) -> list[dict]:
    profiles = read_jsonl(out_dir / "source_profiles.jsonl")
    deep_dorks = read_jsonl(out_dir / "deep_search_dorks.jsonl")
    sitemap_dorks = read_jsonl(out_dir / "sitemap_discovery_dorks.jsonl")
    coverage = read_json(out_dir / "source_profile_coverage.json", {})

    all_rows = [
        *profile_leads(profiles),
        *dork_leads(deep_dorks, source="deep_dork"),
        *dork_leads(sitemap_dorks, source="sitemap"),
        *coverage_gap_leads(coverage),
    ]
    candidates = []
    seen = set()
    for row in sorted(all_rows, key=lambda item: (-int(item.get("priority", 0)), item.get("id", ""))):
        key = (row["lead_type"], row.get("query", ""), row.get("source_url", ""), tuple(row.get("signals", [])))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(row)

    buckets: dict[str, list[dict]] = collections.defaultdict(list)
    for row in candidates:
        buckets[row.get("source_family") or row.get("lead_type", "unknown")].append(row)
    family_order = sorted(
        buckets,
        key=lambda family: (-int(buckets[family][0].get("priority", 0)), family),
    )

    ranked: list[dict] = []
    while len(ranked) < target_count and any(buckets.values()):
        for family in family_order:
            if not buckets[family]:
                continue
            row = buckets[family].pop(0)
            row["rank"] = len(ranked) + 1
            ranked.append(row)
            if len(ranked) >= target_count:
                break
    return ranked


def run_pipeline(out_dir: Path = DEFAULT_OUT_DIR, *, target_count: int = 1000) -> dict:
    rows = queue_rows(out_dir, target_count=target_count)
    write_jsonl(out_dir / "branching_research_queue.jsonl", rows)
    by_type = collections.Counter(row["lead_type"] for row in rows)
    by_signal: collections.Counter[str] = collections.Counter()
    by_family: collections.Counter[str] = collections.Counter()
    for row in rows:
        by_signal.update(row.get("signals", []))
        by_family[row.get("source_family", "unknown")] += 1
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "branching_research_queue": len(rows),
        "lead_types": dict(sorted(by_type.items())),
        "signals": dict(sorted(by_signal.items())),
        "source_families": dict(sorted(by_family.items())),
        "privacy": {
            "public_source_metadata_only": True,
            "raw_private_cases_ingested": False,
            "private_case_terms_allowed": False,
            "no_people_search_or_contact_harvesting": True,
        },
    }
    (out_dir / "branching_research_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--target-count", type=int, default=1000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_pipeline(Path(args.out_dir), target_count=args.target_count)
    print(
        "public-branching-research-queue: "
        f"leads={summary['branching_research_queue']} "
        f"types={len(summary['lead_types'])}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
