# Copilot Handoff: Cross-Repo Consistency Review

> **Role:** You are doing a structured design + nomenclature + taxonomy
> review of a multi-component AI safety project. The output is a
> prioritized punch list of suggestions, not direct code edits. The
> human will decide which to apply.

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

## What to produce

A single Markdown report with this structure:

```markdown
# Copilot review of DueCare wheel + kernels vs website

## Headline findings
- 3-5 bullet points; the most important issues

## Nomenclature drift (sweeps not yet complete)
- One row per banned-term hit, with file:line and a one-line fix

## Visual / structural drift
- Wheel chat playground vs website chrome
- Kernel READMEs vs website docs pages
- Anything that uses a different layout pattern than the website

## Taxonomy alignment with app/schema.py
- Are wheel models named consistently with schema.py?
- Are kernel example outputs shaped like the canonical envelope?

## Missing website coverage
- Features in wheel/kernels that the website does not document
- Suggested website page or section for each

## Quick wins
- Items under ~10 lines each that are pure copy + paste fixes

## Larger refactors (not for one-shot fixes)
- Items the human should decide whether to take on; explain trade-offs
```

Cap the report at ~2000 words. Be specific: use file paths and line
numbers, quote the actual current text, propose the actual replacement.
Avoid theory; aim for actionable items that a human can apply or reject
in a single review pass.

## What NOT to do in this review

- Do **not** write or edit any code files. The output is a report.
- Do **not** run shell commands beyond `grep`/`find` for searching.
- Do **not** break the deployed website by suggesting changes that
  would require schema migrations without flagging them as such.
- Do **not** invent terminology. If the right word doesn't exist in
  the website's lexicon, propose it explicitly and explain why.
- Do **not** flag style choices as problems unless they violate the
  enforced rules above (em dashes, banned terms, etc.).

## Final note

The human author has been polishing this codebase under deadline
pressure for the Gemma 4 Good Hackathon (submission 2026-05-18).
Bias your suggestions toward **high-leverage, low-risk** changes that
visibly improve the demo for a judge looking at this for the first
time. Mark anything risky or breaking as such. Mark anything that's
"nice but not load-bearing" as such.
