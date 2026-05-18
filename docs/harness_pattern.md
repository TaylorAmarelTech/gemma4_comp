# Multi-harness architecture

Every safety-bearing surface in the kernel ecosystem is a **harness** -- a
self-contained module exposing the same minimal contract. In the broader
DueCare sense, a harness is any repeatable chain of preprocessing,
post-processing, context, tools, privacy checks, evaluation, training, or
export logic wrapped around Gemma 4 or a trust boundary for a specific goal.

## See also (the harness documentation trinity)

- [`docs/harness_ecosystem.md`](harness_ecosystem.md) — vocabulary,
  registered harness inventory, broader harness families, naming. The
  authoritative inventory.
- **`docs/harness_pattern.md`** (this file) — required module contract,
  per-task JSONL training-data flow, and the 10-step recipe for adding
  a new registered harness.
- [`docs/harness_standard_contract.md`](harness_standard_contract.md) —
  the `HarnessSpec` field shape that every registered harness declares.

This document covers the registered `duecare.chat.harnesses` module contract.
For the full project-wide inventory, including A-00 synthetic-data,
fine-tuning, judging, report, online-grounding, and research-graph harnesses,
see [`docs/harness_ecosystem.md`](harness_ecosystem.md). For the
normalized fields every harness should expose, see
[`docs/harness_standard_contract.md`](harness_standard_contract.md).

## The contract

Lives at `packages/duecare-llm-chat/src/duecare/chat/harnesses/`. Every
harness module exports three required names from its `__init__.py`:

| Name | Type | Purpose |
|---|---|---|
| `name` | `str` | canonical short name (chat / process / extraction / ...) |
| `applied_layers` | `tuple[str, ...]` | which safety layers fire via `_layers.compose_layers` (allowed: persona, grep, rag, tools, official_sources, online) |
| `register_routes(app)` | callable | attaches FastAPI routes (no-op for notebook kernels) |

Optional per-harness extensions:

| Module | Purpose |
|---|---|
| `tools.py` -> `list_tools()` | function-calling tools specific to this harness |
| `knowledge.py` -> `manifest()` | KnowledgeObject types emitted/consumed |
| `evaluation.py` -> `rubric`, `examples` | per-harness grading rubric + golden examples |
| `_training_log.log_interaction()` | shared logger; each handler calls it at completion |

## Standardized logic/pack contract

Every registered harness now exposes these additional optional fields through
`HarnessSpec` and `GET /api/harnesses`:

| Field | Purpose |
|---|---|
| `logic_paths` | Named execution paths with entrypoints, steps, consumed objects, emitted objects, model-call role, and verification checks. |
| `knowledge_packs` | Fact/context packs consumed by the harness, such as GREP rules, RAG docs, local imports, contacts, and corridor profiles. |
| `logic_packs` | Prompt templates, tool registries, schemas, rubrics, backend registries, and other non-fact logic dependencies. |
| `model_io` | What reaches the model, what returns from it, and which model transport is used. |
| `model_targets` | Provider-neutral targets a harness can use: no model, local Gemma runtime, DueCare model adapter, Ollama, OpenAI-compatible, Anthropic, Gemini, HF endpoint, local transformers/Unsloth/llama.cpp, or a frontier API. |
| `input_verification` | Preconditions and safety checks before a model call or external boundary. |
| `output_verification` | Checks after model calls, generated artifacts, or exported reports. |
| `privacy_boundaries` | Where raw data must stay local, when redaction is mandatory, and what can cross external boundaries. |

The portable caller for those targets lives in
`harnesses/model_interface.py`. It normalizes prompt strings or chat messages
into `UniversalModelRequest`, invokes `.generate(...)`, `.chat(...)`,
`.complete(...)`, or a direct callable, and returns `UniversalModelResponse`.
That keeps each harness route portable across local Gemma, Ollama,
OpenAI-compatible endpoints, Anthropic, Gemini, HF endpoints, and test doubles.

## Primary harnesses

| Harness | Endpoints | Gemma 4 role | Applied layers |
|---|---|---|---|
| `chat/` | `/api/chat/{send,upload-image,image/{sid}}` | full multimodal orchestrator | persona/grep/rag/tools/official_sources/online |
| `process/` | `/api/process/{batch,graph-chat}` | bundle analyst | grep/rag/tools |
| `extraction/` | `/api/knowledge/draft-envelope` | KnowledgeObject drafter | grep/rag |
| `anonymization/` | `/api/{anonymize,submit/knowledge,submit/local}` | PII gate (regex-only, NO Gemma) | () |
| `search_safety/` | `/api/search/{sanitize,safety-info}` | outbound query privacy gate | () |
| `post_search_verification/` | `/api/search/{verify-results,verification-info}` | candidate result verification gate | () |

## Secondary harnesses

| Harness | Endpoints | Notes |
|---|---|---|
| `import_corpus/` | `/api/import/*` (6 routes) | CRUD over user-attached evidence; no LLM |
| `search/` | `/api/search/{client,server,backends}` | search utility; run only after search-safety sanitization |

## Per-harness finetuning data flow

Each handler calls
`harnesses._training_log.log_interaction(harness=name, input_payload=...,
output_payload=..., applied_layers=..., trace=...)` at completion.
Output: one JSONL stream per harness at
`/kaggle/working/training/<harness>.jsonl` (fallback `./.duecare-training/`).

```
training/
|-- chat.jsonl          # multi-turn safety conversations
|-- process.jsonl       # bundle-analysis Q&A
|-- extraction.jsonl    # structured-output (raw_text -> envelope JSON)
|-- anonymization.jsonl # text -> redactions list
|-- search_safety.jsonl # raw/sanitized query audits
|-- search.jsonl        # result-set metadata when enabled
`-- import_corpus.jsonl # uploaded evidence metadata
```

Each row schema:

```json
{
  "ts": "2026-05-13T08-50-00Z",
  "harness": "<name>",
  "input": "<anonymized text or dict>",
  "output": "<anonymized text or dict>",
  "input_sha256": "<16-char hex>",
  "output_sha256": "<16-char hex>",
  "applied_layers": {"grep": {"fired": true}, ...},
  "trace": {...},
  "anonymized": true
}
```

PII anonymized by default before the row is written. The A-00 preconfigured
pipeline can pick any of these JSONL streams and run per-task Unsloth LoRA
fine-tuning without extra plumbing -- the harness boundary already labeled the
task.

## Adding a new harness (10-step recipe)

1. `mkdir packages/duecare-llm-chat/src/duecare/chat/harnesses/<name>/`
2. Write `__init__.py` exporting `name`, `applied_layers`, `register_routes`
3. Write `handler.py` with route handlers inside `register_routes(app)`
4. Write `prompts.py` if the harness calls Gemma 4
5. Add `tools.py` / `knowledge.py` / `evaluation.py` if applicable
6. Call `_training_log.log_interaction(...)` at the end of each successful handler
7. Add the new (path, method) pairs to `tests/test_route_contract.py`
8. Wire in `app.py` `create_app`:
   ```python
   from .harnesses import <name> as _h
   _h.register_routes(app)
   ```
9. (Optional) Register in `harnesses/__init__.py` as PRIMARY or SECONDARY
10. Run `pytest tests/test_route_contract.py tests/test_harness_imports.py`

## Why this matters

- **Per-task finetuning**: harness boundary == task boundary == JSONL boundary
- **Per-task evaluation**: each harness owns its rubric in `evaluation.py`
- **Per-task tools/knowledge**: scoped namespaces prevent global registry sprawl
- **Verifiability**: a regulator can grep `applied_layers` and verify
  `anonymization` declares `()` -- i.e., never passes raw PII to Gemma
- **Reusability**: the exploration workbench and A-00 proof path reuse the
  same registered harness contracts and shared GREP/RAG/tool primitives instead
  of carrying divergent local copies.

## Safety net: route contract + adversarial validation

- `tests/test_route_contract.py` -- snapshots every (path, method) pair.
- `tests/test_harness_imports.py` -- every harness exports the 3 required names.
- `tests/test_compose_layers.py` -- unit tests for the shared layer composer.
- Adversarial validation: every refactor verified via TestClient smoke calls.

## Active Kaggle Integration

The active competition path is the three script-kernel set in
`kaggle/_INDEX.md`:

| Pattern | Used by | How to opt in |
|---|---|---|
| `duecare.chat.create_app(**default_harness())` | `01-duecare-exploration-workbench` | Auto-inherits the registered harness ecosystem through the chat app |
| `duecare.server.create_app` plus `Gemma4Runtime` | `02-live-demo` | Uses the shared runtime and focused demo surface |
| A-00 pipeline with shared harness callables | `A-00-omni-experiment-workbench` | Calls the shared GREP/RAG/tools and combined grading primitives from the pipeline |

### Legacy minimal-shell kernels

The minimal shell remains useful reference code for archived appendix kernels
or future small demos, but it is not part of the active three-kernel submission
path. If it is used again, pass explicit harness modules:

```python
from duecare.chat.kernel_shell import build_minimal_shell
from duecare.chat.harnesses import anonymization, extraction

app, url = build_minimal_shell(
    summary={"title": "knowledge-builder kernel", ...},
    kernel_id="knowledge-builder-kernel",
    harnesses=[anonymization, extraction],  # opt-in
)
# /api/anonymize, /api/submit/knowledge, /api/knowledge/draft-envelope
# now registered, with per-task training-log JSONL emission.
```

The example uses a hypothetical kernel name. The active submission
runs through the three kernels in
`kaggle/01-duecare-exploration-workbench/`,
`kaggle/02-live-demo/`, and
`kaggle/A-00-omni-experiment-workbench/`; the minimal-shell pattern
remains available for any future single-purpose kernel that needs a
subset of the registered harnesses.

### Notebook-only kernels

For appendix kernels with no FastAPI surface (data-pipeline notebooks),
`log_kernel_interaction` lets them participate in the per-task training-data
flywheel without declaring a full harness module:

```python
from duecare.chat.kernel_shell import log_kernel_interaction

result = classify(text)
log_kernel_interaction(
    "a-04-content-knowledge-builder",
    input_payload={"text": text, "task": "classify"},
    output_payload={"label": result.label, "confidence": result.confidence},
    applied_layers={"classifier": {"fired": True}},
    trace={"rule_id": result.rule_id},
)
# -> /kaggle/working/training/a-04-content-knowledge-builder.jsonl
# Same schema as the primary harnesses; ready for Unsloth ingestion.
```

### Verification

01 workbench boot-equivalent: `create_app(**default_harness())` registers all expected
harness routes (chat / process / extraction / anonymization / search_safety /
search / import_corpus). Verified via TestClient smoke:

```
/api/chat/send                  OK
/api/chat/upload-image          OK
/api/process/batch              OK
/api/process/graph-chat         OK
/api/knowledge/draft-envelope   OK
/api/anonymize                  OK
/api/search/sanitize            OK
/api/search/client              OK
/api/submit/knowledge           OK
/api/import/upload              OK
```

Each endpoint emits to the correct per-task JSONL stream at completion.


## Knowledge object consumption + emission

Every harness self-describes which `KnowledgeObject` types it reads and
writes via `consumes` and `emits` tuples on its `__init__.py`. Validated
against the live taxonomy exposed by `KO_BRANCHES` and
`GET /api/knowledge/taxonomy`.

| Harness | consumes | emits |
|---|---|---|
| `chat` | grep_rule, glob_rule, classifier_rule, heuristic_rule, rag_doc, citation_edge, corridor_profile, ngo_directory, persona_block, context_snippet, reasoning_step, rubric_dimension, tool_definition, tool_example | (none) |
| `process` | grep_rule, glob_rule, rag_doc, corridor_profile, ngo_directory, tool_definition, context_snippet | audit_template, extracted_fact, entity_signal, modus_operandi, fact_template, context_snippet |
| `extraction` | grep_rule, rag_doc, prompt_template, fact_template | grep_rule, rag_doc, ngo_directory, fact_template, extracted_fact, entity_signal, context_snippet, modus_operandi, rubric_dimension, citation_edge, envelope_schema |
| `anonymization` | prompt_template | audit_template, submission_schema |
| `search_safety` | grep_rule, prompt_template | audit_template |
| `search` | corridor_profile, ngo_directory, context_snippet | context_snippet, citation_edge |
| `import_corpus` | upload_schema | context_snippet |

A knowledge-pack builder kernel can pick a harness, read its `consumes`
list, and generate targeted training data for exactly those KO types.

## BaseHarness class (opt-in)

`harnesses/base.py` exports both:

- **`HarnessBase` Protocol** — structural typing contract (required for
  every harness, enforced by `test_harness_imports.py`).
- **`BaseHarness` class** — opt-in convenience base for new harnesses
  that want shared helpers without writing them by hand.

```python
from duecare.chat.harnesses.base import BaseHarness


class MyHarness(BaseHarness):
    name = "my_harness"
    applied_layers = ("grep", "rag")
    consumes = ("grep_rule", "rag_doc", "prompt_template")
    emits = ("envelope_schema",)

    def register_routes(self, app):
        @app.post("/api/my-endpoint")
        async def handler(req):
            grounding = self.compose(app, req.text)["grounding"]
            extras = self.load_knowledge(app, "grep_rule")
            output = ...
            self.emit_training_row(
                input_payload=req.text,
                output_payload=output,
                applied_layers={"grep": {"fired": True}},
            )
            return output


harness = MyHarness()
name = harness.name
applied_layers = harness.applied_layers
consumes = harness.consumes
emits = harness.emits
register_routes = harness.register_routes
```

The existing harnesses continue as plain modules (back-compat). New
harnesses can pick whichever style fits.


## Multi-rubric design review (2026-05-13)

| Rubric | Result |
|---|---|
| Functional validation | Registered harnesses importable, all conform |
| Flexibility | A new harness needs 5 attributes + 0 ceremony |
| Extensibility | Optional `tools`, `knowledge`, `evaluation` per harness |
| Finetuning fitness | Schema consistent across harnesses; Unsloth-ready |
| QoL | grep tells you everything; one composer for all layers |
| Tests | 24/24 contract + import + composer tests pass |
| Audit | 0 findings |
