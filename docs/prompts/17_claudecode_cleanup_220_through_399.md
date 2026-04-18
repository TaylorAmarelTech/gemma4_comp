# ClaudeCode cleanup: 220 through 399

This prompt is for ClaudeCode running inside the DueCare repo. The job
is to clean up the remaining notebooks in the Baseline Text
Comparisons section, implement fixes directly, rebuild the affected
artifacts, and validate the outputs.

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

1. 220: DueCare Gemma 4 vs 6 OSS Models via Ollama Cloud
   https://www.kaggle.com/code/taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud
2. 230: DueCare Gemma 4 vs Mistral Family
   https://www.kaggle.com/code/taylorsamarel/230-duecare-gemma-4-vs-mistral-family
3. 240: DueCare Gemma 4 vs Frontier Cloud Models
   https://www.kaggle.com/code/taylorsamarel/240-duecare-gemma-4-vs-frontier-cloud-models
4. 250: DueCare Anchored Grading vs Reference Responses
   https://www.kaggle.com/code/taylorsamarel/250-duecare-anchored-grading-vs-reference-responses
5. 260: DueCare Plain vs Retrieval-Augmented vs System-Guided
   https://www.kaggle.com/code/taylorsamarel/260-duecare-plain-vs-retrieval-augmented-vs-system-guided
6. 270: DueCare Gemma 2 vs 3 vs 4 Safety Gap
   https://www.kaggle.com/code/taylorsamarel/270-duecare-gemma-2-vs-3-vs-4-safety-gap
7. 399: DueCare Baseline Text Comparisons Conclusion
   https://www.kaggle.com/code/taylorsamarel/399-duecare-baseline-text-comparisons-conclusion

## Context-only checkpoints

Read these for continuity, but do not edit them unless a tiny fix is
required to prevent a direct contradiction:

1. 200: DueCare Cross-Domain Proof
   https://www.kaggle.com/code/taylorsamarel/200-duecare-cross-domain-proof
2. 210: DueCare Gemma 4 vs OSS Models
   https://www.kaggle.com/code/taylorsamarel/210-duecare-gemma-4-vs-oss-models
3. 199: DueCare Free Form Exploration Conclusion
   https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion

## Source-of-truth files to inspect first

- scripts/build_notebook_220_ollama_cloud_comparison.py
- scripts/build_notebook_230_mistral_family_comparison.py
- scripts/build_notebook_240_openrouter_frontier_comparison.py
- scripts/build_notebook_270_gemma_generations.py
- scripts/build_grading_notebooks.py
- scripts/build_showcase_notebooks.py
- scripts/build_section_conclusion_notebooks.py
- notebooks/220_ollama_cloud_comparison.ipynb
- notebooks/230_mistral_family_comparison.ipynb
- notebooks/240_openrouter_frontier_comparison.ipynb
- notebooks/250_comparative_grading.ipynb
- notebooks/260_rag_comparison.ipynb
- notebooks/270_gemma_generations.ipynb
- notebooks/399_baseline_text_comparisons_conclusion.ipynb

If 250 or 260 are generated from a shared builder, edit the shared
builder, not the emitted notebook JSON.

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
- Do not use "judge" language in prose unless the notebook's core
  subject really requires it.

## Required actions

1. Re-read the current builder files and current emitted notebook files.
2. Identify the highest-value structural, prose, and continuity fixes in
   scope.
3. Implement the fixes directly in the source-of-truth builders.
4. Rebuild only the affected notebooks.
5. Run targeted validation on 220, 230, 240, 250, 260, 270, and 399.
6. Confirm that 210 now hands off cleanly into 220, and that 399 closes
   the section honestly.
7. Preserve unrelated user changes outside this scope.

## Done definition

You are done only when all notebooks in scope satisfy these checks:

- Header block is coherent and current.
- Install cell is pinned and consistent.
- Final cell gives a strong next-step handoff.
- Narrative flow across 210 -> 220 -> 230 -> 240 -> 250 -> 260 -> 270
  -> 399 makes sense.
- Emitted notebook and Kaggle kernel copy match.
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
