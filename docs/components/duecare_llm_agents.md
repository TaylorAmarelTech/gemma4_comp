# Component — `duecare-llm-agents`

> **Status: shipped.** 12 agents + supervisor infrastructure, 17 tests
> passing, wheel built.

## What it is

The **DueCare swarm**: 12 autonomous agents that compose Tasks and Tools
into workflows, plus the **`AgentSupervisor`** meta-agent that wraps
every agent call with retry, budget, and abort-on-harm policies.

## The 12 agents

```
Scout → DataGenerator → Adversary → Anonymizer → Curator → Judge →
CurriculumDesigner → Trainer → Validator → Exporter → Historian

                              ▲
                              │
                        Coordinator
                  (Gemma 4 E4B + function calling)
```

| Agent | Role | What it produces |
|---|---|---|
| `scout` | Profiler | domain_readiness_score, domain_stats |
| `data_generator` | Teacher | synthetic_probes, graded_examples |
| `adversary` | Mutator | adversarial_probes (3 mutators × N base probes) |
| `anonymizer` | Hard PII gate | clean_probes, anon_audit, quarantine |
| `curator` | Dedupe + split | train_jsonl, val_jsonl, test_jsonl, split_stats |
| `judge` | Scorer | evaluation_results, per_category_breakdown |
| `validator` | Red-teamer | validation_report, no_harm_certificate |
| `curriculum_designer` | Iterator | next_curriculum (weak areas) |
| `trainer` | Fine-tuner | lora_adapters, merged_fp16 (stub until Unsloth extra) |
| `exporter` | Publisher | gguf_paths, hf_hub_url (stub until publishing deps) |
| `historian` | Narrator | run_report_md |
| `coordinator` | Orchestrator | workflow_run |

## AgentSupervisor

A meta-agent that wraps every agent call with:

- **Retry policy** — up to `max_retries` on transient exceptions, with
  exponential backoff
- **Hard budget cap** — tracks `cost_usd` across the whole run; raises
  `BudgetExceeded` before the next agent if over budget
- **Harm detection** — any agent can set `ctx.record("harm_detected",
  True)` to signal the Validator found new harm in the trained model;
  the Supervisor raises `HarmDetected` and aborts the workflow before
  the Exporter publishes anything
- **Telemetry** — `.summary()` returns `{total_runs, total_failures,
  total_cost_usd, success_rate}`

```python
from duecare.agents import agent_registry, AgentSupervisor
from duecare.agents.base import SupervisorPolicy

sup = AgentSupervisor(SupervisorPolicy(
    max_retries=3,
    hard_budget_usd=100.0,
    abort_on_harm=True,
))

scout = agent_registry.get("scout")
output = sup.run(scout, ctx)

print(sup.summary())
# {"total_runs": 1, "total_failures": 0, "total_cost_usd": 0.0, "success_rate": 1.0}
```

## Install

```bash
pip install duecare-llm-agents

# Or with the Trainer's heavy deps
pip install 'duecare-llm-agents[trainer]'  # pulls duecare-llm-models[unsloth]
```

## Quick start

```python
from datetime import datetime
from duecare.core import AgentContext
from duecare.agents import agent_registry

ctx = AgentContext(
    run_id="test_001",
    git_sha="abc",
    workflow_id="rapid_probe",
    target_model_id="gemma_4_e4b_stock",
    domain_id="trafficking",
    started_at=datetime.now(),
)

# Run Scout directly
scout = agent_registry.get("scout")
output = scout.execute(ctx)
print(output.decision)
# Domain 'trafficking' ready (score=1.00): 12 prompts, 10 evidence, 5 categories

# Or wrap it in a supervisor
from duecare.agents import AgentSupervisor
sup = AgentSupervisor()
output = sup.run(scout, ctx)
```

## Design decisions

### 1. Agents are instances, not classes

Every agent registers a **pre-instantiated** instance in
`agent_registry`. This is different from the model adapter pattern
(which registers classes to be constructed with config). Reason:
agents are singletons per run, don't take per-call config, and need
to be reconstructable without arguments.

### 2. `NoopModel` for model-free agents

Curator, Adversary, Anonymizer, Historian, Exporter, and Coordinator
don't call an LLM. They have `model = noop_model()` which raises if
anyone tries to call `.generate()`. This means every agent has a
`model` attribute (satisfying the `Agent` protocol) but the type
system doesn't lie about which agents need a real one.

### 3. Decisions live in the shared context

Every agent writes its decision to `ctx.outputs_by_agent[role]` as
well as the `ctx.decisions` list. The Historian walks this shared
blackboard to build the run report. No per-agent persistence.

### 4. The supervisor is NOT registered in the swarm

`AgentSupervisor` doesn't appear in `agent_registry` because it's a
meta-agent, not a peer of the other 12. It's created by whoever wants
to run an agent with policies — typically the `WorkflowRunner`.

## Tests

17 tests passing:

- All 12 agents register
- Scout actually profiles the trafficking domain pack (readiness 1.00)
- DataGenerator emits probes
- Adversary mutates probes (3 mutators × N)
- Anonymizer redacts PII in test fixtures
- Curator splits with dedup
- CurriculumDesigner identifies weak areas from mock evaluation results
- Historian writes a real markdown report to a tmp dir
- Validator skips without a trained model (correct behavior)
- Trainer/Exporter stub modes return SKIPPED with clear TODOs
- Coordinator walks a pipeline via the supervisor
- AgentSupervisor retries a flaky agent 3 times and succeeds
- AgentSupervisor aborts on `harm_detected=True`
- AgentSupervisor tracks summary stats correctly

## Status

- [x] 12 agents implemented
- [x] AgentSupervisor with retry / budget / harm-abort policies
- [x] 17 tests passing
- [x] Wheel built + installed
- [ ] Trainer: MVP stub; real implementation needs `duecare-llm-models[unsloth]`
- [ ] Exporter: MVP stub; real implementation needs `duecare-llm-publishing[hf-hub]`
- [ ] Coordinator: rule-based DAG walker; full version needs Gemma 4
      function calling integration

## License

MIT.
