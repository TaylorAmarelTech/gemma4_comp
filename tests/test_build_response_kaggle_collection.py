from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_response_kaggle_collection.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("response_kaggle_collection", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_module()
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
).strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(value: dict) -> dict:
    result = dict(value)
    result["sha256"] = builder._canonical_sha256(result)
    return result


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> dict:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    return {
        "bytes": path.stat().st_size,
        "rows": len(rows),
        "sha256": _sha256_file(path),
    }


def _common(split: str, index: int, chosen: str, rejected: str) -> dict:
    prompt = f"Protective worker-centred prompt {index}"
    prompt_id_sha256 = hashlib.sha256(f"PROMPT-{index}".encode()).hexdigest()
    baseline_components = {"A": 5.0, "B": 2.0, "C": 5.0, "D": 2.0, "E": 1.0}
    target_components = {"A": 20.0, "B": 15.0, "C": 20.0, "D": 12.0, "E": 13.0}
    dimensions = {
        "A": "indicator_identification",
        "B": "legal_grounding",
        "C": "protective_refusal",
        "D": "concrete_resources_and_actions",
        "E": "safety_and_privacy",
    }
    quality_evidence = {
        "gate_version": "test-complete-bounded-grades-v1",
        "complete_bounded_components": True,
        "component_bounds": builder.COMPONENT_BOUNDS,
        "baseline_arm": "baseline",
        "teacher_arm": "harness_core",
        "baseline_mean_score_0_100": 15.0,
        "target_mean_score_0_100": 80.0,
        "score_lift": 65.0,
        "baseline_components": baseline_components,
        "target_components": target_components,
        "failure_dimension_deltas": [
            {
                "dimension_id": component,
                "dimension": dimensions[component],
                "baseline": baseline_components[component],
                "target": target_components[component],
                "delta": target_components[component] - baseline_components[component],
            }
            for component in "ABCDE"
        ],
        "grounding_delta": 38.0,
        "judge_provenance": {
            "baseline": [
                {
                    "judge": "test-judge",
                    "judge_sha256": "8" * 64,
                    "score_0_100": 15.0,
                    "components": baseline_components,
                }
            ],
            "target": [
                {
                    "judge": "test-judge",
                    "judge_sha256": "8" * 64,
                    "score_0_100": 80.0,
                    "components": target_components,
                }
            ],
        },
        "thresholds": {
            "min_target": 70.0,
            "min_lift": 20.0,
            "min_grounding": 24.0,
            "min_cite": 4.0,
            "min_grounding_delta": 2.0,
        },
        "source_grade_key_binding": {
            "model": "gemma4:test",
            "prompt_id_sha256": prompt_id_sha256,
            "baseline_arm": "baseline",
            "teacher_arm": "harness_core",
            "method": builder.GRADE_BINDING_METHOD,
        },
    }
    quality_evidence["evidence_sha256"] = builder._quality_evidence_sha256(
        quality_evidence
    )
    source_response_sha256 = {
        "baseline": hashlib.sha256(rejected.encode()).hexdigest(),
        "teacher": hashlib.sha256(chosen.encode()).hexdigest(),
    }
    training_response_sha256 = {
        "chosen": hashlib.sha256(chosen.encode()).hexdigest(),
        "rejected": hashlib.sha256(rejected.encode()).hexdigest(),
    }
    grade_evidence_binding_sha256 = builder._canonical_sha256(
        {
            "quality_evidence_sha256": quality_evidence["evidence_sha256"],
            "source_response_sha256": source_response_sha256,
            "training_response_sha256": training_response_sha256,
        }
    )
    return {
        "allow_public_redistribution": False,
        "allow_training_use": split == "train",
        "baseline_arm": "baseline",
        "generator_version": "test-response-bundle/1.0",
        "grade_evidence_binding_sha256": grade_evidence_binding_sha256,
        "license": "CC-BY-4.0",
        "lineage_family_id": f"prompt-cluster:{index:064x}",
        "pii_checked": True,
        "prompt_id_sha256": prompt_id_sha256,
        "prompt_cluster_id": f"prompt-cluster:{index:064x}",
        "publication_approval_required": True,
        "quality_evidence": quality_evidence,
        "quality_evidence_sha256": quality_evidence["evidence_sha256"],
        "quality_gate": {
            "accepted": True,
            "checks": {
                "hidden_reasoning_absent": True,
                "pii_absent_after_scrub": True,
                "same_prompt_pair": True,
            },
        },
        "rights_basis": {
            "prompt_corpus_license": "CC-BY-4.0",
            "response_model_license": "Apache-2.0",
            "dataset_row_license": "CC-BY-4.0",
            "publication_status": "separate_manifest_bound_approval_required",
        },
        "rights_holder": "DueCare project contributors",
        "source_response_sha256": source_response_sha256,
        "source_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "split": split,
        "synthetic": True,
        "teacher_arm": "harness_core",
        "teacher_model": "gemma4:test",
        "teacher_model_license": "Apache-2.0",
        "training_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "training_response_sha256": training_response_sha256,
    }


def _candidate(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    candidate.mkdir(parents=True)
    files: dict[str, dict] = {}
    split_counts: dict[str, int] = {}
    prompt_hashes: dict[str, list[str]] = {}
    clusters: dict[str, list[str]] = {}

    for index, split in enumerate(("train", "validation", "test"), 1):
        prompt = f"Protective worker-centred prompt {index}"
        chosen = f"Positive response {index}: preserve evidence and seek reviewed support."
        rejected = f"Nonpreferred response {index}: minimize safeguards."
        common = _common(split, index, chosen, rejected)
        sft = _row(
            {
                **common,
                "id": f"sft-{index}",
                "lineage_id": f"response-pair:{index}:sft",
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": chosen},
                ],
            }
        )
        dpo = _row(
            {
                **common,
                "id": f"dpo-{index}",
                "lineage_id": f"response-pair:{index}:dpo",
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "preference_rationale": {
                    "kind": "visible_grade_delta_not_hidden_reasoning",
                    "score_lift": 42.0,
                },
            }
        )
        reward_positive = _row(
            {
                **common,
                "id": f"reward-positive-{index}",
                "lineage_id": f"response-pair:{index}:reward-positive",
                "prompt": prompt,
                "response": chosen,
                "label": 1,
                "label_semantics": "preferred_same_prompt_response",
                "training_lane": "reward_label_and_positive_target_reference",
            }
        )
        reward_negative = _row(
            {
                **common,
                "id": f"reward-negative-{index}",
                "lineage_id": f"response-pair:{index}:reward-negative",
                "prompt": prompt,
                "response": rejected,
                "label": 0,
                "label_semantics": "nonpreferred_same_prompt_baseline_response",
                "assistant_target_allowed": False,
                "negative_only": True,
                "training_lane": "reward_label_only_never_sft_assistant_target",
                "quality_gate": {
                    "accepted": True,
                    "accepted_as": "negative_reward_label_only",
                    "negative_only": True,
                    "unsafe_advice_filtered": False,
                    "checks": {
                        "hidden_reasoning_absent": True,
                        "negative_never_assistant_target": True,
                        "pii_absent_after_scrub": True,
                        "same_prompt_pair": True,
                    },
                },
            }
        )
        prefixes = {
            "sft-positive": [sft],
            "dpo-preference": [dpo],
            "reward-labels": [reward_positive, reward_negative],
        }
        for prefix, rows in prefixes.items():
            name = f"{prefix}-{split}-00000.jsonl"
            files[name] = _write_jsonl(candidate / name, rows)
        split_counts[split] = 1
        prompt_hashes[split] = [common["training_prompt_sha256"]]
        clusters[split] = [common["prompt_cluster_id"]]

    inventory = _row(
        {
            "schema_version": "duecare.response-log-inventory.v1",
            "contains_raw_text": False,
            "prompt_sha256": "1" * 64,
            "response_sha256": "2" * 64,
            "response_chars": 120,
            "grading_status": "ungraded",
        }
    )
    quarantine = _row(
        {
            "schema_version": "duecare.response-quarantine.v1",
            "contains_raw_text": False,
            "prompt_id_sha256": "3" * 64,
            "model_sha256": "4" * 64,
            "reason_codes": ["provider_output_rights_pending"],
        }
    )
    files["response-inventory-00000.jsonl"] = _write_jsonl(
        candidate / "response-inventory-00000.jsonl", [inventory]
    )
    files["quarantine-00000.jsonl"] = _write_jsonl(
        candidate / "quarantine-00000.jsonl", [quarantine]
    )

    ledger = {
        "schema_version": builder.CONTAMINATION_SCHEMA,
        "created_at": "2026-07-15T00:00:00+00:00",
        "selection_uses_source_benchmark_grades": True,
        "source_benchmark_cannot_be_reused_as_model_improvement_evidence": True,
        "independent_external_evidence_eligible": False,
        "accepted_training_prompt_sha256_by_split": prompt_hashes,
        "prompt_cluster_ids_by_split": clusters,
        "prompt_cluster_overlap": {
            "train_validation": [],
            "train_test": [],
            "validation_test": [],
        },
        "policy": "Use a separate lineage-independent holdout.",
    }
    ledger["sha256"] = builder._canonical_sha256(ledger)
    _write_json(candidate / "contamination-ledger.json", ledger)
    files["contamination-ledger.json"] = {
        "bytes": (candidate / "contamination-ledger.json").stat().st_size,
        "sha256": _sha256_file(candidate / "contamination-ledger.json"),
    }

    manifest = {
        "schema_version": builder.CANDIDATE_SCHEMA,
        "generator_version": "test-response-bundle/1.0",
        "created_at": "2026-07-15T00:00:00+00:00",
        "materialized": True,
        "mode": "build",
        "source": {
            "promptset": {"path": "reports/benchmark/prompts.json", "sha256": "5" * 64},
            "panel": {"path": "reports/grades/panel.jsonl", "sha256": "6" * 64},
            "results": {
                "path": "reports/responses/results.jsonl",
                "snapshot_sha256": "7" * 64,
            },
        },
        "counts": {
            "sft_rows": 3,
            "dpo_rows": 3,
            "reward_rows": 6,
            "response_inventory_rows": 1,
            "quarantine_rows": 1,
            "split_candidates": split_counts,
        },
        "rights": {
            "row_license": "CC-BY-4.0",
            "rights_holder": "DueCare project contributors",
            "prompt_corpus_license": "CC-BY-4.0",
            "model_output_licenses": {"gemma4:test": "Apache-2.0"},
            "allow_public_redistribution": False,
        },
        "allowed_models": {"gemma4:test": "Apache-2.0"},
        "reasoning_data_policy": (
            "Hidden reasoning and provider-private scratchpads are rejected and never "
            "exported."
        ),
        "contamination_ledger": {
            "file": "contamination-ledger.json",
            "sha256": ledger["sha256"],
            "source_benchmark_cannot_be_reused_as_model_improvement_evidence": True,
            "independent_external_evidence_eligible": False,
        },
        "gates": [
            {"id": "row_integrity", "blocking": True, "passed": True},
            {"id": "negative_never_assistant_target", "blocking": True, "passed": True},
            {
                "id": builder.GRADE_GATE_ID,
                "blocking": True,
                "passed": True,
                "value": {"rows": 3, "components": ["A", "B", "C", "D", "E"]},
            },
            *[
                {"id": gate_id, "blocking": True, "passed": True, "value": 0}
                for gate_id in sorted(
                    builder.REQUIRED_BLOCKING_GATES
                    - {
                        "row_integrity",
                        "negative_never_assistant_target",
                        builder.GRADE_GATE_ID,
                    }
                )
            ],
            {"id": "publication_approval_separate", "blocking": False, "passed": False},
        ],
        "blocking_failures": [],
        "safe_to_train": True,
        "publication_ready": False,
        "publication_approval": {"required": True, "status": "absent"},
        "files": dict(sorted(files.items())),
    }
    _write_json(candidate / "candidate-manifest.json", manifest)
    return candidate


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _notebook_code(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    assert all(cell.get("id") for cell in notebook["cells"])
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    compile(code, str(path), "exec")
    return code


def _approval(candidate: Path) -> dict:
    ledger_path = candidate / "contamination-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    return {
        "schema_version": builder.APPROVAL_SCHEMA,
        "handoff_kind": builder.APPROVAL_KIND,
        "source_candidate_manifest_sha256": _sha256_file(candidate / "candidate-manifest.json"),
        "contamination_ledger_file_sha256": _sha256_file(ledger_path),
        "contamination_ledger_content_sha256": ledger["sha256"],
        "approved_by": "independent-test-curator",
        "approved_at": "2026-07-15T01:00:00+00:00",
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "rights_holder": "DueCare project contributors",
        "row_license": "CC-BY-4.0",
        "release_license": "CC-BY-4.0",
        "approvals": {
            "curator_approved": True,
            "privacy_approved": True,
            "license_approved": True,
            "quality_approved": True,
            "public_redistribution_approved": True,
        },
    }


def test_builds_private_manifest_bound_collection_and_cpu_notebooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate(tmp_path)
    output = tmp_path / "collection"
    result = builder.build_collection(
        candidate / "candidate-manifest.json",
        output,
        repo_commit=TEST_COMMIT,
    )

    assert result["publication_state"] == "candidate_private"
    assert result["publication_ready"] is False
    assert result["safe_to_train"] is True
    assert result["safe_to_publish"] is False
    assert result["no_upload_or_publication_performed"] is True
    assert result["verification"]["ok"] is True
    assert result["repo_provenance"]["commit"] == TEST_COMMIT
    assert result["repo_provenance"]["state"] in {
        "clean_commit",
        "uncommitted_worktree_explicitly_recorded",
    }
    dataset = output / "dataset"
    metadata = json.loads((dataset / "dataset-metadata.json").read_text(encoding="utf-8"))
    release = json.loads((dataset / "release-manifest.json").read_text(encoding="utf-8"))
    index = json.loads((dataset / "shard-index.json").read_text(encoding="utf-8"))
    assert metadata["isPrivate"] is True
    assert metadata["description"].startswith("A private Kaggle / Gemma 4 Good Hackathon")
    assert metadata["keywords"] == ["nlp"]
    assert metadata["licenses"] == [
        {"name": "Attribution 4.0 International (CC BY 4.0)"}
    ]
    assert release["safe_to_train"] is True
    assert release["publication_ready"] is False
    assert release["publication_approval"] is None
    assert release["validation"]["negative_never_assistant_target"] is True
    assert release["claims"] == {
        "training_completed": False,
        "adapter_produced": False,
        "model_lift_demonstrated": False,
        "independent_external_evaluation_completed": False,
        "full_flywheel_closure": False,
    }
    assert index["lanes"]["sft_positive_train"]["rows"] == 1
    assert index["lanes"]["reward_labels_train"]["rows"] == 2
    assert index["lanes"]["response_inventory"]["rows"] == 1
    assert index["lanes"]["quarantine"]["rows"] == 1
    for name in (
        "README.md",
        "DATA_CARD.md",
        "SCHEMA.md",
        "LOADING.md",
        "SOURCES.md",
        "LIMITATIONS.md",
        "LICENSE",
        "CITATION.cff",
        "candidate-manifest.json",
        "contamination-ledger.json",
        "dataset-overview.csv",
        "preview-catalog.jsonl",
        "croissant.json",
    ):
        assert (dataset / name).is_file(), name
    croissant = json.loads((dataset / "croissant.json").read_text(encoding="utf-8"))
    assert croissant["dct:conformsTo"] == "http://mlcommons.org/croissant/1.0"
    assert croissant["url"] == "https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus"
    assert croissant["distribution"]
    for item in croissant["distribution"]:
        declaration = release["artifacts"][item["@id"]]
        assert item["sha256"] == declaration["sha256"]
        assert item["contentSize"] == f"{declaration['bytes']} B"
    assert builder.verify_dataset_package(dataset)["ok"] is True
    collection_manifest = json.loads(
        (output / "collection-manifest.json").read_text(encoding="utf-8")
    )
    assert collection_manifest["publication_ready"] is False
    assert collection_manifest["safe_to_train"] is True
    assert collection_manifest["safe_to_publish"] is False
    assert "dataset/dataset-metadata.json" in collection_manifest["artifacts"]
    assert (
        "notebooks/integrity_exploration/kernel-metadata.json"
        in collection_manifest["artifacts"]
    )
    assert builder.verify_collection_package(output)["ok"] is True

    with (dataset / "dataset-overview.csv").open(encoding="utf-8", newline="") as handle:
        overview = list(csv.DictReader(handle))
    assert len(overview) == len(builder.LANES)
    assert {row["training_role"] for row in overview} >= {
        "positive_sft_target",
        "same_prompt_preference_pair",
        "reward_or_quality_label",
        "audit_only_not_trainable",
        "audit_only_excluded",
    }

    integrity_code = _notebook_code(
        output / "notebooks" / "integrity_exploration" / "notebook.ipynb"
    )
    plan_code = _notebook_code(output / "notebooks" / "training_plan" / "notebook.ipynb")
    for notebook_dir in ("integrity_exploration", "training_plan"):
        kernel = json.loads(
            (output / "notebooks" / notebook_dir / "kernel-metadata.json").read_text(
                encoding="utf-8"
            )
        )
        assert kernel["is_private"] is True
        assert kernel["enable_gpu"] is False
        assert kernel["enable_internet"] is False
    assert "integrity-audit.json" in integrity_code
    assert "negative response appears as an SFT target" in integrity_code
    assert "TRAINING_ENABLED = False" in plan_code
    assert '"training_completed": False' in plan_code
    assert "reward_classifier" in plan_code

    with monkeypatch.context() as patch:
        patch.chdir(output)
        exec(compile(integrity_code, "integrity-notebook", "exec"), {})
        exec(compile(plan_code, "training-plan-notebook", "exec"), {})
    audit_output = output / "duecare_training_outputs" / "integrity-audit.json"
    plan_output = output / "duecare_training_outputs" / "training-plan.json"
    assert json.loads(audit_output.read_text(encoding="utf-8"))["ok"] is True
    assert json.loads(plan_output.read_text(encoding="utf-8"))["training_completed"] is False

    data_card = dataset / "DATA_CARD.md"
    original_data_card = data_card.read_bytes()
    data_card.write_bytes(original_data_card + b"tamper\n")
    try:
        with monkeypatch.context() as patch:
            patch.chdir(output)
            with pytest.raises(AssertionError):
                exec(compile(integrity_code, "tampered-integrity-notebook", "exec"), {})
    finally:
        data_card.write_bytes(original_data_card)

    extra = dataset / "undeclared-upload-control.txt"
    extra.write_text("must not be uploaded\n", encoding="utf-8")
    dataset_failure = builder.verify_dataset_package(dataset)
    collection_failure = builder.verify_collection_package(output)
    assert dataset_failure["ok"] is False
    assert "undeclared dataset artifact" in " ".join(dataset_failure["failures"])
    assert collection_failure["ok"] is False
    assert "undeclared collection artifact" in " ".join(collection_failure["failures"])
    extra.unlink()


def test_collection_is_deterministic_and_streams_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate(tmp_path)
    first, second = tmp_path / "first", tmp_path / "second"
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path.suffix == ".jsonl":
            raise AssertionError(f"JSONL must be streamed: {path}")
        return original_read_text(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", guarded_read_text)
        builder.build_collection(
            candidate / "candidate-manifest.json", first, repo_commit=TEST_COMMIT
        )
    builder.build_collection(
        candidate / "candidate-manifest.json", second, repo_commit=TEST_COMMIT
    )
    assert _file_hashes(first) == _file_hashes(second)


def test_rejects_secret_tampering_and_negative_sft_target(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    inventory_path = candidate / "response-inventory-00000.jsonl"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["note"] = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    inventory = _row({key: value for key, value in inventory.items() if key != "sha256"})
    declaration = _write_jsonl(inventory_path, [inventory])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][inventory_path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="credential-like secret"):
        builder.build_collection(
            manifest_path, tmp_path / "secret-output", repo_commit=TEST_COMMIT
        )
    assert not (tmp_path / "secret-output").exists()

    candidate = _candidate(tmp_path / "second-candidate")
    sft_path = candidate / "sft-positive-train-00000.jsonl"
    dpo = json.loads(
        (candidate / "dpo-preference-train-00000.jsonl").read_text(encoding="utf-8")
    )
    sft = json.loads(sft_path.read_text(encoding="utf-8"))
    sft["messages"][-1]["content"] = dpo["rejected"]
    sft["training_response_sha256"]["chosen"] = hashlib.sha256(
        dpo["rejected"].encode()
    ).hexdigest()
    sft["source_response_sha256"]["teacher"] = sft["training_response_sha256"][
        "chosen"
    ]
    sft["grade_evidence_binding_sha256"] = builder._canonical_sha256(
        {
            "quality_evidence_sha256": sft["quality_evidence"]["evidence_sha256"],
            "source_response_sha256": sft["source_response_sha256"],
            "training_response_sha256": sft["training_response_sha256"],
        }
    )
    sft = _row({key: value for key, value in sft.items() if key != "sha256"})
    declaration = _write_jsonl(sft_path, [sft])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][sft_path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="negative response is present"):
        builder.build_collection(
            manifest_path, tmp_path / "negative-output", repo_commit=TEST_COMMIT
        )


def test_public_ready_requires_exact_independent_approval(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    with pytest.raises(builder.CollectionError, match="requires exact independent approval"):
        builder.build_collection(
            manifest_path,
            tmp_path / "unapproved",
            repo_commit=TEST_COMMIT,
            public_ready=True,
        )
    approval = _approval(candidate)
    approval["source_candidate_manifest_sha256"] = "0" * 64
    approval_path = tmp_path / "wrong-approval.json"
    _write_json(approval_path, approval)
    with pytest.raises(builder.CollectionError, match="not bound to the candidate"):
        builder.build_collection(
            manifest_path,
            tmp_path / "wrong",
            repo_commit=TEST_COMMIT,
            public_ready=True,
            approval_path=approval_path,
        )

    approval = _approval(candidate)
    approval["approved_by"] = "curator@example.org"
    _write_json(approval_path, approval)
    with pytest.raises(builder.CollectionError, match="PII-like data"):
        builder.build_collection(
            manifest_path,
            tmp_path / "pii-approval",
            repo_commit=TEST_COMMIT,
            public_ready=True,
            approval_path=approval_path,
        )

    approval = _approval(candidate)
    approval["note"] = "An arbitrary note is not part of the approval contract."
    _write_json(approval_path, approval)
    with pytest.raises(builder.CollectionError, match="closed schema without notes"):
        builder.build_collection(
            manifest_path,
            tmp_path / "noted",
            repo_commit=TEST_COMMIT,
            public_ready=True,
            approval_path=approval_path,
        )

    approval = _approval(candidate)
    _write_json(approval_path, approval)
    result = builder.build_collection(
        manifest_path,
        tmp_path / "approved",
        repo_commit=TEST_COMMIT,
        public_ready=True,
        approval_path=approval_path,
    )
    assert result["publication_ready"] is True
    assert result["safe_to_train"] is True
    collection = json.loads(
        (tmp_path / "approved" / "collection-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert collection["safe_to_publish"] is True
    metadata = json.loads(
        (tmp_path / "approved" / "dataset" / "dataset-metadata.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["isPrivate"] is False


def test_rejects_incomplete_or_unbound_grade_components(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    path = candidate / "sft-positive-train-00000.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["quality_evidence"]["target_components"].pop("E")
    row["quality_evidence"]["evidence_sha256"] = builder._quality_evidence_sha256(
        row["quality_evidence"]
    )
    row["quality_evidence_sha256"] = row["quality_evidence"]["evidence_sha256"]
    row["grade_evidence_binding_sha256"] = builder._canonical_sha256(
        {
            "quality_evidence_sha256": row["quality_evidence"]["evidence_sha256"],
            "source_response_sha256": row["source_response_sha256"],
            "training_response_sha256": row["training_response_sha256"],
        }
    )
    row = _row({key: value for key, value in row.items() if key != "sha256"})
    declaration = _write_jsonl(path, [row])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="exactly complete A-E"):
        builder.build_collection(
            manifest_path,
            tmp_path / "incomplete-grade-output",
            repo_commit=TEST_COMMIT,
        )

    candidate = _candidate(tmp_path / "missing-gate")
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["gates"] = [
        gate for gate in manifest["gates"] if gate.get("id") != builder.GRADE_GATE_ID
    ]
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match=builder.GRADE_GATE_ID):
        builder.build_collection(
            manifest_path,
            tmp_path / "missing-gate-output",
            repo_commit=TEST_COMMIT,
        )


def test_force_replacement_rolls_through_staging_and_rejects_source_overlap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate(tmp_path)
    output = tmp_path / "collection"
    first = builder.build_collection(
        candidate / "candidate-manifest.json", output, repo_commit=TEST_COMMIT
    )
    second = builder.build_collection(
        candidate / "candidate-manifest.json",
        output,
        repo_commit=TEST_COMMIT,
        force=True,
    )
    assert first["release_id"] == second["release_id"]
    assert second["previous_output_backup_retained"] is False
    assert not (tmp_path / ".collection-previous").exists()
    assert builder.verify_collection_package(output)["ok"] is True

    before_failure = _sha256_file(output / "collection-manifest.json")
    original_rename = Path.rename

    def fail_staging_commit(path: Path, target: Path):
        if path.name.startswith(".collection-building-") and Path(target) == output:
            raise OSError("simulated staging commit failure")
        return original_rename(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "rename", fail_staging_commit)
        with pytest.raises(OSError, match="simulated staging commit failure"):
            builder.build_collection(
                candidate / "candidate-manifest.json",
                output,
                repo_commit=TEST_COMMIT,
                force=True,
            )
    assert _sha256_file(output / "collection-manifest.json") == before_failure
    assert not (tmp_path / ".collection-previous").exists()
    assert builder.verify_collection_package(output)["ok"] is True

    with pytest.raises(builder.CollectionError, match="must not overlap"):
        builder.build_collection(
            candidate / "candidate-manifest.json",
            candidate / "nested-output",
            repo_commit=TEST_COMMIT,
        )
    assert not (candidate / "nested-output").exists()

    linked_output = tmp_path / "linked-output"
    try:
        linked_output.symlink_to(tmp_path / "real-output", target_is_directory=True)
    except OSError:
        pass
    else:
        with pytest.raises(builder.CollectionError, match="symlink or junction"):
            builder.build_collection(
                candidate / "candidate-manifest.json",
                linked_output,
                repo_commit=TEST_COMMIT,
            )


def test_commit_staging_retries_transient_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / ".collection-building-transient"
    output = tmp_path / "collection"
    staging.mkdir()
    (staging / "collection-manifest.json").write_text("{}", encoding="utf-8")
    original_rename = Path.rename
    attempts = 0

    def transient_rename(path: Path, target: Path):
        nonlocal attempts
        if path == staging and Path(target) == output and attempts < 2:
            attempts += 1
            raise PermissionError("simulated transient OneDrive lock")
        attempts += 1
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", transient_rename)
    monkeypatch.setattr(builder.time, "sleep", lambda _seconds: None)

    retained = builder._commit_staging(staging, output)

    assert retained is None
    assert attempts == 3
    assert (output / "collection-manifest.json").exists()


def test_commit_staging_uses_verified_marker_last_copy_after_persistent_lock(
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
    monkeypatch.setattr(builder.time, "sleep", lambda _seconds: None)

    retained = builder._commit_staging(staging, output)

    assert retained is None
    assert not staging.exists()
    assert (output / "payload.txt").read_text(encoding="utf-8") == "bound payload"
    assert (output / "collection-manifest.json").read_text(encoding="utf-8") == "{}"


def test_rejects_license_and_prompt_response_binding_mismatches(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rights"]["row_license"] = "proprietary"
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match=r"only CC-BY-4\.0"):
        builder.build_collection(
            manifest_path, tmp_path / "bad-license", repo_commit=TEST_COMMIT
        )

    candidate = _candidate(tmp_path / "bindings")
    path = candidate / "sft-positive-train-00000.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row.pop("quality_evidence_sha256")
    row = _row({key: value for key, value in row.items() if key != "sha256"})
    declaration = _write_jsonl(path, [row])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="quality-evidence binding"):
        builder.build_collection(
            manifest_path, tmp_path / "missing-quality-binding", repo_commit=TEST_COMMIT
        )

    candidate = _candidate(tmp_path / "source-response")
    path = candidate / "dpo-preference-train-00000.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["source_response_sha256"]["teacher"] = "0" * 64
    row["grade_evidence_binding_sha256"] = builder._canonical_sha256(
        {
            "quality_evidence_sha256": row["quality_evidence_sha256"],
            "source_response_sha256": row["source_response_sha256"],
            "training_response_sha256": row["training_response_sha256"],
        }
    )
    row = _row({key: value for key, value in row.items() if key != "sha256"})
    declaration = _write_jsonl(path, [row])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="do not bind the emitted responses"):
        builder.build_collection(
            manifest_path, tmp_path / "bad-source-response", repo_commit=TEST_COMMIT
        )

    candidate = _candidate(tmp_path / "prompt-binding")
    path = candidate / "sft-positive-train-00000.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["messages"][0]["content"] = "A prompt that does not match the declared hash"
    row = _row({key: value for key, value in row.items() if key != "sha256"})
    declaration = _write_jsonl(path, [row])
    manifest_path = candidate / "candidate-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][path.name] = declaration
    _write_json(manifest_path, manifest)
    with pytest.raises(builder.CollectionError, match="prompt text is not bound"):
        builder.build_collection(
            manifest_path, tmp_path / "bad-prompt", repo_commit=TEST_COMMIT
        )
