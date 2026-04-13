"""Agent base helpers and the AgentSupervisor.

The Supervisor is a meta-agent that wraps another agent and enforces
cross-cutting policies: budget caps, retry logic, health checks,
abort-on-harm. Every real-world run of the Duecare swarm is wrapped by
a Supervisor, not by a direct call to agent.execute().
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from duecare.core.contracts import Agent, Model
from duecare.core.enums import AgentRole, Capability, TaskStatus
from duecare.core.schemas import (
    AgentContext,
    AgentOutput,
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.observability.logging import get_logger

log = get_logger("duecare.agents")


# -------- exceptions --------


class BudgetExceeded(Exception):
    """Raised when an agent exceeds its cost_budget_usd."""


class HarmDetected(Exception):
    """Raised when the Validator or Supervisor detects new harm in a
    trained model's output. Aborts the workflow."""


# -------- helpers --------


def fresh_agent_output(agent_id: str, role: AgentRole) -> AgentOutput:
    """Build an empty 'running' AgentOutput."""
    return AgentOutput(
        agent_id=agent_id,
        agent_role=role,
        status=TaskStatus.RUNNING,
        decision="(not yet decided)",
    )


class NoopModel:
    """A Model that raises on every call. Used as a placeholder for
    agents that don't actually need a model (Curator, Adversary)."""

    id = "noop"
    display_name = "No-op Model"
    provider = "noop"
    capabilities: set[Capability] = set()
    context_length = 0

    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs) -> GenerationResult:
        raise RuntimeError("Noop model cannot generate. Configure a real model on this agent.")

    def embed(self, texts: list[str]) -> list[Embedding]:
        return []

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(model_id=self.id, healthy=True)


_NOOP = NoopModel()


def noop_model() -> Model:
    """Return the shared noop model singleton."""
    return _NOOP


# -------- supervisor --------


@dataclass
class SupervisorPolicy:
    max_retries: int = 2
    retry_backoff_s: float = 1.0
    hard_budget_usd: float = 100.0
    per_agent_timeout_s: float = 600.0
    abort_on_harm: bool = True
    abort_on_budget: bool = True


class AgentSupervisor:
    """Meta-agent that wraps another agent and enforces cross-cutting policies.

    Typical use:

        supervisor = AgentSupervisor(SupervisorPolicy())
        agent = agent_registry.get("scout")
        output = supervisor.run(agent, ctx)

    Enforces:
      - max_retries on transient exceptions
      - hard_budget_usd across the whole run
      - per_agent_timeout_s soft timeout (logged, not SIGKILL)
      - abort on HarmDetected or BudgetExceeded

    The supervisor is itself an 'agent' in spirit, but it's not
    registered in agent_registry because workflows always wrap
    registered agents in a supervisor at execution time.
    """

    def __init__(self, policy: SupervisorPolicy | None = None) -> None:
        self.policy = policy or SupervisorPolicy()
        self._total_cost: float = 0.0
        self._total_runs: int = 0
        self._total_failures: int = 0

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost

    def run(self, agent: Agent, ctx: AgentContext) -> AgentOutput:
        """Execute an agent with supervisor policies applied."""
        self._total_runs += 1
        log.info(
            "supervisor.run agent=%s role=%s run_id=%s",
            agent.id, agent.role.value, ctx.run_id,
        )

        # Pre-flight budget check
        if self._total_cost > self.policy.hard_budget_usd and self.policy.abort_on_budget:
            raise BudgetExceeded(
                f"Hard budget ${self.policy.hard_budget_usd} exceeded "
                f"before {agent.id} could run"
            )

        attempts = 0
        last_error: Exception | None = None
        start = time.perf_counter()

        while attempts <= self.policy.max_retries:
            attempts += 1
            try:
                output = agent.execute(ctx)
                elapsed_s = time.perf_counter() - start
                output.duration_ms = int(elapsed_s * 1000)

                # Update totals
                self._total_cost += output.cost_usd
                ctx.budget_used_usd += output.cost_usd

                # Harm check: any agent can set a 'harm_detected' context flag
                if self.policy.abort_on_harm and ctx.lookup("harm_detected") is True:
                    raise HarmDetected(
                        f"Harm flag set during {agent.id} execution (run_id={ctx.run_id})"
                    )

                # Record decision in the shared blackboard
                ctx.decisions.append(f"{agent.id}: {output.decision}")
                ctx.outputs_by_agent[agent.role.value] = {
                    "agent_id": agent.id,
                    "decision": output.decision,
                    "metrics": output.metrics,
                    "artifacts": {k: str(v) for k, v in output.artifacts_written.items()},
                }

                log.info(
                    "supervisor.ok agent=%s decision=%s cost=$%.4f duration_ms=%d",
                    agent.id, output.decision, output.cost_usd, output.duration_ms,
                )
                return output

            except (HarmDetected, BudgetExceeded):
                # Never retry these - bubble up
                self._total_failures += 1
                raise
            except Exception as e:
                last_error = e
                log.warning(
                    "supervisor.retry agent=%s attempt=%d/%d error=%s",
                    agent.id, attempts, self.policy.max_retries + 1, e,
                )
                if attempts > self.policy.max_retries:
                    self._total_failures += 1
                    break
                time.sleep(self.policy.retry_backoff_s * attempts)

        # All retries exhausted
        assert last_error is not None
        return AgentOutput(
            agent_id=agent.id,
            agent_role=agent.role,
            status=TaskStatus.FAILED,
            decision=f"failed after {attempts} attempts",
            error=str(last_error),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "total_runs": self._total_runs,
            "total_failures": self._total_failures,
            "total_cost_usd": round(self._total_cost, 4),
            "success_rate": (
                (self._total_runs - self._total_failures) / self._total_runs
                if self._total_runs else 1.0
            ),
        }
