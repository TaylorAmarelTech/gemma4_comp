from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF_SCRIPT = ROOT / "scripts" / "build_kaggle_proof_training_bundle.py"
RELEASE_SCRIPT = ROOT / "scripts" / "build_kaggle_training_release.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proof = _load(PROOF_SCRIPT, "build_kaggle_proof_training_bundle")
release = _load(RELEASE_SCRIPT, "build_kaggle_training_release")


def test_builds_kaggle_proof_training_release(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    release_dir = tmp_path / "release"

    summary = proof.build_bundle(source_dir)
    assert summary["publication_ready"] is True
    assert summary["sft_train_rows"] == 24
    assert summary["preference_train_rows"] == 24
    assert summary["sft_validation_rows"] == 4
    assert summary["sft_test_rows"] == 4

    source_manifest = json.loads((source_dir / "source_manifest.json").read_text(encoding="utf-8"))
    assert source_manifest["safe_to_train"] is True
    assert source_manifest["prompt_scope"]["closure_status"] == "partial"
    assert source_manifest["prompt_scope"]["full_flywheel_closure"] is False
    assert source_manifest["training_validation"]["ok"] is True

    result = release.build_release(
        source_dir / "source_manifest.json",
        approval_path=source_dir / "publication_approval.json",
        output_dir=release_dir,
        dataset_id="taylorsamarel/duecare-proof-finetuning-data",
        title="DueCare Proof Fine-Tuning Data",
    )
    assert result["safe_to_publish"] is True
    assert result["release_tier"] == "preview"
    assert result["counts"] == {
        "sft_train": 24,
        "preference_train": 24,
        "sft_validation": 4,
        "sft_test": 4,
        "quarantined": 0,
    }
    gates = result["gates"]["canonical_training_contract"]["gates"]
    assert all(gate["passed"] for gate in gates)

    metadata = json.loads((release_dir / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "taylorsamarel/duecare-proof-finetuning-data"
    assert 20 <= len(metadata["subtitle"]) <= 80
    assert release.verify_release_dir(release_dir)["ok"] is True
