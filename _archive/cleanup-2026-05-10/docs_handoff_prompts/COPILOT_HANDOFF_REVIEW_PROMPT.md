# Copilot Handoff: Cross-Repo Consistency Review

> **Role:** You are doing a structured design + nomenclature + taxonomy
> review of a multi-component AI safety project. The output is a
> prioritized punch list of suggestions, not direct code edits. The
> human will decide which to apply.

## First five minutes (read in this order)

1. This document, top to bottom (you're here).
2. `apps/duecare-ai.com/app/main.py` — public-hub FastAPI app + every
   route + every Pydantic model. Skim, don't deep-read.
3. `apps/duecare-ai.com/app/schema.py` — the canonical knowledge-object
   hierarchy. **This is the taxonomy you check everything else against.**
4. `apps/duecare-ai.com/app/templates/index.html` — public homepage.
   This is the project's self-description; the wheel + kernels should
   be saying the same thing.
5. `kaggle/_INDEX.md` — the canonical 13-kernel ordering and titles.
6. `packages/duecare-llm-chat/src/duecare/chat/_brand.py` — the wheel's
   single-source-of-truth for layer counts.

If you only have time for steps 1-3, do those. Steps 4-6 catch the
wheel/kernel-side findings.

## What this project is, in one paragraph

DueCare is a Gemma 4-powered safety harness for migrant-worker
protection. It ships as: (a) a public coordination website at
[duecare-ai.com](https://duecare-ai.com) (currently
[gemma4-comp.onrender.com](https://gemma4-comp.onrender.com)), (b) a
Python wheel called `duecare-llm-chat` that bundles the chat
playground + 11 static viewer pages + the safety harness, and (c) 13
Kaggle notebook kernels (2 core + 11 appendix) that demo the wheel on
free GPUs. The website was just put through a heavy polish pass.
**It is the design + nomenclature + taxonomy source of truth.**

## Hackathon and stakes

This is a submission for the **Gemma 4 Good Hackathon** on Kaggle,
deadline **2026-05-18**, with a $200K prize pool. The judging rubric
is weighted:

- **Impact & Vision — 40 pts** (verified from the 3-minute video)
- **Video Pitch & Storytelling — 30 pts** (also from the video)
- **Technical Depth & Execution — 30 pts** (verified from the code
  repository + writeup, which means: from what you are reviewing)

70 points live in the video; 30 in the code. **Your review should
bias toward the 30 — anything that makes a judge looking at the code
go "this is real, well-engineered, internally consistent" wins more
than another polish micro-pass on a page only the author will see.**

## Two surfaces, one product

DueCare deliberately has **two surfaces** that look like the same
product but serve different audiences:

1. **The Kaggle live demo** at
   [`kaggle.com/code/taylorsamarel/duecare-harness-chat`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat) —
   technical-depth proof. A judge clicks "Run All", a cloudflared URL
   prints, the chat playground opens. This is the wheel + kernel
   surface you are auditing.
2. **The public hub** at
   [`duecare-ai.com`](https://duecare-ai.com) (live at
   [`gemma4-comp.onrender.com`](https://gemma4-comp.onrender.com)) —
   platform-infrastructure proof. Shows the project is shared
   coordination infrastructure, not one chatbot. This is the website
   surface that is the source of truth.

When the wheel and the website disagree on a name, a count, or a
shape, the **website wins** — but flag the disagreement so the human
can decide whether to retro-fix the website instead.

## Eight-component platform

The website's `/components` and `/architecture` pages frame the project
as eight components. Use this taxonomy when you are reviewing what is
documented vs. what exists:

| # | Component | Status | Lives at |
|---|---|---|---|
| 1 | **Runtime** (Gemma 4 model layer) | Live | Wheel + Kaggle |
| 2 | **Harness** (GREP + RAG + Tools + Online + Persona + Imports) | Live | Wheel |
| 3 | **Exchange** (privacy-preserving signed-pack distribution) | Hub-scaffolded | Public hub |
| 4 | **Eval** (rubrics + benchmarks + regression gate) | Partial | Wheel + A-11 kernel |
| 5 | **Trainer** (Unsloth LoRA -> GGUF / LiteRT) | Prototype | A-07 kernel |
| 6 | **Sentinel / Server automation** (continuous-update agent) | Hub-scaffolded | Public hub |
| 7 | **Channels** (NGO / regulator chatbot integrations) | Roadmap | n/a |
| 8 | **Mobile** (Duecare Journey on-device app) | Live, sibling repo | [`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android) |

Anything in the wheel or kernels that maps to one of these components
should be findable from the website's `/components` or `/architecture`
page. Anything that doesn't map should appear in your "missing website
coverage" findings.

## What to use as the source of truth

**The website is canonical.** When you see drift between the website
and any other surface, **the website wins** unless the website is
demonstrably wrong.

Read these files first; they ARE the design language:

```
apps/duecare-ai.com/
├── app/
│   ├── main.py                         FastAPI app + 21 routes + Pydantic models
│   ├── schema.py                       Knowledge-object hierarchy (schema.org-style)
│   ├── packs.py                        Pack registry + filter/version/sync helpers
│   ├── automation.py                   Server-side LLM (vet/extract/draft/verify)
│   ├── hub_client.py                   Reference client; the protocol contract
│   ├── pii.py                          Edge-filter PII detector (shared)
│   ├── data/packs/*.json               4 example packs (ContextPack, GrepRulePack,
│   │                                   ContactPack, RubricPack) showing the canonical
│   │                                   envelope shape
│   ├── static/styles.css               Visual system (light, warm-paper, civic teal)
│   ├── static/hub-pages.css            Hub-family page styles
│   └── templates/                      40 Jinja templates
│       ├── _nav.html                   Shared top nav
│       ├── _footer.html                Shared 2-level footer
│       ├── index.html                  Home (5-use-case grid + privacy band)
│       ├── mission.html                Mission (10 sections, TOC sidebar)
│       ├── hub.html                    Hub overview (8-tab integrate panel)
│       ├── docs.html                   Docs index
│       ├── contribute.html             3-pathway contribute page + form
│       ├── server-automation.html      Replaces /openclaw; documents the LLM engine
│       └── ... (32 more pages)
└── docs/
    ├── BULK_INGEST_PLAN.md             Architecture for the local-KB feature
    ├── HOST_HUB_GLOBAL_SERVER_PLAN.md  Hub design intent
    └── TECHNICAL_DOCS_PAGE_PLAN.md     Technical-docs page plan
```

The wheel runtime is a **separate FastAPI app** that lives inside the
Kaggle session — not the same app as the website hub. It has its own
routes, its own Pydantic models, its own static pages. Read these
files alongside the website source-of-truth to spot terminology drift
between the two FastAPI surfaces:

```
packages/duecare-llm-chat/
├── src/duecare/chat/
│   ├── app.py                          Wheel-side FastAPI app (~5000 LOC)
│   ├── _brand.py                       Single-source-of-truth for live counts
│   │                                   (n_grep_rules, n_rag_docs, etc.) +
│   │                                   layer descriptions consumed by
│   │                                   /api/brand and the static pages
│   ├── _model_output.py                Sanitizer for Gemma 4 thinking-mode
│   │                                   leaks; covered by 15-case regression
│   ├── _grading.py                     The 4 grading modes
│   ├── harness/
│   │   ├── __init__.py                 161 GREP rules + 46 RAG docs lists
│   │   ├── _rubric_universal.json      46-dim rubric v3.10
│   │   ├── _examples.json              587 example prompts (8 buckets)
│   │   ├── _citations.json             46-edge citation graph
│   │   ├── _contacts.json              26-entry contact directory
│   │   └── _governance.py              Curator-block JSON loaders
│   └── static/
│       ├── _chrome.css                 NEW shared design tokens
│       ├── index.html                  Chat playground (large, ~5000 LOC)
│       ├── anonymization-preview.html  NEW privacy preview page
│       ├── harness.html                Catalog of safety layers
│       └── persona.html, grep-rules.html, ... (10 more viewer pages)
└── tests/                              Unit tests for the wheel
```

Plus the kernel side (the actual notebooks judges click on):

```
kaggle/
├── _INDEX.md                           Canonical 13-kernel ordering
├── 01-duecare-harness-chat/            Core notebook 1 (script)
│   ├── kernel.py                       What Kaggle executes
│   ├── README.md                       Just standardized in this push
│   └── kernel-metadata.json            Kaggle slug + dataset references
├── 02-live-demo/                       Core notebook 2 (notebook)
└── A-01-...                            Appendix notebooks A-01 .. A-11
```

And the cross-cutting helpers:

```
scripts/
├── polish_kernels_uxbar.py             Kernel intro + README + footer pass
└── (10+ other v141_ / v07_ / v09_ scripts the human uses ad hoc)

apps/duecare-ai.com/scripts/
├── build_design_templates.py           One-shot design import from claude.ai/design
├── partialize_nav_footer.py            Extract shared partials
├── polish_design_templates.py          First polish pass
├── polish_design_pass2.py              Second pass (em-dash + chip cleanup)
└── polish_design_pass3.py              Third pass (signed -> vetted, brand casing)

packages/duecare-llm-chat/scripts/
└── polish_wheel_chrome.py              Bulk wheel polish (chrome link + titles)
```

## Design principles the website embodies

You are checking whether the **wheel** and the **kernels** follow these
same principles.

### 1. Plain English over jargon

The website went through a sweep that dropped jargon for plain words.
Track these enforced renames; anything in the wheel/kernels still
using the old term is a finding:

| Banned | Replacement | Why |
|---|---|---|
| `signed` (as a noun adjective for packs) | `vetted` | "Signed" reads as cryptographic; "vetted" reads as approved |
| `coarse` (as a modifier for signals/patterns) | `anonymized` | "Coarse" doesn't mean anything to non-engineers |
| `Eval` / `eval` (as a standalone word) | `Evaluation` / `evaluation` | Real word, not a fake abbreviation |
| `OpenClaw` / `OpenCrawl` / `Sentinel` (as product names) | `server automation` / `the automation` / `the public-source crawler` | We don't own those names; pages should not lock to a specific upstream project |
| `Harness inspector` | `Safety layers` | The user-facing concept is layers, not inspection |
| `NOT WIRED` (status label) | `Not enabled here` | "NOT WIRED" reads as a bug |
| Em dashes (`—`) in prose | `.` or `,` based on context | Style choice; consistent across the site |

### 2. Consistent nomenclature for knowledge objects

Every artifact descends from `KnowledgeObject` in `app/schema.py`. The
site uses these terms with these meanings; cross-check that the wheel
and kernels match:

- **Knowledge pack** — the artifact (a versioned, downloadable bundle
  the hub serves)
- **Corridor pack** — a knowledge pack scoped to one migration
  corridor (e.g. PHL-KWT)
- **Context pack** — a knowledge pack when retrieval is loading it
  into a model prompt
- **Vetted pack** — any knowledge pack a curator has approved
- **Server automation** — the hub-side LLM that vets/extracts/drafts/verifies
- **Anonymization pipeline** — the pre-send privacy gate (regex →
  LLM → preview → confirm)
- **Safety layers** — the 6 toggleable harness layers (Persona, GREP,
  RAG, Tools, Online, Imports). NOT "inspector", NOT "harness modules"
- **Grading modes** — the UI uses Rule-Based / LLM-Based / Combined /
  Expert (legacy). Some kernels still call them Universal / Expert /
  Deep / Combined; flag every mismatch

The schema-org-style envelope every Pack subtype carries:

```jsonc
{
  "@context": "https://duecare-ai.com/schema/v1",
  "@type": "ContextPack",   // or GrepRulePack / ToolPack / ContactPack /
                            // RubricPack / EvalPromptPack / TrainingExamplePack
  "id": "phl-kwt-domestic",
  "version": "1.7.2",
  "schema_version": 1,
  "status": "vetted",       // proposed | needs_review | vetted | deprecated
  "jurisdictions": [...],
  "corridors": [...],
  "tags": [...],
  "source": {...},
  "provenance": {...},
  "content_hash": "sha256:...",
  "content": {...},         // shape varies by @type
  "extensions": {}          // open dict; partners add "<vendor>.<key>" fields
}
```

### 3. Visual system

The website uses:

- **Typography**: Inter (UI) + JetBrains Mono (labels / code)
- **Palette**: warm paper background (`--paper #F7F6F1`), warm ink
  (`--ink #0E1116`), civic teal accent (`--accent oklch(0.52 0.08 195)`),
  ember used **only** for the privacy boundary (`--ember oklch(0.58 0.14 45)`)
- **Hero pattern**: every top-level page uses the 2-column grid
  (`minmax(0, 1.4fr) minmax(280px, 1fr)`, gap 56px) with a kicker +
  h1 + lede on the left and a TOC sidebar on the right
- **Section anchors**: every page section has an `id` so the TOC
  links anchor correctly
- **Card pattern**: whole-card click (use `<a class="card" href>`,
  not `<div>` with a tiny inner link)
- **Footer**: 2-level (centered brand line on top, 4 columns below)
  with one separator only (the outer `<footer>` border-top)

The wheel uses a **dark** playground theme but the same Inter + JetBrains
Mono typography. The shared `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
carries the typography import and color tokens; per-page overrides are
limited to `--accent`.

## What to review

### 4.1 Wheel chat playground (`packages/duecare-llm-chat/src/duecare/chat/`)

Check:

- `static/index.html` — main chat UI. Does the empty state advertise
  the demo path clearly? Is the layer count consistent with the actual
  number of toggles (6)? Does the About modal still help a first-time
  judge?
- `static/_chrome.css` — the shared chrome added recently. Any per-page
  CSS that should move into the shared module?
- `static/anonymization-preview.html` — the new privacy-pipeline
  preview page. Is the three-stage layout (Local / Boundary / Outbound)
  clear? Does it use the same nomenclature as the website?
- The 11 viewer pages (`harness.html`, `persona.html`, `grep-rules.html`,
  `grep-tester.html`, `rag-corpus.html`, `rag-graph.html`, `tools.html`,
  `online.html`, `hotlines.html`, `search.html`, `index.html`) — do
  they all link `_chrome.css`? Do their headers use the shared
  `dc-chrome-header` class? Is the cross-page nav consistent?
- `app.py` and `harness/` modules — do their docstrings + Pydantic
  models use the canonical terminology from `apps/duecare-ai.com/app/schema.py`?

### 4.2 Kaggle kernels (`kaggle/`)

There are 13 kernels:

- `01-duecare-harness-chat/` — core notebook 1 (chat playground)
- `02-live-demo/` — core notebook 2 (focused live URL)
- `A-01-chat-playground/` through `A-11-grading-evaluation/` — appendix

Each one has been intro'd with a markdown / comment-block header. Check:

- Does each kernel's intro accurately describe what the notebook does?
- Do the bullet "what to look for after Run All" items match what
  Run All actually produces?
- Is the per-notebook README h1 in the canonical form
  `# DueCare — <title> (#NN core | #ANN appendix)`?
- Is the cross-kernel footer (under `<!-- duecare:kernel-footer -->`)
  consistent? Does it list all 13 kernels with the current one bolded?
- Does the kernel reference the live hub URL
  (`https://gemma4-comp.onrender.com`) when describing the hub
  side, instead of inventing a different URL?

### 4.3 Cross-repo nomenclature drift

For every banned term in the table above:

```
grep -rn "<banned>" packages/ kaggle/ docs/
```

Report each hit with context. The website-side sweep is done; the
wheel + kernel side is partial.

### 4.5 Two FastAPI apps, one product family

There are TWO distinct FastAPI applications in this repo. They share
some Pydantic shapes and a lot of vocabulary, and they need to stay
in sync:

- **Public hub app**: `apps/duecare-ai.com/app/main.py` — runs at
  `gemma4-comp.onrender.com`. Models live in `app/main.py` itself
  plus the typed hierarchy in `app/schema.py`.
- **Wheel runtime app**: `packages/duecare-llm-chat/src/duecare/chat/app.py`
  — runs inside Kaggle when judges click Run All. Has its own routes
  for chat, examples, governance, retrieval, grading.

Look for:

- **Endpoint paths** that the website documents but the wheel runtime
  exposes differently (or vice versa).
- **Pydantic class names** that should match across both apps but
  don't. The wheel predates `app/schema.py`; ideally the wheel
  imports the canonical types from `apps/duecare-ai.com/app/schema.py`
  or at minimum mirrors them. Today it doesn't.
- **Counts** that the website hard-codes vs. counts the wheel exposes
  via `/api/brand` and `_brand.py`. The website should defer to
  `_brand.py` numbers wherever possible (the human has tagged some of
  these with `data-brand-count` HTML attributes).

### 4.6 Pack JSON files vs. canonical schema

`apps/duecare-ai.com/app/data/packs/*.json` are the four example packs
the registry serves. They need to be valid against `app/schema.py`'s
`KnowledgeObject` -> `Pack` -> `<subtype>` hierarchy.

For each file in `app/data/packs/`:

- Does the `@type` field match a class in `app/schema.py`?
- Are all required envelope fields present (`id`, `version`,
  `schema_version`, `status`, `source`, `provenance`)?
- Is `content_hash` consistent with the `content` payload? (the
  website's `canonical_content_hash()` helper computes this)
- Are jurisdictions / corridors strings consistent with the format
  used elsewhere (ISO codes, `XXX-YYY` for corridors)?

Report any pack that would fail strict validation against
`KnowledgeObject` + its declared subtype.

### 4.7 Local-KB feature (just shipped, lightly tested)

`apps/duecare-ai.com/app/local_kb.py` + `templates/local-kb.html` +
`/api/local-kb/*` endpoints are a brand-new feature added in the same
review window. Look for:

- Does the local-KB module's vocabulary match the canonical schema?
  (entities have `kind`, `name_hash`; cases have `corridor`, `sector`,
  `summary` — same words used elsewhere?)
- Does the `/local-kb` page use the standard hero+TOC pattern other
  pages use?
- The architecture lives in `apps/duecare-ai.com/docs/BULK_INGEST_PLAN.md`.
  Does the shipped scaffold honor the hard contracts (nothing leaves
  device until explicit, opt-in processing, anonymization gate)?
- Is the right-to-erasure ("Forget everything") path complete and
  irreversible?

### 4.8 The 307/308 redirects we kept for backward compat

After the OpenClaw -> server-automation rename:

- `GET /openclaw` returns 307 -> `/server-automation`
- `POST /api/hub/openclaw/inbound-email` returns 308 ->
  `/api/hub/automation/inbound-email`

If you spot any internal link still using the legacy paths (templates,
docs, kernels), it should be updated to the new path. The redirect is
for external callers only.

### 4.4 Things the wheel/kernels do that are NOT documented on the website

The website talks about: signal intake, opencrawl proposals, knowledge
packs, anonymization, server automation. The wheel + kernels include
features the website does not cover yet, e.g.:

- The `Compare` tab (run same prompt with two harness configs)
- The `Online` layer's deep-fetch via Playwright (`A-09`)
- The jailbroken-Gemma comparison (`A-10`)
- The Unsloth fine-tune + GGUF export pipeline (`A-07`)
- The Gemma-self-generates-evaluation-prompts loop (`A-06`)

For each, check whether the website's `/components`, `/harness`,
`/evaluation`, `/why-gemma`, or `/docs` pages mention it. Anything not
mentioned should appear in your suggestions list as **"Document on
the website"**.

## Project conventions you must respect

The repo has these enforced conventions. If you suggest something
that breaks one, **flag it explicitly as a constraint violation**:

### Auto-loaded rules at `.claude/rules/`

These markdown files load into every Claude Code session and apply to
every change in the repo. Read each at least once before reviewing:

- `00_overarching_goals.md` — the three rubric goals (Impact / Video /
  Tech) every action is measured against
- `10_safety_gate.md` — no PII in git, logs, training data, or
  published artifacts. Hard rule. The `_reference/` folder is
  gitignored because it contains proprietary benchmark data
- `20_code_style.md` — Python 3.11+, Pydantic v2, `typing.Protocol`
  for cross-layer contracts, type hints on everything,
  `pathlib.Path` over `os.path`, no bare `except:`
- `30_test_before_commit.md` — `duecare test` must pass before any
  code commit
- `40_forge_module_contract.md` — folder-per-module pattern: every
  module is its own folder with PURPOSE.md / AGENTS.md / TESTS.md etc.
  auto-generated from a descriptor list
- `50_publish_strategy.md` — three channels: GitHub (this repo) +
  PyPI (17 packages under `packages/`) + Kaggle Notebooks
- `60_notebook_presentation.md` — Kaggle-safe HTML (the saved-output
  viewer strips `<script>`, `display:flex`, `max-height + overflow:auto`,
  `position:fixed|absolute|sticky`, external stylesheets, custom fonts).
  No truncation in displayed text (no `text[:N]...`). Pandas Styler +
  Markdown over raw HTML. Shared helpers in `scripts/_notebook_display.py`.

### "Execute, don't ask"

The author has a documented preference (in `~/.claude/.../memory/`)
for "execute, don't ask — pick sensible defaults and proceed" for
reversible work. This applies to your suggestions: write each one as
something the author can apply directly, not as a question to answer.

### Test commands

Hub tests:

```
DUECARE_DATA_DIR=/tmp/dc_smoke pytest apps/duecare-ai.com/tests/
```

(currently 19/19 passing). The wheel + kernels have less test
coverage; flag any place where you'd want a test but there isn't one.

### Environment variables

The wheel + hub honor these env vars:

- `DUECARE_HUB_URL` — overrides the default public hub URL in
  `app/hub_client.py`. Lets a deployer point at their own private
  hub or federate.
- `DUECARE_AUTOMATION_*` — provider config for the LLM evaluator
  (OpenRouter / Mistral / OpenAI / Ollama); legacy `OPENCLAW_*`
  names still read for backward compat via `_env()` helper
- `DUECARE_DATA_DIR` — Render disk mount point for hub JSONL store
- `DUECARE_LOCAL_KB` — path to operator's local-KB SQLite file
- `DUECARE_LOCAL_KB_SALT` — per-deployment salt for entity name hashing

Don't suggest renaming any of these without flagging the migration cost.

### Sibling repos

- `duecare-journey-android` (separate GitHub repo) — the on-device
  Mobile companion app. The website's `/components` page links to it;
  if you spot anything in the website or wheel that contradicts what
  the Mobile app does, flag it.
- `_reference/` (gitignored) — the author's proprietary 21K-test
  trafficking benchmark. Code in this repo can reference patterns from
  it but never include its data. **Never suggest committing anything
  under `_reference/`.**

## What to produce

A single Markdown report with this structure:

```markdown
# Copilot review of DueCare wheel + kernels vs website

## Headline findings
- 3-5 bullet points; the most important issues

## What looks right (do NOT change)
- 5-10 bullets calling out things that are working well so the
  author knows not to retro-fix them in a polish pass

## Nomenclature drift (sweeps not yet complete)
For each banned-term hit:
- file:line — quoted current text — proposed replacement — effort: S
- (S = under 10 lines, M = 10-50 lines, L = 50+ lines or
  cross-cutting)

## Visual / structural drift
- Wheel chat playground vs website chrome
- Kernel READMEs vs website docs pages
- Anything that uses a different layout pattern than the website

## Taxonomy alignment with app/schema.py
- Are wheel Pydantic models named consistently with schema.py?
- Are example pack JSON files in app/data/packs/ valid against the
  declared @type subtype?
- Are kernel outputs shaped like the canonical envelope where they
  produce serialized records?

## Two-FastAPI-app divergence
- Endpoint paths the website documents but the wheel exposes differently
- Pydantic class names that should mirror across both apps but don't
- Counts that the website hard-codes vs counts the wheel exposes via
  /api/brand and _brand.py

## Missing website coverage
For each wheel/kernel feature not yet on the website:
- What it does
- Suggested website page or section for it
- Effort: S/M/L

## Breaking-change flags
- For every suggestion that would change a public API, env var, route,
  or Pydantic schema field name, mark it [BREAKING] and explain the
  migration cost. Default to "don't break things" unless the gain
  clearly justifies it.

## Things you cannot verify from the code
- Anything where you'd need to run the wheel, hit a live URL, view
  rendered HTML, or check Kaggle's saved-output viewer to be sure.
- Be honest. The human can verify these.

## Quick wins
- Items under ~10 lines each that are pure copy + paste fixes.
  Order by visual impact for a judge.

## Larger refactors (not for one-shot fixes)
- Items the human should decide whether to take on; explain trade-offs.
- Estimate effort: M (one focused session) or L (multiple sessions).

## Constraint violations (anything that breaks the .claude/rules/ files)
- For each, name which rule and why your finding doesn't apply.
- If your finding is correct AND breaks a rule, propose a path that
  honors both.
```

Cap the report at ~3000 words. Be specific: use file paths and line
numbers, quote the actual current text, propose the actual replacement.
Avoid theory; aim for actionable items that a human can apply or reject
in a single review pass.

## How to read this codebase efficiently

If you're starting cold, this is the fastest path to understanding
what's where:

1. `apps/duecare-ai.com/app/main.py` — read the route table at the
   top + the PAGE_ROUTES dict. That's the website surface in a
   single file.
2. `apps/duecare-ai.com/app/schema.py` — read the class hierarchy.
   Everything in the system is a `KnowledgeObject` or descends from
   one.
3. `apps/duecare-ai.com/app/templates/index.html` — read the home
   page hero + the 5 use-case cards. That's the project's public
   self-description.
4. `apps/duecare-ai.com/app/templates/hub.html` — read sections 01
   (what the hub is), 03 (what it gives you), 04 (the 8-tab
   integrate panel). That's the API contract in narrative form.
5. `packages/duecare-llm-chat/src/duecare/chat/_brand.py` — read
   it. This is the wheel's single-source-of-truth for live counts.
6. `packages/duecare-llm-chat/src/duecare/chat/static/index.html`
   — large file (~5000 LOC). Skim the top + the empty-state +
   the harness-tiles section. Don't try to read every line.
7. `kaggle/_INDEX.md` — the canonical 13-kernel ordering with the
   canonical title for each.
8. `apps/duecare-ai.com/docs/BULK_INGEST_PLAN.md` — the brand-new
   local-KB design that just shipped a scaffold.

Then run the banned-term grep across `packages/`, `kaggle/`, `docs/`
and you'll have most of the punch list.

## Common anti-patterns this codebase already avoids (don't reintroduce)

The website went through several passes that surfaced and killed these
specific anti-patterns. Don't suggest reverting toward any of them:

- **Cards with a tiny inner link**. Cards must be whole-element
  clickable. We use `<a class="card" href>` not `<div>` + footer link.
- **Truncated displayed text in notebooks**. No `text[:N]...` on
  anything a reader is supposed to understand.
- **`display:flex` and `max-height:Npx; overflow:auto`** in HTML the
  Kaggle viewer renders. Both get stripped.
- **Inline `<script>`** in any HTML the Kaggle viewer renders. Stripped
  for security.
- **Emoji as load-bearing UI**. The website rule is "only use emojis
  if explicitly requested". Existing emoji in the wheel UI is
  grandfathered but new UI should use word labels + small SVG glyphs.
- **Single-letter glyph badges** (e.g. `[C]` for Context, `[R]` for
  Grep). The contribute page already had these and they were replaced
  with descriptive cards. Don't suggest adding new single-letter
  badges anywhere.
- **Em dashes** in prose copy. We use `.` or `,` based on context.
  Standalone em dashes in tables (as "n/a" cell-fillers) are OK.
- **Brand-name jargon**. "OpenClaw", "Sentinel", "OpenCrawl" are
  upstream project names we don't own. The website calls the engine
  "server automation" or "the public-source crawler" depending on
  context.
- **"Coarse signal" / "Eval" / "signed pack"** — see banned-term table.
- **Mid-footer separator lines**. The footer has exactly one separator
  (the outer `<footer>` border-top). Inner mid-footer borders create
  the "three horizontal lines" issue we already fixed.
- **Centered-narrow page widths (`max-width: 980px`)** as a way to
  make pages look like blog posts. Every top-level page uses the
  standard 1200px wrap. The mission page used to override this; we
  removed the override.

## What NOT to do in this review

- Do **not** write or edit any code files. The output is a report.
- Do **not** run shell commands beyond `grep`/`find` for searching.
- Do **not** break the deployed website by suggesting changes that
  would require schema migrations without flagging them as such.
- Do **not** invent terminology. If the right word doesn't exist in
  the website's lexicon, propose it explicitly and explain why.
- Do **not** flag style choices as problems unless they violate the
  enforced rules above (em dashes, banned terms, etc.).
- Do **not** suggest renaming any of the env vars (`DUECARE_*`,
  legacy `OPENCLAW_*`) without explicitly flagging the migration cost
  and the backward-compat fallbacks already in place.
- Do **not** suggest committing anything under `_reference/` — that
  folder is gitignored on purpose because it contains the author's
  proprietary 21K-test trafficking benchmark. The repo can reference
  patterns from it, never include its data.
- Do **not** suggest adding tracking pixels, analytics, telemetry, or
  any "send a beacon to learn more about users" code. The privacy
  story is load-bearing.
- Do **not** propose Python <3.11 compatibility. The repo is 3.11+
  and uses 3.12 in production (Render Dockerfile pins `python:3.12-slim`).
- Do **not** propose moving away from FastAPI / Pydantic v2 / Jinja2 /
  uvicorn. These are the chosen stack.

## When in doubt

If you can't tell whether a finding is correct without seeing the
rendered output, **say so explicitly in the "Things you cannot verify"
section** rather than guessing. The human can spin up the site and
the wheel locally to verify; they'd rather have an honest "I think X
but cannot confirm without rendering" than a confident wrong answer.

If you find something the website does that contradicts itself
(rare but it happens — terminology drift between two pages, a count
that's wrong in one place vs another), flag the contradiction and
propose which of the two should win. Don't assume one is right.

## Final note

The human author has been polishing this codebase under deadline
pressure for the Gemma 4 Good Hackathon (submission 2026-05-18).
Bias your suggestions toward **high-leverage, low-risk** changes that
visibly improve the demo for a judge looking at this for the first
time. Mark anything risky or breaking as such. Mark anything that's
"nice but not load-bearing" as such.
