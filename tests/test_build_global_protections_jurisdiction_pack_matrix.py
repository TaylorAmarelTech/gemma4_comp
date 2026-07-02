"""Tests for the global protections jurisdiction-pack matrix."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


builder = _load(
    "build_global_protections_jurisdiction_pack_matrix",
    _ROOT / "scripts" / "build_global_protections_jurisdiction_pack_matrix.py",
)


def test_jurisdiction_pack_matrix_builds_pilot_pack_cells():
    doc = builder.build_jurisdiction_pack_matrix()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["safe_for_pack_planning"] is True
    assert summary["jurisdiction_scope_count"] == 8
    assert summary["jurisdiction_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert summary["queued_jurisdiction_scope_count"] == 5
    assert summary["queued_jurisdiction_scope_ids"] == [
        "kh_domestic_supply_chain",
        "et_origin_domestic_work",
        "ug_origin_agriculture",
        "ng_origin_credit_migration",
        "co_ve_migrant_worker_housing",
    ]
    assert summary["domain_lens_count"] == 3
    assert summary["domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert summary["pack_cell_count"] == 24
    assert summary["source_object_slot_count"] == 120
    assert summary["not_started_source_object_slots"] == 120
    assert summary["language_review_required_cells"] == 24
    assert summary["scope_resolution_required_cells"] == 3
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_jurisdiction_pack_matrix_links_known_project_families_and_patterns():
    doc = builder.build_jurisdiction_pack_matrix()

    families = {scope["jurisdiction_family"] for scope in doc["pilot_jurisdiction_scopes"]}
    lenses = {lens["id"] for lens in doc["domain_lenses"]}

    assert "South Asia origin states" in families
    assert "Southeast Asia origin states" in families
    assert "East Africa origin and destination states" in families
    assert "West Africa origin and destination states" in families
    assert "Gulf and other destination corridors only after concrete forum scope" in families
    assert lenses == {
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    }
    assert all(scope["ready_for_pack_cell_generation"] is False for scope in doc["queued_jurisdiction_scopes"])
    assert all(scope["ready_for_comparable_scoring"] is False for scope in doc["queued_jurisdiction_scopes"])


def test_jurisdiction_pack_matrix_slots_are_source_gated_and_blank():
    doc = builder.build_jurisdiction_pack_matrix()
    slots = [
        slot
        for cell in doc["pack_cells"]
        for slot in cell["source_object_slots"]
    ]

    assert slots
    assert all(slot["status"] == "not_started" for slot in slots)
    assert all(slot["source_coverage_status"] == "source_gap" for slot in slots)
    assert all(slot["accepted_source_object_id"] == "" for slot in slots)
    assert all(slot["requires_dated_source_object"] is True for slot in slots)
    assert all(slot["requires_archive_status"] is True for slot in slots)
    assert all(slot["requires_source_path_review"] is True for slot in slots)
    assert all(slot["requires_privacy_review"] is True for slot in slots)
    assert all(slot["requires_expert_review"] is True for slot in slots)


def test_jurisdiction_pack_matrix_is_privacy_safe_and_non_scoring():
    doc = builder.build_jurisdiction_pack_matrix()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert all(cell["ready_for_comparable_scoring"] is False for cell in doc["pack_cells"])


def test_jurisdiction_pack_matrix_rejects_unknown_domain_lens():
    config = json.loads(builder.CONFIG.read_text(encoding="utf-8"))
    config["domain_lenses"][0]["id"] = "unknown_domain_lens"

    doc = builder.build_jurisdiction_pack_matrix(config=config)

    assert doc["summary"]["consistency_ok"] is False
    assert "domain_lenses_known_to_project" in [check["id"] for check in doc["checks"] if not check["ok"]]


def test_jurisdiction_pack_matrix_markdown_lists_pack_cells_and_policy():
    doc = builder.build_jurisdiction_pack_matrix()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Jurisdiction-Pack Matrix" in rendered
    assert "GPJPM-001" in rendered
    assert "cross_border_worker_protections" in rendered
    assert "Source-object slots" in rendered
    assert "Jurisdiction scope IDs" in rendered
    assert "Queued jurisdiction scope IDs" in rendered
    assert "Domain lens IDs" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_jurisdiction_pack_matrix_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "jurisdiction_pack_matrix.json"
    md_out = tmp_path / "jurisdiction_pack_matrix.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "24 pack cells" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["pack_cell_count"] == 24
    assert doc["summary"]["queued_jurisdiction_scope_count"] == 5
    assert md_out.exists()
    assert "# Global Protections Jurisdiction-Pack Matrix" in md_out.read_text(encoding="utf-8")
