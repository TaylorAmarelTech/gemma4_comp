# DueCare Kaggle Notebooks — Iteration Brief for GPT 5.5x

> **Self-contained brief.** Paste this whole document into GPT 5.5x. No
> external file fetches required. Goal: **iterate and improve** all 13
> Kaggle notebooks toward production polish suitable for the 3-minute
> hackathon screen-recording video. Output concrete edits / diffs /
> file contents, not just recommendations.

---

## 0. Read this first

Today is **2026-05-11**. The Gemma 4 Good Hackathon submission is due
**2026-05-18** — T-7 days. The submission ships **13 Kaggle notebooks**
plus a public website plus a writeup plus a 3-minute video.

**The video is a screen recording of the live product**, not slides or
mock-ups. Every UI surface a camera might pan past must look intentional
and finished before recording begins. A re-record is expensive (Taylor's
time + GPU quota + cloudflared session continuity).

Your job is **not to redesign from scratch**. The visual system, audience
lanes, shell primitives, dashboards, and dc_log standard are all in
place and proven. Your job is to **find every remaining friction point**
across all 13 notebooks, propose specific edits, and where appropriate
output the actual code/HTML to apply.

Latest committed state: **commit `3e3ff9e`** on `master`. Latest chat
wheel: **`duecare-llm-chat 0.16.0`** (kernel-shell `homepage_html` +
`extra_routes` extension). Latest server wheel: **`duecare-llm-server
0.1.2`** (`/wb-static/` cross-mount).

---

## 1. Mission (one paragraph)

You are reviewing **DueCare** — a Gemma 4-powered safety harness for
migrant-worker protection. The harness wraps Gemma 4 with persona +
161 deterministic GREP regex rules + 46-doc RAG corpus across 27
jurisdictions + 5 function-calling tools + an optional online-search
layer, so the model produces grounded, citable, audience-appropriate
responses about labor recruitment, fee scams, passport retention, debt
bondage, and corridor-specific legal protections. The Kaggle submission
ships **2 core + 11 appendix = 13 notebooks** — all visible to judges.
Each has a `kernel.py` (script kernel source) and a `README.md`. The
team has unified them under a shared workbench shell built around three
primitives (`_chrome.css`, `_nav.js`, `dc_log`) plus four bespoke
dashboards (A-06/07/08/11). The remaining work: tighten every visible
surface so the screen recording goes cleanly on the first take.

---

## 2. Hackathon rubric (the scoring math)

| Weight | Axis | What it measures |
|---|---|---|
| 40 | Impact & Vision | Does this address a significant real-world problem? Is the vision inspiring and the potential change tangible? **Verified in the video.** |
| 30 | Video Pitch & Storytelling | How exciting/engaging/well-produced is the video? Does it tell a powerful story? |
| 30 | Technical Depth & Execution | Innovative use of Gemma 4's unique features (native function calling, multimodal). Real, functional, well-engineered, not faked for the demo. **Verified from code + writeup.** |

**70 of 100 points are under the video's control.** Every polish task
should be judged by: does this advance Impact, Video, or Tech-Depth?
If none, cut it.

**Tie-breaker:** Impact > Video > Tech.

---

## 3. The 5 canonical audiences (do not invent new ones)

Source-of-truth: `configs/duecare/canonical_messaging.yaml` +
`docs/canonical_use_cases_and_components.md`.

| Lane | Name | Primary need |
|---|---|---|
| 1 | **Platform safety** | Trust & safety teams scoring recruitment posts/messages, routing high-risk items to reviewers, sharing anonymized abuse patterns. |
| 2 | **NGO & regulator** | Caseworkers, legal-aid groups, consulates, labor inspectors triaging messages and documents, finding contacts, drafting complaint materials. |
| 3 | **Individual worker** | Migrant workers privately checking suspicious offers, contracts, recruiter messages, fee demands; getting localized warning signs and trusted next-step contacts. |
| 4 | **Researcher** | Academic and public-interest researchers reproducing prompts, comparing models, scoring responses, auditing claims from source artifacts. |
| 5 | **Developer / integration partner** | Devs embedding the harness into moderation tools, NGO systems, mobile clients via APIs and pinned wheels. |

Banned alternatives (these labels have been explicitly retired):
"social platforms", "enterprise", "worker-side", "NGO dashboard",
"custom integration", "activist", "media", "OFW".

---

## 4. Repo layout (the relevant slice)

```
gemma4_comp/
├── apps/
│   └── duecare-ai.com/                        ← public website (deployed to Render)
│       └── app/
│           ├── static/styles.css               ← public-site CSS (uses same tokens)
│           └── templates/_nav.html             ← single-row nav template
├── packages/
│   ├── duecare-llm-chat/                      ← chat package (the workbench)
│   │   ├── pyproject.toml                      ← version 0.16.0
│   │   └── src/duecare/chat/
│   │       ├── app.py                          ← FastAPI app factory + chat endpoints
│   │       ├── kernel_shell.py                 ← build_minimal_shell() helper
│   │       ├── _dc_log.py                      ← JSON-Lines logging primitive
│   │       └── static/
│   │           ├── _chrome.css                 ← design tokens + shell styles
│   │           ├── _nav.html                   ← status strip + single-row nav
│   │           ├── _nav.js                     ← auto-injects nav, polls APIs
│   │           ├── showcase.css                ← shared audience-page styles
│   │           ├── index.html                  ← chat homepage (data-nav="chat")
│   │           ├── showcase-*.html             ← 5 audience landing pages
│   │           ├── all-tools.html              ← Tools menu index
│   │           ├── grade.html                  ← standalone grader (data-nav="grade")
│   │           ├── models.html                 ← model picker (data-nav="models")
│   │           ├── logs.html                   ← dc_log viewer (data-nav="logs")
│   │           ├── import.html                 ← doc import (data-nav="import")
│   │           ├── settings.html               ← retrieval/online config (data-nav="settings")
│   │           ├── harness.html                ← layer catalog (data-nav="layers")
│   │           ├── persona.html                ← (data-nav="layers")
│   │           ├── grep-rules.html             ← (data-nav="layers")
│   │           ├── grep-tester.html            ← (data-nav="layers")
│   │           ├── rag-corpus.html             ← (data-nav="layers")
│   │           ├── rag-graph.html              ← (data-nav="layers")
│   │           ├── tools.html                  ← function-calling tools (data-nav="layers")
│   │           ├── online.html                 ← (data-nav="layers")
│   │           ├── search.html                 ← cross-layer search (data-nav="search")
│   │           ├── hotlines.html               ← hotline directory (data-nav="hotlines")
│   │           └── anonymization-preview.html  ← (data-nav="anonymize")
│   └── duecare-llm-server/                    ← server package (the public hub)
│       ├── pyproject.toml                      ← version 0.1.2
│       └── src/duecare/server/
│           ├── app.py                          ← FastAPI app + /wb-static/ cross-mount
│           └── static/                         ← server-specific homepage assets
└── kaggle/
    ├── 01-duecare-exploration-workbench/      ← CORE notebook #1
    │   ├── kernel.py
    │   ├── kernel-metadata.json
    │   ├── README.md
    │   └── wheels/                             ← duecare-llm-chat-0.16.0.whl + deps
    ├── 02-live-demo/                          ← CORE notebook #2
    ├── A-01-chat-playground/                  ← appendix
    ├── A-02-chat-playground-with-grep-rag-tools/
    ├── A-03-content-classification-playground/
    ├── A-04-content-knowledge-builder-playground/
    ├── A-05-gemma-content-classification-evaluation/
    ├── A-06-prompt-generation/                ← has corpus-browser dashboard
    ├── A-07-bench-and-tune/                   ← has training-pipeline dashboard
    ├── A-08-research-graphs/                  ← has inline-chart dashboard
    ├── A-09-chat-playground-with-agentic-research/
    ├── A-10-chat-playground-jailbroken-models/
    └── A-11-grading-evaluation/               ← has lift dashboard
```

---

## 5. Design system (the visual source of truth)

The public website (https://duecare-ai.com) is the canonical aesthetic.
The chat package's `_chrome.css` and server package's `style.css` both
import the same tokens. Every notebook UI must match.

**Aesthetic direction:** civic-tech research lab. Warm paper backgrounds,
not stark white. Dark ink text, not gray-on-gray. Civic teal accent used
sparingly. Ember orange reserved exclusively for privacy-boundary
indicators. No generic Tailwind defaults, no dark mode (except the
intentional shutdown overlay).

**Tokens (must match exactly):**

```css
/* Surfaces (warm paper) */
--paper:        #F7F6F1;
--paper-2:      #EFEDE4;
--paper-3:      #E4E1D7;

/* Ink (text) */
--ink:    #0E1116;
--ink-2:  #2A2D34;
--ink-3:  #5B5F68;
--ink-4:  #8A8E97;

/* Lines */
--line:      #DDD8C9;
--line-soft: #E8E4D7;

/* Accent (civic teal) — sparingly */
--accent:      oklch(0.52 0.08 195);
--accent-soft: oklch(0.92 0.03 195);
--accent-ink:  oklch(0.32 0.07 195);

/* Ember (privacy boundary ONLY) */
--ember:      oklch(0.58 0.14 45);
--ember-soft: oklch(0.94 0.04 45);

/* Semantic */
--good: oklch(0.55 0.10 155);   /* success / passing / lift */
--warn: oklch(0.65 0.10 80);    /* warning / unchanged */

/* Typography */
--sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
```

**Banned colors (legacy palette retired in earlier sessions):**
- `#1e40af`, `#1e3a8a`, `#3b82f6`, `#2563eb`, `#0066ff` (legacy dark-blue)
  — only acceptable as semantic jurisdiction-flag colors in `_brand.py`.
- `#f59e0b`, `#ec4899` (legacy amber/pink) — replace with `--warn` /
  `--ember` / `--accent` as appropriate.
- Tailwind grays (`#f8fafc`, `#1f2937`, `#9ca3af`, `#6b7280`, `#e5e7eb`,
  `#d1d5db`) — replace with the paper/ink/line tokens.

---

## 6. The workbench shell (3 reusable primitives)

Every served UI page in the project uses these three primitives so they
look like part of the same product.

### 6.1 `_chrome.css` — the design tokens + base styles

```html
<link rel="stylesheet" href="/static/_chrome.css">
```

Provides: token system, status-strip styles, nav-row styles, button
classes (`.primary`, `.secondary`, `.danger`, `.utility`), card
styles, pill styles, focus rings, table styles. Importing this file
gives a page the entire visual system.

### 6.2 `_nav.html` + `_nav.js` — the shared top chrome

```html
<body data-nav="<key>">     <!-- key matches a nav-key in _nav.html -->
<script src="/static/_nav.js" defer></script>
```

`_nav.js` runs on DOMContentLoaded:
1. Fetches `/static/_nav.html` and inserts it as the first child of `<body>`.
2. Marks the active nav link by matching `<body data-nav>` against the
   nav partial's `data-nav-key` attribute.
3. Polls `/api/version` + `/api/model-info` every 10s to populate the
   status strip (model name, version, GPU memory).
4. Wires the Shutdown button.

Layout (top to bottom):

```
┌──────────────────────────────────────────────────────────────────────┐
│ ● Model: gemma-4-e4b-it · v0.16.0 · 1.2GB GPU      [⏻ Shutdown]      │  ← status strip
├──────────────────────────────────────────────────────────────────────┤
│ DueCare Workbench  Platform · NGO · Worker · Researcher · Developer  │  ← single-row nav
│                                                          [Tools →]   │
├──────────────────────────────────────────────────────────────────────┤
│  [page content]                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Valid `data-nav` keys:
- `chat` (home / playground)
- `platform`, `ngo`, `worker`, `researcher`, `developer` (5 audience tabs)
- `tools` (Tools utility link)
- `grade`, `models`, `logs`, `import`, `settings`, `layers`, `search`,
  `hotlines`, `anonymize` (sub-tools — won't match any nav link but the
  brand stays as the home indicator)

### 6.3 `dc_log` — JSON-Lines logging primitive

```python
from duecare.chat._dc_log import dc_log, set_kernel_id
set_kernel_id("a-XX-some-kernel")
dc_log("chat.send", "user sent prompt", chars=len(prompt))
dc_log("grep.test", "fired 3 rules", layer="grep", rule_ids=["a","b","c"])
dc_log("kernel.error", "model load failed", level="error", err=str(e))
```

Writes one JSON line per event to both stderr AND
`/kaggle/working/duecare-logs.jsonl`. Schema:
`{ts, level, kernel, kind, layer?, msg, ...payload}`.

The Logs page (`/static/logs.html`) reads back via `GET /api/dc-logs?
tail=200&level=warn&kind=grep&layer=rag`. Available endpoints:
- `GET /api/dc-logs` — events tail
- `GET /api/dc-logs/stats` — counts by level/kind
- `POST /api/dc-logs/clear` — drop the ring buffer

---

## 7. The cross-mount: `/wb-static/`

Both the server package (02-live-demo) and the three custom-FastAPI
appendix kernels (A-03, A-04, A-09) mount the chat package's static
directory at `/wb-static/` so they can pull `_chrome.css`, `_nav.js`,
and the audience showcase pages from the same source as notebook #01.

Pattern:

```python
import duecare.chat as _chat_pkg
from pathlib import Path
_wb_static = Path(_chat_pkg.__file__).parent / "static"
if _wb_static.exists():
    app.mount("/wb-static", StaticFiles(directory=str(_wb_static)), name="wb-static")
```

Then in the served HTML:

```html
<link rel="stylesheet" href="/wb-static/_chrome.css">
<script src="/wb-static/_nav.js" defer></script>
<body data-nav="tools">
```

---

## 8. The `build_minimal_shell()` helper (notebook-only kernels)

For notebooks that compute outputs without needing the full chat playground
(A-05, A-06, A-07, A-08, A-11), `build_minimal_shell()` gives them a
workbench-consistent web UI with one call.

Signature (chat 0.16.0):

```python
from duecare.chat.kernel_shell import build_minimal_shell

app, url = build_minimal_shell(
    summary={                        # required — fallback summary view
        "title": "...",
        "audience": "researcher",
        "lede": "...",
        "results": [{"label": "...", "value": "..."}],
        "artifacts": [{"name": "...", "path": "..."}],
        "links": [("Workbench (full)", "https://...")],
        "next_steps": ["..."],
    },
    kernel_id="a-XX-some-kernel",
    port=8080,
    homepage_html=my_dashboard_html, # OPTIONAL — overrides GET /
    extra_routes={                   # OPTIONAL — kernel-specific routes
        "/api/lift":        ("GET", _api_lift_handler),
        "/export/lift.csv": ("GET", _export_csv_handler),
    },
)
```

Always-available routes (the helper wires these for you):
- `GET /` — dashboard or summary
- `GET /summary` — default summary (always reachable)
- `GET /healthz`, `/api/version`, `/api/model-info`, `/api/brand`
- `GET /api/dc-logs`, `/api/dc-logs/stats`, `POST /api/dc-logs/clear`
- `GET /artifact/{name:path}` — downloads from `/kaggle/working/`
- `/static/*` — chat package static (so `_chrome.css` and `_nav.js` work)

---

## 9. The 4 bespoke dashboards (just shipped)

### 9.1 A-11 lift dashboard (`kaggle/A-11-grading-evaluation/kernel.py`)

Hero KPIs (mean lift pp, win/loss/tie tally, score before→after,
grounding lift) + per-prompt scorecard with side-by-side score bars +
provenance footer. Exports: JSON, MD, CSV. Routes: `/api/lift`,
`/export/lift.csv`.

### 9.2 A-08 inline Plotly viewer (`kaggle/A-08-research-graphs/kernel.py`)

All 6 charts (entity graph, corridor Sankey, benchmark bars,
fee-camouflage heatmap, ILO indicator hits, RAG sunburst) embedded as
iframes with per-chart Open ↗ / Download. Routes: `/api/charts`.

### 9.3 A-07 training pipeline (`kaggle/A-07-bench-and-tune/kernel.py`)

9-phase pipeline visualization (Load → bench-stock → SFT-dataset → SFT
→ DPO-dataset → DPO → bench-FT → GGUF → HF-push) with per-phase ✓/×/—
status, rubric-lift KPI cards, per-phase JSON detail collapses.
Routes: `/api/eval-results`, `/export/phases.csv`.

### 9.4 A-06 corpus browser (`kaggle/A-06-prompt-generation/kernel.py`)

Filterable table (category / locale / search) over freshly generated
prompts. Expandable rows for full text + graded response. Per-row "Open
in chat" deep-link. Routes: `/api/prompts`, `/export/prompts.csv`.

**These four dashboards are the reference pattern for any future
notebook-only visualization.** Their HTML is inline in each kernel.py
and links `/static/_chrome.css` + `/static/_nav.js`.

---

## 10. The 5 audience showcase pages

Live at `packages/duecare-llm-chat/src/duecare/chat/static/showcase-*.html`.

Each page follows the same skeleton:
1. **Crumbs:** `Showcase · For <audience> teams`
2. **H1:** action-oriented sentence (~10 words)
3. **Lede:** 3-sentence problem-and-solution paragraph
4. **CTA row:** `Open the playground →` + secondary
5. **Curated prompts:** 3 audience-specific sample buttons that deep-link
   to `/?prompt=<URL-encoded>&audience=<lane>`
6. **Tools row:** 4 tool cards from `all-tools.html` curated to this lane

Click flow: showcase page → click curated prompt → chat homepage
pre-fills the input via `URLSearchParams` consumer in `index.html` line
1779. The chat homepage strips the params from the URL after consumption
so a refresh doesn't re-pre-fill.

Existing curated-prompt examples (each grounded in real corridors):
- Platform: Saudi domestic-worker recruitment ad with debt-bondage
  warning signs; UAE recruiter DM with passport-retention pattern; PH
  forum post about likely-unlicensed agency with refundable-deposit scam.
- NGO: PH→HK passport-retention case; PH→UAE pre-departure fee scam;
  NP→KSA kafala wage-theft + complaint draft.
- Worker: PH→HK placement-fee legality check; PH→KSA passport-retention
  rights; recruiter-linked salary-advance loan debt-bondage signs.
- Researcher: multi-jurisdiction legal comparison; DAN-style jailbreak;
  5-indicator compound case (the headline-lift demo).
- Developer: full API tour with 8 endpoints + curl examples.

---

## 11. The 13 notebooks (current architecture pattern + state)

| # | Folder | Pattern | Dashboard | Audience |
|---|---|---|---|---|
| 01 | `01-duecare-exploration-workbench` | chat-shell (`from duecare.chat import create_app`) | the full workbench | all |
| 02 | `02-live-demo` | server-shell (`from duecare.server import create_app`) | server hub homepage | all |
| A-01 | `A-01-chat-playground` | chat-shell | workbench homepage | researcher |
| A-02 | `A-02-chat-playground-with-grep-rag-tools` | chat-shell | workbench homepage | researcher |
| A-03 | `A-03-content-classification-playground` | custom-FastAPI (uses `/wb-static/`) | custom classifier page | platform |
| A-04 | `A-04-content-knowledge-builder-playground` | custom-FastAPI (uses `/wb-static/`) | custom KB-builder page | developer |
| A-05 | `A-05-gemma-content-classification-evaluation` | classifier (`from duecare.chat import create_classifier_app`) | NGO dashboard | ngo |
| A-06 | `A-06-prompt-generation` | notebook-only (`build_minimal_shell` + `homepage_html`) | corpus browser | researcher |
| A-07 | `A-07-bench-and-tune` | notebook-only | training pipeline | researcher |
| A-08 | `A-08-research-graphs` | notebook-only | inline Plotly viewer | researcher |
| A-09 | `A-09-chat-playground-with-agentic-research` | custom-FastAPI (uses `/wb-static/`) | custom agentic-chat page | researcher |
| A-10 | `A-10-chat-playground-jailbroken-models` | chat-shell | workbench homepage | researcher |
| A-11 | `A-11-grading-evaluation` | notebook-only | lift dashboard | researcher |

**Each `kernel-metadata.json` IDs match the folder name** (e.g.
`taylorsamarel/duecare-exploration-workbench`).

---

## 12. UI/UX rubric (the 13 principles — apply consistently)

Source-of-truth: `docs/workbench_audit.md`.

1. **One page, one job.** Primary action describable in one sentence.
2. **Progressive disclosure.** ≤ 3 prominent CTAs above the fold;
   advanced knobs hidden behind expanders.
3. **Transparency is a clickable ribbon, not a wall.** Every assistant
   response shows a one-line trace strip
   (`PERSONA · GREP(7) · RAG(top-5) · TOOLS(2) · 1.4s`) that expands.
4. **Citations are clickable evidence.** Every "ILO C181" / "POEA
   Circular 015" must link to the actual source text in the RAG corpus.
5. **Audience-first nav.** 5-lane top nav reflects the canonical
   audiences; capability tabs live as `Tools →` index.
6. **Logs are first-class.** Audit/governance/pipeline traces reachable
   in 1 click from the top nav, not buried.
7. **Showcase every functionality on its own stage.** Every API
   capability gets a UI page even if small. Audience pages compose those
   primitives.
8. **Modals fit the viewport.** `min(92vh, 100dvh - 48px)`. Body scrolls,
   chrome stays pinned. Absolutely no overflow-hidden traps.
9. **Mobile is not an afterthought.** ≥ 44px touch targets;
   single-column at < 600px; no horizontal scroll.
10. **Match duecare-ai.com visual language.** Same tokens, same fonts,
    same single-row nav restraint.
11. **Every claim is verifiable from the workbench.** README counts
    cross-link to the live API and the live page.
12. **Don't break what works.** Extractions preserve identical behavior;
    only the page composition changes.
13. **Single-row top nav, 4–7 items max.** Brand left, utility right.
    No two-row nav, no permanent sub-tabs, no top-level dropdowns with
    multi-level nesting.

---

## 13. Hard rules (non-negotiable)

These are derived from `.claude/rules/*.md` plus durable user feedback.

### Privacy / PII
- **No raw PII anywhere a judge can see.** No real names, real phone
  numbers, real passport IDs, real emails, real bank accounts. Composite
  characters (Maria, Ramesh, Sita) must be explicitly labeled composite.
  Real NGO names (Polaris, IJM, POEA, BP2MI) are public organizations
  and load-bearing for the impact story — they stay.

### Truncation / placeholder content
- **Never truncate displayed text** — no `text[:N]...`, no `..."`
  ellipsis on responses, no `response_preview` fields. Show the full
  content. Pandas: call `pd.set_option('display.max_colwidth', None)`
  before `display()`.
- **No "Coming soon" pages, no Lorem Ipsum, no TODO/FIXME/TBD in
  user-facing surfaces.** Every page must do something real.

### Voice / copy
- **Never use "ship" or "shipping" for software releases.** Use literal
  verbs: publish, release, deploy, push, merge, finish.
- **Don't headline "Privacy is non-negotiable."** Privacy is one
  supporting boundary, not a slogan. The story is helping migrant
  workers across the 5 lanes.
- **Concrete sentences, not slogans.** Replace abstract claims with the
  actual mechanism. Example: "Sensitive PII is anonymized via Gemma 4
  before submission, then re-stripped on the server" not "your data is
  safe with us."
- **BEST tier is mixed-case bold, not ALL-CAPS.** `**Legal Violations:**`
  not `LEGAL VIOLATIONS:`.

### Kaggle viewer compatibility (notebook outputs only)
- **No `display: flex` / `flex-wrap`** — gets stripped. Use
  `pandas.Styler` tables instead.
- **No `max-height: ...; overflow: auto`** — overflow gets stripped,
  produces unscrollable giant blocks. Render full-height.
- **No `<script>` tags in notebook outputs** — stripped. Use Plotly's
  safe JS injection path for interactivity.
- **No `position: fixed|absolute|sticky`** — stripped.
- **No external stylesheets in notebook outputs** — use inline `style=`
  only.

### Web UI (served pages, not notebooks)
- The above Kaggle viewer constraints **do not apply** to served pages
  reached via cloudflared. Use `<script>`, `position: sticky`, modern
  CSS freely there.

### Code style (Python)
- **Python 3.11+**, type hints on function signatures, Pydantic v2 for
  data models, `pathlib.Path` for paths, structured logging via
  `structlog` / `dc_log` (never `print()` in library code, except
  console-orchestration scripts like `kernel.py`).
- **`from __future__ import annotations`** at the top of every
  package-level module.

### Build / wheel hygiene
- Every chat-package change bumps `pyproject.toml` version
  (`0.16.0` → `0.16.1` etc.).
- After `pip wheel`, propagate the new `.whl` to all 13
  `kaggle/*/wheels/` folders. Remove the older version.

---

## 14. Validation gates (run before claiming "done")

```bash
# Public-surface audit (must show 4/4 OK, 0 findings)
.venv/Scripts/python.exe scripts/validate_public_surface.py

# Notebook structural validator (9 legacy notebooks must parse)
.venv/Scripts/python.exe scripts/validate_notebooks.py

# Package test suite (must exit 0 — meta-pkg CLI test fails without
# editable installs, that's expected)
.venv/Scripts/python.exe -m pytest packages/ \
    --ignore=packages/duecare-llm/tests \
    --ignore=packages/duecare-llm-agents/src/duecare/agents/anonymizer/tests \
    -q

# AST-parse every kernel.py you touched
python -c "import ast; [ast.parse(open(p).read()) for p in [...]]"
```

The audit script checks four invariants:
1. `drift_terms` — no banned terms / stale slugs / legacy palette
2. `hub_routes_200` — 41 declared routes resolve (9 nav + 19 footer)
3. `five_lane_order` — the 5 canonical audiences appear in correct order
4. `kaggle_lane_labels` — all 13 numbered Kaggle folders use canonical
   audience labels

---

## 15. Kaggle publish + notebook source-of-truth conventions

- **Source of truth is `kernel.py`**, not the `.ipynb` mirror.
- **`.ipynb` files are preview artifacts** generated by builder scripts
  under `scripts/build_notebook_*.py`. Regenerate only when the source
  changed and the preview must stay in sync. Do not create net-new
  notebooks for the submission without explicit user approval.
- **Kaggle publishing is manual.** Default agent behavior: edit source +
  validate locally + prepare paste-ready text + leave the final Kaggle
  UI step (copy/paste, Save & Run, publish) to the user.
- **Don't claim a slug is "live"** without verification. The local
  `kernel-metadata.json` declares the slug we *want*; the actual live
  URL may use an older slug.

---

## 16. What you're being asked to do

Read all 13 kernels (`kaggle/*/kernel.py`), all 13 READMEs
(`kaggle/*/README.md`), the workbench static (`packages/duecare-llm-chat/
src/duecare/chat/static/*.html`), the server static
(`packages/duecare-llm-server/src/duecare/server/static/*.html`), and
the public website templates (`apps/duecare-ai.com/app/templates/*.html`),
then propose concrete iterative improvements.

### Output structure

Return four layers of output.

#### Layer A — Per-notebook polish edits (13 sections)

For each of the 13 notebooks, output:

1. **Audience match.** Which lane primarily? Is that clear in the README's
   first 200 words and the kernel's homepage above-the-fold?
2. **Primary action.** Single imperative sentence ("Score a recruitment
   post and see why each rule fired" / "Compare stock Gemma against the
   harness on 5-indicator compound prompts"). Propose if missing.
3. **Top 5 concrete edits.** For each edit, output the file path, line
   range, and either the exact replacement code/HTML or a precise
   description. Examples of acceptable edits:
   - Replace a hardcoded color `#f59e0b` at `kernel.py:813` with
     `var(--warn)`.
   - Add a `data-nav="tools"` attribute to the `<body>` tag of
     `kaggle/A-XX-foo/kernel.py:625`.
   - Tighten a 4-line README headline to a single sentence.
4. **Demo-recording readiness.** Score 1-5 (where 5 = no friction during
   the 3-min recording). If <5, list the specific friction.

#### Layer B — Cross-notebook consistency edits

Output specific changes that align the 13 notebooks as a series:

1. **README skeleton.** Propose a uniform 6-section skeleton (Lede,
   What it does, Demo path, Audience, Outputs, Cross-links) that every
   README follows. If any of the 13 don't conform, list the gap.
2. **Cross-link block.** Every README should end with a 4-link cross-link
   block: (a) workbench, (b) live-demo, (c) sibling appendix that's the
   natural next step, (d) public website. Propose the exact wording.
3. **Visual identity per appendix.** Should each appendix have a small
   distinguishing visual element (a colored top-strip, a numbered tag),
   or should they all look identical? Justify and prescribe.
4. **Status strip consistency.** Every served-UI kernel should report
   the same shape from `/api/version` + `/api/model-info`. Audit the
   13 kernels and list any inconsistencies.
5. **Naming consistency.** The 11 appendix slugs (A-01 ... A-11) — are
   they well-ordered for the 5-minute judge journey? If a different
   ordering would tell a better story, propose it.

#### Layer C — Demo-recording strategy

Output a click-by-click script for the 3-minute screen recording:

1. **The 3-minute click path.** Open at <URL>; pause on <visible
   element>; click <CTA>; show <feature>; cut to <next>. ~12-18 actions
   total, with time budget per action.
2. **Hero moments.** Which 3-4 specific UI states / dashboards make
   the strongest visual claims? Mark them.
3. **B-roll candidates.** What 5-6 supporting shots could the recorder
   capture between hero moments (e.g., the 161-rule GREP browser
   scrolling, the citation graph rotating, a Plotly chart drilling in)?
4. **Pre-record checklist.** What 8-12 verifications must Taylor run
   before hitting Record? (e.g., "Kaggle session is warm", "model is
   loaded — check the green dot in the status strip", "Audience pages
   all load < 1s").

#### Layer D — Risk register (what could embarrass us)

List the top 8 design / engineering risks that could hurt the judging
score on Impact / Video / Tech-Depth axes. For each:

- The risk (one sentence)
- How it appears in the video (concrete)
- The probability it gets caught by a judge
- The cost to fix (estimate in hours)
- Recommended mitigation

---

## 17. Format we want back

For Layer A, use this exact shape:

```markdown
## 01 exploration-workbench
- Audience match: <which lane(s)> — <evidence in code>
- Primary action: "<single sentence>"
- Demo-readiness: 4/5 (friction: <list>)
- Top 5 edits:
  1. `<file>:<line-range>` — <description or replacement>
  2. ...
  3. ...
  4. ...
  5. ...

## 02 live-demo
[same shape]

## A-01 chat-playground
[same shape]

[... through A-11 ...]
```

For Layer B/C/D, use prose + bullets + code blocks freely.

**Don't restate this brief back at us.** Jump directly to the review.
Be specific and bullet-dense. Every claim that requires verification
should cite the file path and approximate line number.

---

## 18. Out of scope (do not propose)

- Changing the 5 canonical audiences. They are partner-vetted.
- Replacing Gemma 4 with another model (hackathon rule).
- Redesigning the public website. It's the source of truth.
- Replacing the wheel-based distribution mechanism.
- Multi-row nav, sticky sub-tabs, multi-level dropdown menus.
- Adding new top-level audiences ("activist", "media", etc.).
- Renaming the `duecare-` slug prefix.
- Adding cloud-hosted dependencies (no LLM API as a hard requirement —
  must work fully offline on the Kaggle GPU).
- Building the actual video. Taylor will record after polish completes.
- Touching `_archive/` — frozen historical material.

---

## 19. Reference URLs / file paths to inspect

| What | Where |
|---|---|
| Public website | https://duecare-ai.com (deployed) / `apps/duecare-ai.com/` (source) |
| Public-site CSS (token source) | `apps/duecare-ai.com/app/static/styles.css` |
| Public-site nav | `apps/duecare-ai.com/app/templates/_nav.html` |
| Workbench audit + 13 principles | `docs/workbench_audit.md` |
| Canonical audiences + components | `docs/canonical_use_cases_and_components.md` |
| Canonical messaging | `configs/duecare/canonical_messaging.yaml` |
| Chat-package design tokens | `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css` |
| Chat-package nav partial | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html` |
| Chat-package nav loader | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js` |
| Chat-package showcase CSS | `packages/duecare-llm-chat/src/duecare/chat/static/showcase.css` |
| Server-package design tokens | `packages/duecare-llm-server/src/duecare/server/static/style.css` |
| Server-package `/wb-static/` mount | `packages/duecare-llm-server/src/duecare/server/app.py` |
| 5 audience showcase pages | `packages/duecare-llm-chat/src/duecare/chat/static/showcase-*.html` |
| Tools index | `packages/duecare-llm-chat/src/duecare/chat/static/all-tools.html` |
| Minimal-shell helper | `packages/duecare-llm-chat/src/duecare/chat/kernel_shell.py` |
| dc_log primitive | `packages/duecare-llm-chat/src/duecare/chat/_dc_log.py` |
| 13 notebook folders | `kaggle/01-...`, `kaggle/02-...`, `kaggle/A-01-...` through `kaggle/A-11-...` |
| 4 bespoke dashboards | `kaggle/A-06/07/08/11/kernel.py` (search `_build_*_dashboard_html`) |
| Audit script | `scripts/validate_public_surface.py` |
| Judge-facing entry | `docs/FOR_KAGGLE_JUDGES.md` |
| Writeup draft (1500-word cap) | `docs/writeup_draft.md` (currently ~1218 words) |
| Video script | `docs/video_script.md` |
| GitHub | https://github.com/TaylorAmarelTech/gemma4_comp |
| Latest commit | `3e3ff9e` (4 dashboards + chat 0.16.0) |

---

## 20. Why this matters for the score

The hackathon rubric weights **Impact & Vision (40)** + **Video Pitch
& Storytelling (30)** + **Technical Depth & Execution (30)**. Notebook
UX maps to all three:

- A judge who lands on the workbench and immediately understands "I'm
  an NGO, here's the demo for me" scores higher Impact (the vision
  feels concretely useful, not abstract).
- A judge who can flip between Platform / NGO / Worker / Researcher /
  Developer and see five distinct, polished demos in 3 minutes scores
  higher Video Pitch (the story is multi-stakeholder).
- A judge who can click "Pipeline trace" and see real per-layer
  latency + fired GREP rules + retrieved docs scores higher Tech Depth
  (the harness is *visible*, not asserted).

Your iteration job: surface every remaining friction point that
prevents any of those three judge-experiences from feeling polished,
and output the actual edits to fix them, ranked by expected score
impact.
