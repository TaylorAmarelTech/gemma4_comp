"""Tests for scripts/validate_training_provenance.py -- one-shot Phase 3 provenance gate."""
from __future__ import annotations

import hashlib
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


vtp = _load("validate_training_provenance", _ROOT / "scripts" / "validate_training_provenance.py")
fr = _load("finetune_registry_for_provenance_tests", _ROOT / "scripts" / "finetune_registry.py")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _fingerprint(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _valid_sft() -> list[dict]:
    return [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]


def _valid_dpo() -> list[dict]:
    return [{"prompt": "p", "chosen": "grounded answer", "rejected": "weak answer"}]


def _write_quality_audit(path: Path, *, clean: bool = False, dense: int = 9) -> None:
    path.write_text(json.dumps({
        "clean": clean,
        "risk_flags": [] if clean else ["9 dense single-corridor typologies"],
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "n_dense_single_corridor": dense,
            "corridor_expansion_queue_count": dense,
            "corridor_expansion_task_count": dense * 5,
            "corridor_expansion_queue_privacy_scan": {"ok": True},
            "corridor_expansion_tasks_privacy_scan": {"ok": True},
        },
        "citation_relevance": {
            "n_incoherent": 0,
            "repair_queue_count": 0,
            "repair_queue_privacy_scan": {"ok": True},
        },
        "fragile_fact_assertions": {"with_phone_like": 0},
    }), encoding="utf-8")


def _write_corridor_plan(
    plan: Path,
    manifest: Path,
    audit: Path,
    *,
    planned: int = 5,
    safe: bool = True,
    source_sha: str | None = None,
    raw_plan_field: bool = False,
) -> None:
    entries = []
    for idx in range(planned):
        entry = {
            "task_id": f"corridor-expansion-labor-trafficking-{idx}",
            "category": "labor_trafficking",
            "target_corridor": "Bangladesh->Malaysia",
            "recommended_rows": 3,
            "source_policy": "synthetic_or_public_only",
            "scenario_constraints": ["synthetic_or_public_only", "no_names", "no_contacts"],
            "acceptance_checks": ["metadata_only", "privacy_scan_ok"],
            "curation_status": "todo",
            "review_required": True,
        }
        if raw_plan_field and idx == 0:
            entry["prompt"] = "raw worker@example.com narrative must not be copied"
        entries.append(entry)
    batches = [{
        "batch_id": "corridor-expansion-labor-trafficking",
        "category": "labor_trafficking",
        "task_count": planned,
        "recommended_rows": planned * 3,
        "target_corridors": ["Bangladesh->Malaysia"],
        "task_ids": [entry["task_id"] for entry in entries],
        "curation_status": "todo",
    }]
    payload = {
        "source_audit_path": "external",
        "source_audit_sha256": source_sha or hashlib.sha256(audit.read_bytes()).hexdigest(),
        "queue_count": 1,
        "source_task_count": planned,
        "planned_task_count": planned,
        "batch_count": len(batches),
        "recommended_rows": planned * 3,
        "by_category": {"labor_trafficking": planned},
        "by_target_corridor": {"Bangladesh->Malaysia": planned},
        "skipped": {},
        "metadata_only": True,
        "source_privacy_ok": True,
        "privacy_scan": {"ok": safe and not raw_plan_field},
        "plan_manifest_issues": [] if safe else ["source issue redacted"],
        "safe_for_curation": safe,
        "actionable_for_curation": bool(entries),
        "output_path": "external",
        "manifest_path": "external",
    }
    doc = {"plan": entries, "batches": batches, "manifest": payload}
    plan.write_text(json.dumps(doc), encoding="utf-8")
    manifest.write_text(json.dumps(payload), encoding="utf-8")


def _append_record(registry: Path, *, model_id: str, sft: Path, dpo: Path, artifacts: dict | None = None) -> None:
    test_root = registry.parent
    fr._ROOT = test_root
    vtp._ROOT = test_root
    registry_module = sys.modules.get("finetune_registry")
    if registry_module is not None:
        registry_module._ROOT = test_root
    # Other tests can reload finetune_registry under the canonical module name
    # after validate_training_provenance has imported function objects from it.
    # Update those imported function globals directly so fixture paths remain
    # rooted in tmp_path regardless of pytest collection order.
    for func in (vtp.verify_record_artifacts, vtp.load_registry, vtp.latest_by_id):
        func.__globals__["_ROOT"] = test_root
    payload = artifacts if artifacts is not None else {
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
        },
    }
    fr.append(fr.make_record(
        model_id=model_id,
        base_model="google/gemma-4-e4b-it",
        status="planned",
        created_utc="2026-06-28T00:00:00+00:00",
        artifacts=payload,
    ), registry)


def test_validate_training_provenance_passes_for_matching_record(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is True
    assert report["registry"]["matched"] == 2
    assert report["trainer"]["ok"] is True
    assert report["model_card"]["ok"] is True


def test_validate_training_provenance_verifies_quality_audit_summary(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=True, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is True
    assert report["quality_audit"]["ok"] is True
    assert report["quality_audit"]["summary"]["corridor_expansion_queue_count"] == 9
    assert report["quality_audit"]["summary"]["corridor_expansion_task_count"] == 45


def test_validate_training_provenance_blocks_matching_dirty_quality_audit(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["quality_audit"]["ok"] is False
    assert report["quality_audit"]["issue"] == "quality_audit is not clean"
    assert "quality audit: quality_audit is not clean" in report["issues"]


def test_validate_training_provenance_verifies_corridor_expansion_plan(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    plan = tmp_path / "corridor_expansion_plan.json"
    manifest = tmp_path / "corridor_expansion_plan_manifest.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=True, dense=1)
    _write_corridor_plan(plan, manifest, audit, planned=5)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "corridor_expansion_plan_path": str(plan),
        "corridor_expansion_plan_manifest": str(manifest),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
            "corridor_expansion_plan": _fingerprint(plan),
            "corridor_expansion_plan_manifest": _fingerprint(manifest),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is True
    assert report["corridor_expansion_plan"]["ok"] is True
    assert report["corridor_expansion_plan"]["summary"] == {
        "planned_task_count": 5,
        "batch_count": 1,
        "recommended_rows": 15,
        "safe_for_curation": True,
        "actionable_for_curation": True,
        "privacy_ok": True,
    }


def test_validate_training_provenance_fails_when_corridor_plan_manifest_missing(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    plan = tmp_path / "corridor_expansion_plan.json"
    manifest = tmp_path / "corridor_expansion_plan_manifest.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=1)
    _write_corridor_plan(plan, manifest, audit, planned=5)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "corridor_expansion_plan_path": str(plan),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
            "corridor_expansion_plan": _fingerprint(plan),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["corridor_expansion_plan"]["issue"] == "corridor_expansion_plan_manifest missing"
    assert "corridor expansion plan: corridor_expansion_plan_manifest missing" in report["issues"]


def test_validate_training_provenance_fails_when_corridor_plan_unsafe_without_copying_values(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    plan = tmp_path / "corridor_expansion_plan.json"
    manifest = tmp_path / "corridor_expansion_plan_manifest.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=1)
    _write_corridor_plan(plan, manifest, audit, planned=5, raw_plan_field=True)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "corridor_expansion_plan_path": str(plan),
        "corridor_expansion_plan_manifest": str(manifest),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
            "corridor_expansion_plan": _fingerprint(plan),
            "corridor_expansion_plan_manifest": _fingerprint(manifest),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert "corridor_expansion_plan_privacy_scan_not_ok" in report["corridor_expansion_plan"]["manifest_issues"]
    assert "corridor_expansion_plan_recorded_privacy_scan_not_ok" in report["corridor_expansion_plan"]["manifest_issues"]
    assert "raw worker@example.com narrative" not in report_json
    assert "worker@example.com" not in report_json


def test_validate_training_provenance_fails_when_corridor_plan_source_audit_hash_is_stale(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    plan = tmp_path / "corridor_expansion_plan.json"
    manifest = tmp_path / "corridor_expansion_plan_manifest.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=1)
    _write_corridor_plan(plan, manifest, audit, planned=5, source_sha="0" * 64)
    summary = vtp._quality_audit_summary_from_file(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "corridor_expansion_plan_path": str(plan),
        "corridor_expansion_plan_manifest": str(manifest),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
            "corridor_expansion_plan": _fingerprint(plan),
            "corridor_expansion_plan_manifest": _fingerprint(manifest),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert "corridor_expansion_plan_source_audit_sha_mismatch" in (
        report["corridor_expansion_plan"]["manifest_issues"]
    )


def test_validate_training_provenance_fails_when_quality_audit_summary_missing(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit)
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["quality_audit"]["issue"] == "quality_audit_summary missing or malformed"
    assert "quality audit: quality_audit_summary missing or malformed" in report["issues"]


def test_validate_training_provenance_fails_when_quality_audit_summary_stale(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    stale = vtp._quality_audit_summary_from_file(audit)
    stale["corridor_expansion_queue_count"] = 0
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": stale,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["quality_audit"]["issue"] == "quality_audit_summary does not match quality_audit artifact"
    assert report["quality_audit"]["mismatches"]["corridor_expansion_queue_count"] == {
        "expected": 9,
        "recorded": 0,
    }


def test_validate_training_provenance_redacts_risk_flag_mismatch_values(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    summary["risk_flags"] = ["worker@example.com asked us to call +1 555 0100"]
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["quality_audit"]["mismatches"]["risk_flags"] == {
        "expected_count": 0,
        "recorded_count": 1,
    }
    assert "worker@example.com" not in report_json
    assert "+1 555 0100" not in report_json


def test_validate_training_provenance_redacts_non_finite_quality_mismatches(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    summary["dense_single_corridor_typologies"] = float("nan")
    summary["corridor_expansion_queue_count"] = float("inf")
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["quality_audit"]["mismatches"]["dense_single_corridor_typologies"] == {
        "expected": 9,
        "recorded": "redacted",
    }
    assert report["quality_audit"]["mismatches"]["corridor_expansion_queue_count"] == {
        "expected": 9,
        "recorded": "redacted",
    }
    assert "NaN" not in report_json
    assert "Infinity" not in report_json


def test_validate_training_provenance_redacts_negative_quality_mismatches(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    summary["dense_single_corridor_typologies"] = -1
    summary["corridor_expansion_queue_count"] = -2.5
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["quality_audit"]["mismatches"]["dense_single_corridor_typologies"] == {
        "expected": 9,
        "recorded": "redacted",
    }
    assert report["quality_audit"]["mismatches"]["corridor_expansion_queue_count"] == {
        "expected": 9,
        "recorded": "redacted",
    }
    assert "-1" not in report_json
    assert "-2.5" not in report_json


def test_validate_training_provenance_fails_when_quality_audit_summary_contains_raw_queue(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    summary["corridor_expansion_queue"] = [{"prompt": "must not be recorded"}]
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["quality_audit"]["issue"] == "quality_audit_summary contains non-metadata keys"
    assert report["quality_audit"]["extra_keys"] == ["additional_field_1"]
    assert "must not be recorded" not in json.dumps(report)


def test_validate_training_provenance_redacts_quality_audit_scalar_mismatch_values(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    audit = tmp_path / "quality_audit.json"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _write_quality_audit(audit, clean=False, dense=9)
    summary = vtp._quality_audit_summary_from_file(audit)
    summary["gold_phone_like"] = "worker@example.com"
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "quality_audit_path": str(audit),
        "quality_audit_summary": summary,
        "artifact_files": {
            "selected_sft": _fingerprint(sft),
            "selected_dpo": _fingerprint(dpo),
            "quality_audit": _fingerprint(audit),
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["quality_audit"]["mismatches"]["gold_phone_like"] == {
        "expected": 0,
        "recorded": "redacted",
    }
    assert "worker@example.com" not in report_json


def test_validate_training_provenance_fails_on_stale_fingerprint(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)
    _write_jsonl(sft, _valid_sft() + _valid_sft())

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert "registry artifact selected_sft: fingerprint_mismatch" in report["issues"]
    assert report["trainer"]["ok"] is True


def test_validate_training_provenance_redacts_registry_issue_details(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    case_file = tmp_path / "case-123456789.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    case_file.write_text("new content", encoding="utf-8")
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={
        "sft_path": str(sft),
        "dpo_path": str(dpo),
        "artifact_files": {
            "worker@example.com case notes": {
                "path": str(case_file),
                "sha256": "0" * 64,
                "bytes": 3,
            },
        },
    })

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["registry"]["issues"] == [
        {"artifact": "additional_artifact_1", "issue": "unverifiable_path"}
    ]
    assert "registry artifact additional_artifact_1: unverifiable_path" in report["issues"]
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert str(case_file) not in report_json


def test_validate_training_provenance_reports_sanitized_paths(tmp_path):
    sft = tmp_path / "worker@example.com-sft.jsonl"
    dpo = tmp_path / "case-123456789-dpo.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    report = vtp.validate_training_provenance(model_id="m", registry=reg, sft=sft, dpo=dpo)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["registry"]["issues"] == [
        {"artifact": "selected_sft", "issue": "unverifiable_path"},
        {"artifact": "selected_dpo", "issue": "unverifiable_path"},
    ]
    assert report["trainer"]["ok"] is True
    assert report["registry_path"] == "external"
    assert report["selected_training_files"] == {"sft": "external", "dpo": "external"}
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert str(tmp_path) not in report_json


def test_validate_training_provenance_redacts_unknown_trainer_issues(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": False,
            "sft_rows": 1,
            "sft_valid": 1,
            "dpo_rows": 1,
            "dpo_valid": 1,
            "issues": ["worker@example.com says call +1 555 0100 about case-123456789"],
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["trainer"]["issues"] == ["trainer issue redacted"]
    assert "trainer: trainer issue redacted" in report["issues"]
    assert "worker@example.com" not in report_json
    assert "+1 555 0100" not in report_json
    assert "case-123456789" not in report_json


def test_validate_training_provenance_collapses_trainer_manifest_issue_details(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": False,
            "sft_rows": 1,
            "sft_valid": 1,
            "dpo_rows": 1,
            "dpo_valid": 1,
            "issues": [r"SFT variant manifest missing: C:\cases\worker@example.com-manifest.json"],
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["trainer"]["issues"] == ["SFT variant manifest missing"]
    assert "trainer: SFT variant manifest missing" in report["issues"]
    assert "worker@example.com" not in report_json
    assert "C:\\cases" not in report_json


def test_validate_training_provenance_drops_unknown_trainer_payloads(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": False,
            "sft_rows": 1,
            "sft_valid": 1,
            "sft_malformed_rows": 2,
            "dpo_rows": 1,
            "dpo_valid": 1,
            "dpo_malformed_rows": 3,
            "issues": [],
            "sample_bad_rows": [{"prompt": "worker@example.com case-123456789"}],
            "sft_manifest": {
                "path": r"C:\cases\worker@example.com-sft_manifest.json",
                "variant": "reasoning_repaired",
                "safe_to_train": False,
                "source_repair_manifest_issues": ["case-123456789 leaked detail"],
                "source_repair_manifest": {
                    "path": r"C:\cases\worker@example.com-repair.json",
                    "repair_manifest_issues": ["call +1 555 0100"],
                    "raw_rows": [{"prompt": "nested worker@example.com should never appear"}],
                    "source_queue": {
                        "metadata_only": True,
                        "privacy_scan_ok": False,
                        "queue_manifest_issues": ["case-123456789 leaked queue detail"],
                        "queued": 1,
                        "target_links": ["statute", "worker@example.com"],
                        "raw_prompt": "worker@example.com queue prompt",
                    },
                },
                "raw_rows": [{"prompt": "worker@example.com should never appear"}],
            },
            "dpo_manifest": {
                "path": r"C:\cases\worker@example.com-dpo_manifest.json",
                "variant": "base_plus_contract",
                "source_manifest_issues": ["case-123456789 source issue"],
                "by_ablated_link": {"action": 1, "worker@example.com": 99},
                "source_manifests": {
                    "base_dpo": {
                        "path": r"C:\cases\worker@example.com-organize.json",
                        "dpo_train": 1,
                        "raw_rows": [{"prompt": "base worker@example.com row"}],
                    },
                    "contract_dpo": {
                        "path": r"C:\cases\worker@example.com-contract.json",
                        "pairs": 1,
                        "by_ablated_link": {"statute": 1, "case-123456789": 1},
                        "pair_integrity_issues": ["call +1 555 0100"],
                        "raw_rows": [{"prompt": "contract worker@example.com row"}],
                    },
                },
            },
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["trainer"]["issues"] == ["trainer issue redacted"]
    assert report["trainer"]["sft_malformed_rows"] == 2
    assert report["trainer"]["dpo_malformed_rows"] == 3
    assert report["trainer"]["sft_manifest"]["path"] == "external"
    assert report["trainer"]["sft_manifest"]["source_repair_manifest_issues"] == ["manifest issue redacted"]
    assert report["trainer"]["sft_manifest"]["source_repair_manifest"]["repair_manifest_issues"] == [
        "manifest issue redacted"
    ]
    assert report["trainer"]["sft_manifest"]["source_repair_manifest"]["source_queue"]["target_links"] == [
        "statute"
    ]
    assert report["trainer"]["sft_manifest"]["source_repair_manifest"]["source_queue"]["queue_manifest_issues"] == [
        "manifest issue redacted"
    ]
    assert report["trainer"]["dpo_manifest"]["by_ablated_link"] == {"action": 1}
    assert report["trainer"]["dpo_manifest"]["source_manifest_issues"] == ["manifest issue redacted"]
    assert report["trainer"]["dpo_manifest"]["source_manifests"]["contract_dpo"]["by_ablated_link"] == {
        "statute": 1
    }
    assert report["trainer"]["dpo_manifest"]["source_manifests"]["contract_dpo"]["pair_integrity_issues"] == [
        "manifest issue redacted"
    ]
    assert "sample_bad_rows" not in report["trainer"]
    assert "raw_rows" not in report["trainer"]["sft_manifest"]
    assert "raw_rows" not in report["trainer"]["sft_manifest"]["source_repair_manifest"]
    assert "raw_prompt" not in report["trainer"]["sft_manifest"]["source_repair_manifest"]["source_queue"]
    assert "raw_rows" not in report["trainer"]["dpo_manifest"]["source_manifests"]["base_dpo"]
    assert "raw_rows" not in report["trainer"]["dpo_manifest"]["source_manifests"]["contract_dpo"]
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "+1 555 0100" not in report_json


def test_validate_training_provenance_sanitizes_core_remedy_repair_metadata(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": True,
            "sft_rows": 1,
            "sft_valid": 1,
            "sft_variant_rows": 1,
            "sft_variant_names": ["reasoning_repaired"],
            "dpo_rows": 1,
            "dpo_valid": 1,
            "contract_dpo_rows": 0,
            "issues": [],
            "sft_manifest": {
                "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
                "variant": "reasoning_repaired",
                "safe_to_train": True,
                "output_rows": 1,
                "output_prompt_ids": 1,
                "one_row_per_base_prompt": True,
                "repaired_input_rows": 1,
                "replaced_rows": 1,
                "require_core_remedies": True,
                "by_added_core_remedy": {
                    "compensation_damages": 1,
                    "worker@example.com": 99,
                },
                "source_repair_manifest": {
                    "path": "reports/training/reasoning_repaired_sft_manifest.json",
                    "output_path": "reports/training/reasoning_repaired_sft.jsonl",
                    "repaired_rows": 1,
                    "safe_to_train": True,
                    "require_core_remedies": True,
                    "by_added_core_remedy": {
                        "non_punishment": 1,
                        "case-123456789": 99,
                    },
                    "repair_manifest_issues": [],
                    "source_queue": {
                        "metadata_only": True,
                        "privacy_scan_ok": True,
                        "safe_for_repair": True,
                        "actionable_for_repair": True,
                        "queue_manifest_issues": [],
                        "queued": 1,
                        "target_links": ["statute", "worker@example.com"],
                        "require_core_remedies": True,
                        "by_core_missing": {
                            "compensation_damages": 1,
                            "worker@example.com": 99,
                        },
                    },
                },
                "source_repair_manifest_issues": [],
            },
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)
    sft_manifest = report["trainer"]["sft_manifest"]
    repair = sft_manifest["source_repair_manifest"]

    assert report["ok"] is True
    assert sft_manifest["require_core_remedies"] is True
    assert sft_manifest["by_added_core_remedy"] == {"compensation_damages": 1}
    assert repair["require_core_remedies"] is True
    assert repair["by_added_core_remedy"] == {"non_punishment": 1}
    assert repair["source_queue"]["require_core_remedies"] is True
    assert repair["source_queue"]["by_core_missing"] == {"compensation_damages": 1}
    assert repair["source_queue"]["target_links"] == ["statute"]
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json


def test_validate_training_provenance_sanitizes_trainer_summary_scalars(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": False,
            "sft_rows": "worker@example.com",
            "sft_valid": r"C:\Users\worker@example.com\case-123456789",
            "sft_malformed_rows": True,
            "sft_variant_rows": 2,
            "sft_variant_names": [
                "reasoning_repaired",
                "worker@example.com",
                "case-123456789",
                r"C:\Users\Taylor\case-notes",
                "../case-notes",
            ],
            "dpo_rows": -1,
            "dpo_valid": 1,
            "dpo_malformed_rows": None,
            "contract_dpo_rows": "case-123456789",
            "issues": ["worker@example.com says call +1 555 0100 about case-123456789"],
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["trainer"]["ok"] is False
    assert report["trainer"]["sft_rows"] == "redacted"
    assert report["trainer"]["sft_valid"] == "redacted"
    assert report["trainer"]["sft_malformed_rows"] == "redacted"
    assert report["trainer"]["sft_variant_rows"] == 2
    assert report["trainer"]["sft_variant_names"] == ["reasoning_repaired"]
    assert report["trainer"]["dpo_rows"] == "redacted"
    assert report["trainer"]["dpo_valid"] == 1
    assert report["trainer"]["dpo_malformed_rows"] is None
    assert report["trainer"]["contract_dpo_rows"] == "redacted"
    assert report["trainer"]["issues"] == ["trainer issue redacted"]
    assert "worker@example.com" not in report_json
    assert "+1 555 0100" not in report_json
    assert "case-123456789" not in report_json
    assert "C:\\Users" not in report_json
    assert "case-notes" not in report_json


def test_validate_training_provenance_sanitizes_trainer_manifest_scalars(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    def fake_validate_training_data(*args, **kwargs):
        return {
            "ok": False,
            "sft_rows": 1,
            "sft_valid": 1,
            "dpo_rows": 1,
            "dpo_valid": 1,
            "issues": [],
            "sft_manifest": {
                "path": r"C:\cases\worker@example.com-sft_manifest.json",
                "variant": "worker@example.com",
                "safe_to_train": "case-123456789",
                "output_rows": "worker@example.com",
                "output_prompt_ids": True,
                "one_row_per_base_prompt": "yes",
                "repaired_input_rows": 2,
                "replaced_rows": 2,
                "source_repair_manifest": {
                    "path": r"C:\cases\worker@example.com-repair.json",
                    "output_path": "/home/taylor/case-notes.jsonl",
                    "repaired_rows": "worker@example.com",
                    "safe_to_train": "case-123456789",
                    "repair_manifest_issues": [],
                    "source_queue": {
                        "metadata_only": "worker@example.com",
                        "privacy_scan_ok": "case-123456789",
                        "safe_for_repair": True,
                        "actionable_for_repair": False,
                        "queue_manifest_issues": [],
                        "queued": "worker@example.com",
                        "target_links": ["statute", "worker@example.com"],
                    },
                },
            },
            "dpo_manifest": {
                "path": r"C:\cases\worker@example.com-dpo_manifest.json",
                "variant": r"C:\Users\worker@example.com\case-123456789",
                "safe_to_train": "worker@example.com",
                "pairs": -1,
                "base_rows": 1,
                "contract_rows": "case-123456789",
                "duplicate_output_pair_rows": True,
                "min_steps": 10,
                "source_manifests": {
                    "base_dpo": {
                        "path": r"C:\cases\worker@example.com-base.json",
                        "base_path": "/tmp/case-notes.jsonl",
                        "dpo_train": "worker@example.com",
                        "dpo_heldout": 0,
                        "seed": "case-123456789",
                        "heldout_fraction": float("inf"),
                        "dedup_kept_pre_split": 3,
                    },
                    "contract_dpo": {
                        "path": r"C:\cases\worker@example.com-contract.json",
                        "output_path": "/Users/Taylor/case-notes.jsonl",
                        "pairs": 1.5,
                        "safe_to_train": "case-123456789",
                        "by_ablated_link": {"action": 1, "worker@example.com": 99},
                        "pair_integrity_issues": [],
                        "contract_manifest_issues": [],
                        "duplicate_output_pair_rows": "worker@example.com",
                    },
                },
            },
        }

    monkeypatch.setattr(vtp, "validate_training_data", fake_validate_training_data)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)
    report_json = json.dumps(report)
    sft_manifest = report["trainer"]["sft_manifest"]
    dpo_manifest = report["trainer"]["dpo_manifest"]

    assert sft_manifest["path"] == "external"
    assert sft_manifest["variant"] == "redacted"
    assert sft_manifest["safe_to_train"] == "redacted"
    assert sft_manifest["output_rows"] == "redacted"
    assert sft_manifest["output_prompt_ids"] == "redacted"
    assert sft_manifest["one_row_per_base_prompt"] == "redacted"
    assert sft_manifest["repaired_input_rows"] == 2
    assert sft_manifest["replaced_rows"] == 2
    repair = sft_manifest["source_repair_manifest"]
    assert repair["path"] == "external"
    assert repair["output_path"] == "redacted"
    assert repair["repaired_rows"] == "redacted"
    assert repair["safe_to_train"] == "redacted"
    assert repair["source_queue"]["metadata_only"] == "redacted"
    assert repair["source_queue"]["privacy_scan_ok"] == "redacted"
    assert repair["source_queue"]["safe_for_repair"] is True
    assert repair["source_queue"]["actionable_for_repair"] is False
    assert repair["source_queue"]["queued"] == "redacted"
    assert repair["source_queue"]["target_links"] == ["statute"]
    assert dpo_manifest["path"] == "external"
    assert dpo_manifest["variant"] == "redacted"
    assert dpo_manifest["safe_to_train"] == "redacted"
    assert dpo_manifest["pairs"] == "redacted"
    assert dpo_manifest["base_rows"] == 1
    assert dpo_manifest["contract_rows"] == "redacted"
    assert dpo_manifest["duplicate_output_pair_rows"] == "redacted"
    assert dpo_manifest["min_steps"] == 10
    base_source = dpo_manifest["source_manifests"]["base_dpo"]
    assert base_source["path"] == "external"
    assert base_source["base_path"] == "redacted"
    assert base_source["dpo_train"] == "redacted"
    assert base_source["dpo_heldout"] == 0
    assert base_source["seed"] == "redacted"
    assert base_source["heldout_fraction"] == "redacted"
    assert base_source["dedup_kept_pre_split"] == 3
    contract_source = dpo_manifest["source_manifests"]["contract_dpo"]
    assert contract_source["path"] == "external"
    assert contract_source["output_path"] == "redacted"
    assert contract_source["pairs"] == "redacted"
    assert contract_source["safe_to_train"] == "redacted"
    assert contract_source["by_ablated_link"] == {"action": 1}
    assert contract_source["duplicate_output_pair_rows"] == "redacted"
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "C:\\cases" not in report_json
    assert "/home/" not in report_json
    assert "/tmp/" not in report_json
    assert "/Users/" not in report_json
    assert "case-notes" not in report_json
    assert "Infinity" not in report_json


def test_validate_training_provenance_fails_for_legacy_record_without_fingerprints(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo, artifacts={"sft_path": str(sft), "dpo_path": str(dpo)})

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert "registry row has no structured artifact_files payload" in report["issues"]
    assert report["trainer"]["ok"] is True


def test_validate_training_provenance_fails_when_card_omits_fingerprint_section(tmp_path, monkeypatch):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)
    monkeypatch.setattr(vtp, "render_card", lambda record: "# Model card\n\nNo artifact table here.\n")

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert report["model_card"]["issue"] == "model card is missing artifact fingerprints section"
    assert "model card: model card is missing artifact fingerprints section" in report["issues"]


def test_validate_training_provenance_fails_on_invalid_training_rows(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, [{"messages": [{"role": "user", "content": "missing assistant"}]}])
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id="m", sft=sft, dpo=dpo)

    report = vtp.validate_training_provenance(model_id="m", registry=reg)

    assert report["ok"] is False
    assert any(issue.startswith("trainer: no valid SFT rows") for issue in report["issues"])
    assert report["registry"]["ok"] is True


def test_main_prints_json_and_returns_failure_for_missing_record(tmp_path, capsys):
    rc = vtp.main(["--registry", str(tmp_path / "missing.jsonl"), "--model-id", "m", "--json"])
    out = capsys.readouterr().out

    assert rc == 1
    assert json.loads(out)["issues"] == ["no registry record for m"]


def test_main_redacts_sensitive_missing_model_id(tmp_path, capsys):
    raw_model_id = r"worker@example.com\..\case-123456789"

    rc = vtp.main(["--registry", str(tmp_path / "missing.jsonl"), "--model-id", raw_model_id, "--json"])
    out = capsys.readouterr().out
    report = json.loads(out)

    assert rc == 1
    assert report["model_id"] == "redacted"
    assert report["issues"] == ["no registry record for redacted"]
    assert "worker@example.com" not in out
    assert "case-123456789" not in out


def test_validate_training_provenance_redacts_sensitive_registry_model_id(tmp_path):
    raw_model_id = r"worker@example.com\..\case-123456789"
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    _append_record(reg, model_id=raw_model_id, sft=sft, dpo=dpo)

    report = vtp.validate_training_provenance(model_id=raw_model_id, registry=reg)
    report_json = json.dumps(report)

    assert report["ok"] is True
    assert report["model_id"] == "redacted"
    assert report["registry"]["model_id"] == "redacted"
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json


def test_validate_training_provenance_fails_closed_for_malformed_artifacts_payload(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    fr.append({
        "model_id": "m",
        "base_model": "google/gemma-4-e4b-it",
        "status": "planned",
        "created_utc": "2026-06-28T00:00:00+00:00",
        "data": {},
        "eval": {},
        "artifacts": ["worker@example.com", r"C:\Users\Taylor\case-123456789.jsonl"],
    }, reg)

    report = vtp.validate_training_provenance(model_id="m", registry=reg, sft=sft, dpo=dpo)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["registry"]["issues"] == [{"artifact": "additional_artifact_1", "issue": "malformed"}]
    assert "registry artifact additional_artifact_1: malformed" in report["issues"]
    assert report["quality_audit"] == {"ok": True, "available": False}
    assert report["trainer"]["ok"] is True
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "C:\\Users" not in report_json


def test_validate_training_provenance_fails_closed_for_malformed_artifact_files_payload(tmp_path):
    sft = tmp_path / "sft_train.jsonl"
    dpo = tmp_path / "dpo_train.jsonl"
    reg = tmp_path / "registry.jsonl"
    _write_jsonl(sft, _valid_sft())
    _write_jsonl(dpo, _valid_dpo())
    fr.append({
        "model_id": "m",
        "base_model": "google/gemma-4-e4b-it",
        "status": "planned",
        "created_utc": "2026-06-28T00:00:00+00:00",
        "data": {},
        "eval": {},
        "artifacts": {
            "artifact_files": ["worker@example.com", r"C:\Users\Taylor\case-123456789.jsonl"],
        },
    }, reg)

    report = vtp.validate_training_provenance(model_id="m", registry=reg, sft=sft, dpo=dpo)
    report_json = json.dumps(report)

    assert report["ok"] is False
    assert report["registry"]["issues"] == [{"artifact": "additional_artifact_1", "issue": "malformed"}]
    assert "registry artifact additional_artifact_1: malformed" in report["issues"]
    assert report["quality_audit"] == {"ok": True, "available": False}
    assert report["trainer"]["ok"] is True
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "C:\\Users" not in report_json
