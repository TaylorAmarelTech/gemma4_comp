#!/usr/bin/env python3
"""Build sitemap-first crawl plans from the public source domain frontier.

This script does not fetch the internet. It prepares reviewable, deterministic
queues for later sitemap/robots probing after manual source review. Advertools
is treated as an optional parser plan, not a required dependency.
"""

from __future__ import annotations

import argparse
import collections
import json
import urllib.parse
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
PROBE_SCHEMA_VERSION = "public_sitemap_probe_queue.v1"
POLICY_SCHEMA_VERSION = "public_domain_crawl_policy.v1"
DORK_SCHEMA_VERSION = "public_sitemap_discovery_dork.v1"
BROWSER_ALLOWLIST_SCHEMA_VERSION = "public_browser_fetch_allowlist.v1"
SUMMARY_SCHEMA_VERSION = "public_sitemap_frontier_summary.v1"

SIGNAL_KEYWORDS = {
    "debt_bondage": ["debt", "bondage", "recruitment fee", "deduction", "loan"],
    "forced_labor": ["forced labor", "forced labour", "servitude", "exploitation"],
    "illegal_recruitment": ["illegal recruitment", "placement fee", "fake job", "no job order"],
    "document_control": ["passport", "document", "confiscation", "safekeeping"],
    "online_bait": ["online job", "telegram", "social media", "scam"],
    "referral": ["victim identification", "referral", "screening", "repatriation"],
    "immigration_status_control": ["visa", "work permit", "deportation", "status"],
    "forced_criminality": ["forced criminality", "scam compound", "telecom fraud", "non-punishment"],
    "supply_chain": ["supply chain", "procurement", "contractor", "modern slavery"],
    "law_enforcement": ["prosecution", "court", "conviction", "investigation"],
}

DEFAULT_PATH_HINTS = (
    "trafficking",
    "forced-labor",
    "forced-labour",
    "modern-slavery",
    "illegal-recruitment",
    "victim",
    "case",
    "report",
    "publication",
)

DENY_PATH_HINTS = (
    "/login",
    "/signin",
    "/sign-in",
    "/account",
    "/wp-admin",
    "/admin",
    "/private",
    "/cart",
    "/checkout",
    "/subscribe",
    "/newsletter",
    "mailto:",
    "tel:",
)

BROWSER_DENIED_WHEN = (
    "robots_disallow",
    "login_or_credential_required",
    "captcha_or_bot_check",
    "form_submission_required",
    "file_upload_required",
    "private_case_terms_or_identifiers",
    "person_email_contact_or_subdomain_harvesting",
    "proxy_rotation_or_stealth_requested",
)

BROWSER_ALLOWED_WHEN = (
    "http_extraction_failed_or_page_requires_javascript_rendered_text",
    "manual_reviewer_approved_javascript_need",
    "robots_txt_allows_path",
    "same_public_domain_as_source_frontier",
    "url_matches_allow_path_keywords",
    "no_login_no_session_no_captcha_no_form_submit",
)

FORBIDDEN_BROWSER_FEATURES = (
    "stealth",
    "proxy_rotation",
    "captcha_bypass",
    "fingerprint_evasion",
    "credentialed_login",
    "form_submission",
    "file_upload",
    "persistent_context",
    "storage_state_reuse",
    "download_without_manual_review",
)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def _domain_scheme(row: dict) -> str:
    robots_url = row.get("robots_url", "")
    parsed = urllib.parse.urlsplit(robots_url)
    return parsed.scheme if parsed.scheme in {"http", "https"} else "https"


def _base_url(row: dict) -> str:
    return f"{_domain_scheme(row)}://{row['domain']}"


def signal_keywords(signals: Iterable[str]) -> list[str]:
    keywords: list[str] = []
    for signal in signals:
        keywords.extend(SIGNAL_KEYWORDS.get(signal, []))
    deduped = []
    seen = set()
    for keyword in [*keywords, *DEFAULT_PATH_HINTS]:
        lowered = keyword.lower()
        if lowered not in seen:
            seen.add(lowered)
            deduped.append(keyword)
    return deduped[:18]


def crawl_priority(row: dict) -> int:
    source_count = int(row.get("source_count", 0))
    signal_bonus = min(len(row.get("top_signals", [])) * 3, 24)
    official_bonus = 10 if any("gov" in family or "justice" in family for family in row.get("source_families", [])) else 0
    return min(100, 35 + source_count * 4 + signal_bonus + official_bonus)


def probe_queue_rows(domain_rows: list[dict]) -> list[dict]:
    probes: list[dict] = []
    for row in sorted(domain_rows, key=lambda item: (-crawl_priority(item), item["domain"])):
        domain = row["domain"]
        common = {
            "domain": domain,
            "jurisdictions": row.get("jurisdictions", []),
            "source_families": row.get("source_families", []),
            "top_signals": row.get("top_signals", []),
            "priority": crawl_priority(row),
            "network_policy": {
                "network_fetch_default": False,
                "manual_review_before_fetch": True,
                "requires_robots_check": True,
                "respect_rate_limits": True,
                "polite_delay_seconds": row.get("queue_policy", {}).get("polite_delay_seconds", 3),
            },
            "privacy": {
                "public_domain_only": True,
                "private_case_terms_allowed": False,
                "raw_private_cases_ingested": False,
                "pii_redaction_required_before_publish": True,
            },
        }
        probes.append(
            {
                **common,
                "schema_version": PROBE_SCHEMA_VERSION,
                "probe_type": "robots_txt",
                "url": row.get("robots_url") or f"{_base_url(row)}/robots.txt",
                "parser_plan": {
                    "primary": "urllib_robotparser_stdlib",
                    "fallbacks": ["manual_browser_review"],
                },
            }
        )
        for sitemap_url in row.get("sitemap_candidates") or [f"{_base_url(row)}/sitemap.xml"]:
            probes.append(
                {
                    **common,
                    "schema_version": PROBE_SCHEMA_VERSION,
                    "probe_type": "sitemap",
                    "url": sitemap_url,
                    "parser_plan": {
                        "primary": "advertools_sitemap_to_df_optional",
                        "fallbacks": ["stdlib_xml_sitemap_parser", "metadata_only"],
                        "max_urls_to_extract_after_review": 5000,
                        "keyword_filters": signal_keywords(row.get("top_signals", [])),
                    },
                }
            )
    return probes


def domain_policy_rows(domain_rows: list[dict]) -> list[dict]:
    policies = []
    for row in sorted(domain_rows, key=lambda item: (-crawl_priority(item), item["domain"])):
        policies.append(
            {
                "schema_version": POLICY_SCHEMA_VERSION,
                "domain": row["domain"],
                "priority": crawl_priority(row),
                "source_count": row.get("source_count", 0),
                "jurisdictions": row.get("jurisdictions", []),
                "source_families": row.get("source_families", []),
                "top_signals": row.get("top_signals", []),
                "allow_path_keywords": signal_keywords(row.get("top_signals", [])),
                "deny_path_keywords": list(DENY_PATH_HINTS),
                "max_pages_after_manual_review": 120,
                "crawl_order": ["robots_txt", "sitemap", "seed_urls", "same_domain_links"],
                "extractor_plan": {
                    "html": ["trafilatura_optional", "stdlib_html"],
                    "pdf": ["pdfplumber_optional", "pypdf_optional", "metadata_only"],
                    "office_document": ["markitdown_optional", "metadata_only"],
                },
                "crawl_policy": {
                    "network_fetch_default": False,
                    "manual_review_before_fetch": True,
                    "respect_robots_txt": True,
                    "sitemap_first": True,
                    "disable_javascript_browser_by_default": True,
                    "no_proxy_rotation": True,
                    "no_evasion": True,
                },
                "privacy": {
                    "raw_private_cases_ingested": False,
                    "private_case_paths_allowed": False,
                    "publish_redacted_extract_only": True,
                },
            }
        )
    return policies


def browser_fetch_allowlist_rows(domain_rows: list[dict]) -> list[dict]:
    """Prepare an explicit allowlist before any JavaScript browser fetch exists."""

    rows = []
    for row in sorted(domain_rows, key=lambda item: (-crawl_priority(item), item["domain"])):
        rows.append(
            {
                "schema_version": BROWSER_ALLOWLIST_SCHEMA_VERSION,
                "domain": row["domain"],
                "priority": crawl_priority(row),
                "status": "deferred_policy_only_no_browser_fetch",
                "browser_tool": "playwright_python",
                "source_count": row.get("source_count", 0),
                "jurisdictions": row.get("jurisdictions", []),
                "source_families": row.get("source_families", []),
                "top_signals": row.get("top_signals", []),
                "candidate_base_url": _base_url(row),
                "eligible_input_artifacts": [
                    "source_domain_frontier.jsonl",
                    "sitemap_probe_queue.jsonl",
                    "domain_crawl_policy.jsonl",
                    "source_fetch_manifest.jsonl",
                ],
                "allow_path_keywords": signal_keywords(row.get("top_signals", [])),
                "deny_path_keywords": list(DENY_PATH_HINTS),
                "allowed_when": list(BROWSER_ALLOWED_WHEN),
                "denied_when": list(BROWSER_DENIED_WHEN),
                "forbidden_browser_features": list(FORBIDDEN_BROWSER_FEATURES),
                "network_policy": {
                    "network_fetch_default": False,
                    "manual_review_before_fetch": True,
                    "requires_http_extraction_attempt_first": True,
                    "requires_robots_check": True,
                    "respect_rate_limits": True,
                    "polite_delay_seconds": row.get("queue_policy", {}).get("polite_delay_seconds", 3),
                    "max_pages_after_manual_review": 20,
                },
                "browser_state_policy": {
                    "ephemeral_context_only": True,
                    "persistent_context_allowed": False,
                    "storage_state_saved": False,
                    "cookies_saved": False,
                    "downloads_allowed": False,
                    "screenshots_allowed_after_redaction_review": False,
                },
                "allowed_outputs": [
                    "rendered_text_excerpt_after_redaction",
                    "source_metadata",
                    "same_domain_link_candidates",
                    "extraction_failure_reason",
                ],
                "privacy": {
                    "public_domain_only": True,
                    "raw_private_cases_ingested": False,
                    "private_case_terms_allowed": False,
                    "private_case_paths_allowed": False,
                    "people_or_contact_harvesting_allowed": False,
                    "publish_redacted_extract_only": True,
                },
            }
        )
    return rows


def sitemap_discovery_dorks(domain_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    templates = (
        ("sitemap_xml", "site:{domain} inurl:sitemap filetype:xml"),
        ("robots_sitemap_hint", "site:{domain} \"Sitemap:\" \"robots.txt\""),
        ("trafficking_publication", "site:{domain} (\"human trafficking\" OR \"forced labor\" OR \"forced labour\") (report OR publication OR case)"),
        ("debt_bondage_publication", "site:{domain} (\"debt bondage\" OR \"recruitment fee\" OR \"illegal recruitment\")"),
    )
    for row in sorted(domain_rows, key=lambda item: (-crawl_priority(item), item["domain"])):
        for intent, template in templates:
            rows.append(
                {
                    "schema_version": DORK_SCHEMA_VERSION,
                    "intent": intent,
                    "domain": row["domain"],
                    "query": template.format(domain=row["domain"]),
                    "top_signals": row.get("top_signals", []),
                    "privacy": {
                        "public_domain_only": True,
                        "private_case_terms_allowed": False,
                        "raw_private_cases_ingested": False,
                    },
                }
            )
    return rows


def run_pipeline(out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    domain_rows = load_jsonl(out_dir / "source_domain_frontier.jsonl")
    probes = probe_queue_rows(domain_rows)
    policies = domain_policy_rows(domain_rows)
    browser_allowlist = browser_fetch_allowlist_rows(domain_rows)
    dorks = sitemap_discovery_dorks(domain_rows)

    write_jsonl(out_dir / "sitemap_probe_queue.jsonl", probes)
    write_jsonl(out_dir / "domain_crawl_policy.jsonl", policies)
    write_jsonl(out_dir / "browser_fetch_allowlist.jsonl", browser_allowlist)
    write_jsonl(out_dir / "sitemap_discovery_dorks.jsonl", dorks)

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "domains": len(domain_rows),
        "sitemap_probe_queue": len(probes),
        "domain_crawl_policy": len(policies),
        "browser_fetch_allowlist": len(browser_allowlist),
        "sitemap_discovery_dorks": len(dorks),
        "probe_types": dict(collections.Counter(row["probe_type"] for row in probes)),
        "privacy": {
            "network_fetch_default": False,
            "manual_review_before_fetch": True,
            "raw_private_cases_ingested": False,
            "private_case_terms_allowed": False,
        },
    }
    (out_dir / "sitemap_frontier_summary.json").write_text(
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
        "public-sitemap-frontier: "
        f"domains={summary['domains']} "
        f"probes={summary['sitemap_probe_queue']} "
        f"browser_allowlist={summary['browser_fetch_allowlist']} "
        f"dorks={summary['sitemap_discovery_dorks']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
