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
    queries = spider.build_queries(max_per_family=48)
    text = "\n".join(q["query"] for q in queries)

    assert "site:iom.int" in text or "site:publications.iom.int" in text
    assert "site:gov.ph" in text or "site:dmw.gov.ph" in text
    assert "site:gov.hk" in text or "site:labour.gov.hk" in text
    assert "site:gov.cn" in text or "site:english.court.gov.cn" in text
    assert "site:justice.gov" in text or "site:dhs.gov" in text
    assert "site:gov.uk" in text or "site:cps.gov.uk" in text
    assert "site:fbi.gov" in text
    assert "site:egmontgroup.org" in text
    assert "site:publicsafety.gc.ca" in text or "site:justice.gc.ca" in text
    assert "site:ag.gov.au" in text or "site:afp.gov.au" in text
    assert "site:immigration.govt.nz" in text or "site:employment.govt.nz" in text
    assert "site:mom.gov.sg" in text or "site:police.gov.sg" in text
    assert "site:mohr.gov.my" in text or "site:moha.gov.my" in text
    assert "site:dsi.go.th" in text or "site:mol.go.th" in text
    assert "site:akp.gov.kh" in text or "site:interior.gov.kh" in text
    assert "site:mohre.gov.ae" in text
    assert "site:mol.gov.qa" in text
    assert "site:hrsd.gov.sa" in text or "site:my.gov.sa" in text
    assert "filetype:pdf" in text
    assert any(q["intent"] == "debt_bondage_mechanics" for q in queries)
    assert any(q["intent"] == "victim_referral_access_to_justice" for q in queries)
    assert any(q["intent"] == "asean_forced_criminality_and_repatriation" for q in queries)
    assert any(q["intent"] == "gulf_sponsorship_and_mobility_controls" for q in queries)
    assert any(q["intent"] == "payment_instrument_and_virtual_asset_trails" for q in queries)


def test_deep_dorks_include_google_operators_and_non_html_artifacts():
    dorks = spider.build_deep_dorks(max_per_family=300)
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
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=300))
    signals = {signal for row in candidates for signal in row["signals"]}

    assert "indicators-human-trafficking" in source_text
    assert "technology-facilitating-trafficking" in source_text
    assert "working-to-stop-migrant-exploitation" in source_text
    assert {"accommodation_control", "immigration_status_control", "online_bait"} <= signals
    assert "sham employment websites" in dork_text
    assert "migrant exploitation protection work visa" in dork_text


def test_iom_and_hong_kong_official_report_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    signals = {signal for row in candidates for signal in row["signals"]}

    assert spider.profile_for_url("https://publications.iom.int/system/files/pdf/Fair-Ethical-Recruitment.pdf")["id"] == "iom"
    assert spider.profile_for_url("https://www.fdh.labour.gov.hk/en/faq.html")["id"] == "hong_kong_gov"
    assert "regional-baseline-assessment-forced-labour-unfair-and-unethical-recruitment-practices" in source_text
    assert "Fair-Ethical-Recruitment.pdf" in source_text
    assert "migrants_and_their_vulnerability.pdf" in source_text
    assert "P2018012600676" in source_text
    assert "fdh.labour.gov.hk/en/faq.html" in source_text
    assert {"debt_bondage", "fee_overcharging", "forced_labor"} <= signals


def test_iom_worker_voice_and_employer_guidance_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=300))
    signals = {signal for row in candidates for signal in row["signals"]}

    for needle in [
        "migrant-worker-guidelines-employers-checklist-labour-recruiter-service-agreements",
        "migrant-worker-guidelines-employers-checklist-employment-contracts",
        "migrant-worker-guidelines-employers-checklist-migrant-workers-accommodations",
        "MWG-Tool-1-Summary_0.pdf",
        "labour-migration-process-mapping-guide-migrant-worker-interview-tool",
        "establishing-ethical-recruitment-practices-hospitality-industry",
    ]:
        assert needle in source_text
    assert {"worker_voice_grievance", "referral", "accommodation_control"} <= signals
    assert "migrant worker interview" in dork_text
    assert "grievance mechanism" in dork_text
    assert "access to remedy" in dork_text


def test_sherloc_bali_and_relationship_lure_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=220))
    signals = {signal for row in candidates for signal in row["signals"]}

    assert spider.profile_for_url("https://sherloc.unodc.org/cld/en/case-law-doc/example")["id"] == "intergovernmental"
    assert spider.profile_for_url("https://www.aic.gov.au/publications/special/special-22")["id"] == "australia_homeaffairs_agd_afp"
    assert spider.profile_for_url("https://globalinitiative.net/example.pdf")["id"] == "regional_research_programs"
    for needle in [
        "case_no._23572010",
        "crim._case_no._21898",
        "o.o.o._and_others_v_commissioner",
        "united_states_v._abdel_nasser_youssef_ibrahim",
        "sc-online-sweetheart-guilty",
        "showdocs/1/69188",
        "articles/1263630",
        "new-reports-explore-how-transnational-crime-networks",
        "compound-crime-cyber-scam-operations",
        "cyber-scam-operations-southeast-asia",
    ]:
        assert needle in source_text
    assert {"relationship_lure", "role_shifting_complicity", "forced_criminality"} <= signals
    assert "people they know and trust" in dork_text
    assert "role-shifters" in dork_text
    assert "SHERLOC case law" in dork_text


def test_financial_obfuscation_and_nonpunishment_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=220))
    signals = {signal for row in candidates for signal in row["signals"]}

    assert spider.profile_for_url("https://www.fincen.gov/resources/advisories/example")["id"] == "financial_intelligence"
    assert spider.profile_for_url("https://www.amlc.gov.ph/example")["id"] == "financial_intelligence"
    assert spider.profile_for_url("https://egmontgroup.org/wp-content/uploads/example.pdf")["id"] == "financial_intelligence"
    assert spider.profile_for_url("https://www.fbi.gov/example")["id"] == "us_justice_dhs_state"
    assert "fincen-advisory-fin-2020-a008" in source_text
    assert "FinCEN-WCHT-Notice.pdf" in source_text
    assert "fincen-advisory-fin-2014-a008" in source_text
    assert "Virtual-assets-red-flag-indicators" in source_text
    assert "fincen-sees-increase-bsa-reporting-involving-use-convertible-virtual-currency" in source_text
    assert "money-mules" in source_text
    assert "Egmont_Group_Annual_Report_2019-2020.pdf" in source_text
    assert "EGMONT_2021-2023-BECA-III_FINAL.pdf" in source_text
    assert "oai-hts-2021-eng" in source_text
    assert "bulletins/sport-eng" in source_text
    assert "DetectingAndStoppingForcedSexualServitude" in source_text
    assert "philippines-exposure-to-external-and-internal-threats" in source_text
    assert "secretariat/438323" in source_text
    assert "principle-of-non-criminalization-of-victims" in source_text
    assert "section 45" in source_text
    assert {"financial_obfuscation", "payment_instrument_control"} <= signals
    assert "peer-to-peer transfers" in dork_text
    assert "prepaid access cards" in dork_text
    assert "convertible virtual currency" in dork_text
    assert "suspicious activity report" in dork_text
    assert "money laundering" in dork_text


def test_asean_gulf_official_corridor_sources_are_seeded():
    candidates = spider.seed_source_candidates()
    source_text = "\n".join(
        " ".join([row["url"], row["title"], row["snippet"], *row["signals"]])
        for row in candidates
    )
    dork_text = "\n".join(q["query"] for q in spider.build_deep_dorks(max_per_family=260))
    signals = {signal for row in candidates for signal in row["signals"]}

    assert spider.profile_for_url("https://www.dsi.go.th/en/Detail/example")["id"] == "thailand_labor_justice"
    assert spider.profile_for_url("https://rnk.gov.kh/article/example")["id"] == "cambodia_gov_scam_enforcement"
    assert spider.profile_for_url("https://www.mohre.gov.ae/en/example")["id"] == "uae_mohre_domestic_work"
    assert spider.profile_for_url("https://www.mol.gov.qa/admin/Publications/example.pdf")["id"] == "qatar_labour_anti_trafficking"
    assert spider.profile_for_url("https://prod.hrsd.gov.sa/sites/default/files/example.pdf")["id"] == "saudi_labour_human_rights"
    for needle in [
        "26c3d68bdb19b24daaa84decdfc68890",
        "20500b7c6eecef0d371cb5f403e43995",
        "post/detail/342578",
        "rnk.gov.kh/article/66354",
        "can-an-employer-keep-a-workers-passport",
        "mohre-12-unlicensed-domestic-worker-recruitment-offices",
        "labour-inspector-guide-combating-forced-labour-en",
        "The%20National%20Report%20on%20Combating%20Human%20Trafficking%202024.pdf",
        "The%20National%20Policy%20for%20the%20Elimination%20of%20Forced%20Labor",
    ]:
        assert needle in source_text
    assert {"sponsorship_mobility_control", "forced_criminality", "fee_overcharging", "document_control"} <= signals
    assert "sponsorship system" in dork_text
    assert "deported foreign nationals" in dork_text
    assert "casino scam center" in dork_text


def test_public_court_case_frontier_sources_are_seeded():
    source_text = json.dumps(spider.DEFAULT_SEED_SOURCES)

    assert spider.profile_for_url("https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/67018")["id"] == "courts_case_law"
    assert spider.profile_for_url("https://www.corteidh.or.cr/docs/casos/articulos/seriec_318_esp.pdf")["id"] == "courts_case_law"
    assert spider.profile_for_url("https://supremecourt.uk/cases/uksc-2019-0055")["id"] == "courts_case_law"
    assert spider.profile_for_url("https://api.sci.gov.in/supremecourt/example.pdf")["id"] == "courts_case_law"
    assert spider.profile_for_url("https://indiankanoon.org/doc/595099/")["id"] == "courts_case_law"
    for needle in [
        "showdocs/1/67018",
        "showdocs/1/53646",
        "001-172365",
        "seriec_318_esp.pdf",
        "uksc-2019-0055",
        "4072_2020_8_1502_47917",
        "indiankanoon.org/doc/595099",
    ]:
        assert needle in source_text


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


def test_financial_obfuscation_signal_creates_dimension_candidate():
    candidates = spider.source_candidates_from_hits(
        [
            spider.SearchHit(
                url="https://www.fincen.gov/example",
                title="Human trafficking financial red flags",
                snippet=(
                    "Financial institutions identified suspicious activity reports, payment patterns, "
                    "money laundering, and financial benefit from forced labor."
                ),
            )
        ]
    )

    assert "financial_obfuscation" in candidates[0]["signals"]
    knowledge = spider.generate_knowledge_objects(candidates, spider.source_profiles(candidates))
    dimensions = spider.generate_dimension_candidates(knowledge)
    assert any("detects_financial_obfuscation" in row["candidate_dim_id"] for row in dimensions)


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
