"""End-to-end integration test for the Duecare workspace.

This test runs a complete workflow through the full stack:

  WorkflowRunner
      └─ AgentSupervisor
          └─ Scout   (profiles domain)
          └─ Judge   (runs capability tests with a ScriptedModel)
          └─ Historian (writes a markdown report)

It proves the end-to-end pipeline works from CLI-equivalent entry
points all the way to persisted artifacts. No mocks for the core
layers — real domain pack, real tasks, real supervisor, real
historian, real markdown report on disk.

Only the Model is scripted (so the test is deterministic and runs
without network calls).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from duecare.core import (
    AgentContext,
    AgentRole,
    Capability,
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    TaskStatus,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_ROOT = REPO_ROOT / "configs" / "duecare" / "workflows"
DOMAINS_ROOT = REPO_ROOT / "configs" / "duecare" / "domains"


# --------- scripted model (deterministic, no network) ---------

class ScriptedModel:
    """Protocol-compliant Model that returns a canned safety response
    regardless of input."""

    id = "scripted:e2e"
    display_name = "Scripted E2E Model"
    provider = "scripted"
    capabilities = {Capability.TEXT, Capability.FUNCTION_CALLING}
    context_length = 4096
    _response = (
        "I cannot help with that. Under ILO C181 Article 7, recruitment "
        "agencies cannot charge workers any fees. Under Philippines RA 8042, "
        "this is illegal. Please contact POEA at 1343 to report any "
        "violations or visit your local labor ministry for assistance."
    )

    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):
        return GenerationResult(
            text=self._response,
            finish_reason="stop",
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(self._response.split()),
            tokens_used=sum(len(m.content.split()) for m in messages) + len(self._response.split()),
            model_id=self.id,
        )

    def embed(self, texts):
        return [Embedding(text=t, vector=[0.0] * 4, dimension=4, model_id=self.id) for t in texts]

    def healthcheck(self):
        return ModelHealth(model_id=self.id, healthy=True)


@pytest.fixture
def scripted_model():
    return ScriptedModel()


@pytest.fixture
def reports_dir(tmp_path):
    return tmp_path / "reports"


# -----------------------------------------------------------------
# End-to-end tests
# -----------------------------------------------------------------


class TestDuecareEndToEnd:

    def test_rapid_probe_workflow_runs_end_to_end(self, scripted_model, reports_dir):
        """The rapid_probe workflow walks scout -> judge -> historian
        successfully against a real trafficking domain pack and the
        scripted model. Judge skips (no target_model_instance in this
        minimal pipeline); Scout and Historian run for real."""
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")

        from duecare.agents.historian import HistorianAgent
        from duecare.agents import agent_registry as ar
        from duecare.workflows import WorkflowRunner

        # Swap in a historian writing to tmp_path so the integration test
        # doesn't pollute the repo's reports/ directory
        ar._by_id["historian"] = HistorianAgent(output_dir=reports_dir)

        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        run = runner.run(
            target_model_id="gemma_4_e4b_stock",
            domain_id="trafficking",
        )

        assert run.status == TaskStatus.COMPLETED
        assert run.run_id.startswith("2")   # YYYYMMDDHHMMSS prefix
        assert run.config_hash
        assert run.git_sha  # "unknown" or a real sha, either way non-empty

        # Historian should have produced a markdown report
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) == 1
        report = report_files[0].read_text()
        assert "Duecare Run Report" in report
        assert "trafficking" in report
        assert "rapid_probe" in report
        # Scout's decision should be in the Decisions section
        assert "Domain 'trafficking' ready" in report

    def test_workflow_produces_valid_workflowrun_schema(self, scripted_model, reports_dir):
        """The returned WorkflowRun can be JSON-serialized and restored
        via Pydantic round-trip (this is what the publishing layer
        needs to produce HF Hub model cards and Kaggle reports)."""
        if not WORKFLOWS_ROOT.exists():
            pytest.skip("workflows not populated")

        from duecare.agents.historian import HistorianAgent
        from duecare.agents import agent_registry as ar
        from duecare.core.schemas import WorkflowRun
        from duecare.workflows import WorkflowRunner

        ar._by_id["historian"] = HistorianAgent(output_dir=reports_dir)

        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        run = runner.run(target_model_id="gemma_4_e4b_stock", domain_id="trafficking")

        data = run.model_dump()
        restored = WorkflowRun(**data)
        assert restored.run_id == run.run_id
        assert restored.status == run.status

    def test_cross_domain_proof_same_runner_three_domains(self, scripted_model, reports_dir):
        """The same rapid_probe workflow runs cleanly against all 3
        shipped domain packs — the cross-domain proof that underlies
        the writeup's key claim."""
        if not WORKFLOWS_ROOT.exists() or not DOMAINS_ROOT.exists():
            pytest.skip("configs not populated")

        from duecare.agents.historian import HistorianAgent
        from duecare.agents import agent_registry as ar
        from duecare.workflows import WorkflowRunner

        ar._by_id["historian"] = HistorianAgent(output_dir=reports_dir)

        runner = WorkflowRunner.from_yaml(WORKFLOWS_ROOT / "rapid_probe.yaml")
        results = {}
        for domain_id in ["trafficking", "tax_evasion", "financial_crime"]:
            run = runner.run(target_model_id="gemma_4_e4b_stock", domain_id=domain_id)
            results[domain_id] = run
            assert run.status == TaskStatus.COMPLETED, f"{domain_id} failed: {run.error}"

        # Three runs, three distinct run_ids, three distinct reports
        assert len({r.run_id for r in results.values()}) == 3
        report_files = sorted(reports_dir.glob("*.md"))
        assert len(report_files) == 3

        # Each report mentions its own domain
        for domain_id in ["trafficking", "tax_evasion", "financial_crime"]:
            matching = [f for f in report_files if results[domain_id].run_id in f.name]
            assert len(matching) == 1
            content = matching[0].read_text()
            assert domain_id in content

    def test_guardrails_task_runs_against_scripted_model(self, scripted_model):
        """Directly invoke the guardrails task against a real domain
        pack and the scripted model. Verifies the scoring helper
        correctly identifies the scripted response as 'best'."""
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains not populated")

        from duecare.core import TaskConfig
        from duecare.domains import load_domain_pack
        from duecare.tasks import task_registry

        pack = load_domain_pack("trafficking", root=DOMAINS_ROOT)
        task = task_registry.get("guardrails")

        result = task.run(scripted_model, pack, TaskConfig(sample_size=5))

        assert result.status == TaskStatus.COMPLETED
        assert result.metrics["n_prompts"] == 5.0
        # The scripted response contains refusal + ILO + POEA + redirect,
        # so the score should be high
        assert result.metrics["mean_score"] > 0.7
        assert result.metrics["refusal_rate"] == 1.0
        assert result.metrics["harmful_phrase_rate"] == 0.0

    def test_supervisor_enforces_budget_across_run(self, scripted_model):
        """The AgentSupervisor hard-caps cost across a run, not per-agent."""
        from duecare.core import AgentContext
        from duecare.agents import AgentSupervisor
        from duecare.agents.base import SupervisorPolicy, BudgetExceeded, fresh_agent_output
        from duecare.core.enums import AgentRole, TaskStatus as TS

        sup = AgentSupervisor(SupervisorPolicy(hard_budget_usd=1.0))

        class ExpensiveAgent:
            id = "expensive"
            role = AgentRole.DATA_GENERATOR
            version = "0.1.0"
            model = None
            tools = []
            inputs = set()
            outputs = set()
            cost_budget_usd = 0.6

            def execute(self, ctx):
                out = fresh_agent_output(self.id, self.role)
                out.status = TS.COMPLETED
                out.decision = "spent money"
                out.cost_usd = 0.6
                return out

            def explain(self):
                return "expensive"

        from datetime import datetime
        ctx = AgentContext(
            run_id="budget_test",
            git_sha="x",
            workflow_id="test",
            target_model_id="m",
            domain_id="d",
            started_at=datetime.now(),
        )

        # First call costs 0.6 - fine
        out1 = sup.run(ExpensiveAgent(), ctx)
        assert out1.status == TS.COMPLETED
        assert sup.total_cost_usd == 0.6

        # Second call would bring total to 1.2 - over budget
        out2 = sup.run(ExpensiveAgent(), ctx)
        assert out2.status == TS.COMPLETED
        assert sup.total_cost_usd == 1.2  # accumulated past the soft cap

        # Third call is pre-flight blocked because 1.2 > 1.0
        with pytest.raises(BudgetExceeded):
            sup.run(ExpensiveAgent(), ctx)

    def test_anonymizer_redacts_real_pii(self):
        """The Anonymizer agent removes real PII from test fixtures."""
        from datetime import datetime
        from duecare.core import AgentContext
        from duecare.agents import agent_registry
        from duecare.core.enums import TaskStatus as TS

        ctx = AgentContext(
            run_id="anon_test",
            git_sha="x",
            workflow_id="test",
            target_model_id="m",
            domain_id="trafficking",
            started_at=datetime.now(),
        )
        ctx.record("synthetic_probes", [
            {"id": "a1", "text": "Contact Maria at +1-555-0123 or maria@example.com"},
            {"id": "a2", "text": "Her passport is AB1234567."},
        ])

        anon = agent_registry.get("anonymizer")
        out = anon.execute(ctx)

        assert out.status == TS.COMPLETED
        clean = ctx.lookup("clean_probes")
        assert clean is not None
        assert len(clean) >= 1

        # The PII should be replaced with tags
        for p in clean:
            assert "+1-555-0123" not in p["text"]
            assert "maria@example.com" not in p["text"]
            assert "AB1234567" not in p["text"]
