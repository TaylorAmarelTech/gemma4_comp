from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

survey = importlib.import_module("public_tool_survey")


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_matrix_covers_required_tool_families_and_fields():
    rows = survey.matrix_rows()
    survey.validate_matrix(rows)
    by_id = {row["tool_id"]: row for row in rows}

    expected = {
        "scrapy",
        "crawlee_python",
        "crawl4ai",
        "trafilatura",
        "advertools",
        "playwright_python",
        "pymupdf",
        "pdfplumber",
        "pypdf",
        "markitdown",
        "unstructured",
        "warcio",
        "courlan",
        "searxng",
        "brave_search_api",
        "serpapi",
        "ddgs",
        "pagodo",
        "photon",
        "theharvester",
        "metagoofil",
    }
    assert expected <= set(by_id)
    assert all(survey.REQUIRED_MATRIX_FIELDS <= set(row) for row in rows)
    assert by_id["manual_dork_queue"]["safe_default"] is True
    assert by_id["brave_search_api"]["requires_credentials"] is True


def test_osint_adjacent_tools_are_not_operationalized():
    rows = survey.matrix_rows()
    by_id = {row["tool_id"]: row for row in rows}

    for tool_id in {"pagodo", "photon", "theharvester", "metagoofil"}:
        row = by_id[tool_id]
        assert row["adoption_decision"] == "reject_operational_use_inspiration_only"
        assert not row["registries"]
        assert "private_case_ingestion" in row
        assert row["private_case_ingestion"] is False


def test_provider_registries_exclude_rejected_osint_tools():
    rows = survey.matrix_rows()
    search = survey.provider_registry("search", rows)
    crawler = survey.provider_registry("crawler", rows)
    extractor = survey.provider_registry("extractor", rows)

    search_ids = {p["tool_id"] for p in search["providers"]}
    crawler_ids = {p["tool_id"] for p in crawler["providers"]}
    extractor_ids = {p["tool_id"] for p in extractor["providers"]}

    assert {"manual_dork_queue", "brave_search_api", "searxng", "serpapi"} <= search_ids
    assert {"scrapy", "advertools", "crawl4ai", "playwright_python"} <= crawler_ids
    assert {"trafilatura", "pdfplumber", "pypdf", "warcio", "courlan"} <= extractor_ids
    assert not ({"pagodo", "photon", "theharvester", "metagoofil"} & (search_ids | crawler_ids | extractor_ids))
    assert search["privacy_boundary"]["remote_private_queries_allowed"] is False


def test_pipeline_writes_deterministic_artifacts(tmp_path):
    summary = survey.run_pipeline(tmp_path)

    assert summary["tool_profiles"] >= 21
    assert summary["matrix_rows_written"] == summary["tool_profiles"]
    assert summary["search_providers"] >= 5
    assert summary["crawler_providers"] >= 4
    assert summary["extractor_providers"] >= 7
    assert set(summary["implemented_provider_wrappers"]) == {
        "manual_dork_queue",
        "brave_search_api",
        "github_search_api",
    }
    assert set(summary["implemented_extractor_wrappers"]) == {
        "stdlib_html",
        "trafilatura_optional",
        "pdfplumber_optional",
        "pypdf_optional",
        "markitdown_optional",
    }
    assert "theharvester" in summary["rejected_operational_tools"]

    matrix = _jsonl(tmp_path / "tool_evaluation_matrix.jsonl")
    assert len(matrix) == summary["tool_profiles"]
    assert (tmp_path / "tool_adoption_notes.md").exists()
    assert (tmp_path / "search_provider_registry.json").exists()
    assert (tmp_path / "crawler_provider_registry.json").exists()
    assert (tmp_path / "extractor_provider_registry.json").exists()
    assert (tmp_path / "tool_survey_summary.json").exists()
    assert (tmp_path / "research_run_state.json").exists()
    assert (tmp_path / "research_frontier.json").exists()
    assert (tmp_path / "frontier_handoff.md").exists()

    state = json.loads((tmp_path / "research_run_state.json").read_text(encoding="utf-8"))
    assert len(state["next_30_branches"]) == 30
    assert state["artifact_counts"]["implemented_search_provider_wrappers"] == 3
    assert state["artifact_counts"]["implemented_extractor_wrappers"] == 5
    assert state["artifact_counts"]["source_fetch_manifest"] == 0
    assert state["artifact_counts"]["source_domain_frontier"] == 0
    assert state["artifact_counts"]["source_archive_manifest"] == 0
    assert state["artifact_counts"]["sitemap_probe_queue"] == 0
    assert state["artifact_counts"]["domain_crawl_policy"] == 0
    assert state["artifact_counts"]["sitemap_discovery_dorks"] == 0
    assert state["artifact_counts"]["branching_research_queue"] == 0
    assert state["artifact_counts"]["conversation_prompts"] == 0
    assert state["artifact_counts"]["decomposition_followup_queries"] == 0
    assert state["artifact_counts"]["decomposition_mixed_conversations"] == 0
    assert state["artifact_counts"]["hybrid_scenario_prompts"] == 0
    assert state["artifact_counts"]["long_context_stress_prompts"] == 0
    assert state["artifact_counts"]["refusal_detection_prompts"] == 0
    assert state["artifact_counts"]["source_decompositions"] == 0
    assert "Long-context stress prompts" in (tmp_path / "frontier_handoff.md").read_text(encoding="utf-8")
    assert "Refusal/detection prompts" in (tmp_path / "frontier_handoff.md").read_text(encoding="utf-8")
    assert "Source decompositions" in (tmp_path / "frontier_handoff.md").read_text(encoding="utf-8")
    assert "Decomposition follow-up dorks" in (tmp_path / "frontier_handoff.md").read_text(encoding="utf-8")
    assert "Decomposition mixed conversations" in (tmp_path / "frontier_handoff.md").read_text(encoding="utf-8")
    branch_status = {branch["branch_id"]: branch["status"] for branch in state["next_30_branches"]}
    assert branch_status["prototype_brave_search_adapter"] == "completed"
    assert branch_status["prototype_github_search_tool_discovery"] == "completed"
    assert branch_status["prototype_trafilatura_html_extractor"] == "completed"
    assert branch_status["prototype_pdfplumber_pdf_extractor"] == "completed"
    assert branch_status["prototype_pypdf_lightweight_fallback"] == "completed"
    assert branch_status["prototype_warcio_manifest_archiving"] == "completed"
    assert branch_status["evaluate_advertools_sitemap_crawl"] == "completed"
    assert branch_status["philippines_court_illegal_recruitment_cases"] == "completed"
    assert branch_status["multi_turn_worker_triage_conversations"] == "completed"
    assert branch_status["hybrid_moe_stress_scenarios"] == "completed"
    assert branch_status["applicability_judge_seed_tags"] == "completed"
    assert state["privacy"]["osint_adjacent_tools_operationalized"] is False

    combined = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.iterdir())
    assert "C:\\projects\\major_cases" not in combined
    assert '"private_case_ingestion": true' not in combined
    assert "No raw private case files" in combined
