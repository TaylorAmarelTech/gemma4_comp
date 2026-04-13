"""Real tests for duecare.core.schemas. Every model must round-trip cleanly."""

from __future__ import annotations

from datetime import datetime

import pytest

from duecare.core.enums import AgentRole, Capability, Grade, Severity, TaskStatus
from duecare.core.schemas import (
    AgentContext,
    AgentOutput,
    ChatMessage,
    DomainCard,
    Embedding,
    GenerationResult,
    Issue,
    ItemResult,
    ModelHealth,
    Provenance,
    ResponseExample,
    TaskConfig,
    TaskResult,
    ToolCall,
    ToolSpec,
    WorkflowRun,
)


def _make_provenance() -> Provenance:
    return Provenance(
        run_id="test_run",
        git_sha="abc123",
        workflow_id="evaluate_only",
        created_at=datetime.now(),
        checksum="deadbeef",
    )


class TestChatAndTools:
    def test_chat_message_roles(self):
        for role in ("system", "user", "assistant", "tool"):
            msg = ChatMessage(role=role, content="hello")
            assert msg.role == role
            assert msg.content == "hello"

    def test_tool_spec_to_openai(self):
        tool = ToolSpec(
            name="anonymize",
            description="Strip PII from text",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        )
        openai = tool.to_openai()
        assert openai["type"] == "function"
        assert openai["function"]["name"] == "anonymize"
        assert openai["function"]["parameters"]["type"] == "object"

    def test_tool_spec_to_anthropic(self):
        tool = ToolSpec(name="classify", description="Label text")
        anthropic = tool.to_anthropic()
        assert anthropic["name"] == "classify"
        assert "input_schema" in anthropic

    def test_tool_call_roundtrip(self):
        call = ToolCall(name="anonymize", arguments={"text": "Maria"})
        data = call.model_dump()
        restored = ToolCall(**data)
        assert restored == call


class TestGeneration:
    def test_generation_result_required_fields(self):
        result = GenerationResult(text="hi", model_id="gemma-4-e4b", finish_reason="stop")
        assert result.tokens_used == 0
        assert result.cost_usd == 0.0
        assert result.tool_calls == []

    def test_embedding_dimension(self):
        emb = Embedding(
            text="hello", vector=[0.1, 0.2, 0.3], dimension=3, model_id="sbert"
        )
        assert emb.dimension == 3
        assert len(emb.vector) == 3

    def test_model_health(self):
        health = ModelHealth(model_id="m1", healthy=True, details={"latency_ms": 42})
        assert health.healthy
        assert health.details["latency_ms"] == 42


class TestDomain:
    def test_domain_card_roundtrip(self):
        card = DomainCard(
            id="test",
            display_name="Test Domain",
            version="0.1.0",
            description="A test pack",
            capabilities_required={Capability.TEXT},
        )
        data = card.model_dump()
        restored = DomainCard(**data)
        assert restored.id == "test"
        assert Capability.TEXT in restored.capabilities_required

    def test_issue_with_severity(self):
        issue = Issue(
            type="missed_indicator",
            description="Missed passport retention",
            severity=Severity.HIGH,
            documentation_ref="ilo_c181",
        )
        assert issue.severity == Severity.HIGH

    def test_response_example(self):
        ex = ResponseExample(
            text="I cannot help with this.",
            grade=Grade.GOOD,
            score=0.82,
            explanation="Refuses correctly but doesn't cite sources",
        )
        assert ex.grade == Grade.GOOD
        assert 0.0 <= ex.score <= 1.0


class TestTaskAndAgent:
    def test_task_config_defaults(self):
        config = TaskConfig()
        assert config.sample_size is None
        assert config.seed == 3407
        assert config.temperature == 0.0

    def test_item_result(self):
        item = ItemResult(
            item_id="prompt_001",
            scores={"grade_exact_match": 1.0},
            grade=Grade.BEST,
        )
        assert item.grade == Grade.BEST
        assert item.scores["grade_exact_match"] == 1.0

    def test_task_result_summary(self):
        result = TaskResult(
            task_id="guardrails",
            model_id="gemma-4-e4b",
            domain_id="trafficking",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            metrics={"grade_exact_match": 0.68},
            provenance=_make_provenance(),
        )
        summary = result.summary()
        assert "guardrails" in summary
        assert "completed" in summary
        assert "0.680" in summary

    def test_agent_context_record_and_lookup(self):
        ctx = AgentContext(
            run_id="r1",
            git_sha="abc",
            workflow_id="w1",
            target_model_id="m1",
            domain_id="d1",
            started_at=datetime.now(),
        )
        ctx.record("scout_output", {"readiness": 0.85})
        assert ctx.lookup("scout_output")["readiness"] == 0.85
        assert ctx.lookup("missing", default="none") == "none"

    def test_agent_output(self):
        out = AgentOutput(
            agent_id="scout",
            agent_role=AgentRole.SCOUT,
            status=TaskStatus.COMPLETED,
            decision="domain is ready",
            metrics={"readiness": 0.85},
        )
        assert out.agent_role == AgentRole.SCOUT


class TestWorkflow:
    def test_workflow_run_summary(self):
        run = WorkflowRun(
            run_id="r1",
            workflow_id="evaluate_only",
            git_sha="abc",
            config_hash="123",
            target_model_id="gemma-4-e4b",
            domain_id="trafficking",
            started_at=datetime.now(),
            status=TaskStatus.COMPLETED,
            total_cost_usd=4.20,
            total_duration_s=125.5,
        )
        summary = run.summary()
        assert "r1" in summary
        assert "gemma-4-e4b" in summary
        assert "$4.20" in summary


class TestProvenance:
    def test_minimum_provenance(self):
        p = _make_provenance()
        assert p.run_id == "test_run"
        assert p.git_sha == "abc123"
        assert p.checksum == "deadbeef"
