"""Tests for scripts/build_corridor_expansion_plan.py -- privacy-safe corridor curation handoff."""
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


cep = _load("build_corridor_expansion_plan", _ROOT / "scripts" / "build_corridor_expansion_plan.py")


def _task(category: str, corridor: str) -> dict:
    origin, _, destination = corridor.partition("->")
    return {
        "task_id": f"corridor-expansion-{category.replace('_', '-')}-{corridor.lower().replace('->', '-')}",
        "category": category,
        "target_corridor": corridor,
        "origin": origin,
        "destination": destination,
        "coverage_gap": "generic_corridor_only",
        "suggestion_source": "global_prompt_metadata",
        "suggested_min_synthetic_rows": 3,
        "required_metadata_fields": ["id", "category", "corridor", "source", "privacy_review"],
        "scenario_constraints": [
            "synthetic_or_public_only",
            "no_names",
            "no_contacts",
            "include_ilo_indicator",
        ],
        "acceptance_checks": [
            "metadata_only",
            "privacy_scan_ok",
            "corridor_matches_target",
            "typology_matches_category",
        ],
        "curation_hint": "safe metadata-only hint",
    }


def _audit(*, task_privacy_ok: bool = True) -> dict:
    tasks = [
        _task("labor_trafficking", "Bangladesh->Malaysia"),
        _task("labor_trafficking", "India->Saudi Arabia"),
    ]
    return {
        "jurisdiction_corridor_diversity": {
            "corridor_expansion_queue": [
                {
                    "category": "labor_trafficking",
                    "train_rows": 2304,
                    "coverage_gap": "generic_corridor_only",
                }
            ],
            "corridor_expansion_queue_count": 1,
            "corridor_expansion_queue_metadata_only": True,
            "corridor_expansion_queue_privacy_scan": {"ok": True},
            "corridor_expansion_tasks": tasks,
            "corridor_expansion_task_count": len(tasks),
            "corridor_expansion_tasks_metadata_only": True,
            "corridor_expansion_tasks_privacy_scan": {"ok": task_privacy_ok},
        }
    }


def test_build_plan_groups_tasks_and_keeps_metadata_only(tmp_path):
    audit_path = tmp_path / "quality_audit.json"
    audit_path.write_text(json.dumps(_audit()), encoding="utf-8")

    doc = cep.build_plan(json.loads(audit_path.read_text(encoding="utf-8")), audit_path=audit_path)
    manifest = doc["manifest"]

    assert manifest["safe_for_curation"] is True
    assert manifest["actionable_for_curation"] is True
    assert manifest["source_privacy_ok"] is True
    assert manifest["planned_task_count"] == 2
    assert manifest["batch_count"] == 1
    assert manifest["recommended_rows"] == 6
    assert manifest["by_category"] == {"labor_trafficking": 2}
    assert manifest["by_target_corridor"] == {
        "Bangladesh->Malaysia": 1,
        "India->Saudi Arabia": 1,
    }
    assert manifest["privacy_scan"]["ok"] is True
    batch = doc["batches"][0]
    assert batch["batch_id"] == "corridor-expansion-labor-trafficking"
    assert batch["observed_train_rows"] == 2304
    assert batch["task_count"] == 2
    first = doc["plan"][0]
    assert first["source_policy"] == "synthetic_or_public_only"
    assert first["curation_status"] == "todo"
    assert first["review_required"] is True
    assert not {"messages", "prompt", "chosen", "rejected", "assistant", "text"} & set(first)
    assert "safe metadata-only hint" not in json.dumps(doc)


def test_build_plan_fails_closed_when_source_privacy_scan_fails():
    doc = cep.build_plan(_audit(task_privacy_ok=False))
    manifest = doc["manifest"]

    assert manifest["safe_for_curation"] is False
    assert "corridor_expansion_source_privacy_not_ok" in manifest["plan_manifest_issues"]
    assert manifest["actionable_for_curation"] is True


def test_build_plan_flags_missing_required_task_fields_without_copying_values():
    audit = _audit()
    task = audit["jurisdiction_corridor_diversity"]["corridor_expansion_tasks"][0]
    del task["target_corridor"]
    audit["jurisdiction_corridor_diversity"]["corridor_expansion_task_count"] = 1

    doc = cep.build_plan(audit)
    manifest_json = json.dumps(doc["manifest"])

    assert doc["manifest"]["safe_for_curation"] is False
    assert "corridor_expansion_task_required_fields_missing" in doc["manifest"]["plan_manifest_issues"]
    assert "safe metadata-only hint" not in manifest_json


def test_privacy_scan_flags_forbidden_fields_and_pii_without_copying_values():
    scan = cep._privacy_scan({
        "plan": [
            {
                "task_id": "safe-task",
                "category": "labor_trafficking",
                "target_corridor": "Bangladesh->Malaysia",
                "prompt": "raw prompt must not be copied",
                "review_note": "email worker@example.com or call +1 555 0100",
            }
        ],
        "batches": [{"batch_id": "b", "category": "labor_trafficking", "raw": "private narrative"}],
    })
    encoded = json.dumps(scan)

    assert scan["ok"] is False
    assert "$.plan[0].prompt" in scan["forbidden_field_paths"]
    assert "$.plan[0].review_note" in scan["email_like_paths"]
    assert "$.plan[0].review_note" in scan["phone_like_paths"]
    assert "$.plan[0].review_note" in scan["unexpected_plan_field_paths"]
    assert "$.batches[0].raw" in scan["unexpected_batch_field_paths"]
    assert "raw prompt must not be copied" not in encoded
    assert "private narrative" not in encoded


def test_privacy_scan_flags_8_digit_case_like_values_without_copying_them():
    scan = cep._privacy_scan({
        "plan": [
            {
                "task_id": "safe-task",
                "category": "labor_trafficking",
                "target_corridor": "Bangladesh->Malaysia",
                "scenario_constraints": ["remove copied case_12345678 before curation"],
            }
        ],
        "batches": [],
    })
    encoded = json.dumps(scan)

    assert scan["ok"] is False
    assert scan["counts"]["long_digit"] == 1
    assert scan["long_digit_paths"] == ["$.plan[0].scenario_constraints[0]"]
    assert "case_12345678" not in encoded


def test_main_writes_plan_and_side_manifest(tmp_path):
    audit = tmp_path / "quality_audit.json"
    out = tmp_path / "corridor_expansion_plan.json"
    manifest = tmp_path / "corridor_expansion_plan_manifest.json"
    audit.write_text(json.dumps(_audit()), encoding="utf-8")

    rc = cep.main(["--audit", str(audit), "--out", str(out)])

    assert rc == 0
    assert out.exists()
    assert manifest.exists()
    plan_doc = json.loads(out.read_text(encoding="utf-8"))
    side_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert plan_doc["manifest"]["safe_for_curation"] is True
    assert side_manifest["safe_for_curation"] is True
    assert side_manifest["planned_task_count"] == 2
    assert side_manifest["source_audit_sha256"]


def test_main_validate_refuses_unsafe_source_without_writing(tmp_path):
    audit = tmp_path / "quality_audit.json"
    out = tmp_path / "corridor_expansion_plan.json"
    audit.write_text(json.dumps(_audit(task_privacy_ok=False)), encoding="utf-8")

    rc = cep.main(["--audit", str(audit), "--out", str(out), "--validate"])

    assert rc == 1
    assert not out.exists()
