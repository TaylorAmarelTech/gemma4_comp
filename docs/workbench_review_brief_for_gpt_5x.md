# DueCare Workbench — Design review brief for GPT 5.5x

> **Self-contained brief.** Paste this whole document into GPT 5.5x. No
> external file fetches required. Goal: an expert UI/UX + product review
> of the 2 main + 11 appendix Kaggle notebooks against the design system
> and primitives the project just adopted.

---

## 1. Mission

You are reviewing the Kaggle-notebook surface of **DueCare** — a Gemma 4
Good Hackathon submission (deadline 2026-05-18, $200K prize pool across
Main / Impact / Special Technology tracks). DueCare is an LLM safety
harness for migrant-worker protection: it wraps Gemma 4 with a persona,
GREP rules (161 deterministic regexes), a RAG corpus (46 docs across 27
jurisdictions), 5 function-calling tools, and an optional online-search
layer, so the model produces grounded, citable, audience-appropriate
responses about labor recruitment, fee scams, passport retention,
debt bondage, and corridor-specific legal protections.

The submission has **13 Kaggle notebooks**: 2 "main" (a workbench and a
live-demo) and 11 "appendix" (specialized playgrounds and research
artifacts). All 13 are visible to judges. They currently do not share a
common visual language or navigation pattern, and the design quality
varies significantly. The team just rebuilt the #1 notebook into a
formal **Exploration Workbench** with a shared design system; the
question for you is **how to apply that system consistently across the
other 12 notebooks** without losing each notebook's individual purpose.

---

## 2. Audiences (canonical, do not invent new ones)

These five lanes are defined in `configs/duecare/canonical_messaging.yaml`
and `docs/canonical_use_cases_and_components.md`. Every notebook should
identify which of the five it primarily serves:

| Lane | Plain-language name | Primary need |
|---|---|---|
| 1 | **Platform safety** | Trust & safety teams scoring recruitment posts/messages, routing high-risk items to reviewers, sharing anonymized abuse patterns. |
| 2 | **NGO & regulator** | Caseworkers, legal-aid groups, consulates, labor inspectors triaging messages and documents, finding contacts, drafting complaint materials. |
| 3 | **Individual worker / mobile** | Migrant workers privately checking suspicious offers, contracts, recruiter messages, fee demands; getting localized warning signs and trusted next-step contacts. |
| 4 | **Researcher** | Academic and public-interest researchers reproducing prompts, comparing model variants, scoring responses, auditing claims from source artifacts. |
| 5 | **Developer / integration partner** | Devs embedding the harness into moderation tools, NGO systems, mobile clients via APIs and pinned wheels. |

Use these names exactly. Do **not** use "social platforms" / "enterprise"
/ "worker-side" / "researchers" (plural) / "NGO dashboard" / "custom
integration" as top-level lane labels — they are explicitly banned in
the canonical doc.

---

## 3. Public-website design system (the visual source of truth)

The public website lives at https://gemma4-comp.onrender.com/ and ships
under `apps/duecare-ai.com/app/static/styles.css`. It is the source of
truth for every other surface in the project. The notebook workbench
just adopted the same tokens; appendix notebooks should align too.

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
--good: oklch(0.55 0.10 155);
--warn: oklch(0.65 0.10 80);

/* Typography */
--sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
```

---

## 4. The new Workbench shell (just shipped, commit c221174)

The #1 notebook now serves the chat-package's static viewer pages with a
**single-row top nav matching the duecare-ai.com pattern** plus a thin
**status strip** above it for system info.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ● Model: gemma-4-e4b-it · v0.14.7 · 1.2GB GPU      [⏻ Shutdown]      │  ← status strip
├──────────────────────────────────────────────────────────────────────┤
│ DueCare Workbench  Platform · NGO · Worker · Researcher · Developer  │  ← single-row nav
│                                                          [Tools →]   │
├──────────────────────────────────────────────────────────────────────┤
│  [page content]                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Three reusable primitives appendix notebooks should adopt:

1. **`packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`** —
   token system + status-strip + nav-row + buttons + cards + pills + tables.
   Importing this file gives a notebook the entire visual system.
2. **`packages/duecare-llm-chat/src/duecare/chat/static/_nav.html`** +
   **`_nav.js`** — drop-in shared shell. Each page tags itself with
   `<body data-nav="<key>">` and includes
   `<script src="/static/_nav.js" defer></script>`. The script
   auto-fetches the partial, marks the active nav link, polls
   `/api/version` + `/api/model-info` for the status strip, and wires the
   Shutdown button.
3. **`packages/duecare-llm-chat/src/duecare/chat/static/showcase.css`** —
   shared styles for audience-landing pages: lede typography, demo-prompt
   buttons, tool-card grids, CTAs.

Audience pages live at `static/showcase-{platform,ngo,worker,researcher,
developer}.html`. Each is: 1-line lede → 3 curated sample prompts that
link to the chat with `?prompt=…&audience=…` pre-filled → a "Tools for
this lane" card row → a link to `all-tools.html`.

The Tools index at `static/all-tools.html` lists every workbench page
grouped by Chat/Classification, Layer transparency, Worker/NGO utilities,
System & observability.

---

## 5. UI/UX rubric (12 + 1 principles to apply consistently)

Every notebook surface gets graded against these. Source-of-truth in
`docs/workbench_audit.md`.

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
   chrome stays pinned.
9. **Mobile is not an afterthought.** ≥ 44px touch targets;
   single-column at < 600px; no horizontal scroll.
10. **Match duecare-ai.com visual language.** Same tokens, same fonts,
    same single-row nav restraint.
11. **Every claim is verifiable from the workbench.** README counts
    cross-link to the live API and the live page.
12. **Don't break what works.** Extractions preserve identical behavior;
    only the page composition changes.
13. **Match duecare-ai.com nav pattern.** Single-row top nav, 4–7 items
    max, brand left + utility right. No two-row nav, no permanent
    sub-tabs, no top-level dropdowns with multi-level nesting.

---

## 6. The 13 notebooks to review

All live under `kaggle/`. Each has a `kernel.py` (the script kernel
source) and a `README.md` (judge-facing walkthrough).

### Main notebooks (2)

1. **`01-duecare-exploration-workbench/`** — formerly "duecare-harness-chat".
   The full-featured workbench. Free-form chat with all 6 harness layers,
   model picker (9 variants), 4 grading modes, pipeline trace, 12+ static
   viewer pages now under a unified nav. **The reference implementation
   for the design system.** [kernel.py: ~1900 lines]
2. **`02-live-demo/`** — focused, scripted walkthrough that proves the
   "+56.5pp lift" thesis (baseline Gemma vs full harness on a curated set
   of 5-indicator compound prompts). Uses the same chat-package wheel as
   #01 but is meant to run a tighter, more linear narrative.

### Appendix notebooks (11)

Each is a specialized playground or research artifact:

- **A-01 chat-playground** — stock Gemma 4 baseline chat (no harness).
  Provides the "before" comparison for the lift story.
- **A-02 chat-playground-with-grep-rag-tools** — original 4-toggle subset
  playground. The early-version chat that #01 evolved beyond.
- **A-03 content-classification-playground** — hands-on classification
  sandbox; multimodal input, harness toggles, result history.
- **A-04 content-knowledge-builder-playground** — knowledge-builder
  sandbox + JSON export pipeline.
- **A-05 gemma-content-classification-evaluation** — NGO classifier
  evaluation dashboard; aggregate scoring across a benchmark set.
- **A-06 prompt-generation** — Gemma generates evaluation prompts (the
  benchmark-bootstrapper).
- **A-07 bench-and-tune** — Unsloth fine-tune + GGUF export pipeline.
- **A-08 research-graphs** — CPU-only research graphs (citation graph,
  retrieval-trace visualizations).
- **A-09 chat-playground-with-agentic-research** — BYOK + Playwright
  multi-step web research agent.
- **A-10 chat-playground-jailbroken-models** — jailbroken-Gemma comparison
  (abliterated 31B and E4B variants); proves harness wins even against an
  unaligned base.
- **A-11 grading-evaluation** — grading-lift regenerator; 4-mode grader
  benchmark.

---

## 7. What we want from you

Produce a structured review covering three layers:

### Layer A — Per-notebook design review (13 sections)

For each notebook, answer:

1. **Audience match.** Which of the 5 canonical lanes is this notebook's
   primary audience? Does the README and kernel make that obvious in the
   first 30 seconds?
2. **Primary action.** Is there a single imperative sentence that
   describes what a judge or partner does on this notebook? If not,
   propose one.
3. **Adopting the workbench shell.** Should this notebook serve its own
   static pages with the new shared `_chrome.css` + `_nav.html` shell,
   or is it better off staying as a notebook-only surface (no served
   web app)? If yes, what does its top-nav look like — same 5
   audience tabs, or a notebook-specific subset?
4. **Reusable primitives this notebook should pull in.** From the
   primitives list (status strip, demo-prompt cards, tool cards,
   audience pill, citation linker, pipeline trace strip, grade panel),
   which apply here?
5. **Top 3 specific UI/UX issues** you'd fix.
6. **Top 3 specific opportunities** to make this notebook punch above
   its weight in the judge's 5-minute walkthrough.

### Layer B — Cross-notebook consistency

Answer these systemically:

1. **Should every appendix notebook adopt the same workbench shell**, or
   is it OK for some to keep a more notebook-native presentation?
   Give specific criteria for "this one needs the shell" vs "this one
   doesn't."
2. **Naming consistency.** Are the 11 appendix slugs (A-01 ... A-11)
   well-named for an audience-first nav, or should they be renamed?
   Propose a naming scheme if needed.
3. **Cross-linking.** What's the right pattern for each appendix
   notebook to link back to the main workbench, and to its sibling
   appendices, without polluting the page with link-soup?
4. **README structure.** Propose a minimal README skeleton every
   notebook follows so the 13 README walkthroughs feel like a series,
   not 13 ad-hoc pages.
5. **Visual identity per appendix.** Should each appendix have a small
   distinguishing visual element (a colored top-strip, a numbered tag),
   or should they all look identical?

### Layer C — Strategic recommendations

1. **The 5-minute judge journey.** Map an ideal sequence of clicks for
   a hackathon judge with only 5 minutes. Does it start at the public
   website? At the workbench? At a specific audience page?
2. **What to cut.** Which of the 11 appendix notebooks could be
   merged, deprecated, or hidden from the main index without losing
   judge-visible value?
3. **What's missing.** Identify any audience-task that the 13
   notebooks don't cover well today and propose a 14th notebook (or a
   new section in an existing one).
4. **Risk register.** Top 3 design risks that could hurt the judging
   score under "Impact & Vision" / "Video Pitch & Storytelling" /
   "Technical Depth & Execution" rubric headings.

---

## 8. Format we want back

```
# Layer A — Per-notebook
## 01 exploration-workbench
- Audience match: <answer>
- Primary action: <answer>
- Adopt workbench shell: yes/no/partial — <reasoning>
- Primitives to pull in: <list>
- Top 3 issues: 1) … 2) … 3) …
- Top 3 opportunities: 1) … 2) … 3) …

## 02 live-demo
[same shape]

## A-01 chat-playground
[same shape]

[... A-02 through A-11 ...]

# Layer B — Cross-notebook
## Should every appendix adopt the workbench shell?
[answer]
## Naming consistency
[answer]
## Cross-linking pattern
[answer]
## README skeleton
[answer]
## Visual identity per appendix
[answer]

# Layer C — Strategic
## 5-minute judge journey
[answer with click-by-click steps]
## What to cut
[answer with explicit notebook IDs]
## What's missing
[answer]
## Risk register
1. …
2. …
3. …
```

Bullet-dense is fine. Short reasoning per claim is required. Don't
restate this brief back at us; jump straight to the review.

---

## 9. Out of scope (do not propose)

- Changing the 5 canonical audiences. They are derived from real
  partner-vetted use cases and will not be renamed for the hackathon.
- Replacing Gemma 4 with another model. Hackathon rules require Gemma 4.
- Switching the public site (`apps/duecare-ai.com`) — that's the design
  source of truth, not a thing to redesign.
- Replacing the wheel-based distribution. The chat-package wheel
  shipping mechanism is locked.
- Multi-row nav, sticky sub-tabs, top-nav dropdowns with > 1 nesting
  level. P13 is non-negotiable.
- Adding new top-level audiences ("activist", "media", etc.). Stick to
  the canonical 5.

---

## 10. Reference URLs / file paths to inspect

| What | Where |
|---|---|
| Public website | https://gemma4-comp.onrender.com/ |
| Public-site CSS (source of truth) | `apps/duecare-ai.com/app/static/styles.css` |
| Public-site nav | `apps/duecare-ai.com/app/templates/_nav.html` |
| Workbench audit + principles | `docs/workbench_audit.md` |
| Canonical audiences + components | `docs/canonical_use_cases_and_components.md` |
| Workbench shared chrome | `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css` |
| Workbench nav partial | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html` |
| Workbench nav loader | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js` |
| Showcase shared styles | `packages/duecare-llm-chat/src/duecare/chat/static/showcase.css` |
| 5 audience pages | `packages/duecare-llm-chat/src/duecare/chat/static/showcase-*.html` |
| Tools index | `packages/duecare-llm-chat/src/duecare/chat/static/all-tools.html` |
| 13 notebook folders | `kaggle/01-duecare-exploration-workbench`, `kaggle/02-live-demo`, `kaggle/A-01*` … `kaggle/A-11*` |
| Live workbench (Kaggle) | https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat (slug change to `duecare-exploration-workbench` pending next push) |
| GitHub repo | https://github.com/TaylorAmarelTech/gemma4_comp |
| Latest commit reviewers should pin | `c221174` (workbench shell + 5 audience pages + tools index + chat URL-param consumer) |

---

## 11. Why this matters for the score

The hackathon rubric weights **Impact & Vision (40)** + **Video Pitch &
Storytelling (30)** + **Technical Depth & Execution (30)**. Notebook UX
maps to all three:

- A judge who lands on the workbench and immediately understands "I'm
  an NGO, here's the demo for me" scores higher Impact (the vision
  feels concretely useful, not abstract).
- A judge who can flip between Platform / NGO / Worker / Researcher /
  Developer and see five distinct, polished demos in 5 minutes scores
  higher Video Pitch (the story is multi-stakeholder, not one-trick).
- A judge who can click "Pipeline trace" and see real per-layer
  latency + fired GREP rules + retrieved docs scores higher Tech Depth
  (the harness is *visible*, not asserted).

Your review's job: surface the friction points that prevent any of those
three judge-experiences from feeling polished, and rank the fixes by
expected score impact.
