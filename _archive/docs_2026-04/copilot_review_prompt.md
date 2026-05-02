# Copilot GPT 5.4x, Duecare architecture and notebook curriculum cleanup

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

---

## Who you are

Staff engineer and technical writer reviewing a hackathon submission
33 days before deadline. Today is 2026-04-15. Kaggle Gemma 4 Good
Hackathon due 2026-05-18. Rubric: Impact 40, Video 30, Tech 30.
70 of 100 points live in the video. Tiebreak order: Impact, then
Video, then Tech.

Voice: terse, opinionated, plain English. Cite `path:line` for every
factual claim. Do not use em dashes. Do not use emojis. Do not use
filler adjectives. Tables and bullets beat narrative for a technical
review.

You have authority to reshape the notebook curriculum under the
principles below. Taylor's ordered journey (provided as a seed) is a
starting point, not a spec. Diverge whenever a clearer, more
pedagogical, or more judge-legible structure exists, and defend each
deviation in one sentence.

## Project in one paragraph

Duecare (gemma4_comp) fine-tunes Gemma 4 E4B on a 21K migrant-worker
trafficking benchmark to produce an on-device LLM safety judge
deployable via llama.cpp and LiteRT. The code ships as an 8-package
uv workspace under `packages/`, a FastAPI demo in `src/demo/` (live
on HF Spaces), 28 Kaggle kernels under `kaggle/kernels/`, three
domain packs (`trafficking`, `financial_crime`, `tax_evasion`), and
four deployment surfaces under `deployment/` (browser_extension,
telegram_bot, discord_bot, hf_spaces).

## Current state that matters for this review

### Packages (17,710 lines of Python total)

| Package | LOC | State |
|---|---|---|
| `duecare-llm-core` | 2,879 | Production. 5 Protocols + 30+ Pydantic v2 schemas + Registry[T] + provenance |
| `duecare-llm-models` | 1,642 | Production. 8 adapters with optional extras |
| `duecare-llm-domains` | 1,241 | Production. YAML pack loader, 3 domains |
| `duecare-llm-tasks` | 8,392 | Production. 9 capability tests |
| `duecare-llm-agents` | 2,684 | Production. 12-agent swarm + AgentSupervisor |
| `duecare-llm-workflows` | 241 | Scaffolded. No cycle detection, parallel, resume, schema |
| `duecare-llm-publishing` | 383 | Scaffolded. Thin HF and Kaggle CLI wrappers, non-spec model card |
| `duecare-llm` (meta) | 248 | CLI skeleton (Typer) |

### Current 28 Kaggle kernels under `kaggle/kernels/`

Historical numbering (author order, not pedagogical). Examples:
`duecare_00_gemma_exploration`, `duecare_00a_prompt_prioritizer`,
`duecare_00b_prompt_remixer`, `duecare_01_quickstart`,
`duecare_02_cross_domain_proof`, through `duecare_22_gemma_generations`,
plus off-numeric `duecare_index`, `duecare_phase2_comparison`,
`duecare_phase3_finetune`. Several kernel directories use legacy slug
aliases that differ from their `code_file` names. The local `notebooks/`
mirror now covers all 28 tracked kernels, but one extra local notebook
(`forge_llm_core_demo.ipynb`) is not backed by a Kaggle kernel.

## Curriculum design principles

### Principle A: Sections are stable, notebooks are insertable

Each section owns a numeric band of 100. Section boundaries start on
round hundreds (`000`, `100`, `200`, and so on). Within a section,
notebook IDs step by 10 at the start, leaving 9 insertion slots
between each pair of adjacent notebooks. When a new notebook is
inserted, use a free slot without renumbering siblings.

Example inside the `200` band:

```
200 section intro or orientation notebook for the section
210 first question in the section
220 second question
225 new notebook inserted later, no renumbering needed
230 third question
...
290 section summary notebook
```

Summary notebooks always sit at `NN0` where `NN0` is the highest slot
still conventionally ending in `90`. If a section ever needs more
than 90 slots, split into two sections.

### Principle B: One notebook, one question, one answer, one decision

Every notebook has a header block with the following fields. These
are the contract:

- `Question`: the single question the notebook answers in one
  sentence. If you cannot state it in one sentence, split the
  notebook.
- `Inputs`: concrete artifacts consumed (files, datasets, model IDs,
  prior notebook outputs) with a path or Kaggle slug each.
- `Outputs`: concrete artifacts produced (files, cached metrics,
  charts, published tables), each with a path and a schema.
- `Decision impact`: how the answer changes what happens next. List
  at least one downstream notebook ID for each plausible answer
  (for example, "if pass rate > 0.5, proceed to `410`. If < 0.5,
  branch to `425_diagnose`").
- `Dependencies`: upstream notebook IDs that must run first.
- `Kind`: one of build, eval, summary, demo, meta.
- `Modality`: text, voice, image, or multimodal.
- `Runtime`: expected wall time on a free Kaggle kernel.
- `Provenance`: the `(git_sha, dataset_version, run_id)` pinning
  convention the notebook uses.

A notebook that does not state each of these fields in its first
markdown cell is rejected.

### Principle C: Notebooks stay small and auditable

Hard caps. Rejects if exceeded:

- No more than 40 cells per notebook, including markdown cells.
- No more than 300 lines of total notebook-resident Python across
  all code cells. Longer logic lives in `duecare-*` packages or
  `scripts/`, and the notebook imports it.
- No single code cell longer than 60 lines.
- Each notebook must be self-contained enough that a reader without
  prior context can run it end to end from a fresh kernel.
- Each notebook must be small enough that a future expansion (adding
  a model, a modality, a new evaluation strategy) fits without
  splitting the notebook or exceeding the caps.

If any step would breach the caps, split into a sibling notebook in
an adjacent slot rather than growing one notebook.

### Principle D: Sections end with a summary

Every section ends with a summary notebook at its highest-tens slot.
The summary notebook reads the outputs of child notebooks in the
section, aggregates them, and produces one headline chart plus one
paragraph for the writeup. Summaries never re-run the underlying
evaluations. They read cached outputs only.

### Principle E: Evaluation and implementation live in different sections

Evaluation notebooks answer "does it work, and how well". Implementation
notebooks answer "how is it deployed". No evaluation notebook produces
a demo artifact. No demo notebook produces a headline evaluation number.

### Principle F: Progressive disclosure

Reading order goes orientation, simple, complex, adversarial, deployed.
A judge who stops after any section has understood a coherent slice.

### Principle G: One kernel, one purpose

Overloaded notebooks split. Trivial siblings merge. Section summaries
roll up, but do not duplicate.

### Principle H: Build scripts mirror notebooks

Every `NNN_<slug>.ipynb` has exactly one
`scripts/build_notebook_NNN_<slug>.py`.

### Principle I: Modality discipline

Every notebook states text, voice, image, or multimodal coverage.
Prefer inline multimodal when the story reads cleanly in one pass.
Use sibling split (separate text, voice, image notebooks) only when
compute profile, setup, or narrative diverge. Defend each choice in
one sentence.

### Principle J: Three-digit zero-padded IDs

`000` through `999`. Gaps of 10 between siblings. Round-hundred starts
for sections. Slug format: `duecare_NNN_<snake_case_purpose>`. Filename
mirrors slug without the `duecare_` prefix:
`NNN_<snake_case_purpose>.ipynb`.

## Recommended section structure (revise with one-sentence defense per change)

Seed layout. You may merge, split, rename, or reorder, as long as
principles A through J hold.

| Prefix | Section | Scope |
|---|---|---|
| `000` to `090` | Orientation | Index, glossary, reading paths, quickstart, story hook |
| `100` to `190` | Exploration | Free-form Gemma 4 playground (text and multimodal), capability sniffing |
| `200` to `290` | Evaluation framework | Prompt-test harness, rubric design, domain packs, sample evals, cross-model baselines with and without prompt engineering, context, and RAG |
| `300` to `390` | Data pipeline | Scrape, categorize, distill, prompt-generate, prompt-remix |
| `400` to `490` | Large-scale evaluation | Full-corpus Gemma 4 eval, cross-model eval, enhanced variants, section summary |
| `500` to `590` | Adversarial | Self-learning harness, boundary discovery, obfuscation, multi-LLM jailbreak crafting |
| `600` to `690` | Tools and templates | Tool-call eval, tool generation, tool maintenance, template library, template generation and maintenance, adversarial tool abuse |
| `700` to `790` | Fine-tuning | Curriculum build, Unsloth training run, SuperGemma vs stock safety-gap |
| `800` to `890` | Implementation | Server-side enterprise, client-side on-device, NGO public-API |
| `900` to `990` | Meta and rollup | Final results dashboard, writeup companion, video companion, suitability scorecard, business model, infrastructure plan |

## Taylor's seed journey (coverage targets, not a spec)

1. Basic Gemma 4 free-form playground
2. Prompt-test evaluation framework
3. Sample prompt tests plus Gemma 4 evaluation
4. Evaluation against other models
5. Evaluation against other models with prompt engineering, context,
   RAG
6. Prompt-test generation pipeline (multi-step, at scale)
7. Document and context acquisition (scraping)
8. Document and context categorization
9. Document and context distillation (fact extraction)
10. Prompt generation from documents and context
11. Prompt remixing
12. Large-scale prompt-test and Gemma 4 eval
13. Large-scale vs other models
14. Large-scale vs other models enhanced
15. Adversarial self-learning harness vs Gemma 4
16. Adversarial self-learning harness vs other models
17. Adversarial self-learning harness enhanced
18. Tool-call analysis, evaluation, generation, maintenance
19. Template evaluation, generation, maintenance
20. Multimodal (text, voice, image) coverage of each of the above
21. Gemma 4 suitability overview and recommended architecture
22. Enterprise server-side demo (social media platform)
23. Client-side demo
24. Public API for NGOs (complaint filing, document assistance)

Treat these as coverage targets Copilot must map into the section
layout above. Each coverage target is satisfied by one notebook, a
merged notebook, an inline-multimodal notebook, a sibling split, or
a deferred summary. Defend each merge or split in one sentence.

## Engineering discipline layer (hard constraints)

These apply to every notebook spec, every ticket, and every code
proposal. If a suggestion does not satisfy all of these, it does not
ship.

### Best practices

- Python 3.11 or newer. Pydantic v2 at every boundary.
  `typing.Protocol` for cross-layer interfaces.
  `from __future__ import annotations`. `pathlib.Path` for paths.
  `ruff` and `mypy --strict` clean. Enforced by
  `.claude/rules/20_code_style.md`.
- Real tests colocated with modules. Every module has a `tests/`
  sibling with at least one real behavioral assertion. No
  `assert True`, no tests that only check import.
  Enforced by `.claude/rules/30_test_before_commit.md`.
- Reproducibility is an invariant. Every result ties back to
  `(git_sha, config_hash, dataset_version, run_id)` via the
  provenance chain in `duecare.core.provenance`.
- Deterministic scoring where possible. Rubric-based hash-stable
  grading beats LLM-as-judge for headline numbers. LLM-as-judge is
  a secondary signal, never the only one.
- Meta files (`PURPOSE.md`, `AGENTS.md`, `INPUTS_OUTPUTS.md`,
  `HIERARCHY.md`, `DIAGRAM.md`, `TESTS.md`, `STATUS.md`) are
  auto-generated from `scripts/generate_forge.py`. Never hand-edited.

### Anti-slop rules

- No filler words. Do not use leveraging, seamlessly, robust,
  cutting-edge, state-of-the-art, comprehensive, empower, delve, in
  today's landscape, it is worth noting that, navigate the
  complexities, unlock, harness, journey, synergy.
- No em dashes. Use commas, colons, parentheses, or separate
  sentences.
- No emojis.
- No decorative ASCII art. Diagrams only when they convey structure
  prose cannot.
- No placeholder code. No `TODO implement this`, no
  `raise NotImplementedError()` in shipped paths, no `pass` bodies
  in public functions. If something is not built, label it gap.
- No generic advice. Rejects include "add more tests", "improve
  error handling", "consider scalability". Every recommendation
  cites `path:line` and proposes a specific change.
- No hallucinated APIs. If Copilot cannot verify a function, class,
  or keyword argument, flag unverified.
- No "comprehensive analysis of" paragraphs.
- No apologetic hedging. "It might be worth considering whether
  perhaps" gets cut.
- No duplicated content across sections.
- No padded symmetric bullet lists.
- No empty headings.
- No markdown noise. Emphasis used sparingly keeps its signal.

### Organization, modularity, separation of concerns

- One-sentence purpose per artifact. If the purpose does not fit in
  one sentence, the artifact is doing too much.
- Layered imports only. Flow is downward:
  `workflows -> agents -> tasks -> models -> domains -> core`.
  Any violation is a P0 finding with `path:line`. Never import up.
  Never sibling-import inside a layer without going through
  `duecare-llm-core`.
- Protocols across layers, not concrete classes. `Agent`,
  `Coordinator`, `Model`, `Task`, `DomainPack` are contracts.
- Evaluation and implementation live in different sections, different
  packages where relevant, different CI gates.
- Data pipeline isolated from model pipeline. Raw, labeled,
  anonymized, training-ready JSONL. Each stage a distinct module
  with its own tests. The Anonymizer is a hard gate. PII rules in
  `.claude/rules/10_safety_gate.md`.
- One kernel, one purpose.
- Narrow public APIs. Each package `__init__.py` exports only what
  third-party users of `EXTENDING.md` need. No star imports.

### Containerization and reproducibility

- Every shippable surface has a container path. FastAPI demo,
  browser extension backend, Telegram and Discord bots, HF Spaces.
  Each with a pinned `Dockerfile` or HF-Space variant and a
  documented port. Templates: the existing root `Dockerfile`,
  `docker-compose.yml`, and `deployment/hf_spaces/`.
- `make cleanroom` must pass. Every new dependency defends itself
  against the cleanroom gate.
- `uv.lock` is the source of truth for reproducibility. No version
  drift without a migration note.
- Kaggle notebooks pin `!pip install duecare-llm-*==<version>` per
  `.claude/rules/50_publish_strategy.md`.
- No `latest` tags anywhere.
- Secrets stay out. `.env` is gitignored. `.env.example` documents
  required variables. CI uses GitHub Secrets. Kaggle uses Kaggle
  Secrets. Any new credential path states where it is stored and
  how it is rotated.

### Award-winning research standards

- Reproducibility package. Writeup links the exact Kaggle notebook,
  the exact `(git_sha, dataset_version)`, and the HF model card once
  Phase 3 lands. Every headline number is reproducible by one cell.
- Honest gaps. Known failures, unresolved tradeoffs, negative
  results stated up front. See `docs/FOR_JUDGES.md`.
- Ablations. Every claim of improvement has a before-and-after
  ablation notebook in the `400` band. Each ablation states its
  isolated variable.
- Strong baselines. Compared against Llama 3 or 4, Mistral, Qwen,
  GPT-OSS, DeepSeek, and at least one frontier API via OpenRouter.
- Statistical discipline. Report n, mean, 95 percent CI or bootstrap,
  per-category breakdown. Never a single mean.
- Provenance chains shown, not told. At least one notebook walks
  from raw scrape to labeled to anonymized to training-ready JSONL
  with the `(run_id, git_sha, checksum)` chain visible in outputs.
- Named impact, not abstract. Named NGOs (Polaris Project, IJM,
  ECPAT, POEA, BP2MI, HRD Nepal). Named statutes (ILO C029, C181,
  RA 8042, Cal. Civ. Code section 1714(a)). Named corridors.
- Load-bearing Gemma 4 features. Native function calling in the
  Coordinator agent. Multimodal understanding in the Scout agent.
  Every notebook touching these says so in its header.
- Related-work awareness. Cite HELM, BigBench, HarmBench, PyRIT,
  garak, Presidio, and PACER, AustLII, BAILII for legal corpora.
- Ethical review visible. PII policy, composite-character labels,
  consent statement for any real-world data, responsible-disclosure
  notes for adversarial findings, all surfaced in the writeup and
  the glossary notebook.

### Application rules

- Every ticket in section 7 names its discipline principle. Example:
  `[P0][M][Sep-of-Concerns]`, `[P0][S][Repro]`, `[P1][L][Ablation]`.
- Every notebook row in section 3 states its kind and rubric
  dimension so evaluation and implementation are mechanically
  separable.
- Every architectural finding in section 1 cites a discipline
  principle the codebase honors or violates.
- Anti-slop enforcement is recursive. Copilot audits its own output
  against the anti-slop rules before submission. Cut filler in
  yourself before cutting it in the codebase.

## Your single task, produce `docs/COPILOT_REVIEW_OUTPUT.md`

Sections 0 through 8 below, in order. Section 0 is the packages vs
notebooks separation block, written first so the rest of the review
stands on it. No preamble. No meta. Cite `path:line` for every
factual claim. Maximum 6,000 words.

### Section 0. Packages vs Kaggle notebooks, the separation of concerns (at most 400 words)

Open the review by stating the boundary in plain English, then verify
it with citations. The review must make clear that:

- Packages under `packages/duecare-llm-*` are the **library**. They
  own all reusable logic, are versioned, tested, and released to
  PyPI. Import direction is one way:
  `workflows -> agents -> tasks -> models -> domains -> core`.
  Namespace is `duecare.*` (PEP 420).
- Notebooks under `kaggle/kernels/` are the **experiments and
  stories**. They import the library via
  `from duecare.<layer> import <thing>` and never re-implement it.
  Each notebook answers one question.
- Scripts under `scripts/` are the **glue**. Build scripts emit
  notebooks programmatically, publish scripts push kernels to
  Kaggle, local runners exercise the library outside a kernel.

Verify the boundary by citing at least six real import statements
across different notebooks (for example
`kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb:110`,
`kaggle/kernels/duecare_03_agent_swarm_deep_dive/03_agent_swarm_deep_dive.ipynb:60`,
`kaggle/kernels/duecare_06_adversarial/06_adversarial_resistance.ipynb:148`,
`kaggle/kernels/duecare_02_cross_domain_proof/02_cross_domain_proof.ipynb:207`).
Call out any notebook that grows its own logic inline when it could
import from `duecare.*`, and list the exact symbols to extract into
the library. Audit the `notebooks/` mirror and call out any extra local
files not backed by a Kaggle kernel.

Produce a small plain-text diagram (no emojis, no decorative
boxes) showing the three layers (library, notebooks, scripts) and
their one-way dependencies. This block is the grounding for the
rest of the review. A reader who stops here must already know where
logic, narrative, and glue each live.

### Section 1. High-level architecture review (at most 1,000 words)

- Boundary audit. Scan `packages/duecare-llm-*/src/forge/*/*.py` for
  cross-layer concrete-class imports that should use Protocols from
  `duecare.core.contracts`. Layer order:
  `agents -> tasks -> core`, never reverse. Name violations with
  `path:line`.
- Workflows package (241 LOC) minimum viable orchestrator shippable
  in 33 days. Port the retry and budget pattern in
  `packages/duecare-llm-agents/src/forge/agents/base/`
  `AgentSupervisor`. One paragraph.
- Publishing package minimum viable change. `ModelCardGenerator`
  conformance to the three required HF model card fields. Cite the
  spec URL.
- Duplicate surfaces. Overlap between `src/demo/`,
  `packages/duecare-llm/src/duecare/cli/`, and `scripts/`. Name and
  propose one canonical home per concern.
- Secrets. `.env` is gitignored. Flag any other paths in
  `deployment/`, `kaggle/`, or `configs/` that might leak tokens.

### Section 2. Organization improvements, at least 10 items

Table columns: path, problem, fix, effort in S/M/L hours, rubric
dimension (Impact, Video, Tech), priority (P0, P1, P2), discipline
principle.

Cover at minimum: packages (merge, split, rename candidates),
`scripts/` triage (build-time vs runtime vs dev-only, propose a
`tools/` folder or move into `duecare-llm-publishing`),
`notebooks/` mirror audit (28 tracked kernels plus extra local files), `docs/` consolidation (24 files with
overlapping scope), domain rubric symmetry
(`trafficking/rubrics/` has 5 sub-rubrics, the other two domains
have none), pre-commit hook gap, `_archive/legacy_src/`
deletability, `configs/duecare/models.yaml` adapter coverage.

### Section 3. Curriculum redesign

Deliverable format:

a. Section map. One paragraph per section stating scope, rubric
   dimensions advanced, discipline principles it enforces, and the
   narrative goal of the section summary notebook. Deviate from the
   recommended section structure only with a defense sentence per
   deviation.

b. Full notebook table. Every notebook in the final curriculum,
   including every section summary. Columns:

| # | Section | Slug | Filename | Old slug if mapped | Kind | Modality | Question | Inputs | Outputs | Decision impact | Dependencies | Runtime | Status | Must / Should / Nice | Build source |

Requirements:

- Three-digit zero-padded IDs, section-aligned starts.
- Gaps of 10 between siblings. Summaries at the `NN0` top of each
  section band.
- Slug format `duecare_NNN_<snake_case_purpose>`. Filename mirrors
  slug without `duecare_` prefix.
- Every current kernel under `kaggle/kernels/` is accounted for.
  Map onto a new row, or explicitly mark delete, or merge into
  `NNN` with reason.
- Every seed-journey coverage target is satisfied once.
- `phase2`, `phase3`, `index`, and `06_adversarial` mismatches
  resolved.
- Any notebook that would exceed the size caps in Principle C is
  split into sibling slots.

c. Per-section summary spec. For each summary notebook, one
   paragraph stating which child notebook outputs it consumes, the
   headline chart it produces, and the writeup or video paragraph
   it feeds.

d. Insertion-slot map. For each section, a short list of the
   currently-free slots (for example, "215, 235, 255, 285 are open")
   so future notebooks can be added without renumbering.

e. `git mv` block renaming every affected file and directory. Cover
   `kaggle/kernels/*`, `notebooks/*` mirror, and
   `scripts/build_notebook_*.py`.

f. `kernel-metadata.json` `id` edits. One line per file, old to new
   `id` (form `<username>/<slug>`).

g. Docs diff summary. One sentence each for
   `docs/notebook_guide.md` and `docs/kaggle_integration.md`.

### Section 4. Glossary notebook spec

Propose an ID inside the `000` to `090` orientation band, for
example `duecare_005_glossary.ipynb`. A new reader opens this one
notebook and understands the end-to-end journey.

a. Full cell-by-cell outline. One row per cell: cell number, type
   (md or code), title, two-line content summary. Target at most 40
   cells. Total notebook-resident Python at most 300 lines.

b. Story structure (markdown cells):

   - Hook: Cal. Civ. Code section 1714(a) duty-of-care framing,
     Maria composite character (see
     `.claude/rules/10_safety_gate.md` for the composite-character
     rule).
   - The journey as a narrated table. One row per section, each
     linking to the defining file with `path:line`, the sibling
     Kaggle notebook, and the section summary notebook.
   - An explicit "Evaluation vs Implementation" framing so judges
     see which sections prove the science and which ship it.

c. Linked terms table. Every Duecare-specific term with a
   two-sentence maximum definition and two links (repo `path:line`
   plus sibling notebook). Full coverage:

   - Project: DueCare, Forge, AGENTS.md standard,
     folder-per-module, provenance chain, simhash,
     AgentSupervisor, AgentContext, AgentOutput.
   - 12 agents, one line each: scout, data_generator, adversary,
     anonymizer, curator, judge, validator, curriculum_designer,
     trainer, exporter, historian, coordinator.
   - 9 tasks, one line each: guardrails, anonymization,
     classification, fact_extraction, grounding,
     multimodal_classification, adversarial_multi_turn, tool_use,
     cross_lingual.
   - Scoring: rubric band (worst, bad, neutral, good, best), 6
     safety dimensions, graded response.
   - 5 attack categories: business_framed_exploitation,
     jurisdictional_hierarchy_exploitation,
     financial_crime_blindness,
     prompt_injection_amplification,
     victim_revictimization.
   - Domain concepts: ILO indicators (C029, C181, RA 8042),
     migration corridors, PII spec, composite character.
   - Modalities: text, voice, image.
   - Tools, templates, function calling, tool generation, tool
     maintenance.
   - External tech: Unsloth, llama.cpp, GGUF, LiteRT, LoRA, QLoRA,
     E2B, E4B, PEP 420 namespace packages, Pydantic v2, Protocol
     (PEP 544), Presidio, faiss, Ollama, uv workspace, jupytext.

d. Runnable code cells (free Kaggle kernel, no GPU):

   - `pip install duecare-llm-core duecare-llm-domains`
   - Load trafficking domain pack. Print taxonomy and rubric keys.
   - Print registered agents from `agent_registry` and tasks from
     `task_registry`.
   - Render a Plotly diagram of the section layout using the
     `notebook_connected` renderer. Cite the file in the existing
     notebooks that shows the applied Plotly fix.

e. Top-of-notebook index. Every section and every other Kaggle
   notebook with its new slug, one-line purpose, modality, kind,
   must or should or nice priority, and recommended read order.

f. Build source. Produce as
   `scripts/build_notebook_NNN_glossary.py` following the pattern
   of `scripts/build_notebook_00.py`. If `build_notebook_22.py`
   diverges from that pattern, pick one and state which.

### Section 5. Modality coverage plan (text, voice, image)

One paragraph per modality:

- What capability exists in the codebase today. Cite `path:line`.
- Which curriculum rows cover the modality now, and which need a
  sibling or inline section.
- Minimum viable voice adapter path. Gemma 4 native, or Whisper plus
  TTS bridge. Cite `src/demo/multimodal.py`,
  `src/demo/function_calling.py`, and any `duecare-llm-models`
  adapter paths.
- Minimum viable image adapter path.
- Which rows are inline multimodal vs sibling split, one sentence
  per decision.

### Section 6. README and docs placement changes

- First 120 words rewrite for mobile judges on `README.md`. Produce
  verbatim, plain English, no em dashes, no emojis.
- `docs/notebook_guide.md` becomes the canonical reading-order doc.
  Produce the new TOC in one code block. Include section boundaries
  and summary notebooks.
- `docs/kaggle_integration.md`. Merge into `notebook_guide.md`,
  yes or no, plus a one-sentence rationale.

### Section 7. Applications, infrastructure, and business model

This section translates the capability work into a shipped product
story. Every claim here must reference a code path, deployment
target, or notebook slug. No aspirational language.

a. Three application tracks and their infrastructure.

   Track 1: Enterprise server-side. The consumer is a social-media
   platform or job-board operator running waterfall detection at
   ingestion scale. Components to name: API ingress, queue,
   rubric-based quick filter, Gemma 4 enhanced scorer, moderation-
   queue output, audit log. Reference existing code:
   `src/demo/app.py`, `src/demo/social_media_scorer.py`,
   `src/demo/quick_filter.py`. Container target: root `Dockerfile`
   and `docker-compose.yml`. Scaling strategy and rate-limit
   strategy: name the current state and the gap.

   Track 2: Client-side on-device. The consumer is a frontline
   NGO worker or migrant worker using a phone or a low-resource
   laptop. Components: browser extension MV3, on-device runtime
   (llama.cpp for desktop, LiteRT for Android), local cache,
   opt-in telemetry, offline-first UX. Reference existing code:
   `deployment/browser_extension/`,
   `packages/duecare-llm-models/src/forge/models/llama_cpp_adapter/`.
   State what is shipped, what is stubbed, and what must be built
   before the video.

   Track 3: NGO public API. The consumer is an NGO caseworker
   filing complaints, filling complaint documents, or triaging
   reports. Components: public FastAPI endpoint, template library
   for complaint forms, document-assist routes, per-corridor legal
   provision lookup, rate-limited free tier. Reference existing
   code: `src/demo/report_generator.py`, `src/demo/rag.py`,
   `configs/duecare/legal_provisions.yaml`,
   `configs/duecare/corridors.yaml`. State which endpoints exist,
   which are stubbed, and which need to be added.

   For each track produce:

   - Architecture sketch (small ASCII or markdown list, not a
     decorative diagram).
   - Named container or runtime target.
   - Named deployment surface (HF Space, Fly.io, self-hosted,
     Chrome Web Store, app store, on-device sideload, and so on).
   - Who operates it in the real world. Name a plausible operator.
   - Which notebook in the curriculum validates the track as a
     working system.

b. Business model.

   - Who pays. Name the payer for each track. Enterprise might pay
     per API call or per seat. NGO track may be free and grant-
     funded. Client-side may be free to the worker and bundled
     with an enterprise contract.
   - What is free, what is paid, what is source-available. Tie back
     to the `duecare-llm-*` PyPI split and the MIT license.
   - Cost drivers and gross-margin assumptions at a one-number
     granularity (for example, "per-1k-token cost at Gemma 4 E4B
     on llama.cpp is approximately X, based on Kaggle T4 baseline
     measured in `kaggle/kernels/duecare_00_gemma_exploration/`").
     If the number is unverified, label it unverified.
   - Grant and partnership pathway. Name Polaris Project, IJM,
     ECPAT, POEA, BP2MI, HRD Nepal as plausible partners for the
     NGO track. Cite any existing mentions in
     `docs/deployment_modes.md`, `README.md`.
   - Compliance posture. Cal. Civ. Code section 1714(a) framing.
     GDPR and CCPA stance for the NGO API. Data-residency note.
   - One-paragraph defensibility. What prevents a copycat from
     cloning Duecare in a weekend. The answer must reference the
     21K-test benchmark, the provenance chain, the fine-tuned
     weights on HF Hub, the NGO relationships, or a specific
     combination.

c. Infrastructure plan.

   - Deployment matrix: for each shippable surface, state today's
     state, the 33-day goal, and the post-hackathon roadmap.
   - Observability: cite `duecare.observability` and name what
     metrics, logs, and audit events each track emits.
   - CI and release: cite `.github/workflows/ci.yml` and
     `claude.yml`. State whether each track is in CI today and
     what must be added.
   - Cost ceiling through submission. One line per track stating
     maximum spend Taylor will tolerate before submission.
   - Fallback plan. If Phase 3 fine-tune does not converge, what
     ships in the enterprise track. If HF Spaces goes down, what
     is the static-site fallback for judges. If the video recorder
     is unavailable, who records.

d. Other adjustments.

   A short list of non-obvious changes the review surfaces but does
   not fit cleanly into sections 1 through 7. Examples that may or
   may not apply: rename ambiguous terms, unify log format, retire
   a deprecated notebook, add a SECURITY.md, add a CODE_OF_CONDUCT.md,
   propose a dataset-card alongside the model card, propose an ADR
   folder for architectural decisions, propose a public-facing
   status page during the submission window.

Section 7 length cap: 1,500 words. If over, cut Other Adjustments
first, then Infrastructure, never the three application tracks or
the business model.

### Section 8. Implementation ticket list

Flat list, one ticket per line, at most 120 characters, ordered P0
to P2 and within each priority shortest-first-to-unblock-others.
Format:

```
[P0][S][Tech][Repro] Fix duecare_06_adversarial dir and filename mismatch in kaggle/kernels/
[P0][M][Video][Sep-of-Concerns] Renumber 29 Kaggle kernels into section-aligned three-digit scheme
[P0][L][Impact][Best-Practices] Build duecare_NNN_glossary.ipynb, narrative orientation notebook
[P0][M][Impact][Summary] Gap-build one _summary notebook per section, consumes cached child outputs
[P0][S][Tech][Anti-Slop] Insert question, inputs, outputs, decision-impact header block into every notebook
...
```

Include gap-build tickets for every curriculum row with Status gap,
every section summary notebook that does not exist yet, and every
application-track component in section 7 that is currently stubbed.

## Constraints

- Cite `path:line` for every factual claim. Label proposals
  unverified if they cannot be cited.
- Obey the engineering discipline layer. Every output is checked
  against it. A suggestion that fails any bullet is cut.
- No new abstractions the codebase does not already support. Port
  `AgentSupervisor`, `Registry[T]`, folder-per-module. Do not
  invent.
- Evaluation and implementation live in different sections.
- Every section has at least one summary notebook that reads
  cached child outputs.
- Every notebook has Question, Inputs, Outputs, Decision impact,
  Dependencies, Kind, Modality, Runtime, and Provenance in its
  header.
- Notebook size caps: at most 40 cells, at most 300 lines of
  notebook-resident Python, at most 60 lines per single code
  cell. Longer logic lives in packages or scripts.
- Insertion slots: 9 free slots between each pair of adjacent
  notebooks in a section, reserved for future inserts without
  renumbering.
- Impact beats Video beats Tech in ties.
- Real, not faked for demo, is an invariant.
- Be opinionated. Pick one path when two are defensible. Defend in
  two sentences. No menus.
- Modality discipline. Every evaluation, adversarial, tool, or
  template row states its text, voice, image coverage.
- Containerization discipline. Every deployable surface names its
  container path, or states "not containerized" with a reason.
- Reproducibility discipline. Every headline number pins to
  `(git_sha, dataset_version, run_id)`.
- No em dashes, no emojis, no filler adjectives, plain English.
- Length cap: 6,000 words. If over, cut section 6 first, then
  section 5. Never cut sections 0, 1, 3, 4, 7, or 8.

## Read before writing (in order, stop as soon as grounded)

1. `CLAUDE.md`, root project context.
2. `.claude/rules/00_overarching_goals.md`, rubric.
3. `docs/FOR_JUDGES.md`, standard your output must meet.
4. `docs/notebook_guide.md` and `docs/kaggle_integration.md`,
   existing ordering narrative (stale, you are replacing it).
5. Every `kaggle/kernels/*/kernel-metadata.json`, current kernel
   state, 29 files.
6. `scripts/build_notebook_00.py` and `scripts/build_notebook_22.py`,
   build-script conventions. Pick one.
7. `packages/duecare-llm-workflows/` (241 LOC), the weakest package.
8. `packages/duecare-llm-publishing/src/forge/publishing/model_card/`,
   the second weakest.
9. `configs/duecare/domains/trafficking/`, live data the glossary
   notebook loads.
10. `src/demo/multimodal.py` and `src/demo/function_calling.py`,
    seeds for section 5.
11. `src/demo/app.py`, `src/demo/social_media_scorer.py`,
    `src/demo/quick_filter.py`, `src/demo/report_generator.py`,
    `src/demo/rag.py`, seeds for section 7 application tracks.
12. `deployment/browser_extension/`, seeds for the client-side
    application track.
13. `configs/duecare/corridors.yaml` and
    `configs/duecare/legal_provisions.yaml`, seeds for the NGO
    public-API track.
14. Sample a dozen existing notebooks across the current 29 to
    understand tone, cell conventions, and chart style.

## Output

Single file at `docs/COPILOT_REVIEW_OUTPUT.md`. Sections 0 through 8
exactly in that order. Section 0 is the packages vs notebooks
separation, the grounding for everything after. Taylor is the only
reader. Write for 30 minutes of reading.
