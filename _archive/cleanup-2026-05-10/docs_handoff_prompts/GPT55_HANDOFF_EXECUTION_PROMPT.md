# GPT-5.5 Handoff: Execute the Polish Pass

> **Role:** You are taking over a deadline-pressured Gemma 4 hackathon
> submission and **actually editing the code** to bring it to a
> ship-ready state. Unlike the Copilot review prompt at
> [`docs/COPILOT_HANDOFF_REVIEW_PROMPT.md`](./COPILOT_HANDOFF_REVIEW_PROMPT.md)
> which produces a report, your output is **a sequence of focused
> commits that move the codebase forward**.

## Read first

Before you change a single line, read these in order. Do not skip;
they encode constraints that will bite you otherwise:

1. **This document, top to bottom.**
2. [`docs/COPILOT_HANDOFF_REVIEW_PROMPT.md`](./COPILOT_HANDOFF_REVIEW_PROMPT.md)
   — same project context, design language, banned-term sweeps,
   knowledge-object schema, anti-patterns the codebase already avoids,
   project conventions. **Treat that document as your design reference;
   do not re-derive any of it.**
3. `apps/duecare-ai.com/app/schema.py` — the canonical taxonomy.
4. `apps/duecare-ai.com/app/main.py` — public hub routes + Pydantic
   models.
5. `kaggle/_INDEX.md` — canonical 13-kernel ordering.
6. `packages/duecare-llm-chat/src/duecare/chat/_brand.py` — the
   wheel's single-source-of-truth for live counts.

If the Copilot review prompt has already been run and a punch-list
report exists in the repo or in your conversation, read that too —
many of your priority-1 fixes will be its top findings.

## Stakes

Hackathon submission is **2026-05-18** (T-10 days from this writing).
Rubric: Impact 40 / Video 30 / Tech 30. Video does not exist yet and
the human will not record it until the code stops moving. **Every
edit you make either accelerates or delays the recording.** Ship
focused changes that visibly tighten the demo flow; defer anything
that doesn't.

## The non-negotiables

Same as the Copilot prompt, but enforced because you are writing code:

1. **Tests pass before you push.** Run
   `DUECARE_DATA_DIR=/tmp/dc_smoke pytest apps/duecare-ai.com/tests/`
   after every meaningful change. If tests fail, fix the failure
   before adding more changes. Never push red.
2. **Small focused commits.** One purpose per commit, one-line
   summary, body explaining the why. Match the existing commit style
   (`hub: ...`, `wheel: ...`, `kernel: ...`, `docs: ...`).
3. **Never touch `_reference/`.** It's gitignored on purpose; it
   contains the author's proprietary 21K-test trafficking benchmark.
4. **Never rename a public API, env var, or Pydantic field name
   without preserving backward compat.** The pattern in the repo: add
   the new name, keep the old as an alias, log the migration. Example:
   `OPENCLAW_*` env vars still resolve via the `_env()` helper in
   `app/automation.py` even though the canonical name is now
   `DUECARE_AUTOMATION_*`.
5. **Honor the 7 auto-loaded `.claude/rules/*.md` files.** Skim each
   once before editing. The most likely-to-bite ones are
   `10_safety_gate.md` (no PII) and `60_notebook_presentation.md`
   (Kaggle-safe HTML, no truncation, no `display:flex` in viewer
   pages).
6. **No telemetry, no tracking pixels, no analytics beacons.** The
   privacy story is load-bearing.
7. **Push to master directly.** This repo doesn't gate on PRs for
   the author's own work. Push commits as soon as their tests are
   green and they form a coherent unit.

## Priority tiers — work in this order

The author has explicitly prioritized these and will not record the
video until Tier 0 + Tier 1 are done. **Do Tier 0 to completion
first; do not start Tier 1 until every Tier 0 item is shipped or
explicitly skipped.**

### Tier 0 — must-have for submission

#### T0.1 — Verify live deploys are current

The Render hub and the Kaggle wheels lag the source tree if no one
explicitly republishes. Confirm both are at the latest commit.

```
# Hub (Render auto-deploys from master).
curl -s https://gemma4-comp.onrender.com/api/health | jq .
curl -s https://gemma4-comp.onrender.com/api/hub/status | jq .version

# Compare against the local commit.
git log -1 --format='%h %s'
```

If the hub's `version` field doesn't match the local commit's
deployment expectation, look at `render.yaml` at the repo root and
verify `autoDeploy: true` + `branch: master`. Note any divergence in
your handoff back to the human; they own the Render dashboard.

For Kaggle, the kernels reference wheel datasets. If the dataset
metadata at e.g. `kaggle/01-duecare-harness-chat/wheels/dataset-metadata.json`
shows an older version than `packages/duecare-llm-chat/pyproject.toml`,
the wheel needs a rebuild + republish. The republish itself is rate-
limited and the human should do it; but you can:

- Rebuild the wheel locally if there are uncommitted package changes
- Verify the wheel version matches across dataset metadata files
- Flag any inconsistency in your handoff

#### T0.2 — Refresh `docs/writeup_draft.md`

The writeup was last anchored to v0.14.7. Since then we've shipped:

- `app/automation.py` (server-side LLM evaluator)
- `app/schema.py` (knowledge-object hierarchy)
- `app/packs.py` + `app/data/packs/*.json` (real pack registry with
  4 example packs)
- `app/hub_client.py` (reference client with `DUECARE_HUB_URL` override)
- `app/local_kb.py` (operator-side case database) + `/local-kb` page
- New endpoints: `/api/hub/packs/{filter,id,versions,id/version,sync}`,
  `/api/hub/client/submission`, `/api/hub/client/submission/retract`,
  `/api/hub/automation/inbound-email`, `/api/local-kb/*`
- `/static/anonymization-preview.html` in the wheel
- Mission redesign with TOC sidebar
- Renamed: OpenClaw -> server automation; "signed" -> "vetted";
  "coarse" -> "anonymized"; "Eval" -> "Evaluation"
- Footer redesign (2-level, single separator)
- Knowledge-pack glossary on /hub + /docs

Edit the writeup in place. Keep the existing structure. Update the
headline numbers + the "what's live" paragraphs + the architecture
diagram description. Cap remains 1500 words. Re-run
`scripts/v141_word_count.py` after editing if it exists.

#### T0.3 — `/knowledge-packs` filter UI

The audit's biggest IA gap. The hub talks about filtering knowledge
packs by corridor / sector / kind / status everywhere; the
`/knowledge-packs` page has no filter UI. The API endpoint already
exists at `/api/hub/packs?kind=&jurisdiction=&corridor=&tag=&status_=`.

Build it:

- Look at `/packages` page for the canonical filter sidebar pattern
  (260px sidebar with checkbox groups)
- Add a similar sidebar to `/knowledge-packs` that hits
  `/api/hub/packs` and renders the response
- Use the `available_kinds`, `available_corridors`,
  `available_jurisdictions` arrays the API returns to populate the
  filter checkboxes
- Whole-card click on every result row, going to
  `/api/hub/packs/{id}` (or to a future `/knowledge-pack/{id}` page;
  if you build that page too, it's bonus)

This unblocks a real demo-path moment for judges: "open
/knowledge-packs, filter to PHL-KWT, see the pack, click to download".

#### T0.4 — Confirm the contribute form actually posts

`templates/contribute.html` has a `submitForm()` JS handler that should
POST to `/api/hub/client/submission`. Test it end-to-end:

- Open `/contribute` locally (`uvicorn app.main:app --reload`)
- Fill the form with valid data
- Click submit
- Confirm a 202 in the network panel and a tracking id in the alert
- Verify the record landed in `.duecare/updates.jsonl`

If anything fails, fix it. This is the public website's primary
user-action, the demo can't gloss over a broken submit button.

### Tier 1 — highest-leverage polish

#### T1.1 — Heading hierarchy + a11y sweep

The original audit flagged: `<h1>` -> `<h3>` jumps without `<h2>`,
missing `:focus-visible` for non-`<a>`/`<button>` interactive
elements, `.role-card` is a `<div>` with click handler (no keyboard
support), `aria-selected` missing on tablists.

Files to touch:

- `apps/duecare-ai.com/app/templates/index.html` lines 462+ (uc cards)
- `apps/duecare-ai.com/app/templates/submit-information.html` lines 30+
- `apps/duecare-ai.com/app/templates/dashboard.html` lines 252+
- `apps/duecare-ai.com/app/templates/setup.html` lines 88-112
  (.role-card -> `<button>`)
- `apps/duecare-ai.com/app/static/styles.css` add a global rule:
  ```
  a:focus-visible, button:focus-visible, [tabindex]:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  ```

Mostly invisible to a casual judge but tightens the "real, not faked"
signal for anyone reading the source.

#### T1.2 — Wheel `index.html` deeper chrome integration

The chat playground at
`packages/duecare-llm-chat/src/duecare/chat/static/index.html` (~5000
LOC) loads `_chrome.css` for design tokens but still owns its own
inline `<style>` block with hardcoded colors. The empty-state demo
cards landed in the last push. Next:

- Move the harness-tile-row color usage from inline hex to the
  semantic per-layer accents (`var(--accent-persona)` etc.) defined
  in `_chrome.css`
- Wrap the top toolbar buttons (`Compare`, `Layers`, `History`,
  `About`, `Anonymization preview`) in a proper tab strip styled like
  the website's nav
- Verify the empty-state cards work after changes (they target
  `.harness-tiles` for scroll-into-view)

Don't refactor the whole file; this is a token + tab-strip pass, not
a layout rewrite.

#### T1.3 — Two-FastAPI Pydantic alignment

The wheel runtime at `packages/duecare-llm-chat/src/duecare/chat/app.py`
has its own Pydantic models that predate `apps/duecare-ai.com/app/schema.py`.
The right-end-state is for the wheel to import the canonical types
from `app/schema.py` (or, if the package layout makes that hard, to
mirror them exactly).

For each model in the wheel app, check whether a counterpart exists
in `app/schema.py`. If yes and they differ, propose a unification
plan in a comment block + flag it as `[BREAKING]` if the API surface
would change. Don't actually break the wheel API unless you've
verified the kernels still work; flag the suggestion + leave the
existing models in place.

#### T1.4 — Run the Copilot review and act on its findings

If the Copilot review prompt has been run and a report exists, work
through its findings in this order:

1. **Quick wins** (S effort) — apply directly
2. **Nomenclature drift hits** — apply directly (the sweep is mostly
   automated via `scripts/polish_design_pass*.py` patterns)
3. **Visual / structural drift** — apply where the change is
   localized to one file
4. **Larger refactors (M/L effort)** — propose, do not execute,
   unless the human explicitly approves

Each finding becomes its own commit.

### Tier 2 — defer if Tier 0 + 1 take the time

- Local-KB ZIP upload + folder-watch (scaffold ships; ingest is
  single-text only today)
- New wheel viewer pages from the BULK_INGEST_PLAN: `local-case.html`,
  `local-graph.html`, `local-ingest.html`, `local-share.html`
- More tests for the wheel runtime (hub is at 19/19; the wheel
  has minimal coverage)
- Per-viewer-page `:root` cleanup in the 11 wheel viewer pages
  (today they each set their own; the chrome.css provides defaults)
- The bigger feature gaps documented but not built: Channels
  integrations, multi-tenant Trainer, autonomous Sentinel crawler

## Working loop (do this, in this order, every cycle)

```
1. PICK ONE ITEM from the priority tier you're in.
2. READ the file(s) you'll be touching, top to bottom.
3. RUN the relevant tests once (baseline green).
4. EDIT.
5. RUN the tests again. Fix any failures before continuing.
6. RUN the smoke check for the surface you changed:
   - Hub: curl -s http://localhost:8000/api/health
   - Wheel: import the package and check the brand counts
   - Kernel: open the notebook and verify it parses
7. COMMIT with the conventional prefix (hub:|wheel:|kernel:|docs:|scripts:)
   and a body that explains the WHY.
8. PUSH to master.
9. Mark the item done. Pick the next item.
```

Do not batch multiple unrelated changes into one commit. Do not push
red tests. Do not skip the smoke check.

## Test commands cheat sheet

```bash
# Hub tests (19/19 currently green)
DUECARE_DATA_DIR=/tmp/dc_smoke pytest apps/duecare-ai.com/tests/

# Hub smoke (after edits)
cd apps/duecare-ai.com && uvicorn app.main:app --reload &
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/hub/status
curl -s http://localhost:8000/api/hub/packs | jq .count

# Wheel package import sanity
python -c "from duecare.chat.app import create_app; print('ok')"

# Wheel + hub smoke against Render
curl -s https://gemma4-comp.onrender.com/api/health
curl -s https://gemma4-comp.onrender.com/api/hub/status
curl -s https://gemma4-comp.onrender.com/api/hub/packs | jq .count

# Validate templates render (catches Jinja syntax errors before deploy)
python -c "
import sys; sys.path.insert(0, 'apps/duecare-ai.com')
from fastapi.testclient import TestClient
from app.main import create_app
client = TestClient(create_app())
for path in ['/', '/hub', '/docs', '/mission', '/use-cases', '/knowledge-packs',
             '/contribute', '/server-automation', '/local-kb', '/stats',
             '/technical-docs']:
    r = client.get(path)
    print(path, r.status_code)
"

# Word count for the writeup
python scripts/v141_word_count.py 2>/dev/null || wc -w docs/writeup_draft.md
```

## When you're blocked

- **Tests fail and you can't tell why**: revert your last edit
  (`git checkout -- <file>`), confirm tests go back to green, then
  re-do the edit in smaller increments to isolate the breaker.
- **A finding requires a decision the human should make** (e.g.
  "should the wheel API endpoint be renamed to match the hub?"):
  do not guess. Add a TODO comment + flag it in your handoff back.
- **Render won't pick up a push**: confirm `git push origin master`
  succeeded, confirm the commit shows on GitHub. Render auto-deploys
  but takes 1-3 minutes; if 5 minutes after push the hub still serves
  the old version, the human needs to check the Render dashboard.
- **Kaggle dataset republish fails**: it's rate-limited per UTC day.
  Don't retry; flag in your handoff back.
- **You hit an enforced rule**: stop, read the rule, find a path
  that honors it. Don't push past a rule violation.

## What "done" looks like

You've shipped enough when:

- Hub tests are 19/19 passing
- The hub at `gemma4-comp.onrender.com` serves the latest commit
- The writeup matches what's live (no v0.14.7 references when v0.14.x is shipped)
- `/knowledge-packs` has a working filter UI that hits the live API
- `/contribute` form posts successfully end-to-end
- The wheel's chat playground reads as the same product as the website
  (typography, tokens, demo path)
- No banned-term hits in `apps/duecare-ai.com/app/templates/` (sweep
  via `grep -rn "signed pack\|coarse signal\|Eval &\|OpenClaw\|Sentinel\|Harness inspector\|NOT WIRED" apps/duecare-ai.com/app/templates/`)

You've shipped **too much** when:

- You've touched files outside Tier 0 + Tier 1 without finishing those
- You've started a refactor that takes more than one commit
- You've made changes that break tests and pushed anyway

## Output format (handoff back to the human)

When you stop (because Tier 0 + 1 is done OR because you're blocked
OR because the time budget is up), produce a single Markdown report:

```markdown
# GPT-5.5 execution handoff back to author

## Commits I pushed this session
- <hash> <subject>
- <hash> <subject>
...

## Tier 0 status
- T0.1 deploys verified: <yes/partial/no, with details>
- T0.2 writeup refresh: <yes/no, word count>
- T0.3 knowledge-packs filter: <yes/no>
- T0.4 contribute form: <yes/no>

## Tier 1 status
- T1.1 a11y sweep: <how many files touched, what changed>
- T1.2 wheel chrome deeper integration: <yes/partial/no>
- T1.3 two-FastAPI alignment: <flagged for human, or applied>
- T1.4 Copilot findings: <how many applied, with hashes>

## Things I left for the human
- <decisions I deferred, with the question + my recommendation>

## Tests
- Hub: 19/19 green / N failed (with file:line)
- Smoke checks I ran: <list>

## What I did not touch (and why)
- <Tier 2 items skipped because Tier 0/1 took the time>
- <files I intentionally left alone>
```

## Anti-patterns to avoid

The codebase already enforces these; do not reintroduce them:

- Cards with a tiny inner link (use `<a class="card" href>`)
- Truncated displayed text in notebooks (`text[:N]...`)
- `display:flex` and `max-height + overflow:auto` in HTML the
  Kaggle viewer renders (both get stripped)
- Inline `<script>` in any HTML the Kaggle viewer renders
- Single-letter glyph badges
- Em dashes in prose
- Brand-name jargon (OpenClaw / Sentinel / OpenCrawl as nouns)
- Mid-footer separator lines (one separator only, the outer
  `<footer>` border-top)
- Centered-narrow page widths (`max-width: 980px` for marketing
  pages — every top-level page uses 1200px)
- Hardcoded brand version numbers in templates (use `_brand.py`
  via `data-brand-count` / `data-brand-text`)
- Adding new env vars without flagging them in the handoff (the
  human curates the env-var list deliberately)

## Final note

The author has been polishing this codebase under deadline pressure.
You are inheriting a codebase that just had a heavy review pass; most
of the obvious things have been fixed. **Bias toward closing concrete
gaps the audit + this handoff explicitly named, not toward finding
new things to fix.** If you have time after Tier 0 + 1, propose Tier
2 items as a list back to the human; do not unilaterally start them.

Ship focused, ship green, ship with a handoff back.
