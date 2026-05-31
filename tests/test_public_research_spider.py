from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

spider = importlib.import_module("public_research_spider")


def test_build_queries_covers_requested_public_source_families():
    queries = spider.build_queries(max_per_family=12)
    text = "\n".join(q["query"] for q in queries)

    assert "site:iom.int" in text or "site:publications.iom.int" in text
    assert "site:gov.ph" in text or "site:dmw.gov.ph" in text
    assert "site:gov.hk" in text or "site:labour.gov.hk" in text
    assert "site:gov.cn" in text or "site:english.court.gov.cn" in text
    assert "filetype:pdf" in text
    assert any(q["intent"] == "debt_bondage_mechanics" for q in queries)
    assert any(q["intent"] == "victim_referral_access_to_justice" for q in queries)


def test_redaction_and_prompt_generation_do_not_emit_contact_details():
    email = "helper" + "@example.org"
    phone = "+1 202" + " 555 0100"
    passport = "AB" + "1234567"
    redacted, counts = spider.redact_text(f"Email {email}, call {phone}, passport {passport}.")

    assert email not in redacted
    assert phone not in redacted
    assert passport not in redacted
    assert counts["email"] == 1
    assert counts["phone"] == 1
    assert counts["passport"] == 1

    candidates = spider.source_candidates_from_hits(
        [
            spider.SearchHit(
                url="https://immigration.gov.ph/example",
                title="Debt bondage case",
                snippet=f"Email {email} about debt bondage and passport control.",
            )
        ]
    )
    prompts = spider.generate_prompt_candidates(candidates)
    prompt_text = json.dumps(prompts)
    assert email not in prompt_text
    assert "[REDACTED_EMAIL]" not in prompt_text
    assert "[WORKER]" not in prompt_text  # this spider uses prose placeholders, not raw worker facts
    assert "public-source context" in prompts[0]["text"]


def test_url_normalization_and_scoring_prefer_official_sources():
    assert (
        spider.normalize_url("https://Example.org/report?utm_source=x&b=2#a")
        == "https://example.org/report?b=2"
    )

    official = spider.SearchHit(
        url="https://www.eaa.labour.gov.hk/en/helpers.html?utm_source=x",
        title="Foreign domestic helper agency fee and passport guidance",
        snippet="Agency fees, take up loans, surrender passport, debt bondage, salary deduction.",
    )
    commentary = spider.SearchHit(
        url="https://example-blog.test/hk-helper-fees",
        title="Foreign domestic helper agency fee and passport guidance",
        snippet="Agency fees, take up loans, surrender passport, debt bondage, salary deduction.",
    )

    assert spider.score_hit(official)["score"] > spider.score_hit(commentary)["score"]
    assert spider.score_hit(official)["source_family"] == "hong_kong_gov"


def test_robots_cache_disallows_blocked_paths_and_defaults_conservatively():
    def fake_request(url: str, **kwargs) -> bytes:
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow: /private\nCrawl-delay: 7\n"
        raise AssertionError(f"unexpected fetch: {url}")

    cache = spider.RobotsCache(request_func=fake_request)

    blocked = cache.decision("https://example.org/private/case.html")
    allowed = cache.decision("https://example.org/public/report.html")

    assert not blocked.allowed
    assert blocked.reason == "robots_disallow"
    assert allowed.allowed
    assert allowed.crawl_delay_seconds == 7.0


def test_missing_provider_key_returns_fallback_without_network(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    query = spider.build_queries(max_per_family=1)[0]

    hits, error = spider.run_search_provider("brave", query)

    assert hits == []
    assert error["status"] == "missing_api_key"
    assert error["fallback"] == "manual_search_url"


def test_pipeline_writes_deterministic_no_network_artifacts(tmp_path):
    args = spider.build_parser().parse_args(
        [
            "--out-dir",
            str(tmp_path),
            "--max-queries-per-family",
            "4",
            "--manual-fallback-limit",
            "5",
            "--prompt-limit",
            "6",
        ]
    )

    summary = spider.run_pipeline(args)

    assert summary["queries"] >= 20
    assert summary["source_candidates"] >= 8
    assert summary["prompt_candidates"] == 6
    assert summary["test_candidates"] >= 6
    assert (tmp_path / "search_queries.jsonl").exists()
    assert (tmp_path / "source_candidates.jsonl").exists()
    assert (tmp_path / "prompt_candidates.jsonl").exists()
    assert (tmp_path / "fallback_playbook.json").exists()

    prompt_text = (tmp_path / "prompt_candidates.jsonl").read_text(encoding="utf-8")
    assert "public_url_metadata_only_no_private_case_snippets" in prompt_text
    assert "C:\\projects\\major_cases" not in prompt_text
