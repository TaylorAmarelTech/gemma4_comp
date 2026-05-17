# Standard Harness Contract

DueCare harnesses should expose the same concepts even when their route
handlers stay specialized. This keeps chat, process, extraction, search,
anonymization, synthetic-data, fine-tuning, judging, and report workflows
auditable through one vocabulary.

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
| `applied_layers` | Layer composer names: `persona`, `grep`, `rag`, `tools`, `online`. |
| `consumes` | KnowledgeObject leaf types the harness can read. |
| `emits` | KnowledgeObject leaf types the harness can write or propose. |
| `logic_paths` | Named execution paths inside the harness, with steps, entrypoints, model-call role, consumed objects, emitted objects, and verification checks. |
| `knowledge_packs` | Data packs the harness reads: GREP rules, RAG docs, local imports, contact packs, corridor packs, etc. |
| `logic_packs` | Non-data packs the harness uses: prompt templates, tool registries, schemas, rubrics, backend registries, training profiles. |
| `model_io` | What goes into the model, what comes out, and which model transport is used. |
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
        "compose persona/GREP/RAG/tools",
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
5. Call Gemma 4 or another configured model if the path requires it.
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
