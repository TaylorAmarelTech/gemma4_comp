"""Tests for the Trainer agent's dry-run and real-training modes."""

from __future__ import annotations

from datetime import datetime

from duecare.core.enums import TaskStatus
from duecare.core.schemas import AgentContext


def _build_ctx() -> AgentContext:
    return AgentContext(
        run_id="test-trainer-1",
        workflow_id="test-workflow",
        git_sha="abc123",
        target_model_id="gemma_4_e4b_stock",
        domain_id="trafficking",
        started_at=datetime.now(),
    )


def test_trainer_dry_run_is_skipped() -> None:
    """With dry_run=True, the trainer records config but doesn't train."""
    from duecare.agents.trainer.trainer import TrainerAgent

    trainer = TrainerAgent(dry_run=True, num_train_epochs=1)
    ctx = _build_ctx()
    ctx.record("train_jsonl", [{"text": "sample 1"}, {"text": "sample 2"}])
    ctx.record("val_jsonl", [{"text": "val 1"}])

    out = trainer.execute(ctx)
    assert out.status == TaskStatus.SKIPPED
    assert "DRY RUN" in out.decision
    assert out.metrics["mode"] == 0.0  # 0 = dry-run
    assert out.metrics["n_train_samples"] == 2.0

    # Config was recorded for downstream agents
    config = ctx.lookup("training_config")
    assert config["base_model"].startswith("unsloth/gemma-4")
    assert config["n_train"] == 2


def test_trainer_skips_cleanly_without_unsloth() -> None:
    """When unsloth isn't installed and dry_run=False, trainer skips with
    install hint — no silent failure, no crash."""
    from duecare.agents.trainer.trainer import TrainerAgent

    trainer = TrainerAgent(dry_run=False)
    ctx = _build_ctx()
    ctx.record("train_jsonl", [{"text": "x"}])

    out = trainer.execute(ctx)
    # Either SKIPPED (no unsloth) or COMPLETED (unsloth somehow available)
    assert out.status in (TaskStatus.SKIPPED, TaskStatus.COMPLETED)
    if out.status == TaskStatus.SKIPPED:
        assert "unsloth" in out.decision.lower() or "install" in out.decision.lower()
        assert out.metrics["mode"] == -1.0  # -1 = skipped due to missing deps


def test_trainer_records_config_even_on_skip() -> None:
    """Even when skipping, the training config is recorded for provenance."""
    from duecare.agents.trainer.trainer import TrainerAgent

    trainer = TrainerAgent(dry_run=True, lora_r=32, lora_alpha=64)
    ctx = _build_ctx()
    ctx.record("train_jsonl", [])
    trainer.execute(ctx)
    config = ctx.lookup("training_config")
    assert config["lora_r"] == 32
    assert config["lora_alpha"] == 64


def test_trainer_explain_describes_both_modes() -> None:
    """explain() mentions both Unsloth and the skip behavior."""
    from duecare.agents.trainer.trainer import TrainerAgent

    trainer = TrainerAgent()
    text = trainer.explain()
    assert "Unsloth" in text or "unsloth" in text.lower()
    assert "LoRA" in text or "lora" in text.lower()
