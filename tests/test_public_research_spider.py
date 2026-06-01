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
    queries = spider.build_queries(max_per_family=20)
    text = "\n".join(q["query"] for q in queries)

    assert "site:iom.int" in text or "site:publications.iom.int" in text
    assert "site:gov.ph" in text or "site:dmw.gov.ph" in text
    assert "site:gov.hk" in text or "site:labour.gov.hk" in text
    assert "site:gov.cn" in text or "site:english.court.gov.cn" in text
    assert "site:justice.gov" in text or "site:dhs.gov" in text
    assert "site:gov.uk" in text or "site:cps.gov.uk" in text
    assert "site:publicsafety.gc.ca" in text or "site:justice.gc.ca" in text
    assert "site:ag.gov.au" in text or "site:afp.gov.au" in text
    assert "site:immigration.govt.nz" in text or "site:employment.govt.nz" in text
    assert "site:mom.gov.sg" in text or "site:police.gov.sg" in text
    assert "site:mohr.gov.my" in text or "site:moha.gov.my" in text
    assert "filetype:pdf" in text
    assert any(q["intent"] == "debt_bondage_mechanics" for q in queries)
    assert any(q["intent"] == "victim_referral_access_to_justice" for q in queries)


def test_deep_dorks_include_google_operators_and_non_html_artifacts():
    dorks = spider.build_deep_dorks(max_per_family=220)
    text = "\n".join(q["query"] for q in dorks)

    assert "intitle:" in text
    assert "inurl:" in text
    assert "filetype:pdf" in text
    assert "filetype:xlsx" in text
    assert "after:2020" in text
    assert any(q["intent"] == "case_digest_evidence" for q in dorks)
    assert any(q["intent"] == "fishing_seafood_forced_labor" for q in spider.build_queries(max_per_family=20))
    assert "migrant fishers" in text
    assert "transport logistics" in text


def test_sparse_signal_terms_and_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=220))
    signals = {signal for row in candidates for signal in row["signals"]}

    assert "indicators-human-trafficking" in source_text
    assert "technology-facilitating-trafficking" in source_text
    assert "working-to-stop-migrant-exploitation" in source_text
    assert {"accommodation_control", "immigration_status_control", "online_bait"} <= signals
    assert "sham employment websites" in dork_text
    assert "migrant exploitation protection work visa" in dork_text


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


def test_source_profile_second_wave_and_knowledge_objects_stay_public_metadata_only():
    candidates = spider.source_candidates_from_hits(
        [
            spider.SearchHit(
                url="https://www.justice.gov/humantrafficking/example?utm_source=x",
                title="Forced labor prosecution involving recruitment fees",
                snippet="Public report mentions debt bondage, passport confiscation, and victim identification.",
            )
        ]
    )

    terms = spider.extract_terms_for_candidate(candidates[0])
    profiles = spider.source_profiles(candidates)
    wave2 = spider.second_wave_queries(candidates, max_per_source=4)
    knowledge = spider.generate_knowledge_objects(candidates, profiles)
    dimensions = spider.generate_dimension_candidates(knowledge)

    assert "debt bondage" in terms
    assert profiles[0]["recommended_followup_terms"]
    assert len(wave2) == 4
    assert all(row["parent_source_candidate_id"] == candidates[0]["id"] for row in wave2)
    assert knowledge[0]["status"] == "candidate_needs_human_or_model_verification"
    assert knowledge[0]["safe_use"]["private_case_ingestion"] is False
    assert dimensions
    assert "private names" in " ".join(dimensions[0]["negative_controls"])


def test_source_profiles_preserve_redacted_public_metadata_and_sector_terms():
    candidates = spider.source_candidates_from_hits(
        [
            spider.SearchHit(
                url="https://www.ilo.org/example/fair-seas",
                title="Guidelines for fair labour market services for migrant fishers",
                snippet="Fishing vessel and seafood processing workers faced debt bondage, document retention, and wage theft.",
            ),
            spider.SearchHit(
                url="https://www.europol.europa.eu/example/action-days",
                title="Labour exploitation in transport logistics and construction",
                snippet="Public action days flagged warehouse, driver, construction site, and document-control indicators.",
            ),
        ]
    )

    profiles = spider.source_profiles(candidates)

    all_sectors = {sector for profile in profiles for sector in profile["sector_terms"]}
    assert {"fishing", "construction", "logistics"} <= all_sectors
    assert profiles[0]["source_title"]
    assert profiles[0]["source_snippet"]
    assert all(profile["privacy"]["public_url_metadata_only"] is True for profile in profiles)


def test_new_public_source_signals_create_dimension_candidates():
    candidates = spider.source_candidates_from_hits(
        [
            spider.SearchHit(
                url="https://www.gla.gov.uk/example",
                title="Forced labour report on care-sector recruitment fees and housing",
                snippet=(
                    "Workers faced attempted overcharging, unpaid wages, unsafe accommodation, "
                    "constant surveillance, and bait-and-switch contract deception."
                ),
            )
        ]
    )

    signals = set(candidates[0]["signals"])
    assert {
        "fee_overcharging",
        "wage_theft",
        "accommodation_control",
        "surveillance_isolation",
        "contract_deception",
    } <= signals
    knowledge = spider.generate_knowledge_objects(candidates, spider.source_profiles(candidates))
    dimensions = spider.generate_dimension_candidates(knowledge)
    dim_ids = {row["candidate_dim_id"] for row in dimensions}
    assert any("detects_fee_overcharging" in dim_id for dim_id in dim_ids)
    assert any("detects_wage_theft" in dim_id for dim_id in dim_ids)


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
    assert spider.profile_for_url("https://jtksm.mohr.gov.my/report.pdf")["id"] == "malaysia_labour_homeaffairs"
    assert spider.profile_for_url("https://www.gla.gov.uk/who-we-are/modern-slavery")["id"] == "uk_homeoffice_cps"


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
    assert summary["deep_search_dorks"] >= 20
    assert summary["source_candidates"] >= 40
    assert summary["source_profiles"] == summary["source_candidates"]
    assert summary["second_wave_queries"] >= summary["source_candidates"]
    assert summary["knowledge_objects"] == summary["source_candidates"]
    assert summary["dimension_candidates"] >= 10
    assert summary["prompt_candidates"] == 6
    assert summary["test_candidates"] >= 6
    assert (tmp_path / "search_queries.jsonl").exists()
    assert (tmp_path / "deep_search_dorks.jsonl").exists()
    assert (tmp_path / "source_candidates.jsonl").exists()
    assert (tmp_path / "source_profiles.jsonl").exists()
    assert (tmp_path / "second_wave_queries.jsonl").exists()
    assert (tmp_path / "knowledge_objects.jsonl").exists()
    assert (tmp_path / "dimension_candidates.jsonl").exists()
    assert (tmp_path / "prompt_candidates.jsonl").exists()
    assert (tmp_path / "fallback_playbook.json").exists()

    prompt_text = (tmp_path / "prompt_candidates.jsonl").read_text(encoding="utf-8")
    knowledge_text = (tmp_path / "knowledge_objects.jsonl").read_text(encoding="utf-8")
    assert "public_url_metadata_only_no_private_case_snippets" in prompt_text
    assert "C:\\projects\\major_cases" not in prompt_text
    assert "candidate_needs_human_or_model_verification" in knowledge_text
    assert "C:\\projects\\major_cases" not in knowledge_text
