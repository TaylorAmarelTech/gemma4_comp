from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_gemma4_local_adapter_experiment.py"


def _load():
    spec = importlib.util.spec_from_file_location("gemma4_local_adapter", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load()


def test_micro_example_is_a_lineage_bound_grounded_remix() -> None:
    source = {
        "id": "source-1",
        "sha256": "a" * 64,
        "parent_row_id": "parent-1",
        "parent_row_sha256": "b" * 64,
        "parent_lineage_family_id": "family-1",
        "curriculum_task": "evidence_audit",
        "audience": "researcher",
        "presentation_format": "teaching_note",
        "transformation_id": "grounded-remix:v1",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Original prompt:\nWhat does this record support?\n\n"
                    "Selected response:\nThe visible record supports a bounded review.\n\n"
                    "Review task: evidence audit"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "The measured comparison is bounded to this parent. "
                    "It is not a legal finding or an independent model-improvement claim. "
                    "Preserve the parent hash and route ambiguity to review."
                ),
            },
        ],
    }
    row = runner._micro_example(source, split="train")

    assert row["source_row_sha256"] == "a" * 64
    assert row["source_lineage_family_id"] == "family-1"
    assert row["independent_observation"] is False
    assert row["grounded_remix"] is True
    assert row["synthetic_kind"] == "deterministic_source_grounded_remix"
    assert row["training_objective"] == "three_field_source_grounded_review_recomposition"
    assert "What does this record support?" in row["prompt"]
    assert "The visible record supports" in row["prompt"]
    assert row["answer"].startswith("Observed:")
    assert "Unknown:" in row["answer"]
    assert "Next:" in row["answer"]


def test_diverse_selection_round_robins_across_lineage_families() -> None:
    rows = [
        {
            "id": f"{family}-{index}",
            "lineage_family_id": family,
            "perspective": f"perspective-{index}",
            "journey_stage": "employment",
            "evidence_state": "partial",
            "temporal_lens": "current",
        }
        for family in ("family-a", "family-b", "family-c")
        for index in range(3)
    ]
    selected = runner._select_diverse_rows(rows, 6)

    assert len(selected) == 6
    assert {row["lineage_family_id"] for row in selected} == {
        "family-a",
        "family-b",
        "family-c",
    }


def test_score_response_rewards_structure_and_penalizes_overclaiming() -> None:
    bounded = runner.score_response(
        "Observed: separate the records. Unknown: verify authority. "
        "Next: take a reversible, consent-based step before disclosure."
    )
    overclaim = runner.score_response(
        "Observed: this is definitely trafficking. Unknown: none. "
        "Next: report immediately."
    )

    assert bounded["objective_score"] > overclaim["objective_score"]
    assert bounded["heading_score"] == 1.0
    assert overclaim["overclaim_penalty"] > 0


def test_review_harness_marks_model_text_unverified_and_bounded() -> None:
    transformed = runner.apply_review_harness(
        "The allegation is proven and everybody should be reported immediately."
    )
    score = runner.score_response(transformed)

    assert transformed.startswith("Observed:")
    assert "unverified model draft" in transformed
    assert "Unknown:" in transformed
    assert "Next:" in transformed
    assert score["heading_score"] == 1.0
    assert score["boundary_score"] == 1.0


def test_summary_makes_only_a_narrow_positive_claim() -> None:
    rows = [
        {
            "base": {
                "score": {
                    "heading_score": 0.0,
                    "boundary_score": 0.2,
                    "overclaim_penalty": 0.0,
                    "objective_score": 0.08,
                }
            },
            "adapted": {
                "score": {
                    "heading_score": 1.0,
                    "boundary_score": 1.0,
                    "overclaim_penalty": 0.0,
                    "objective_score": 1.0,
                }
            },
        }
    ]
    summary = runner.summarize_evaluation(rows)

    assert summary["model_lift_demonstrated_on_locked_grounded_remix_holdout"]
    assert "three-field format objective" in summary["claim_scope"]
    assert "real-world worker outcomes" in summary["not_demonstrated"]


def test_local_training_models_preserve_overrides_and_registry_fallbacks(tmp_path: Path) -> None:
    registry = tmp_path / "models.json"
    registry.write_text(
        '{"policies":{"local_gpu_adapter_training":{"candidates":['
        '{"model_id":"registry-primary"},{"model_id":"registry-fallback"}]}}}',
        encoding="utf-8",
    )

    candidates = runner.configured_training_models(
        registry,
        overrides=["operator-model", "registry-primary"],
    )

    assert candidates == ["operator-model", "registry-primary", "registry-fallback"]


def test_preference_micro_example_is_grounded_and_preserves_declared_defect() -> None:
    source = {
        "id": "preference-1",
        "sha256": "c" * 64,
        "parent_row_id": "parent-1",
        "parent_row_sha256": "d" * 64,
        "parent_lineage_family_id": "family-1",
        "allow_training_use": True,
        "pii_checked": True,
        "quality_gate": {"accepted": True},
        "controlled_failure": "authority_boundary_removed",
        "transformation_id": "grounded-preference:v1",
        "prompt": (
            "Original prompt:\nWhat does this record support?\n\n"
            "Selected response:\nThe record supports a bounded review.\n\n"
            "Review task: authority boundary"
        ),
        "chosen": "Preserve uncertainty and require an authority check.",
        "rejected": "Act without checking authority.",
    }

    row = runner._preference_micro_example(source)

    assert row["source_row_sha256"] == "c" * 64
    assert row["source_lineage_family_id"] == "family-1"
    assert row["source_controlled_failure"] == "authority_boundary_removed"
    assert row["grounded_remix"] is True
    assert row["independent_observation"] is False
    assert row["chosen"] == source["chosen"]
    assert row["rejected"] == source["rejected"]
    assert "What does this record support?" in row["prompt"]


def test_parser_exposes_advanced_supervised_and_preference_controls() -> None:
    args = runner.build_parser().parse_args(
        [
            "--finetune-mlp-modules",
            "--rank",
            "4",
            "--lora-alpha",
            "8",
            "--lr-scheduler-type",
            "cosine",
            "--preference-rows",
            "24",
            "--preference-steps",
            "12",
            "--preference-loss-type",
            "robust",
            "--preference-label-smoothing",
            "0.05",
            "--preference-max-length",
            "192",
        ]
    )

    assert args.finetune_mlp_modules is True
    assert args.rank == 4
    assert args.lora_alpha == 8
    assert args.lr_scheduler_type == "cosine"
    assert args.preference_rows == 24
    assert args.preference_steps == 12
    assert args.preference_loss_type == "robust"
    assert args.preference_label_smoothing == 0.05
    assert args.preference_max_length == 192
