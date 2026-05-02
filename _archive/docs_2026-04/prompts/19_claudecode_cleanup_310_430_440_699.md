# ClaudeCode cleanup: 310, 430, 440, 699

This prompt is for ClaudeCode running inside the DueCare repo. The job
is to clean up the Advanced Prompt-Test Generation section, implement
fixes directly, rebuild the affected artifacts, and validate the
outputs.

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

1. 310: DueCare Adversarial Prompt Factory
   https://www.kaggle.com/code/taylorsamarel/310-duecare-adversarial-prompt-factory
2. 430: DueCare 54-Criterion Pass/Fail Rubric Evaluation
   https://www.kaggle.com/code/taylorsamarel/430-duecare-54-criterion-pass-fail-rubric-evaluation
3. 440: DueCare Per-Prompt Rubric Generator
   https://www.kaggle.com/code/taylorsamarel/440-duecare-per-prompt-rubric-generator
4. 699: DueCare Advanced Prompt-Test Generation Conclusion
   https://www.kaggle.com/code/taylorsamarel/699-duecare-advanced-prompt-test-generation-conclusion

## Context-only checkpoints

Read these for continuity, but do not edit them unless a tiny fix is
required to prevent a direct contradiction:

1. 499: DueCare Advanced Evaluation Conclusion
   https://www.kaggle.com/code/taylorsamarel/499-duecare-advanced-evaluation-conclusion
2. 300: DueCare Adversarial Resistance Against 15 Attack Vectors
   https://www.kaggle.com/code/taylorsamarel/300-duecare-adversarial-resistance-against-15-attack-vectors
3. 410: DueCare Six-Dimension LLM Judge Grading
   https://www.kaggle.com/code/taylorsamarel/410-duecare-six-dimension-llm-judge-grading

## Source-of-truth files to inspect first

- scripts/build_grading_notebooks.py
- scripts/build_notebook_440_per_prompt_rubric_generator.py
- scripts/build_section_conclusion_notebooks.py
- notebooks/310_prompt_factory.ipynb
- notebooks/430_rubric_evaluation.ipynb
- notebooks/440_per_prompt_rubric_generator.ipynb
- notebooks/699_advanced_prompt_test_generation_conclusion.ipynb

There may not be a dedicated builder for 310. Search first. If there is
no real source-of-truth builder, edit the notebook carefully and note
that in the final summary.

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
- Make the section read like generation work, not a second copy of the
  evaluation section.

## Required actions

1. Re-read the current source files in scope.
2. Fix the major reader-facing and builder-level issues directly.
3. Normalize continuity from 499 into 310 and from 440 into 699.
4. Rebuild the affected notebooks.
5. Run targeted validation on 310, 430, 440, and 699.
6. Confirm the section now makes it obvious how generated prompts and
   rubrics feed later adversarial and fine-tuning work.

## Done definition

You are done only when all notebooks in scope satisfy these checks:

- Header block is coherent and current.
- Install cell is pinned and consistent.
- Final cell gives a strong next-step handoff.
- Narrative flow across 310 -> 430 -> 440 -> 699 makes sense.
- Emitted notebook and Kaggle kernel copy match where generated.
- Targeted validator passes for every notebook in scope.

## Constraints

- Prefer editing builders over editing generated notebook JSON.
- If a notebook has no discoverable builder, search first, then edit the
  notebook only if there is no better source of truth.
- Do not rename Kaggle IDs or slugs.
- Do not rebuild unrelated notebooks.
- Do not stop at a findings list. Land the fixes.

## Final response

Return a short execution summary with these sections only:

1. Changes made
2. Validation
3. Remaining risks
