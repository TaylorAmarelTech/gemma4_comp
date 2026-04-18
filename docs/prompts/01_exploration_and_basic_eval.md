# Prompt 01. Exploration and basic evaluation (bands 100 to 290)

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
> This prompt covers the first real narrative track: loading Gemma 4,
> running free-form prompts, introducing the evaluation framework, and
> running the first sample evaluations. Read
> `docs/prompts/_shared_discipline.md` first. It supplies the voice,
> the engineering discipline layer, the curriculum principles, and the
> full-curriculum map.

---

## Scope

Cover bands 100 through 290 only. Do not design notebooks for other
bands. Do not re-specify the glossary (that is band 000 to 090, owned
by a different prompt).

| Band | Section | What this prompt owns |
|---|---|---|
| 100 to 190 | Exploration | Free-form Gemma 4 playground. Load the model, send raw prompts, inspect outputs. Sniff capabilities without scoring machinery. |
| 200 to 290 | Evaluation framework and sample runs | Introduce the prompt-test harness, rubric, domain pack. Run the first sample evaluations (small corpus, single model, then single model vs a handful of others). |

## Coverage targets (must each be satisfied inside bands 100 to 290)

1. **Free-form text playground.** Load Gemma 4 E4B and E2B locally
   (Ollama) and on a Kaggle T4 (transformers). Send a handful of
   trafficking prompts and inspect raw outputs. No rubric. Purpose:
   reader sees the model respond.
2. **Free-form multimodal playground.** Same as 1 but with vision and
   voice inputs where the adapter supports it. Cite
   `src/demo/multimodal.py` and `src/demo/function_calling.py` for
   the existing multimodal surfaces.
3. **Evaluation framework walkthrough.** Introduce the domain pack
   concept, the rubric (5-band worst to best), the nine tasks, the
   registries. This is the reader's first exposure to
   `duecare.tasks`, `duecare.domains`, `duecare.core`.
4. **Sample evaluation of Gemma 4 alone.** A small corpus (at most
   50 prompts) scored with the rubric. Reports n, mean, 95% CI,
   per-category breakdown. Produces a headline number and a chart.
5. **Sample evaluation of Gemma 4 alone, multimodal.** Voice and
   image sibling of 4. Decide inline vs sibling and defend.
6. **Sample evaluation vs other models, plain.** Gemma 4 vs Llama 3
   or 4, Mistral, Qwen, GPT-OSS, DeepSeek on the same 50-prompt
   corpus.
7. **Sample evaluation vs other models, enhanced.** Same comparison
   with prompt engineering, retrieval context, and RAG applied
   identically across all models. Isolate the enhancement as the
   variable.
8. **Section summary notebook at 290.** Reads cached outputs from
   the band, produces one chart and one paragraph for the writeup.

Any seed concern from the 24-step journey that does not fit here
belongs to a different band. Say so and route it.

## Current kernels in or adjacent to this band

Source of truth is `docs/current_kaggle_notebook_state.md`. Use the
Kaggle id column in that file, not the directory slug, when
referring to a kernel. Candidates based on current content:

- `duecare_00_gemma_exploration` (Kaggle id
  `taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts`)
  maps to the 100 range.
- `duecare_01_quickstart` maps to the early 200 range (framework
  tour).
- `duecare_02_cross_domain_proof` maps to band 200 or 400 depending
  on scale.
- `duecare_04_submission_walkthrough` maps to band 000 to 090
  orientation, not this band. Route out.
- `duecare_07_oss_comparison`, `duecare_11_comparative`,
  `duecare_15_ollama_cloud`, `duecare_16_mistral_family`,
  `duecare_17_openrouter_frontier` map to the 260 to 280 range
  (cross-model sample eval).
- `duecare_05_rag_comparison` may map here (enhanced sample eval)
  or to band 400 (large-scale enhanced). Decide.

For every current kernel, decide: stays in this band with new slug,
moves to a different band, or is deleted with a reason.

### `forge_llm_core_demo.ipynb` decision (owned by this prompt)

This is the only orphan local notebook. Resolve it here. Choose one:

a. Delete, with a one-sentence reason (likely redundant with
   `duecare_01_quickstart`).
b. Promote to a Kaggle kernel at a slug in band 100 or 200, with a
   new `kaggle/kernels/duecare_NNN_<slug>/kernel-metadata.json` and
   a `scripts/build_notebook_NNN_<slug>.py`.
c. Mark local-only by design, with a rationale, and propose the
   "Local-only by design" heading to add to
   `docs/current_kaggle_notebook_state.md`.

The deliverable must include the chosen path and the exact file
changes (git mv, new metadata, new build script, or delete).

## Deliverable, produce `docs/review/100-290_exploration_and_basic_eval.md`

Sections 0 through 5 below in order. Cite `path:line` for every
factual claim. Maximum 2,500 words.

### Section 0. Band scope and grounding (at most 200 words)

State in plain English what bands 100 to 290 cover and what they do
not. Confirm the packages vs notebooks boundary for this band
specifically: every notebook imports from `duecare.models`,
`duecare.domains`, `duecare.tasks`, and `duecare.core`; no notebook
in this band defines its own adapter or scorer inline. Cite at
least three existing import lines across current kernels in this
band.

### Section 1. Per-notebook audit of existing kernels in the band

For each current kernel that belongs here, fill the Principle B
header checklist:

- Slug (current) and proposed new slug.
- Question (one sentence).
- Inputs (paths and Kaggle slugs).
- Outputs (paths and schemas).
- Decision impact (which downstream notebook IDs each plausible
  answer routes to).
- Dependencies (upstream notebook IDs).
- Kind, Modality, Runtime, Provenance.
- Cell count and notebook-resident Python line count. Flag breaches
  of Principle C.
- Logic that should be extracted into `duecare.*` with exact symbol
  names and target packages.

Use a compact table, one row per kernel.

### Section 2. Target section map for bands 100 to 290

For bands 100 and 200:

- Name the section.
- State scope in one sentence.
- State rubric dimensions advanced (Impact, Video, Tech).
- State the summary notebook's narrative goal.
- List the insertion slots currently free (for example, "115, 135,
  155, 175 are open").

### Section 3. Full notebook table for the band

Columns: #, Section, Slug, Filename, Old slug if mapped, Kind,
Modality, Question, Inputs, Outputs, Decision impact, Dependencies,
Runtime, Status (exists / partial / gap), Must / Should / Nice,
Build source.

Rules:

- Three-digit zero-padded IDs, step of 10, round-hundred section
  starts.
- Slug format `duecare_NNN_<snake_case_purpose>`.
- Summary at 190 and 290.
- Every coverage target 1 through 8 above appears as a row.
- Every current kernel in the band appears: mapped, moved, or
  marked delete with reason.

Append:

- `git mv` block for affected `kaggle/kernels/*` directories,
  `notebooks/*` mirror files, and `scripts/build_notebook_*.py`.
- `kernel-metadata.json` id edits, one line per file, old to new.
- Build-script names for any gap rows
  (`scripts/build_notebook_NNN_<slug>.py`).

### Section 4. Gap list

Flat list. Each item states: new slug, what is missing, why it is
required by a coverage target, and an effort estimate (S, M, L).
Include both full-notebook gaps and smaller gaps (for example,
"duecare_220 is missing the 95% CI block required by award-winning
research standards").

### Section 5. Ticket list for this band

Flat, one per line, at most 120 characters, ordered P0 to P2.
Format:

```
[P0][S][Tech][Anti-Slop] Insert Principle B header block into duecare_100_<slug>
[P0][M][Video][Summary] Build duecare_290_summary reading cached outputs from 100-280
[P0][M][Impact][Ablation] Gap-build duecare_280_vs_others_enhanced, isolates RAG as variable
[P0][S][Repro] Pin duecare-llm-*==<version> in every band 100-290 pip install cell
...
```

Include at least one ticket for:

- Every Principle C size-cap breach flagged in section 1.
- Every piece of notebook-inline logic that should be extracted
  into `duecare.*`.
- Every coverage gap in section 4.
- The 290 summary notebook.
- The `notebooks/` local mirror resync if kernels in this band are
  affected.

## Constraints specific to this prompt

- Do not design notebooks outside bands 100 to 290.
- Do not respec the glossary (band 000 to 090).
- Do not respec large-scale eval (band 400) or adversarial (band
  500). Route concerns there.
- Every notebook in this band must run on a free Kaggle kernel or a
  single T4, not multi-GPU.
- Every notebook header must state Gemma 4 version(s) tested
  (E2B, E4B, both).
- Every comparison notebook must name its baseline models explicitly
  and cite the adapter path in `packages/duecare-llm-models/src/duecare/models/`.

## Read before writing, in order, stop when grounded

1. `docs/current_kaggle_notebook_state.md`, the authoritative
   inventory.
2. `docs/prompts/_shared_discipline.md`.
3. `CLAUDE.md`.
4. `.claude/rules/00_overarching_goals.md`.
5. `docs/FOR_JUDGES.md`.
6. `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb`.
7. `kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb`.
8. `kaggle/kernels/duecare_07_oss_comparison/07_oss_model_comparison.ipynb`.
9. `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb`.
10. `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb`.
11. `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb`.
12. `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb`.
13. `notebooks/forge_llm_core_demo.ipynb`, the orphan local
    notebook this prompt must resolve.
14. `scripts/build_notebook_00.py` and one of the 07, 15, 16, 17
    build scripts for the comparison convention.
15. `scripts/publish_kaggle.py` for the push-notebooks contract.
16. `packages/duecare-llm-models/src/duecare/models/__init__.py`
    and the Ollama, transformers, OpenAI-compatible, and
    HF-endpoint adapter folders.
17. `packages/duecare-llm-domains/src/duecare/domains/__init__.py`.
18. `packages/duecare-llm-tasks/src/duecare/tasks/__init__.py`.

## Output

Single file at `docs/review/100-290_exploration_and_basic_eval.md`.
Sections 0 through 5 in order. Taylor is the only reader.
