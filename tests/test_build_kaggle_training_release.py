from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kaggle_training_release.py"
SPEC = importlib.util.spec_from_file_location("build_kaggle_training_release", SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


MODEL_REVISION = "a" * 40
QUALITY_SHA = "f" * 64
ROW_LICENSE = "CC-BY-SA-4.0"
RIGHTS_HOLDER = "DueCare project contributors"


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
        "pii_checked": True,
        "lineage_id": lineage,
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
    validation_prompt = "A contract changed after arrival. How should I preserve and verify the terms?"
    test_prompt = "A worker fears retaliation after questioning a deduction. What is a safe response?"
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
    test = [
        _sft_row(row_id="test-1", prompt=test_prompt, lineage="lineage-test", split="test")
    ]
    heldout_hashes = sorted(
        release.canonical_sha256(prompt) for prompt in (validation_prompt, test_prompt)
    )
    heldout_lineages = ["lineage-test", "lineage-validation"]
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
        artifacts["source_audit"],
        {
            "schema_version": "1.0",
            "clean": source_audit_clean,
            "risk_flags": [] if source_audit_clean else ["review_pending"],
            "approvals": {
                "curator_approved": source_audit_clean,
                "privacy_approved": source_audit_clean,
                "license_approved": source_audit_clean,
            },
            "quality_audit_sha256": QUALITY_SHA,
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
        "model": {"id": "google/gemma-4-E2B-it", "revision": MODEL_REVISION},
        "source_scope": {"raw_publication_ingestion_by_default": False},
        "prompt_scope": prompt_scope,
        "safe_to_train": True,
        "training_validation": training_validation,
        "heldout_prompt_sha256": heldout_hashes,
        "heldout_lineage_ids": heldout_lineages,
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
        "quality_audit": {"clean": True, "risk_flags": [], "artifact_sha256": QUALITY_SHA},
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
    public_row = json.loads((output / "sft_train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "metadata" not in public_row
    assert public_row["allow_training_use"] is True
    assert public_row["allow_public_redistribution"] is True
    assert public_row["sha256"] == release.training_row_sha256(public_row)


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
