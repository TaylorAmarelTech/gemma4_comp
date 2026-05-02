# 26: DueCare suite status snapshot

Date captured: 2026-04-16
Scope: end of the current Claude Code working pass, before the next
Kaggle daily cap reset.

## Corpus example notebook: yes, exists

A dedicated notebook now explains and shows the prompt-test corpus
with concrete prompt and graded-response examples.

- **ID and title:** `130: DueCare Prompt Corpus Exploration`
- **Builder:** `scripts/build_notebook_130_prompt_corpus_exploration.py`
- **Emitted:** `notebooks/130_prompt_corpus_exploration.ipynb` and
  `kaggle/kernels/duecare_130_prompt_corpus_exploration/`
- **Target Kaggle slug:** `taylorsamarel/130-duecare-prompt-corpus-exploration`
- **Validator:** OK in `scripts/validate_notebooks.py`
- **Kaggle publish state:** push-ready, not yet live. First-time
  kernel creation blocked today by Kaggle cap and `Notebook not found`
  new-kernel response; queued for next cap reset.

### What 130 actually contains

- HTML header block with Inputs / Outputs / Prerequisites / Runtime /
  Pipeline position fixed-width table.
- Step 1: loads the shipped `trafficking` domain pack from
  `duecare-llm-domains` and, when attached, the full corpus at
  `taylorsamarel/duecare-trafficking-prompts` (74,567 prompts).
- Step 2: corpus-level HTML tables for category, sector, corridor,
  difficulty, and grade-key appearance.
- Step 3: 5-grade rubric reference card explaining `worst`, `bad`,
  `neutral`, `good`, `best`, their fixed scores (0.0, 0.2, 0.5, 0.8,
  1.0), and the `best_criteria` / `worst_criteria` flags.
- Step 4: full walk-through of `TAYLOR-001` (Hong Kong SAR domestic
  worker fee deduction prompt) rendered as 5 colored HTML cards, one
  per grade, each showing the reference response text, the numeric
  score, and the explanation of why that grade was assigned.
- Step 5: one prompt per major category
  (`business_framed_exploitation`, `regulatory_evasion`,
  `coercion_manipulation`, `victim_revictimization`,
  `moral_religious_framing`) with the best-grade reference response
  truncated for on-screen readability.
- Step 6: score-distribution summary printing count, share, and
  average score per grade across the active corpus.
- Summary: troubleshooting HTML table; URL-bearing final print
  handing off to 299 and 100.

## Implemented changes this session

### Builders edited

- `scripts/build_notebook_210_oss_model_comparison.py` rewritten to
  canonical style: HTML header, Phase 1 baseline loader with
  `PUBLISHED_BASELINE` fallback, shared `SAFETY_DIMENSIONS` constant,
  `overall is not None` assertion before plotting, HTML gap table,
  HTML troubleshooting, `_hex_to_rgba` radar fill, URL-bearing final
  print to 220 and 399, duplicate wheel-walk removed.
- `scripts/build_notebook_220_ollama_cloud_comparison.py` rebuilt in
  the canonical 200/210 style: HTML header, single hardener install,
  rubric cross-link to 100, rgba radar fill, shared
  `SAFETY_DIMENSIONS`, HTML troubleshooting, URL-bearing final print
  to 230 and 399.
- `scripts/build_notebook_130_prompt_corpus_exploration.py` created
  as the new corpus-exploration builder.
- `scripts/build_notebook_230_mistral_family_comparison.py` line 395:
  `m_info['color'] + '15'` replaced with
  `_hex_to_rgba(m_info['color'])`; helper added at top of the radar
  cell.
- `scripts/build_notebook_240_openrouter_frontier_comparison.py` line
  408: same fillcolor fix and helper.

### Shared scripts edited

- `scripts/build_index_notebook.py`: added `130 Prompt Corpus
  Exploration` into the Baseline Text Evaluation Framework section
  between 120 and 299; added `"210":
  "duecare-gemma-vs-oss-comparison"` to `PUBLIC_SLUG_OVERRIDES`.
- `scripts/build_notebook_005_glossary.py`: added the same `"210"`
  override to its `PUBLIC_SLUG_OVERRIDES`.
- `scripts/build_section_conclusion_notebooks.py`: added the same
  `"210"` override; expanded 299 recap and key points to name 130;
  rewrote 399 recap and key points to tell the post-210 / post-220
  story (5-point recap; key points about zero-harm Gemma 4 E4B,
  frontier-hedge gap, Gemma 2 -> 3 -> 4 trajectory, reproducible
  inputs).
- `scripts/notebook_hardening_utils.py`: registered
  `130_prompt_corpus_exploration.ipynb` in `INSTALL_PACKAGES` and
  `SUMMARY_MESSAGES`.

### Validators added

- `scripts/_validate_210_adversarial.py`: 17 explicit checks across
  metadata, HTML header, cross-links, install cell, SAFETY_DIMENSIONS
  reuse, assertion presence, HTML gap table, troubleshooting table,
  make_subplots import, final-print handoff, and hardener-default
  patching.
- `scripts/_validate_220_adversarial.py`: equivalent 17-check
  mirror, adapted for 220's `DIMENSION_WEIGHTS`-derived dimension
  list, rgba helper, and 230/399 handoff.

## Notebooks rebuilt in this pass

- `000_index.ipynb`
- `005_glossary.ipynb`
- `130_prompt_corpus_exploration.ipynb`
- `210_oss_model_comparison.ipynb`
- `220_ollama_cloud_comparison.ipynb`
- `230_mistral_family_comparison.ipynb`
- `240_openrouter_frontier_comparison.ipynb`
- `270_gemma_generations.ipynb`
- All nine section-conclusion notebooks: `099`, `199`, `299`, `399`,
  `499`, `599`, `699`, `799`, `899`.

## Kaggle publish state

- `210` live and `COMPLETE` as v3 at
  `taylorsamarel/duecare-gemma-vs-oss-comparison`.
- `000 index` pushed live this session as v16.
- `220`, `130`, `399`, `299`, `005` push-ready locally but currently
  cap-blocked (`400 Bad Request` or `Notebook not found` on
  new-kernel creation path).

## Validation results

- `python scripts/validate_notebooks.py`: 39 of 42 OK.
- `python scripts/_validate_210_adversarial.py`: ALL CHECKS PASSED.
- `python scripts/_validate_220_adversarial.py`: ALL CHECKS PASSED.
- Remaining 3 validator failures: `duecare_150_free_form_gemma_playground`,
  `duecare_155_tool_calling_playground`,
  `duecare_160_image_processing_playground` all missing a final summary
  code cell. Pre-existing, unrelated to this session's work.

## Notebooks that still need further review

### Dedicated builders, canonical rewrite pending

- `230 DueCare Gemma 4 vs Mistral Family`: only the plotly fill was
  fixed; still carries em-dash H1, `| | |` markdown pseudo-table, no
  HTML header, no HTML troubleshooting, hardener default final print.
- `240 DueCare Gemma 4 vs Frontier Cloud Models`: same list.
- `270 DueCare Gemma 2 vs 3 vs 4 Safety Gap`: same list; also needs
  live `gemma_baseline_findings.json` load so the V3 band is not a
  hardcoded placeholder.

### Shared builders, canonical rewrite pending

- `250 DueCare Anchored Grading vs Reference Responses` inside
  `scripts/build_grading_notebooks.py` (`NB11_CELLS`). Shared builder
  also emits `310`, `410`, `420`, `430`; any edit must rebuild all
  siblings and run `scripts/validate_notebooks.py`.
- `260 DueCare Plain vs Retrieval-Augmented vs System-Guided` inside
  `scripts/build_showcase_notebooks.py` (`RAG_CELLS`). Shared builder
  also emits `300`, `400`, `500`; same blast-radius discipline.

### Validator failures still open

- `150 Free Form Gemma Playground`
- `155 Tool Calling Playground`
- `160 Image Processing Playground`

Each needs a final summary code cell added by its builder. Three-file
repair required before `42 of 42 OK` can be claimed in the writeup.

### Not yet touched in canonical style

- `300 Adversarial Resistance` (shared showcase builder).
- `310 Prompt Factory` (shared grading builder).
- `320 Finding Gemma 4 Safety Line` (dedicated builder
  `scripts/build_notebook_320_supergemma_safety_gap.py`).
- `400 Function Calling and Multimodal` (shared showcase builder).
- `410 LLM Judge Grading` (shared grading builder).
- `420 Conversation Testing` (shared grading builder).
- `430 Rubric Evaluation` (shared grading builder).
- `440 Per-Prompt Rubric Generator`, `450 Contextual Worst Response
  Judge`.
- `499` Advanced Evaluation Conclusion recap.
- `500 Agent Swarm Deep Dive` (shared showcase builder).
- `510 Phase 2 Model Comparison`, `520 Phase 3 Curriculum Builder`,
  `530 Phase 3 Unsloth Finetune`, `599` conclusion.
- `600 Results Dashboard`, `610 Submission Walkthrough`, `699`, `799`,
  `899` conclusions.

## Next immediate action when Kaggle cap resets

```
$env:PYTHONIOENCODING = "utf-8"
$env:KAGGLE_API_TOKEN = "KGAT_cae9959f7adc60ceb6d52746bd3fd807"
kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
kaggle kernels push -p kaggle/kernels/duecare_005_glossary
kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
```

If `130` or `399` continue to return `Notebook not found` after the
cap reset, drop the `NNN-` prefix in `KERNEL_ID` to match the
title-derived slug Kaggle auto-creates, rebuild, retry once.

## Known risks carried forward

- `210` live slug is non-canonical (`duecare-gemma-vs-oss-comparison`).
  Every cross-link in `130`, `200`, `220`, `299`, `399`, index,
  glossary uses that slug via `PUBLIC_SLUG_OVERRIDES`. A future
  slug-normalization pass must not drop that override.
- `220` and `130` first-time push may keep failing with `Notebook not
  found` if Kaggle cannot resolve the canonical NNN-prefixed slug.
  Fallback: adopt the title-derived slug Kaggle auto-creates.
- `150`, `155`, `160` still block a clean 42-of-42 validator pass.
- `130` walk-through renders best-grade only when
  `taylorsamarel/duecare-trafficking-prompts` is not attached;
  screenshots for the video must come from a run with that dataset
  attached.
- Shared-builder blast radius on `250` and `260` requires rebuilding
  every sibling on every edit; do not edit a single cells block in
  isolation.
- `configs/duecare/domains/trafficking/seed_prompts.jsonl` (74,567
  rows) lives under `configs/`. Verify `.gitignore` coverage before
  any PR so the full proprietary corpus is not published by accident.
