#!/usr/bin/env python3
"""implement_component_docs.py - Write component docs for the 7 remaining packages."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


DOCS = {

    "docs/components/duecare_llm_models.md": '''# Component — `duecare-llm-models`

> **Status: shipped.** 8 adapters, 22 tests passing, wheel built,
> installed from the wheel.

## What it is

Eight pluggable model adapters, all implementing the `duecare.core.Model`
protocol. Every backend that Duecare supports ships as its own folder
inside this package. Adding a new backend is a new folder — not a
refactor.

## Adapters shipped

| Id | Folder | Use case |
|---|---|---|
| `transformers` | `transformers_adapter/` | Any HF-hosted causal LM, 4-bit via bitsandbytes |
| `llama_cpp` | `llama_cpp_adapter/` | GGUF files via llama-cpp-python (primary runtime for the Duecare demo) |
| `unsloth` | `unsloth_adapter/` | Unsloth FastLanguageModel for fast inference + fine-tune |
| `ollama` | `ollama_adapter/` | Local Ollama server via stdlib urllib (no extra deps) |
| `openai_compatible` | `openai_compatible_adapter/` | Any provider with the OpenAI chat schema: OpenAI, DeepSeek, Together, Groq, Fireworks, OpenRouter, Mistral |
| `anthropic` | `anthropic_adapter/` | Claude Messages API |
| `google_gemini` | `google_gemini_adapter/` | Hosted Gemini via google-generativeai |
| `hf_inference_endpoint` | `hf_inference_endpoint_adapter/` | Any HF Inference Endpoint |

Every adapter is registered in `model_registry` on import. Tool Search
loads adapter schemas lazily, so you can `pip install duecare-llm-models`
without pulling in torch, transformers, unsloth, or llama-cpp-python.

## Install

```bash
# Base (no heavy ML deps)
pip install duecare-llm-models

# With specific backends (extras)
pip install 'duecare-llm-models[transformers]'  # + transformers + torch + bitsandbytes
pip install 'duecare-llm-models[unsloth]'        # + unsloth + peft + trl
pip install 'duecare-llm-models[llama-cpp]'      # + llama-cpp-python
pip install 'duecare-llm-models[ollama]'         # + ollama client
pip install 'duecare-llm-models[openai]'         # + openai client (optional; stdlib works too)
pip install 'duecare-llm-models[anthropic]'      # + anthropic client (optional)
pip install 'duecare-llm-models[google]'         # + google-generativeai
pip install 'duecare-llm-models[hf-endpoint]'    # + huggingface_hub
pip install 'duecare-llm-models[all]'            # everything
```

## Quick start

```python
from duecare.core import ChatMessage
from duecare.models.openai_compatible_adapter import OpenAICompatibleModel

m = OpenAICompatibleModel(
    model_id="gpt-4o-mini",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
)

result = m.generate([
    ChatMessage(role="user", content="Hello, Duecare."),
])

print(result.text)
print(f"Tokens: {result.tokens_used}, Latency: {result.latency_ms}ms")
```

Every adapter exposes the same `Model` protocol. You can swap one line
and target a different backend without changing any downstream code.

## Design decisions

### 1. Lazy imports of heavy dependencies

`transformers`, `unsloth`, `llama-cpp-python`, and `google-generativeai`
are imported **inside** the adapter's `_load()` method, not at module
import time. This means:

- `import duecare.models` takes milliseconds on any Python environment
- `TransformersModel` instances can be constructed without torch installed
- Trying to `generate()` without the extra installed raises a clean
  `ImportError` with install instructions

### 2. Stdlib for OpenAI-compatible + Ollama

Both use `urllib.request` from the stdlib, not the `openai` or `ollama`
Python clients. This means `duecare-llm-models` (base) has no runtime
dependencies beyond `duecare-llm-core` — you can hit OpenAI, DeepSeek,
Ollama, or any OpenAI-compatible provider from a bare install.

### 3. `ModelAdapterBase` is optional

Adapters can subclass `ModelAdapterBase` for shared retry/logging/
latency behavior, or they can implement the `Model` protocol
directly. The protocol is duck-typed — inheritance is a convenience,
not a requirement.

## Tests

22 tests, all passing:

- Registration: all 8 adapters register cleanly on package import
- Protocol conformance: every adapter is an `isinstance(m, Model)`
- Construction: every adapter can be instantiated without crashing
- Missing-extra errors: adapters raise `ImportError` with clear
  install instructions when their extra is missing
- Mocked generate(): `OpenAICompatibleModel.generate()` is exercised
  end-to-end with a mocked `urllib.request.urlopen` and asserts
  correct request body, response parsing, and tool-call extraction

## Status

- [x] 8 adapters implemented
- [x] 22 tests passing
- [x] Wheel built
- [x] Installed + smoke-tested
- [x] Registered in `configs/duecare/models.yaml` with 10 models (Gemma 4 E2B/E4B, GPT-OSS, Qwen, Llama, Mistral, DeepSeek, GPT-4o-mini, Claude Haiku, Gemini)

## License

MIT.
''',

    "docs/components/duecare_llm_domains.md": '''# Component — `duecare-llm-domains`

> **Status: shipped.** Pack loader + 3 real domain packs, 23 tests
> passing, wheel built, installed.

## What it is

Duecare's pluggable safety domain system. A "domain pack" is a folder of
YAML + JSONL files that defines a safety domain — taxonomy, rubric,
PII spec, seed prompts, evidence base. This package holds the loader
and the `FileDomainPack` class that reads them.

**Domain packs are content, not code.** Adding a new domain is a
directory copy and some YAML editing — zero Python changes.

## Shipped domain packs

| Pack | Categories | Indicators | Seed prompts | Evidence items |
|---|---|---|---|---|
| `trafficking` | 5 | 11 ILO | 12 (with graded responses) | 10 |
| `tax_evasion` | 4 | 8 FATF | 4 | 4 |
| `financial_crime` | 4 | 10 FATF | 3 | 3 |

All three use the **same `FileDomainPack` implementation**. The loader
knows nothing about the specific domain content — that's the whole
point of the abstraction.

## Install

```bash
pip install duecare-llm-domains
```

## Quick start

```python
from duecare.domains import load_domain_pack, discover_all, domain_registry, register_discovered

# Load one pack by id
pack = load_domain_pack("trafficking")
print(pack.card().display_name)  # "Human Trafficking & Migrant-Worker Exploitation"
print(pack.card().version)       # "0.1.0"

# Iterate seed prompts + evidence
for prompt in pack.seed_prompts():
    print(prompt["id"], "-", prompt["text"][:60], "...")

# Discover all packs under configs/duecare/domains/
packs = discover_all()
print(f"Found {len(packs)} domain packs")

# Register all discovered packs in the global registry
n = register_discovered()
print(f"Registered {n} packs")
for pack_id in domain_registry.all_ids():
    print(f"  - {pack_id}")
```

## Directory layout of a domain pack

```
configs/duecare/domains/<id>/
├── card.yaml              # metadata (id, display_name, version, description, license, owner, ...)
├── taxonomy.yaml          # categories, indicators, sectors/jurisdictions, doc refs
├── rubric.yaml            # per-task grading criteria (guardrails, anon, classify, extract, grounding)
├── pii_spec.yaml          # which PII categories matter for this domain
├── seed_prompts.jsonl     # one prompt per line, with graded response examples
├── evidence.jsonl         # one fact per line (laws, statistics, cases, advisories)
├── known_failures.jsonl   # populated by the Validator agent over time
└── README.md              # human-readable intro
```

## Adding a new domain pack

```bash
mkdir -p configs/duecare/domains/medical_misinformation
cd configs/duecare/domains/medical_misinformation

# Copy templates from an existing pack
cp ../trafficking/card.yaml .
cp ../trafficking/taxonomy.yaml .
cp ../trafficking/rubric.yaml .
cp ../trafficking/pii_spec.yaml .

# Edit them for your domain
# Populate seed_prompts.jsonl with your test prompts + graded responses
# Populate evidence.jsonl with your domain's verified facts

# Verify it loads
forge domains list
# -> medical_misinformation should appear
```

Then:

```python
from duecare.domains import load_domain_pack
pack = load_domain_pack("medical_misinformation")
```

No Python code changes.

## Design decisions

### 1. File-backed by default

`FileDomainPack` reads from the filesystem on-demand. `seed_prompts.jsonl`
and `evidence.jsonl` are streamed (not fully loaded), so a pack with
100K prompts doesn't bloat memory.

### 2. YAML for configuration, JSONL for data

Taxonomy, rubric, and pii_spec are small structured configs — YAML is
human-friendly for editing. Seed prompts and evidence are append-only
lists with embedded structure — JSONL keeps diffs clean in git.

### 3. The `DomainPack` protocol is minimal

7 methods: `card()`, `taxonomy()`, `rubric()`, `pii_spec()`,
`seed_prompts()`, `evidence()`, `known_failures()`. Plus 3 attributes:
`id`, `display_name`, `version`. A custom `DomainPack` that hits an
HTTP API or a SQL database would be ~50 lines of code.

## Tests

23 tests, all passing:

- `FileDomainPack` round-trip for every shipped pack (12 tests)
- Loader + `discover_all` edge cases (9 tests)
- Package-level smoke tests verifying trafficking/tax_evasion/
  financial_crime all load correctly (2 tests)

## Status

- [x] `FileDomainPack` implementation
- [x] `discover_all` + `load_domain_pack` loaders
- [x] 3 real domain packs populated
- [x] 19 graded seed prompts across the 3 packs
- [x] 17 evidence items across the 3 packs
- [x] 23 tests passing
- [x] Wheel built + installed

## License

MIT.
''',

    "docs/components/duecare_llm_tasks.md": '''# Component — `duecare-llm-tasks`

> **Status: shipped.** 9 capability tests, 16 tests passing, wheel built.

## What it is

Nine capability tests, each runnable against any `(Model, DomainPack)`
pair. A task is a pure function: it takes a model and a domain,
produces a `TaskResult`, and has no side effects beyond writing
artifact files.

## Tasks shipped

| Id | Capability tested | Reads from pack | Metrics produced |
|---|---|---|---|
| `guardrails` | Response policy, refusal quality, citations, redirects | `seed_prompts.jsonl` + `rubric.yaml` | `mean_score`, `grade_exact_match`, `grade_within_1`, `refusal_rate`, `harmful_phrase_rate` |
| `anonymization` | PII detection + redaction in model output | `pii_spec.yaml` | `pii_span_recall`, `pii_span_precision` |
| `classification` | Multi-label classification against taxonomy | `taxonomy.yaml` + `seed_prompts.jsonl` | `category_accuracy` |
| `fact_extraction` | Entity / date / currency extraction from source docs | `evidence.jsonl` | `entity_overlap` |
| `grounding` | Cites verifiable domain evidence (not confabulation) | `rubric.yaml` grounding section | `citation_rate` |
| `multimodal_classification` | Classify a document from its image | (requires `Capability.VISION`) | `accuracy` |
| `adversarial_multi_turn` | Crescendo-style resistance over 4 turns | `rubric.yaml` | `survival_rate` |
| `tool_use` | Correct function-calling against a mock tool set | (requires `Capability.FUNCTION_CALLING`) | `tool_call_accuracy` |
| `cross_lingual` | Guardrails in non-English languages | `rubric.yaml` | `mean_score` per-language |

## Install

```bash
pip install duecare-llm-tasks
```

Optional extras for richer evaluation:

```bash
pip install 'duecare-llm-tasks[anonymization]'  # + presidio-analyzer, presidio-anonymizer
pip install 'duecare-llm-tasks[embedding]'       # + sentence-transformers, faiss-cpu
```

## Quick start

```python
from duecare.domains import load_domain_pack
from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
from duecare.tasks import task_registry
from duecare.core import TaskConfig

domain = load_domain_pack("trafficking")
model = OpenAICompatibleModel("gpt-4o-mini")

# Run the guardrails task
task = task_registry.get("guardrails")
result = task.run(model, domain, TaskConfig(sample_size=12))

print(result.summary())
# guardrails [completed] mean_score=0.680, grade_exact_match=0.583, refusal_rate=0.917

# Inspect per-item scores
for item in result.per_item[:3]:
    print(f"{item.item_id}: {item.grade} ({item.scores})")
```

## Tests as pure functions

Every task is a plain class with a `run(model, domain, config) -> TaskResult`
method. It does **not** make decisions, **not** call tools, and **not**
persist state beyond its returned `TaskResult`. Decisions and tool
calls live in Agents. This separation matters because:

1. Tasks are deterministic (given deterministic models)
2. Tasks are trivially testable against scripted models
3. Tasks can be run in parallel without coordination
4. Tasks can be swapped out (the `adversarial_multi_turn` task can be
   replaced with a production-grade version without changing the
   agents that use it)

## Design decisions

### Rule-based scoring in `base.score_against_rubric`

The shared helper does simple phrase matching against the rubric's
`refusal_phrases` / `harmful_phrases` / education/citation/redirect
signals. This is the "rule-based" grader. Richer grading (embedding
similarity, LLM-as-judge) lives in the `Judge` agent in
`duecare-llm-agents`, which calls this function as one of its four
scoring modes.

### Capability gating

`multimodal_classification` raises `RuntimeError` if the model doesn't
declare `Capability.VISION`. `tool_use` raises if the model doesn't
declare `Capability.FUNCTION_CALLING`. This is intentional — tasks
refuse to run against unsupported models rather than silently
degrading.

## Tests

16 tests passing:

- All 9 tasks register and are retrievable from the task registry
- `Guardrails` task distinguishes best-response from worst-response
  models on real trafficking domain seed prompts
- Every task produces a valid `TaskResult` with populated metrics
- `score_against_rubric` helper tested directly with refusal /
  harmful / neutral text
- `multimodal_classification` correctly raises on non-vision models
- `tool_use` correctly raises on non-function-calling models

## Status

- [x] 9 real task implementations
- [x] Base helpers (`fresh_task_result`, `score_against_rubric`)
- [x] 16 tests passing
- [x] Wheel built + installed

## License

MIT.
''',

    "docs/components/duecare_llm_agents.md": '''# Component — `duecare-llm-agents`

> **Status: shipped.** 12 agents + supervisor infrastructure, 17 tests
> passing, wheel built.

## What it is

The **Duecare swarm**: 12 autonomous agents that compose Tasks and Tools
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
''',

    "docs/components/duecare_llm_workflows.md": '''# Component — `duecare-llm-workflows`

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
''',

    "docs/components/duecare_llm_publishing.md": '''# Component — `duecare-llm-publishing`

> **Status: shipped.** HF Hub + Kaggle + reports + model cards, 9
> tests passing, wheel built.

## What it is

The publication layer. Turns run artifacts (weights, datasets,
reports, model cards) into public deliverables on HuggingFace Hub,
Kaggle, and local markdown.

## What ships

- `HFHubPublisher` — wrapper over `huggingface_hub` (lazy-imported)
- `KagglePublisher` — wrapper over the Kaggle CLI (subprocess)
- `MarkdownReportGenerator` — renders `WorkflowRun` to markdown
- `ModelCardGenerator` — HF Hub-compatible model cards from run metrics

## Install

```bash
pip install duecare-llm-publishing

# With the HF Hub upload path
pip install 'duecare-llm-publishing[hf-hub]'

# With the Kaggle upload path
pip install 'duecare-llm-publishing[kaggle]'

# Everything
pip install 'duecare-llm-publishing[all]'
```

## Quick start

### Generate a markdown report

```python
from datetime import datetime
from duecare.core import WorkflowRun, TaskStatus
from duecare.publishing import MarkdownReportGenerator

run = WorkflowRun(
    run_id="demo_001",
    workflow_id="rapid_probe",
    git_sha="abc123",
    config_hash="def456",
    target_model_id="gemma-4-e4b",
    domain_id="trafficking",
    started_at=datetime.now(),
    ended_at=datetime.now(),
    status=TaskStatus.COMPLETED,
    final_metrics={"grade_exact_match": 0.68},
    total_cost_usd=0.0,
)

gen = MarkdownReportGenerator(output_dir="reports/")
report_path = gen.write(run)
print(f"Report at {report_path}")
```

### Publish weights to HF Hub

```python
from duecare.publishing import HFHubPublisher

pub = HFHubPublisher(token_env="HUGGINGFACE_TOKEN")
pub.create_repo_if_missing("taylorsamarel/duecare-gemma-4-e4b-safety-v0.1")
url = pub.upload_folder(
    repo_id="taylorsamarel/duecare-gemma-4-e4b-safety-v0.1",
    folder_path="models/duecare/merged_fp16",
    commit_message="v0.1 - initial release",
)
print(url)
```

### Generate a model card

```python
from duecare.publishing import ModelCardGenerator

gen = ModelCardGenerator()
gen.write(
    "models/duecare/README.md",
    model_name="gemma-4-e4b-safetyjudge-v0.1",
    base_model="unsloth/gemma-4-e4b-bnb-4bit",
    dataset_id="taylorsamarel/duecare-trafficking-training-v1",
    description="Fine-tuned Gemma 4 E4B safety judge for migrant-worker trafficking",
    grade_exact_match=0.68,
    grade_within_1=0.92,
    ilo_indicator_recall=0.81,
    refusal_rate=0.95,
    n_train_samples=12000,
)
```

### Publish to Kaggle

```python
from duecare.publishing import KagglePublisher

pub = KagglePublisher()
pub.datasets_init("kaggle/datasets/forge-trafficking-eval-v1")
# Edit dataset-metadata.json generated by datasets_init
pub.datasets_create("kaggle/datasets/forge-trafficking-eval-v1")
```

## Design decisions

### 1. Lazy imports of optional dependencies

`huggingface_hub` is imported inside `HFHubPublisher.upload_folder()`,
not at module load time. You can `pip install duecare-llm-publishing`
without pulling in the HF stack. Calling a real upload method without
the extra installed raises `ImportError` with install instructions.

### 2. Subprocess for Kaggle

`KagglePublisher` shells out to the `kaggle` CLI via `subprocess.run`.
This means the user needs the CLI installed + a token at
`~/.kaggle/kaggle.json`, but it avoids a runtime dependency on the
kaggle Python client.

### 3. Markdown reports are pure Python

`MarkdownReportGenerator` builds the report string with f-strings and
list joins. No template engine, no dependency on jinja. The `Historian`
agent uses this class directly; the report it writes contains the same
information as this class's output.

## Tests

9 tests passing:

- `MarkdownReportGenerator` renders a valid markdown document from a
  `WorkflowRun` with all fields populated
- Error state (`WorkflowRun.error`) is rendered in a fenced block
- `ModelCardGenerator` produces a valid HF Hub model card with YAML
  front matter
- `HFHubPublisher` raises a clean error when `HUGGINGFACE_TOKEN` is
  unset
- `KagglePublisher._run()` surfaces CLI errors (non-zero exit code)
  as `RuntimeError` with stderr snippet
- `is_hf_hub_available()` and `is_kaggle_cli_available()` both return
  `bool` without raising

## Status

- [x] `MarkdownReportGenerator`
- [x] `ModelCardGenerator`
- [x] `HFHubPublisher` (upload_folder + create_repo_if_missing)
- [x] `KagglePublisher` (datasets / kernels / models init + create + version)
- [x] 9 tests passing
- [x] Wheel built + installed

## License

MIT.
''',

    "docs/components/duecare_llm_meta.md": '''# Component — `duecare-llm` (meta)

> **Status: shipped.** The `duecare` CLI + meta-package that pulls in
> all 7 siblings. 6 tests passing, wheel built.

## What it is

The **meta-package** that bundles all 7 Duecare library packages and
provides the `duecare` CLI entry point. This is what judges and users
install when they want "the whole thing."

## Install

```bash
pip install duecare-llm
```

This pulls in:

- `duecare-llm-core>=0.1.0,<0.2.0`
- `duecare-llm-models>=0.1.0,<0.2.0`
- `duecare-llm-domains>=0.1.0,<0.2.0`
- `duecare-llm-tasks>=0.1.0,<0.2.0`
- `duecare-llm-agents>=0.1.0,<0.2.0`
- `duecare-llm-workflows>=0.1.0,<0.2.0`
- `duecare-llm-publishing>=0.1.0,<0.2.0`
- `typer>=0.12.0`, `rich>=13.0.0`

And registers the `duecare` command on your PATH.

With extras:

```bash
# All ML + publishing dependencies
pip install 'duecare-llm[all]'

# Dev tools (pytest, ruff, mypy)
pip install 'duecare-llm[dev]'
```

## CLI reference

```
duecare run <workflow> --target-model <id> --domain <id>
    Run a workflow end-to-end via the WorkflowRunner.

duecare tree
    Show the module tree (folder-per-module view).

duecare review <path>
    Print the 7 meta files for a module folder.

duecare test <path> [-r/--no-recursive]
    Run pytest scoped to a path.

duecare status
    Show module completeness report (counts per layer).

forge agents list
    List all 12 registered agents.

forge models list
    List all 8 registered model adapters.

forge domains list
    List discoverable domain packs.

forge tasks list
    List all 9 registered capability tests.

duecare runs list
    List previous workflow runs by scanning the reports folder.
```

## Quick start via CLI

```bash
# Verify everything is installed and registered
forge agents list
forge models list
forge tasks list
forge domains list

# Run a workflow
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking

# Cross-domain proof - same command, different domain
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain tax_evasion
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain financial_crime

# Check the reports
duecare runs list
```

## Why a meta-package

Three reasons:

1. **Single pip install** for end users: `pip install duecare-llm` beats
   `pip install duecare-llm-core duecare-llm-models duecare-llm-domains
   duecare-llm-tasks duecare-llm-agents duecare-llm-workflows
   duecare-llm-publishing` every time.
2. **Single entry-point registration** — the `duecare` script is
   declared in exactly one `pyproject.toml`.
3. **Single version pin** — the meta package constrains every sibling
   to `>=0.1.0,<0.2.0`, so `pip install duecare-llm==0.1.0` gets you a
   fully compatible set of 8 packages without mix-and-match risk.

## Design decisions

### 1. No `forge/` `__init__.py` in the meta package

The `duecare` directory in `packages/duecare-llm/src/forge/` has **no**
`__init__.py` at the namespace level. It contains only the `cli/`
subpackage. This is critical for PEP 420 namespace packages to work
— adding an `__init__.py` here would make `duecare` a regular package
and break the seven sibling packages.

### 2. The CLI is `duecare.cli`, not `duecare`

`from duecare.cli import app` works; `from duecare import app` does not
and should not. Keeping `duecare` as a namespace means every sibling
contributes its own subpackage cleanly.

### 3. Typer + rich for the CLI

Typer gives us declarative subcommands and auto-generated help. Rich
gives us pretty tables for `agents list`, `models list`, etc.
Neither is load-bearing — a fallback to argparse + plain print would
work too.

## Tests

6 tests passing:

- `forge --help` exits cleanly
- `forge agents list` shows all 12 agents
- `forge models list` shows all 8 adapters
- `forge tasks list` shows all 9 tasks
- `forge domains list` works even with no domains
- `duecare status` emits a status table without crashing

## Status

- [x] Meta package depends on all 7 siblings
- [x] `duecare` CLI entry point via `[project.scripts]`
- [x] 10 CLI commands implemented
- [x] 6 tests passing
- [x] Wheel built + installed
- [x] End-to-end `duecare run rapid_probe` verified against the trafficking domain

## License

MIT.
''',
}


def main() -> int:
    created = 0
    for rel, content in DOCS.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"WRITE {rel}")
        created += 1
    print(f"\nWrote {created} component docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
