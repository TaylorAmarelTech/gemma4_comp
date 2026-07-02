"""Tests for scripts/training_engine.py -- the Phase-3 data->train->eval->register orchestrator."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


te = _load("training_engine", _ROOT / "scripts" / "training_engine.py")


def _artifacts_from_register(step):
    return json.loads(step["cmd"][step["cmd"].index("--artifacts") + 1])


def test_plan_order_is_the_pipeline_dag():
    names = [s["name"] for s in te.plan(model_id="m", base="b", with_gpu=False)]
    assert names == [
        "distill",
        "organize",
        "reason",
        "contract",
        "dpo_mix",
        "gaps",
        "repair",
        "variant",
        "audit",
        "corridor_plan",
        "train",
        "evaluate",
        "register",
    ]


def test_plan_gpu_gating_offline():
    steps = {s["name"]: s for s in te.plan(model_id="m", base="b", with_gpu=False)}
    # offline host: data-prep + audit + register run; GPU train/evaluate are skipped (will_run False, reason)
    assert steps["distill"]["will_run"] and steps["organize"]["will_run"] and steps["reason"]["will_run"]
    assert steps["contract"]["will_run"] and steps["dpo_mix"]["will_run"]
    assert steps["gaps"]["will_run"] and steps["repair"]["will_run"]
    assert steps["variant"]["will_run"]
    assert steps["audit"]["will_run"] and steps["corridor_plan"]["will_run"] and steps["register"]["will_run"]
    assert not steps["train"]["will_run"] and not steps["evaluate"]["will_run"]
    assert steps["train"]["skip_reason"] and "GPU" in steps["train"]["skip_reason"]


def test_plan_gpu_gating_with_gpu():
    steps = {s["name"]: s for s in te.plan(model_id="m", base="b", with_gpu=True)}
    assert all(steps[n]["will_run"] for n in ("distill", "train", "evaluate", "register"))


def test_train_step_uses_organized_train_splits():
    train = next(s for s in te.plan(model_id="m", base="b", with_gpu=True) if s["name"] == "train")
    assert "--sft" in train["cmd"] and train["cmd"][train["cmd"].index("--sft") + 1].endswith("sft_train.jsonl")
    assert "--dpo" in train["cmd"] and train["cmd"][train["cmd"].index("--dpo") + 1].endswith("dpo_train.jsonl")


def test_train_step_can_select_reasoning_repaired_sft_variant():
    train = next(
        s for s in te.plan(model_id="m", base="b", with_gpu=True, sft_variant="reasoning_repaired")
        if s["name"] == "train"
    )
    sft_path = train["cmd"][train["cmd"].index("--sft") + 1]
    assert sft_path.endswith("sft_train_reasoning_repaired.jsonl")
    assert "--dpo" in train["cmd"] and train["cmd"][train["cmd"].index("--dpo") + 1].endswith("dpo_train.jsonl")


def test_train_step_can_select_core_remedy_reasoning_repaired_sft_variant():
    steps = te.plan(model_id="m", base="b", with_gpu=True, sft_variant="reasoning_repaired_core")
    by_name = {s["name"]: s for s in steps}

    assert "--require-core-remedies" in by_name["gaps"]["cmd"]
    assert by_name["gaps"]["cmd"][by_name["gaps"]["cmd"].index("--out") + 1].endswith(
        "reasoning_gap_queue_core.json"
    )
    assert "--require-core-remedies" in by_name["repair"]["cmd"]
    assert by_name["repair"]["cmd"][by_name["repair"]["cmd"].index("--queue") + 1].endswith(
        "reasoning_gap_queue_core.json"
    )
    assert by_name["repair"]["cmd"][by_name["repair"]["cmd"].index("--out") + 1].endswith(
        "reasoning_repaired_core_sft.jsonl"
    )
    assert by_name["variant"]["cmd"][by_name["variant"]["cmd"].index("--repaired") + 1].endswith(
        "reasoning_repaired_core_sft.jsonl"
    )
    assert by_name["variant"]["cmd"][by_name["variant"]["cmd"].index("--out") + 1].endswith(
        "sft_train_reasoning_repaired_core.jsonl"
    )
    assert by_name["train"]["cmd"][by_name["train"]["cmd"].index("--sft") + 1].endswith(
        "sft_train_reasoning_repaired_core.jsonl"
    )


def test_train_step_can_select_contract_dpo_variant():
    train = next(
        s for s in te.plan(model_id="m", base="b", with_gpu=True, dpo_variant="contract")
        if s["name"] == "train"
    )
    dpo_path = train["cmd"][train["cmd"].index("--dpo") + 1]
    assert dpo_path.endswith("contract_dpo.jsonl")
    assert "--sft" in train["cmd"] and train["cmd"][train["cmd"].index("--sft") + 1].endswith("sft_train.jsonl")


def test_train_step_can_select_mixed_dpo_variant():
    train = next(
        s for s in te.plan(model_id="m", base="b", with_gpu=True, dpo_variant="base_plus_contract")
        if s["name"] == "train"
    )
    dpo_path = train["cmd"][train["cmd"].index("--dpo") + 1]
    assert dpo_path.endswith("dpo_train_plus_contract.jsonl")
    assert "--sft" in train["cmd"] and train["cmd"][train["cmd"].index("--sft") + 1].endswith("sft_train.jsonl")


def test_register_status_tracks_gpu():
    def status(with_gpu):
        reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=with_gpu) if s["name"] == "register")
        return reg["cmd"][reg["cmd"].index("--status") + 1]
    assert status(False) == "planned"     # offline data-prep -> a planned run
    assert status(True) == "trained"      # GPU train ran -> a trained run


def test_register_artifacts_record_base_training_inputs():
    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False, sft_variant="base")
               if s["name"] == "register")
    artifacts = _artifacts_from_register(reg)
    assert artifacts["sft_variant"] == "base"
    assert artifacts["dpo_variant"] == "base"
    assert artifacts["sft_path"].endswith("sft_train.jsonl")
    assert artifacts["dpo_path"].endswith("dpo_train.jsonl")
    assert artifacts["contract_dpo_path"].endswith("contract_dpo.jsonl")
    assert artifacts["contract_dpo_manifest"].endswith("contract_dpo_manifest.json")
    assert artifacts["dpo_mix_path"].endswith("dpo_train_plus_contract.jsonl")
    assert artifacts["dpo_mix_manifest"].endswith("dpo_train_plus_contract_manifest.json")
    assert artifacts["quality_audit_path"].endswith("quality_audit.json")
    assert artifacts["corridor_expansion_plan_path"].endswith("corridor_expansion_plan.json")
    assert artifacts["corridor_expansion_plan_manifest"].endswith("corridor_expansion_plan_manifest.json")
    assert artifacts["sft_variant_manifest"] is None
    assert artifacts["dpo_variant_manifest"] is None


def test_register_artifacts_record_reasoning_repaired_manifest():
    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False, sft_variant="reasoning_repaired")
               if s["name"] == "register")
    artifacts = _artifacts_from_register(reg)
    assert artifacts["sft_variant"] == "reasoning_repaired"
    assert artifacts["dpo_variant"] == "base"
    assert artifacts["sft_path"].endswith("sft_train_reasoning_repaired.jsonl")
    assert artifacts["dpo_path"].endswith("dpo_train.jsonl")
    assert artifacts["contract_dpo_path"].endswith("contract_dpo.jsonl")
    assert artifacts["contract_dpo_manifest"].endswith("contract_dpo_manifest.json")
    assert artifacts["dpo_mix_path"].endswith("dpo_train_plus_contract.jsonl")
    assert artifacts["dpo_mix_manifest"].endswith("dpo_train_plus_contract_manifest.json")
    assert artifacts["sft_variant_manifest"].endswith("sft_train_reasoning_repaired_manifest.json")
    assert artifacts["dpo_variant_manifest"] is None


def test_register_artifacts_record_core_remedy_reasoning_repaired_manifest():
    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False, sft_variant="reasoning_repaired_core")
               if s["name"] == "register")
    artifacts = _artifacts_from_register(reg)
    assert artifacts["sft_variant"] == "reasoning_repaired_core"
    assert artifacts["reasoning_repair_mode"] == "core_remedies"
    assert artifacts["sft_path"].endswith("sft_train_reasoning_repaired_core.jsonl")
    assert artifacts["sft_variant_manifest"].endswith("sft_train_reasoning_repaired_core_manifest.json")
    assert artifacts["reasoning_gap_queue_path"].endswith("reasoning_gap_queue_core.json")
    assert artifacts["reasoning_repaired_rows_path"].endswith("reasoning_repaired_core_sft.jsonl")
    assert artifacts["artifact_files"]["reasoning_gap_queue"]["path"].endswith("reasoning_gap_queue_core.json")
    assert artifacts["artifact_files"]["reasoning_repaired_rows"]["path"].endswith(
        "reasoning_repaired_core_sft.jsonl"
    )
    assert artifacts["artifact_files"]["reasoning_repaired_rows_manifest"]["path"].endswith(
        "reasoning_repaired_core_sft_manifest.json"
    )


def test_register_artifacts_record_contract_dpo_selection():
    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False, dpo_variant="contract")
               if s["name"] == "register")
    artifacts = _artifacts_from_register(reg)
    assert artifacts["sft_variant"] == "base"
    assert artifacts["dpo_variant"] == "contract"
    assert artifacts["dpo_path"].endswith("contract_dpo.jsonl")
    assert artifacts["dpo_variant_manifest"].endswith("contract_dpo_manifest.json")


def test_register_artifacts_record_mixed_dpo_selection():
    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False, dpo_variant="base_plus_contract")
               if s["name"] == "register")
    artifacts = _artifacts_from_register(reg)
    assert artifacts["sft_variant"] == "base"
    assert artifacts["dpo_variant"] == "base_plus_contract"
    assert artifacts["dpo_path"].endswith("dpo_train_plus_contract.jsonl")
    assert artifacts["dpo_variant_manifest"].endswith("dpo_train_plus_contract_manifest.json")
    assert artifacts["dpo_mix_path"].endswith("dpo_train_plus_contract.jsonl")
    assert artifacts["dpo_mix_manifest"].endswith("dpo_train_plus_contract_manifest.json")


def test_register_artifacts_include_file_fingerprints(tmp_path, monkeypatch):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    paths = {
        "MANIFEST": sensitive_dir / "manifest.json",
        "SFT_TRAIN": sensitive_dir / "sft_train.jsonl",
        "DPO_TRAIN": sensitive_dir / "dpo_train.jsonl",
        "CONTRACT_DPO": sensitive_dir / "contract_dpo.jsonl",
        "DPO_TRAIN_PLUS_CONTRACT": sensitive_dir / "dpo_train_plus_contract.jsonl",
        "QUALITY_AUDIT": sensitive_dir / "quality_audit.json",
        "CORRIDOR_EXPANSION_PLAN": sensitive_dir / "corridor_expansion_plan.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(te, name, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
        path.with_name(f"{path.stem}_manifest.json").write_text(f"{name}-manifest", encoding="utf-8")

    artifacts = te._registry_artifacts("base", "base")
    artifacts_json = json.dumps(artifacts)
    selected_sft = artifacts["artifact_files"]["selected_sft"]
    assert selected_sft["path"] == "external"
    assert selected_sft["bytes"] == len("SFT_TRAIN")
    assert selected_sft["sha256"] == hashlib.sha256(b"SFT_TRAIN").hexdigest()
    assert artifacts["artifact_files"]["selected_sft_manifest"] is None
    assert artifacts["artifact_files"]["contract_dpo_manifest"]["sha256"]
    assert artifacts["artifact_files"]["dpo_mix_manifest"]["sha256"]
    assert artifacts["artifact_files"]["quality_audit"]["sha256"] == hashlib.sha256(b"QUALITY_AUDIT").hexdigest()
    assert artifacts["artifact_files"]["corridor_expansion_plan"]["sha256"] == hashlib.sha256(
        b"CORRIDOR_EXPANSION_PLAN"
    ).hexdigest()
    assert artifacts["quality_audit_summary"] is None
    assert artifacts["sft_path"] == "external"
    assert artifacts["dpo_path"] == "external"
    assert artifacts["contract_dpo_path"] == "external"
    assert artifacts["contract_dpo_manifest"] == "external"
    assert artifacts["dpo_mix_path"] == "external"
    assert artifacts["dpo_mix_manifest"] == "external"
    assert artifacts["quality_audit_path"] == "external"
    assert artifacts["corridor_expansion_plan_path"] == "external"
    assert artifacts["corridor_expansion_plan_manifest"] == "external"
    assert str(tmp_path) not in artifacts_json
    assert "worker@example.com" not in artifacts_json
    assert "case-123456789" not in artifacts_json


def test_register_artifacts_include_quality_audit_summary(tmp_path, monkeypatch):
    audit = tmp_path / "quality_audit.json"
    audit.write_text(json.dumps({
        "clean": False,
        "risk_flags": ["worker@example.com must not be recorded"],
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "ok": False,
            "min_rows": 4,
            "n_dense_single_corridor": 9,
            "corridor_expansion_queue_count": 9,
            "corridor_expansion_task_count": 45,
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
    monkeypatch.setattr(te, "QUALITY_AUDIT", audit)

    artifacts = te._registry_artifacts("base", "base")

    assert artifacts["quality_audit_summary"]["clean"] is False
    assert artifacts["quality_audit_summary"]["risk_flags"] == [
        "9 dense single-corridor typologies (>=4 rows, jurisdiction shortcut risk)"
    ]
    assert artifacts["quality_audit_summary"]["corridor_expansion_queue_count"] == 9
    assert artifacts["quality_audit_summary"]["corridor_expansion_task_count"] == 45
    assert artifacts["quality_audit_summary"]["corridor_expansion_queue_privacy_ok"] is True
    assert artifacts["quality_audit_summary"]["corridor_expansion_tasks_privacy_ok"] is True
    assert "worker@example.com" not in json.dumps(artifacts["quality_audit_summary"])
    assert "corridor_expansion_queue" not in artifacts["quality_audit_summary"]


def test_register_step_refreshes_artifact_fingerprints_at_execution(tmp_path, monkeypatch):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    paths = {
        "MANIFEST": sensitive_dir / "manifest.json",
        "SFT_TRAIN": sensitive_dir / "sft_train.jsonl",
        "DPO_TRAIN": sensitive_dir / "dpo_train.jsonl",
        "CONTRACT_DPO": sensitive_dir / "contract_dpo.jsonl",
        "DPO_TRAIN_PLUS_CONTRACT": sensitive_dir / "dpo_train_plus_contract.jsonl",
        "QUALITY_AUDIT": sensitive_dir / "quality_audit.json",
        "CORRIDOR_EXPANSION_PLAN": sensitive_dir / "corridor_expansion_plan.json",
    }
    for name, path in paths.items():
        monkeypatch.setattr(te, name, path)

    reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=False) if s["name"] == "register")
    planned = _artifacts_from_register(reg)
    assert planned["artifact_files"]["selected_sft"]["sha256"] is None

    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
        path.with_name(f"{path.stem}_manifest.json").write_text(f"{name}-manifest", encoding="utf-8")
    results = te.run_steps([reg], dry_run=True)
    refreshed = _artifacts_from_register(results[0])
    refreshed_json = json.dumps(refreshed)
    assert refreshed["artifact_files"]["selected_sft"]["sha256"] == hashlib.sha256(b"SFT_TRAIN").hexdigest()
    assert refreshed["artifact_files"]["selected_sft"]["path"] == "external"
    assert refreshed["artifact_files"]["quality_audit"]["sha256"] == hashlib.sha256(b"QUALITY_AUDIT").hexdigest()
    assert refreshed["artifact_files"]["corridor_expansion_plan"]["sha256"] == hashlib.sha256(
        b"CORRIDOR_EXPANSION_PLAN"
    ).hexdigest()
    assert str(tmp_path) not in refreshed_json
    assert "worker@example.com" not in refreshed_json
    assert "case-123456789" not in refreshed_json


def test_quality_audit_summary_is_safe_and_actionable(tmp_path):
    audit = tmp_path / "quality_audit.json"
    audit.write_text(json.dumps({
        "clean": False,
        "risk_flags": ["raw worker@example.com must not be recorded"],
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "ok": False,
            "min_rows": 10,
            "n_dense_single_corridor": 9,
            "corridor_expansion_queue_count": 9,
            "corridor_expansion_task_count": 45,
            "corridor_expansion_queue_privacy_scan": {"ok": True},
            "corridor_expansion_tasks_privacy_scan": {"ok": True},
            "corridor_expansion_queue": [{"category": "labor_trafficking", "prompt": "forbidden"}],
        },
        "citation_relevance": {
            "n_incoherent": 0,
            "repair_queue_count": 0,
            "repair_queue_privacy_scan": {"ok": True},
        },
        "fragile_fact_assertions": {"with_phone_like": 0},
    }), encoding="utf-8")

    summary = te._quality_audit_summary(audit)

    assert summary == {
        "path": "external",
        "clean": False,
        "risk_flags": ["9 dense single-corridor typologies (>=10 rows, jurisdiction shortcut risk)"],
        "sft_leaked": 0,
        "dpo_leaked": 0,
        "dense_single_corridor_typologies": 9,
        "corridor_expansion_queue_count": 9,
        "corridor_expansion_task_count": 45,
        "corridor_expansion_queue_privacy_ok": True,
        "corridor_expansion_tasks_privacy_ok": True,
        "citation_incoherent": 0,
        "citation_repair_queue_count": 0,
        "citation_repair_queue_privacy_ok": True,
        "gold_phone_like": 0,
    }
    assert "corridor_expansion_queue" not in summary
    assert "worker@example.com" not in json.dumps(summary)
    assert "prompt" not in json.dumps(summary)


def test_run_steps_attaches_quality_audit_summary(tmp_path, monkeypatch):
    audit = tmp_path / "quality_audit.json"
    audit.write_text(json.dumps({
        "clean": True,
        "risk_flags": [],
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "n_dense_single_corridor": 0,
            "corridor_expansion_queue_count": 0,
            "corridor_expansion_task_count": 0,
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
    monkeypatch.setattr(te, "QUALITY_AUDIT", audit)

    class Done:
        returncode = 0

    monkeypatch.setattr(te.subprocess, "run", lambda *args, **kwargs: Done())

    results = te.run_steps([{"name": "audit", "will_run": True, "cmd": [sys.executable, "-c", "pass"]}],
                           dry_run=False)

    assert results[0]["status"] == "ok"
    assert results[0]["quality_audit"]["clean"] is True
    assert results[0]["quality_audit"]["corridor_expansion_queue_count"] == 0


def test_run_steps_dry_run_executes_nothing():
    steps = te.plan(model_id="m", base="b", with_gpu=False)
    results = te.run_steps(steps, dry_run=True)
    by = {r["name"]: r for r in results}
    assert by["distill"]["status"] == "dry-run" and "cmd" in by["distill"]
    assert by["train"]["status"] == "skipped"          # GPU step skipped even in dry-run
    assert "cmd" in by["train"]                        # keep the later GPU job spec visible
    assert {r["status"] for r in results} <= {"dry-run", "skipped"}   # nothing actually executed


def test_dry_run_logs_use_display_safe_commands(capsys):
    steps = te.plan(model_id="worker@example.com-case-123456789", base="b", with_gpu=False)

    te.run_steps(steps, dry_run=True)
    out = capsys.readouterr().out

    assert "<artifact_fingerprints_json>" in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert str(te._ROOT) not in out


def test_main_writes_display_safe_plan_for_sensitive_model_id(tmp_path, monkeypatch, capsys):
    out_path = tmp_path / "worker@example.com-case-123456789-plan.json"
    monkeypatch.setattr(te, "OUT", out_path)

    rc = te.main(["--dry-run", "--model-id", "worker@example.com-case-123456789"])
    captured = capsys.readouterr().out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    payload_json = json.dumps(payload)

    assert rc == 0
    assert payload["model_id"] == "redacted"
    assert any("<artifact_fingerprints_json>" in step.get("cmd", []) for step in payload["steps"])
    assert "worker@example.com" not in payload_json
    assert "case-123456789" not in payload_json
    assert str(te._ROOT) not in payload_json
    assert "worker@example.com" not in captured
    assert "case-123456789" not in captured
    assert str(tmp_path) not in captured


def test_skipped_gpu_plan_preserves_selected_sft_variant_command():
    steps = te.plan(model_id="m", base="b", with_gpu=False, sft_variant="reasoning_repaired")
    results = te.run_steps(steps, dry_run=True)
    train = next(r for r in results if r["name"] == "train")
    assert train["status"] == "skipped"
    assert train["cmd"][train["cmd"].index("--sft") + 1].endswith("sft_train_reasoning_repaired.jsonl")


def test_skipped_gpu_plan_preserves_selected_dpo_variant_command():
    steps = te.plan(model_id="m", base="b", with_gpu=False, dpo_variant="contract")
    results = te.run_steps(steps, dry_run=True)
    train = next(r for r in results if r["name"] == "train")
    assert train["status"] == "skipped"
    assert train["cmd"][train["cmd"].index("--dpo") + 1].endswith("contract_dpo.jsonl")


def test_skipped_gpu_plan_preserves_selected_mixed_dpo_variant_command():
    steps = te.plan(model_id="m", base="b", with_gpu=False, dpo_variant="base_plus_contract")
    results = te.run_steps(steps, dry_run=True)
    train = next(r for r in results if r["name"] == "train")
    assert train["status"] == "skipped"
    assert train["cmd"][train["cmd"].index("--dpo") + 1].endswith("dpo_train_plus_contract.jsonl")


def test_gpu_available_returns_bool_without_raising():
    assert isinstance(te.gpu_available(), bool)        # no torch / no driver in CI -> False, never raises
