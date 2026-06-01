from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

queue = importlib.import_module("public_branching_research_queue")


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_profile_leads_request_safe_work_products():
    rows = queue.profile_leads(
        [
            {
                "id": "SRC-PROFILE-1",
                "source_candidate_id": "SRC-CAND-1",
                "url": "https://agency.gov/report",
                "source_family": "official_family",
                "jurisdictions": ["Example"],
                "signals": ["debt_bondage", "fee_overcharging"],
            }
        ]
    )

    assert rows[0]["lead_type"] == "source_profile_review"
    assert rows[0]["privacy"]["raw_private_cases_ingested"] is False
    assert rows[0]["privacy"]["private_case_terms_allowed"] is False
    assert "knowledge_object" in rows[0]["work_products_requested"]
    assert any("publication/update date" in step for step in rows[0]["verification"])


def test_dork_leads_map_intents_to_research_work_products():
    rows = queue.dork_leads(
        [
            {
                "id": "DORK-1",
                "intent": "case_digest_evidence",
                "priority": 90,
                "family": "courts_case_law",
                "query": "site:example.org forced labour case",
                "expected_signals": ["forced_labor"],
                "google_manual": "https://www.google.com/search?q=x",
            }
        ],
        source="deep_dork",
    )

    assert rows[0]["lead_type"] == "court_or_prosecution_case_search"
    assert "dimension_candidate" in rows[0]["work_products_requested"]
    assert rows[0]["provider_fallback_urls"]["google_manual"].startswith("https://")
    assert rows[0]["privacy"]["no_people_search_or_contact_harvesting"] is True


def test_pipeline_writes_target_sized_queue_without_private_flags(tmp_path):
    out_dir = tmp_path / "research_spider"
    out_dir.mkdir()
    (out_dir / "source_profiles.jsonl").write_text(
        json.dumps(
            {
                "id": "SRC-PROFILE-1",
                "source_candidate_id": "SRC-CAND-1",
                "url": "https://agency.gov/report",
                "source_family": "official_family",
                "jurisdictions": ["Example"],
                "signals": ["debt_bondage"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "deep_search_dorks.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "id": f"DORK-{idx}",
                    "intent": "indicator_guidance" if idx % 2 else "case_digest_evidence",
                    "priority": 100 - idx,
                    "family": "official_family",
                    "query": f"site:agency.gov trafficking {idx}",
                    "expected_signals": ["debt_bondage"],
                }
            )
            for idx in range(12)
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "sitemap_discovery_dorks.jsonl").write_text(
        json.dumps({"id": "SITE-1", "domain": "agency.gov", "query": "site:agency.gov sitemap"}) + "\n",
        encoding="utf-8",
    )
    (out_dir / "source_profile_coverage.json").write_text(
        json.dumps({"gaps": {"sparse_sectors": ["fishing"], "missing_signals": ["wage_theft"]}}),
        encoding="utf-8",
    )

    summary = queue.run_pipeline(out_dir, target_count=10)

    assert summary["branching_research_queue"] == 10
    assert summary["privacy"]["raw_private_cases_ingested"] is False
    assert summary["privacy"]["private_case_terms_allowed"] is False
    rows = _jsonl(out_dir / "branching_research_queue.jsonl")
    assert len(rows) == 10
    assert rows[0]["rank"] == 1
    combined = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.iterdir())
    assert "C:\\projects\\major_cases" not in combined
    assert '"raw_private_cases_ingested": true' not in combined
