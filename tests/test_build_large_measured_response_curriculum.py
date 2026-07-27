from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_large_measured_response_curriculum.py"


def _load():
    spec = importlib.util.spec_from_file_location("large_measured_review_curriculum", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parent(split: str, index: int) -> dict:
    row = {
        "id": f"parent-{split}-{index}",
        "split": split,
        "lineage_family_id": f"family-{split}-{index}",
        "messages": [
            {
                "role": "user",
                "content": (
                    "How should a worker review a disputed record "
                    f"{split}-{index}?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Separate the account from the record, preserve uncertainty, "
                    "ask what outcome is safest, and verify current authority "
                    "before acting."
                ),
            },
        ],
        "quality_evidence": {
            "baseline_mean_score_0_100": 55.0,
            "target_mean_score_0_100": 88.0,
            "score_lift": 33.0,
            "baseline_components": {"A": 10.0, "B": 8.0, "C": 12.0, "D": 6.0, "E": 7.0},
            "target_components": {"A": 22.0, "B": 18.0, "C": 24.0, "D": 13.0, "E": 13.0},
        },
        "quality_evidence_sha256": "a" * 64,
        "source_response_sha256": {"teacher": "b" * 64, "baseline": "c" * 64},
        "source_refs": ["repo:synthetic-test"],
        "pii_checked": True,
        "quality_gate": {"accepted": True},
    }
    row["sha256"] = builder.training_row_sha256(row)
    return row


def _source_release(tmp_path: Path) -> Path:
    dataset = tmp_path / "dataset"
    dataset.mkdir(parents=True)
    lane_rows = {
        "sft_positive_train": [_parent("train", 0), _parent("train", 1)],
        "sft_positive_validation": [_parent("validation", 0)],
        "sft_positive_test": [_parent("test", 0)],
    }
    lane_rows.update(
        {
            name.replace("sft_positive", "dpo_preference"): [
                {
                    "id": row["id"].replace("parent-", "preference-"),
                    "split": row["split"],
                    "lineage_id": f"response-pair:{row['id']}:dpo",
                    "prompt": row["messages"][0]["content"],
                    "chosen": row["messages"][1]["content"],
                    "rejected": "Ignore the record boundaries and act immediately.",
                }
                for row in rows
            ]
            for name, rows in list(lane_rows.items())
        }
    )
    for rows in lane_rows.values():
        for row in rows:
            if "messages" in row:
                row["lineage_id"] = f"response-pair:{row['id']}:sft"
    lanes = {}
    for lane, rows in lane_rows.items():
        path = dataset / f"{lane}.jsonl"
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        lanes[lane] = {
            "kind": lane.rsplit("_", 1)[0],
            "split": rows[0]["split"],
            "rows": len(rows),
            "shards": [
                {
                    "path": path.name,
                    "rows": len(rows),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            ],
        }
    (dataset / "shard-index.json").write_text(
        json.dumps({"lanes": lanes}), encoding="utf-8"
    )
    release = {
        "schema_version": "duecare.kaggle.response-training-release.v1",
        "dataset_id": "test/measured-response",
        "publication_state": "approved_public_ready",
        "safe_to_train": True,
        "safe_to_publish": True,
        "release_manifest_payload_sha256": "d" * 64,
        "publication_approval": {
            "approvals": {
                "curator_approved": True,
                "privacy_approved": True,
                "license_approved": True,
                "public_redistribution_approved": True,
            }
        },
    }
    release_path = dataset / "release-manifest.json"
    release_path.write_text(json.dumps(release), encoding="utf-8")
    return release_path


def test_plan_exposes_parent_and_descendant_accounting(tmp_path: Path) -> None:
    source = _source_release(tmp_path)
    plan = builder.build_plan(source)

    assert plan["parent_counts"] == {"train": 2, "validation": 1, "test": 1}
    assert plan["view_matrix"]["total_combinations"] == 320
    assert plan["counts"] == {
        "supervised_train": 640,
        "preference_train": 640,
        "supervised_validation": 8,
        "supervised_test": 8,
    }
    assert "not independent human judgments" in plan["independence_warning"]


def test_small_candidate_is_deterministic_lineage_bound_and_verified(tmp_path: Path) -> None:
    source = _source_release(tmp_path / "source")
    kwargs = {
        "train_views_per_parent": 8,
        "heldout_views_per_parent": 2,
        "shard_rows": 5,
        "minimum_train_rows": 16,
    }
    first = tmp_path / "first"
    second = tmp_path / "second"
    summary = builder.build_candidate(source, first, **kwargs)
    builder.build_candidate(source, second, **kwargs)

    assert summary["safe_to_train"] is True
    assert summary["safe_to_publish"] is False
    assert summary["counts"]["supervised_train"] == 16
    assert summary["counts"]["preference_train"] == 16
    assert builder.verify_candidate_dir(first)["ok"] is True

    manifest = json.loads((first / "candidate-manifest.json").read_text(encoding="utf-8"))
    assert manifest["augmentation_accounting"]["independent_observation"] is False
    assert (
        "cannot support independent model-improvement claims"
        in manifest["contamination_boundary"]
    )

    first_shard = manifest["artifacts"]["shards"]["supervised_train"][0]["path"]
    first_row = json.loads(
        next((first / first_shard).open(encoding="utf-8"))
    )
    assert first_row["parent_row_sha256"]
    assert first_row["parent_lineage_family_id"].startswith("family-train-")
    assert first_row["independent_observation"] is False
    assert first_row["quality_gate"]["accepted"] is True
    assert first_row["sha256"] == builder.training_row_sha256(first_row)

    def hashes(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): _sha256(path)
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    assert hashes(first) == hashes(second)


def test_source_must_be_approved_for_public_redistribution(tmp_path: Path) -> None:
    source = _source_release(tmp_path)
    release = json.loads(source.read_text(encoding="utf-8"))
    release["safe_to_publish"] = False
    source.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(builder.CurriculumError, match="approved for training"):
        builder.build_plan(source)
