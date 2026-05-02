"""Real tests for duecare.core.contracts Protocols.

Uses runtime_checkable isinstance() checks to verify a class satisfies
the protocol structurally.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from duecare.core.contracts import (
    Agent,
    Coordinator,
    DomainPack,
    Model,
    Task,
)
from duecare.core.enums import AgentRole, Capability, TaskStatus
from duecare.core.schemas import (
    AgentContext,
    AgentOutput,
    ChatMessage,
    DomainCard,
    Embedding,
    GenerationResult,
    ModelHealth,
    Provenance,
    TaskConfig,
    TaskResult,
    ToolSpec,
    WorkflowRun,
)


# -------- minimal conforming implementations --------


class _StubModel:
    id = "stub:model"
    display_name = "Stub Model"
    provider = "stub"
    capabilities: set[Capability] = {Capability.TEXT}
    context_length = 4096

    def generate(
        self,
        messages: list[ChatMessage],
        tools=None,
        images=None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs,
    ) -> GenerationResult:
        return GenerationResult(text="stub", model_id=self.id)

    def embed(self, texts: list[str]) -> list[Embedding]:
        return [
            Embedding(text=t, vector=[0.0], dimension=1, model_id=self.id)
            for t in texts
        ]

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(model_id=self.id, healthy=True)


class _StubDomainPack:
    id = "stub_domain"
    display_name = "Stub Domain"
    version = "0.0.1"
    root = Path("/tmp/stub")

    def card(self) -> DomainCard:
        return DomainCard(
            id=self.id, display_name=self.display_name, version=self.version
        )

    def taxonomy(self) -> dict:
        return {}

    def rubric(self) -> dict:
        return {}

    def pii_spec(self) -> dict:
        return {}

    def seed_prompts(self) -> Iterator[dict]:
        yield from []

    def evidence(self) -> Iterator[dict]:
        yield from []

    def known_failures(self) -> Iterator[dict]:
        yield from []


class _StubTask:
    id = "stub_task"
    name = "Stub Task"
    capabilities_required: set[Capability] = {Capability.TEXT}

    def run(self, model, domain, config: TaskConfig) -> TaskResult:
        return TaskResult(
            task_id=self.id,
            model_id=model.id,
            domain_id=domain.id,
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            provenance=Provenance(
                run_id="r",
                git_sha="s",
                workflow_id="w",
                created_at=datetime.now(),
                checksum="c",
            ),
        )


class _StubAgent:
    id = "stub_agent"
    role = AgentRole.SCOUT
    version = "0.0.1"
    model = None  # type: ignore[assignment]
    tools: list[ToolSpec] = []
    inputs: set[str] = set()
    outputs: set[str] = {"ok"}
    cost_budget_usd = 0.0

    def execute(self, ctx: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent_id=self.id,
            agent_role=self.role,
            status=TaskStatus.COMPLETED,
            decision="ok",
        )

    def explain(self) -> str:
        return "stub"


class _StubCoordinator:
    id = "stub_coord"
    version = "0.0.1"
    workflow_id = "stub_wf"

    def run_workflow(self, ctx: AgentContext) -> WorkflowRun:
        return WorkflowRun(
            run_id=ctx.run_id,
            workflow_id=self.workflow_id,
            git_sha=ctx.git_sha,
            config_hash="",
            target_model_id=ctx.target_model_id,
            domain_id=ctx.domain_id,
            started_at=ctx.started_at,
            ended_at=datetime.now(),
            status=TaskStatus.COMPLETED,
        )

    def explain(self) -> str:
        return "stub"


# -------- actual tests --------


def test_model_protocol_structural_check() -> None:
    m = _StubModel()
    assert isinstance(m, Model)


def test_domain_pack_protocol_structural_check() -> None:
    d = _StubDomainPack()
    assert isinstance(d, DomainPack)


def test_task_protocol_structural_check() -> None:
    t = _StubTask()
    assert isinstance(t, Task)


def test_agent_protocol_structural_check() -> None:
    a = _StubAgent()
    assert isinstance(a, Agent)


def test_coordinator_protocol_structural_check() -> None:
    c = _StubCoordinator()
    assert isinstance(c, Coordinator)


def test_stub_model_generate_roundtrip() -> None:
    m = _StubModel()
    result = m.generate([ChatMessage(role="user", content="hi")])
    assert result.text == "stub"
    assert result.model_id == "stub:model"


def test_stub_task_run_produces_completed_result() -> None:
    m = _StubModel()
    d = _StubDomainPack()
    t = _StubTask()
    result = t.run(m, d, TaskConfig())
    assert result.status == TaskStatus.COMPLETED
    assert result.model_id == m.id
    assert result.domain_id == d.id
