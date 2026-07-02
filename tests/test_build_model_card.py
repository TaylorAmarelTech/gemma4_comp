"""Tests for scripts/build_model_card.py -- render a provenance model card from a registry record."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))   # so the sibling finetune_registry import resolves


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bmc = _load("build_model_card", _ROOT / "scripts" / "build_model_card.py")


def _rec(**kw):
    base = {"model_id": "duecare-x-v0.1.0", "base_model": "google/gemma-4-e4b-it", "status": "trained",
            "git_sha": "abc1234", "created_utc": "2026-06-27T00:00:00+00:00",
            "data": {"manifest_sha256": "deadbeef12345678", "sft_examples": 2613, "dpo_examples": 2613},
            "eval": {}}
    base.update(kw)
    return base


def test_render_card_frontmatter_and_provenance():
    card = bmc.render_card(_rec())
    assert card.startswith("---")                                  # YAML frontmatter for HF
    assert "base_model: google/gemma-4-e4b-it" in card
    assert "duecare-x-v0.1.0" in card and "abc1234" in card and "deadbeef12345678" in card  # reproducibility
    assert "2613" in card                                          # training counts surfaced
    assert "No per-file artifact fingerprints" in card             # legacy records remain honest
    assert "No structured quality-audit summary" in card
    assert "Not legal advice" in card and "Privacy boundary" in card


def test_render_card_artifact_fingerprints_without_absolute_local_paths():
    selected_sft_sha = "a" * 64
    selected_dpo_manifest_sha = "b" * 64
    card = bmc.render_card(_rec(artifacts={"artifact_files": {
        "selected_sft": {
            "path": str(_ROOT / "reports" / "training" / "sft_train_reasoning_repaired.jsonl"),
            "sha256": selected_sft_sha,
            "bytes": 12345,
        },
        "selected_dpo_manifest": {
            "path": "reports\\training\\dpo_train_plus_contract_manifest.json",
            "sha256": selected_dpo_manifest_sha,
            "bytes": 789,
        },
        "selected_sft_manifest": None,
    }}))

    assert "## Artifact fingerprints" in card
    assert selected_sft_sha in card and selected_dpo_manifest_sha in card
    assert "`reports/training/sft_train_reasoning_repaired.jsonl`" in card
    assert "`reports/training/dpo_train_plus_contract_manifest.json`" in card
    assert "12345" in card and "789" in card
    assert str(_ROOT) not in card
    assert "selected_sft_manifest" not in card


def test_render_card_keeps_core_reasoning_artifacts_and_training_arms():
    card = bmc.render_card(_rec(artifacts={
        "sft_variant": "reasoning_repaired_core",
        "dpo_variant": "base_plus_contract",
        "reasoning_repair_mode": "core_remedies",
        "artifact_files": {
            "reasoning_gap_queue": {
                "path": "reports/training/reasoning_gap_queue_core.json",
                "sha256": "1" * 64,
                "bytes": 101,
            },
            "reasoning_repaired_rows": {
                "path": "reports/training/reasoning_repaired_core_sft.jsonl",
                "sha256": "2" * 64,
                "bytes": 202,
            },
            "reasoning_repaired_rows_manifest": {
                "path": "reports/training/reasoning_repaired_core_sft_manifest.json",
                "sha256": "3" * 64,
                "bytes": 303,
            },
            "corridor_expansion_plan": {
                "path": "reports/training/corridor_expansion_plan.json",
                "sha256": "4" * 64,
                "bytes": 404,
            },
            "corridor_expansion_plan_manifest": {
                "path": "reports/training/corridor_expansion_plan_manifest.json",
                "sha256": "5" * 64,
                "bytes": 505,
            },
        },
    }))

    assert "| SFT arm | `reasoning_repaired_core` |" in card
    assert "| DPO arm | `base_plus_contract` |" in card
    assert "| Reasoning repair mode | `core_remedies` |" in card
    assert "`reasoning_gap_queue`" in card
    assert "`reasoning_repaired_rows`" in card
    assert "`reasoning_repaired_rows_manifest`" in card
    assert "`corridor_expansion_plan`" in card
    assert "`corridor_expansion_plan_manifest`" in card
    assert "additional_artifact" not in card
    assert "`reports/training/reasoning_gap_queue_core.json`" in card
    assert "`reports/training/reasoning_repaired_core_sft.jsonl`" in card
    assert "`reports/training/reasoning_repaired_core_sft_manifest.json`" in card
    assert "`reports/training/corridor_expansion_plan.json`" in card
    assert "`reports/training/corridor_expansion_plan_manifest.json`" in card


def test_render_card_artifact_fingerprints_redact_unknown_names_and_external_paths():
    card = bmc.render_card(_rec(artifacts={"artifact_files": {
        "worker@example.com case notes": {
            "path": "reports\\training\\worker@example.com.jsonl",
            "sha256": "c" * 64,
            "bytes": 11,
        },
        "outside_case_file": {
            "path": "C:\\Users\\worker@example.com\\case-123456789.jsonl",
            "sha256": "d" * 64,
            "bytes": 12,
        },
    }}))

    assert "`additional_artifact_1`" in card
    assert "`additional_artifact_2`" in card
    assert "`redacted`" in card
    assert "`external`" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card
    assert "outside_case_file" not in card


def test_render_card_artifact_fingerprints_redact_posix_absolute_paths():
    card = bmc.render_card(_rec(artifacts={"artifact_files": {
        "selected_sft": {
            "path": "/home/taylor/case-notes.jsonl",
            "sha256": "a" * 64,
            "bytes": 12,
        },
        "selected_dpo": {
            "path": "/tmp/case-notes.jsonl",
            "sha256": "b" * 64,
            "bytes": 13,
        },
        "quality_audit": {
            "path": "/Users/Taylor/case-notes.json",
            "sha256": "c" * 64,
            "bytes": 14,
        },
    }}))

    assert "| `selected_sft` | `redacted` |" in card
    assert "| `selected_dpo` | `redacted` |" in card
    assert "| `quality_audit` | `redacted` |" in card
    assert "/home/" not in card
    assert "/tmp/" not in card
    assert "/Users/" not in card
    assert "case-notes" not in card


def test_render_card_artifact_fingerprints_redact_untrusted_sha_and_bytes():
    valid_numeric_sha = "1234567890123456789012345678901234567890123456789012345678901234"
    card = bmc.render_card(_rec(artifacts={"artifact_files": {
        "selected_sft": {
            "path": "reports/training/sft_train.jsonl",
            "sha256": "worker@example.com-case-123456789",
            "bytes": "C:\\Users\\worker@example.com\\case-123456789",
        },
        "selected_dpo": {
            "path": "reports/training/dpo_train.jsonl",
            "sha256": valid_numeric_sha,
            "bytes": -1,
        },
    }}))

    assert "| `selected_sft` | `reports/training/sft_train.jsonl` | `redacted` | redacted |" in card
    assert f"| `selected_dpo` | `reports/training/dpo_train.jsonl` | `{valid_numeric_sha}` | redacted |" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card
    assert "C:\\Users" not in card


def test_render_card_preserves_full_sha256_provenance_values():
    full_sha = "1" * 64
    card = bmc.render_card(_rec(git_sha=full_sha, data={"manifest_sha256": full_sha}))

    assert f"| git_sha (code version) | `{full_sha}` |" in card
    assert f"| data_manifest_sha256 (dataset version) | `{full_sha}` |" in card


def test_render_card_quality_audit_summary_without_raw_queue():
    card = bmc.render_card(_rec(artifacts={
        "quality_audit_summary": {
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
            "corridor_expansion_queue": [{"prompt": "must not render"}],
        },
    }))

    assert "## Pre-train quality audit" in card
    assert "| clean | `false` |" in card
    assert "| corridor expansion queue targets | `9` |" in card
    assert "| corridor expansion curation tasks | `45` |" in card
    assert "| corridor queue privacy scan ok | `true` |" in card
    assert "| corridor task privacy scan ok | `true` |" in card
    assert "9 dense single-corridor typologies (>=10 rows, jurisdiction shortcut risk)" in card
    assert "must not render" not in card
    assert "corridor_expansion_queue" not in card


def test_render_card_quality_audit_scalars_are_sanitized():
    card = bmc.render_card(_rec(artifacts={
        "quality_audit_summary": {
            "clean": False,
            "risk_flags": [],
            "sft_leaked": "worker@example.com",
            "dpo_leaked": r"C:\Users\worker@example.com\case-123456789",
            "dense_single_corridor_typologies": {"raw": "not publishable"},
            "corridor_expansion_queue_count": 9,
            "corridor_expansion_task_count": {"raw": "not publishable"},
            "corridor_expansion_queue_privacy_ok": True,
            "corridor_expansion_tasks_privacy_ok": "worker@example.com",
            "citation_incoherent": 0,
            "citation_repair_queue_count": 0,
            "citation_repair_queue_privacy_ok": True,
            "gold_phone_like": "case-123456789",
        },
    }))

    assert "| SFT heldout near-dup leaks | `redacted` |" in card
    assert "| DPO heldout near-dup leaks | `redacted` |" in card
    assert "| dense single-corridor typologies | `redacted` |" in card
    assert "| corridor expansion queue targets | `9` |" in card
    assert "| corridor expansion curation tasks | `redacted` |" in card
    assert "| corridor task privacy scan ok | `redacted` |" in card
    assert "| gold replies with phone-like strings | `redacted` |" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card
    assert "C:\\Users" not in card


def test_render_card_redacts_non_finite_numeric_values():
    card = bmc.render_card(_rec(
        eval={
            "nan_metric": float("nan"),
            "inf_metric": float("inf"),
            "safe_metric": 0.25,
        },
        artifacts={
            "quality_audit_summary": {
                "clean": False,
                "risk_flags": [],
                "sft_leaked": float("nan"),
                "dpo_leaked": float("inf"),
                "dense_single_corridor_typologies": float("-inf"),
                "corridor_expansion_queue_count": 9,
                "corridor_expansion_task_count": float("nan"),
                "corridor_expansion_queue_privacy_ok": True,
                "corridor_expansion_tasks_privacy_ok": True,
                "citation_incoherent": 0,
                "citation_repair_queue_count": 0,
                "citation_repair_queue_privacy_ok": True,
                "gold_phone_like": 0,
            },
        },
    ))

    assert "| nan_metric | `redacted` |" in card
    assert "| inf_metric | `redacted` |" in card
    assert "| safe_metric | `0.25` |" in card
    assert "| SFT heldout near-dup leaks | `redacted` |" in card
    assert "| DPO heldout near-dup leaks | `redacted` |" in card
    assert "| dense single-corridor typologies | `redacted` |" in card
    assert "`nan`" not in card
    assert "`inf`" not in card
    assert "`-inf`" not in card


def test_render_card_redacts_negative_quality_audit_counts():
    card = bmc.render_card(_rec(artifacts={
        "quality_audit_summary": {
            "clean": False,
            "risk_flags": [],
            "sft_leaked": -1,
            "dpo_leaked": -2.5,
            "dense_single_corridor_typologies": -3,
            "corridor_expansion_queue_count": 9,
            "corridor_expansion_task_count": -4,
            "corridor_expansion_queue_privacy_ok": True,
            "corridor_expansion_tasks_privacy_ok": True,
            "citation_incoherent": 0,
            "citation_repair_queue_count": 0,
            "citation_repair_queue_privacy_ok": True,
            "gold_phone_like": 0,
        },
    }))

    assert "| SFT heldout near-dup leaks | `redacted` |" in card
    assert "| DPO heldout near-dup leaks | `redacted` |" in card
    assert "| dense single-corridor typologies | `redacted` |" in card
    assert "| corridor expansion queue targets | `9` |" in card
    assert "| corridor expansion curation tasks | `redacted` |" in card
    assert "`-1`" not in card
    assert "`-2.5`" not in card
    assert "`-3`" not in card
    assert "`-4`" not in card


def test_render_card_redacts_untrusted_quality_risk_flags():
    card = bmc.render_card(_rec(artifacts={
        "quality_audit_summary": {
            "clean": False,
            "risk_flags": [
                "worker@example.com asked us to call +1 555 0100",
                "coverage queue needs widening with raw details",
                "9 dense single-corridor typologies (>=10 rows, jurisdiction shortcut risk): raw details",
            ],
            "sft_leaked": 0,
            "dpo_leaked": 0,
            "dense_single_corridor_typologies": 0,
            "corridor_expansion_queue_count": 0,
            "corridor_expansion_task_count": 0,
            "corridor_expansion_queue_privacy_ok": True,
            "corridor_expansion_tasks_privacy_ok": True,
            "citation_incoherent": 0,
            "citation_repair_queue_count": 0,
            "citation_repair_queue_privacy_ok": True,
            "gold_phone_like": 0,
        },
    }))

    assert "3 untrusted risk flag(s) redacted" in card
    assert "worker@example.com" not in card
    assert "+1 555 0100" not in card
    assert "coverage queue needs widening" not in card
    assert "raw details" not in card


def test_render_card_eval_pending_then_present():
    pending = bmc.render_card(_rec(eval={}))
    assert "Pending the GPU four-arm evaluation" in pending
    scored = bmc.render_card(_rec(eval={"internalisation": 12.3, "generalisation_gap": 4.1}))
    assert "internalisation" in scored and "12.3" in scored and "Pending the GPU" not in scored


def test_render_card_eval_redacts_untrusted_metric_names_and_values():
    card = bmc.render_card(_rec(eval={
        "worker@example.com metric": 98.1,
        "unsafe_path_metric": r"C:\Users\worker@example.com\case-123456789.json",
        "windows_path_metric": r"C:\Users\Taylor\case-notes",
        "posix_path_metric": "/home/taylor/case-notes",
        "safe text metric": "12.3%",
        "nested_metric": {"raw": "not publishable"},
    }))

    assert "additional_metric_1" in card
    assert "| unsafe_path_metric | `redacted` |" in card
    assert "| safe text metric | `12.3%` |" in card
    assert "| nested_metric | `redacted` |" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card
    assert "Taylor" not in card
    assert "case-notes" not in card
    assert "C:\\Users" not in card
    assert "/home/" not in card


def test_render_card_redacts_unsafe_model_and_base_identifiers():
    card = bmc.render_card(_rec(
        model_id=r"worker@example.com\..\case-123456789",
        base_model=r"C:\Users\worker@example.com\gemma",
    ))

    assert "# redacted" in card
    assert "base_model: redacted" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card


def test_render_card_redacts_posix_absolute_base_model():
    card = bmc.render_card(_rec(base_model="/home/taylor/local-gemma"))

    assert "base_model: redacted" in card
    assert "`redacted`" in card
    assert "/home/" not in card
    assert "local-gemma" not in card


def test_render_card_redacts_untrusted_provenance_scalars():
    card = bmc.render_card(_rec(
        status="worker@example.com",
        git_sha="worker@example.com-case-123456789",
        created_utc=r"C:\Users\worker@example.com\case-123456789",
        data={
            "manifest_sha256": "1234567890123456",
            "sft_examples": "worker@example.com",
            "dpo_examples": -1,
        },
    ))

    assert "| status | redacted |" in card
    assert "| git_sha (code version) | `redacted` |" in card
    assert "| data_manifest_sha256 (dataset version) | `redacted` |" in card
    assert "| created_utc | redacted |" in card
    assert "- SFT examples: **redacted**" in card
    assert "- DPO examples: **redacted**" in card
    assert "worker@example.com" not in card
    assert "case-123456789" not in card
    assert "C:\\Users" not in card


def test_render_card_minimal_record_no_crash():
    card = bmc.render_card({"model_id": "m"})                      # missing base/data/eval -> .get fallbacks
    assert "# m" in card and "n/a" in card                        # counts fall back to n/a, no KeyError


def test_main_require_verified_artifacts_passes_for_matching_file(tmp_path, monkeypatch, capsys):
    artifact = tmp_path / "sft_train.jsonl"
    artifact.write_text("training rows", encoding="utf-8")
    rec = _rec(artifacts={"artifact_files": {
        "selected_sft": {
            "path": str(artifact),
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "bytes": artifact.stat().st_size,
        }
    }})
    monkeypatch.setattr(bmc, "_load_registry", lambda: [rec])

    rc = bmc.main(["--model-id", "duecare-x-v0.1.0", "--stdout", "--require-verified-artifacts"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "## Artifact fingerprints" in captured.out
    assert captured.err == ""


def test_main_require_verified_artifacts_blocks_mismatch(tmp_path, monkeypatch, capsys):
    artifact = tmp_path / "dpo_train.jsonl"
    artifact.write_text("new content", encoding="utf-8")
    rec = _rec(artifacts={"artifact_files": {
        "selected_dpo": {"path": str(artifact), "sha256": "0" * 64, "bytes": 3}
    }})
    monkeypatch.setattr(bmc, "_load_registry", lambda: [rec])

    rc = bmc.main(["--model-id", "duecare-x-v0.1.0", "--stdout", "--require-verified-artifacts"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "artifact verification failed" in captured.err
    assert "selected_dpo:fingerprint_mismatch" in captured.err


def test_main_require_verified_artifacts_redacts_untrusted_issue_details(tmp_path, monkeypatch, capsys):
    artifact = tmp_path / "case-123456789.jsonl"
    artifact.write_text("new content", encoding="utf-8")
    rec = _rec(artifacts={"artifact_files": {
        "worker@example.com case notes": {
            "path": str(artifact),
            "sha256": "0" * 64,
            "bytes": 3,
        }
    }})
    monkeypatch.setattr(bmc, "_load_registry", lambda: [rec])

    rc = bmc.main(["--model-id", "duecare-x-v0.1.0", "--stdout", "--require-verified-artifacts"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "additional_artifact_1:fingerprint_mismatch" in captured.err
    assert "worker@example.com" not in captured.err
    assert "case-123456789" not in captured.err
    assert str(artifact) not in captured.err


def test_main_require_verified_artifacts_blocks_legacy_record(monkeypatch, capsys):
    monkeypatch.setattr(bmc, "_load_registry", lambda: [_rec()])

    rc = bmc.main(["--model-id", "duecare-x-v0.1.0", "--stdout", "--require-verified-artifacts"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "no structured artifact_files" in captured.err


def test_main_missing_record_redacts_sensitive_model_ids(monkeypatch, capsys):
    monkeypatch.setattr(bmc, "_load_registry", lambda: [_rec(model_id="worker@example.com")])

    rc = bmc.main(["--model-id", "case-123456789"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "no registry record for redacted" in captured.out
    assert "known: redacted" in captured.out
    assert "worker@example.com" not in captured.out
    assert "case-123456789" not in captured.out


def test_main_uses_safe_filename_for_unsafe_model_id(tmp_path, monkeypatch, capsys):
    raw_model_id = r"worker@example.com\..\case-123456789"
    monkeypatch.setattr(bmc, "_load_registry", lambda: [_rec(model_id=raw_model_id)])

    rc = bmc.main(["--model-id", raw_model_id, "--out-dir", str(tmp_path)])
    captured = capsys.readouterr()
    written = list(tmp_path.iterdir())

    assert rc == 0
    assert len(written) == 1
    assert written[0].parent == tmp_path
    assert written[0].name.startswith("model_card_")
    assert written[0].name.endswith(".md")
    assert "worker@example.com" not in written[0].name
    assert "case-123456789" not in written[0].name
    assert "worker@example.com" not in captured.out
    assert "case-123456789" not in captured.out
    assert str(tmp_path) not in captured.out


def test_main_write_summary_redacts_untrusted_status_and_data_sha(tmp_path, monkeypatch, capsys):
    rec = _rec(
        status="worker@example.com",
        data={"manifest_sha256": "1234567890123456", "sft_examples": 1, "dpo_examples": 1},
    )
    monkeypatch.setattr(bmc, "_load_registry", lambda: [rec])

    rc = bmc.main(["--model-id", "duecare-x-v0.1.0", "--out-dir", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "status=redacted" in captured.out
    assert "data_sha=redacted" in captured.out
    assert "worker@example.com" not in captured.out
    assert "1234567890123456" not in captured.out
