# Claude review: cumulative notebook review through 210

This prompt asks Claude to review the full reader path up to notebook
210. The earlier notebooks are part of the review scope, not just
background context, because notebook 210 inherits their terminology,
promises, links, and narrative setup.

Notebook 210 gets the full cell by cell review. Every earlier notebook
gets a checkpoint review focused on the cells that shape what a reader
believes before they open 210.

## Who you are

Staff-level engineer and technical writer reviewing a Kaggle hackathon
submission. You have opened Kaggle notebooks before and understand how
they render. Voice: terse, opinionated, plain English. Cite notebook
IDs, cell numbers, and exact strings. Use cell numbers only, never
internal cell IDs. No em dashes. No emojis. No filler adjectives.

Today is 2026-04-16. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18. The submission ships as 38+ live Kaggle notebooks grouped
into 9 sections.

## Project in one paragraph

DueCare is an applied exploration of Google Gemma 4 as an on-device
LLM safety system for migrant-worker trafficking detection. It takes
its name from California Civil Code section 1714(a), the common-law
duty of care. The suite ships as a 38-notebook Kaggle curriculum, a
fine-tuned Gemma 4 (pending), and four solution surfaces: enterprise
content moderation (600), client-side verification (010), a
generalized NGO API (500), and custom trafficking case analysis for
victims and advocates (400 plus 450).

## Review scope

Review these notebooks in this exact reader order:

1. 000 Index
   URL: https://www.kaggle.com/code/taylorsamarel/duecare-000-index
2. 005 Glossary and Reading Map
   URL: https://www.kaggle.com/code/taylorsamarel/005-duecare-glossary-and-reading-map
3. 010 Quickstart in 5 Minutes
   URL: https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes
4. 099 Orientation and Background and Package Setup Conclusion
   URL: https://www.kaggle.com/code/taylorsamarel/099-duecare-orientation-and-background-and-package-setup-conclusion
5. 110 Prompt Prioritizer
   URL: https://www.kaggle.com/code/taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline
6. 120 Prompt Remixer
   URL: https://www.kaggle.com/code/taylorsamarel/120-duecare-prompt-remixer
7. 299 Baseline Text Evaluation Framework Conclusion
   URL: https://www.kaggle.com/code/taylorsamarel/299-duecare-baseline-text-evaluation-framework-conclusion
8. 100 Gemma 4 Exploration (Phase 1 Baseline)
   URL: https://www.kaggle.com/code/taylorsamarel/100-duecare-gemma-4-exploration-phase-1-baseline
9. 150 Free Form Gemma Playground
   URL: https://www.kaggle.com/code/taylorsamarel/150-duecare-free-form-gemma-playground
10. 155 Tool Calling Playground
    URL: https://www.kaggle.com/code/taylorsamarel/155-duecare-tool-calling-playground
11. 160 Image Processing Playground
    URL: https://www.kaggle.com/code/taylorsamarel/160-duecare-image-processing-playground
12. 199 Free Form Exploration Conclusion
    URL: https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion
13. 200 Cross-Domain Proof
    URL: https://www.kaggle.com/code/taylorsamarel/200-duecare-cross-domain-proof
14. 210 Gemma 4 vs OSS Models
    URL: https://www.kaggle.com/code/taylorsamarel/210-duecare-gemma-4-vs-oss-models

Primary target for deep review: 210.

Secondary scope: every notebook before 210, because each one shapes the
reader's expectations, vocabulary, and trust before the first major OSS
comparison notebook lands.

## Current local section map

Use this when checking whether 210 appears in the right narrative place.

| # | Section | Notebooks |
|---|---|---|
| 1 | Background and Package Setup | 000 Index, 005 Glossary, 010 Quickstart, 099 |
| 2 | Baseline Text Evaluation Framework | 110 Prompt Prioritizer, 120 Prompt Remixer, 299 |
| 3 | Free Form Exploration | 100 Gemma Exploration, 150 Free Form Gemma Playground, 155 Tool Calling Playground, 160 Image Processing Playground, 199 |
| 4 | Baseline Text Comparisons | 200 Cross-Domain Proof, 210 vs OSS, 220 Ollama Cloud, 230 Mistral Family, 240 OpenRouter Frontier, 260 RAG Comparison, 270 Gemma Generations, 399 |

## Shared conventions across the suite

These apply to every notebook. Flag violations when you see them.

- Canonical title format: `NNN: DueCare <Descriptive Title>`.
  No em dashes, `DueCare` capitalized exactly this way, no emojis.
- Three-digit zero-padded IDs (`NNN`). First digit names the section
  band. Step of 10 between siblings so new notebooks can be inserted
  without renumbering.
- N99 conclusion notebooks close each section.
- HTML tables with fixed column widths for consistent Kaggle rendering.
  Raw markdown tables render cramped when cell text is long.
- Pinned pip install as the first code cell:
  `duecare-llm==0.1.0` or a package-subset pin. Wheel fallback via the
  `taylorsamarel/duecare-llm-wheels` Kaggle dataset is expected.
- Canonical final cell: a single `print(...)` summary line.
- Header block at the top of every notebook with Inputs, Outputs,
  Prerequisites, Runtime, Pipeline position. Each pipeline-position
  link is a real Kaggle URL, not a relative path.
- No "judge" language in notebook prose.
- Three reading paths at the top when relevant: full narrative, fast
  proof, architecture detour.
- Troubleshooting table near the end when the notebook is runnable.
- Gemma 4 is the headline model. On-device inference starts in 100
  Gemma Exploration. Earlier notebooks are CPU-only on purpose.

## How to read the notebooks

### For notebooks 000 through 200

You are reviewing these earlier notebooks as real artifacts, but keep
the depth proportional. For each earlier notebook, read at minimum:

1. Cell 1.
2. The pip install or first code cell.
3. Any cell that contains the pipeline-position block, reading paths,
   runtime claims, or outbound notebook links.
4. The final visible cell.
5. Any cell you need to inspect more closely because it contradicts a
   later notebook or makes a promise that 210 depends on.

### For notebook 210

Read every cell top to bottom. Treat it like a PR that has to ship.
Check not only internal quality, but whether it lands correctly after
everything that came before it.

## What the author wants from you

Produce one cumulative review that answers two questions at once:

1. Did the notebooks before 210 prepare the reader properly?
2. Does notebook 210 deliver on the comparison story the earlier
   notebooks set up?

Return the following sections in order:

### 1. Sequence summary

Three paragraphs maximum. What story does the run from 000 through 210
promise? What does it actually deliver? Where does that run-up make 210
stronger, and where does it leave 210 carrying too much explanatory
weight?

### 2. Previous-notebook checkpoint review

Produce one row per notebook for every notebook before 210.

| Notebook | Role before 210 | Strongest cell | Weakest cell | Issues | Recommended change |
|---|---|---|---|---|---|

Rules:
- Use notebook IDs and cell numbers exactly.
- Keep this section concise.
- Focus on what each notebook contributes to the reader's readiness for
  210.
- If a prior notebook is fine, say so plainly.

### 3. 210 read-through summary

Three paragraphs maximum. What does notebook 210 promise? What does it
actually deliver? Where does the promise diverge from the delivery?
Name the strongest cell and the weakest cell by cell number.

### 4. 210 cell-by-cell review

For every cell in 210, produce one row in a table:

| Cell | Type | Current purpose | Issues | Recommended change |
|---|---|---|---|---|

Rules:
- Cite cell numbers exactly.
- "Issues" should be a short list. Blank if none.
- "Recommended change" must be concrete enough to execute.
- Flag any stale content, broken promise, contradictory runtime claim,
  or cross-reference drift.

### 5. Cross-notebook continuity check

Compare 210 against all earlier notebooks in scope. Cover at least:

- Whether 210 assumes terminology, scoring logic, or inputs that were
  actually introduced earlier.
- Whether 210 repeats earlier setup unnecessarily.
- Whether 210 contradicts earlier notebooks on runtime, provenance,
  scope, or narrative position.
- Whether the final cell of 200 makes 210 the obvious next click.
- Whether the conclusion notebooks 099, 299, and 199 actually tee up
  the later work they claim to lead into.

Use this table format:

| Topic | Earlier notebook(s) | 210 cell(s) | Assessment | Recommended fix |
|---|---|---|---|---|

### 6. Shared-convention compliance

Check the full run-up to 210 against the shared conventions above.
For each convention, mark one of: compliant, partial, violation.
Cite the notebook ID and cell number that proves your answer.

### 7. Prioritized fix list

A ranked list of at most 20 fixes across the whole run-up to 210. For
each:

- Rank
- Fix description
- Affected notebook(s) and cell(s)
- Effort (S, M, L hours)
- Impact (High, Medium, Low)
- Category (Critical, Content drift, Structural, Consistency, Technical)

Order by impact first, effort second. Critical and Content-drift items
rise to the top.

### 8. Recommended replacement for 210's final cell

Write one replacement terminal cell for notebook 210 in plain English,
under 80 words. It should name the next two notebooks in the sequence
and link to them as full Kaggle URLs.

### 9. Content gaps before 220

List three to five things the run from 000 through 210 should already
have established before the reader opens 220, but does not. Be specific.

### 10. Red-team the final impression

Imagine a hostile judge opens 000, scans the run-up, then opens 210,
reads Cell 1 and the last cell, and closes the tab. What do they
believe about DueCare after that 90 seconds? What claim looks weakest?
What earlier notebook most undermines 210? What earlier notebook most
helps it?

## Constraints on your output

- Cite notebook IDs, cell numbers, and exact quoted strings. No vague
  references.
- Use cell numbers only, not notebook-internal cell IDs.
- No em dashes. No emojis. No filler adjectives.
- Maximum 4,500 words total.
- Do not propose renaming kernel slugs or changing Kaggle IDs.
- Do not propose new notebooks unless the current sequence has a real
  structural gap that no existing notebook covers.
- Prefer rewriting prose over restructuring code.
- If an earlier notebook is fine but thin, say that it is fine and thin.

## Output

Single markdown document. Sections 1 through 10 in order. No preamble.
No meta. Start directly at section 1.