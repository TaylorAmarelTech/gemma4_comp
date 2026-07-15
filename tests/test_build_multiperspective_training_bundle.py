from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "build_multiperspective_training_bundle.py"
RELEASE_PATH = ROOT / "scripts" / "build_kaggle_training_release.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load(GENERATOR_PATH, "build_multiperspective_training_bundle")
release = _load(RELEASE_PATH, "build_kaggle_training_release_for_multiperspective")


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _lineage_families(rows: list[dict]) -> set[str]:
    return {str(row["lineage_family_id"]) for row in rows}


def _user_prompt(row: dict) -> str:
    return next(message["content"] for message in row["messages"] if message["role"] == "user")


def test_declares_complete_grounded_multiperspective_matrix() -> None:
    assert generator.matrix_size() == 96_768
    assert len(generator.enumerate_descriptors()) == 96_768
    assert len(generator.PERSONAS) == 8
    assert len(generator.JOURNEY_STAGES) == 7
    assert len(generator.TEMPORAL_LENSES) == 4
    assert len(generator.EVIDENCE_STATES) == 4
    assert len(generator.VIEW_MODES) == 3
    assert len(generator.JURISDICTION_PATTERNS) == 3
    assert len(generator.MECHANISMS) == 12
    assert {
        "worker",
        "newly_arrived_worker",
        "third_party_observer",
        "ngo_caseworker",
        "origin_country_official",
        "destination_regulator",
        "legal_scholar",
    }.issubset(generator.PERSONA_BY_KEY)
    assert (
        generator.TRAIN_MECHANISM_KEYS
        | generator.VALIDATION_MECHANISM_KEYS
        | generator.TEST_MECHANISM_KEYS
    ) == set(generator.MECHANISM_BY_KEY)


def test_case_graphs_are_dated_and_temporally_compatible() -> None:
    for mechanism in generator.MECHANISMS:
        for jurisdiction in generator.JURISDICTION_PATTERNS:
            graph = generator.build_fact_graph(mechanism["key"], jurisdiction["key"])
            assert graph["synthetic"] is True
            assert len(graph["events"]) == 7
            assert len(graph["records"]) == 14
            assert len(graph["contradictions"]) == 7
            assert [event["date"] for event in graph["events"]] == sorted(
                event["date"] for event in graph["events"]
            )
            onset = generator.STAGE_INDEX[mechanism["onset"]]
            assert all(
                event["status"] == "prospective_context_only"
                for event in graph["events"][:onset]
            )
            assert graph["events"][onset]["status"] == "reported_condition_with_competing_account"
            assert all(
                event["status"] == "post_onset_followup"
                for event in graph["events"][onset + 1 :]
            )
            actor_ids = {actor["id"] for actor in graph["actors"]}
            assert all(record["source_actor"] in actor_ids for record in graph["records"])
            assert all(
                mechanism["condition"] not in record["excerpt"]
                for record in graph["records"]
                if generator.STAGE_INDEX[record["stage"]] != onset
            )
            assert any(
                event["status"] == "reported_condition_with_competing_account"
                for event in graph["events"]
            )

    descriptor = next(
        row
        for row in generator.enumerate_descriptors()
        if row["mechanism"] == "post_deployment_debt"
        and row["journey_stage"] == "recruitment"
        and row["temporal_lens"] == "prospective"
        and row["persona"] == "newly_arrived_worker"
        and row["evidence_state"] == "conflicting_records"
        and row["view_mode"] == "multi_actor_synthesis"
    )
    dossier = generator._dossier(descriptor)
    assert dossier["graph"]["events"][0]["status"] == "prospective_context_only"
    assert all(
        event["summary"] == "future outcome intentionally withheld"
        for event in dossier["timeline"][1:]
    )
    prompt = generator._prompt(descriptor)
    assert "Later outcomes must not be read back" in prompt
    assert "post_deployment_debt" not in prompt
    assert "held-out family" not in prompt
    assert "I am new in Country B" not in prompt

    account_only = dict(descriptor)
    account_only["evidence_state"] = "account_only"
    visible = generator._dossier(account_only)["visible_records"]
    assert visible
    assert all(row["kind"] == "bounded_perspective_note" for row in visible)

    rule_change = dict(descriptor)
    rule_change["temporal_lens"] = "rule_change"
    assert len(generator._dossier(rule_change)["rule_objects"]) == 2


def test_builds_audited_lineage_isolated_release(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    release_dir = tmp_path / "release"
    summary = generator.build_bundle(
        source_dir,
        train_rows=224,
        validation_rows=64,
        test_rows=64,
    )

    assert summary["cartesian_matrix_rows"] == 96_768
    assert summary["sft_train_rows"] == 224
    assert summary["preference_train_rows"] == 224
    assert summary["sft_validation_rows"] == 64
    assert summary["sft_test_rows"] == 64
    assert summary["training_validation_ok"] is True
    assert summary["quality_audit_clean"] is True
    assert summary["publication_ready"] is False
    assert not (source_dir / "publication_approval.json").exists()
    assert summary["selection_contract"]["axis_coverage_complete"] is True
    assert not any(summary["selection_contract"]["mechanism_family_overlap"].values())

    sft = _jsonl(source_dir / "source_sft.jsonl")
    preference = _jsonl(source_dir / "source_dpo.jsonl")
    validation = _jsonl(source_dir / "source_validation.jsonl")
    test = _jsonl(source_dir / "source_test.jsonl")

    assert {row["id"] for row in sft} == {row["id"] for row in preference}
    assert _lineage_families(sft).isdisjoint(_lineage_families(validation))
    assert _lineage_families(sft).isdisjoint(_lineage_families(test))
    assert _lineage_families(validation).isdisjoint(_lineage_families(test))
    assert {row["lineage_id"] for row in sft}.isdisjoint(
        {row["lineage_id"] for row in preference}
    )

    sft_by_id = {row["id"]: row for row in sft}
    rejected = set()
    for row in preference:
        assert row["synthetic"] is True
        assert row["prompt"] == _user_prompt(sft_by_id[row["id"]])
        assert "Compare the two candidate" not in row["prompt"]
        assert "Issue pattern" not in row["prompt"]
        assert "held-out family" not in row["prompt"]
        assert row["prompt_family"] not in row["prompt"]
        assert "weaker response" not in row["rejected"].lower()
        assert 0.55 <= len(row["chosen"]) / len(row["rejected"]) <= 2.0
        assert len(row["rejected"].split("\n\n")) == len(set(row["rejected"].split("\n\n")))
        assert row["journey_stage"] in row["preference_rationale"]["journey_stage"]
        rejected.add(row["rejected"])
    assert len(rejected) == len(preference)

    for row in [*sft, *validation, *test]:
        scaffold = row["structured_rationale"]
        assert scaffold["schema"] == "duecare.visible_decision_scaffold.v2"
        assert scaffold["case_graph_id"]
        assert scaffold["perspectives"]
        assert scaffold["record_ledger"]
        assert scaffold["supported"]
        assert scaffold["inference"]
        assert scaffold["unknown"]
        assert scaffold["alternative_explanation"]
        assert scaffold["counterfactual_question"]
        assert scaffold["retrieval_boundary"]
        if row["view_mode"] == "multi_actor_synthesis":
            assert {
                "worker",
                "ngo_caseworker",
                "origin_country_official",
                "destination_regulator",
            }.issubset({item["persona"] for item in scaffold["perspectives"]})
        if row["temporal_lens"] == "rule_change":
            assert len(scaffold["rule_objects"]) == 2
        answer = row["messages"][-1]["content"]
        assert all(item["record_id"] in answer for item in scaffold["record_ledger"])

    quality = json.loads((source_dir / "quality_audit.json").read_text(encoding="utf-8"))
    assert quality["clean"] is True
    assert quality["approval_status"].startswith("pending_")
    assert quality["counts"]["unique_rejected"] == 224
    assert quality["near_duplicate_audit"]["passed"] is True
    assert quality["near_duplicate_audit"]["max_similarity"] < 0.88
    assert all(gate["passed"] for gate in quality["gates"])

    manifest = json.loads((source_dir / "source_manifest.json").read_text(encoding="utf-8"))
    gates = manifest["training_validation"]["gates"]
    assert all(gate["passed"] for gate in gates)
    assert manifest["safe_to_train"] is True
    assert manifest["prompt_scope"]["closure_status"] == "partial"
    assert manifest["prompt_scope"]["full_flywheel_closure"] is False
    assert manifest["matrix_definition"]["split_unit"].startswith("whole mechanism")
    assert set(manifest["heldout_lineage_family_ids"]) == (
        _lineage_families(validation) | _lineage_families(test)
    )
    assert manifest["model"] == {
        "id": "unsloth/gemma-4-E2B-it",
        "revision": generator.MODEL_REVISION,
    }
    assert manifest["model_role"] == "intended_finetuning_base_not_data_generator"
    assert manifest["training_profile"]["max_steps"] == 56
    assert manifest["training_profile"]["dpo_max_steps"] == 28

    generator.write_publication_approval(
        source_dir / "source_manifest.json",
        approved_by="test-explicit-reviewer",
    )
    result = release.build_release(
        source_dir / "source_manifest.json",
        approval_path=source_dir / "publication_approval.json",
        output_dir=release_dir,
        dataset_id="taylorsamarel/duecare-harness-training-data",
        title="DueCare Grounded Multi-Perspective Data",
    )
    assert result["safe_to_publish"] is True
    assert result["release_tier"] == "preview"
    assert result["source_bundle"]["model_role"] == "intended_finetuning_base_not_data_generator"
    assert result["matrix_summary"]["cartesian_rows"] == 96_768
    assert result["training_profile"]["id"] == "full_preview_lora"
    assert result["training_profile"]["max_steps"] == 56
    assert result["training_profile"]["execute"] is False
    assert set(result["heldout_lineage_family_ids"]) == set(
        manifest["heldout_lineage_family_ids"]
    )
    assert release.verify_release_dir(release_dir)["ok"] is True
    data_card = (release_dir / "DATA_CARD.md").read_text(encoding="utf-8")
    assert "Synthetic reasoning matrix" in data_card
    assert "96,768" in data_card
    assert "harness-to-training-data flywheel" not in data_card

    public_sft = _jsonl(release_dir / "sft_train.jsonl")
    public_preference = _jsonl(release_dir / "preference_train.jsonl")
    for row in (public_sft[0], public_preference[0]):
        assert row["lineage_family_id"]
        assert row["synthetic"] is True
        assert row["target_model_id"] == generator.MODEL_ID
        assert row["target_model_revision"] == generator.MODEL_REVISION
        assert row["model_role"] == generator.MODEL_ROLE
        assert row["perspective"] in generator.PERSONA_BY_KEY
        assert row["journey_stage"] in generator.STAGE_BY_KEY
        assert row["temporal_lens"] in generator.TEMPORAL_BY_KEY
        assert row["evidence_state"] in generator.EVIDENCE_BY_KEY
        assert row["view_mode"] in generator.VIEW_BY_KEY
        assert row["jurisdiction_pattern"] in generator.JURISDICTION_BY_KEY
        assert row["generator_version"] == generator.GENERATOR_VERSION


def test_build_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    kwargs = {"train_rows": 224, "validation_rows": 64, "test_rows": 64}
    generator.build_bundle(first, **kwargs)
    generator.build_bundle(second, **kwargs)
    expected = {
        "source_sft.jsonl",
        "source_dpo.jsonl",
        "source_validation.jsonl",
        "source_test.jsonl",
        "source_quarantine.json",
        "quality_audit.json",
        "source_audit.json",
        "source_manifest.json",
        "build_summary.json",
    }
    assert {path.name for path in first.iterdir()} == expected
    assert {path.name for path in second.iterdir()} == expected
    for name in expected:
        assert (first / name).read_bytes() == (second / name).read_bytes()
