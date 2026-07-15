from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kaggle_training_release.py"
SPEC = importlib.util.spec_from_file_location("build_kaggle_training_release", SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


MODEL_REVISION = "a" * 40
ROW_LICENSE = "CC-BY-SA-4.0"
RIGHTS_HOLDER = "DueCare project contributors"
TARGET_MODEL_ID = "google/gemma-4-E2B-it"
MODEL_ROLE = "intended_finetuning_base_not_data_generator"
QUALITY_GATE_IDS = [
    "canonical_training_contract",
    "selection_contract",
    "pii_detector_clean",
    "all_deterministic_row_checks_pass",
    "dpo_prompt_matches_sft_scenario",
    "dpo_reject_is_unique_per_row",
    "dpo_reject_reflects_all_axes",
    "dpo_pairwise_length_ratio",
    "dpo_reject_no_repeated_paragraphs",
    "dpo_reject_single_controlled_failure",
    "mandatory_semantic_quality_checks_present",
    "heldout_near_duplicate",
    "official_source_reference_shape",
    "target_model_revision_pinned",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sft_row(*, row_id: str, prompt: str, lineage: str, split: str) -> dict:
    row = {
        "id": row_id,
        "messages": [
            {"role": "system", "content": "Answer directly with cited, safe next steps."},
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": (
                    "Pause the payment, preserve the written terms, and ask an independent worker-support "
                    "service to verify the demand against the cited source."
                ),
            },
        ],
        "source_profile": "full_harness",
        "rubric_targets": ["safety_non_uplift", "evidence_fidelity"],
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": lineage,
        "lineage_family_id": f"family-{lineage}",
        "split": split,
        "license": ROW_LICENSE,
        "rights_holder": RIGHTS_HOLDER,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "quality_gate": {
            "accepted": True,
            "unsafe_advice_filtered": True,
            "judge": "fixture",
        },
        "source_refs": ["ilo:forced-labour-indicators"],
        "knowledge_pack_refs": ["duecare-core@1"],
        "prompt_family": "recruitment-fees",
        "created_at": "2026-07-14T00:00:00+00:00",
        "target_model_id": TARGET_MODEL_ID,
        "model_role": MODEL_ROLE,
        "model_revision": MODEL_REVISION,
        "harness_version": "fixture-v1",
        "rubric_version": "fixture-v1",
        "metadata": {"runtime_trace": "removed by public release builder"},
    }
    row["sha256"] = release.training_row_sha256(row)
    return row


def _preference_row(*, row_id: str, prompt: str, lineage: str) -> dict:
    row = {
        "id": row_id,
        "prompt": prompt,
        "chosen": (
            "Pause the payment, preserve the written terms, and ask an independent worker-support "
            "service to verify the demand against the cited source."
        ),
        "rejected": (
            "Proceed only after independent verification; keep records and avoid sharing identity details "
            "until a trusted reviewer checks the request."
        ),
        "preference_rationale": "The chosen answer preserves evidence and adds a source-grounded safe action.",
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": lineage,
        "lineage_family_id": f"family-{lineage}",
        "split": "train",
        "license": ROW_LICENSE,
        "rights_holder": RIGHTS_HOLDER,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "quality_gate": {
            "accepted": True,
            "unsafe_advice_filtered": True,
            "judge": "fixture",
        },
        "source_refs": ["ilo:forced-labour-indicators"],
        "knowledge_pack_refs": ["duecare-core@1"],
        "created_at": "2026-07-14T00:00:00+00:00",
        "target_model_id": TARGET_MODEL_ID,
        "model_role": MODEL_ROLE,
        "model_revision": MODEL_REVISION,
        "harness_version": "fixture-v1",
        "rubric_version": "fixture-v1",
        "metadata": {"runtime_trace": "removed by public release builder"},
    }
    row["sha256"] = release.training_row_sha256(row)
    return row


def _bundle(tmp_path: Path, *, source_audit_clean: bool = True) -> tuple[Path, Path]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    train_prompts = [
        "A recruiter asks for an unreceipted fee before departure. What should I do?",
        "An employer wants to retain an identity document. What safe steps should I take?",
    ]
    validation_prompt = (
        "A contract changed after arrival. How should I preserve and verify the terms?"
    )
    test_prompt = (
        "A worker fears retaliation after questioning a deduction. What is a safe response?"
    )
    sft = [
        _sft_row(row_id=f"train-{i}", prompt=prompt, lineage=f"lineage-{i}", split="train")
        for i, prompt in enumerate(train_prompts, start=1)
    ]
    preference = [
        _preference_row(row_id=f"train-{i}", prompt=prompt, lineage=f"lineage-{i}")
        for i, prompt in enumerate(train_prompts, start=1)
    ]
    validation = [
        _sft_row(
            row_id="validation-1",
            prompt=validation_prompt,
            lineage="lineage-validation",
            split="validation",
        )
    ]
    test = [_sft_row(row_id="test-1", prompt=test_prompt, lineage="lineage-test", split="test")]
    heldout_hashes = sorted(
        release.canonical_sha256(prompt) for prompt in (validation_prompt, test_prompt)
    )
    heldout_lineages = ["lineage-test", "lineage-validation"]
    heldout_families = ["family-lineage-test", "family-lineage-validation"]
    prompt_hashes = sorted(
        release.canonical_sha256(prompt)
        for prompt in [*train_prompts, validation_prompt, test_prompt]
    )
    prompt_scope = {
        "scope_kind": "test_fixture",
        "scope_id": "fixture-prompts",
        "requested_count": 4,
        "prompt_count": 4,
        "prompt_sha256": release.canonical_sha256("\n".join(prompt_hashes)),
        "closure_status": "partial",
        "full_flywheel_closure": False,
        "closure_evidence_sha256": "",
        "job_complete": True,
    }

    artifacts = {
        "sft": bundle / "source_sft.jsonl",
        "dpo": bundle / "source_dpo.jsonl",
        "sft_validation": bundle / "source_validation.jsonl",
        "sft_test": bundle / "source_test.jsonl",
        "quarantine": bundle / "source_quarantine.json",
        "quality_audit": bundle / "quality_audit.json",
        "source_audit": bundle / "source_audit.json",
    }
    _write_jsonl(artifacts["sft"], sft)
    _write_jsonl(artifacts["dpo"], preference)
    _write_jsonl(artifacts["sft_validation"], validation)
    _write_jsonl(artifacts["sft_test"], test)
    _write_json(
        artifacts["quarantine"],
        {"schema_version": "1.0", "contains_raw_text": False, "rows": []},
    )
    _write_json(
        artifacts["quality_audit"],
        {
            "schema_version": "duecare.synthetic_quality_audit.v2",
            "audit_kind": "deterministic fixture audit",
            "clean": True,
            "risk_flags": [],
            "checks": {"fixture_rows_valid": True},
            "gates": [{"id": gate_id, "passed": True} for gate_id in QUALITY_GATE_IDS],
        },
    )
    quality_sha = _sha(artifacts["quality_audit"])
    _write_json(
        artifacts["source_audit"],
        {
            "schema_version": "1.0",
            "clean": source_audit_clean,
            "risk_flags": [] if source_audit_clean else ["review_pending"],
            "quality_audit_sha256": quality_sha,
            "prompt_scope": prompt_scope,
            "row_grounding": [],
        },
    )
    training_validation = release.validate_training_rows(
        sft,
        preference,
        evaluation_prompt_hashes=heldout_hashes,
        evaluation_lineage_ids=heldout_lineages,
        require_preference=True,
    )
    assert training_validation["ok"]
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": release.SOURCE_HANDOFF_KIND,
        "id": "fixture-training-bundle",
        "created_at": "2026-07-14T00:00:00+00:00",
        "generator_mode": "rubric_polisher",
        "harness_profile": "full_harness",
        "model": {"id": TARGET_MODEL_ID, "revision": MODEL_REVISION},
        "model_role": MODEL_ROLE,
        "source_scope": {"raw_publication_ingestion_by_default": False},
        "prompt_scope": prompt_scope,
        "safe_to_train": True,
        "training_validation": training_validation,
        "heldout_prompt_sha256": heldout_hashes,
        "heldout_lineage_ids": heldout_lineages,
        "heldout_lineage_family_ids": heldout_families,
        "reasoning_data_policy": "Final answers and deliberately authored visible rationales only.",
        "artifacts": {key: path.name for key, path in artifacts.items()},
        "artifact_sha256": {key: _sha(path) for key, path in artifacts.items()},
    }
    manifest_path = bundle / "source_manifest.json"
    _write_json(manifest_path, manifest)
    approval = {
        "schema_version": "1.0",
        "handoff_kind": release.APPROVAL_HANDOFF_KIND,
        "source_manifest_sha256": _sha(manifest_path),
        "approved_by": "curator-team",
        "approved_at": "2026-07-14T00:05:00+00:00",
        "rights_holder": RIGHTS_HOLDER,
        "row_license": ROW_LICENSE,
        "release_license": ROW_LICENSE,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "approvals": {
            "curator_approved": True,
            "privacy_approved": True,
            "license_approved": True,
            "quality_approved": True,
            "public_redistribution_approved": True,
        },
        "quality_audit": {
            "clean": True,
            "risk_flags": [],
            "artifact_sha256": quality_sha,
        },
        "prompt_scope": prompt_scope,
    }
    approval_path = bundle / "publication_approval.json"
    _write_json(approval_path, approval)
    return manifest_path, approval_path


def _rebind_approval(manifest_path: Path, approval_path: Path) -> None:
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["source_manifest_sha256"] = _sha(manifest_path)
    _write_json(approval_path, approval)


def test_builds_and_reverifies_manifest_bound_public_release(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    output = tmp_path / "release"

    result = release.build_release(
        manifest_path,
        approval_path=approval_path,
        output_dir=output,
        min_sft_rows=2,
        min_preference_rows=2,
    )

    assert result["safe_to_publish"] is True
    assert result["release_tier"] == "preview"
    assert result["counts"]["sft_train"] == 2
    assert release.verify_release_dir(output)["ok"] is True
    public_row = json.loads(
        (output / "sft_train.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert "metadata" not in public_row
    assert public_row["allow_training_use"] is True
    assert public_row["allow_public_redistribution"] is True
    assert public_row["target_model_id"] == TARGET_MODEL_ID
    assert public_row["model_role"] == MODEL_ROLE
    assert public_row["sha256"] == release.training_row_sha256(public_row)
    preference_row = json.loads(
        (output / "preference_train.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert preference_row["synthetic"] is True
    assert preference_row["target_model_id"] == TARGET_MODEL_ID
    assert preference_row["model_role"] == MODEL_ROLE
    assert result["heldout_lineage_family_ids"] == [
        "family-lineage-test",
        "family-lineage-validation",
    ]


def test_requires_manifest_bound_publication_approval(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["source_manifest_sha256"] = "0" * 64
    _write_json(approval_path, approval)

    with pytest.raises(release.ReleaseError, match="not bound"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_dirty_source_audit(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path, source_audit_clean=False)

    with pytest.raises(release.ReleaseError, match="source audit is not clean"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_requires_human_approval_to_bind_the_actual_quality_audit(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    quality_path = manifest_path.parent / manifest["artifacts"]["quality_audit"]
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["checks"]["additional_check"] = True
    _write_json(quality_path, quality)
    changed_quality_sha = _sha(quality_path)
    manifest["artifact_sha256"]["quality_audit"] = changed_quality_sha

    source_audit_path = manifest_path.parent / manifest["artifacts"]["source_audit"]
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    source_audit["quality_audit_sha256"] = changed_quality_sha
    _write_json(source_audit_path, source_audit)
    manifest["artifact_sha256"]["source_audit"] = _sha(source_audit_path)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="approval is not bound"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_unpinned_model_revision_even_with_rehashed_source(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sft_path = manifest_path.parent / manifest["artifacts"]["sft"]
    rows = [json.loads(line) for line in sft_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["model_revision"] = "main"
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(sft_path, rows)
    manifest["artifact_sha256"]["sft"] = _sha(sft_path)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="unpinned model revision"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_row_model_metadata_drift_even_when_rehashed_source(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preference_path = manifest_path.parent / manifest["artifacts"]["dpo"]
    rows = [json.loads(line) for line in preference_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["target_model_id"] = "google/gemma-4-E4B-it"
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(preference_path, rows)
    manifest["artifact_sha256"]["dpo"] = _sha(preference_path)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="target model metadata"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_hidden_reasoning_markup(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sft_path = manifest_path.parent / manifest["artifacts"]["sft"]
    rows = [json.loads(line) for line in sft_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["messages"][-1]["content"] = "<think>private scratch work</think> Safe answer."
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(sft_path, rows)
    manifest["artifact_sha256"]["sft"] = _sha(sft_path)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="hidden-reasoning"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_reverify_detects_row_tampering_even_when_file_map_is_rehashed(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    output = tmp_path / "release"
    release.build_release(
        manifest_path,
        approval_path=approval_path,
        output_dir=output,
        min_sft_rows=2,
        min_preference_rows=2,
    )
    sft_path = output / "sft_train.jsonl"
    rows = [json.loads(line) for line in sft_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["allow_training_use"] = False
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(sft_path, rows)
    release_manifest_path = output / "release-manifest.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    release_manifest["files"]["sft_train.jsonl"]["sha256"] = _sha(sft_path)
    release_manifest["files"]["sft_train.jsonl"]["bytes"] = sft_path.stat().st_size
    _write_json(release_manifest_path, release_manifest)

    with pytest.raises(release.ReleaseError, match="training-use permission"):
        release.verify_release_dir(output)


def test_blocks_declared_heldout_superset(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["heldout_prompt_sha256"].append("b" * 64)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="exactly match"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_declared_heldout_family_superset(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["heldout_lineage_family_ids"].append("family-not-present")
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="family ids do not exactly match"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_source_train_validation_family_leak_even_when_rehashed(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation_path = manifest_path.parent / manifest["artifacts"]["sft_validation"]
    rows = [json.loads(line) for line in validation_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["lineage_family_id"] = "family-lineage-1"
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(validation_path, rows)
    manifest["artifact_sha256"]["sft_validation"] = _sha(validation_path)
    manifest["heldout_lineage_family_ids"] = ["family-lineage-1", "family-lineage-test"]
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="train and validation lineage families overlap"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_blocks_source_sft_preference_family_mismatch_by_row_id(tmp_path: Path) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preference_path = manifest_path.parent / manifest["artifacts"]["dpo"]
    rows = [json.loads(line) for line in preference_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["lineage_family_id"] = "family-different"
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(preference_path, rows)
    manifest["artifact_sha256"]["dpo"] = _sha(preference_path)
    _write_json(manifest_path, manifest)
    _rebind_approval(manifest_path, approval_path)

    with pytest.raises(release.ReleaseError, match="do not match by row id"):
        release.build_release(
            manifest_path,
            approval_path=approval_path,
            output_dir=tmp_path / "release",
            min_sft_rows=2,
            min_preference_rows=2,
        )


def test_reverify_blocks_family_leak_even_when_rows_and_manifest_are_rehashed(
    tmp_path: Path,
) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    output = tmp_path / "release"
    release.build_release(
        manifest_path,
        approval_path=approval_path,
        output_dir=output,
        min_sft_rows=2,
        min_preference_rows=2,
    )
    validation_path = output / "sft_validation.jsonl"
    rows = [json.loads(line) for line in validation_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["lineage_family_id"] = "family-lineage-1"
    rows[0]["sha256"] = release.training_row_sha256(rows[0])
    _write_jsonl(validation_path, rows)
    release_manifest_path = output / "release-manifest.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    release_manifest["heldout_lineage_family_ids"] = [
        "family-lineage-1",
        "family-lineage-test",
    ]
    release_manifest["files"]["sft_validation.jsonl"]["sha256"] = _sha(validation_path)
    release_manifest["files"]["sft_validation.jsonl"]["bytes"] = validation_path.stat().st_size
    _write_json(release_manifest_path, release_manifest)

    with pytest.raises(release.ReleaseError, match="train and validation lineage families overlap"):
        release.verify_release_dir(output)


def test_reverify_blocks_internal_file_symlink_before_resolving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, approval_path = _bundle(tmp_path)
    output = tmp_path / "release"
    release.build_release(
        manifest_path,
        approval_path=approval_path,
        output_dir=output,
        min_sft_rows=2,
        min_preference_rows=2,
    )
    link_path = output / "DATA_CARD.md"
    link_path.unlink()
    try:
        os.symlink("dataset-metadata.json", link_path)
    except OSError:
        original_is_symlink = Path.is_symlink
        original_resolve = Path.resolve

        def _is_internal_link(path: Path) -> bool:
            return path == link_path or original_is_symlink(path)

        def _guarded_resolve(path: Path, *args, **kwargs):
            if path == link_path:
                raise AssertionError("declared symlink was resolved before rejection")
            return original_resolve(path, *args, **kwargs)

        monkeypatch.setattr(Path, "is_symlink", _is_internal_link)
        monkeypatch.setattr(Path, "resolve", _guarded_resolve)
    else:
        if not link_path.is_symlink():
            pytest.fail("file symlink creation was not retained by this filesystem")
        target = output / "dataset-metadata.json"
        release_manifest_path = output / "release-manifest.json"
        release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        release_manifest["files"]["DATA_CARD.md"]["sha256"] = _sha(target)
        release_manifest["files"]["DATA_CARD.md"]["bytes"] = target.stat().st_size
        _write_json(release_manifest_path, release_manifest)

    with pytest.raises(release.ReleaseError, match="must not be a symlink"):
        release.verify_release_dir(output)
