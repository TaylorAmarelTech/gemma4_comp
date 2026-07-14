"""Focused tests for the standalone GPU training-bundle boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "validate_training_bundle.py"
    spec = importlib.util.spec_from_file_location("validate_training_bundle_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_sha(row: dict) -> str:
    value = {key: item for key, item in row.items() if key != "sha256"}
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sft(row_id: str, prompt: str, lineage: str, split: str) -> dict:
    row = {
        "id": row_id,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "Preserve records and seek trusted support."},
        ],
        "source_profile": "fixture",
        "rubric_targets": ["safe_action"],
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": lineage,
        "split": split,
        "license": "CC-BY-SA-4.0",
        "quality_gate": {"accepted": True, "unsafe_advice_filtered": True},
        "source_refs": ["fixture:source"],
    }
    row["sha256"] = _row_sha(row)
    return row


def _preference(row_id: str, prompt: str, lineage: str) -> dict:
    row = {
        "id": row_id,
        "prompt": prompt,
        "chosen": "Preserve records and seek trusted support.",
        "rejected": "Ignore the warning signs.",
        "preference_rationale": "The chosen answer is safer and more actionable.",
        "pii_checked": True,
        "lineage_id": lineage,
        "split": "train",
        "license": "CC-BY-SA-4.0",
        "quality_gate": {"accepted": True, "unsafe_advice_filtered": True},
        "source_refs": ["fixture:source"],
    }
    row["sha256"] = _row_sha(row)
    return row


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")


def _bundle(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "bundle"
    root.mkdir()
    train_prompt = "A recruiter changes the agreement. What is a safe next step?"
    validation_prompt = "How can a worker preserve evidence of a contract change?"
    test_prompt = "What should someone do when they fear retaliation?"
    sft_rows = [_sft("train-1", train_prompt, "lineage-train", "train")]
    preference_rows = [_preference("train-1", train_prompt, "lineage-train")]
    validation_rows = [_sft("validation-1", validation_prompt, "lineage-validation", "validation")]
    test_rows = [_sft("test-1", test_prompt, "lineage-test", "test")]
    files = {
        "sft": root / "sft.jsonl",
        "dpo": root / "dpo.jsonl",
        "sft_validation": root / "validation.jsonl",
        "sft_test": root / "test.jsonl",
    }
    _write_jsonl(files["sft"], sft_rows)
    _write_jsonl(files["dpo"], preference_rows)
    _write_jsonl(files["sft_validation"], validation_rows)
    _write_jsonl(files["sft_test"], test_rows)
    heldout_hashes = sorted(
        gate.canonical_sha256(prompt) for prompt in (validation_prompt, test_prompt)
    )
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": gate.SOURCE_HANDOFF_KIND,
        "safe_to_train": True,
        "training_validation": {"ok": True},
        "reasoning_data_policy": "Final answers and deliberately authored visible rationales only.",
        "heldout_prompt_sha256": heldout_hashes,
        "frozen_evaluation_prompt_sha256": heldout_hashes,
        "heldout_lineage_ids": ["lineage-test", "lineage-validation"],
        "artifacts": {key: path.name for key, path in files.items()},
        "artifact_sha256": {key: _sha_file(path) for key, path in files.items()},
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path, files["sft"], files["dpo"]


def test_accepts_manifest_bound_rows_and_returns_path_free_summary(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)

    verified = gate.validate_training_bundle(manifest, sft_path=sft, preference_path=dpo)

    assert len(verified.sft_rows) == 1
    assert len(verified.preference_rows) == 1
    assert verified.contract["ok"] is True
    summary = verified.summary()
    assert summary["manifest_sha256"] == _sha_file(manifest)
    assert str(tmp_path) not in json.dumps(summary)


def test_blocks_tampered_train_artifact_before_row_loading(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)
    sft.write_text(sft.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    with pytest.raises(gate.TrainingBundleError, match="SFT train artifact checksum mismatch"):
        gate.validate_training_bundle(manifest, sft_path=sft, preference_path=dpo)


def test_blocks_identical_but_unbound_selected_file(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)
    unbound = sft.parent / "unbound-copy.jsonl"
    unbound.write_bytes(sft.read_bytes())

    with pytest.raises(gate.TrainingBundleError, match="not the manifest-bound artifact"):
        gate.validate_training_bundle(manifest, sft_path=unbound, preference_path=dpo)


def test_blocks_heldout_declaration_not_proven_by_validation_and_test_rows(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["heldout_prompt_sha256"].append("f" * 64)
    _write_json(manifest, payload)

    with pytest.raises(gate.TrainingBundleError, match="do not exactly match"):
        gate.validate_training_bundle(manifest, sft_path=sft, preference_path=dpo)


def test_recomputed_canonical_contract_blocks_hidden_reasoning(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)
    row = json.loads(sft.read_text(encoding="utf-8"))
    row["messages"][1]["content"] = "<think>private reasoning</think> Safe answer."
    row["sha256"] = _row_sha(row)
    _write_jsonl(sft, [row])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifact_sha256"]["sft"] = _sha_file(sft)
    _write_json(manifest, payload)

    with pytest.raises(gate.TrainingBundleError, match="canonical training contract failed"):
        gate.validate_training_bundle(manifest, sft_path=sft, preference_path=dpo)


def test_legacy_manifest_cannot_authorize_gpu_training(tmp_path: Path) -> None:
    manifest, sft, dpo = _bundle(tmp_path)
    _write_json(manifest, {"schema_version": "1.0", "artifacts": {}})

    with pytest.raises(gate.TrainingBundleError, match="handoff_kind"):
        gate.validate_training_bundle(manifest, sft_path=sft, preference_path=dpo)


def test_accepts_verified_kaggle_release_manifest(tmp_path: Path) -> None:
    source_manifest, source_sft, source_dpo = _bundle(tmp_path)
    root = source_manifest.parent
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    release_files = {
        "sft_train.jsonl": source_sft,
        "preference_train.jsonl": source_dpo,
        "sft_validation.jsonl": root / source["artifacts"]["sft_validation"],
        "sft_test.jsonl": root / source["artifacts"]["sft_test"],
    }
    for name, source_path in list(release_files.items()):
        target = root / name
        target.write_bytes(source_path.read_bytes())
        release_files[name] = target
    release = {
        "schema_version": "1.0",
        "handoff_kind": gate.RELEASE_HANDOFF_KIND,
        "public": True,
        "safe_to_publish": True,
        "reasoning_data_policy": source["reasoning_data_policy"],
        "publication_approval": {"allow_training_use": True},
        "gates": {
            "source_manifest_safe_to_train": True,
            "canonical_training_contract": {"ok": True},
        },
        "heldout_prompt_sha256": source["heldout_prompt_sha256"],
        "heldout_lineage_ids": source["heldout_lineage_ids"],
        "files": {
            name: {"sha256": _sha_file(path)} for name, path in release_files.items()
        },
    }
    release_manifest = root / "release-manifest.json"
    _write_json(release_manifest, release)

    verified = gate.validate_training_bundle(
        release_manifest,
        sft_path=release_files["sft_train.jsonl"],
        preference_path=release_files["preference_train.jsonl"],
    )

    assert verified.handoff_kind == gate.RELEASE_HANDOFF_KIND
    assert verified.summary()["counts"] == {"sft": 1, "preference": 1}
