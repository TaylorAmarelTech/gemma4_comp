# ClaudeCode single-notebook improvement: 140 Evaluation Mechanics

This prompt is for ClaudeCode or GPT-5.4 running inside the DueCare
repo. The job is to review the current repo context around notebook 140,
improve notebook 140 directly in its source-of-truth builder, rebuild
the emitted artifacts, validate them, and leave a written report.

Do not stop at review. Make the edits.

## Who you are

Staff-level engineer and technical writer improving a Kaggle hackathon
submission. Voice: terse, opinionated, plain English. Use notebook IDs,
cell numbers, exact strings, and file paths when reasoning. Use cell
numbers only, never internal cell IDs. No em dashes. No emojis. No
filler adjectives.

Today is 2026-04-16. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18.

## Primary target

1. 140: DueCare Evaluation Mechanics
   https://www.kaggle.com/code/taylorsamarel/duecare-140-evaluation-mechanics

This notebook is the scoring-mechanics bridge between 130 Prompt Corpus
Exploration and 299 Baseline Text Evaluation Framework Conclusion. Its
job is to make the rubric machinery legible before readers hit the
scored comparison notebooks.

## Read these first

1. docs/prompts/README.md
2. docs/current_kaggle_notebook_state.md
3. docs/notebook_guide.md
4. docs/project_status.md
5. README.md
6. scripts/build_notebook_140_evaluation_mechanics.py
7. scripts/_validate_140_adversarial.py
8. scripts/notebook_hardening_utils.py
9. scripts/build_index_notebook.py
10. scripts/build_section_conclusion_notebooks.py
11. scripts/build_notebook_100.py
12. scripts/build_notebook_130_prompt_corpus_exploration.py
13. scripts/build_grading_notebooks.py
14. notebooks/140_evaluation_mechanics.ipynb
15. kaggle/kernels/duecare_140_evaluation_mechanics/140_evaluation_mechanics.ipynb
16. kaggle/kernels/duecare_140_evaluation_mechanics/kernel-metadata.json
17. notebooks/130_prompt_corpus_exploration.ipynb
18. notebooks/250_comparative_grading.ipynb
19. notebooks/299_baseline_text_evaluation_framework_conclusion.ipynb
20. notebooks/410_llm_judge_grading.ipynb
21. notebooks/430_rubric_evaluation.ipynb

## What to evaluate

Decide whether 140 fully earns its place as the bridge notebook between
corpus preparation and scored evaluation. Improve it where needed.

Focus especially on these themes:

1. Narrative framing in the opening markdown and whether it clearly
   explains why 140 exists.
2. Prompt selection quality and whether the chosen example actually
   teaches the scoring mechanics.
3. Scripted candidate realism and whether harmful, hedging, and safe
   responses are cleanly separated.
4. Weighted-rubric calibration and whether the dimension scores feel
   defensible relative to 100, 250, 410, and 430.
5. V3 classifier explanation and whether the banding logic is legible.
6. Radar readability, color contrast, and screenshot quality for Kaggle
   and the writeup.
7. Ownership-table clarity and whether each downstream notebook mapping
   is correct.
8. Troubleshooting rows, final handoff print, and cross-links to 130,
   299, 100, 250, 410, and 430.
9. Direct repo drift caused by 140, such as stale 140 summary strings,
   stale ordering references, or direct claims that still act like 140
   does not exist.

## Required actions

1. Re-read the current 140 builder, emitted notebook mirror, kernel
   metadata, and validator.
2. Compare 140 against 130, 250, 299, 100, 410, and 430 to confirm that
   it explains only what those notebooks assume and does not duplicate
   them unnecessarily.
3. Identify the highest-value structural, prose, and continuity fixes.
4. Implement the fixes in source-of-truth files. Prefer editing
   `scripts/build_notebook_140_evaluation_mechanics.py` and only touch
   direct supporting files when the change is required for 140 to stay
   coherent.
5. If you find direct 140-related drift in `scripts/notebook_hardening_utils.py`,
   `scripts/build_index_notebook.py`, `scripts/build_section_conclusion_notebooks.py`,
   or prompt/docs files that surface 140's existence, fix that drift in the
   same pass.
6. Rebuild 140 from the builder. If you touched direct 140 continuity
   owners such as the index or section-conclusion builder, rebuild those
   emitted artifacts too.
7. Run targeted validation:
   - `python scripts/_validate_140_adversarial.py`
   - `python scripts/validate_notebooks.py`
8. Create or update `docs/review/32_140_improvement_report.md` with
   these sections only:
   - `What changed in 140`
   - `Why each change matters`
   - `Validation`
   - `Remaining risks`
   - `Forward handoff check`

## Done definition

You are done only when all of these are true:

1. 140 opens with a coherent, current explanation of why the notebook
   exists.
2. The example prompt and scripted responses actually teach the scoring
   machinery.
3. The keyword scorer, weighted rubric, V3 classifier, and radar all
   feel internally consistent.
4. 140 still runs CPU-only, stays fast, and keeps exactly one install
   cell.
5. 140 still has a single URL-bearing final print cell.
6. 140 hands off cleanly in the sequence `130 -> 140 -> 299`.
7. The 140 adversarial validator passes.
8. The full notebook validator stays green.
9. `docs/review/32_140_improvement_report.md` exists.

## Constraints

1. Prefer builder edits over editing emitted notebook JSON directly.
2. Do not rename the Kaggle slug or kernel id for 140.
3. Do not widen scope into a suite-wide cleanup pass.
4. Preserve unrelated user changes outside files you must touch.
5. Keep 140 CPU-only and free of external API key requirements.
6. Do not add the phrase `Privacy is non-negotiable` to 140.
7. If you find repo drift that is real but not directly required for 140,
   note it in the report and do not detour.

## Final response

Return a short execution summary with these sections only:

1. Changes made
2. Validation
3. Remaining risks