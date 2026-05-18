# Claude Code Prompt: Bulk File Review Demo And UX Verification

You are Claude Code working in:

```text
C:\Users\amare\OneDrive\Documents\gemma4_comp
```

Your task is to review and improve the Bulk File Review demo path. Treat this
as a demo-critical workflow, not a cosmetic pass.

## Context

Bulk File Review lives at:

- `packages/duecare-llm-chat/src/duecare/chat/static/process.html`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/prompts.py`
- `scripts/build_static_samples.py`
- `packages/duecare-llm-chat/src/duecare/chat/static/samples/`

North-star contract:

- `docs/bulk_file_review_north_star.md`

## Goal

Verify and improve the live demo sequence:

1. Use `case_files_streamlined_demo.zip`.
2. Process the bundle with a visible loading/progress path.
3. Inspect extracted graph intelligence.
4. Mark the review gate complete.
5. Run the optional local Gemma 4 edge pass with its own progress timeline.
6. Ask graph questions and receive row/path/evidence-grounded answers.

## Critical Requirements

- Deterministic processing must not require a model.
- Deterministic graph chat must not require a model.
- The model selector must not open unless the user explicitly chooses model-backed work that truly requires a loaded model.
- If no model is loaded, the Gemma edge pass must report `deterministic_no_model` and keep deterministic edges visible.
- Activity log must show start, poll events, completion, errors, and fallbacks.
- The UI must distinguish:
  - processing complete
  - OCR/media queued
  - Gemma edge pass queued/running/complete/fallback
  - review gate complete
  - graph answer ready
- Long status strings, paths, row IDs, and trace details must stay inside their cards.
- The streamlined sample must remain synthetic and small.

## Verification Commands

Run focused checks first:

```powershell
python scripts/build_static_samples.py
python -m py_compile scripts/build_static_samples.py packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py
pytest packages/duecare-llm-chat/tests/test_static_sample_bundles.py packages/duecare-llm-chat/tests/test_process_bulk_review.py packages/duecare-llm-chat/tests/test_harness_workbench.py tests/test_route_contract.py -q -p no:cacheprovider
```

If the environment has browser tooling available, also perform a real UI pass:

1. Open `/static/process.html`.
2. Click `Use streamlined demo`.
3. Click `Start processing`.
4. Confirm the progress bar and Activity log update with server events.
5. Confirm Step 3.
6. Click `Run local Gemma edge pass`.
7. Confirm the edge-pass progress box updates and either model edges or deterministic fallback appears.
8. Ask: `Which rows support fee camouflage and restricted provider choice?`
9. Confirm the graph-chat progress box updates and the answer cites evidence.

## What To Fix If Found

- Any automatic model popup during deterministic processing or deterministic graph chat.
- Any button whose label implies processing when it only records a review decision.
- Any progress bar that jumps to 100% while implying OCR/Gemma media work completed.
- Any stale `No activity yet` line after log events.
- Any clipped/overflowing text in workflow cards, trace cards, tables, logs, graph detail, or progress tiles.
- Any route that blocks the workflow when no model is loaded despite deterministic fallback being available.

## Deliverable

Make minimal, targeted code/test/doc edits. In your final response, report:

- files changed
- commands run
- whether the streamlined demo path is fully wired
- any remaining risk or follow-up
