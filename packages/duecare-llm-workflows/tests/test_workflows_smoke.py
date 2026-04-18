"""Package-level tests for duecare-llm-workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from duecare.core.contracts import Model
from duecare.core.schemas import ChatMessage, Embedding, GenerationResult, ModelHealth
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


class FakeModel(Model):
    id = "fake:model"
    display_name = "Fake Model"
    provider = "fake"
    capabilities = set()
    context_length = 8192

    def generate(
        self,
        messages: list[ChatMessage],
        tools=None,
        images=None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs,
    ) -> GenerationResult:
        return GenerationResult(
            text=(
                "I cannot help exploit migrant workers. "
                "Contact labor authorities and protective services."
            ),
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=12,
            tokens_used=22,
            model_id=self.id,
            model_version="test",
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        return []

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(model_id=self.id, healthy=True)


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
    def test_run_rapid_probe_without_model_marks_skipped(self):
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        run = runner.run(
            target_model_id="gemma-4-e4b",
            domain_id="trafficking",
        )
        assert run.status == TaskStatus.SKIPPED
        assert run.run_id
        assert run.config_hash
        assert any(output.status == TaskStatus.SKIPPED for output in run.agent_outputs)

    def test_run_rapid_probe_with_model_collects_metrics_and_artifacts(self):
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        run = runner.run(
            target_model_id="fake-model",
            domain_id="trafficking",
            target_model_instance=FakeModel(),
        )
        assert run.status == TaskStatus.COMPLETED
        assert run.agent_outputs
        assert "readiness_score" in run.final_metrics
        assert any(metric.startswith("guardrails.") for metric in run.final_metrics)
        assert "run_report" in run.final_artifacts

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
