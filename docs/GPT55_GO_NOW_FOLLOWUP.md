# GPT-5.5: Go now — execute, do not re-review

> **Continuation prompt.** Paste directly into the GPT-5.5 conversation
> after it has produced the read-only consistency report. This is
> the instruction to **stop reviewing and start editing**.

---

## ACK on your two constraint calls

Both flags you raised are correct and confirmed by the human:

1. **Route/model renames need backward-compatible aliases.** Yes.
   The pattern in this repo:
   - The OpenClaw -> server automation rename kept `GET /openclaw` as
     a 307 redirect to `/server-automation`, and
     `POST /api/hub/openclaw/inbound-email` as a 308 redirect to
     `/api/hub/automation/inbound-email`. See
     `apps/duecare-ai.com/app/main.py` near the bottom for the pattern.
   - The `OPENCLAW_*` env vars are still read alongside the new
     `DUECARE_AUTOMATION_*` names via the `_env()` helper in
     `apps/duecare-ai.com/app/automation.py`. See that helper.
   Apply the same pattern for any future rename you suggest. Never
   break a public endpoint or env var without the alias.

2. **Notebook-presentation rules apply to Kaggle's saved-output
   viewer, not to the served browser app.** Correct. The chat
   playground at
   `packages/duecare-llm-chat/src/duecare/chat/static/index.html`
   is a real interactive browser app served via cloudflared. You can
   use `display:flex`, `max-height + overflow:auto`, inline `<script>`,
   etc., there. The `60_notebook_presentation.md` rule applies
   specifically to HTML *embedded in `.ipynb` cells* that the Kaggle
   saved-output viewer sanitizes.

Don't re-litigate either of these. Move forward.

---

## Your mandate, restated

You have already produced the punch-list report. **Do not produce
another report.** Your output for the next cycle is **commits**.

Concretely: open the repo, pick the highest-priority item from
your own punch list (or from the Tier 0 / Tier 1 list in
`docs/GPT55_HANDOFF_EXECUTION_PROMPT.md`), edit the file, run the
test, commit with a clear message, push to master, then pick the
next item.

You stop when one of:

- All Tier 0 + Tier 1 items are shipped.
- Tests are red and you can't fix them in 2 attempts (revert + handoff
  back to the human).
- You hit a decision the human should make (flag + handoff back).
- The time budget you set yourself is up (handoff back with a list of
  what's left).

You do **not** stop because "the review is complete." The review is
complete. Now ship the fixes.

---

## Current state (as of commit `f98ad65`)

Repo HEAD is `f98ad65`. Tests are 19/19 green. The Render hub
auto-deploys from master. The Kaggle wheels lag the source tree
unless explicitly republished (the human owns the republish; you can
flag the version drift but should not run `kaggle kernels push`).

Files added in the most recent pushes that you may not have read yet:

- `apps/duecare-ai.com/app/schema.py` — schema.org-style hierarchy
- `apps/duecare-ai.com/app/packs.py` — pack registry helpers
- `apps/duecare-ai.com/app/local_kb.py` — operator-side SQLite store
- `apps/duecare-ai.com/app/hub_client.py` — reference client protocol
- `apps/duecare-ai.com/app/automation.py` — server-side LLM evaluator
- `apps/duecare-ai.com/app/data/packs/*.json` — 4 example packs
- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
- `packages/duecare-llm-chat/src/duecare/chat/static/anonymization-preview.html`
- `apps/duecare-ai.com/docs/BULK_INGEST_PLAN.md`
- 13 kernel intros + standardized READMEs (via
  `scripts/polish_kernels_uxbar.py`)
- `docs/COPILOT_HANDOFF_REVIEW_PROMPT.md` (your design reference)
- `docs/GPT55_HANDOFF_EXECUTION_PROMPT.md` (your execution contract)
- `docs/GPT55_GO_NOW_FOLLOWUP.md` (this document)

If your earlier review predates these files, **re-grep the repo
before editing anything**. Don't suggest creating something that
already exists.

---

## Execution order

Work this list top-down. Each item is one or more commits.

### Now (Tier 0)

1. **Verify the live deploys are at `f98ad65` or newer.**
   ```
   git log -1 --format='%h %s'
   curl -s https://gemma4-comp.onrender.com/api/health | jq .version
   ```
   If they don't match, that's a Render-dashboard issue the human
   has to fix. Note in your handoff. Don't try to redeploy.

2. **Refresh `docs/writeup_draft.md`.** Last anchored to v0.14.7.
   Update the headline numbers and the "what's live" paragraphs to
   reflect: schema.py, packs.py + 4 example packs, local_kb.py,
   hub_client.py, server-automation rename, /knowledge-packs filter
   (once you build it), 19 hub tests, etc. Cap at 1500 words.
   Verify with `wc -w docs/writeup_draft.md`. Single commit.

3. **Build the `/knowledge-packs` filter UI.** The biggest IA gap
   from the original audit. The API endpoint exists; the page has no
   filter. Pattern: copy the filter sidebar from
   `apps/duecare-ai.com/app/templates/packages.html` (260px sidebar
   with checkbox groups). Wire the result list to
   `/api/hub/packs?kind=&jurisdiction=&corridor=&tag=&status_=`.
   Use `available_kinds`, `available_corridors`,
   `available_jurisdictions` from the API response to populate the
   filter checkboxes. Each result row should be a whole-card link
   to `/api/hub/packs/{id}`. Single commit; smoke check by
   loading `/knowledge-packs` against your local FastAPI run.

4. **Confirm the contribute form actually posts end-to-end.**
   Run uvicorn, open `/contribute`, fill the form, submit, watch
   the network tab for a 202, watch `.duecare/updates.jsonl` for a
   new line. If it fails, fix it. If it works, no commit needed,
   just confirm in your handoff.

### Next (Tier 1)

5. **Heading hierarchy + a11y sweep.** Files listed in
   `docs/GPT55_HANDOFF_EXECUTION_PROMPT.md` under T1.1. Add the
   global `:focus-visible` rule. Convert `.role-card` div-with-
   onclick to `<button>`. Standardize `<h1>` -> `<h2>` -> `<h3>` so
   no level is skipped. One commit per file ideally; one focused
   batch commit acceptable if changes are small.

6. **Wheel `index.html` deeper chrome integration.** Move the
   `harness-tile-row` per-layer accent colors from inline hex to
   `var(--accent-persona)` etc. (defined in `_chrome.css`).
   **Do not** rewrite the file's layout. **Do not** remove the
   inline `<style>` block; the playground owns its layout.
   Single commit.

7. **Apply your own punch-list quick wins.** Read your earlier
   review report. For every item you marked S effort: apply it.
   One commit per finding (or one batch commit if all are pure
   nomenclature swaps in different files via the
   `polish_design_pass*.py` pattern).

### Defer (Tier 2 — do not start unless 1-7 are done)

- Local-KB ZIP/folder ingest endpoints
- More wheel viewer pages (local-case.html, local-graph.html,
  local-ingest.html, local-share.html)
- Two-FastAPI Pydantic alignment between hub and wheel runtime
- Per-viewer-page `:root` cleanup in the 11 wheel viewers

---

## Cadence

For each item above:

```
1. Read the file(s) you'll touch. Top to bottom.
2. Run the test baseline:
   DUECARE_DATA_DIR=/tmp/dc_smoke pytest apps/duecare-ai.com/tests/
3. Edit.
4. Run tests again. Fix any red BEFORE the next edit.
5. Smoke check the surface:
   - Hub: curl -s http://localhost:8000/api/health
   - Templates: TestClient render check (snippet in execution prompt)
6. Commit. Subject prefix matches surface (hub:|wheel:|kernel:|docs:|scripts:).
   Body: 2-3 sentences explaining the WHY, not the what (diff shows what).
7. Push to master.
8. Move to next item.
```

**Do not batch unrelated edits into one commit.** A "kernel intro
fixes + writeup refresh + filter UI" megacommit is wrong. Three
commits.

**Do not push red.** If tests fail and you can't fix them quickly,
revert (`git checkout -- <file>`) and retry in smaller increments.

**Do not push without running tests.** No "looks fine to me" pushes.

---

## Stop conditions and handoff format

When you stop, produce a single handoff message to the human with:

```markdown
# GPT-5.5 execution handoff #N

## Commits I pushed this session
- <hash> <subject>
- ...

## Tier 0 status
- T0.1 deploys verified: <yes/partial/no, details>
- T0.2 writeup refresh: <yes/no, word count>
- T0.3 /knowledge-packs filter: <yes/no, screenshot or curl proof>
- T0.4 contribute form end-to-end: <yes/no>

## Tier 1 status
- T1.1 a11y sweep: <files touched>
- T1.2 wheel chrome deeper integration: <yes/partial/no>
- T1.3 punch-list quick wins applied: <count>

## What I left for the human
- <decision needed, with my recommendation>

## Tests
- Hub: 19/19 green | N failed (with file:line)
- Smoke checks I ran: <list>

## What I did not touch
- <Tier 2 items deferred + why>
```

Stop. Hand back. Do not start Tier 2.

---

## One more constraint

You earlier flagged a privacy item where the local-KB copy fix
strengthens the privacy claim. Apply that fix in the same session
that touches `local_kb.py` or any `/local-kb` template. Privacy is
load-bearing for the hackathon Impact 40 score; tightening that
copy is one of the highest-leverage edits you can make.

---

## Final

You have one job for the next several hours: **ship Tier 0, then
Tier 1, then hand back.** No more reviews. No more reports until you
have something to hand back.

Go.
