# Goal 1 — Polish button on search.html

> Status: **PENDING**. Created 2026-05-24. Built on top of commit `92f45ac` (Goal 10 E2E tests).

## 1. Goal

Add the same "Polish further (Gemma 4)" button + inline critique + per-field diff panel that knowledge.html already has, to every draft card produced by a search result on search.html.

## 2. Why it matters

When a reviewer searches the web and drafts an envelope from a result, the draft is one-shot. Promoting it without iterating means the envelope carries vague phrasing or build-log quotes into the saved knowledge store. The `POST /api/knowledge/polish-envelope` endpoint already exists (commit `84695fc`) and the JS pattern is already proven in knowledge.html. Search.html just needs the same UX so reviewers get one-click iterative refinement on web-sourced drafts.

## 3. Current state

- `search.html` has a `searchRenderDraftCard()` function (~line 681) that renders each drafted envelope with one button: "Save this draft".
- `search.html` already imports `_activity_log.js` and uses `_searchLog.net/ok/err/warn/info/step`.
- `search.html` already surfaces the provenance row (`Gemma 4 refined / Noise scrubbed / Standard shape` pills) per commit `84695fc`.
- `knowledge.html` has `kxPolishDraft(idx)` (~line 1021) that:
  - Calls `POST /api/knowledge/polish-envelope` with the envelope.
  - Renders the critique summary + foldable per-field diff in a teal callout.
  - Bumps the top-bar tally on real polish runs.
  - Updates the JSON pre block with the polished envelope.

## 4. Target state

- Every draft card in search.html has a "Polish further (Gemma 4)" button next to "Save this draft".
- Clicking the button posts the envelope to `POST /api/knowledge/polish-envelope` with `{envelope, use_gemma: true, max_passes: 2}`.
- The response renders inline in the same card: teal callout with critique summary + foldable diff.
- Activity log gets `_searchLog.net('POST /api/knowledge/polish-envelope', ...)` on request start and `_searchLog.ok(...)` on completion.
- Top-bar Gemma tally bumps when `passes > 0`.
- Button is disabled while a polish is in flight; "Save this draft" stays enabled (reviewer can save the unpolished draft if they don't want to wait).
- When `passes === 0` (Gemma unavailable), the activity log explains why; the card stays usable.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — read sections 4, 5, 6.
2. [`docs/safe_text_layer.md`](../../safe_text_layer.md) — section "Iterative polish layer" + the provenance flags table.
3. `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — search for `kxPolishDraft` and the `kx-polish-btn-` button id. Read the entire function + the inline-rendering block (~lines 1021-1170).
4. `packages/duecare-llm-chat/src/duecare/chat/static/search.html` — read `searchRenderDraftCard()` (~lines 681-750) + the provenance-pill block.
5. `packages/duecare-llm-chat/tests/test_polish_envelope.py` — understand the response shape the new JS will consume.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/static/search.html` | Add a new button + click handler + inline-render block inside `searchRenderDraftCard()` |

## 7. Files to create

None. The endpoint, the CSS classes (`dc-gemma-mark`, `wb-btn-secondary`), and the activity-log helper already exist.

## 8. Acceptance criteria

1. Every draft card rendered by `searchRenderDraftCard()` has a button with text `"Polish further (Gemma 4)"`.
2. The button has a unique id of the form `search-polish-btn-${idx}` so multiple cards don't collide.
3. Clicking the button calls `POST /api/knowledge/polish-envelope` with `{envelope, use_gemma: true, max_passes: 2}`.
4. The button is disabled with text `"Polishing pass 1/2..."` while the request is in flight; re-enabled on completion or error.
5. The "Save this draft" button is NOT disabled during the polish (reviewer can still save).
6. On success, the existing `<pre>` block in the card is updated with the polished envelope (`JSON.stringify`, 2-space indent).
7. A new `.search-polish-notes` div is inserted ABOVE the `<pre>` block containing:
   - Header: `"Gemma 4 polish: N pass(es), M field(s) changed"`
   - Optional overall critique text (italic, teal)
   - Bulleted list of up to 6 critique issues (field name + why + suggested fix)
   - A `<details>` element with the per-field diff table
8. Activity log gets:
   - `_searchLog.net('POST /api/knowledge/polish-envelope', '<title>')` on request start
   - `_searchLog.ok('Polish complete (Xms)', 'N pass(es), M field(s) changed — <overall>')` on success
   - `_searchLog.err('Polish failed (HTTP ...)' , ...)` on HTTP error
9. `window.dcGemmaStats.bump('chat')` fires only when `passes > 0`.
10. When `passes === 0`, the activity log says `"Polish skipped: <reason>"` and the card stays usable.
11. No existing search.html test breaks. The provenance pill row (Gemma 4 refined / Noise scrubbed / Standard shape) still renders.

## 9. Do-not-break checklist

- **Section 5**: Don't rename `_searchLog` or change its `.net/.ok/.err/.warn/.info` API.
- **Section 4**: Don't rename `searchRenderDraftCard()` or change its `(entry, idx)` signature.
- **Section 4**: Don't rename or remove the existing per-card `<pre>` block (other code references `card.querySelector('pre')`).
- **Section 3**: The "Save this draft" button must stay present and functional.
- **Section 2**: Reuse `POST /api/knowledge/polish-envelope` as-is. No request/response schema changes.
- **Section 6**: Use the existing `chat` bucket on `dcGemmaStats.bump()` — do NOT add a new `polish` bucket here (a later cross-cutting goal might add it for ALL polish callers consistently).
- **Section 9**: No `innerHTML` for user-derived strings. Use `createElement` + `textContent`. The critique summary and field-name display must use textContent only.

## 10. Verification commands

```bash
# After editing, confirm the new button + handler are in place
python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/search.html').read_text(encoding='utf-8'); assert 'Polish further' in t, 'button text missing'; assert 'search-polish-btn-' in t, 'button id missing'; assert '/api/knowledge/polish-envelope' in t, 'endpoint reference missing'; print('PASS structural check')"

# Confirm the existing card layout is unchanged
python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/search.html').read_text(encoding='utf-8'); assert 'Save this draft' in t, 'Save button missing'; assert 'dc-gemma-mark' in t, 'provenance pill block missing'; print('PASS no-regression check')"

# Optional: run the polish endpoint tests (needs working pytest)
python -m pytest packages/duecare-llm-chat/tests/test_polish_envelope.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 4, 5, 6, and the safe-text
layer docs at docs/safe_text_layer.md (Iterative polish layer section).
Then read packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html
and locate the kxPolishDraft function (~line 1021) plus its
"Polish further (Gemma 4)" button (~line 1001). Read
packages/duecare-llm-chat/src/duecare/chat/static/search.html and
locate searchRenderDraftCard (~line 681).

Port the same polish UX to search.html inside searchRenderDraftCard:
add a "Polish further (Gemma 4)" button next to "Save this draft" with
id `search-polish-btn-${idx}`. Add an async searchPolishDraft(idx)
function that:
  1. POSTs to /api/knowledge/polish-envelope with
     {envelope, use_gemma: true, max_passes: 2}
  2. Disables the button while in flight (text: "Polishing pass 1/2...")
  3. Updates the card's existing <pre> block with the polished envelope
  4. Inserts a .search-polish-notes div ABOVE the <pre> with: header
     ("Gemma 4 polish: N pass(es), M field(s) changed"), italic overall
     text, bullet list of up to 6 critique issues, foldable per-field
     diff table

Use _searchLog (NOT a new log handle):
  - _searchLog.net on request start
  - _searchLog.ok on success
  - _searchLog.err on HTTP error
Bump window.dcGemmaStats.bump('chat') only when passes > 0.

DO NOT:
  - rename _searchLog
  - change searchRenderDraftCard's signature
  - remove the existing "Save this draft" button
  - change the polish endpoint's request/response schema
  - use innerHTML for any user-derived string (critique text, field
    names, diff values). Use createElement + textContent.

Verify with:
  python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/search.html').read_text(encoding='utf-8'); assert 'Polish further' in t and 'search-polish-btn-' in t and '/api/knowledge/polish-envelope' in t and 'Save this draft' in t; print('PASS')"

Acceptance criteria are spelled out in docs/codex/goal_01_polish_button_search/handoff.md section 8.
```

## 12. Out of scope

- **No new endpoint.** The polish endpoint is already pinned by `tests/test_polish_envelope.py`. Adding a new variant would split the contract.
- **No changes to the polish response shape.** The diff renderer relies on `{envelope, critique, passes, diff}` exactly.
- **No new tally bucket.** Wait for a cross-cutting goal to add `polish` consistently across all callers.
- **No multi-card batch polish.** That's Goal 5 (auto-polish queue) — a separate handoff.
- **No inline word diff.** That's Goal 8 — a separate handoff.
- **No CSS overhaul.** Use existing classes: `wb-btn-secondary`, `dc-gemma-mark`, `wb-muted`. Inline styles only for the new `.search-polish-notes` div (mirror knowledge.html's `.kx-polish-notes` exactly).
