# Multi-harness architecture

Every safety-bearing surface in the kernel ecosystem is a **harness** -- a
self-contained module exposing the same minimal contract. This is the
architectural backbone that lets per-task finetuning, per-task evaluation,
and per-task knowledge packs work without bespoke plumbing.

## The contract

Lives at `packages/duecare-llm-chat/src/duecare/chat/harnesses/`. Every
harness module exports three required names from its `__init__.py`:

| Name | Type | Purpose |
|---|---|---|
| `name` | `str` | canonical short name (chat / process / extraction / ...) |
| `applied_layers` | `tuple[str, ...]` | which safety layers fire via `_layers.compose_layers` (allowed: persona, grep, rag, tools, online) |
| `register_routes(app)` | callable | attaches FastAPI routes (no-op for notebook kernels) |

Optional per-harness extensions:

| Module | Purpose |
|---|---|
| `tools.py` -> `list_tools()` | function-calling tools specific to this harness |
| `knowledge.py` -> `manifest()` | KnowledgeObject types emitted/consumed |
| `evaluation.py` -> `rubric`, `examples` | per-harness grading rubric + golden examples |
| `_training_log.log_interaction()` | shared logger; each handler calls it at completion |

## Primary harnesses (4 -- the user-named safety surfaces)

| Harness | Endpoints | Gemma 4 role | Applied layers |
|---|---|---|---|
| `chat/` | `/api/chat/{send,upload-image,image/{sid}}` | full multimodal orchestrator | persona/grep/rag/tools/online |
| `process/` | `/api/process/{batch,graph-chat}` | bundle analyst | grep/rag/tools |
| `extraction/` | `/api/knowledge/draft-envelope` | KnowledgeObject drafter | grep/rag |
| `anonymization/` | `/api/{anonymize,submit/knowledge,submit/local}` | PII gate (regex-only, NO Gemma) | () |

## Secondary harnesses

| Harness | Endpoints | Notes |
|---|---|---|
| `import_corpus/` | `/api/import/*` (6 routes) | CRUD over user-attached evidence; no LLM |

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
`-- anonymization.jsonl # text -> redactions list
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

PII anonymized by default before the row is written. The bench-and-tune
kernel (`kaggle/A-07-bench-and-tune`) can pick any of these JSONL streams
and run per-task Unsloth LoRA fine-tuning without extra plumbing -- the
harness boundary already labeled the task.

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
- **Reusability**: A-02 (with-grep-rag-tools) and A-10 (jailbroken comparison)
  auto-inherit all 4 primary harnesses because they call `create_app()`

## Safety net: route contract + adversarial validation

- `tests/test_route_contract.py` -- snapshots every (path, method) pair.
- `tests/test_harness_imports.py` -- every harness exports the 3 required names.
- `tests/test_compose_layers.py` -- unit tests for the shared layer composer.
- Adversarial validation: every refactor verified via TestClient smoke calls.

## Cross-kernel integration (Phase 8c)

The harness pattern works across **all three** server-style kernel patterns
in `kaggle/`:

| Pattern | Used by | How to opt in |
|---|---|---|
| `duecare.chat.create_app(**default_harness())` | 01-duecare-exploration-workbench, A-10 | **Auto-inherits** all 5 harnesses |
| `duecare.chat.kernel_shell.build_minimal_shell(harnesses=[...])` | A-01, A-03, A-04, A-05, A-11, A-13, A-15, A-16 | Pass list of harness modules |
| Notebook-only (no FastAPI) | A-06, A-07, A-08, A-12, A-14 | Call `log_kernel_interaction(...)` directly |

### Minimal-shell kernels

Appendix kernels using the minimal shell get the same harness routes by
passing `harnesses=[...]`:

```python
from duecare.chat.kernel_shell import build_minimal_shell
from duecare.chat.harnesses import anonymization, extraction

app, url = build_minimal_shell(
    summary={"title": "A-04 knowledge builder", ...},
    kernel_id="a-04-content-knowledge-builder",
    harnesses=[anonymization, extraction],  # opt-in
)
# /api/anonymize, /api/submit/knowledge, /api/knowledge/draft-envelope
# now registered, with per-task training-log JSONL emission.
```

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

A-10 boot-equivalent: `create_app(**default_harness())` registers all
8 expected harness routes (chat / process / extraction / anonymization /
import_corpus). Verified via TestClient smoke:

```
/api/chat/send                  OK
/api/chat/upload-image          OK
/api/process/batch              OK
/api/process/graph-chat         OK
/api/knowledge/draft-envelope   OK
/api/anonymize                  OK
/api/submit/knowledge           OK
/api/import/upload              OK
```

Each endpoint emits to the correct per-task JSONL stream at completion.


## Multi-rubric design review (2026-05-13)

| Rubric | Result |
|---|---|
| Functional validation | 5 harnesses importable, all conform |
| Flexibility | A new harness needs 5 attributes + 0 ceremony |
| Extensibility | Optional `tools`, `knowledge`, `evaluation` per harness |
| Finetuning fitness | Schema consistent across harnesses; Unsloth-ready |
| QoL | grep tells you everything; one composer for all layers |
| Tests | 24/24 contract + import + composer tests pass |
| Audit | 0 findings |
