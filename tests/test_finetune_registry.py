"""Tests for scripts/finetune_registry.py -- the fine-tune run provenance ledger."""
from __future__ import annotations

import hashlib
import importlib.util
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


fr = _load("finetune_registry", _ROOT / "scripts" / "finetune_registry.py")


def test_make_record_builds_provenance(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sft_examples": 200, "dpo_examples": 200, "selected_pairs": 200}),
                        encoding="utf-8")
    rec = fr.make_record(model_id="m-v0.1.0", base_model="google/gemma-4-e4b-it", status="trained",
                         created_utc="2026-06-26T22:40:00+00:00", git="abc1234", data_manifest=manifest)
    assert rec["model_id"] == "m-v0.1.0" and rec["status"] == "trained" and rec["git_sha"] == "abc1234"
    assert rec["data"]["manifest_sha256"] and len(rec["data"]["manifest_sha256"]) == 16   # dataset fingerprint
    assert rec["data"]["sft_examples"] == 200 and rec["data"]["dpo_examples"] == 200       # pulled from manifest
    assert rec["data"]["manifest_path"] == "external"


def test_make_record_persists_display_safe_data_manifest_path(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    manifest = sensitive_dir / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"sft_examples": 1}), encoding="utf-8")
    reg = tmp_path / "registry.jsonl"

    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="2026-06-29T02:10:02+00:00",
        data_manifest=manifest,
    )
    fr.append(rec, reg)
    raw_registry = reg.read_text(encoding="utf-8")

    assert rec["data"]["manifest_path"] == "external"
    assert rec["data"]["manifest_sha256"] == fr.file_sha256(manifest)
    assert "worker@example.com" not in raw_registry
    assert "case-123456789" not in raw_registry
    assert str(tmp_path) not in raw_registry


def test_make_record_rejects_bad_status():
    import pytest
    with pytest.raises(ValueError):
        fr.make_record(model_id="m", base_model="b", status="bogus", created_utc="t")


def test_make_record_redacts_sensitive_bad_status_error():
    import pytest
    with pytest.raises(ValueError) as excinfo:
        fr.make_record(
            model_id="m",
            base_model="b",
            status="worker@example.com case-123456789",
            created_utc="t",
        )

    message = str(excinfo.value)
    assert "got redacted" in message
    assert "worker@example.com" not in message
    assert "case-123456789" not in message


def test_make_record_preserves_valid_artifact_fingerprints():
    sha = "a" * 64
    artifacts = {
        "hf_repo": "org/model",
        "artifact_files": {
            "selected_sft": {"path": "reports/training/sft_train.jsonl", "sha256": sha, "bytes": 123},
            "selected_sft_manifest": None,
            "planned_missing": {"path": "reports/training/missing.jsonl", "sha256": None, "bytes": None},
        },
    }
    rec = fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t", artifacts=artifacts)
    assert rec["artifacts"]["hf_repo"] == "org/model"
    assert rec["artifacts"]["artifact_files"]["selected_sft"]["sha256"] == sha
    assert rec["artifacts"]["artifact_files"]["selected_sft_manifest"] is None


def test_make_record_persists_display_safe_artifact_payloads(tmp_path):
    artifact = tmp_path / "worker@example.com-case-123456789.jsonl"
    artifact.write_text("training rows", encoding="utf-8")
    reg = tmp_path / "registry.jsonl"

    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="2026-06-29T02:10:02+00:00",
        artifacts={
            "worker@example.com extra": r"C:\Users\worker@example.com\case-123456789",
            "artifact_files": {
                "worker@example.com notes": {
                    "path": str(artifact),
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "bytes": artifact.stat().st_size,
                },
            },
        },
    )
    fr.append(rec, reg)
    raw_registry = reg.read_text(encoding="utf-8")

    assert "additional_field_1" in rec["artifacts"]
    assert rec["artifacts"]["additional_field_1"] == "redacted"
    stored_entry = rec["artifacts"]["artifact_files"]["additional_artifact_1"]
    assert stored_entry["path"] == "external"
    assert stored_entry["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert stored_entry["bytes"] == artifact.stat().st_size
    assert "worker@example.com" not in raw_registry
    assert "case-123456789" not in raw_registry
    assert "C:\\Users" not in raw_registry
    assert str(tmp_path) not in raw_registry


def test_make_record_allows_legacy_artifacts_without_fingerprint_map():
    rec = fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t",
                         artifacts={"hf_repo": "org/model", "gguf": "model.gguf"})
    assert rec["artifacts"] == {"hf_repo": "org/model", "gguf": "model.gguf"}


def test_make_record_rejects_malformed_artifact_fingerprints():
    import pytest
    with pytest.raises(ValueError, match="artifacts must be a JSON object"):
        fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t", artifacts=[])
    with pytest.raises(ValueError, match="artifact_files.selected_sft.sha256"):
        fr.make_record(
            model_id="m",
            base_model="b",
            status="planned",
            created_utc="t",
            artifacts={"artifact_files": {
                "selected_sft": {"path": "reports/training/sft_train.jsonl", "sha256": "deadbeef", "bytes": 123}
            }},
        )
    with pytest.raises(ValueError, match="artifact_files.selected_sft.bytes"):
        fr.make_record(
            model_id="m",
            base_model="b",
            status="planned",
            created_utc="t",
            artifacts={"artifact_files": {
                "selected_sft": {"path": "reports/training/sft_train.jsonl", "sha256": "b" * 64, "bytes": -1}
            }},
        )


def test_make_record_redacts_sensitive_artifact_names_in_validation_errors():
    import pytest
    with pytest.raises(ValueError) as excinfo:
        fr.make_record(
            model_id="m",
            base_model="b",
            status="planned",
            created_utc="t",
            artifacts={"artifact_files": {
                "worker@example.com case-123456789": {
                    "path": "reports/training/sft_train.jsonl",
                    "sha256": "deadbeef",
                    "bytes": 123,
                }
            }},
        )

    message = str(excinfo.value)
    assert "artifact_files.additional_artifact_1.sha256" in message
    assert "worker@example.com" not in message
    assert "case-123456789" not in message


def test_verify_record_artifacts_matches_current_files(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_ROOT", tmp_path)
    artifact = tmp_path / "sft_train.jsonl"
    artifact.write_text("training rows", encoding="utf-8")
    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="t",
        artifacts={"artifact_files": {
            "selected_sft": {
                "path": str(artifact),
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "bytes": artifact.stat().st_size,
            },
            "selected_dpo_manifest": None,
            "planned_optional": {"path": str(tmp_path / "future.json"), "sha256": None, "bytes": None},
        }},
    )

    result = fr.verify_record_artifacts(rec)
    assert result["ok"] is True
    assert result["checked"] == 1 and result["matched"] == 1 and result["pending"] == 2
    assert result["issues"] == []
    assert rec["artifacts"]["artifact_files"]["selected_sft"]["path"] == "sft_train.jsonl"


def test_verify_record_artifacts_preserves_core_reasoning_artifact_names(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_ROOT", tmp_path)
    queue = tmp_path / "reports" / "training" / "reasoning_gap_queue_core.json"
    repaired = tmp_path / "reports" / "training" / "reasoning_repaired_core_sft.jsonl"
    manifest = tmp_path / "reports" / "training" / "reasoning_repaired_core_sft_manifest.json"
    corridor_plan = tmp_path / "reports" / "training" / "corridor_expansion_plan.json"
    corridor_manifest = tmp_path / "reports" / "training" / "corridor_expansion_plan_manifest.json"
    for path, text in [
        (queue, "queue"),
        (repaired, "rows"),
        (manifest, "manifest"),
        (corridor_plan, "corridor-plan"),
        (corridor_manifest, "corridor-manifest"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="t",
        artifacts={"artifact_files": {
            "reasoning_gap_queue": {
                "path": str(queue),
                "sha256": hashlib.sha256(queue.read_bytes()).hexdigest(),
                "bytes": queue.stat().st_size,
            },
            "reasoning_repaired_rows": {
                "path": str(repaired),
                "sha256": "0" * 64,
                "bytes": repaired.stat().st_size,
            },
            "reasoning_repaired_rows_manifest": {
                "path": str(manifest),
                "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "bytes": manifest.stat().st_size,
            },
            "corridor_expansion_plan": {
                "path": str(corridor_plan),
                "sha256": hashlib.sha256(corridor_plan.read_bytes()).hexdigest(),
                "bytes": corridor_plan.stat().st_size,
            },
            "corridor_expansion_plan_manifest": {
                "path": str(corridor_manifest),
                "sha256": hashlib.sha256(corridor_manifest.read_bytes()).hexdigest(),
                "bytes": corridor_manifest.stat().st_size,
            },
        }},
    )

    result = fr.verify_record_artifacts(rec)

    assert result["checked"] == 5
    assert result["matched"] == 4
    assert result["ok"] is False
    assert result["issues"] == [{
        "artifact": "reasoning_repaired_rows",
        "issue": "fingerprint_mismatch",
        "path": "reports/training/reasoning_repaired_core_sft.jsonl",
        "expected_sha256": "0" * 64,
        "actual_sha256": hashlib.sha256(repaired.read_bytes()).hexdigest(),
        "expected_bytes": repaired.stat().st_size,
        "actual_bytes": repaired.stat().st_size,
    }]
    assert rec["artifacts"]["artifact_files"]["reasoning_gap_queue"]["path"] == (
        "reports/training/reasoning_gap_queue_core.json"
    )
    assert rec["artifacts"]["artifact_files"]["reasoning_repaired_rows_manifest"]["path"] == (
        "reports/training/reasoning_repaired_core_sft_manifest.json"
    )
    assert rec["artifacts"]["artifact_files"]["corridor_expansion_plan"]["path"] == (
        "reports/training/corridor_expansion_plan.json"
    )
    assert rec["artifacts"]["artifact_files"]["corridor_expansion_plan_manifest"]["path"] == (
        "reports/training/corridor_expansion_plan_manifest.json"
    )


def test_verify_record_artifacts_reports_missing_and_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(fr, "_ROOT", tmp_path)
    artifact = tmp_path / "dpo_train.jsonl"
    artifact.write_text("new content", encoding="utf-8")
    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="t",
        artifacts={"artifact_files": {
            "selected_dpo": {"path": str(artifact), "sha256": "c" * 64, "bytes": 5},
            "selected_sft": {"path": str(tmp_path / "missing.jsonl"), "sha256": "d" * 64, "bytes": 10},
        }},
    )

    result = fr.verify_record_artifacts(rec)
    assert result["ok"] is False
    issues = {(i["artifact"], i["issue"]) for i in result["issues"]}
    assert ("selected_dpo", "fingerprint_mismatch") in issues
    assert ("selected_sft", "missing_file") in issues


def test_verify_record_artifacts_returns_display_safe_issue_payloads(tmp_path):
    artifact = tmp_path / "worker@example.com-case-123456789.jsonl"
    artifact.write_text("new content", encoding="utf-8")
    result = fr.verify_record_artifacts({
        "model_id": "worker@example.com-case-123456789",
        "status": "worker@example.com",
        "created_utc": r"C:\Users\worker@example.com\case-123456789",
        "artifacts": {"artifact_files": {
            "worker@example.com case notes": {"path": str(artifact), "sha256": "0" * 64, "bytes": 3},
        }},
    })
    result_json = json.dumps(result)

    assert result["model_id"] == "redacted"
    assert result["status"] == "redacted"
    assert result["created_utc"] == "redacted"
    assert result["issues"][0]["artifact"] == "additional_artifact_1"
    assert result["issues"][0]["issue"] == "fingerprint_mismatch"
    assert result["issues"][0]["path"] == "external"
    assert "worker@example.com" not in result_json
    assert "case-123456789" not in result_json
    assert str(tmp_path) not in result_json


def test_main_verify_latest_registry_records(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fr, "_ROOT", tmp_path)
    artifact = tmp_path / "artifact.jsonl"
    artifact.write_text("ok", encoding="utf-8")
    reg = tmp_path / "finetune_registry.jsonl"
    fr.append(fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="2026-06-29T02:10:02+00:00",
        artifacts={"artifact_files": {
            "selected_sft": {
                "path": str(artifact),
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "bytes": artifact.stat().st_size,
            }
        }},
    ), reg)

    assert fr.main(["--registry", str(reg), "verify", "m"]) == 0
    out = capsys.readouterr().out
    assert "OK m" in out
    assert "created=2026-06-29T02:10:02+00:00" in out
    assert fr.main(["--registry", str(reg), "verify", "missing-model"]) == 1


def test_main_verify_json_redacts_untrusted_issue_details(tmp_path, capsys):
    artifact = tmp_path / "worker@example.com-case-123456789.jsonl"
    artifact.write_text("new content", encoding="utf-8")
    reg = tmp_path / "finetune_registry.jsonl"
    rec = fr.make_record(
        model_id="worker@example.com-case-123456789",
        base_model="b",
        status="planned",
        created_utc="t",
        artifacts={"artifact_files": {
            "worker@example.com notes": {"path": str(artifact), "sha256": "c" * 64, "bytes": 5},
        }},
    )
    fr.append(rec, reg)

    assert fr.main(["--registry", str(reg), "verify", "worker@example.com-case-123456789", "--json"]) == 1
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload[0]["model_id"] == "redacted"
    assert payload[0]["issues"] == [{
        "artifact": "additional_artifact_1",
        "issue": "unverifiable_path",
        "path": "external",
    }]
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert str(tmp_path) not in out


def test_main_show_redacts_sensitive_registry_record_fields(tmp_path, capsys):
    artifact = tmp_path / "worker@example.com-case-123456789.jsonl"
    artifact.write_text("ok", encoding="utf-8")
    reg = tmp_path / "finetune_registry.jsonl"
    rec = fr.make_record(
        model_id="worker@example.com-case-123456789",
        base_model="b",
        status="planned",
        created_utc="t",
        data_manifest=artifact,
        artifacts={
            "worker@example.com extra": "call +1 555 0100",
            "artifact_files": {
                "worker@example.com notes": {
                    "path": str(artifact),
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "bytes": artifact.stat().st_size,
                },
            },
        },
    )
    fr.append(rec, reg)

    assert fr.main(["--registry", str(reg), "show", "worker@example.com-case-123456789"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload[0]["model_id"] == "redacted"
    assert payload[0]["data"]["manifest_path"] == "external"
    assert payload[0]["artifacts"]["artifact_files"]["additional_artifact_1"]["path"] == "external"
    assert "additional_field_1" in payload[0]["artifacts"]
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert "+1 555 0100" not in out
    assert str(tmp_path) not in out


def test_main_add_redacts_sensitive_status_output(tmp_path, capsys):
    manifest = tmp_path / "worker@example.com-case-123456789-manifest.json"
    manifest.write_text(json.dumps({"sft_examples": 1}), encoding="utf-8")
    reg = tmp_path / "finetune_registry.jsonl"

    assert fr.main([
        "--registry", str(reg),
        "add",
        "--model-id", "worker@example.com-case-123456789",
        "--base", "b",
        "--data-manifest", str(manifest),
    ]) == 0
    out = capsys.readouterr().out

    assert "+planned redacted" in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert str(tmp_path) not in out


def test_main_add_redacts_sensitive_base_model_output(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"

    assert fr.main([
        "--registry", str(reg),
        "add",
        "--model-id", "m",
        "--base", r"C:\Users\worker@example.com\case-123456789",
    ]) == 0
    out = capsys.readouterr().out

    assert "base=redacted" in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out


def test_main_list_redacts_sensitive_base_and_eval_values(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"
    rec = fr.make_record(
        model_id="m",
        base_model=r"C:\Users\worker@example.com\case-123456789",
        status="planned",
        created_utc="t",
        eval_scores={
            "safe_metric": 12.3,
            "worker@example.com metric": "call +1 555 0100 about case-123456789",
        },
    )
    fr.append(rec, reg)

    assert fr.main(["--registry", str(reg), "list"]) == 0
    out = capsys.readouterr().out

    assert "base=redacted" in out
    assert "safe_metric" in out
    assert "additional_field_1" in out
    assert "worker@example.com" not in out
    assert "+1 555 0100" not in out
    assert "case-123456789" not in out


def test_main_list_redacts_pathlike_eval_keys_without_pii_patterns(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"
    rec = fr.make_record(
        model_id="m",
        base_model="b",
        status="planned",
        created_utc="t",
        eval_scores={
            r"C:\Users\Taylor\case-notes": 9.1,
            "/home/taylor/case-notes": 8.7,
            "safe_metric": 7.5,
            "local_path_value": r"C:\Users\Taylor\case-notes",
            "posix_path_value": "/home/taylor/case-notes",
        },
    )
    fr.append(rec, reg)

    assert fr.main(["--registry", str(reg), "list"]) == 0
    out = capsys.readouterr().out

    assert "additional_field_1" in out
    assert "additional_field_2" in out
    assert "safe_metric" in out
    assert "local_path_value" in out
    assert "posix_path_value" in out
    assert "Taylor" not in out
    assert "case-notes" not in out
    assert "C:\\Users" not in out
    assert "/home/" not in out


def test_main_list_redacts_untrusted_status_and_data_sha_from_loaded_record(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"
    fr.append({
        "model_id": "m",
        "base_model": "b",
        "status": "worker@example.com",
        "created_utc": "2026-06-29T02:10:02+00:00",
        "data": {"manifest_sha256": "1234567890123456"},
        "eval": {},
        "artifacts": {},
    }, reg)

    assert fr.main(["--registry", str(reg), "list"]) == 0
    out = capsys.readouterr().out

    assert "redacted" in out
    assert "data_sha=redacted" in out
    assert "worker@example.com" not in out
    assert "1234567890123456" not in out


def test_main_verify_json_redacts_untrusted_record_scalars(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"
    fr.append({
        "model_id": "m",
        "base_model": "b",
        "status": "worker@example.com",
        "created_utc": r"C:\Users\worker@example.com\case-123456789",
        "data": {},
        "eval": {},
        "artifacts": {"artifact_files": {}},
    }, reg)

    assert fr.main(["--registry", str(reg), "verify", "m", "--json"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload[0]["status"] == "redacted"
    assert payload[0]["created_utc"] == "redacted"
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert "C:\\Users" not in out


def test_file_sha256_is_deterministic_and_content_sensitive(tmp_path):
    p = tmp_path / "a.json"; p.write_text("hello", encoding="utf-8")
    q = tmp_path / "b.json"; q.write_text("world", encoding="utf-8")
    assert fr.file_sha256(p) == fr.file_sha256(p)        # deterministic -> reproducible dataset version
    assert fr.file_sha256(p) != fr.file_sha256(q)        # content-sensitive
    assert fr.file_sha256(tmp_path / "missing.json") is None and fr.file_sha256(None) is None


def test_append_preserves_history_and_latest_wins(tmp_path):
    reg = tmp_path / "finetune_registry.jsonl"
    r1 = fr.make_record(model_id="m", base_model="b", status="planned",
                        created_utc="2026-06-26T20:00:00+00:00")
    r2 = fr.make_record(model_id="m", base_model="b", status="trained",
                        created_utc="2026-06-26T22:00:00+00:00")
    fr.append(r1, reg)
    fr.append(r2, reg)
    records = fr.load(reg)
    assert len(records) == 2                              # append-only: prior 'planned' row never destroyed
    assert fr.latest_by_id(records)["m"]["status"] == "trained"   # queries collapse to the latest status
    assert r1["data"]["manifest_sha256"] is None         # no manifest -> None, no crash


def test_load_skips_malformed_and_non_object_registry_rows(tmp_path):
    reg = tmp_path / "finetune_registry.jsonl"
    good = fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t")
    reg.write_text(
        "\n".join([
            json.dumps(good),
            '"worker@example.com case-123456789 raw registry row"',
            "[1, 2, 3]",
            "{bad json",
        ]) + "\n",
        encoding="utf-8",
    )

    records = fr.load(reg)

    assert records == [good]
    assert fr.latest_by_id(records)["m"] == good


def test_latest_by_id_skips_non_object_records_from_direct_call():
    good = fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t")

    latest = fr.latest_by_id([
        "worker@example.com case-123456789 raw registry row",
        ["not", "a", "record"],
        good,
    ])

    assert latest == {"m": good}


def test_main_list_ignores_non_object_registry_rows_without_leaking(tmp_path, capsys):
    reg = tmp_path / "finetune_registry.jsonl"
    good = fr.make_record(model_id="m", base_model="b", status="planned", created_utc="t")
    reg.write_text(
        "\n".join([
            json.dumps(good),
            '"worker@example.com case-123456789 raw registry row"',
            "[1, 2, 3]",
        ]) + "\n",
        encoding="utf-8",
    )

    assert fr.main(["--registry", str(reg), "list"]) == 0
    out = capsys.readouterr().out

    assert "m" in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
