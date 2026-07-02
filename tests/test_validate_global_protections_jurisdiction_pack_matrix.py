"""Tests for the global protections jurisdiction-pack matrix validator."""
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
validator = _load(
    "validate_global_protections_jurisdiction_pack_matrix",
    _ROOT / "scripts" / "validate_global_protections_jurisdiction_pack_matrix.py",
)


def _matrix_doc() -> dict:
    return builder.build_jurisdiction_pack_matrix()


def test_validator_accepts_current_jurisdiction_pack_matrix():
    report = validator.validate_jurisdiction_pack_matrix(_matrix_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["jurisdiction_scope_count"] == 8
    assert report["summary"]["jurisdiction_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert report["summary"]["queued_jurisdiction_scope_count"] == 5
    assert report["summary"]["queued_jurisdiction_scope_ids"] == [
        "kh_domestic_supply_chain",
        "et_origin_domestic_work",
        "ug_origin_agriculture",
        "ng_origin_credit_migration",
        "co_ve_migrant_worker_housing",
    ]
    assert report["summary"]["domain_lens_count"] == 3
    assert report["summary"]["domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert report["summary"]["pack_cell_count"] == 24
    assert report["summary"]["source_object_slot_count"] == 120
    assert report["summary"]["not_started_source_object_slots"] == 120
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_prompt_and_scoring_drift_without_current_chain():
    doc = _matrix_doc()
    doc["pack_cells"][0]["ready_for_prompt_generation"] = True
    doc["pack_cells"][0]["ready_for_comparable_scoring"] = True
    doc["summary"]["ready_for_prompt_generation"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "matrix_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_slot_promotion_without_current_chain():
    doc = _matrix_doc()
    slot = doc["pack_cells"][0]["source_object_slots"][0]
    slot["status"] = "accepted"
    slot["accepted_source_object_id"] = "SOURCE-1"
    slot["source_coverage_status"] = "covered"

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_slot_integrity" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_matrix" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_cross_product_cell_without_current_chain():
    doc = _matrix_doc()
    doc["pack_cells"].pop()

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_matrix" in report["summary"]["failed_check_ids"]
    assert "cross_product_cells_unique_and_complete" in report["summary"]["failed_check_ids"]


def test_validator_rejects_summary_scope_and_lens_id_drift_without_current_chain():
    doc = _matrix_doc()
    doc["summary"]["jurisdiction_scope_ids"] = ["stale_scope"]
    doc["summary"]["domain_lens_ids"] = ["stale_lens"]

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_matrix" in report["summary"]["failed_check_ids"]
    assert "matrix_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_url_dump_without_current_chain():
    doc = _matrix_doc()
    doc["pack_cells"][0]["next_step"] = "Review candidate_url at https://example.invalid/source"

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "matrix_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unknown_slot_shape_without_current_chain():
    doc = _matrix_doc()
    slot = doc["pack_cells"][0]["source_object_slots"][0]
    slot["source_url"] = "redacted"
    slot.pop("requires_expert_review")

    report = validator.validate_jurisdiction_pack_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_slot_integrity" in report["summary"]["failed_check_ids"]
    assert "matrix_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _matrix_doc()
    doc["pack_cells"][0]["ready_for_prompt_generation"] = True
    report = validator.validate_jurisdiction_pack_matrix(doc)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Jurisdiction-Pack Matrix Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Jurisdiction scope IDs" in rendered
    assert "Queued jurisdiction scope IDs" in rendered
    assert "Domain lens IDs" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    matrix_path = tmp_path / "global_protections_jurisdiction_pack_matrix.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    matrix_path.write_text(json.dumps(_matrix_doc()), encoding="utf-8")

    assert validator.main(["--matrix", str(matrix_path), "--validate"]) == 0
    assert validator.main([
        "--matrix",
        str(matrix_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_matrix(tmp_path):
    doc = _matrix_doc()
    doc["pack_cells"][0]["ready_for_comparable_scoring"] = True
    matrix_path = tmp_path / "global_protections_jurisdiction_pack_matrix.json"
    out = tmp_path / "validation.json"
    matrix_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main(["--matrix", str(matrix_path), "--out", str(out), "--no-current-chain"]) == 1
    assert out.exists()
