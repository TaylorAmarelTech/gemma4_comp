# Harnesses

This folder holds the seven reviewer-facing DueCare harness surfaces for
the migrant-worker recruitment / trafficking domain. Five are primary
safety surfaces. Two are secondary utilities that support the Gemma-backed
flows but are not themselves Gemma response harnesses.

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
def register_routes(app) -> None: ...  # attaches routes to a FastAPI app
```

The shared `_layers.py` module provides `compose_layers(app, text, *, layers)`
which fans out to `app.state.{grep_call, rag_call, tools_call, online_search_call}`
and returns `{"trace": {...}, "grounding": str}`.

## Adding a new harness

1. `mkdir harnesses/<name>/`
2. Write `__init__.py` re-exporting `name`, `applied_layers`, `register_routes`.
3. Write `handler.py` with handlers inside `register_routes(app)`.
4. Write `prompts.py` if the harness calls Gemma 4.
5. Add domain helpers as separate modules for fast unit-testing.
6. Write a `README.md` documenting the contract.
7. Add the new (path, method) pairs to `tests/test_route_contract.py`.
8. Wire in `app.py` `create_app`:
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
