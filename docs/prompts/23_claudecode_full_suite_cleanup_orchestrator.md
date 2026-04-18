# ClaudeCode cleanup: full-suite orchestrator

This prompt is for ClaudeCode running inside the DueCare repo. The job
is to clean up the entire Kaggle notebook suite by executing the
section-scoped cleanup prompts in order, making code changes, rebuilding
only what changed, and validating the suite at each stage.

Do not stop at analysis. Execute the work.

## Read these prompts first

1. docs/prompts/16_claude_cumulative_review_through_210.md
2. docs/prompts/17_claudecode_cleanup_220_through_399.md
3. docs/prompts/18_claudecode_cleanup_300_400_410_420_499.md
4. docs/prompts/19_claudecode_cleanup_310_430_440_699.md
5. docs/prompts/20_claudecode_cleanup_320_450_799.md
6. docs/prompts/21_claudecode_cleanup_500_510_520_530_599.md
7. docs/prompts/22_claudecode_cleanup_600_610_899.md

## Execution order

Work in this exact order:

1. Through 210 review and cleanup context
2. 220 through 399
3. 300, 400, 410, 420, 499
4. 310, 430, 440, 699
5. 320, 450, 799
6. 500, 510, 520, 530, 599
7. 600, 610, 899

## Global rules

- Edit source-of-truth builders whenever they exist.
- Re-read files that recently changed before editing them.
- Rebuild only the notebooks affected by the current section.
- Validate each section before moving to the next one.
- Preserve unrelated user changes.
- Do not rename Kaggle IDs or slugs.
- Prefer small, defensible fixes over broad speculative rewrites.

## Per-section workflow

For each section:

1. Inspect builder files and emitted notebooks.
2. Identify the highest-value reader-facing and technical fixes.
3. Apply the fixes directly.
4. Rebuild affected notebooks.
5. Run targeted validation for that section.
6. Record anything still blocked or intentionally deferred.

## Full-suite done definition

You are done only when all of the following are true:

- Every notebook in prompts 16 through 22 has been checked in context.
- Every notebook with a fixable structural or continuity issue has been
  updated.
- Generated notebooks and Kaggle kernel copies are synchronized.
- Section conclusions read honestly and hand off cleanly.
- The final suite narrative is coherent from 000 through 899.

## Final response

Return a compact report with these sections only:

1. Sections completed
2. Validation status
3. Remaining blockers
