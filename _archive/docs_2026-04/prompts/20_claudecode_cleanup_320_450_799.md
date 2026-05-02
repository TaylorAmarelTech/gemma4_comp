# ClaudeCode cleanup: 320, 450, 799

This prompt is for ClaudeCode running inside the DueCare repo. The job
is to clean up the Adversarial Prompt-Test Evaluation section,
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

1. 320: DueCare Red-Team Safety Gap
   https://www.kaggle.com/code/taylorsamarel/320-duecare-red-team-safety-gap
2. 450: DueCare Contextual Worst-Response Judge
   https://www.kaggle.com/code/taylorsamarel/450-duecare-contextual-worst-response-judge
3. 799: DueCare Adversarial Prompt-Test Evaluation Conclusion
   https://www.kaggle.com/code/taylorsamarel/799-duecare-adversarial-prompt-test-evaluation-conclusion

## Context-only checkpoints

Read these for continuity, but do not edit them unless a tiny fix is
required to prevent a direct contradiction:

1. 699: DueCare Advanced Prompt-Test Generation Conclusion
   https://www.kaggle.com/code/taylorsamarel/699-duecare-advanced-prompt-test-generation-conclusion
2. 300: DueCare Adversarial Resistance Against 15 Attack Vectors
   https://www.kaggle.com/code/taylorsamarel/300-duecare-adversarial-resistance-against-15-attack-vectors
3. 440: DueCare Per-Prompt Rubric Generator
   https://www.kaggle.com/code/taylorsamarel/440-duecare-per-prompt-rubric-generator

## Source-of-truth files to inspect first

- scripts/build_notebook_320_supergemma_safety_gap.py
- scripts/build_notebook_450_contextual_worst_response_judge.py
- scripts/build_section_conclusion_notebooks.py
- notebooks/320_supergemma_safety_gap.ipynb
- notebooks/450_contextual_worst_response_judge.ipynb
- notebooks/799_adversarial_prompt_test_evaluation_conclusion.ipynb

Important: these files have seen recent local edits. Re-read the current
contents before changing anything, especially 320 and the shared section
conclusion builder.

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
- Make the reader understand what was attacked, how it was scored, and
  why the result matters.

## Required actions

1. Re-read the current source files in scope.
2. Fix the major reader-facing and builder-level issues directly.
3. Normalize continuity from 699 into 320 and from 450 into 799.
4. Rebuild the affected notebooks.
5. Run targeted validation on 320, 450, and 799.
6. Confirm the section now reads like a real adversarial evaluation arc
   rather than two isolated experiments plus a conclusion.

## Done definition

You are done only when all notebooks in scope satisfy these checks:

- Header block is coherent and current.
- Install cell is pinned and consistent.
- Final cell gives a strong next-step handoff.
- Narrative flow across 320 -> 450 -> 799 makes sense.
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
