# Harnesses

This folder holds the four DueCare safety harnesses that wrap Gemma 4
for the migrant-worker recruitment / trafficking domain.

## The four harnesses

| Harness | Endpoint(s) | Gemma 4 role | Safety layers applied |
|---|---|---|---|
| `chat/` | `/api/chat/{send,upload-image,image/{sid}}` | full multimodal orchestrator | persona, grep, rag, tools, online |
| `process/` | `/api/process/{batch,graph-chat}` | bundle analyst over uploaded case material | grep, rag, tools |
| `extraction/` | `/api/knowledge/draft-envelope` | drafts typed KnowledgeObject envelopes | grep, rag |
| `anonymization/` | `/api/{anonymize,submit/knowledge,submit/local}` | NOT USED (regex-only safety gate) | none, by design |

## Architectural contract

Every harness exports three names from `__init__.py`:

```python
name: str                              # canonical short name
applied_layers: tuple[str, ...]        # which safety layers fire
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
