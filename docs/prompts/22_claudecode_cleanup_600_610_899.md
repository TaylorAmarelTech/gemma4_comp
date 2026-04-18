# ClaudeCode cleanup: 600, 610, 899

This prompt is for ClaudeCode running inside the DueCare repo. The job
is to clean up the Solution Surfaces ending of the notebook suite,
implement fixes directly, rebuild the affected artifacts, and validate
the outputs.

Do not stop at review. Make the edits.

## Who you are

Staff-level engineer and technical writer cleaning a Kaggle hackathon
submission. Voice: terse, opinionated, plain English. Use notebook IDs,
cell numbers, exact strings, and file paths when reasoning. Use cell
numbers only, never internal cell IDs. No em dashes. No emojis. No
filler adjectives.

Today is 2026-04-16. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18.

## Primary scope

Clean these notebooks completely:

1. 600: DueCare Results Dashboard
   https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard
2. 610: DueCare End-to-End Submission Walkthrough
   https://www.kaggle.com/code/taylorsamarel/610-duecare-end-to-end-submission-walkthrough
3. 899: DueCare Solution Surfaces Conclusion
   https://www.kaggle.com/code/taylorsamarel/899-duecare-solution-surfaces-conclusion

## Context-only checkpoints

Read these for continuity, but do not edit them unless a tiny fix is
required to prevent a direct contradiction:

1. 010: DueCare Quickstart in 5 Minutes
   https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes
2. 400: DueCare Gemma 4 Native Tool Calls and Multimodal
   https://www.kaggle.com/code/taylorsamarel/400-duecare-gemma-4-native-tool-calls-and-multimodal
3. 450: DueCare Contextual Worst-Response Judge
   https://www.kaggle.com/code/taylorsamarel/450-duecare-contextual-worst-response-judge
4. 500: DueCare 12-Agent Gemma 4 Safety Swarm
   https://www.kaggle.com/code/taylorsamarel/500-duecare-12-agent-gemma-4-safety-swarm
5. 599: DueCare Model Improvement Opportunities Conclusion
   https://www.kaggle.com/code/taylorsamarel/599-duecare-model-improvement-opportunities-conclusion

## Source-of-truth files to inspect first

- scripts/build_kaggle_notebooks.py
- scripts/build_section_conclusion_notebooks.py
- notebooks/600_results_dashboard.ipynb
- notebooks/610_submission_walkthrough.ipynb
- notebooks/899_solution_surfaces_conclusion.ipynb

There may not be a dedicated builder for 600. Search first. If there is
no real source-of-truth builder, edit the notebook carefully and note
that in the final summary.

Important: `notebooks/600_results_dashboard.ipynb` has recent local
changes. Re-read the current contents before changing anything.

## Shared conventions to enforce

- Canonical title format: `NNN: DueCare <Descriptive Title>`.
- HTML tables with fixed column widths in the header block.
- First code cell pins DueCare packages at `0.1.0` with wheel fallback.
- Final visible code cell is a single `print(...)` handoff line.
- Pipeline position links are full Kaggle URLs.
- No stale notebook numbers, stale section names, or contradictory
  runtime claims.
- Add a troubleshooting table near the end when the notebook is
  runnable.
- Make the ending feel like a real product surface, not a loose appendix.

## Required actions

1. Re-read the current source files in scope.
2. Fix the major reader-facing and builder-level issues directly.
3. Normalize continuity from 599 into 600, then into 610, then into 899.
4. Rebuild the affected notebooks.
5. Run targeted validation on 600, 610, and 899.
6. Confirm the closing arc clearly answers: what ships, who uses it,
   and why the solution is credible.

## Done definition

You are done only when all notebooks in scope satisfy these checks:

- Header block is coherent and current.
- Install cell is pinned and consistent.
- Final cell gives a strong next-step handoff.
- Narrative flow across 600 -> 610 -> 899 makes sense.
- Emitted notebook and Kaggle kernel copy match where generated.
- Targeted validator passes for every notebook in scope.

## Constraints

- Prefer editing builders over editing generated notebook JSON.
- Do not rename Kaggle IDs or slugs.
- Do not rebuild unrelated notebooks.
- Do not stop at a findings list. Land the fixes.

## Final response

Return a short execution summary with these sections only:

1. Changes made
2. Validation
3. Remaining risks
