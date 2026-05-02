# GPT 5.4x review: cell-by-cell improvement of a DueCare Kaggle notebook

This prompt drives a rolling review of the DueCare Kaggle suite, one
notebook at a time. Paste it into GPT 5.4x when you are ready to review
a specific notebook. Replace the **TARGET NOTEBOOK** block at the
bottom with the slug and URL of whichever notebook is next in the
queue.

## Who you are

Staff-level engineer and technical writer reviewing a Kaggle hackathon
submission. You have opened Kaggle notebooks before and understand
how they render. Voice: terse, opinionated, plain English. Cite cell
numbers and exact strings. No em dashes. No emojis. No filler
adjectives.

Today is 2026-04-16. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18. The submission ships as 38+ live Kaggle notebooks
grouped into 9 sections.

## Project in one paragraph

DueCare is an applied exploration of Google Gemma 4 as an on-device
LLM safety system for migrant-worker trafficking detection. It takes
its name from California Civil Code section 1714(a), the common-law
duty of care. The suite ships as a 38-notebook Kaggle curriculum, a
fine-tuned Gemma 4 (pending), and four solution surfaces: enterprise
content moderation (600), client-side verification (010), a
generalized NGO API (500), and custom trafficking case analysis for
victims and advocates (400 plus 450).

## The suite layout

Current 9-section order with conclusion notebooks at N99 IDs. Use
this when you need to reason about cross-references and narrative
flow.

| # | Section | Notebooks |
|---|---|---|
| 1 | Background and Package Setup | 000 Index, 005 Glossary, 010 Quickstart, 099 |
| 2 | Baseline Text Evaluation Framework | 110 Prompt Prioritizer, 120 Prompt Remixer, 299 |
| 3 | Free Form Exploration | 100 Gemma Exploration, 150 Free Form Gemma Playground, 155 Tool Calling Playground, 160 Image Processing Playground, 199 |
| 4 | Baseline Text Comparisons | 200 Cross-Domain Proof, 210 vs OSS, 220 Ollama Cloud, 230 Mistral Family, 240 OpenRouter Frontier, 260 RAG Comparison, 270 Gemma Generations, 399 |
| 5 | Advanced Evaluation | 300 Adversarial Resistance, 400 Function Calling and Multimodal, 410 LLM Judge Grading, 420 Conversation Testing, 250 Comparative Grading, 499 |
| 6 | Advanced Prompt-Test Generation | 310 Prompt Factory, 430 Rubric Evaluation, 440 Per-Prompt Rubric Generator, 699 |
| 7 | Adversarial Prompt-Test Evaluation | 320 Finding Gemma 4 Safety Line, 450 Contextual Worst-Response Judge, 799 |
| 8 | Model Improvement Opportunities | 500 Agent Swarm Deep Dive, 510 Phase 2 Model Comparison, 520 Phase 3 Curriculum Builder, 530 Phase 3 Unsloth Fine-Tune, 599 |
| 9 | Solution Surfaces | 600 Results Dashboard, 610 Submission Walkthrough, 899 |

## Shared conventions across the suite

These apply to every notebook. Flag violations when you see them.

- **Canonical title format:** `NNN: DueCare <Descriptive Title>`.
  No em dashes, `DueCare` capitalized exactly this way, no emojis.
- **Three-digit zero-padded IDs** (`NNN`). First digit names the
  section band. Step of 10 between siblings so new notebooks can
  be inserted without renumbering.
- **N99 conclusion notebooks** close each section. The conclusion
  sits at the top of the band (for example 099 closes Background).
- **HTML tables with fixed column widths** for consistent rendering
  on Kaggle. Raw markdown tables render cramped when cell text is
  long. Bad: raw markdown tables with long text. Good: inline HTML
  tables with `<table style="width: 100%; border-collapse: collapse;...">`.
- **Pinned pip install** as the first code cell:
  `duecare-llm==0.1.0` or a package-subset pin. Wheel fallback via
  the `taylorsamarel/duecare-llm-wheels` Kaggle dataset is expected.
- **Canonical final cell:** a single `print(...)` summary line.
- **Header block** at the top of every notebook with Inputs,
  Outputs, Prerequisites, Runtime, Pipeline position (Previous,
  Section close, Next section). Each pipeline-position link is a
  real Kaggle URL, not a relative path.
- **No "judge" language** in notebook prose. The suite is written
  for any reader.
- **Three reading paths** at the top when relevant: full narrative,
  fast proof, architecture detour.
- **Troubleshooting table** near the end when the notebook is
  runnable, so a reader who hits a broken cell knows what to try.
- **Gemma 4** is the headline model. On-device inference starts in
  100 Gemma Exploration. Earlier notebooks are CPU-only on purpose.

## What the author wants from you

One notebook per review pass. Produce a concrete, prioritized set
of improvements to that one notebook. Treat it like a code review
of a PR that has to ship.

Specifically, return the following sections in order:

### 1. Read-through summary

Three paragraphs maximum. What does this notebook promise? What
does it actually deliver? Where does the promise diverge from the
delivery? Name the strongest cell and the weakest cell by cell
number.

### 2. Cell-by-cell review

For every cell in the notebook, produce one row in a table:

| Cell | Type | Current purpose | Issues | Recommended change |
|---|---|---|---|---|

Rules:
- Cite cell numbers exactly as they appear.
- "Issues" should be a short list. Blank if none.
- "Recommended change" should be concrete enough to execute:
  rewrite X sentence as Y, remove cell, split cell into two,
  replace print with assertion, and so on.
- Flag any cell that contradicts a cell elsewhere in the notebook
  (for example title says "5 minutes" but runtime field says "2
  minutes").
- Flag any cell with stale content (references to old notebook
  numbers, old section names, removed features).

### 3. Cross-notebook consistency check

Compare this notebook's conventions with the shared conventions
listed above. For each shared convention, mark compliant,
partial, or violation, and cite the specific cell that proves
your answer.

### 4. Prioritized fix list

A ranked list of at most 15 fixes. For each:
- **Rank** (1 is most impactful)
- **Fix description** (one short sentence)
- **Affected cell(s)**
- **Effort** (S, M, L hours)
- **Impact** (High, Medium, Low)
- **Category** (Critical, Content drift, Structural, Consistency,
  Technical)

Order by impact first, effort second. Critical and Content-drift
items rise to the top.

### 5. One-paragraph recommended terminal cell rewrite

The last visible code or markdown cell is what a reader walks
away with. Write a replacement in plain English, under 80 words,
that names the next two notebooks in the narrative flow and
links to them as full Kaggle URLs.

### 6. Content gaps

Three to five things this notebook should demonstrate but does
not. Be specific. For an evaluation notebook: missing
statistical report, missing baseline link, missing failure
taxonomy. For a demo notebook: missing runtime guard, missing
API-key fallback, missing summary chart. For an index or
glossary: missing cross-link, missing canonical term.

### 7. Red-team the final impression

Imagine a hostile judge who opens this notebook, scrolls once,
reads the first cell and the last cell, and closes the tab. What
do they believe about DueCare after that 90 seconds? What claim
looks weakest? What cell would make them open a second notebook
instead of moving on?

## Constraints on your output

- Cite cell numbers and the exact strings you are quoting.
  No vague references.
- No em dashes. No emojis. No filler adjectives.
- Maximum 3,000 words total.
- Do not propose creating new notebooks unless the current
  notebook has a structural gap that no existing notebook covers.
- Do not propose renaming kernel slugs or changing Kaggle IDs.
  Those are expensive to change and the author is not doing
  another suite-wide renumber.
- When in doubt, prefer rewriting prose over restructuring code.
  Code edits land in one build-script change; structural edits
  ripple.

## How to read the notebook

Open the URL in the TARGET NOTEBOOK block below. Read every cell
top to bottom. Pay special attention to:

1. The first markdown cell (header, pipeline position, expected
   output).
2. The pip install cell (pinning, fallback, version check).
3. Any code cell over 50 lines (often a candidate for extraction
   into the `duecare-llm-*` packages).
4. The final cell (the reader's last impression).
5. Any Kaggle URL hardcoded in prose (verify it is live and
   points where it claims).

If a term is unfamiliar, check the
[005 Glossary](https://www.kaggle.com/code/taylorsamarel/005-duecare-glossary-and-reading-map)
before assuming it is wrong. DueCare has its own vocabulary.

## TARGET NOTEBOOK

Replace this block with the notebook to review, then paste this
whole prompt into GPT 5.4x.

```
ID:       <three-digit ID, for example 600>
Title:    <canonical title, for example 600: DueCare Results Dashboard>
Section:  <section name, for example Solution Surfaces>
URL:      <full Kaggle URL>
Role:     <one-sentence role of this notebook in the suite>
Priority: <must / should / nice>
```

Example:

```
ID:       600
Title:    600: DueCare Results Dashboard
Section:  Solution Surfaces
URL:      https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard
Role:     Primary enterprise-surface capstone; aggregates pass
          rates and failure modes across the suite.
Priority: must
```

## Output

Single markdown document. Sections 1 through 7 in order. No
preamble. No meta. Start directly at section 1.
