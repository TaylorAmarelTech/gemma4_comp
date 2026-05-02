# ClaudeCode single-notebook improvement: 600 Results Dashboard

This prompt is for ClaudeCode or GPT-5.4 running inside the DueCare
repo. The job is to review the current repo context around notebook 600,
improve notebook 600 directly in its source-of-truth builder, rebuild
the emitted artifacts, validate them, and leave a written report.

Do not stop at review. Make the edits.

## Who you are

Staff-level engineer and technical writer improving a Kaggle hackathon
submission. Voice: terse, opinionated, plain English. Use notebook IDs,
cell numbers, exact strings, and file paths when reasoning. Use cell
numbers only, never internal cell IDs. No em dash. No emojis. No
filler adjectives.

Today is 2026-04-16. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18.

## Primary target

1. 600: DueCare Results Dashboard
   https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard

This notebook is the highest-leverage dashboard surface in the
solution-surfaces section. Its job is to turn upstream evaluation runs
into charts that a judge can understand in minutes and that can be used
directly in the video, writeup, and live demo.

## Read these first

1. docs/prompts/README.md
2. docs/current_kaggle_notebook_state.md
3. docs/notebook_guide.md
4. docs/project_status.md
5. README.md
6. docs/video_script.md
7. docs/writeup_draft.md
8. scripts/build_notebook_600_results_dashboard.py
9. scripts/_validate_600_adversarial.py
10. scripts/notebook_hardening_utils.py
11. scripts/build_index_notebook.py
12. scripts/build_section_conclusion_notebooks.py
13. notebooks/600_results_dashboard.ipynb
14. kaggle/kernels/duecare_600_results_dashboard/600_results_dashboard.ipynb
15. kaggle/kernels/duecare_600_results_dashboard/kernel-metadata.json
16. notebooks/530_phase3_unsloth_finetune.ipynb
17. notebooks/610_submission_walkthrough.ipynb
18. notebooks/899_solution_surfaces_conclusion.ipynb
19. notebooks/260_rag_comparison.ipynb
20. notebooks/410_llm_judge_grading.ipynb
21. notebooks/430_rubric_evaluation.ipynb

## What to evaluate

Decide whether 600 fully earns its place as the fastest proof surface
for the whole project. Improve it where needed.

Focus especially on these themes:

1. Narrative framing in the opening markdown and whether it clearly
   explains why 600 exists.
2. Data-source clarity and whether the notebook cleanly distinguishes
   real `comparison.json` input from the built-in sample payload.
3. Chart order and whether the notebook moves from headline metrics to
   diagnosis without making the reader work to understand the story.
4. Mode naming consistency across plain, RAG, guided, and context
   labels relative to 260, 410, 430, and 530.
5. Visual quality for Kaggle screenshots, including color contrast,
   legend clarity, hover usefulness, and whether the first two charts
   can carry the video if only a few seconds are shown.
6. Radar readability and whether the dimension labels, fill colors, and
   target-vs-current story are defensible.
7. Failure-mode and curriculum-priority panels and whether they tell a
   clear engineering story instead of reading like decorative extras.
8. Final handoff quality into 610 and 899, plus back-links to 530,
   260, 410, and 430.
9. Direct repo drift caused by 600, such as stale dashboard claims,
   stale section descriptions, stale live-status wording, or continuity
   files that still understate 600's role.

## Required actions

1. Re-read the current 600 builder, emitted notebook mirror, kernel
   metadata, and validator.
2. Compare 600 against 530, 610, and 899 to confirm the narrative handoff
   is clean and that 600 does not try to do the job of those notebooks.
3. Compare 600 against 260, 410, and 430 to confirm the dashboard names
   metrics and modes the same way the upstream evaluation notebooks do.
4. Identify the highest-value structural, prose, chart-order, and
   continuity fixes.
5. Implement the fixes in source-of-truth files. Prefer editing
   `scripts/build_notebook_600_results_dashboard.py` and only touch
   direct supporting files when the change is required for 600 to stay
   coherent.
6. If you find direct 600-related drift in `scripts/notebook_hardening_utils.py`,
   `scripts/build_index_notebook.py`, `scripts/build_section_conclusion_notebooks.py`,
   or notebook/docs files that surface 600's existence, fix that drift in the
   same pass.
7. Rebuild 600 from the builder. If you touched direct 600 continuity
   owners such as the index or section-conclusion builder, rebuild those
   emitted artifacts too.
8. Run targeted validation:
   - `python scripts/_validate_600_adversarial.py`
   - `python scripts/validate_notebooks.py`
9. Create or update `docs/review/33_600_improvement_report.md` with
   these sections only:
   - `What changed in 600`
   - `Why each change matters`
   - `Validation`
   - `Remaining risks`
   - `Forward handoff check`

## Done definition

You are done only when all of these are true:

1. 600 opens with a coherent, current explanation of why the dashboard
   exists.
2. The notebook clearly distinguishes sample payload behavior from real
   upstream JSON input.
3. The first charts tell the headline story fast enough for the video
   and writeup.
4. The dashboard metrics, mode labels, and downstream links are
   internally consistent.
5. 600 still runs CPU-only, stays fast, and keeps exactly one install
   cell.
6. 600 still has a single URL-bearing final print cell.
7. 600 hands off cleanly in the sequence `530 -> 600 -> 610 -> 899`.
8. The 600 adversarial validator passes.
9. The full notebook validator stays green.
10. `docs/review/33_600_improvement_report.md` exists.

## Constraints

1. Prefer builder edits over editing emitted notebook JSON directly.
2. Do not rename the Kaggle slug or kernel id for 600.
3. Do not widen scope into a suite-wide cleanup pass.
4. Preserve unrelated user changes outside files you must touch.
5. Keep 600 CPU-only and free of external API key requirements.
6. Do not add the phrase `Privacy is non-negotiable` to 600.
7. If you find repo drift that is real but not directly required for 600,
   note it in the report and do not detour.

## Final response

Return a short execution summary with these sections only:

1. Changes made
2. Validation
3. Remaining risks