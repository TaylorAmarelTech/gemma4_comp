from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proof = _load(
    ROOT / "scripts" / "build_kaggle_proof_training_bundle.py",
    "interim_collection_proof_builder",
)
release = _load(
    ROOT / "scripts" / "build_kaggle_training_release.py",
    "interim_collection_release_builder",
)
collection = _load(
    ROOT / "scripts" / "build_kaggle_interim_collection.py",
    "build_kaggle_interim_collection",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _approved_release(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source"
    release_dir = tmp_path / "release"
    proof.build_bundle(source_dir)
    release.build_release(
        source_dir / "source_manifest.json",
        approval_path=source_dir / "publication_approval.json",
        output_dir=release_dir,
        dataset_id=collection.COMBINED_DATASET_ID,
        title="DueCare Proof Fine-Tuning Data",
    )
    return release_dir


def _notebook(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["nbformat"] == 4
    for index, cell in enumerate(value["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        compile(source, f"{path.name}:cell-{index}", "exec")
    return value


def test_builds_two_datasets_and_three_notebooks(tmp_path: Path) -> None:
    release_dir = _approved_release(tmp_path)
    output = tmp_path / "collection"

    result = collection.build_collection(
        release_dir,
        output,
        repo_commit="a" * 40,
    )

    assert result["claims"] == {
        "datasets_are_interim_proof": True,
        "hidden_chain_of_thought_published": False,
        "adapter_weights_published": False,
        "completed_improvement_result": False,
        "full_flywheel_corpus_published": False,
    }
    assert result["source_release_sha256"] == _sha(release_dir / "release-manifest.json")

    sft_dir = output / "datasets" / "visible_reasoning_sft"
    preference_dir = output / "datasets" / "preference_pairs"
    sft_manifest = json.loads((sft_dir / "lane-manifest.json").read_text(encoding="utf-8"))
    preference_manifest = json.loads(
        (preference_dir / "lane-manifest.json").read_text(encoding="utf-8")
    )
    assert sft_manifest["lane"] == "sft"
    assert preference_manifest["lane"] == "preference"
    assert sft_manifest["safe_to_publish"] is True
    assert preference_manifest["safe_to_publish"] is True
    assert sft_manifest["derived_publication_authorization"] == {
        "basis": "exact-byte subset redistribution from the approved source release",
        "new_or_modified_training_rows": 0,
        "source_allow_public_redistribution": True,
        "source_approval_sha256": sft_manifest["publication_approval"]["approval_sha256"],
        "note": (
            "This is not a new curator judgment. The lane contains exact public row bytes "
            "already covered by the source approval and redistribution permission."
        ),
    }
    assert (sft_dir / "sft_train.jsonl").read_bytes() == (
        release_dir / "sft_train.jsonl"
    ).read_bytes()
    assert (preference_dir / "preference_train.jsonl").read_bytes() == (
        release_dir / "preference_train.jsonl"
    ).read_bytes()
    assert "preference_train.jsonl" not in sft_manifest["files"]
    assert "sft_train.jsonl" not in preference_manifest["files"]
    assert "Hidden model chain-of-thought is neither requested" in (
        sft_dir / "DATA_CARD.md"
    ).read_text(encoding="utf-8")

    notebook_dirs = {
        "integrity_audit": collection.AUDIT_NOTEBOOK_ID,
        "gemma4_training_starter": collection.TRAINING_NOTEBOOK_ID,
        "four_arm_evaluation": collection.EVALUATION_NOTEBOOK_ID,
    }
    for directory, notebook_id in notebook_dirs.items():
        root = output / "notebooks" / directory
        metadata = json.loads((root / "kernel-metadata.json").read_text(encoding="utf-8"))
        assert metadata["id"] == notebook_id
        assert metadata["kernel_type"] == "notebook"
        assert metadata["enable_gpu"] is False
        _notebook(root / "notebook.ipynb")

    training_notebook = json.loads(
        (output / "notebooks" / "gemma4_training_starter" / "notebook.ipynb").read_text(
            encoding="utf-8"
        )
    )
    training_source = "\n".join(
        "".join(cell["source"]) for cell in training_notebook["cells"]
    )
    assert "RUN_GPU_TRAINING = False" in training_source
    assert '"repository_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in training_source
    assert "No successful training or model-improvement claim" in training_source


def test_refuses_source_release_that_does_not_reverify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(collection, "verify_release_dir", lambda _path: {"ok": False})

    with pytest.raises(collection.CollectionError, match="reverification"):
        collection.build_collection(source, tmp_path / "out")


def test_force_refuses_unexpected_output_entry(tmp_path: Path) -> None:
    release_dir = _approved_release(tmp_path)
    output = tmp_path / "collection"
    collection.build_collection(release_dir, output)
    unexpected = output / "datasets" / "visible_reasoning_sft" / "do-not-delete.txt"
    unexpected.write_text("owned by someone else", encoding="utf-8")

    with pytest.raises(collection.CollectionError, match="unexpected output entry"):
        collection.build_collection(release_dir, output, force=True)
