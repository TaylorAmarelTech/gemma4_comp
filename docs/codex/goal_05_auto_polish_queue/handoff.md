# Goal 5 — Auto-polish queue

> Status: **PENDING**. Created 2026-05-24. Depends on Goal 1 being landed.

## 1. Goal

Add a checkbox that auto-polishes every new draft as it lands in the list, so a reviewer reviewing 50 envelopes doesn't click Polish 50 times.

## 2. Why it matters

Reviewing a batch of drafts is the common case. Today the reviewer has to click "Polish further (Gemma 4)" individually on every card. For 50 drafts that's 50 clicks + 50 wait spinners. A switch that auto-polishes the queue gives them the polished output by the time they finish reading the first envelope.

## 3. Current state

- `kxPolishDraft(idx)` polishes a single draft per call.
- New drafts are appended by `/api/knowledge/draft-envelope/start` polling.
- No queue, no auto-trigger.

## 4. Target state

- A checkbox above the draft list: `"Auto-polish new drafts (uses 2x Gemma calls per draft)"`.
- When checked, every new draft is automatically polished after rendering.
- Checkbox state persists in `localStorage` as `duecare:auto-polish`.
- Activity log reports `"Auto-polish: X of Y drafts polished (skipped Z for OOM/error)"` at batch end.
- OOM/error in one polish does NOT crash the queue — it's logged and the next draft starts.
- Tally bumps per successful polish.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — sections 4, 5, 6.
2. `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft`, the draft-rendering loop (`kxDrafts.map((env, idx) => ...)`), `kxSetWorkflow`.
3. `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js` — `dcGemmaStats.bump('chat')`.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` | Add checkbox, persist to localStorage, auto-trigger `kxPolishDraft` per draft after batch rendering, sequential queue with error recovery |

## 7. Files to create

None. All plumbing exists.

## 8. Acceptance criteria

1. A new checkbox is rendered above the draft list with label exactly `"Auto-polish new drafts (uses 2x Gemma calls per draft)"`.
2. Checkbox id: `kx-auto-polish`.
3. Initial state read from `localStorage.getItem('duecare:auto-polish') === '1'`.
4. State changes persist via `localStorage.setItem('duecare:auto-polish', this.checked ? '1' : '0')`.
5. When checked AND a draft batch lands, the page sequentially calls `kxPolishDraft(idx)` on each draft in order.
6. Sequential — never two polish calls in flight at the same time (GPU contention guard).
7. On individual polish error (OOM, HTTP failure), the queue logs the error and continues to the next draft. No exception bubbles to the page.
8. Activity log at batch start: `wbLog('info', 'Auto-polish enabled', 'queuing N draft(s) for polish')`.
9. Activity log at batch end: `wbLog('ok', 'Auto-polish complete', 'X of Y polished (Z skipped for OOM/error)')`.
10. Tally bumps `dcGemmaStats.bump('chat')` per successful polish (matches single-polish behavior).
11. Checkbox stays usable during polish queue (user can disable mid-run; in-flight polish completes, next ones are skipped).

## 9. Do-not-break checklist

- **Section 4**: Don't rename `kxDrafts`, `kxPolishDraft`, or the draft-card DOM ids.
- **Section 5**: Don't add a new log handle; use the existing `wbLog`.
- **Section 6**: Use existing `chat` bucket. Don't add a `polish` bucket.
- The single-draft "Polish further" button must keep working unchanged.
- No new endpoint; reuse `/api/knowledge/polish-envelope`.
- localStorage key `duecare:auto-polish` must not collide with existing keys (verify by greping for `duecare:` in `_nav.js`).

## 10. Verification commands

```bash
python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html').read_text(encoding='utf-8'); assert 'Auto-polish new drafts' in t and \"'duecare:auto-polish'\" in t and 'kx-auto-polish' in t; print('PASS')"

# Verify localStorage key uniqueness
python -c "import pathlib, re; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/_nav.js').read_text(encoding='utf-8'); keys = set(re.findall(r\"'duecare:[\w-]+'\", t)); print('Existing duecare: keys in _nav.js:', sorted(keys))"
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 4, 5, 6. Then read
packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html for
kxPolishDraft and the draft-rendering loop (search for kxDrafts.map).

Add a checkbox above the draft list with label exactly "Auto-polish
new drafts (uses 2x Gemma calls per draft)" and id kx-auto-polish.

Persist state: read from localStorage.getItem('duecare:auto-polish')
=== '1' on load, write on change. Default unchecked.

When checked AND a draft batch lands, sequentially call kxPolishDraft
on each draft in order. SEQUENTIAL — never two polish calls in flight
at the same time. On individual polish error, log via wbLog('err', ...)
and continue to the next draft (no exception bubble).

Activity log:
  - At queue start: wbLog('info', 'Auto-polish enabled', 'queuing N draft(s) for polish')
  - At queue end: wbLog('ok', 'Auto-polish complete', 'X of Y polished (Z skipped for OOM/error)')

Bump window.dcGemmaStats.bump('chat') per successful polish.

DO NOT:
  - rename kxDrafts, kxPolishDraft, or any draft-card DOM id
  - add a new tally bucket
  - parallelize polish calls
  - break the single-draft Polish button

Acceptance criteria in docs/codex/goal_05_auto_polish_queue/handoff.md section 8.
```

## 12. Out of scope

- Resumable queues (refreshing the page loses state).
- Auto-polish on Goal 1's search.html — separate ask later.
- A progress bar in addition to the activity log.
- Configurable concurrency. Always sequential.
