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
ledger = importlib.import_module("public_osint_rejection_ledger")


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_rejected_rows_are_design_reference_only():
    rows = ledger.rejected_rows(survey.matrix_rows())
    by_id = {row["tool_id"]: row for row in rows}

    assert set(by_id) == {"metagoofil", "pagodo", "photon", "theharvester"}
    for row in rows:
        assert row["operational_status"] == "rejected_design_reference_only"
        assert row["provider_registry_allowed"] is False
        assert row["adapters_allowed"] is False
        assert row["network_execution_allowed"] is False
        assert row["private_case_ingestion_allowed"] is False
        assert row["source_matrix_decision"] == "reject_operational_use_inspiration_only"
        assert row["source_matrix_registries"] == []
        assert row["privacy"]["raw_private_cases_ingested"] is False
        assert row["privacy"]["people_email_or_contact_harvesting_allowed"] is False
        assert row["privacy"]["subdomain_or_credential_harvesting_allowed"] is False
        assert row["privacy"]["stealth_evasion_or_proxy_rotation_allowed"] is False

    assert "people_email_domain_reconnaissance" in by_id["theharvester"]["blocked_capabilities"]
    assert "metadata_strip_requirements" in by_id["metagoofil"]["allowed_design_lessons"]


def test_pipeline_writes_rejection_ledger_without_private_flags(tmp_path):
    survey.run_pipeline(tmp_path)

    summary = ledger.run_pipeline(tmp_path)

    assert summary["rejected_operational_tools"] == 4
    assert summary["privacy"]["remote_private_queries_allowed"] is False
    assert summary["privacy"]["stealth_evasion_or_proxy_rotation_allowed"] is False
    rows = _jsonl(tmp_path / "rejected_operational_tools.jsonl")
    assert len(rows) == 4
    assert (tmp_path / "osint_rejection_summary.json").exists()

    combined = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.iterdir())
    assert "C:\\projects\\major_cases" not in combined
    assert '"raw_private_cases_ingested": true' not in combined
    assert '"people_email_or_contact_harvesting_allowed": true' not in combined
    assert '"stealth_evasion_or_proxy_rotation_allowed": true' not in combined
