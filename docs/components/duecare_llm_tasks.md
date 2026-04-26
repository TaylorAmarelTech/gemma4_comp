# Component — `duecare-llm-tasks`

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
