from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

expander = importlib.import_module("public_benchmark_expander")


def _profile(profile_id: str, family: str, jurisdiction: str, signals: list[str], text: str = "") -> dict:
    return {
        "id": profile_id,
        "source_candidate_id": "SRC-" + profile_id,
        "url": f"https://{family}.example.org/{profile_id}.html",
        "source_family": family,
        "source_tier": "official_government",
        "jurisdictions": [jurisdiction],
        "signals": signals,
        "recommended_followup_terms": ["debt bondage", "passport safekeeping", text],
        "top_terms": ["motel", text],
        "signal_terms": ["forced labor", "recruitment fees"],
    }


def _knowledge(profile: dict) -> dict:
    return {
        "id": "KNOW-PUBLIC-" + profile["id"],
        "source": {
            "source_candidate_id": profile["source_candidate_id"],
            "family": profile["source_family"],
            "jurisdictions": profile["jurisdictions"],
            "title": "Synthetic public source title",
            "url": profile["url"],
        },
        "distilled_context": {
            "behavior_signals": profile["signals"],
            "context_card": "Public metadata suggests debt and forced labor indicators.",
        },
    }


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_coverage_counts_signals_families_and_sector_terms():
    profiles = [
        _profile("A", "philippines_gov", "Philippines", ["debt_bondage", "fee_overcharging"], "domestic helper"),
        _profile("B", "us_justice", "United States", ["forced_labor"], "restaurant"),
    ]
    coverage = expander.coverage_summary(profiles, [_knowledge(profiles[0])], [], {"coverage": {}})

    assert coverage["counts"]["source_profiles"] == 2
    assert coverage["coverage"]["by_signal"]["debt_bondage"] == 1
    assert coverage["coverage"]["by_signal"]["fee_overcharging"] == 1
    assert coverage["coverage"]["by_source_family"]["philippines_gov"] == 1
    assert coverage["coverage"]["by_sector"]["domestic_work"] == 1
    assert "fee_overcharging" not in coverage["gaps"]["missing_signals"]
    assert "document_control" in coverage["gaps"]["missing_signals"]
    assert coverage["privacy"]["raw_private_cases_ingested"] is False


def test_detect_sectors_uses_redacted_public_metadata_fields():
    fishing = {
        "url": "https://www.ilo.org/example",
        "source_family": "intergovernmental",
        "source_title": "Guidelines for fair labour market services for migrant fishers",
        "source_snippet": "Fishing vessel and seafood processing workers faced document retention and wage theft.",
        "sector_terms": ["fishing"],
    }
    mixed = {
        "url": "https://www.europol.europa.eu/example",
        "source_family": "eu_interpol_law_enforcement",
        "source_title": "Action days in transport logistics and construction",
        "source_snippet": "Warehouse drivers and construction-site workers were screened for labour exploitation.",
        "top_terms": ["document retention"],
    }

    assert expander.detect_sectors(fishing) == ["fishing"]
    assert {"construction", "logistics"} <= set(expander.detect_sectors(mixed))


def test_corroboration_links_require_shared_signal_and_different_source_context():
    profiles = [
        _profile("A", "philippines_gov", "Philippines", ["debt_bondage", "forced_labor"]),
        _profile("B", "us_justice", "United States", ["debt_bondage"]),
        _profile("C", "us_justice", "United States", ["referral"]),
    ]
    links = expander.corroboration_links(profiles)

    assert len(links) == 1
    assert links[0]["shared_signals"] == ["debt_bondage"]
    assert links[0]["corroboration_type"] == "cross_source_metadata_signal_overlap"
    assert links[0]["privacy"]["public_url_metadata_only"] is True


def test_prompts_are_synthetic_and_keep_applicability_expectations():
    profile = _profile("A", "hong_kong_gov", "Hong Kong SAR, China", ["document_control"], "domestic helper")
    conversations = expander.conversation_prompt_rows([profile])
    long_context = expander.long_context_stress_rows(
        [profile],
        {
            "coverage": {
                "behavior_patterns": ["debt_bondage_fee_stack"],
                "camouflage_patterns": ["safekeeping_euphemism"],
                "response_traps": ["middle_needle"],
            }
        },
    )
    applicability = expander.applicability_seed_rows([profile])

    assert conversations[0]["privacy"]["synthetic_placeholders_only"] is True
    assert conversations[0]["turns"][0]["speaker"] == "Worker A"
    assert long_context[0]["privacy"]["aggregate_private_pattern_ids_only"] is True
    assert "Long-context benchmark" in long_context[0]["prompt"]
    assert "middle_needle" in long_context[0]["response_trap"]
    assert applicability[0]["prompt_metadata_tags"]["sector"] == "generic_work"
    assert applicability[0]["content_derived_expectations"]["sector"] == "domestic_work"
    assert applicability[0]["judge_should_add"] == ["document_control"]


def test_pipeline_writes_expansion_artifacts(tmp_path):
    out_dir = tmp_path / "research_spider"
    out_dir.mkdir()
    profiles = [
        _profile("A", "philippines_gov", "Philippines", ["debt_bondage", "forced_labor"], "domestic helper"),
        _profile("B", "us_justice", "United States", ["debt_bondage", "document_control"], "motel"),
        _profile("C", "netherlands_gov", "Netherlands", [], "labour exploitation"),
    ]
    for name, rows in {
        "source_profiles.jsonl": profiles,
        "knowledge_objects.jsonl": [_knowledge(profiles[0]), _knowledge(profiles[1])],
        "dimension_candidates.jsonl": [{"id": "DIM-1"}],
        "source_fetch_manifest.jsonl": [
            {"source_candidate_id": "SRC-A", "content_kind": "html"},
            {"source_candidate_id": "SRC-C", "content_kind": "plain_or_unknown"},
        ],
    }.items():
        (out_dir / name).write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    major = tmp_path / "coverage.json"
    major.write_text(
        json.dumps(
            {
                "coverage": {
                    "behavior_patterns": ["debt_bondage_fee_stack"],
                    "camouflage_patterns": ["safekeeping_euphemism"],
                    "sectors": ["hospitality"],
                }
            }
        ),
        encoding="utf-8",
    )

    summary = expander.run_pipeline(out_dir, major)

    assert summary["corroboration_links"] >= 1
    assert summary["verified_knowledge_objects"] >= 1
    assert summary["conversation_prompts"] == 3
    assert summary["hybrid_scenario_prompts"] >= 3
    assert summary["long_context_stress_prompts"] == 3
    assert summary["applicability_seed_tags"] == 2
    assert summary["rejected_or_deferred_sources"] >= 1
    assert (out_dir / "source_profile_coverage.json").exists()
    assert (out_dir / "conversation_manifest.json").exists()
    assert (out_dir / "long_context_stress_prompts.jsonl").exists()
    assert len(_jsonl(out_dir / "conversation_prompts.jsonl")) == 3
    combined = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.iterdir())
    assert '"raw_private_cases_ingested": true' not in combined
    assert "Worker A" in combined
