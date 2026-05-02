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
    TrainingDatasetManifest,
    TrainingExample,
    TrainingMessage,
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
    def test_chat_message_roles(self) -> None:
        for role in ("system", "user", "assistant", "tool"):
            msg = ChatMessage(role=role, content="hello")
            assert msg.role == role
            assert msg.content == "hello"

    def test_tool_spec_to_openai(self) -> None:
        tool = ToolSpec(
            name="anonymize",
            description="Strip PII from text",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        )
        openai = tool.to_openai()
        assert openai["type"] == "function"
        assert openai["function"]["name"] == "anonymize"
        assert openai["function"]["parameters"]["type"] == "object"

    def test_tool_spec_to_anthropic(self) -> None:
        tool = ToolSpec(name="classify", description="Label text")
        anthropic = tool.to_anthropic()
        assert anthropic["name"] == "classify"
        assert "input_schema" in anthropic

    def test_tool_call_roundtrip(self) -> None:
        call = ToolCall(name="anonymize", arguments={"text": "Maria"})
        data = call.model_dump()
        restored = ToolCall(**data)
        assert restored == call


class TestGeneration:
    def test_generation_result_required_fields(self) -> None:
        result = GenerationResult(text="hi", model_id="gemma-4-e4b", finish_reason="stop")
        assert result.tokens_used == 0
        assert result.cost_usd == 0.0
        assert result.tool_calls == []

    def test_embedding_dimension(self) -> None:
        emb = Embedding(
            text="hello", vector=[0.1, 0.2, 0.3], dimension=3, model_id="sbert"
        )
        assert emb.dimension == 3
        assert len(emb.vector) == 3

    def test_model_health(self) -> None:
        health = ModelHealth(model_id="m1", healthy=True, details={"latency_ms": 42})
        assert health.healthy
        assert health.details["latency_ms"] == 42


class TestDomain:
    def test_domain_card_roundtrip(self) -> None:
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

    def test_issue_with_severity(self) -> None:
        issue = Issue(
            type="missed_indicator",
            description="Missed passport retention",
            severity=Severity.HIGH,
            documentation_ref="ilo_c181",
        )
        assert issue.severity == Severity.HIGH

    def test_response_example(self) -> None:
        ex = ResponseExample(
            text="I cannot help with this.",
            grade=Grade.GOOD,
            score=0.82,
            explanation="Refuses correctly but doesn't cite sources",
        )
        assert ex.grade == Grade.GOOD
        assert 0.0 <= ex.score <= 1.0


class TestTaskAndAgent:
    def test_task_config_defaults(self) -> None:
        config = TaskConfig()
        assert config.sample_size is None
        assert config.seed == 3407
        assert config.temperature == 0.0

    def test_item_result(self) -> None:
        item = ItemResult(
            item_id="prompt_001",
            scores={"grade_exact_match": 1.0},
            grade=Grade.BEST,
        )
        assert item.grade == Grade.BEST
        assert item.scores["grade_exact_match"] == 1.0

    def test_task_result_summary(self) -> None:
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

    def test_agent_context_record_and_lookup(self) -> None:
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

    def test_agent_output(self) -> None:
        out = AgentOutput(
            agent_id="scout",
            agent_role=AgentRole.SCOUT,
            status=TaskStatus.COMPLETED,
            decision="domain is ready",
            metrics={"readiness": 0.85},
        )
        assert out.agent_role == AgentRole.SCOUT


class TestWorkflow:
    def test_workflow_run_summary(self) -> None:
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


class TestTrainingSchemas:
    def test_training_example_roundtrip(self) -> None:
        example = TrainingExample(
            prompt_id="prompt_001",
            grade="best",
            type="positive",
            text=(
                "<start_of_turn>user\nIs this fee scheme legal?<end_of_turn>\n"
                "<start_of_turn>model\nI cannot help with that exploitative"
                " scheme.<end_of_turn>"
            ),
            messages=[
                TrainingMessage(role="user", content="Is this fee scheme legal?"),
                TrainingMessage(
                    role="assistant",
                    content="I cannot help with that exploitative scheme.",
                ),
            ],
            category="financial_crime_blindness",
            source="taylor_amarel_tests",
            source_record_ids=["prompt_001"],
            source_record_checksums=["abc123"],
            provenance=_make_provenance(),
        )

        restored = TrainingExample(**example.model_dump(by_alias=True))
        assert restored.prompt_id == "prompt_001"
        assert restored.example_type == "positive"
        assert restored.messages[-1].role == "assistant"

    def test_training_example_allows_contrast_grade(self) -> None:
        example = TrainingExample(
            prompt_id="prompt_002",
            grade="contrast",
            type="negative",
            text="<start_of_turn>user\nQuestion<end_of_turn>",
            messages=[TrainingMessage(role="user", content="Question")],
            provenance=_make_provenance(),
        )
        assert example.grade == "contrast"

    def test_training_dataset_manifest_roundtrip(self) -> None:
        manifest = TrainingDatasetManifest(
            run_id="run_001",
            git_sha="abc123",
            created_at=datetime.now(),
            source_path="configs/duecare/domains/trafficking/seed_prompts.jsonl",
            source_checksum="deadbeef",
            output_dir="data/training",
            n_source_prompts=10,
            n_examples=20,
            n_positive=18,
            n_negative=2,
            split_counts={"train": 16, "val": 2, "test": 2},
            split_checksums={"train": "aa", "val": "bb", "test": "cc"},
            grade_distribution={"best": 10, "good": 8, "contrast": 2},
            type_distribution={"positive": 18, "negative": 2},
            include_negative=True,
            max_examples=20,
            seed=42,
        )

        restored = TrainingDatasetManifest(**manifest.model_dump())
        assert restored.n_examples == 20
        assert restored.split_counts["train"] == 16


class TestProvenance:
    def test_minimum_provenance(self) -> None:
        p = _make_provenance()
        assert p.run_id == "test_run"
        assert p.git_sha == "abc123"
        assert p.checksum == "deadbeef"
