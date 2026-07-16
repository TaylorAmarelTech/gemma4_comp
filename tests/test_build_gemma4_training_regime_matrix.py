from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_gemma4_training_regime_matrix as matrix


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _run(root: Path, name: str, *, preference: bool, delta: float) -> Path:
    run = root / name
    (run / "adapter").mkdir(parents=True)
    (run / "adapter" / "adapter_model.safetensors").write_bytes(name.encode())
    (run / "train.jsonl").write_text('{"id":"train"}\n', encoding="utf-8")
    (run / "holdout.jsonl").write_text('{"id":"holdout"}\n', encoding="utf-8")
    if preference:
        (run / "preference.jsonl").write_text(
            '{"id":"preference"}\n', encoding="utf-8"
        )
    evaluation = {
        "id": "holdout",
        "prompt": "prompt",
        "reference": "reference",
        "base": {"response": "base"},
        "adapted": {"response": "adapted"},
    }
    (run / "evaluation.jsonl").write_text(
        json.dumps(evaluation) + "\n", encoding="utf-8"
    )
    metrics = {
        "training": {
            "steps": 2,
            "training_loss": 1.2,
            "runtime_seconds": 3.0,
            "trainable_parameters": 20,
            "total_parameters": 100,
            "log_history": [
                {"step": 1, "loss": 1.4, "learning_rate": 0.0001},
                {"step": 2, "loss": 1.0, "learning_rate": 0.00005},
            ],
        },
        "preference_training": {
            "completed": preference,
            "steps": 1 if preference else 0,
            "training_loss": 0.6 if preference else None,
            "runtime_seconds": 2.0 if preference else 0,
            "loss_type": "robust" if preference else None,
            "beta": 0.1 if preference else None,
            "label_smoothing": 0.05 if preference else None,
            "log_history": (
                [{"step": 1, "loss": 0.6, "rewards/accuracies": 1.0}]
                if preference
                else []
            ),
        },
        "evaluation": {
            "base_mean": {"objective_score": 0.4},
            "adapted_mean": {"objective_score": 0.4 + delta},
            "delta": {"objective_score": delta},
            "model_lift_demonstrated_on_locked_grounded_remix_holdout": delta > 0,
        },
        "memory": {"peak_training_allocated_bytes": 1234},
        "wall_clock_seconds": 9.0,
    }
    _json(run / "metrics.json", metrics)
    artifacts = {
        label: {"path": filename, "sha256": _sha256(run / filename)}
        for label, filename in (
            ("training_rows", "train.jsonl"),
            ("holdout_rows", "holdout.jsonl"),
            ("evaluation", "evaluation.jsonl"),
            ("metrics", "metrics.json"),
        )
    }
    if preference:
        artifacts["preference_rows"] = {
            "path": "preference.jsonl",
            "sha256": _sha256(run / "preference.jsonl"),
        }
    artifacts["adapter_files"] = {
        "adapter/adapter_model.safetensors": {
            "sha256": _sha256(run / "adapter" / "adapter_model.safetensors")
        }
    }
    manifest = {
        "experiment_id": name,
        "model": "gemma-test",
        "training_completed": True,
        "adapter_produced": True,
        "source_candidate_manifest_sha256": "a" * 64,
        "source_holdout_parent_sha256": ["b" * 64],
        "evaluation_config": {"rows": 1},
        "training_config": {
            "rows": 4,
            "steps": 2,
            "rank": 2,
            "lora_alpha": 4,
            "learning_rate": 0.0001,
            "lr_scheduler_type": "cosine",
            "finetune_attention_modules": True,
            "finetune_mlp_modules": False,
        },
        "preference_training_config": {
            "enabled": preference,
            "rows": 2 if preference else 0,
            "learning_rate": 0.00001 if preference else None,
        },
        "artifacts": artifacts,
    }
    _json(run / "run-manifest.json", manifest)
    return run


def test_build_matrix_preserves_matched_receipts_and_preference_curves(
    tmp_path: Path,
) -> None:
    first = _run(tmp_path, "supervised", preference=False, delta=0.1)
    second = _run(tmp_path, "hybrid", preference=True, delta=0.2)
    output = tmp_path / "matrix"

    result = matrix.build_matrix([first, second], output)

    assert result["run_count"] == 2
    assert len(result["matched_holdout_groups"]) == 1
    assert result["overview"][1]["preference_loss_type"] == "robust"
    assert (output / "training-regime-overview.csv").is_file()
    curves = (output / "learning-curve-points.csv").read_text(encoding="utf-8")
    assert "rewards/accuracies" in curves
    assert "preference" in curves


def test_build_matrix_rejects_unmatched_holdouts(tmp_path: Path) -> None:
    first = _run(tmp_path, "first", preference=False, delta=0.1)
    second = _run(tmp_path, "second", preference=False, delta=0.1)
    manifest = json.loads((second / "run-manifest.json").read_text(encoding="utf-8"))
    manifest["source_holdout_parent_sha256"] = ["c" * 64]
    _json(second / "run-manifest.json", manifest)

    try:
        matrix.build_matrix([first, second], tmp_path / "matrix")
    except matrix.MatrixError as exc:
        assert "no two runs share" in str(exc)
    else:
        raise AssertionError("expected unmatched holdout rejection")
