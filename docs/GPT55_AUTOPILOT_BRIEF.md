# DueCare AI — GPT-5.5 8-to-10-hour autopilot brief

You are GPT-5.5 picking up an in-flight hackathon polish session in
the `gemma4_comp` repository. Use your full reasoning budget. Slow
down. Treat this like a release-hardening pass for a public Kaggle
hackathon submission that judges will inspect line-by-line.

This is **not** a brainstorming session. This is execution with
evidence. Every claim you make must be backed by one of:

- a file you read in this session
- a command you ran in this session
- a test or smoke check from this session
- the current `git diff`

If you have not verified something, write **"Not verified yet"** and
stop. Do not rely on memory, summaries, or assumptions.

---

## 1. Mission and rubric (the only thing that earns points)

DueCare AI exists to **help migrant workers** across **five user
lanes**. Every change must advance at least one of:

1. **Impact & Vision (40 pts)** — the path from this code to better
   outcomes for migrant workers must become more concrete and more
   believable.
2. **Video Pitch & Storytelling (30 pts)** — the public demo must
   become clearer, more compelling, and easier to explain in three
   minutes.
3. **Technical Depth & Execution (30 pts)** — the implementation
   must remain real, tested, reproducible, and not faked.

**70 of 100 points live in the video.** Anything you ship that does
not appear on screen, in the writeup, on the website, or in a
notebook a judge can run, is invisible to the rubric.

If a proposed action does not advance one of these three goals, **cut
it**. Do not chase tidiness for its own sake.

---

## 2. The five lanes (canonical taxonomy — preserve everywhere)

The public website is the alignment anchor. The five lanes, in this
exact order, in this exact wording:

| # | Lane | Audience | What runs locally | What crosses the public hub |
|---|---|---|---|---|
| 01 | **Platform safety** | Social platforms, recruitment marketplaces, T&S teams | Pre-publish moderation classifier + grep + corridor packs | Aggregate flag-rate metrics, opt-in only |
| 02 | **NGO & regulator** | Caseworkers, legal aid, regulators, embassies | Office edge box, local Gemma 4 + harness, private dashboard | Public-source update proposals; anonymized aggregates only |
| 03 | **Individual worker / mobile** | Migrant workers using DueCare Journey on Android | On-device model, journal, evidence, drafts, panic wipe | Nothing unless the worker explicitly shares |
| 04 | **Researcher** | Academics, journalists, policy analysts, Kaggle judges | Kaggle notebooks, eval packs, benchmark scripts | Pack hashes, rubric proposals to public review queue |
| 05 | **Developer / integration partner** | Teams embedding into WhatsApp, Messenger, dashboards, internal tools | API client, pack registry, Docker | Pulls verified packs; proposes; never pushes raw cases |

**Do not collapse this to two lanes.** NGO and mobile are not the
whole product — they're two of five equally first-class lanes.

Anchor surfaces (when these disagree about lane shape, fix the doc to
match the website, not the other way):

- [`apps/duecare-ai.com/app/templates/index.html`](../apps/duecare-ai.com/app/templates/index.html) — homepage
- [`apps/duecare-ai.com/app/templates/setup.html`](../apps/duecare-ai.com/app/templates/setup.html) — five-lane setup selector (canonical)
- [`apps/duecare-ai.com/app/templates/use-cases.html`](../apps/duecare-ai.com/app/templates/use-cases.html) — narrative version (uc-platform / uc-ngo / uc-worker / uc-research / uc-custom)
- [`apps/duecare-ai.com/app/templates/client-connect.html`](../apps/duecare-ai.com/app/templates/client-connect.html) — developer/integration lane detail
- [`README.md`](../README.md) — repo front door (needs role-based onboarding block — see Tier 0)

Authoritative slugs in `setup.html`: `plat`, `ngo`, `worker`,
`research`, `dev`. Use those exact data-track values when wiring the
selector.

---

## 3. Privacy framing (concrete, not slogan)

Privacy is **one supporting boundary**, not the headline. The user
explicitly rejected slogan-style framing
(`feedback_no_privacy_emphasis.md` in memory). Stop using
"Privacy is non-negotiable" as a tagline; reframe as concrete data
rules:

- The mobile app stores worker data on-device.
- The NGO edge box stores case files on NGO hardware.
- The public hub never receives either.
- Public artifacts (Kaggle, HF Hub, Render, GitHub) contain only
  synthetic, public, anonymized, or consented data.
- Audit logs store hashes, never plaintext.

When you mention privacy, mention it where it's load-bearing — in the
setup-page boundary table, in the client-connect "what crosses"
diagram, in the worker-app onboarding. Not as a recurring slogan.

---

## 4. What's already done (do not redo)

The 5 commits below are on `master`, pushed to GitHub:

```
4fb792f docs: align active surface counts to 13 competition + 77 research
fb1e275 docs(kaggle): correct _INDEX file-count claims and add manual-run flow
5819095 docs: cross-link REPO_LAYOUT and disambiguate hf_space vs hf-space
86e0000 docs: add REPO_LAYOUT one-screen map of every top-level dir
7a783f7 docs: replace GPT55_GO_NOW_FOLLOWUP with anti-shortcut execution prompt
```

Specifically:

- `kaggle/_INDEX.md` row 1 now reads **"✓ 3 (script)"** and the
  legend explains that script kernels can ship 3 or 4 files.
  **Do not** generate `notebook.ipynb` for `01-duecare-harness-chat/`
  — the user explicitly chose to leave it as a script kernel and
  document the copy-paste flow instead.
- All active docs now read `13 submission notebooks` (2 core + 11
  appendix) and `77-notebook research pipeline`. Frozen artifacts
  (`docs/adr/004-*.md`, dated `CHECKPOINT_*.md`, `_archive/*`) were
  intentionally **not** edited — those are point-in-time snapshots.
- `docs/REPO_LAYOUT.md` exists and is linked from the README's
  Repository-layout section. Don't recreate it; extend it if needed.
- `hf_space/README.md` and `hf-space/README.md` carry "folder note"
  blocks disambiguating the underscore vs hyphen sibling.

---

## 5. What's in flight (pick up here)

The previous session was working through 8 commits, C1–C8. **C1 and
C2 are committed and pushed.** **C3 has uncommitted changes in the
working tree.**

Working-tree state at handoff:

```
M apps/duecare-ai.com/app/templates/_nav.html       # added "Get started" → /setup
M apps/duecare-ai.com/app/templates/index.html      # added /setup CTA next to /demo
M apps/duecare-ai.com/app/templates/setup.html      # active_nav = "setup"
```

Run `git diff` first to see what landed. Verify the changes are
faithful to the five-lane model before continuing.

---

## 6. Tier 0 — finish the in-flight 8-commit polish pass

Do these in order. One coherent commit per group. Do not batch
unrelated changes.

### T0.C3 — Surface /setup onboarding (in working tree, not yet committed)

**State:** edits applied, tests not yet run.

**Acceptance:**

- `apps/duecare-ai.com/app/templates/_nav.html` shows `Get started`
  link between Use cases and Hub, with `active_nav == "setup"`
  highlighting.
- Homepage CTA row in `index.html` includes `<a class="btn btn-ghost"
  href="/setup">Get started</a>` between `/demo` and `/use-cases`.
- `setup.html` declares `{% set active_nav = "setup" %}`.

**Validate:**

```bash
.venv/Scripts/python.exe -m pytest -q apps/duecare-ai.com/tests/
.venv/Scripts/python.exe -m compileall apps/duecare-ai.com/app
```

> **Important:** the system-Python `pytest` is broken on this
> machine (missing `typing_extensions`). Use the project venv at
> `.venv/Scripts/python.exe`. Confirmed working this session.

Smoke check via TestClient (a one-liner is enough — render `/`,
`/setup`, `/use-cases`, status 200, both contain "Get started"):

```bash
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'apps/duecare-ai.com')
from app.main import build_app
from fastapi.testclient import TestClient
import os
os.environ['DUECARE_DATA_DIR'] = '.duecare-smoke'
c = TestClient(build_app())
for path in ('/', '/setup', '/use-cases', '/client-connect'):
    r = c.get(path)
    print(f'{path}: {r.status_code} {len(r.text)} bytes')
    assert r.status_code == 200, path
print('OK')
"
```

**Commit:** `hub: surface /setup onboarding`

### T0.C4 — Make setup.html commands concrete for all 5 lanes

**State:** `setup.html` currently has only one set of code blocks
(NGO-flavored) shown statically. The five role tabs (`plat`, `ngo`,
`worker`, `research`, `dev`) only swap the title + lede — they do
not swap the install commands. The NGO-flavored commands include
unverified `duecare packs pull`, `duecare packs verify`,
`duecare harness run`, and `https://duecare-ai.com/install.sh` (none
of those scripts exist; verify with `Glob` for `scripts/install.*`).

**Do not** delete the existing 5-card role selector — it's the
canonical lane structure.

**Approach (non-destructive):**

- Either add a per-lane code block under each role tab and have the
  selector show/hide them, **or** add five small static panels
  beneath the dynamic title/lede so each lane's commands are
  visible by anchor.
- Replace unverified commands with verified paths from
  [`docs/install.md`](./install.md), [`README.md`](../README.md), and
  the deployment example READMEs.
- Mark planned-but-not-implemented commands with a visible
  "**Planned**" label rather than presenting them as live.

**Lane-specific concrete commands (verified):**

- **01 Platform safety:** classifier endpoint via the developer API
  (link to `/client-connect`); Docker compose recipe from
  [`infra/`](../infra/) (verify which infra recipe is current).
- **02 NGO & regulator:** `git clone`, `make demo`,
  `http://duecare.local`. Link to
  [`docs/scenarios/ngo-office-deployment.md`](./scenarios/ngo-office-deployment.md)
  and `examples/deployment/ngo-office-edge/README.md`.
- **03 Migrant worker / mobile:** Android APK release link, first-
  launch model download, no account, no telemetry, panic wipe. Link
  to [`docs/scenarios/worker-self-help.md`](./scenarios/worker-self-help.md)
  and the mobile architecture doc.
- **04 Researcher:** Kaggle core notebooks, appendix notebooks, `make
  test`, reproducibility pointer
  ([`docs/REPO_LAYOUT.md`](./REPO_LAYOUT.md), `docs/FOR_PEER_REVIEW.md`).
- **05 Developer:** `pip install duecare-llm` (verify it's published
  before promising it; check `pyproject.toml`); `/api/hub/packs`
  pull example; link to `/client-connect`.

**Validate:** hub tests + TestClient render check on `/setup`.

**Commit:** `hub: make setup tracks concrete for all five lanes`

### T0.C5 — Fix client-connect.html API drift

**State:** `client-connect.html` uses stale endpoints
(`/api/packages`, `/api/packages/{id}`, `/api/contributions`,
`/api/signals/aggregate`). Live routes (verified in `main.py`):

| Stale | Current |
|---|---|
| `/api/packages` | `/api/hub/packs` |
| `/api/packages/{id}` | `/api/hub/packs/{pack_id}` |
| `/api/packages/{id}/manifest` | `/api/hub/packs/{pack_id}/{version}` |
| `/api/packages/{id}/download` | (no direct download — bundle assembly is client-side from the pack version response; document the actual flow, don't invent an endpoint) |
| `/api/contributions` | `/api/hub/client/submission` |
| `/api/signals/aggregate` | `/api/hub/signals` |

**Approach:**

- Read `main.py` lines 629–1149 and the templates that already use
  the right endpoints (`hub.html`, `knowledge-packs.html`,
  `submit-information.html`) for verified usage examples.
- Update curl + Python snippets in `client-connect.html` to use the
  live paths.
- Keep the privacy framing ("pulls verified knowledge, never pushes
  raw cases") — that's the lane-5 promise, just stated more plainly.
- Frame this page as the **Developer / integration partner** lane
  (lane 05). Add a small breadcrumb or kicker that places it in the
  lane taxonomy.
- If the page references a download endpoint that doesn't exist,
  either remove that step or document the correct flow (typically:
  list packs → fetch version → consume bundle from the response body
  or the linked dataset).

**Validate:** hub tests + TestClient render check on
`/client-connect`. Curl each endpoint locally with the test client to
confirm the documented JSON shape matches reality.

**Commit:** `hub: align client-connect endpoints with live API`

### T0.C6 — Add "Start here by role" 5-lane block to README.md

**State:** README.md has personas scattered through the doc but no
top-of-file role-based onboarding block. Add one — short, above the
long package inventory.

**Acceptance:** A new section (subhead `## Start here by role`)
within the first 250 lines of README, with five lanes in this exact
order, each linking to existing docs only. Do not create new docs
for this commit.

Suggested content (adapt links to what exists):

```markdown
## Start here by role

| Lane | You are | Read first |
|---|---|---|
| 01 Platform safety | A trust & safety team or recruitment marketplace integrating moderation | [docs/scenarios/enterprise_pilot.md](docs/scenarios/enterprise_pilot.md) · [docs/scenarios/recruiter-self-audit.md](docs/scenarios/recruiter-self-audit.md) · [docs/deployment_enterprise.md](docs/deployment_enterprise.md) |
| 02 NGO & regulator | An NGO caseworker, legal aid org, regulator, or embassy desk | [docs/scenarios/ngo-office-deployment.md](docs/scenarios/ngo-office-deployment.md) · [examples/deployment/ngo-office-edge/README.md](examples/deployment/ngo-office-edge/README.md) |
| 03 Worker / mobile | A migrant worker (or someone supporting one) using the Android app | [docs/scenarios/worker-self-help.md](docs/scenarios/worker-self-help.md) · [docs/android_app_architecture.md](docs/android_app_architecture.md) |
| 04 Researcher / judge | An academic, journalist, policy analyst, or Kaggle judge | [docs/FOR_KAGGLE_JUDGES.md](docs/FOR_KAGGLE_JUDGES.md) · [docs/FOR_PEER_REVIEW.md](docs/FOR_PEER_REVIEW.md) · [docs/scenarios/researcher-analysis.md](docs/scenarios/researcher-analysis.md) · [kaggle/01-duecare-harness-chat/README.md](kaggle/01-duecare-harness-chat/README.md) |
| 05 Developer / integrator | A team embedding DueCare into your own product | [docs/install.md](docs/install.md) · [docs/embedding_guide.md](docs/embedding_guide.md) · [packages/duecare-llm/README.md](packages/duecare-llm/README.md) |
```

**Verify every link target exists** before committing
(`Glob` or `ls`). If a target doesn't exist, link to the closest
real doc or omit that link rather than promising a 404.

**Commit:** `docs: add role-based onboarding entry to README`

### T0.C7 — Refresh mobile + install drift

**State (verified earlier this session, may have shifted; re-verify):**

- `docs/scenarios/worker-self-help.md` references "v0.8 will add..."
  language while the repo describes v0.9.0 as live. Update to v0.9
  current state.
- `docs/deployment_local.md` says "all four toggle layers" — current
  core notebook (`01-duecare-harness-chat`) ships **6 layers**
  (Persona / GREP / RAG / Tools / Online / Imports). Distinguish
  `A-02-` (the 4-toggle appendix, accurate as 4) from `01-` (core, 6).
- `docs/install.md` shows count drift in expected output (e.g. "587
  prompts prompts", older "42 / 26 / 4 / 394" values). Run the
  current verify script or hit `/api/brand` (or whatever the brand
  endpoint is — verify with grep) and update both prose and expected
  output to match what runs today.

**Approach:** read current files first; only change what's actually
stale; do not invent counts. If you can't verify a number from a
running endpoint or a fresh validator pass, leave it as `<verify>`
and call it out in the handoff rather than guessing.

**Commit:** `docs: refresh onboarding setup details`

### T0.C8 — Wheel modal accent color cleanup

**State:** `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
defines layer accent variables:

```
--accent-persona: var(--site-ember);    /* Persona */
--accent-imports: #fb923c;              /* Imports */
--accent-grep:    #14b8a6;              /* GREP */
--accent-rag:     #3b82f6;              /* RAG */
--accent-tools:   #10b981;              /* Tools */
--accent-online:  #06b6d4;              /* Online */
```

Layer tile colors in `index.html` already map to these. Remaining
hardcoded layer colors live inside modal accent strips and inline
hero cards. Replace the hardcoded hex values with `var(--accent-*)`
where the meaning is "this is the layer X color".

**Do not:**

- rewrite the layout
- remove the inline `<style>` block
- apply Kaggle saved-output HTML restrictions to this browser app
  (those rules are for `.ipynb` files only)

**Validate:** grep the changed region after the edit to confirm no
hardcoded layer hex values remain in the modal sections. Static
sanity check the file renders (Python `pathlib.Path(...).read_text()`
+ a quick `assert` that the variable names appear).

**Commit:** `wheel: align modal layer accents with chrome variables`

---

## 7. Tier 1 — notebook ↔ website alignment sweep

Once Tier 0 is done, the headline ask: make the 13 Kaggle notebooks
align with the website's lane taxonomy and visual language.

### T1.1 — Lane labels on each notebook

For each of the 13 notebook folders under `kaggle/`, the README's
top-level header should declare which lane (or lanes) the notebook
serves, in the website's wording. Example (don't redesign — augment):

```markdown
# DueCare — Migrant-worker safety playground (#01 core)
> **Serves lanes:** 02 NGO & regulator · 04 Researcher · 05 Developer
```

This makes a judge clicking from the website's setup page to a
notebook see immediate continuity. Mapping (suggested — verify
against actual notebook content first):

| Folder | Lane(s) |
|---|---|
| `01-duecare-harness-chat` | 02, 04, 05 (omni playground) |
| `02-live-demo` | All five (showcase) |
| `A-01-chat-playground` | 04 (baseline) |
| `A-02-chat-playground-with-grep-rag-tools` | 04 (4-toggle subset) |
| `A-03-content-classification-playground` | 01, 02 |
| `A-04-content-knowledge-builder-playground` | 02, 05 |
| `A-05-gemma-content-classification-evaluation` | 02 (NGO dashboard) |
| `A-06-prompt-generation` | 04 |
| `A-07-bench-and-tune` | 04, 05 (Unsloth) |
| `A-08-research-graphs` | 04 |
| `A-09-chat-playground-with-agentic-research` | 04, 05 (Playwright BYOK) |
| `A-10-chat-playground-jailbroken-models` | 04 (skunkworks-adjacent) |
| `A-11-grading-evaluation` | 04 (lift regenerator) |

Read each notebook's existing README before editing. The lane
mapping in the table above is a starting point — adjust if the
notebook's actual content tells a different story.

**Validate:** `python scripts/validate_notebooks.py` (must still pass
77/77). `python -m pytest -q tests/test_kaggle_notebook_utils.py`.

**Commit:** `notebooks: tag each kernel with website lane labels`

### T1.2 — Notebook intro consistency via polish_kernels_uxbar.py

`scripts/polish_kernels_uxbar.py` is the canonical mechanism that
inserts the top-of-file markdown intro and standardizes the README
h1 across all 13 folders. **Re-run it** after any README edit to
keep the cross-kernel footer in sync.

```bash
.venv/Scripts/python.exe scripts/polish_kernels_uxbar.py
```

If the script fails for a folder, the failure is the bug — fix the
folder, not the script's idempotency check. If the script needs to
learn about lane labels, extend the `KERNELS` list in
`polish_kernels_uxbar.py` and re-run. Commit the generator change
alongside the regenerated files.

**Commit:** `notebooks: refresh cross-kernel intros and footers`

### T1.3 — Visual continuity (notebook ↔ website ↔ wheel)

The website palette (`apps/duecare-ai.com/app/static/styles.css`):

```
--accent:      oklch(0.52 0.08 195);   /* civic teal */
--accent-soft: oklch(0.92 0.03 195);
--accent-ink:  oklch(0.32 0.07 195);
```

The wheel chrome (`packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`):

```
--accent-civic-teal: #14b8a6;
--accent-grep:    #14b8a6;
--accent-rag:     #3b82f6;
--accent-tools:   #10b981;
--accent-online:  #06b6d4;
--accent-persona: var(--site-ember);
--accent-imports: #fb923c;
```

The website uses oklch civic teal (`oklch(0.52 0.08 195)`); the
wheel uses the same hex equivalent (`#14b8a6`) for `--accent-grep`.
This is intentional — civic teal is the brand color and GREP is the
deterministic-verification layer. Do not introduce a new brand
color. Do not use a competing accent in notebook outputs.

For notebook outputs (per `.claude/rules/60_notebook_presentation.md`):

| Role | Hex | Use |
|---|---|---|
| primary | `#4c78a8` | bars, headers (this is the legacy primary; OK in notebooks) |
| success | `#10b981` | refusals, passing cases (matches `--accent-tools`) |
| warning | `#f59e0b` | partial-match, neutral band |
| danger  | `#ef4444` | harmful content |
| info    | `#3b82f6` | informational (matches `--accent-rag`) |
| muted   | `#6b7280` | secondary text |

A notebook color sweep is **out of scope for Tier 1** unless you
spot a clear regression (e.g. a notebook using a competing brand
color in a header).

---

## 8. Tier 2 — UI/UX consistency sweep across hub + wheel + notebooks

These are smaller polish items. Pick whichever rises to the top by
judge-impact, not by tidiness.

### T2.1 — Navigation parity audit

All template files declare `{% set active_nav = ... %}`. Currently in
use: `mission`, `demo`, `use-cases`, `setup`, `hub`, `docs`, `stats`.
The nav itself shows: Mission, Demo, Use cases, Get started, Hub,
Docs, Stats, plus the Get involved CTA.

- Verify every active_nav value matches a real nav link or is
  intentionally `null`. Examples that may need attention: pages
  declaring `active_nav = "hub"` but not actually about the hub.
- Confirm that the new `setup` value in the nav highlights when on
  `/setup` and **only** then.

### T2.2 — Footer consistency

`_footer.html` is included by every page. Check that the four footer
sections (Hub / Docs / Get involved / Verify) point at routes that
actually exist. Drop dead links rather than letting them 404.

### T2.3 — Heading hierarchy

Pages should not skip h1 → h3. Spot-check a few templates with
`grep -n "^<h[1-6]" apps/duecare-ai.com/app/templates/*.html` and fix
any obvious skips.

### T2.4 — Focus-visible already exists

`styles.css` line 61 already has a global `:focus-visible` rule.
**Don't add it again.** A focused a11y sweep should target stale
clickable `div`s with JS navigation (convert to `<a>` or `<button>`),
form controls without labels, and buttons without accessible names.

### T2.5 — Wheel browser-app exception

The wheel chat playground (`packages/duecare-llm-chat/src/duecare/chat/static/`)
is a **served browser app**, not a Kaggle saved-output notebook. The
notebook-presentation restrictions (`60_notebook_presentation.md` —
no `display: flex`, no `max-height: ... overflow: auto`, no inline
`<script>`) do **not** apply here. Don't accidentally remove working
flex layouts or scripts from this surface.

---

## 9. Tier 3 — judge polish (only if Tier 0–2 are complete)

### T3.1 — Writeup refresh

[`docs/writeup_draft.md`](./writeup_draft.md) is the public submission
writeup, capped at 1500 words. Verify the word count first:

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
text = Path('docs/writeup_draft.md').read_text(encoding='utf-8')
print('words:', len(text.split()))
"
```

If under 1500, you have room to update. If over, trim before adding.
Make the story judge-facing, not internal. Lead with a named
composite worker case and close with a named NGO partner.

**Commit:** `docs: refresh competition writeup`

### T3.2 — Video script alignment

[`docs/video_script.md`](./video_script.md) — check it still names
the five lanes in order, references the live demo URL, and times to
under 3 minutes. Don't restructure unless something is materially
wrong.

### T3.3 — FOR_PEER_REVIEW + FOR_KAGGLE_JUDGES

The two judge-facing entry docs. Spot-check for stale wording (the
"5 layers" → "6 layers" sweep was completed earlier; don't re-do —
just verify it stuck).

---

## 10. Anti-shortcut rules (non-negotiable)

You **must not**:

- say "done" without tests or smoke checks
- mark a task complete because the code "looks right"
- edit from memory without reading the current file
- batch unrelated fixes into one commit
- leave uncommitted work without a clear handoff reason
- push if tests are red
- claim a page works without opening it, using a TestClient render
  check, or curling it locally
- claim a notebook exists without verifying the file exists
- claim a doc is consistent without grepping for stale competing
  terms
- use "should", "probably", or "likely" in the final handoff for
  anything that should be verified

If you cannot verify something, write exactly:

> **Not verified in this session.**

---

## 11. Hard constraints (do not violate)

- **Do not edit `_reference/`.**
- **Do not run Kaggle/HF/Render/PyPI publishing commands.** No
  `kaggle kernels push`, no `huggingface-cli upload`, no `git push`
  to a Render-watched branch with intent to trigger deploy. (Pushing
  to `master` is fine; Render auto-deploys, but your changes should
  be safe to deploy.)
- **Do not commit raw PII.**
- **Preserve backward-compat aliases.** Existing examples to
  protect:
  - `/api/hub/openclaw/inbound-email` → 308 redirects to
    `/api/hub/automation/inbound-email`. Keep the redirect.
  - Old env-var names (e.g. `OPENCLAW_*`) may still be read via an
    `_env()` helper that prefers `DUECARE_AUTOMATION_*` but accepts
    the old form. Don't remove the legacy fallback.
- **Do not overwrite user changes.** Run `git status --short` before
  every edit. If a file is `M` in the working tree and you didn't
  intentionally modify it this session, ask before touching it.
- **Do not edit `apps/duecare-ai.com/app/data/demo_priority_examples.json`**
  unless the task explicitly requires it.
- **Notebook-presentation rules apply to `.ipynb` saved-output HTML,
  not the served browser app.** Don't strip CSS/JS from
  `packages/duecare-llm-chat/src/duecare/chat/static/` because of a
  Kaggle viewer restriction.
- **The Render hub is a CPU-only coordination layer**, not hosted
  Gemma GPU inference. Don't document it as one.

---

## 12. Validation matrix (run the narrowest relevant slice)

The system Python is broken; **always** use the project venv:

```bash
PY=.venv/Scripts/python.exe
```

For hub / FastAPI changes:

```bash
DUECARE_DATA_DIR="$PWD/.duecare-smoke" $PY -m pytest -q apps/duecare-ai.com/tests/
$PY -m compileall apps/duecare-ai.com/app
```

For notebook / Kaggle changes:

```bash
$PY scripts/validate_notebooks.py            # must report 77/77
$PY -m pytest -q tests/test_kaggle_notebook_utils.py
```

For Python script changes:

```bash
$PY -m compileall scripts
```

For docs-only changes:

```bash
git diff --check
```

After any docs edits affecting lane / count / setup wording, drift grep:

```bash
grep -REn "6 core \+ 5|all 11 submission notebooks|3 hackathon notebooks|76-notebook|duecare packs pull|duecare packs verify|duecare harness run|signed pack|OpenClaw" \
  README.md docs kaggle apps/duecare-ai.com/app/templates skunkworks 2>/dev/null
```

Anything that hits in an active doc (excluding `_archive/`,
`docs/adr/`, `docs/CHECKPOINT_*`, `docs/GPT55_*` — those reference
the stale terms intentionally) is a defect to fix.

Before each commit:

```bash
git diff --check
git status --short
```

After each commit:

```bash
git log -1 --oneline
git push origin master
```

---

## 13. Required reading before first edit

In order:

1. [`CLAUDE.md`](../CLAUDE.md)
2. [`.claude/rules/00_overarching_goals.md`](../.claude/rules/00_overarching_goals.md)
3. [`.claude/rules/10_safety_gate.md`](../.claude/rules/10_safety_gate.md)
4. [`.claude/rules/30_test_before_commit.md`](../.claude/rules/30_test_before_commit.md)
5. [`.claude/rules/60_notebook_presentation.md`](../.claude/rules/60_notebook_presentation.md)
6. [`docs/REPO_LAYOUT.md`](./REPO_LAYOUT.md)
7. [`docs/GPT55_GO_NOW_FOLLOWUP.md`](./GPT55_GO_NOW_FOLLOWUP.md) — the
   prior anti-shortcut prompt (this brief supersedes it but the
   rules carry over)
8. [`apps/duecare-ai.com/app/templates/setup.html`](../apps/duecare-ai.com/app/templates/setup.html)
9. [`apps/duecare-ai.com/app/templates/use-cases.html`](../apps/duecare-ai.com/app/templates/use-cases.html)
10. [`apps/duecare-ai.com/app/main.py`](../apps/duecare-ai.com/app/main.py) (skim — focus on routes)
11. [`kaggle/_INDEX.md`](../kaggle/_INDEX.md)

For any file you intend to edit, **read it top-to-bottom first**.

---

## 14. Commit discipline

One coherent change per commit. Subject in the form
`<surface>: <imperative>`. Body explains the **why** (judge clarity,
backward compat, rubric goal, lane alignment, reproducibility).

Good subjects:

- `hub: surface /setup onboarding`
- `hub: make setup tracks concrete for all five lanes`
- `hub: align client-connect endpoints with live API`
- `docs: add role-based onboarding entry to README`
- `notebooks: tag each kernel with website lane labels`
- `wheel: align modal layer accents with chrome variables`

Bad:

- `fix stuff`
- `updates`
- a mega-commit containing writeup, hub UI, notebook docs, and wheel CSS

Do **not** commit unrelated modified files. If a file was already
modified by the user and you didn't intentionally edit it, leave it
out of your commit (`git add <specific files>`, never `git add -A`
or `git add .`).

Append the standard co-author trailer:

```
Co-Authored-By: GPT-5.5 <noreply@openai.com>
```

(Or whatever attribution you use; pick one and stay consistent.)

---

## 15. Stop conditions

Stop and hand back if:

- tests fail and two focused fix attempts fail
- a route or env-var rename would break compatibility
- a user-modified file must be overwritten to proceed
- Render deploy is stale and requires dashboard intervention
- Kaggle / HF / PyPI publishing is required
- a decision affects repo organization in a non-trivial way (e.g.
  moving `legacy_notebooks/`)
- Tier 0 is fully done (then proceed to Tier 1; Tier 1 done → Tier 2;
  etc.)
- you hit your 8–10 hour budget

If stopping due to test failure, **revert the partial edit** unless
the human explicitly asked to keep it.

---

## 16. Final handoff format

Use exactly this structure when you're done or out of time:

```markdown
# GPT-5.5 autopilot handoff (yyyy-mm-dd)

## Commits pushed (oldest first)
- `<hash>` `<subject>`
- ...

## Tier 0 status
- T0.C3 surface /setup: <done / partial / blocked> — evidence:
- T0.C4 setup commands: <done / partial / blocked> — evidence:
- T0.C5 client-connect API: <done / partial / blocked> — evidence:
- T0.C6 README role onboarding: <done / partial / blocked> — evidence:
- T0.C7 mobile/install drift: <done / partial / blocked> — evidence:
- T0.C8 wheel modal accents: <done / partial / blocked> — evidence:

## Tier 1 status
- T1.1 lane labels on notebooks: <done / partial / not started> — files:
- T1.2 polish_kernels_uxbar refresh: <done / not started> — output:
- T1.3 visual continuity audit: <done / not started> — findings:

## Tier 2 status
- T2.1 nav parity: <done / partial / not started>
- T2.2 footer consistency: <done / partial / not started>
- T2.3 heading hierarchy: <done / partial / not started>
- T2.4 a11y sweep (clickable divs, labels): <done / partial / not started>

## Tier 3 status
- T3.1 writeup refresh: <done / not started> — word count:
- T3.2 video script: <done / not started>
- T3.3 FOR_PEER_REVIEW / FOR_KAGGLE_JUDGES: <done / not started>

## Tests and smoke checks
- Hub tests: <pass count / total>
- Notebook validator: <77 / 77 or actual>
- compileall hub: <pass / fail>
- TestClient render checks: <list of paths verified 200>
- Drift grep: <count of remaining hits in active surfaces>

## Files intentionally not touched
- `_reference/`
- `apps/duecare-ai.com/app/data/demo_priority_examples.json` (unless required)
- `docs/adr/`, `docs/CHECKPOINT_*`, `_archive/` (frozen artifacts)
- ...

## Blockers / human decisions needed
- ...

## Five-lane consistency check
- Homepage lanes named in order: <yes / no — what differs>
- Setup page lanes named in order: <yes / no — what differs>
- Use-cases page lanes named in order: <yes / no — what differs>
- README role block in same order: <yes / no — what differs>
- Notebook lane labels match the table in T1.1: <yes / no — what differs>

## Next recommended step
- ...
```

No vague language. No unsupported claims. If something was not
verified, say so.

---

## 17. The kill test, before any task

For every action you propose, ask:

1. Does this advance Impact & Vision?
2. Does this advance Video Pitch & Storytelling?
3. Does this advance Technical Depth & Execution?

If the answer is "no" to all three, **cut the task**.

And:

4. Does this preserve the website's five-lane taxonomy?
5. Does this preserve backward-compat aliases?
6. Does this avoid raw PII in committed artifacts?

If the answer is "no" to any of 4–6, **do not do the task**.

---

## 18. Closing

The competition deadline is 2026-05-18. We're 9 days out. The
codebase is in good shape; what's left is consistency polish that
makes the difference between a complete submission and a winning
one. Spend the 8–10 hours on visible, judge-facing improvements —
not on internal tidiness no judge will see.

Slow down. Verify. Commit small. Push only when tests pass.
