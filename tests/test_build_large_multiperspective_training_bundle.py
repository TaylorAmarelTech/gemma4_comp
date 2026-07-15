from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_large_multiperspective_training_bundle.py"


def _load():
    spec = importlib.util.spec_from_file_location("large_multiperspective", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


large = _load()


def _descriptor_for_failure(failure_key: str) -> dict[str, str]:
    return next(
        row
        for row in large.base.enumerate_descriptors()
        if row["split"] == "train" and large.controlled_failure(row)["key"] == failure_key
    )


def test_default_plan_is_large_sharded_bounded_and_candidate_only() -> None:
    plan = large.build_plan(
        train_rows=large.DEFAULT_TRAIN_ROWS,
        validation_rows=large.DEFAULT_VALIDATION_ROWS,
        test_rows=large.DEFAULT_TEST_ROWS,
        shard_rows=large.DEFAULT_SHARD_ROWS,
    )

    assert plan["mode"] == "plan_only_no_files_written"
    assert plan["requested_rows"] == {
        "sft_train": 25_600,
        "preference_train": 25_600,
        "sft_validation": 2_048,
        "sft_test": 2_048,
    }
    assert plan["shards"] == {
        "sft_train": 13,
        "preference_train": 13,
        "sft_validation": 1,
        "sft_test": 1,
    }
    assert plan["unique_training_target_bodies_expected"] == 51_200
    assert set(plan["response_styles"]) == set(large.STYLE_BY_KEY)
    assert plan["publication_status"] == "candidate_only_not_approved"
    assert "one at a time" in plan["bounded_memory"]


def test_blinded_pairs_are_length_balanced_and_change_one_declared_section() -> None:
    seen_styles: set[str] = set()
    for mode in large.base.FAILURE_MODES:
        descriptor = _descriptor_for_failure(mode["key"])
        sft = large._style_sft_row(descriptor)
        preference, pair_audit = large._style_preference_row(descriptor, sft)
        seen_styles.add(preference["response_style"])

        assert preference["pair_design"] == "blinded_length_balanced_single_section_minimal_pair"
        assert preference["controlled_failure"] == mode["key"]
        assert preference["changed_section"] == large.FAILURE_SECTION[mode["key"]]
        assert pair_audit["changed_sections"] == [large.FAILURE_SECTION[mode["key"]]]
        assert 0.90 <= pair_audit["length_ratio"] <= 1.10
        assert pair_audit["cue_findings"] == []
        assert pair_audit["passed"] is True
        assert preference["quality_gate"]["accepted"] is True
        assert preference["sha256"] == large.base.training_row_sha256(preference)

    # The old deterministic reject markers are detected and therefore cannot
    # silently re-enter the scaled candidate.
    descriptor = _descriptor_for_failure("unsupported_certainty")
    old_reject = large.base._rejected_answer(descriptor, large.base._chosen_answer(descriptor))
    assert large._target_cue_findings(old_reject)
    assert seen_styles


def test_small_streaming_candidate_is_manifest_bound_and_deterministic(tmp_path: Path) -> None:
    kwargs = {
        "train_rows": 224,
        "validation_rows": 64,
        "test_rows": 64,
        "shard_rows": 64,
        "_minimum_train_rows": 224,
    }
    first = tmp_path / "first"
    second = tmp_path / "second"
    summary = large.build_candidate(first, **kwargs)
    large.build_candidate(second, **kwargs)

    assert summary["quality_audit_clean"] is True
    assert summary["safe_to_train"] is True
    assert summary["safe_to_publish"] is False
    assert summary["publication_status"] == "candidate_only_not_approved"
    assert summary["counts"]["expected_distinct_target_bodies"] == 576
    assert not (first / "BUILD_FAILED.json").exists()
    assert large.verify_candidate_dir(first)["ok"] is True

    manifest = json.loads((first / "candidate-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == large.SCHEMA_VERSION
    assert manifest["safe_to_publish"] is False
    assert manifest["text_body_accounting"] == {
        "unique_sft_targets": 224,
        "preference_chosen_reuses_sft_targets": 224,
        "unique_preference_rejects": 224,
        "unique_heldout_targets": 128,
        "serialized_target_slots": 800,
    }
    assert set(manifest["artifacts"]["shards"]) == {
        "sft_train",
        "preference_train",
        "sft_validation",
        "sft_test",
    }
    assert len(manifest["artifacts"]["shards"]["sft_train"]) == 4
    assert len(manifest["artifacts"]["shards"]["preference_train"]) == 4

    audit = json.loads((first / "quality-audit.json").read_text(encoding="utf-8"))
    assert audit["clean"] is True
    assert all(gate["passed"] for gate in audit["gates"])
    assert set(audit["style_counts"]["sft_train"]) == set(large.STYLE_BY_KEY)
    length_gate = next(gate for gate in audit["gates"] if gate["id"] == "dpo_pairwise_length_ratio")
    assert 0.90 <= length_gate["min"] <= length_gate["max"] <= 1.10

    first_files = {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_verifier_detects_shard_tampering(tmp_path: Path) -> None:
    output = tmp_path / "candidate"
    large.build_candidate(
        output,
        train_rows=224,
        validation_rows=64,
        test_rows=64,
        shard_rows=64,
        _minimum_train_rows=224,
    )
    manifest = json.loads((output / "candidate-manifest.json").read_text(encoding="utf-8"))
    shard = output / manifest["artifacts"]["shards"]["sft_train"][0]["path"]
    shard.write_bytes(shard.read_bytes() + b"\n")

    result = large.verify_candidate_dir(output)
    assert result["ok"] is False
    assert any(failure.startswith("shard_integrity:sft_train") for failure in result["failures"])
