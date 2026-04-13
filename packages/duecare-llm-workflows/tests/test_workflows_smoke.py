"""Package-level tests for duecare-llm-workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from duecare.core.enums import TaskStatus
from duecare.workflows import (
    AgentStep,
    Workflow,
    WorkflowRunner,
    load_workflow,
    topological_sort,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_ROOT = REPO_ROOT / "configs" / "duecare" / "workflows"


class TestTopologicalSort:
    def test_linear(self):
        order = topological_sort([
            ("a", []),
            ("b", ["a"]),
            ("c", ["b"]),
        ])
        assert order == ["a", "b", "c"]

    def test_diamond(self):
        order = topological_sort([
            ("a", []),
            ("b", ["a"]),
            ("c", ["a"]),
            ("d", ["b", "c"]),
        ])
        # a first, d last; b/c between in alphabetical order
        assert order[0] == "a"
        assert order[-1] == "d"
        assert set(order) == {"a", "b", "c", "d"}

    def test_cycle_raises(self):
        with pytest.raises(ValueError, match="Cycle"):
            topological_sort([
                ("a", ["b"]),
                ("b", ["a"]),
            ])

    def test_unknown_dep_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            topological_sort([
                ("a", ["missing"]),
            ])


class TestWorkflowLoader:
    def test_load_rapid_probe(self):
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        wf = load_workflow(WORKFLOWS_ROOT / "rapid_probe.yaml")
        assert wf.id == "rapid_probe"
        assert len(wf.agents) > 0

    def test_load_evaluate_only(self):
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        wf = load_workflow(WORKFLOWS_ROOT / "evaluate_only.yaml")
        assert wf.id == "evaluate_only"

    def test_workflow_model_roundtrip(self):
        wf = Workflow(
            id="test",
            description="test",
            agents=[AgentStep(id="scout"), AgentStep(id="judge", needs=["scout"])],
        )
        data = wf.model_dump()
        restored = Workflow(**data)
        assert restored.id == "test"
        assert len(restored.agents) == 2


class TestWorkflowRunner:
    def test_run_rapid_probe(self):
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        run = runner.run(
            target_model_id="gemma-4-e4b",
            domain_id="trafficking",
        )
        # The rapid_probe workflow runs scout, judge, historian
        # judge is skipped (no target_model_instance), scout + historian complete
        # Overall status: completed
        assert run.status == TaskStatus.COMPLETED
        assert run.run_id
        assert run.config_hash

    def test_run_with_dag_cycle_fails_gracefully(self):
        wf = Workflow(
            id="bad",
            agents=[
                AgentStep(id="a", needs=["b"]),
                AgentStep(id="b", needs=["a"]),
            ],
        )
        runner = WorkflowRunner(wf)
        run = runner.run(target_model_id="m", domain_id="d")
        assert run.status == TaskStatus.FAILED
        assert "Cycle" in (run.error or "")
