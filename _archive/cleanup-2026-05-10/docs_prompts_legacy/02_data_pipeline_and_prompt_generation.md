# Prompt 02. Data pipeline and prompt generation (band 300 to 390)

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
> This prompt covers the data pipeline track: document scraping,
> categorization, distillation, prompt generation from extracted
> facts, and prompt remixing. Read
> `docs/prompts/_shared_discipline.md` first.

---

## Scope

Cover band 300 to 390 only.

| Band | Section | What this prompt owns |
|---|---|---|
| 300 to 390 | Data pipeline | Acquire documents and context, categorize them, distill facts, generate new prompts from the distilled facts, remix prompts, deduplicate, produce a training-ready JSONL. |

Large-scale evaluation of the resulting corpus belongs to band 400
and is owned by prompt 03. Do not respec band 400 here. Fine-tuning
belongs to band 700 and is out of scope for this prompt.

## Coverage targets (must each be satisfied inside band 300 to 390)

1. **Document acquisition.** Scraping ILO databases, court filing
   repositories (PACER, AustLII, BAILII), FATF and FATCA
   publications, NGO reports. Cite existing Playwright and stealth
   stack code in `_archive/legacy_src/src/scraper/` and the scraper
   pipeline stubs in `packages/duecare-llm-domains/src/duecare/domains/pipeline/`.
2. **Document categorization.** Classify each raw document by
   sector (domestic work, fishing, construction, agriculture),
   migration corridor, ILO forced-labor indicators, attack category
   (business_framed_exploitation, jurisdictional_hierarchy,
   financial_crime_blindness, prompt_injection_amplification,
   victim_revictimization), and severity.
3. **Document distillation.** Extract `ExtractedFact` records:
   named entities, legal citations (ILO C029, C181, RA 8042),
   monetary amounts, employer names, fee structures, migration
   corridors, dates. Cite `duecare.domains.pipeline.extractor`.
4. **Prompt generation from facts.** Take `ExtractedFact` records
   and generate new evaluation prompts with graded response
   examples on the 5-band scale (worst to best). Dedupe against
   the existing 21K corpus. Produce provenance linking each new
   prompt to source documents.
5. **Prompt remixing.** Spintax, regex substitution, charpad, LLM
   rephrase, obfuscation. Cite the existing remixer notebook
   `duecare_00b_prompt_remixer`. Every mutation must preserve the
   graded-response mapping.
6. **Anonymizer gate.** Hard gate between raw documents and the
   training-ready JSONL. No downstream notebook reads raw PII.
   Audit log stores `sha256(original)` only. Enforced by
   `.claude/rules/10_safety_gate.md`. Cite
   `packages/duecare-llm-agents/src/duecare/agents/anonymizer/`.
7. **Dataset assembly.** Merge graded examples, deduplicate,
   balance across domains, categories, grades. Produce Unsloth
   chat-format JSONL, train and val and test splits, and a
   provenance manifest. Cite `scripts/extract_benchmark_prompts.py`
   and `scripts/prepare_training_data.py` as existing glue.
8. **Section summary notebook at 390.** Reads cached outputs,
   produces one chart (counts per domain, category, grade) and one
   paragraph for the writeup. States n, dedupe rate, anonymization
   hit rate, source provenance coverage.

## Source of truth for kernel state

`docs/current_kaggle_notebook_state.md` is authoritative. Use the
Kaggle id from that file when referring to a kernel, not the
directory slug. The renumber pass in this prompt must also resolve
any legacy directory-to-code-file aliases that fall inside band
300 to 390 (for example, `duecare_19_rubric_generator` contains
`19_per_prompt_rubric_generator.ipynb`). Do not touch
`forge_llm_core_demo.ipynb`; that orphan is owned by prompt 01.

## Current kernels and scripts relevant to this band

- `duecare_00a_prompt_prioritizer` maps to band 300 range
  (categorization and difficulty ranking).
- `duecare_00b_prompt_remixer` maps to band 370 range (remixing).
- `duecare_12_prompt_factory` and `duecare_19_rubric_generator`
  map to the 340 to 360 range (generation from facts, rubric
  synthesis).
- `scripts/extract_benchmark_prompts.py` already merges 17 legacy
  sources into unified JSONL. Notebook 390 summary reads its output.
- `scripts/prepare_training_data.py` already assembles the training
  JSONL. This band ends here; fine-tuning is elsewhere.
- `_archive/legacy_src/src/scraper/` has the Playwright stack. Band
  310 and 320 notebooks import a thin wrapper rather than inline
  Playwright code.

For every current kernel, decide: stays in this band with a new
slug, moves to a different band, or is deleted with a reason.

## Deliverable, produce `docs/review/300-390_data_pipeline.md`

Sections 0 through 5 in order. Cite `path:line` for every factual
claim. Maximum 2,500 words.

### Section 0. Band scope and grounding (at most 200 words)

State the band's purpose in plain English. Confirm the packages vs
notebooks boundary: scraper logic lives in
`duecare.domains.pipeline`, anonymizer logic lives in
`duecare.agents.anonymizer`, extraction in
`duecare.domains.pipeline.extractor`. Notebooks orchestrate and
visualize; they do not re-implement scraping, extraction, or
anonymization.

Cite at least three existing imports across current kernels that
confirm the boundary, plus the Anonymizer gate contract from
`.claude/rules/10_safety_gate.md`.

### Section 1. Per-notebook audit of existing kernels in the band

For each current kernel that belongs here, fill the Principle B
header checklist (Question, Inputs, Outputs, Decision impact with
downstream IDs, Dependencies, Kind, Modality, Runtime, Provenance)
plus:

- Cell count and notebook-resident Python line count.
- Logic to extract to `duecare.*` with exact symbol names.
- Compliance with the safety gate (PII handling, audit log,
  composite-character labels).

Compact table, one row per kernel.

### Section 2. Target section map for band 300 to 390

- Scope in one sentence.
- Rubric dimensions advanced.
- Summary notebook narrative goal.
- Insertion slots currently free.
- Any sub-sections (for example, "310 to 330 acquire and
  categorize, 340 to 360 distill and generate, 370 to 380 remix
  and assemble").

### Section 3. Full notebook table for the band

Columns: #, Section, Slug, Filename, Old slug if mapped, Kind,
Modality, Question, Inputs, Outputs, Decision impact, Dependencies,
Runtime, Status, Must / Should / Nice, Build source.

Every coverage target 1 through 8 must appear as a row. Every
current kernel in the band must be mapped, moved, or marked delete
with a reason.

Append:

- `git mv` block.
- `kernel-metadata.json` id edits.
- Build-script names for every gap row.

### Section 4. Data lineage map

A plain-text diagram showing the one-way flow: raw documents ->
categorized -> distilled facts -> generated prompts -> remixed ->
anonymized -> training-ready JSONL -> (hand-off to band 400 for
evaluation, band 700 for fine-tuning). Each node cites the
notebook ID and the `duecare.*` module that does the work.

State at each arrow: what is checked (schema, dedupe, PII gate),
what is logged (run_id, git_sha, checksum), and what is produced
(artifact path).

### Section 5. Ticket list for this band

Flat, one per line, at most 120 characters, ordered P0 to P2.
Format:

```
[P0][M][Tech][Safety] Wire Anonymizer gate between duecare_320 and all downstream notebooks
[P0][S][Repro] Add provenance manifest output to duecare_380_dataset_assembly
[P0][M][Video][Summary] Build duecare_390_summary with counts chart and dedupe rate
[P0][L][Impact][Ablation] Add RA 8042 and ILO C029 citation coverage to extractor
...
```

Include tickets for:

- Every Principle C size-cap breach.
- Every notebook-inline logic extraction into `duecare.*`.
- The PII audit log regression check, if missing.
- The 390 summary notebook.
- The training-JSONL schema contract (Pydantic v2 model in
  `duecare.core.schemas`).

## Constraints specific to this prompt

- Do not propose evaluation of the generated corpus here. Route
  to band 400.
- Do not propose fine-tuning here. Route to band 700.
- Every notebook that touches raw documents must state its PII
  handling in its header and cite the Anonymizer gate.
- Every generated prompt must carry provenance back to at least
  one source document with `sha256` checksum.
- Every remixer mutation must preserve the graded response
  mapping (worst, bad, neutral, good, best).
- No notebook in this band re-implements scraping. All scraping
  goes through `duecare.domains.pipeline.scraper`.

## Read before writing, in order, stop when grounded

1. `docs/current_kaggle_notebook_state.md`.
2. `docs/prompts/_shared_discipline.md`.
3. `.claude/rules/10_safety_gate.md`.
3. `packages/duecare-llm-domains/src/duecare/domains/pipeline/`
   (all files: scraper, extractor, classifier, document_store).
4. `packages/duecare-llm-agents/src/duecare/agents/anonymizer/`.
5. `scripts/extract_benchmark_prompts.py`.
6. `scripts/prepare_training_data.py`.
7. `kaggle/kernels/duecare_00a_prompt_prioritizer/`.
8. `kaggle/kernels/duecare_00b_prompt_remixer/`.
9. `kaggle/kernels/duecare_12_prompt_factory/`.
10. `kaggle/kernels/duecare_19_rubric_generator/`.
11. `configs/duecare/domains/trafficking/` (card, taxonomy, rubric,
    seed_prompts, pii_spec, and the five sub-rubrics).
12. `_archive/legacy_src/src/scraper/` for Playwright patterns, if
    any are ported.

## Output

Single file at `docs/review/300-390_data_pipeline.md`. Sections 0
through 5 in order.
