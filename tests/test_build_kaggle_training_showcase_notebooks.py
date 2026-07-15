from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kaggle_training_showcase_notebooks.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("kaggle_training_showcase", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_module()


def _collection(path: Path, *, dataset_id: str, safe_to_publish: bool) -> None:
    dataset = path / "dataset"
    dataset.mkdir(parents=True)
    (dataset / "release-manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "release_id": dataset_id.rsplit("/", 1)[-1] + "-test",
                "title": dataset_id.rsplit("/", 1)[-1].replace("-", " ").title(),
                "publication_state": (
                    "approved_public_ready" if safe_to_publish else "candidate_private"
                ),
                "safe_to_train": True,
                "safe_to_publish": safe_to_publish,
                "counts": {},
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


def _sources(path: Path) -> tuple[dict, str, str]:
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


@pytest.mark.parametrize("safe_to_publish", [False, True])
def test_builds_three_distinct_runnable_showcase_notebooks(
    tmp_path: Path, safe_to_publish: bool
) -> None:
    response = tmp_path / "response"
    large = tmp_path / "large"
    output = tmp_path / "showcase"
    response_id = "taylorsamarel/duecare-measured-response-training-corpus"
    large_id = "taylorsamarel/duecare-multiperspective-finetuning-corpus"
    _collection(response, dataset_id=response_id, safe_to_publish=safe_to_publish)
    _collection(large, dataset_id=large_id, safe_to_publish=safe_to_publish)

    manifest = builder.build(
        response_collection=response,
        large_collection=large,
        output=output,
        execute_local=False,
    )

    assert manifest["schema_version"] == "duecare.kaggle.training_showcase_notebooks.v1"
    assert manifest["public"] is safe_to_publish
    assert set(manifest["notebooks"]) == {
        "loading_quickstart",
        "cpu_response_quality_baseline",
        "training_data_quality_dashboard",
    }
    assert manifest["gemma_fine_tuning_completed"] is False
    assert manifest["adapter_produced"] is False
    assert manifest["independent_model_lift_demonstrated"] is False

    cases = {
        "loading_quickstart": {
            "datasets": [response_id, large_id],
            "phrases": [
                "Plain-language glossary",
                "quickstart_reproducible_flow.png",
                "KaggleDatasetAdapter",
                "load_dataset",
                "scan_ndjson",
            ],
        },
        "cpu_response_quality_baseline": {
            "datasets": [response_id],
            "phrases": [
                "Central processing unit (CPU)",
                "LogisticRegression",
                "response-quality-baseline-metrics.json",
            ],
        },
        "training_data_quality_dashboard": {
            "datasets": [response_id, large_id],
            "phrases": ["lineage-family", "quality_split_overlap_heatmaps.png"],
        },
    }
    for name, expected in cases.items():
        notebook_dir = output / name
        metadata = json.loads(
            (notebook_dir / "kernel-metadata.json").read_text(encoding="utf-8")
        )
        notebook_path = notebook_dir / "notebook.ipynb"
        notebook_bytes = notebook_path.read_bytes()
        assert all(byte < 128 for byte in notebook_bytes)
        notebook, code, markdown = _sources(notebook_path)
        combined = code + "\n" + markdown
        assert metadata["is_private"] is (not safe_to_publish)
        assert metadata["enable_gpu"] is False
        assert metadata["enable_internet"] is False
        assert metadata["dataset_sources"] == expected["datasets"]
        assert all(phrase in combined for phrase in expected["phrases"])
        assert all(cell.get("id") for cell in notebook["cells"])
        cell_ids = [cell["id"] for cell in notebook["cells"]]
        assert len(cell_ids) == len(set(cell_ids))
        assert len(notebook["cells"]) >= 8


def test_refuses_release_without_training_approval(tmp_path: Path) -> None:
    response = tmp_path / "response"
    large = tmp_path / "large"
    _collection(response, dataset_id="taylorsamarel/response-test", safe_to_publish=False)
    _collection(large, dataset_id="taylorsamarel/large-test", safe_to_publish=False)
    release_path = response / "dataset" / "release-manifest.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["safe_to_train"] = False
    release_path.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(ValueError, match="safe_to_train=true"):
        builder.build(
            response_collection=response,
            large_collection=large,
            output=tmp_path / "out",
            execute_local=False,
        )
