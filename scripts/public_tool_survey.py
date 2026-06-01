#!/usr/bin/env python3
"""Generate deterministic tool-survey artifacts for the research spider.

This script profiles public search, crawl, extraction, archive, and
OSINT-adjacent tools without installing or running them. The output is a safe
adoption matrix for later research-frontier loops:

- tool_evaluation_matrix.jsonl
- tool_adoption_notes.md
- search_provider_registry.json
- crawler_provider_registry.json
- extractor_provider_registry.json
- tool_survey_summary.json

The matrix is intentionally conservative. A tool can be useful design context
and still be rejected for operational use in this repo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
CHECKED_DATE = "2026-05-31"
SCHEMA_VERSION = "public_research_tool_survey.v1"
IMPLEMENTED_PROVIDER_WRAPPERS = (
    "manual_dork_queue",
    "brave_search_api",
    "github_search_api",
)
IMPLEMENTED_EXTRACTOR_WRAPPERS = (
    "stdlib_html",
    "trafilatura_optional",
    "pdfplumber_optional",
    "pypdf_optional",
    "markitdown_optional",
)

REQUIRED_MATRIX_FIELDS = {
    "tool_id",
    "tool_name",
    "repo_url",
    "docs_url",
    "category",
    "license",
    "maintenance_signal",
    "python_support",
    "network_behavior",
    "robots_or_rate_limit_support",
    "privacy_risk",
    "install_risk",
    "dependency_risk",
    "fit_score",
    "adoption_decision",
    "rejection_reason",
    "notes",
    "checked_date",
}


TOOL_CANDIDATES: tuple[dict, ...] = (
    {
        "tool_id": "manual_dork_queue",
        "tool_name": "Manual dork queue",
        "repo_url": "",
        "docs_url": "",
        "category": "search_provider",
        "license": "repo_native",
        "maintenance_signal": "project_owned",
        "python_support": "stdlib_jsonl_artifacts",
        "network_behavior": "no_network_by_default_browser_ready_urls_only",
        "robots_or_rate_limit_support": "manual_review_required_before_fetch",
        "privacy_risk": "low_if_private_terms_are_never_used",
        "install_risk": "none",
        "dependency_risk": "none",
        "fit_score": 95,
        "adoption_decision": "adopt_deterministic_core",
        "rejection_reason": "",
        "notes": "Best default fallback for source discovery when credentials or network are unavailable.",
        "registries": ("search",),
        "safe_default": True,
        "requires_credentials": False,
    },
    {
        "tool_id": "brave_search_api",
        "tool_name": "Brave Search API",
        "repo_url": "",
        "docs_url": "https://brave.com/search/api/",
        "category": "search_provider",
        "license": "commercial_api_terms",
        "maintenance_signal": "active_vendor_api",
        "python_support": "http_json_api",
        "network_behavior": "remote_search_api_requires_key",
        "robots_or_rate_limit_support": "provider_rate_limits_apply_fetches_still_need_robots",
        "privacy_risk": "medium_queries_leave_machine",
        "install_risk": "none_if_using_stdlib_http",
        "dependency_risk": "low",
        "fit_score": 82,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Good optional API candidate for public-source discovery; never send private case terms.",
        "registries": ("search",),
        "safe_default": False,
        "requires_credentials": True,
    },
    {
        "tool_id": "searxng",
        "tool_name": "SearXNG",
        "repo_url": "https://github.com/searxng/searxng",
        "docs_url": "https://docs.searxng.org/dev/search_api.html",
        "category": "search_provider",
        "license": "AGPL-3.0",
        "maintenance_signal": "active_open_source_metasearch",
        "python_support": "http_json_api",
        "network_behavior": "self_host_or_instance_api",
        "robots_or_rate_limit_support": "instance_limits_apply_fetches_still_need_robots",
        "privacy_risk": "medium_instance_operator_can_see_queries",
        "install_risk": "medium_if_self_hosted",
        "dependency_risk": "medium_due_agpl_service_boundary_review",
        "fit_score": 76,
        "adoption_decision": "defer_requires_license_and_instance_review",
        "rejection_reason": "Use only after AGPL/service-boundary and instance privacy review.",
        "notes": "Useful metasearch design reference; registry can support self-hosted endpoint later.",
        "registries": ("search",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "serpapi",
        "tool_name": "SerpApi Google Search API",
        "repo_url": "",
        "docs_url": "https://serpapi.com/search-api",
        "category": "search_provider",
        "license": "commercial_api_terms",
        "maintenance_signal": "active_vendor_api",
        "python_support": "official_python_integration_available",
        "network_behavior": "remote_search_api_requires_key",
        "robots_or_rate_limit_support": "provider_limits_apply_fetches_still_need_robots",
        "privacy_risk": "medium_queries_leave_machine",
        "install_risk": "none_if_using_stdlib_http",
        "dependency_risk": "low_without_package_dependency",
        "fit_score": 72,
        "adoption_decision": "defer_requires_credentials_or_budget",
        "rejection_reason": "Needs API key and budget decision before use.",
        "notes": "Good fallback for exact Google result parity if credentials are available.",
        "registries": ("search",),
        "safe_default": False,
        "requires_credentials": True,
    },
    {
        "tool_id": "ddgs",
        "tool_name": "DDGS / duckduckgo-search successor",
        "repo_url": "https://github.com/deedy5/duckduckgo_search",
        "docs_url": "https://github.com/deedy5/duckduckgo_search",
        "category": "search_provider",
        "license": "verify_before_dependency",
        "maintenance_signal": "active_but_search_backend_behavior_can_drift",
        "python_support": "python_package",
        "network_behavior": "remote_search_requests_without_official_sla",
        "robots_or_rate_limit_support": "backend_rate_limits_can_be_opaque",
        "privacy_risk": "medium_queries_leave_machine",
        "install_risk": "low",
        "dependency_risk": "medium_due_backend_instability",
        "fit_score": 62,
        "adoption_decision": "defer_optional_unstable_backend",
        "rejection_reason": "Prefer official APIs or manual queues until reliability is proven.",
        "notes": "Useful for experimentation, but not a core dependency.",
        "registries": ("search",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "github_search_api",
        "tool_name": "GitHub Search API",
        "repo_url": "",
        "docs_url": "https://docs.github.com/en/rest/search/search",
        "category": "tool_discovery",
        "license": "platform_api_terms",
        "maintenance_signal": "active_vendor_api",
        "python_support": "http_json_api",
        "network_behavior": "remote_api_optional_token_for_higher_limits",
        "robots_or_rate_limit_support": "api_rate_limits_apply",
        "privacy_risk": "low_for_public_tool_queries",
        "install_risk": "none_if_using_stdlib_http",
        "dependency_risk": "low",
        "fit_score": 80,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Best source for discovering and refreshing public Python repo candidates.",
        "registries": ("search",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "scrapy",
        "tool_name": "Scrapy",
        "repo_url": "https://github.com/scrapy/scrapy",
        "docs_url": "https://docs.scrapy.org/en/latest/",
        "category": "crawler",
        "license": "BSD-3-Clause",
        "maintenance_signal": "mature_active_framework",
        "python_support": "python_framework",
        "network_behavior": "direct_crawler_requests",
        "robots_or_rate_limit_support": "supports_robots_and_autothrottle_configuration",
        "privacy_risk": "low_with_public_allowlist_and_redaction",
        "install_risk": "medium",
        "dependency_risk": "medium",
        "fit_score": 84,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Strong candidate for polite, resumable public-source crawling if dependency cost is acceptable.",
        "registries": ("crawler",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "crawlee_python",
        "tool_name": "Crawlee for Python",
        "repo_url": "https://github.com/apify/crawlee-python",
        "docs_url": "https://crawlee.dev/python/",
        "category": "crawler",
        "license": "Apache-2.0",
        "maintenance_signal": "active_open_source_framework",
        "python_support": "python_framework_with_http_and_browser_crawlers",
        "network_behavior": "direct_requests_or_browser_automation",
        "robots_or_rate_limit_support": "review_per_adapter_before_use",
        "privacy_risk": "medium_if_browser_or_storage_features_are_enabled",
        "install_risk": "medium",
        "dependency_risk": "medium",
        "fit_score": 74,
        "adoption_decision": "defer_until_scrapy_gap_is_clear",
        "rejection_reason": "Overlap with simpler crawler options; evaluate after a concrete need appears.",
        "notes": "Good design reference for queues, storage, retries, and browser-backed crawling.",
        "registries": ("crawler",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "advertools",
        "tool_name": "advertools",
        "repo_url": "https://github.com/eliasdabbas/advertools",
        "docs_url": "https://advertools.readthedocs.io/",
        "category": "crawler",
        "license": "MIT",
        "maintenance_signal": "active_docs_and_package",
        "python_support": "python_package",
        "network_behavior": "crawler_and_sitemap_fetches",
        "robots_or_rate_limit_support": "docs_show_robotstxt_obey_and_jsonl_outputs",
        "privacy_risk": "low_with_public_scope",
        "install_risk": "medium",
        "dependency_risk": "medium_scrapy_based_stack",
        "fit_score": 78,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Useful for sitemap-first public source expansion and JSONL crawl outputs.",
        "registries": ("crawler",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "crawl4ai",
        "tool_name": "Crawl4AI",
        "repo_url": "https://github.com/unclecode/crawl4ai",
        "docs_url": "https://docs.crawl4ai.com/",
        "category": "crawler_extractor",
        "license": "verify_before_dependency",
        "maintenance_signal": "active_fast_moving_llm_crawler",
        "python_support": "python_package",
        "network_behavior": "browser_or_http_crawling_markdown_output",
        "robots_or_rate_limit_support": "requires_adapter_review_before_fetching",
        "privacy_risk": "medium_to_high_if_llm_extraction_or_browser_features_enabled",
        "install_risk": "high_if_browser_or_llm_extras_are_installed",
        "dependency_risk": "high_fast_moving_large_stack",
        "fit_score": 64,
        "adoption_decision": "defer_heavy_dependency",
        "rejection_reason": "Prototype only after simpler HTML extraction cannot handle target public sources.",
        "notes": "Strong Markdown/RAG design reference; avoid remote LLM extraction in this repo.",
        "registries": ("crawler", "extractor"),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "playwright_python",
        "tool_name": "Playwright Python",
        "repo_url": "https://github.com/microsoft/playwright-python",
        "docs_url": "https://playwright.dev/python/",
        "category": "browser_automation",
        "license": "Apache-2.0",
        "maintenance_signal": "active_mature_browser_automation",
        "python_support": "python_package_plus_browser_install",
        "network_behavior": "real_browser_public_page_requests",
        "robots_or_rate_limit_support": "must_be_enforced_by_wrapper_and_allowlist",
        "privacy_risk": "medium_browser_state_must_not_persist_private_data",
        "install_risk": "high_due_browser_binaries",
        "dependency_risk": "high",
        "fit_score": 58,
        "adoption_decision": "defer_allowlisted_javascript_only",
        "rejection_reason": "Use only for public pages that cannot be handled by HTTP extraction.",
        "notes": "No stealth, CAPTCHA bypass, login automation, or fingerprint evasion.",
        "registries": ("crawler",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "trafilatura",
        "tool_name": "trafilatura",
        "repo_url": "https://github.com/adbar/trafilatura",
        "docs_url": "https://trafilatura.readthedocs.io/",
        "category": "html_extractor",
        "license": "Apache-2.0",
        "maintenance_signal": "active_open_source_text_extraction",
        "python_support": "python_package_and_cli",
        "network_behavior": "can_extract_from_local_html_or_downloaded_public_html",
        "robots_or_rate_limit_support": "safe_when_used_after_existing_fetch_gate",
        "privacy_risk": "low_for_local_public_html",
        "install_risk": "medium",
        "dependency_risk": "medium",
        "fit_score": 88,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Best first optional extractor for public HTML text and metadata.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "courlan",
        "tool_name": "courlan",
        "repo_url": "https://github.com/adbar/courlan",
        "docs_url": "https://github.com/adbar/courlan",
        "category": "url_filter",
        "license": "Apache-2.0",
        "maintenance_signal": "active_url_filtering_helper",
        "python_support": "python_package_and_cli",
        "network_behavior": "local_url_filtering_no_fetch_required",
        "robots_or_rate_limit_support": "normalization_only_fetch_gate_still_required",
        "privacy_risk": "low",
        "install_risk": "low",
        "dependency_risk": "low",
        "fit_score": 75,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Good candidate for dedupe, filtering, and URL canonicalization after source discovery.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "pymupdf",
        "tool_name": "PyMuPDF",
        "repo_url": "https://github.com/pymupdf/PyMuPDF",
        "docs_url": "https://pymupdf.readthedocs.io/",
        "category": "document_extractor",
        "license": "AGPL-3.0_or_commercial",
        "maintenance_signal": "active_high_performance_pdf_library",
        "python_support": "python_package",
        "network_behavior": "local_document_extraction",
        "robots_or_rate_limit_support": "not_applicable_after_safe_fetch",
        "privacy_risk": "low_for_public_documents_high_for_private_files",
        "install_risk": "medium",
        "dependency_risk": "high_license_review_required",
        "fit_score": 70,
        "adoption_decision": "defer_requires_license_review",
        "rejection_reason": "License review required before dependency adoption.",
        "notes": "Technically strong for PDFs, but license/commercial boundary matters.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "pdfplumber",
        "tool_name": "pdfplumber",
        "repo_url": "https://github.com/jsvine/pdfplumber",
        "docs_url": "https://github.com/jsvine/pdfplumber",
        "category": "document_extractor",
        "license": "MIT",
        "maintenance_signal": "active_pdf_text_and_table_extraction",
        "python_support": "python_package",
        "network_behavior": "local_pdf_extraction",
        "robots_or_rate_limit_support": "not_applicable_after_safe_fetch",
        "privacy_risk": "low_for_public_documents_high_for_private_files",
        "install_risk": "medium",
        "dependency_risk": "medium",
        "fit_score": 84,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Good first PDF/table extractor candidate for public reports and court PDFs.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "pypdf",
        "tool_name": "pypdf",
        "repo_url": "https://github.com/py-pdf/pypdf",
        "docs_url": "https://pypdf.readthedocs.io/",
        "category": "document_extractor",
        "license": "BSD-3-Clause",
        "maintenance_signal": "active_lightweight_pdf_library",
        "python_support": "python_package",
        "network_behavior": "local_pdf_extraction",
        "robots_or_rate_limit_support": "not_applicable_after_safe_fetch",
        "privacy_risk": "low_for_public_documents_high_for_private_files",
        "install_risk": "low",
        "dependency_risk": "low",
        "fit_score": 80,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Good lightweight fallback for simple public PDF text extraction.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "markitdown",
        "tool_name": "Microsoft MarkItDown",
        "repo_url": "https://github.com/microsoft/markitdown",
        "docs_url": "https://github.com/microsoft/markitdown",
        "category": "document_extractor",
        "license": "MIT",
        "maintenance_signal": "active_microsoft_project",
        "python_support": "python_package_and_cli",
        "network_behavior": "local_conversion_for_most_formats_optional_remote_extensions",
        "robots_or_rate_limit_support": "not_applicable_after_safe_fetch",
        "privacy_risk": "medium_disable_remote_or_ai_extensions",
        "install_risk": "medium",
        "dependency_risk": "medium",
        "fit_score": 76,
        "adoption_decision": "defer_extension_review",
        "rejection_reason": "Adopt only with local-only conversion settings and fixture tests.",
        "notes": "Promising Markdown conversion for Office/public reports; remote services must stay off.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "unstructured",
        "tool_name": "unstructured",
        "repo_url": "https://github.com/Unstructured-IO/unstructured",
        "docs_url": "https://docs.unstructured.io/open-source",
        "category": "document_extractor",
        "license": "Apache-2.0",
        "maintenance_signal": "active_document_etl_project",
        "python_support": "python_package_with_extras",
        "network_behavior": "local_partitioning_possible_remote_platform_must_not_be_used",
        "robots_or_rate_limit_support": "not_applicable_after_safe_fetch",
        "privacy_risk": "medium_to_high_if_remote_platform_or_ocr_extras_are_enabled",
        "install_risk": "high_with_all_docs_extras",
        "dependency_risk": "high",
        "fit_score": 60,
        "adoption_decision": "defer_heavy_dependency",
        "rejection_reason": "Large dependency surface; use only if lighter extractors fail.",
        "notes": "Useful design reference for partitioned document elements and metadata.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "warcio",
        "tool_name": "warcio",
        "repo_url": "https://github.com/webrecorder/warcio",
        "docs_url": "https://warcio.readthedocs.io/",
        "category": "archive_reproducibility",
        "license": "Apache-2.0",
        "maintenance_signal": "active_warc_library",
        "python_support": "python_package",
        "network_behavior": "local_read_write_warc_records",
        "robots_or_rate_limit_support": "archive_after_safe_fetch_only",
        "privacy_risk": "medium_archives_can_capture_pii_if_fetch_scope_is_wrong",
        "install_risk": "low",
        "dependency_risk": "low",
        "fit_score": 78,
        "adoption_decision": "adopt_optional_adapter_candidate",
        "rejection_reason": "",
        "notes": "Good candidate for reproducible public-source snapshots with strict redaction gates.",
        "registries": ("extractor",),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "pagodo",
        "tool_name": "pagodo",
        "repo_url": "https://github.com/opsdisk/pagodo",
        "docs_url": "https://github.com/opsdisk/pagodo",
        "category": "osint_adjacent_dorking",
        "license": "GPL-3.0",
        "maintenance_signal": "active_but_offensive_dorking_orientation",
        "python_support": "python_scripts",
        "network_behavior": "automated_google_dorking",
        "robots_or_rate_limit_support": "high_risk_search_terms_and_provider_terms_issue",
        "privacy_risk": "high_for_sensitive_or_targeted_queries",
        "install_risk": "medium",
        "dependency_risk": "high_due_operational_misuse_risk",
        "fit_score": 25,
        "adoption_decision": "reject_operational_use_inspiration_only",
        "rejection_reason": "Do not run GHDB/offensive dork automation from this repo.",
        "notes": "Mine only safe lessons about dork categorization and query metadata.",
        "registries": (),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "photon",
        "tool_name": "Photon",
        "repo_url": "https://github.com/s0md3v/Photon",
        "docs_url": "https://github.com/s0md3v/Photon/wiki/Usage",
        "category": "osint_adjacent_crawler",
        "license": "verify_before_dependency",
        "maintenance_signal": "older_popular_osint_crawler",
        "python_support": "python_scripts",
        "network_behavior": "target_site_crawler_with_intel_extraction_features",
        "robots_or_rate_limit_support": "not_suitable_without_major_restrictions",
        "privacy_risk": "high_extracts_urls_subdomains_and_high_entropy_strings",
        "install_risk": "medium",
        "dependency_risk": "high_due_operational_misuse_risk",
        "fit_score": 20,
        "adoption_decision": "reject_operational_use_inspiration_only",
        "rejection_reason": "Do not run target-enumeration crawlers from this repo.",
        "notes": "Use only as an anti-pattern/design reference for what to disallow.",
        "registries": (),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "theharvester",
        "tool_name": "theHarvester",
        "repo_url": "https://github.com/laramies/theHarvester",
        "docs_url": "https://github.com/laramies/theHarvester",
        "category": "osint_adjacent_recon",
        "license": "verify_before_dependency",
        "maintenance_signal": "active_osint_project",
        "python_support": "python_project",
        "network_behavior": "multi_source_domain_people_email_recon",
        "robots_or_rate_limit_support": "not_suitable_for_duecare_benchmark_fetching",
        "privacy_risk": "very_high_people_and_email_harvesting_focus",
        "install_risk": "medium",
        "dependency_risk": "high_due_people_data_harvesting",
        "fit_score": 10,
        "adoption_decision": "reject_operational_use_inspiration_only",
        "rejection_reason": "People, email, and domain reconnaissance are out of scope.",
        "notes": "Do not adapt operational harvesting features; note only provider-orchestration cautions.",
        "registries": (),
        "safe_default": False,
        "requires_credentials": False,
    },
    {
        "tool_id": "metagoofil",
        "tool_name": "Metagoofil",
        "repo_url": "https://github.com/laramies/metagoofil",
        "docs_url": "https://github.com/laramies/metagoofil",
        "category": "osint_adjacent_metadata",
        "license": "verify_before_dependency",
        "maintenance_signal": "osint_metadata_harvester",
        "python_support": "python_project",
        "network_behavior": "public_document_search_and_metadata_harvest",
        "robots_or_rate_limit_support": "not_suitable_for_public_benchmark_default",
        "privacy_risk": "very_high_metadata_can_expose_people_paths_and_org_details",
        "install_risk": "medium",
        "dependency_risk": "high_due_metadata_harvesting",
        "fit_score": 15,
        "adoption_decision": "reject_operational_use_inspiration_only",
        "rejection_reason": "Metadata harvesting can expose people and internal paths.",
        "notes": "Use as a cautionary pattern: strip metadata from fetched public documents.",
        "registries": (),
        "safe_default": False,
        "requires_credentials": False,
    },
)


def matrix_rows() -> list[dict]:
    rows: list[dict] = []
    for tool in TOOL_CANDIDATES:
        row = {key: tool[key] for key in REQUIRED_MATRIX_FIELDS if key != "checked_date"}
        row["checked_date"] = CHECKED_DATE
        row["schema_version"] = SCHEMA_VERSION
        row["source_kind"] = "public_tool_profile"
        row["synthetic_or_public_only"] = True
        row["private_case_ingestion"] = False
        row["safe_default"] = bool(tool.get("safe_default", False))
        row["requires_credentials"] = bool(tool.get("requires_credentials", False))
        row["registries"] = list(tool.get("registries", ()))
        rows.append(row)
    return rows


def validate_matrix(rows: Iterable[dict]) -> None:
    seen: set[str] = set()
    for row in rows:
        missing = REQUIRED_MATRIX_FIELDS - set(row)
        if missing:
            raise ValueError(f"{row.get('tool_id', '<unknown>')} missing fields: {sorted(missing)}")
        if row["tool_id"] in seen:
            raise ValueError(f"duplicate tool_id: {row['tool_id']}")
        seen.add(row["tool_id"])
        if not isinstance(row["fit_score"], int) or not 0 <= row["fit_score"] <= 100:
            raise ValueError(f"{row['tool_id']} fit_score must be int 0..100")
        if "private" in json.dumps(row).lower() and row["private_case_ingestion"]:
            raise ValueError(f"{row['tool_id']} cannot ingest private case data")


def provider_registry(kind: str, rows: list[dict]) -> dict:
    providers = []
    for row in rows:
        if kind not in row.get("registries", []):
            continue
        providers.append(
            {
                "tool_id": row["tool_id"],
                "tool_name": row["tool_name"],
                "category": row["category"],
                "adapter_status": row["adoption_decision"],
                "safe_default": row["safe_default"],
                "requires_credentials": row["requires_credentials"],
                "network_behavior": row["network_behavior"],
                "privacy_risk": row["privacy_risk"],
                "robots_or_rate_limit_support": row["robots_or_rate_limit_support"],
                "fixture_strategy": "synthetic_provider_results_only",
                "notes": row["notes"],
            }
        )
    return {
        "schema_version": f"public_research_{kind}_provider_registry.v1",
        "generated_at": f"{CHECKED_DATE}T00:00:00Z",
        "source_matrix": "tool_evaluation_matrix.jsonl",
        "privacy_boundary": {
            "raw_private_cases_allowed": False,
            "remote_private_queries_allowed": False,
            "pii_harvesting_allowed": False,
            "credential_or_evasion_features_allowed": False,
        },
        "providers": providers,
    }


def summarize(rows: list[dict]) -> dict:
    decisions: dict[str, int] = {}
    categories: dict[str, int] = {}
    for row in rows:
        decisions[row["adoption_decision"]] = decisions.get(row["adoption_decision"], 0) + 1
        categories[row["category"]] = categories.get(row["category"], 0) + 1
    rejected = [row["tool_id"] for row in rows if row["adoption_decision"].startswith("reject_")]
    adopted = [row["tool_id"] for row in rows if row["adoption_decision"].startswith("adopt_")]
    return {
        "schema_version": "public_research_tool_survey_summary.v1",
        "generated_at": f"{CHECKED_DATE}T00:00:00Z",
        "tool_profiles": len(rows),
        "decision_counts": decisions,
        "category_counts": categories,
        "adopted_or_candidate_tools": adopted,
        "rejected_operational_tools": rejected,
        "implemented_provider_wrappers": list(IMPLEMENTED_PROVIDER_WRAPPERS),
        "implemented_extractor_wrappers": list(IMPLEMENTED_EXTRACTOR_WRAPPERS),
        "privacy": {
            "raw_private_cases_ingested": False,
            "remote_private_queries_allowed": False,
            "osint_adjacent_tools_operationalized": False,
        },
    }


def load_research_spider_summary(out_dir: Path) -> dict:
    path = out_dir / "summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_manifest_summary(out_dir: Path) -> dict:
    path = out_dir / "source_manifest_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def next_frontier_branches(rows: list[dict]) -> list[dict]:
    branch_specs = [
        ("tool", "prototype_brave_search_adapter", "Add an env-key-gated Brave Search API wrapper with synthetic fixture tests."),
        ("tool", "prototype_github_search_tool_discovery", "Use GitHub Search API to refresh Python tool candidates without private queries."),
        ("tool", "prototype_trafilatura_html_extractor", "Extract public HTML text after existing fetch/robots gates."),
        ("tool", "prototype_pdfplumber_pdf_extractor", "Extract public PDF text/tables from court and report fixtures."),
        ("tool", "prototype_pypdf_lightweight_fallback", "Add a lightweight PDF fallback for simple public documents."),
        ("tool", "prototype_warcio_manifest_archiving", "Capture public-source fetch manifests and WARC metadata after redaction gates."),
        ("tool", "evaluate_advertools_sitemap_crawl", "Test sitemap-first expansion for official public domains."),
        ("tool", "evaluate_scrapy_polite_crawler", "Prototype a small Scrapy spider only if sitemap/manual discovery stalls."),
        ("tool", "defer_playwright_allowlist_policy", "Write allowlist policy before any JavaScript browser fetches."),
        ("tool", "reject_osint_operationalization", "Keep pagodo, Photon, theHarvester, and Metagoofil out of provider registries."),
        ("source", "philippines_court_illegal_recruitment_cases", "Search public Philippine court/prosecution sources for illegal recruitment and debt bondage."),
        ("source", "hong_kong_fdh_agency_fee_cases", "Search Hong Kong public sources for FDH agency overcharge, loan, passport, and rest-day indicators."),
        ("source", "china_court_new_trafficking_forms", "Branch from China court summaries into fraud, trafficking, and coded-language public cases."),
        ("source", "iom_recruitment_fee_guidance", "Corroborate recruitment-fee and related-cost guidance with IOM/ILO documents."),
        ("source", "ilo_forced_labour_indicators", "Extract prompt seeds from ILO forced-labour indicators and sector material."),
        ("source", "unodc_case_law_forced_labor", "Search UNODC case-law material for coercion, servitude, and debt-bondage examples."),
        ("source", "fatf_financial_flows_typologies", "Extract financial-obfuscation indicators from FATF/APG trafficking typologies."),
        ("source", "asean_bali_process_corridors", "Search regional sources for transit, scam-compound, and referral pathway patterns."),
        ("source", "europol_eurojust_frontex_operations", "Profile EU law-enforcement operations for cross-border exploitation indicators."),
        ("source", "canada_temporary_foreign_worker_cases", "Search public Canadian justice/labour cases for immigration-status coercion."),
        ("source", "australia_afp_forced_marriage_servitude", "Branch from AFP/Home Affairs trafficking material into prosecution and referral examples."),
        ("source", "new_zealand_migrant_exploitation_cases", "Search NZ immigration/employment sources for exploitation and deception cases."),
        ("source", "singapore_mom_agency_fee_guidance", "Profile Singapore MOM/ICA/police sources for recruitment and permit-control prompts."),
        ("prompt", "multi_turn_worker_triage_conversations", "Generate synthetic conversations with jurisdiction ambiguity and referral needs."),
        ("prompt", "hybrid_moe_stress_scenarios", "Mix debt, document control, immigration status, wage deductions, and benign distractors."),
        ("prompt", "applicability_judge_seed_tags", "Create seed tags where content implies sectors missing from metadata."),
        ("dimension", "financial_obfuscation_dimensions", "Add dimensions for deductions, kickbacks, debt ledgers, and payroll intermediaries."),
        ("dimension", "camouflage_pretext_dimensions", "Add dimensions for safekeeping, training fees, tourist processing, and legal-cover pretexts."),
        ("test", "provider_registry_fixture_tests", "Add fixture tests for search/crawl/extract provider fallback behavior."),
        ("handoff", "frontier_resume_state_refresh", "Refresh frontier_handoff.md after each committed slice."),
    ]
    tool_score = {row["tool_id"]: row["fit_score"] for row in rows}
    completed_branches = {
        "prototype_brave_search_adapter",
        "prototype_github_search_tool_discovery",
        "prototype_trafilatura_html_extractor",
        "prototype_pdfplumber_pdf_extractor",
        "prototype_pypdf_lightweight_fallback",
        "provider_registry_fixture_tests",
        "frontier_resume_state_refresh",
    }
    branches = []
    for index, (kind, branch_id, action) in enumerate(branch_specs, start=1):
        branches.append(
            {
                "rank": index,
                "branch_id": branch_id,
                "kind": kind,
                "action": action,
                "status": "completed" if branch_id in completed_branches else "queued",
                "privacy_boundary": "public_sources_or_synthetic_fixtures_only",
                "tool_fit_context": tool_score if index == 1 else {},
            }
        )
    return branches


def research_run_state(rows: list[dict], summary: dict, spider_summary: dict, manifest_summary: dict) -> dict:
    return {
        "schema_version": "public_research_frontier_run_state.v1",
        "generated_at": f"{CHECKED_DATE}T00:00:00Z",
        "current_loop": "tool_discovery_matrix_v1",
        "completed_loops": [
            "tool_repo_discovery_profiled_23_candidates",
            "safe_search_provider_interface_manual_brave_github",
            "safe_public_fetch_extract_interface_html_pdf_docs",
        ],
        "implemented_provider_wrappers": summary["implemented_provider_wrappers"],
        "implemented_extractor_wrappers": summary["implemented_extractor_wrappers"],
        "artifact_counts": {
            "tool_profiles": summary["tool_profiles"],
            "implemented_search_provider_wrappers": len(summary["implemented_provider_wrappers"]),
            "implemented_extractor_wrappers": len(summary["implemented_extractor_wrappers"]),
            "search_provider_registry": len(provider_registry("search", rows)["providers"]),
            "crawler_provider_registry": len(provider_registry("crawler", rows)["providers"]),
            "extractor_provider_registry": len(provider_registry("extractor", rows)["providers"]),
            "source_candidates": spider_summary.get("source_candidates", 0),
            "source_profiles": spider_summary.get("source_profiles", 0),
            "knowledge_objects": spider_summary.get("knowledge_objects", 0),
            "dimension_candidates": spider_summary.get("dimension_candidates", 0),
            "prompt_candidates": spider_summary.get("prompt_candidates", 0),
            "source_fetch_manifest": manifest_summary.get("source_fetch_manifest", 0),
            "source_domain_frontier": manifest_summary.get("source_domain_frontier", 0),
        },
        "next_30_branches": next_frontier_branches(rows),
        "privacy": summary["privacy"],
        "resume_notes": [
            "Start next loop by selecting the highest-value queued branch.",
            "Do not run OSINT-adjacent tools operationally.",
            "Keep no-network/manual fallbacks green before adding optional adapters.",
        ],
    }


def research_frontier(rows: list[dict], summary: dict) -> dict:
    return {
        "schema_version": "public_research_frontier.v1",
        "generated_at": f"{CHECKED_DATE}T00:00:00Z",
        "frontier_source": "tool_survey_and_existing_public_research_spider",
        "tool_decision_counts": summary["decision_counts"],
        "branches": next_frontier_branches(rows),
    }


def frontier_handoff(state: dict, summary: dict) -> str:
    lines = [
        "# Public Research Frontier Handoff",
        "",
        "Generated by `scripts/public_tool_survey.py`.",
        "",
        "Current slice:",
        "",
        "- Tool/repo discovery matrix created.",
        "- Search, crawler, and extractor provider registries created.",
        "- Manual, Brave, and GitHub search provider wrappers implemented with fixture tests.",
        "- Public HTML, PDF, and document extraction wrappers implemented with no-network fixtures.",
        "- OSINT-adjacent tools remain rejected for operational use.",
        "- No private case files or raw private text were ingested.",
        "",
        "Counts:",
        "",
        f"- Tool profiles: {summary['tool_profiles']}",
        f"- Adopted/candidate tools: {len(summary['adopted_or_candidate_tools'])}",
        f"- Implemented search provider wrappers: {len(summary['implemented_provider_wrappers'])}",
        f"- Implemented extractor wrappers: {len(summary['implemented_extractor_wrappers'])}",
        f"- Rejected operational tools: {len(summary['rejected_operational_tools'])}",
        f"- Source candidates already in spider pack: {state['artifact_counts']['source_candidates']}",
        f"- Source fetch manifest entries: {state['artifact_counts']['source_fetch_manifest']}",
        f"- Source domain frontier entries: {state['artifact_counts']['source_domain_frontier']}",
        f"- Knowledge objects already in spider pack: {state['artifact_counts']['knowledge_objects']}",
        f"- Prompt candidates already in spider pack: {state['artifact_counts']['prompt_candidates']}",
        "",
        "Next 30 branches:",
        "",
    ]
    for branch in state["next_30_branches"]:
        lines.append(f"{branch['rank']}. `{branch['branch_id']}` [{branch['status']}] - {branch['action']}")
    lines.append("")
    return "\n".join(lines)


def adoption_notes(rows: list[dict], summary: dict) -> str:
    adopted = [row for row in rows if row["adoption_decision"].startswith("adopt_")]
    deferred = [row for row in rows if row["adoption_decision"].startswith("defer_")]
    rejected = [row for row in rows if row["adoption_decision"].startswith("reject_")]
    lines = [
        "# Public Research Tool Adoption Notes",
        "",
        "Generated by `scripts/public_tool_survey.py`.",
        "",
        "Purpose: record safe search, crawl, extraction, archive, and tool-discovery",
        "options before any long-running research spider adopts new dependencies.",
        "",
        "Privacy boundary:",
        "",
        "- No raw private case files or private text may be sent to tools or APIs.",
        "- OSINT-adjacent repos are design references only.",
        "- No people, email, subdomain, credential, stealth, evasion, CAPTCHA, or",
        "  proxy-rotation harvesting is allowed from this repo.",
        "- Core artifact generation must keep a deterministic no-network fallback.",
        "",
        "Counts:",
        "",
        f"- Tool profiles: {summary['tool_profiles']}",
        f"- Candidate/adopt decisions: {len(adopted)}",
        f"- Implemented search provider wrappers: {len(summary['implemented_provider_wrappers'])}",
        f"- Implemented extractor wrappers: {len(summary['implemented_extractor_wrappers'])}",
        f"- Deferred decisions: {len(deferred)}",
        f"- Rejected operational tools: {len(rejected)}",
        "",
        "Implemented extractor wrappers:",
        "",
    ]
    for tool_id in summary["implemented_extractor_wrappers"]:
        lines.append(f"- `{tool_id}`: available through `scripts/public_fetch_extract.py` with redaction and fixture tests.")
    lines.extend([
        "",
        "Adopt or prototype first:",
        "",
    ])
    for row in adopted:
        lines.append(f"- `{row['tool_id']}` ({row['category']}): {row['notes']}")
    lines.extend(["", "Deferred until a concrete need or review exists:", ""])
    for row in deferred:
        lines.append(f"- `{row['tool_id']}`: {row['rejection_reason'] or row['notes']}")
    lines.extend(["", "Rejected for operational use; keep only as design cautions:", ""])
    for row in rejected:
        lines.append(f"- `{row['tool_id']}`: {row['rejection_reason']}")
    lines.extend(["", "Next safe adapter order:", ""])
    lines.extend(
        [
            "1. Keep `manual_dork_queue` as the default search fallback.",
            "2. Add a Brave Search API wrapper only behind an environment-key gate.",
            "3. Add trafilatura/pdfplumber/pypdf extractors behind local fixture tests.",
            "4. Add Scrapy or advertools only after a source-family needs real crawling.",
            "5. Keep browser automation and heavy document ETL deferred until needed.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
            count += 1
    return count


def run_pipeline(out_dir: Path) -> dict:
    rows = matrix_rows()
    validate_matrix(rows)
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix_count = write_jsonl(out_dir / "tool_evaluation_matrix.jsonl", rows)
    search_registry = provider_registry("search", rows)
    crawler_registry = provider_registry("crawler", rows)
    extractor_registry = provider_registry("extractor", rows)
    summary = summarize(rows)
    spider_summary = load_research_spider_summary(out_dir)
    manifest_summary = load_source_manifest_summary(out_dir)
    state = research_run_state(rows, summary, spider_summary, manifest_summary)

    write_json(out_dir / "search_provider_registry.json", search_registry)
    write_json(out_dir / "crawler_provider_registry.json", crawler_registry)
    write_json(out_dir / "extractor_provider_registry.json", extractor_registry)
    write_json(out_dir / "tool_survey_summary.json", summary)
    write_json(out_dir / "research_run_state.json", state)
    write_json(out_dir / "research_frontier.json", research_frontier(rows, summary))
    (out_dir / "tool_adoption_notes.md").write_text(adoption_notes(rows, summary), encoding="utf-8", newline="\n")
    (out_dir / "frontier_handoff.md").write_text(frontier_handoff(state, summary), encoding="utf-8", newline="\n")

    return {
        **summary,
        "out_dir": str(out_dir),
        "matrix_rows_written": matrix_count,
        "search_providers": len(search_registry["providers"]),
        "crawler_providers": len(crawler_registry["providers"]),
        "extractor_providers": len(extractor_registry["providers"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--checked-date", default=CHECKED_DATE, help="Informational only; matrix uses the committed survey date.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_pipeline(args.out_dir)
    print(
        "tool_profiles={tool_profiles} search={search_providers} crawler={crawler_providers} "
        "extractor={extractor_providers} rejected={rejected} out={out_dir}".format(
            rejected=len(summary["rejected_operational_tools"]),
            **summary,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
