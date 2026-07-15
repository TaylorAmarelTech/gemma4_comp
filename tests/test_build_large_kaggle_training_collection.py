from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LARGE_BUILDER_PATH = ROOT / "scripts" / "build_large_multiperspective_training_bundle.py"
COLLECTION_BUILDER_PATH = ROOT / "scripts" / "build_large_kaggle_training_collection.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


large_builder = _load_module(
    "large_multiperspective_builder_for_collection_tests", LARGE_BUILDER_PATH
)
collection_builder = _load_module(
    "large_kaggle_collection_builder_for_tests", COLLECTION_BUILDER_PATH
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _notebook_source(path: Path) -> tuple[dict, str]:
    notebook = _json(path)
    code = "\n".join(
        "".join(cell.get("source") or [])
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    compile(code, str(path), "exec")
    return notebook, code


@pytest.fixture(scope="module")
def candidate_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("large-candidate") / "candidate"
    summary = large_builder.build_candidate(
        output,
        train_rows=240,
        validation_rows=60,
        test_rows=60,
        shard_rows=60,
        _minimum_train_rows=1,
    )
    assert summary["quality_audit_clean"] is True
    assert summary["safe_to_publish"] is False
    return output


def _approval(candidate: Path, *, source_manifest_sha256: str | None = None) -> dict:
    manifest_path = candidate / "candidate-manifest.json"
    quality_path = candidate / "quality-audit.json"
    return {
        "schema_version": collection_builder.APPROVAL_SCHEMA,
        "handoff_kind": collection_builder.APPROVAL_KIND,
        "source_manifest_sha256": source_manifest_sha256 or _sha256(manifest_path),
        "approved_by": "test-independent-curator",
        "approved_at": "2026-07-15T00:00:00Z",
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "rights_holder": "DueCare project contributors",
        "row_license": "CC-BY-SA-4.0",
        "release_license": "CC-BY-SA-4.0",
        "approvals": {
            "curator_approved": True,
            "privacy_approved": True,
            "license_approved": True,
            "quality_approved": True,
            "public_redistribution_approved": True,
        },
        "quality_audit": {
            "artifact_sha256": _sha256(quality_path),
            "clean": True,
            "risk_flags": [],
        },
    }


def test_builds_private_manifest_bound_collection_with_cpu_safe_notebooks(
    tmp_path: Path, candidate_dir: Path
) -> None:
    output = tmp_path / "collection"
    result = collection_builder.build_collection(
        candidate_dir / "candidate-manifest.json",
        output,
        shard_target_rows=50,
        repo_commit="a" * 40,
    )

    assert result["publication_state"] == "candidate_private"
    assert result["safe_to_train"] is True
    assert result["safe_to_publish"] is False
    assert result["no_publication_performed"] is True
    assert result["verification"]["ok"] is True
    assert result["dataset"]["counts"] == {
        "sft_train": 240,
        "preference_train": 240,
        "sft_validation": 60,
        "sft_test": 60,
    }

    dataset = output / "dataset"
    release = _json(dataset / "release-manifest.json")
    metadata = _json(dataset / "dataset-metadata.json")
    shard_index = _json(dataset / "shard-index.json")
    assert release["publication_state"] == "candidate_private"
    assert release["safe_to_train"] is True
    assert release["safe_to_publish"] is False
    assert release["public"] is False
    assert release["publication_approval"] is None
    assert release["repo_provenance"]["commit"] == "a" * 40
    assert release["repo_provenance"]["generator_sha256"] == _sha256(
        Path(collection_builder.__file__)
    )
    assert "dataset-metadata.json" not in release["files"]
    assert release["claims"] == {
        "training_completed": False,
        "adapter_produced": False,
        "model_lift_demonstrated": False,
        "full_flywheel_closure": False,
    }
    assert metadata["isPrivate"] is True
    assert metadata["licenses"] == [{"name": "CC-BY-SA-4.0"}]
    assert metadata["keywords"] == ["nlp"]
    assert len(metadata["resources"]) == sum(
        len(lane["shards"]) for lane in shard_index["lanes"].values()
    ) + 12

    for name in (
        "README.md",
        "DATA_CARD.md",
        "SCHEMA.md",
        "LOADING.md",
        "SOURCES.md",
        "LIMITATIONS.md",
        "CHANGELOG.md",
        "LICENSE",
        "CITATION.cff",
        "candidate-manifest.json",
        "quality-audit.json",
        "case-graphs.jsonl",
        "dataset-overview.csv",
        "axis-catalog.csv",
        "preview-catalog.csv",
        "preview-catalog.jsonl",
        "croissant.json",
    ):
        assert (dataset / name).is_file(), name

    croissant = _json(dataset / "croissant.json")
    assert croissant["dct:conformsTo"] == "http://mlcommons.org/croissant/1.0"
    assert croissant["url"] == "https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus"
    assert croissant["distribution"]
    for item in croissant["distribution"]:
        declaration = release["files"][item["@id"]]
        assert item["sha256"] == declaration["sha256"]
        assert item["contentSize"] == f"{declaration['bytes']} B"

    with (dataset / "dataset-overview.csv").open(encoding="utf-8", newline="") as handle:
        overview = list(csv.DictReader(handle))
    assert len(overview) == len(collection_builder.LANES)
    assert {row["training_role"] for row in overview} == {
        "positive_sft_target",
        "chosen_rejected_preference_pair",
        "diagnostic_holdout_not_training",
    }
    with (dataset / "axis-catalog.csv").open(encoding="utf-8", newline="") as handle:
        axis_rows = list(csv.DictReader(handle))
    assert {row["axis"] for row in axis_rows} >= {
        "personas",
        "journey_stages",
        "evidence_states",
        "temporal_lenses",
    }

    for lane_name, lane in shard_index["lanes"].items():
        assert lane["rows"] == result["dataset"]["counts"][lane_name]
        assert sum(part["rows"] for part in lane["shards"]) == lane["rows"]
        for part in lane["shards"]:
            assert 1 <= part["rows"] <= 50
            path = dataset / part["path"]
            assert path.stat().st_size == part["bytes"]
            assert _sha256(path) == part["sha256"]

    assert collection_builder.verify_dataset_package(dataset) == result["verification"]

    integrity_dir = output / "notebooks" / "integrity_exploration"
    integrity_notebook, integrity_code = _notebook_source(integrity_dir / "notebook.ipynb")
    integrity_metadata = _json(integrity_dir / "kernel-metadata.json")
    assert integrity_metadata["is_private"] is True
    assert integrity_metadata["enable_gpu"] is False
    assert integrity_metadata["enable_internet"] is False
    assert "integrity-audit.json" in integrity_code
    assert '.rglob("release-manifest.json")' in integrity_code
    assert all(cell.get("id") for cell in integrity_notebook["cells"])

    smoke_dir = output / "notebooks" / "gemma4_plan_smoke"
    smoke_notebook, smoke_code = _notebook_source(smoke_dir / "notebook.ipynb")
    smoke_metadata = _json(smoke_dir / "kernel-metadata.json")
    assert smoke_metadata["is_private"] is True
    assert smoke_metadata["enable_gpu"] is False
    assert smoke_metadata["model_sources"] == [collection_builder.DEFAULT_MODEL_SOURCE]
    assert "RUN_GPU_MODEL_DATA_PREFLIGHT = False" in smoke_code
    assert '.rglob("release-manifest.json")' in smoke_code
    assert '"training_completed": False' in smoke_code
    assert (
        "This is deliberately a model/data compatibility preflight, not fine-tuning"
        in smoke_code
    )
    assert "cloudflared" not in smoke_code.lower()
    assert "tunnel" not in smoke_code.lower()
    assert all(cell.get("id") for cell in smoke_notebook["cells"])


def test_collection_is_deterministic_and_never_read_texts_jsonl_wholly(
    tmp_path: Path, candidate_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path.suffix == ".jsonl":
            raise AssertionError(f"JSONL must be streamed, not read_text: {path}")
        return original_read_text(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", guarded_read_text)
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            first,
            shard_target_rows=47,
            repo_commit="b" * 40,
        )

    collection_builder.build_collection(
        candidate_dir / "candidate-manifest.json",
        second,
        shard_target_rows=47,
        repo_commit="b" * 40,
    )
    assert _file_hashes(first) == _file_hashes(second)


def test_public_ready_requires_exact_independent_approval(
    tmp_path: Path, candidate_dir: Path
) -> None:
    with pytest.raises(
        collection_builder.CollectionError,
        match="requires exact manifest-bound approval",
    ):
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            tmp_path / "unapproved",
            public_ready=True,
            repo_commit="c" * 40,
    )
    assert not (tmp_path / "unapproved").exists()

    schema_approval = tmp_path / "schema-approval.json"
    invalid_schema = _approval(candidate_dir)
    invalid_schema["schema_version"] = "unexpected"
    schema_approval.write_text(json.dumps(invalid_schema), encoding="utf-8")
    with pytest.raises(collection_builder.CollectionError, match="schema_version"):
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            tmp_path / "bad-schema",
            approval_path=schema_approval,
            public_ready=True,
            repo_commit="c" * 40,
        )
    assert not (tmp_path / "bad-schema").exists()

    wrong_approval = tmp_path / "wrong-approval.json"
    wrong_approval.write_text(
        json.dumps(_approval(candidate_dir, source_manifest_sha256="0" * 64)),
        encoding="utf-8",
    )
    with pytest.raises(collection_builder.CollectionError, match="not bound"):
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            tmp_path / "wrong",
            approval_path=wrong_approval,
            public_ready=True,
            repo_commit="c" * 40,
        )
    assert not (tmp_path / "wrong").exists()

    approval_path = tmp_path / "approval.json"
    approval_path.write_text(json.dumps(_approval(candidate_dir)), encoding="utf-8")
    output = tmp_path / "approved"
    result = collection_builder.build_collection(
        candidate_dir / "candidate-manifest.json",
        output,
        approval_path=approval_path,
        public_ready=True,
        shard_target_rows=75,
        repo_commit="c" * 40,
    )
    release = _json(output / "dataset" / "release-manifest.json")
    metadata = _json(output / "dataset" / "dataset-metadata.json")
    assert result["publication_state"] == "approved_public_ready"
    assert result["safe_to_train"] is True
    assert result["safe_to_publish"] is True
    assert result["no_publication_performed"] is True
    assert release["safe_to_publish"] is True
    assert release["publication_approval"]["approved_by"] == "test-independent-curator"
    assert metadata["isPrivate"] is False


def test_manifest_bound_source_and_finished_release_fail_closed_on_tampering(
    tmp_path: Path, candidate_dir: Path
) -> None:
    candidate_copy = tmp_path / "candidate-copy"
    import shutil

    shutil.copytree(candidate_dir, candidate_copy)
    candidate_manifest = _json(candidate_copy / "candidate-manifest.json")
    source_shard = (
        candidate_copy
        / candidate_manifest["artifacts"]["shards"]["sft_train"][0]["path"]
    )
    with source_shard.open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(collection_builder.CollectionError, match="sha256 mismatch"):
        collection_builder.build_collection(
            candidate_copy / "candidate-manifest.json",
            tmp_path / "rejected-tampered-source",
            repo_commit="d" * 40,
        )

    output = tmp_path / "valid"
    collection_builder.build_collection(
        candidate_dir / "candidate-manifest.json",
        output,
        shard_target_rows=80,
        repo_commit="d" * 40,
    )
    release = _json(output / "dataset" / "release-manifest.json")
    released_shard_name = release["lanes"]["sft_train"]["shards"][0]["path"]
    with (output / "dataset" / released_shard_name).open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(collection_builder.CollectionError, match="release file hash/size mismatch"):
        collection_builder.verify_dataset_package(output / "dataset")


def test_force_replacement_is_transactional_and_refuses_foreign_output(
    tmp_path: Path,
    candidate_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "collection"
    collection_builder.build_collection(
        candidate_dir / "candidate-manifest.json",
        output,
        shard_target_rows=80,
        repo_commit="e" * 40,
    )
    manifest_before = _sha256(output / "collection-manifest.json")

    def fail_after_staging(
        _source_manifest: Path,
        staging: Path,
        **_kwargs,
    ) -> dict:
        (staging / "partial.txt").write_text("partial", encoding="utf-8")
        raise RuntimeError("simulated staged build failure")

    monkeypatch.setattr(collection_builder, "_build_collection_into", fail_after_staging)
    with pytest.raises(RuntimeError, match="simulated staged build failure"):
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            output,
            force=True,
            repo_commit="e" * 40,
        )

    assert _sha256(output / "collection-manifest.json") == manifest_before
    assert collection_builder.verify_dataset_package(output / "dataset")["ok"] is True
    assert not list(tmp_path.glob(".collection-building-*"))

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    foreign_file = foreign / "owned-by-user.txt"
    foreign_file.write_text("preserve", encoding="utf-8")
    with pytest.raises(collection_builder.CollectionError, match="ownership marker"):
        collection_builder.build_collection(
            candidate_dir / "candidate-manifest.json",
            foreign,
            force=True,
            repo_commit="e" * 40,
        )
    assert foreign_file.read_text(encoding="utf-8") == "preserve"


def test_commit_staging_uses_verified_copy_after_persistent_windows_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / ".collection-building-locked"
    output = tmp_path / "collection"
    staging.mkdir()
    (staging / "payload.txt").write_text("bound payload", encoding="utf-8")
    (staging / "collection-manifest.json").write_text("{}", encoding="utf-8")
    original_rename = Path.rename

    def locked_rename(path: Path, target: Path):
        if path == staging and Path(target) == output:
            raise PermissionError("simulated persistent OneDrive lock")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", locked_rename)
    monkeypatch.setattr(collection_builder.time, "sleep", lambda _seconds: None)

    collection_builder._commit_staging(staging, output)

    assert not staging.exists()
    assert (output / "payload.txt").read_text(encoding="utf-8") == "bound payload"
    assert (output / "collection-manifest.json").read_text(encoding="utf-8") == "{}"
