from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

sitemap = importlib.import_module("public_sitemap_frontier")


def _domain(domain: str = "example.gov") -> dict:
    return {
        "schema_version": "public_source_domain_frontier.v1",
        "domain": domain,
        "source_count": 3,
        "source_families": ["philippines_gov"],
        "jurisdictions": ["Philippines"],
        "top_signals": ["debt_bondage", "illegal_recruitment"],
        "robots_url": f"https://{domain}/robots.txt",
        "sitemap_candidates": [f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml"],
        "queue_policy": {
            "network_fetch_default": False,
            "sitemap_first": True,
            "manual_review_before_fetch": True,
            "respect_robots_txt": True,
            "polite_delay_seconds": 3,
        },
    }


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_probe_queue_includes_robots_and_sitemaps_without_network_default():
    rows = sitemap.probe_queue_rows([_domain()])

    assert [row["probe_type"] for row in rows] == ["robots_txt", "sitemap", "sitemap"]
    assert rows[0]["parser_plan"]["primary"] == "urllib_robotparser_stdlib"
    assert rows[1]["parser_plan"]["primary"] == "advertools_sitemap_to_df_optional"
    assert "recruitment fee" in rows[1]["parser_plan"]["keyword_filters"]
    assert all(row["network_policy"]["network_fetch_default"] is False for row in rows)
    assert all(row["privacy"]["raw_private_cases_ingested"] is False for row in rows)
    assert all(row["privacy"]["private_case_terms_allowed"] is False for row in rows)


def test_domain_policy_is_sitemap_first_and_rejects_evasion_patterns():
    row = sitemap.domain_policy_rows([_domain("agency.gov")])[0]

    assert row["domain"] == "agency.gov"
    assert row["crawl_order"][:2] == ["robots_txt", "sitemap"]
    assert row["crawl_policy"]["respect_robots_txt"] is True
    assert row["crawl_policy"]["disable_javascript_browser_by_default"] is True
    assert row["crawl_policy"]["no_proxy_rotation"] is True
    assert row["crawl_policy"]["no_evasion"] is True
    assert "/login" in row["deny_path_keywords"]
    assert "illegal recruitment" in row["allow_path_keywords"]


def test_browser_fetch_allowlist_is_deferred_and_rejects_unsafe_browser_patterns():
    row = sitemap.browser_fetch_allowlist_rows([_domain("justice.gov")])[0]

    assert row["schema_version"] == "public_browser_fetch_allowlist.v1"
    assert row["status"] == "deferred_policy_only_no_browser_fetch"
    assert row["browser_tool"] == "playwright_python"
    assert row["network_policy"]["network_fetch_default"] is False
    assert row["network_policy"]["manual_review_before_fetch"] is True
    assert row["network_policy"]["requires_http_extraction_attempt_first"] is True
    assert row["network_policy"]["requires_robots_check"] is True
    assert row["browser_state_policy"]["ephemeral_context_only"] is True
    assert row["browser_state_policy"]["persistent_context_allowed"] is False
    assert row["browser_state_policy"]["storage_state_saved"] is False
    assert row["browser_state_policy"]["cookies_saved"] is False
    assert {"stealth", "proxy_rotation", "captcha_bypass", "credentialed_login"} <= set(
        row["forbidden_browser_features"]
    )
    assert {"robots_disallow", "login_or_credential_required", "private_case_terms_or_identifiers"} <= set(
        row["denied_when"]
    )
    assert "/login" in row["deny_path_keywords"]
    assert "mailto:" in row["deny_path_keywords"]
    assert row["privacy"]["raw_private_cases_ingested"] is False
    assert row["privacy"]["people_or_contact_harvesting_allowed"] is False


def test_sitemap_discovery_dorks_are_public_domain_only():
    rows = sitemap.sitemap_discovery_dorks([_domain("justice.gov")])

    assert len(rows) == 4
    assert rows[0]["query"] == "site:justice.gov inurl:sitemap filetype:xml"
    assert any('"debt bondage"' in row["query"] for row in rows)
    assert all(row["privacy"]["public_domain_only"] is True for row in rows)
    assert all(row["privacy"]["private_case_terms_allowed"] is False for row in rows)


def test_pipeline_writes_sitemap_frontier_artifacts(tmp_path):
    out_dir = tmp_path / "research_spider"
    out_dir.mkdir()
    (out_dir / "source_domain_frontier.jsonl").write_text(
        json.dumps(_domain("one.gov")) + "\n" + json.dumps(_domain("two.org")) + "\n",
        encoding="utf-8",
    )

    summary = sitemap.run_pipeline(out_dir)

    assert summary["domains"] == 2
    assert summary["sitemap_probe_queue"] == 6
    assert summary["domain_crawl_policy"] == 2
    assert summary["browser_fetch_allowlist"] == 2
    assert summary["sitemap_discovery_dorks"] == 8
    assert summary["probe_types"] == {"robots_txt": 2, "sitemap": 4}
    assert summary["privacy"]["network_fetch_default"] is False
    assert (out_dir / "sitemap_frontier_summary.json").exists()
    assert len(_jsonl(out_dir / "sitemap_probe_queue.jsonl")) == 6
    assert len(_jsonl(out_dir / "domain_crawl_policy.jsonl")) == 2
    assert len(_jsonl(out_dir / "browser_fetch_allowlist.jsonl")) == 2
    assert len(_jsonl(out_dir / "sitemap_discovery_dorks.jsonl")) == 8

    combined = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.iterdir())
    assert "C:\\projects\\major_cases" not in combined
    assert '"raw_private_cases_ingested": true' not in combined
    assert '"private_case_terms_allowed": true' not in combined
    assert '"network_fetch_default": true' not in combined
