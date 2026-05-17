# Harnesses

This folder holds the seven reviewer-facing DueCare harness surfaces for
the migrant-worker recruitment / trafficking domain. Five are primary
safety surfaces. Two are secondary utilities that support the Gemma-backed
flows but are not themselves Gemma response harnesses.

This is the registered FastAPI harness package. The broader DueCare harness
ecosystem also includes A-00 experiment, synthetic-data, training,
evaluation, report, online-grounding, and research-graph harnesses. Keep the
distinction explicit: this package is the route-level harness registry; the
full inventory lives in `docs/harness_ecosystem.md`.

## The seven harness surfaces

| Surface | Tier | Endpoint(s) | Gemma 4 role | Safety layers applied |
|---|---|---|---|---|
| `chat/` | primary | `/api/chat/{send,upload-image,image/{sid}}` | full multimodal orchestrator | persona, grep, rag, tools, online |
| `process/` | primary | `/api/process/{batch,graph-chat}` | graph-chat analyst over uploaded case material | grep, rag, tools |
| `extraction/` | primary | `/api/knowledge/draft-envelope` | drafts typed KnowledgeObject envelopes | grep, rag |
| `anonymization/` | primary | `/api/{anonymize,submit/knowledge,submit/local}` | not required; hard privacy gate | none, by design |
| `search_safety/` | primary | `/api/search/{sanitize,safety-info}` | optional rephrase after redaction | none; this is the safety layer |
| `search/` | secondary | `/api/search/{client,server,backends}` | downstream only, when results feed extraction/chat | none |
| `import_corpus/` | secondary | `/api/import/*` | none; imported evidence feeds Gemma-backed harnesses | none |

## Architectural contract

Every harness surface exports these names from `__init__.py`:

```python
name: str                              # canonical short name
applied_layers: tuple[str, ...]        # which safety layers fire
consumes: tuple[str, ...]              # KnowledgeObject types read
emits: tuple[str, ...]                 # KnowledgeObject types written
spec: HarnessSpec                      # user-facing route/prompt/model contract
def register_routes(app) -> None: ...  # attaches routes to a FastAPI app
```

The shared `_layers.py` module provides `compose_layers(app, text, *, layers)`
which fans out to `app.state.{grep_call, rag_call, tools_call, online_search_call}`
and returns `{"trace": {...}, "grounding": str}`.

`base.py` provides two levels of abstraction:

- `HarnessBase`: optional helper for composed layers, training-row emission,
  and local knowledge loading.
- `HarnessSpec`: the normalized metadata contract used by `/api/harnesses`.
  The spec should live next to the implementation and declare workflow steps,
  prompt sets, model-fit limits, endpoints, examples, and knowledge flow.
- `HarnessModelTarget`: provider-neutral model target metadata. A harness can
  declare local Gemma, DueCare model adapters, Ollama, OpenAI-compatible,
  Anthropic, Gemini, HF endpoint, frontier API, callable, or no-model paths.
- `model_interface.py`: portable request/response and caller helpers for
  `.generate(...)`, `.chat(...)`, `.complete(...)`, or direct callables.

The design rule is practical: route handlers can stay specialized, but every
surface should expose the same contract shape so the Harness Workbench,
documentation, and video narrative remain consistent.

## Adding a new harness

1. `mkdir harnesses/<name>/`
2. Write `__init__.py` re-exporting `name`, `applied_layers`, `register_routes`.
3. Add `spec = HarnessSpec(...)` in `__init__.py`, including workflow,
   prompt sets, model-fit limits, knowledge flow, and model targets.
4. Write `handler.py` with handlers inside `register_routes(app)`.
5. Write `prompts.py` if the harness calls Gemma 4.
6. Add domain helpers as separate modules for fast unit-testing.
7. Write a `README.md` documenting the contract.
8. Add route/page assertions to the relevant tests.
9. Wire in `app.py` `create_app`:
   ```python
   from .harnesses import <name> as _h
   _h.register_routes(app)
   ```

## Persona is a layer name with a caveat

`chat/` declares `applied_layers = ('persona','grep','rag','tools','online')`.
**persona** is special: it is applied as a system-prompt prefix rather than
a fan-out callable. The chat harness's `run_harness` closure (in `app.py`)
injects `app.state.persona_default` or a per-request override. Other harnesses
inject their own system prompts directly via `prompts.py`.
