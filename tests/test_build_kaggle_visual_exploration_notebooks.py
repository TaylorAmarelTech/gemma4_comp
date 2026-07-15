from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kaggle_visual_exploration_notebooks.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("kaggle_visual_notebooks", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_module()


def _release(collection: Path, *, dataset_id: str, release_id: str) -> None:
    dataset = collection / "dataset"
    dataset.mkdir(parents=True)
    (dataset / "release-manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "release_id": release_id,
                "publication_state": "candidate_private",
                "safe_to_train": True,
                "safe_to_publish": False,
                "claims": {
                    "training_completed": False,
                    "adapter_produced": False,
                    "model_lift_demonstrated": False,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    collection_schema = (
        "duecare.kaggle.response-training-local-collection.v1"
        if "response" in dataset_id
        else "duecare.kaggle.large_training_collection.v1"
    )
    (collection / "collection-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": collection_schema,
                "safe_to_train": True,
                "safe_to_publish": False,
                "notebooks": {},
                "artifacts": {},
                "manifest_payload_sha256": "0" * 64,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _notebook_source(path: Path) -> tuple[dict, str, str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source") or [])
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    markdown = "\n".join(
        "".join(cell.get("source") or [])
        for cell in notebook["cells"]
        if cell.get("cell_type") == "markdown"
    )
    compile(code, str(path), "exec")
    return notebook, code, markdown


def test_builds_professional_private_visual_notebooks_and_output_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = tmp_path / "reports" / "response"
    large = tmp_path / "reports" / "large"
    _release(
        response,
        dataset_id="taylorsamarel/duecare-measured-response-training-corpus",
        release_id="response-test",
    )
    _release(
        large,
        dataset_id="taylorsamarel/duecare-multiperspective-finetuning-corpus",
        release_id="large-test",
    )
    monkeypatch.setattr(builder, "ROOT", tmp_path)

    manifest = builder.build(
        response_collection=response,
        large_collection=large,
        execute_local=False,
    )

    assert manifest["schema_version"] == "duecare.kaggle.visual_notebooks.v2"
    assert manifest["notebook_role"] == "kaggle_hackathon_learning_and_dataset_review"
    assert manifest["training_completed"] is False
    assert manifest["adapter_produced"] is False
    assert manifest["model_lift_demonstrated"] is False
    assert set(manifest["notebooks"]["response_visual_explorer"]["expected_charts"]) == set(
        builder.RESPONSE_EXPECTED_CHARTS
    )
    assert set(manifest["notebooks"]["large_visual_explorer"]["expected_charts"]) == set(
        builder.LARGE_EXPECTED_CHARTS
    )
    assert (
        len(manifest["notebooks"]["response_visual_explorer"]["collection_manifest_sha256"])
        == 64
    )
    assert (
        len(manifest["notebooks"]["large_visual_explorer"]["collection_manifest_sha256"])
        == 64
    )

    cases = (
        (
            response / "notebooks" / "visual_explorer",
            "taylorsamarel/duecare-measured-response-training-corpus",
            builder.RESPONSE_EXPECTED_CHARTS,
            "response-visual-report.md",
            (
                "response_rows_by_lane.png",
                "response_dimension_lift.png",
                "response_audit_population.png",
            ),
        ),
        (
            large / "notebooks" / "visual_explorer",
            "taylorsamarel/duecare-multiperspective-finetuning-corpus",
            builder.LARGE_EXPECTED_CHARTS,
            "large-visual-report.md",
            (
                "large_rows_by_lane.png",
                "large_perspective_journey_heatmap.png",
                "large_text_lengths.png",
            ),
        ),
    )
    for notebook_dir, dataset_id, expected_charts, report_name, required_literals in cases:
        metadata = json.loads((notebook_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
        notebook, code, markdown = _notebook_source(notebook_dir / "notebook.ipynb")
        assert metadata["is_private"] is True
        assert metadata["enable_gpu"] is False
        assert metadata["enable_internet"] is False
        assert metadata["dataset_sources"] == [dataset_id]
        assert metadata["keywords"] == ["nlp"]
        assert "Gemma 4 Good Hackathon learning notebook" in markdown
        assert "Training completed: false" in code
        assert report_name in code
        assert all(name in code for name in required_literals)
        assert len(expected_charts) >= 10
        assert all(cell.get("id") for cell in notebook["cells"])


def test_refuses_visual_notebook_generation_without_training_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = tmp_path / "response"
    large = tmp_path / "large"
    _release(response, dataset_id="taylorsamarel/response-test", release_id="response-test")
    _release(large, dataset_id="taylorsamarel/large-test", release_id="large-test")
    response_release = response / "dataset" / "release-manifest.json"
    value = json.loads(response_release.read_text(encoding="utf-8"))
    value["safe_to_train"] = False
    response_release.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(builder, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="safe_to_train=true"):
        builder.build(
            response_collection=response,
            large_collection=large,
            execute_local=False,
        )
