# Prompt 03. Advanced model testing and evaluation (bands 400 to 590)

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
> This prompt covers large-scale evaluation, enhanced cross-model
> evaluation, and the self-learning adversarial harness. Read
> `docs/prompts/_shared_discipline.md` first.

---

## Scope

Cover bands 400 through 590 only.

| Band | Section | What this prompt owns |
|---|---|---|
| 400 to 490 | Large-scale evaluation | Full-corpus Gemma 4 eval, full-corpus cross-model eval, enhanced variants (prompt engineering, context, RAG), per-section summary. |
| 500 to 590 | Adversarial | Self-learning harness that finds boundaries, injects obfuscation, uses other LLMs to craft jailbreaks. Gemma 4 alone, vs other models, enhanced with context and RAG. |

Band 300 data pipeline must already be complete: this band consumes
the training-ready JSONL and the full 74K prompt corpus. Fine-tuning
(band 700) runs after this band and is out of scope for this prompt.

## Coverage targets (must each be satisfied across bands 400 to 590)

Band 400 to 490:

1. **Full-corpus Gemma 4 evaluation, plain.** Run Gemma 4 E4B
   against the full graded corpus. Report n, mean, 95% CI,
   per-category breakdown, per-grade breakdown, per-sub-rubric
   breakdown.
2. **Full-corpus Gemma 4, multimodal.** Voice and image sibling of
   1. Inline multimodal or sibling split; defend in one sentence.
3. **Full-corpus vs other models, plain.** Same corpus, same
   rubric, same seed; Gemma 4 vs Llama 3 or 4, Mistral, Qwen,
   GPT-OSS, DeepSeek, and at least one frontier API via
   OpenRouter.
4. **Full-corpus vs other models, enhanced.** Same comparison with
   prompt engineering, retrieval context, and RAG applied
   identically across all models. Variable isolated per notebook.
5. **Ablation notebooks.** Stock vs prompt-engineered vs RAG vs
   fine-tuned (when Phase 3 lands). Each ablation names its
   isolated variable in the header.
6. **Section summary at 490.** Reads cached outputs, produces the
   headline chart that goes into the writeup.

Band 500 to 590:

7. **Self-learning adversarial harness, Gemma 4 alone.** Harness
   discovers boundaries, injects obfuscation (spintax, homoglyph,
   prompt injection patterns), uses secondary LLMs to craft
   jailbreak candidates, and scores success rate. Cite existing
   adversary generators in
   `packages/duecare-llm-tasks/src/duecare/tasks/generators/`.
8. **Self-learning adversarial harness, multimodal.** Voice and
   image sibling of 7. Defend inline vs split.
9. **Self-learning adversarial harness vs other models.** Same
   harness applied across every adapter in
   `packages/duecare-llm-models/`.
10. **Self-learning adversarial harness, enhanced.** With
    prompt engineering, retrieval context, and RAG defensive and
    offensive strategies.
11. **Responsible-disclosure notes.** Any novel jailbreak findings
    include disclosure metadata in the provenance chain. Cite
    `.claude/rules/10_safety_gate.md` for PII and the
    `docs/FOR_JUDGES.md` honesty bar.
12. **Section summary at 590.** Reads cached adversarial outputs,
    produces the headline chart and paragraph (for example,
    attack-success-rate by category and by model).

## Source of truth for kernel state

`docs/current_kaggle_notebook_state.md` is authoritative. Use the
Kaggle id from that file when referring to a kernel. Legacy
directory-to-code-file aliases for kernels placed in bands 400 to
590 must be resolved by the renumber pass (for example,
`duecare_06_adversarial` contains `06_adversarial_resistance.ipynb`,
`duecare_08_fc_multimodal` contains
`08_function_calling_multimodal.ipynb`,
`duecare_11_comparative` contains
`11_comparative_grading.ipynb`,
`duecare_14_dashboard` contains `14_results_dashboard.ipynb`,
`duecare_15_ollama_cloud` contains
`15_ollama_cloud_comparison.ipynb`,
`duecare_16_mistral_family` contains
`16_mistral_family_comparison.ipynb`,
`duecare_17_openrouter_frontier` contains
`17_openrouter_frontier_comparison.ipynb`,
`duecare_20_contextual_judge` contains
`20_contextual_worst_response_judge.ipynb`,
`duecare_phase2_comparison` contains
`phase2_model_comparison.ipynb`). Do not touch
`forge_llm_core_demo.ipynb`; that orphan is owned by prompt 01.

## Current kernels relevant to these bands

- `duecare_06_adversarial_resistance` maps to band 510 or 520.
- `duecare_05_rag_comparison` likely maps to band 440 or 450
  (enhanced eval), or stays in band 200 if intentionally small-
  scale. Decide.
- `duecare_14_results_dashboard` partly overlaps with 490 summary
  and partly with band 900 meta rollup. Split.
- `duecare_18_supergemma_safety_gap` consumes fine-tune output
  (band 700) and reports a gap; it sits in band 480 or 790. Decide.
- `duecare_11_comparative`, `duecare_15_ollama_cloud`,
  `duecare_16_mistral_family`, `duecare_17_openrouter_frontier`
  already cover cross-model comparisons; decide whether they stay
  in band 200 (sample) or move to band 400 (full-corpus).
- `duecare_08_fc_multimodal` contributes a multimodal adversarial
  surface; decide band 450 or 520.

For every current kernel decision, cite `path:line` in the notebook
that justifies the band placement (size of corpus used, presence
of enhancement, presence of adversarial logic).

## Deliverable, produce `docs/review/400-590_advanced_eval_and_adversarial.md`

Sections 0 through 5 in order. Cite `path:line` for every factual
claim. Maximum 2,500 words.

### Section 0. Band scope and grounding (at most 200 words)

State what these bands cover and what they do not. Confirm the
packages vs notebooks boundary: adversarial generators live in
`duecare.tasks.generators`, scoring in `duecare.tasks.base`,
multi-model orchestration in `duecare.workflows`. Notebooks
orchestrate and visualize; they do not re-implement adversarial
mutation or scoring inline.

### Section 1. Per-notebook audit of kernels placed in bands 400 to 590

For each kernel, fill the Principle B header checklist plus:

- Corpus size used (exact number of prompts).
- Which models were included and which adapter paths.
- Whether the enhancement (prompt engineering, context, RAG) is
  applied identically across models or asymmetrically.
- Whether the notebook reports n, mean, 95% CI, per-category
  breakdown. If not, flag.
- For adversarial notebooks: which mutations were used, which
  secondary LLMs crafted jailbreaks, and whether responsible-
  disclosure metadata is attached.

Compact table, one row per kernel.

### Section 2. Target section map for bands 400 to 590

Two sections. For each:

- Scope in one sentence.
- Rubric dimensions advanced.
- Summary notebook narrative goal.
- Insertion slots currently free.
- Sub-bands if useful (for example, "410 to 440 plain and enhanced
  eval vs self and others, 450 to 470 ablations, 480 to 490
  rollup"; "510 to 530 harness vs Gemma alone and multimodal, 540
  to 560 vs other models and enhanced, 570 to 580 responsible
  disclosure, 590 summary").

### Section 3. Full notebook table for both bands

Columns as in shared discipline. Every coverage target 1 through 12
must appear as a row. Every current kernel placed in these bands
must be mapped, moved, or marked delete with reason.

Append:

- `git mv` block.
- `kernel-metadata.json` id edits.
- Build-script names for every gap row.

### Section 4. Ablation discipline check

For each ablation notebook (coverage target 5), state:

- The isolated variable in one sentence.
- The held-constant factors (seed, corpus version, model version,
  hardware).
- The statistical reporting required (n, mean, 95% CI or
  bootstrap, per-category breakdown).
- The paired comparison used if any (for example, same prompt on
  stock vs enhanced Gemma 4).
- The exact cached-output path the 490 summary notebook reads.

This section enforces award-winning research standards.

### Section 5. Ticket list for these bands

Flat, one per line, at most 120 characters, ordered P0 to P2.

```
[P0][M][Tech][Ablation] Insert isolated-variable header into duecare_440_vs_others_enhanced
[P0][S][Repro] Pin seed and corpus version across duecare_410 through 480
[P0][L][Impact][Adversarial] Build duecare_520_self_learning_harness_gemma4
[P0][M][Video][Summary] Build duecare_490_summary reading cached outputs
[P0][M][Tech][Safety] Attach responsible-disclosure metadata to adversarial notebooks
...
```

Include tickets for:

- Every missing statistical report (n, CI, breakdown).
- Every adversarial notebook missing disclosure metadata.
- Every full-corpus eval missing an identical-enhancement control.
- The 490 and 590 summary notebooks.
- The 18 supergemma safety-gap notebook's band placement decision.

## Constraints specific to this prompt

- Do not design data-pipeline notebooks here. Route to band 300.
- Do not design implementation or demo notebooks here. Route to
  band 800.
- Every full-corpus eval notebook pins seed, corpus version
  (by dataset-version), and model version.
- Every cross-model notebook uses identical prompts and identical
  scoring across models. Asymmetric enhancement is a bug.
- Every adversarial notebook states its threat model in the header
  and its responsible-disclosure posture.
- Every ablation names its isolated variable in one sentence in
  the header.

## Read before writing, in order, stop when grounded

1. `docs/current_kaggle_notebook_state.md`.
2. `docs/prompts/_shared_discipline.md`.
3. `docs/FOR_JUDGES.md` for the honesty and reproducibility bars.
3. `packages/duecare-llm-tasks/src/duecare/tasks/generators/` (full
   folder).
4. `packages/duecare-llm-tasks/src/duecare/tasks/base/` scoring.
5. `packages/duecare-llm-agents/src/duecare/agents/adversary/`.
6. `packages/duecare-llm-models/src/duecare/models/` (all eight
   adapters).
7. `kaggle/kernels/duecare_05_rag_comparison/`.
8. `kaggle/kernels/duecare_06_adversarial/06_adversarial_resistance.ipynb`.
9. `kaggle/kernels/duecare_08_fc_multimodal/`.
10. `kaggle/kernels/duecare_11_comparative/`.
11. `kaggle/kernels/duecare_14_dashboard/`.
12. `kaggle/kernels/duecare_15_ollama_cloud/`,
    `duecare_16_mistral_family/`,
    `duecare_17_openrouter_frontier/`.
13. `kaggle/kernels/duecare_18_supergemma_safety_gap/`.
14. `configs/duecare/domains/trafficking/rubrics/` (all five
    sub-rubrics).
15. `.claude/rules/10_safety_gate.md`.

## Output

Single file at
`docs/review/400-590_advanced_eval_and_adversarial.md`. Sections 0
through 5 in order.
