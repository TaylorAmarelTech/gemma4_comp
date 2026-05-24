# Goal 8 — Inline word diff in the polish panel

> Status: **PENDING**. Created 2026-05-24. Depends on Goal 1 and Goal 5 being landed (so the diff renderer is the same across surfaces).

## 1. Goal

When the polish panel renders the per-field diff, show a word-level inline diff using `<del>` (red strikethrough) and `<ins>` (green underline) tags so reviewers see exactly which words changed at a glance.

## 2. Why it matters

Today the diff is two columns: "Before" (gray) and "After" (teal). A reviewer scanning 20 polished fields has to read both sides to spot the differences. Word-level highlighting collapses that to one column with the changes marked inline — faster to scan, easier to spot hedge-word removals or indicator additions.

## 3. Current state

- `kxPolishDraft(idx)` in knowledge.html renders the diff as a `<details>` element with a 3-column table: Field | Before | After.
- Each `before` / `after` cell uses `escapeHtml(d.before)` / `escapeHtml(d.after)` so no inline highlighting today.

## 4. Target state

- When `before` and `after` are both ≤ 240 characters, render a single column with word-level inline diff: `<del>` for removed words, `<ins>` for added words.
- When either is > 240 chars, fall back to the existing 3-column layout.
- Uses LCS (longest common subsequence) algorithm — no library imports.
- Semantic colors from `docs/ui_color_vocabulary.md`:
  - Removed: `oklch(0.55 0.18 25)` (red) with `text-decoration: line-through`
  - Added: `oklch(0.62 0.10 155)` (green) with `text-decoration: underline`
- All text uses `textContent`/`createElement` (no `innerHTML` for user-derived strings).

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — section 9 (run-time invariants — the no-innerHTML rule).
2. [`docs/ui_color_vocabulary.md`](../../ui_color_vocabulary.md) — for the exact color values.
3. `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft`, especially the diff-table block (search for `Field-level diff`).

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` | Replace the 3-column diff table with the conditional inline-diff renderer. Add a `wordDiff(before, after)` helper. |

## 7. Files to create

None.

## 8. Acceptance criteria

1. New `wordDiff(before, after)` JS function returns an array of `{op, text}` segments using LCS over whitespace-split tokens.
2. When `before.length <= 240` AND `after.length <= 240`, each diff row renders a single column with inline `<del>` (red, strikethrough) and `<ins>` (green, underline) tags.
3. When either side exceeds 240 chars, fall back to the existing two-column (Before / After) layout.
4. Each `<del>` / `<ins>` element is built via `document.createElement('del'|'ins')` + `.textContent = segment.text` — no `innerHTML` with user text.
5. Equal-text segments use plain text nodes (no wrapper).
6. The expandable `<details>` summary still shows `"Field-level diff (N changed)"` exactly.
7. If Goal 1 (search.html polish button) has landed, the SAME helper renders the search.html diff too — extract `wordDiff` + the renderer to a shared scope (e.g. `window.dcDiff = {wordDiff}`).
8. If Goal 5 (auto-polish queue) has landed, the inline diff renders for every queued polish, not just manual ones.
9. Screen reader: `<del>` and `<ins>` are semantic HTML, so no extra ARIA needed.

## 9. Do-not-break checklist

- **Section 4**: Don't change the diff data shape (`{key, before, after, changed}`) — the server-side `_diff_fields` stays untouched.
- **Section 9**: NO `innerHTML` for user-derived strings. The `wordDiff` segments must be appended via `createElement` + `textContent`.
- The polish endpoint response shape (`{envelope, critique, passes, diff}`) is pinned by `test_polish_envelope.py` — don't change it.
- Don't break the existing test `test_response_shape` or `test_diff_reflects_changes`.

## 10. Verification commands

```bash
python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html').read_text(encoding='utf-8'); assert 'wordDiff' in t; assert \"createElement('del'\" in t or 'createElement(\"del\"' in t, 'must use createElement, not raw <del> string'; print('PASS')"

python -m pytest packages/duecare-llm-chat/tests/test_polish_envelope.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md section 9, docs/ui_color_vocabulary.md
for the exact red + green oklch values, and
packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html for
kxPolishDraft (especially the Field-level diff block).

Add a JS helper wordDiff(before, after) that returns an array of
{op: 'eq'|'del'|'ins', text} segments using LCS over whitespace-split
tokens. Implement LCS inline (no library import).

Replace the existing 3-column diff table rendering with this logic:

  if (before.length <= 240 && after.length <= 240) {
    // Render a single column with inline <del>/<ins> tags
    const cell = document.createElement('td');
    for (const seg of wordDiff(before, after)) {
      if (seg.op === 'eq') cell.appendChild(document.createTextNode(seg.text));
      else if (seg.op === 'del') {
        const d = document.createElement('del');
        d.style.cssText = 'color: oklch(0.55 0.18 25); text-decoration: line-through;';
        d.textContent = seg.text;
        cell.appendChild(d);
      } else {
        const i = document.createElement('ins');
        i.style.cssText = 'color: oklch(0.62 0.10 155); text-decoration: underline;';
        i.textContent = seg.text;
        cell.appendChild(i);
      }
    }
    // ... append cell to a 2-column row (Field | Diff)
  } else {
    // existing 3-column fallback (Field | Before | After)
  }

DO NOT:
  - use innerHTML for any user-derived text (createElement + textContent only)
  - change the diff data shape returned by the polish endpoint
  - import a diff library
  - break test_polish_envelope.py

If Goal 1 has landed, factor wordDiff into a shared scope
(window.dcDiff = {wordDiff}) so search.html can reuse it without
duplication.

Acceptance criteria in docs/codex/goal_08_inline_diff/handoff.md section 8.
```

## 12. Out of scope

- Character-level diff (word-level is enough).
- Diff for unchanged fields (the existing collapsed view is fine).
- Animation between before / after states.
- Diff for non-string field values (objects, arrays) — show as compact JSON in the fallback.
