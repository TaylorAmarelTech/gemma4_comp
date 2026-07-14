from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "import_training_candidates.py"
SPEC = importlib.util.spec_from_file_location("import_training_candidates", SCRIPT)
assert SPEC and SPEC.loader
candidate_import = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate_import)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(data_file: str, expected_sha: str) -> dict:
    return {
        "id": "fixture-visible-rationales",
        "enabled": True,
        "source_type": "local_jsonl",
        "dataset_id": "fixture/visible-rationales",
        "revision": "fixture-v1",
        "data_file": data_file,
        "expected_sha256": expected_sha,
        "license": "CC-BY-4.0",
        "terms_url": "https://example.invalid/dataset-terms",
        "rights_holder": "Fixture authors",
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "reasoning_policy": candidate_import.REASONING_POLICY,
        "rationale_visibility": "explicitly_public",
        "fields": {
            "id": "row_id",
            "prompt": "question",
            "answer": "answer",
            "visible_rationale": "public_rationale",
            "source_refs": "citations",
        },
        "max_rows": 10,
    }


def _fixture_file(tmp_path: Path) -> Path:
    source_root = tmp_path / "source"
    source_root.mkdir()
    path = source_root / "rows.jsonl"
    rows = [
        {
            "row_id": "row-1",
            "question": "How should a worker verify an unexpected fee?",
            "answer": "Pause, preserve the written demand, and verify it against the cited public source.",
            "public_rationale": "The answer preserves evidence and avoids unsupported operational advice.",
            "citations": ["public-source:1"],
        },
        {
            "row_id": "row-2",
            "question": "Contact worker@example.invalid about this case.",
            "answer": "<think>private scratchpad</think> Publish the internal notes.",
            "public_rationale": "Not actually public.",
            "citations": [],
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_imports_visible_answer_candidates_and_quarantines_raw_text_free(tmp_path: Path) -> None:
    source_file = _fixture_file(tmp_path)
    source = _source(source_file.name, _sha(source_file))
    output = tmp_path / "output"

    manifest = candidate_import.run_import(
        source,
        output_dir=output,
        local_source_root=source_file.parent,
    )

    assert manifest["safe_to_train"] is False
    assert manifest["raw_source_retained"] is False
    assert manifest["counts"] == {"candidate": 1, "quarantined": 1}
    candidate = json.loads((output / "candidates.jsonl").read_text(encoding="utf-8"))
    assert candidate["final_answer"].startswith("Pause")
    assert candidate["visible_rationale"].startswith("The answer")
    assert candidate["candidate_status"].startswith("pending_")
    assert candidate["safe_to_train"] is False
    quarantine = json.loads((output / "quarantine.json").read_text(encoding="utf-8"))
    assert quarantine["contains_raw_text"] is False
    assert "worker@example.invalid" not in json.dumps(quarantine)
    assert "private scratchpad" not in json.dumps(quarantine)
    assert {"pii_email", "hidden_reasoning"} <= set(quarantine["rows"][0]["reason_codes"])


def test_registry_requires_immutable_huggingface_revision() -> None:
    source = _source("rows.jsonl", "a" * 64)
    source["source_type"] = "huggingface_jsonl"
    source["dataset_id"] = "owner/dataset"
    source["revision"] = "main"

    with pytest.raises(candidate_import.ImportBlocked, match="immutable commit"):
        candidate_import.validate_source(source)


def test_kaggle_import_downloads_the_declared_version_and_file(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "fixture.jsonl"
    payload.write_text('{"row_id":"one"}\n', encoding="utf-8")
    source = _source("nested/rows.jsonl", _sha(payload))
    source["source_type"] = "kaggle_dataset_file"
    source["dataset_id"] = "owner/dataset"
    source["revision"] = 7
    source = candidate_import.validate_source(source)
    observed: dict[str, object] = {}

    def dataset_download(handle, *, path, output_dir, force_download):
        observed.update(
            handle=handle,
            path=path,
            output_dir=output_dir,
            force_download=force_download,
        )
        destination = Path(output_dir) / "nested" / "rows.jsonl"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(payload.read_bytes())
        return str(destination)

    monkeypatch.setitem(sys.modules, "kagglehub", SimpleNamespace(dataset_download=dataset_download))
    target = tmp_path / "downloaded.jsonl"
    candidate_import.acquire_source_file(
        source,
        target=target,
        local_source_root=None,
        kaggle_bin=None,
        max_download_bytes=1024,
    )

    assert target.read_bytes() == payload.read_bytes()
    assert observed["handle"] == "owner/dataset/versions/7"
    assert observed["path"] == "nested/rows.jsonl"
    assert observed["force_download"] is True
    assert Path(str(observed["output_dir"])).name.startswith("duecare-kaggle-import-")


def test_registry_blocks_private_reasoning_field_mapping() -> None:
    source = _source("rows.jsonl", "a" * 64)
    source["fields"]["visible_rationale"] = "private_chain_of_thought"

    with pytest.raises(candidate_import.ImportBlocked, match="private reasoning"):
        candidate_import.validate_source(source)


def test_registry_requires_training_and_redistribution_grants() -> None:
    source = _source("rows.jsonl", "a" * 64)
    source["allow_public_redistribution"] = False

    with pytest.raises(candidate_import.ImportBlocked, match="public redistribution"):
        candidate_import.validate_source(source)


def test_cli_dry_run_validates_registry_without_downloading(tmp_path: Path, capsys) -> None:
    source_file = _fixture_file(tmp_path)
    source = _source(source_file.name, _sha(source_file))
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"schema_version": "1.0", "sources": [source]}),
        encoding="utf-8",
    )

    rc = candidate_import.main(
        [
            "--registry",
            str(registry),
            "--source-id",
            source["id"],
            "--dry-run",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["safe_to_train"] is False
    assert payload["revision"] == "fixture-v1"
