# Standard Harness Contract

DueCare harnesses should expose the same concepts even when their route
handlers stay specialized. This keeps chat, process, extraction, search,
anonymization, synthetic-data, fine-tuning, judging, and report workflows
auditable through one vocabulary.

## See also (the harness documentation trinity)

- [`docs/harness_ecosystem.md`](harness_ecosystem.md) — vocabulary,
  registered harness inventory, broader harness families, naming. The
  authoritative inventory.
- [`docs/harness_pattern.md`](harness_pattern.md) — required module
  contract (`name`, `applied_layers`, `register_routes`), per-task
  JSONL training-data flow, and the 10-step recipe for adding a new
  registered harness.
- **`docs/harness_standard_contract.md`** (this file) — the
  `HarnessSpec` field shape that every registered harness declares.

## Definition

A harness is a named, repeatable workflow around Gemma 4 or a trust boundary.
It can preprocess inputs, load knowledge, call tools, call a model, verify
outputs, protect privacy, generate training data, or emit artifacts.

## Standard fields

The registered harnesses expose these fields through `HarnessSpec` and
`GET /api/harnesses`.

| Field | Meaning |
|---|---|
| `name` | Stable machine name such as `chat`, `process`, or `search_safety`. |
| `tier` | `primary` for reviewer-facing safety surfaces, `secondary` for utilities. |
| `kind` | `gemma_harness`, `safety_gate`, or `utility_surface`. |
| `applied_layers` | Layer composer names: `persona`, `grep`, `rag`, `tools`, `official_sources`, `online`. |
| `consumes` | KnowledgeObject leaf types the harness can read. |
| `emits` | KnowledgeObject leaf types the harness can write or propose. |
| `logic_paths` | Named execution paths inside the harness, with steps, entrypoints, model-call role, consumed objects, emitted objects, and verification checks. |
| `knowledge_packs` | Data packs the harness reads: GREP rules, RAG docs, local imports, contact packs, corridor packs, etc. |
| `logic_packs` | Non-data packs the harness uses: prompt templates, tool registries, schemas, rubrics, backend registries, training profiles. |
| `model_io` | What goes into the model, what comes out, and which model transport is used. |
| `model_targets` | Provider-neutral model targets the harness can use: local Gemma runtime, DueCare adapter, Ollama, OpenAI-compatible, Anthropic, Gemini, HF endpoint, frontier API, callable, or no model. |
| `input_verification` | Checks applied before model calls or external boundaries. |
| `output_verification` | Checks applied after model calls or generated artifacts. |
| `privacy_boundaries` | Trust-boundary rules for raw prompts, local files, search queries, submissions, and logs. |
| `workflow` | Human-readable path shown in workbench docs. |
| `prompt_sets` | Prompts/templates used by this harness. |
| `knowledge_flow` | Short explanation of how knowledge moves through the harness. |
| `model_fit` | Which Gemma model size or external model type is appropriate. |

## Logic path shape

`HarnessLogicPath` is the normalized execution-path object:

```python
HarnessLogicPath(
    id="chat_response",
    label="Prompt to cited response",
    entrypoints=("/api/chat/send", "/static/chat.html"),
    steps=(
        "normalize messages",
        "compose persona/GREP/RAG/tools/official-source checks",
        "call Gemma 4",
        "stream response and trace",
    ),
    consumes=("grep_rule", "rag_doc", "tool_definition"),
    emits=("reasoning_step",),
    model_call="required",
    verification=("layer trace", "optional combined grading"),
)
```

`model_call` should be one of:

- `none`: the path does not call Gemma.
- `optional`: deterministic output exists; Gemma can improve it.
- `hybrid`: deterministic and Gemma paths both contribute.
- `required`: a model call is required for the main output.
- `external_optional`: local path exists; external judge/model can be used.

## Universal model target shape

`HarnessModelTarget` declares how a harness can talk to models without
hardcoding one provider:

```python
HarnessModelTarget(
    id="local_gemma4_runtime",
    label="Local Gemma 4 runtime",
    transport="gemma4_runtime",
    role="Primary Kaggle/local model for answer generation and grading.",
    capabilities=("text_generation", "chat_messages", "structured_json"),
    required=True,
    default=True,
    trust_boundary="local",
)
```

Supported transports are:

- `none`
- `callable`
- `gemma4_runtime`
- `duecare_model_adapter`
- `transformers`
- `unsloth`
- `llama_cpp`
- `ollama`
- `openai_compatible`
- `anthropic`
- `google_gemini`
- `hf_inference_endpoint`
- `frontier_api`

The model target is a contract, not a mandate to call a model. For example,
`anonymization` and `search_safety` default to deterministic local gates and
only optionally call a local or external model after redaction. `chat` defaults
to the local Gemma 4 runtime, but the same harness contract can be backed by a
DueCare model adapter or a frontier judge when credentials and privacy policy
allow it.

`packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`
contains the portable caller:

- `UniversalModelRequest`
- `UniversalModelResponse`
- `normalize_model_messages(...)`
- `call_model_backend(...)`

`call_model_backend(...)` supports `duecare-llm-models` adapters with
`.generate(...)`, objects with `.chat(...)` or `.complete(...)`, and direct
callables such as `app.state.gemma_call`. This lets harness routes keep one
logical path while swapping local Gemma, Ollama, OpenAI-compatible endpoints,
Anthropic, Gemini, HF endpoints, or test doubles.

## Pack contract shape

`HarnessPackContract` declares either a knowledge pack or a logic pack:

```python
HarnessPackContract(
    id="core_rag",
    label="Core RAG corpus",
    kind="knowledge_pack",
    types=("rag_doc", "citation_edge", "corridor_profile"),
    required=True,
    trust_boundary="local",
    freshness="stable",
)
```

Use `knowledge_pack` for facts and context. Use `logic_pack` for prompts,
tools, schemas, rubrics, backend registries, and training profiles.

## Standard lifecycle

Every harness should be describable as this lifecycle, even if some phases are
empty:

1. Receive input.
2. Verify input and trust boundary.
3. Load knowledge packs and logic packs.
4. Compose deterministic layers or preprocessing.
5. Call the configured model target if the path requires it.
6. Verify the model output or generated artifact.
7. Emit trace, knowledge objects, training rows, reports, or audit metadata.
8. Persist artifacts under the correct local path when the workflow is part of
   a Kaggle proof run.

## Current registered harness mapping

| Harness | Main logic path | Knowledge packs | Logic packs |
|---|---|---|---|
| `chat` | prompt to cited response | core GREP, core RAG, imports | persona defaults, tool registry, grading rubrics |
| `process` | bundle review, graph chat | local imports, process grounding | process prompt tree, typed edge schema |
| `extraction` | KnowledgeObject drafting | source context | knowledge schemas and extraction prompts |
| `anonymization` | redact and review before egress | privacy patterns | submission schema |
| `search_safety` | outbound search query sanitization | PII/confidentiality patterns | safe query rewrite prompt |
| `search` | sanitized search execution | search planning context | backend registry |
| `import_corpus` | local evidence import | local evidence shelf | upload validation schema |

## A-00 broader harnesses

A-00 uses the registered harnesses, but it also has broader harness workflows
that should gradually adopt the same contract vocabulary:

- synthetic-data generator harness
- rubric-polish harness
- LoRA fine-tuning/checkpoint harness
- evaluator/judge harness
- report/export harness
- activity-log harness
- research-graph harness

The A-00 default proof path should keep using the same `chat_no_online`
content harness primitives as Kernel 01 while exposing its pipeline stages as
logic paths and saved artifacts.
