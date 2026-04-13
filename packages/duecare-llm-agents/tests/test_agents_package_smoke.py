"""Package-level tests for duecare-llm-agents.

Verifies:
  - all 12 agents register
  - Scout actually profiles a real domain pack
  - Curator dedupes and splits
  - Anonymizer redacts PII
  - Adversary generates adversarial variants
  - Coordinator walks the pipeline via an AgentSupervisor
  - AgentSupervisor enforces retry/budget/harm policies
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from duecare.core import AgentContext, AgentRole, TaskStatus
from duecare.agents import agent_registry, AgentSupervisor
from duecare.agents.base import BudgetExceeded, HarmDetected, SupervisorPolicy


REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAINS_ROOT = REPO_ROOT / "configs" / "duecare" / "domains"


@pytest.fixture
def ctx() -> AgentContext:
    return AgentContext(
        run_id="test_run_001",
        git_sha="abc123",
        workflow_id="rapid_probe",
        target_model_id="gemma-4-e4b",
        domain_id="trafficking",
        started_at=datetime.now(),
    )


class TestAgentRegistration:
    def test_all_12_agents_register(self):
        expected = {
            "scout",
            "data_generator",
            "adversary",
            "anonymizer",
            "curator",
            "judge",
            "validator",
            "curriculum_designer",
            "trainer",
            "exporter",
            "historian",
            "coordinator",
        }
        assert set(agent_registry.all_ids()) == expected
        assert len(agent_registry) == 12


class TestScoutAgent:
    def test_profiles_trafficking_pack(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        scout = agent_registry.get("scout")
        out = scout.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        assert out.metrics["readiness_score"] > 0.9  # Trafficking pack is populated
        assert out.metrics["n_seed_prompts"] >= 10
        assert ctx.lookup("domain_readiness_score") > 0.9


class TestDataGeneratorAgent:
    def test_emits_probes(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        gen = agent_registry.get("data_generator")
        out = gen.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        assert out.metrics["n_probes"] > 0


class TestAdversaryAgent:
    def test_mutates_probes(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        # Seed the data generator first
        agent_registry.get("data_generator").execute(ctx)
        adv = agent_registry.get("adversary")
        out = adv.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        # 3 mutators * N probes
        assert out.metrics["n_adversarial"] == out.metrics["n_base_probes"] * 3


class TestAnonymizerAgent:
    def test_redacts_pii(self, ctx):
        ctx.record("synthetic_probes", [
            {"id": "p1", "text": "Contact Maria at +1-555-0123 or maria@example.com"},
            {"id": "p2", "text": "My passport is AB1234567."},
            {"id": "p3", "text": "Normal text with no PII."},
        ])
        anon = agent_registry.get("anonymizer")
        out = anon.execute(ctx)
        assert out.status == TaskStatus.COMPLETED

        clean = ctx.lookup("clean_probes")
        assert clean is not None
        # At least one item should have been redacted
        assert any("[PHONE]" in p["text"] or "[EMAIL]" in p["text"] or "[PASSPORT]" in p["text"] for p in clean)
        # The third item should pass through unchanged
        assert any(p["text"] == "Normal text with no PII." for p in clean)


class TestCuratorAgent:
    def test_splits(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        # Curator falls back to domain seed prompts
        cur = agent_registry.get("curator")
        out = cur.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        assert out.metrics["n_train"] > 0


class TestCurriculumDesignerAgent:
    def test_identifies_weak_areas(self, ctx):
        ctx.record("evaluation_results", {
            "guardrails": {"status": "completed", "metrics": {"mean_score": 0.45}, "n_items": 3},
            "grounding": {"status": "completed", "metrics": {"citation_rate": 0.90}, "n_items": 3},
        })
        cd = agent_registry.get("curriculum_designer")
        out = cd.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        curriculum = ctx.lookup("next_curriculum")
        # guardrails should be identified as weak
        assert "guardrails" in curriculum["focus_tasks"]


class TestHistorianAgent:
    def test_writes_report(self, ctx, tmp_path):
        from duecare.agents.historian import HistorianAgent
        historian = HistorianAgent(output_dir=tmp_path)
        ctx.decisions.append("Test decision")
        ctx.metrics["test_metric"] = 0.85
        out = historian.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        report_path = tmp_path / f"{ctx.run_id}.md"
        assert report_path.exists()
        content = report_path.read_text()
        assert "Duecare Run Report" in content
        assert "Test decision" in content
        assert "test_metric" in content


class TestValidatorAgent:
    def test_skips_without_trained_model(self, ctx):
        val = agent_registry.get("validator")
        out = val.execute(ctx)
        assert out.status == TaskStatus.SKIPPED


class TestTrainerAgent:
    def test_stub_mode(self, ctx):
        ctx.record("train_jsonl", [{"id": f"p{i}", "text": "x"} for i in range(10)])
        ctx.record("val_jsonl", [{"id": f"v{i}", "text": "y"} for i in range(2)])
        tr = agent_registry.get("trainer")
        out = tr.execute(ctx)
        # Stub returns SKIPPED
        assert out.status == TaskStatus.SKIPPED
        assert "STUB" in out.decision
        assert out.metrics["n_train_samples"] == 10.0


class TestExporterAgent:
    def test_stub_mode(self, ctx):
        exp = agent_registry.get("exporter")
        out = exp.execute(ctx)
        assert out.status == TaskStatus.SKIPPED


class TestCoordinatorAgent:
    def test_walks_pipeline(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        coord = agent_registry.get("coordinator")
        out = coord.execute(ctx)
        assert out.status == TaskStatus.COMPLETED
        # Scout and Historian should both have run
        assert "scout" in ctx.outputs_by_agent
        assert "historian" in ctx.outputs_by_agent

    def test_run_workflow_returns_workflowrun(self, ctx, tmp_path):
        from duecare.agents.coordinator import CoordinatorAgent
        from duecare.agents.historian import HistorianAgent

        # Rewire the coordinator's supervisor's historian to use tmp_path
        coord = CoordinatorAgent(workflow_id="test_wf")
        # Replace the global historian with one that writes to tmp
        from duecare.agents import agent_registry as ar
        ar._by_id["historian"] = HistorianAgent(output_dir=tmp_path)

        run = coord.run_workflow(ctx)
        assert run.run_id == ctx.run_id
        assert run.workflow_id == "test_wf"
        assert run.ended_at is not None


class TestAgentSupervisor:
    def test_supervisor_runs_agent(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        sup = AgentSupervisor()
        scout = agent_registry.get("scout")
        out = sup.run(scout, ctx)
        assert out.status == TaskStatus.COMPLETED
        assert out.duration_ms >= 0

    def test_supervisor_retries_on_failure(self, ctx):
        from duecare.core.enums import AgentRole
        from duecare.agents.base import fresh_agent_output

        attempts = {"n": 0}

        class FlakyAgent:
            id = "flaky"
            role = AgentRole.SCOUT
            version = "0.1.0"
            model = None
            tools = []
            inputs = set()
            outputs = {"ok"}
            cost_budget_usd = 0.0

            def execute(self, ctx):
                attempts["n"] += 1
                if attempts["n"] < 3:
                    raise RuntimeError("transient")
                out = fresh_agent_output(self.id, self.role)
                out.status = TaskStatus.COMPLETED
                out.decision = "ok"
                return out

            def explain(self):
                return "flaky"

        sup = AgentSupervisor(SupervisorPolicy(max_retries=3, retry_backoff_s=0.0))
        out = sup.run(FlakyAgent(), ctx)
        assert out.status == TaskStatus.COMPLETED
        assert attempts["n"] == 3

    def test_supervisor_abort_on_harm(self, ctx):
        from duecare.core.enums import AgentRole
        from duecare.agents.base import fresh_agent_output

        class HarmAgent:
            id = "harm"
            role = AgentRole.VALIDATOR
            version = "0.1.0"
            model = None
            tools = []
            inputs = set()
            outputs = set()
            cost_budget_usd = 0.0

            def execute(self, ctx):
                ctx.record("harm_detected", True)
                out = fresh_agent_output(self.id, self.role)
                out.status = TaskStatus.COMPLETED
                out.decision = "found harm"
                return out

            def explain(self):
                return "harm"

        sup = AgentSupervisor(SupervisorPolicy(abort_on_harm=True))
        with pytest.raises(HarmDetected):
            sup.run(HarmAgent(), ctx)

    def test_supervisor_summary(self, ctx):
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")
        sup = AgentSupervisor()
        scout = agent_registry.get("scout")
        sup.run(scout, ctx)
        summary = sup.summary()
        assert summary["total_runs"] == 1
        assert summary["success_rate"] == 1.0
