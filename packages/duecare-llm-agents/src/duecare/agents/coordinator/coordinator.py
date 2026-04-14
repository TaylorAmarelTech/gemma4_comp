"""Coordinator agent - orchestrates the DueCare swarm.

Two execution modes:
- **Rule-based DAG (default):** sequential topological walk of a
  predefined pipeline. Deterministic, fast, no model required.
- **Gemma 4 function calling:** set `use_gemma_orchestration=True` and
  pass a Gemma 4 model. The Coordinator exposes each swarm agent as a
  tool (run_scout, run_judge, run_anonymizer, ...), asks Gemma 4 what
  to do next given current blackboard state, and follows its tool
  calls until the workflow completes or a max-step budget is hit.
  This is the load-bearing use of Gemma 4's native function calling.
"""

from __future__ import annotations

from datetime import datetime

from duecare.core.contracts import Model
from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.schemas import (
    AgentContext,
    AgentOutput,
    ChatMessage,
    ToolSpec,
    WorkflowRun,
)
from duecare.agents import agent_registry
from duecare.agents.base import AgentSupervisor, fresh_agent_output, noop_model


# Tools exposed to Gemma 4 in function-calling mode. One per agent in
# the swarm. The Coordinator dispatches by name when Gemma 4 emits a
# tool call matching one of these.
def _build_agent_tools() -> list[ToolSpec]:
    """Build the ToolSpec set exposing every registered agent."""
    tools: list[ToolSpec] = []
    empty_params = {"type": "object", "properties": {}}
    for agent_id in agent_registry.all_ids():
        if agent_id == "coordinator":
            continue  # don't let it call itself
        tools.append(
            ToolSpec(
                name=f"run_{agent_id}",
                description=(
                    f"Execute the {agent_id} agent on the current blackboard. "
                    "Returns the agent's output and updates shared context."
                ),
                parameters=empty_params,
            )
        )
    tools.append(
        ToolSpec(
            name="finish_workflow",
            description="Mark the workflow complete. Call when all needed agents have run.",
            parameters=empty_params,
        )
    )
    return tools


class CoordinatorAgent:
    id = "coordinator"
    role = AgentRole.COORDINATOR
    version = "0.2.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = set()
    outputs: set[str] = {"workflow_run"}
    cost_budget_usd = 1.0

    DEFAULT_PIPELINE: list[str] = ["scout", "historian"]

    def __init__(
        self,
        workflow_id: str = "adhoc",
        supervisor: AgentSupervisor | None = None,
        *,
        use_gemma_orchestration: bool = False,
        orchestrator_model: Model | None = None,
        max_orchestration_steps: int = 12,
    ) -> None:
        self.workflow_id = workflow_id
        self.supervisor = supervisor or AgentSupervisor()
        self.use_gemma_orchestration = use_gemma_orchestration
        self.orchestrator_model = orchestrator_model
        self.max_orchestration_steps = max_orchestration_steps

    # ── Rule-based DAG mode (default, backwards-compatible) ──

    def _execute_rule_based(self, ctx: AgentContext) -> list[str]:
        """Sequential topological walk of DEFAULT_PIPELINE."""
        executed: list[str] = []
        for agent_id in self.DEFAULT_PIPELINE:
            if not agent_registry.has(agent_id):
                continue
            agent = agent_registry.get(agent_id)
            self.supervisor.run(agent, ctx)
            executed.append(agent_id)
        return executed

    # ── Gemma 4 function-calling mode ──

    def _execute_gemma_orchestrated(self, ctx: AgentContext) -> list[str]:
        """Let Gemma 4 schedule the swarm via native function calls.

        The Coordinator loops: ask Gemma 4 what to do next, dispatch each
        tool call to the matching agent, report results back, repeat.
        Stops on `finish_workflow` tool call or when max_orchestration_steps
        is reached (safety cap).
        """
        if self.orchestrator_model is None:
            # Fallback to rule-based if no model supplied
            return self._execute_rule_based(ctx)

        tools = _build_agent_tools()
        executed: list[str] = []
        conversation: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are the DueCare Coordinator. Run the swarm by calling "
                    "tools in the best order for a trafficking safety evaluation. "
                    "Start with `run_scout` to profile the domain, then call the "
                    "agents you need (anonymizer, curator, judge, historian, ...). "
                    "Call `finish_workflow` when done."
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"Target model: {ctx.target_model_id}. "
                    f"Domain: {ctx.domain_id}. "
                    "Schedule the swarm."
                ),
            ),
        ]

        for _ in range(self.max_orchestration_steps):
            gen = self.orchestrator_model.generate(
                messages=conversation,
                tools=tools,
                max_tokens=256,
                temperature=0.0,
            )
            if not gen.tool_calls:
                break  # model decided not to call any tool; stop
            for call in gen.tool_calls:
                if call.name == "finish_workflow":
                    return executed
                if call.name.startswith("run_"):
                    agent_id = call.name[len("run_"):]
                    if agent_registry.has(agent_id):
                        agent = agent_registry.get(agent_id)
                        self.supervisor.run(agent, ctx)
                        executed.append(agent_id)
                        conversation.append(
                            ChatMessage(
                                role="tool",
                                content=f"Ran {agent_id}. Continue or finish?",
                                name=call.name,
                            )
                        )
        return executed

    # ── Public execute ──

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            if self.use_gemma_orchestration:
                executed = self._execute_gemma_orchestrated(ctx)
                mode = "gemma4-function-calling"
            else:
                executed = self._execute_rule_based(ctx)
                mode = "rule-based-dag"

            out.status = TaskStatus.COMPLETED
            out.decision = (
                f"Ran {len(executed)} agents via {mode}: {', '.join(executed)}"
            )
            out.metrics = {**self.supervisor.summary(), "orchestration_mode": mode}
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def run_workflow(self, ctx: AgentContext) -> WorkflowRun:
        output = self.execute(ctx)
        return WorkflowRun(
            run_id=ctx.run_id,
            workflow_id=self.workflow_id,
            git_sha=ctx.git_sha,
            config_hash="",
            target_model_id=ctx.target_model_id,
            domain_id=ctx.domain_id,
            started_at=ctx.started_at,
            ended_at=datetime.now(),
            status=output.status,
            final_metrics=output.metrics,
            total_cost_usd=self.supervisor.total_cost_usd,
        )

    def explain(self) -> str:
        mode = "Gemma 4 native function calling" if self.use_gemma_orchestration else "rule-based DAG"
        return f"Orchestrate the DueCare swarm via {mode}."


agent_registry.add("coordinator", CoordinatorAgent())
