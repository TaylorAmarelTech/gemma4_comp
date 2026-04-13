"""Package-level smoke test. Verifies duecare-llm-core's public API is usable."""

from __future__ import annotations

from datetime import datetime

import pytest


def test_top_level_imports():
    from duecare.core import (
        Agent,
        AgentContext,
        AgentOutput,
        AgentRole,
        Capability,
        ChatMessage,
        Coordinator,
        DomainCard,
        DomainPack,
        Embedding,
        GenerationResult,
        Grade,
        Issue,
        ItemResult,
        Model,
        ModelHealth,
        Provenance,
        Registry,
        ResponseExample,
        Severity,
        Task,
        TaskConfig,
        TaskResult,
        TaskStatus,
        ToolCall,
        ToolSpec,
        WorkflowRun,
        compute_checksum,
        generate_run_id,
        get_git_sha,
        get_short_sha,
        hash_config,
        simhash,
    )
    # Soft assertions that the symbols are callable / usable
    assert Grade.BEST.ordinal == 4
    assert Capability.TEXT == "text"
    r = Registry(kind="test")
    assert isinstance(r, Registry)
    assert r.kind == "test"
    assert len(r) == 0


def test_observability_imports():
    from duecare.observability import (
        AuditTrail,
        MetricsSink,
        configure_logging,
        get_logger,
    )
    configure_logging(level="INFO")
    log = get_logger("duecare.smoke")
    log.info("smoke")


def test_version_string_exists():
    import duecare.core
    assert hasattr(duecare.core, "__version__")
    assert duecare.core.__version__


def test_end_to_end_mini_flow():
    """Build a tiny realistic flow: generate run_id, hash config,
    build a TaskResult, summarize it. Exercises several modules at once."""
    from duecare.core import (
        Grade,
        Provenance,
        TaskResult,
        TaskStatus,
        generate_run_id,
        hash_config,
        compute_checksum,
    )

    run_id = generate_run_id("smoke_workflow")
    config_hash = hash_config({"model": "gemma-4-e4b", "temp": 0.0})

    provenance = Provenance(
        run_id=run_id,
        git_sha="abc123",
        workflow_id="smoke_workflow",
        created_at=datetime.now(),
        checksum=compute_checksum(f"{run_id}:guardrails"),
    )

    result = TaskResult(
        task_id="guardrails",
        model_id="gemma-4-e4b",
        domain_id="trafficking",
        status=TaskStatus.COMPLETED,
        started_at=datetime.now(),
        metrics={"grade_exact_match": 0.68, "grade_within_1": 0.92},
        provenance=provenance,
    )

    summary = result.summary()
    assert "guardrails" in summary
    assert "0.680" in summary
    assert result.status == TaskStatus.COMPLETED
