# Goal 4 — Process bundle → knowledge fact: one-click promote

> Status: **DONE 2026-05-24 (`fc7d53f`)**. Created 2026-05-24.

## 1. Goal

After Bulk File Review finishes (case brief + edges + media), let the reviewer click a "Draft as knowledge fact" button on any typed edge to instantly turn that edge into a draft knowledge envelope — opened in a modal with the same polish + promote buttons knowledge.html has.

## 2. Why it matters

Today, after Bulk File Review produces a graph with typed edges, a reviewer who wants to save a fact has to manually retype or copy-paste from the bundle into the knowledge page. The bundle already contains structured data (edge_type, source_node, target_node, evidence, indicators, corridors, journey_stage) — all the fields a knowledge envelope needs. One click should be enough to bridge the two surfaces.

## 3. Current state

- `process.html` renders typed edges in a table after the graph-extract pass completes.
- Each edge has the structured fields above; they're already standardized via `standardize_fact_envelope` upstream.
- `knowledge.html` has the full polish + promote flow.
- There is no shared modal — each page does its own rendering.

## 4. Target state

- Each typed-edge row in process.html has a "Draft as knowledge fact" button.
- Click calls a new endpoint `POST /api/knowledge/from-edge` that builds a draft envelope directly from `{edge_type, source_node, target_node, evidence, indicators, corridors, journey_stage, confidence_0_10}` — no Gemma call needed (deterministic mapping).
- The response renders in a modal overlay on process.html with two buttons: "Polish further (Gemma 4)" and "Promote draft".
- Promote-from-modal calls `POST /api/knowledge/promote` and closes the modal on success.
- Polish-from-modal calls `POST /api/knowledge/polish-envelope` and re-renders the modal content.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — sections 2, 3, 4, 5, 6.
2. `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` — find where typed edges are produced (search for `typed_edges` and `intelligence["typed_edges"]`), then the response shape `/api/process/graph-extract` returns.
3. `packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py` — `_build_draft_response` (~line 370), `_standardize_fact_envelope` usage, the response shape `/api/knowledge/draft-envelope` returns.
4. `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` — `standardize_fact_envelope`.
5. `packages/duecare-llm-chat/src/duecare/chat/static/process.html` — find the edges-table rendering.
6. `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft` and `kxPromoteDraft` for the modal logic pattern.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py` | New `POST /api/knowledge/from-edge` route + a `_build_envelope_from_edge(edge)` helper |
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/__init__.py` | Add the new route to the harness inventory |
| `packages/duecare-llm-chat/src/duecare/chat/static/process.html` | Add "Draft as knowledge fact" button per edge row + modal overlay + polish/promote handlers |

## 7. Files to create

| Path | Purpose |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/static/_polish_modal.js` | OPTIONAL extraction of the polish+promote modal so process.html and knowledge.html share it. If the reused code is small (<50 lines), skip this file and inline it. |
| `packages/duecare-llm-chat/tests/test_knowledge_from_edge.py` | Tests for the new endpoint |

## 8. Acceptance criteria

1. `POST /api/knowledge/from-edge` accepts `{edge: {edge_type, source_node, target_node, evidence, indicators, corridors, journey_stage, confidence_0_10}}` and returns the same shape as `/api/knowledge/draft-envelope`.
2. The new endpoint runs `standardize_fact_envelope` on the produced content.
3. The new endpoint does NOT call Gemma.
4. Process.html adds a "Draft as knowledge fact" button next to each typed edge row's existing actions.
5. Click → POST to `/api/knowledge/from-edge` → opens a modal with the envelope JSON, a "Polish further (Gemma 4)" button, and a "Promote draft" button.
6. Polish button calls `/api/knowledge/polish-envelope` and re-renders the modal content with critique + diff inline.
7. Promote button calls `/api/knowledge/promote` and closes the modal on success.
8. Activity log gets:
   - `_dcLog.net('POST /api/knowledge/from-edge', 'edge=<edge_type>')` on click
   - `_dcLog.ok('Draft created from edge', 'env=<id>')` on success
   - `_dcLog.ok('Promoted', 'id=<promoted_id>')` on promote-from-modal
9. The modal uses `role="dialog"` + `aria-modal="true"` + ESC-to-close.
10. New `tests/test_knowledge_from_edge.py` covers: shape parity, no Gemma call, standardize_fact_envelope ran, indicator/corridor canonicalized.

## 9. Do-not-break checklist

- **Section 2**: Don't change `/api/knowledge/draft-envelope` or `/api/knowledge/polish-envelope` or `/api/knowledge/promote`.
- **Section 4**: Don't rename existing edge-row IDs or break the edges-table layout.
- **Section 5**: Process.html uses `_dcLog`; don't add a new log handle.
- **Section 6**: `dcGemmaStats.bump('chat')` for any Gemma call fired from the modal — don't add a new bucket.
- **Section 9**: No `innerHTML` for edge-derived strings (worker chat content; use `textContent`).
- The modal overlay must NOT block other navigation.

## 10. Verification commands

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py').read_text(encoding='utf-8')); print('PASS AST')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py').read_text(encoding='utf-8'); assert '/api/knowledge/from-edge' in t and '_build_envelope_from_edge' in t; print('PASS server')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/process.html').read_text(encoding='utf-8'); assert 'Draft as knowledge fact' in t and '/api/knowledge/from-edge' in t; print('PASS UI')"

python -m pytest packages/duecare-llm-chat/tests/test_knowledge_from_edge.py packages/duecare-llm-chat/tests/test_polish_envelope.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 2, 3, 4, 5, 6. Then read:
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py
    to find where typed edges are produced
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py
    for _build_draft_response (~line 370) and the existing endpoint shape
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py for
    standardize_fact_envelope
  - packages/duecare-llm-chat/src/duecare/chat/static/process.html for the
    edges-table rendering
  - packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html for
    kxPolishDraft + kxPromoteDraft as the modal logic pattern

Add a new endpoint POST /api/knowledge/from-edge in extraction/handler.py
that accepts {edge: {edge_type, source_node, target_node, evidence,
indicators, corridors, journey_stage, confidence_0_10}}, builds an
envelope deterministically via a new _build_envelope_from_edge helper,
runs standardize_fact_envelope on the content, and returns the SAME
shape /api/knowledge/draft-envelope returns: {envelope, suggestions: [
envelope], model_call_requested: false, model_call_available: <bool>}.
Add the route to the harness inventory in extraction/__init__.py.

In process.html: add a "Draft as knowledge fact" button to each typed
edge row. On click, POST to /api/knowledge/from-edge then open a modal
overlay with the envelope JSON + "Polish further (Gemma 4)" button +
"Promote draft" button. Polish button calls /api/knowledge/polish-envelope
and re-renders inline (mirror the kxPolishDraft pattern). Promote
button calls /api/knowledge/promote and closes the modal.

Modal must be role="dialog" aria-modal="true", ESC closes.

DO NOT:
  - change /api/knowledge/draft-envelope, /polish-envelope, or /promote
  - call Gemma in the from-edge endpoint
  - rename _dcLog on process.html
  - use innerHTML for edge-derived strings (use textContent)
  - block other navigation when the modal opens

Create tests/test_knowledge_from_edge.py covering:
  - test_shape_parity_with_draft_envelope
  - test_no_gemma_call_during_from_edge
  - test_standardize_ran (standardized_shape extension flag)
  - test_indicator_canonicalized

Acceptance criteria in docs/codex/goal_04_process_to_knowledge/handoff.md section 8.
```

## 12. Out of scope

- "Draft all edges" batch button. Per-edge for this goal.
- Editing the envelope before promote (polish handles refinement).
- Wiring to share.html.
- New CSS framework — inline styles only.
