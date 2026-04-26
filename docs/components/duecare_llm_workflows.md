# Component — `duecare-llm-workflows`

> **Status: shipped.** YAML loader + topological DAG runner + 9 tests
> passing, wheel built.

## What it is

The orchestration layer. Reads a workflow YAML, topologically sorts
the agent DAG, walks it via an `AgentSupervisor`, and returns a
`WorkflowRun` record.

## What ships

- `Workflow`, `AgentStep`, `WorkflowBudget`, `RetryPolicy`,
  `FailurePolicy`, `CoordinatorConfig` — Pydantic models
- `load_workflow(path)` — YAML parser
- `topological_sort(dag)` — pure topological sort with cycle
  detection
- `WorkflowRunner` — the runner that walks the DAG

## Install

```bash
pip install duecare-llm-workflows
```

## Quick start

```python
from duecare.workflows import WorkflowRunner

runner = WorkflowRunner.from_yaml("configs/duecare/workflows/rapid_probe.yaml")
run = runner.run(
    target_model_id="gemma_4_e4b_stock",
    domain_id="trafficking",
)

print(run.summary())
# run=... workflow=rapid_probe model=gemma_4_e4b_stock domain=trafficking status=completed cost=$0.00 duration=2.1s
```

## Workflow YAML shape

```yaml
id: rapid_probe
description: "5-minute smoke test"
inputs:
  target_model_id: required
  domain_id: required
budget:
  max_cost_usd: 1.0
  max_wall_clock_hours: 0.25
agents:
  - id: scout
    needs: []
  - id: judge
    needs: [scout]
    config:
      evaluated_model: ${inputs.target_model_id}
  - id: historian
    needs: [scout, judge]
coordinator:
  retry_policy:
    max_attempts: 2
    backoff: exponential
```

## Design decisions

### 1. Topological sort + deterministic tie-breaking

The `topological_sort` is a pure function on a list of `(node_id, deps)`
pairs. On each iteration it picks nodes with zero remaining
dependencies in **alphabetical order** for deterministic runs. Raises
`ValueError` on cycles with the nodes involved in the cycle listed.

### 2. Supervisor-per-run, not shared

The `WorkflowRunner` creates a **new** `AgentSupervisor` for each
`.run()` call. Supervisors hold state (total cost, failure count) and
shouldn't be shared across workflow runs.

### 3. Failure policies

Three configurable failure policies (from `configs/duecare/workflows/`):

- `on_validator_harm_flag: abort` — raise `HarmDetected` and stop
- `on_budget_exceeded: snapshot_and_stop` — freeze state and return
- `on_agent_error: retry_then_skip` — up to N retries, then skip the
  agent and continue

## Tests

9 tests passing:

- `topological_sort` handles linear + diamond + cycle + unknown-dep
  cases
- `load_workflow` loads all 4 shipped YAML files
- `Workflow` Pydantic round-trip
- `WorkflowRunner.run(rapid_probe)` against trafficking domain
  completes successfully
- Cycle in DAG produces `WorkflowRun.status = failed` with a helpful
  error message

## Status

- [x] Loader + Pydantic models
- [x] Topological sort with cycle detection
- [x] Runner with supervisor integration
- [x] 4 workflow YAMLs shipped in `configs/duecare/workflows/`
- [x] 9 tests passing
- [x] Wheel built + installed

## License

MIT.
