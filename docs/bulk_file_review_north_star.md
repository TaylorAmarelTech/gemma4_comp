# Bulk File Review North Star

Bulk File Review is the local case-intake and evidence-graph demo for DueCare.
It must feel like a working investigation surface, not a generic file uploader.

## Core Promise

The user can upload a case bundle, watch local processing happen, inspect the
extracted graph, optionally run a local Gemma 4 edge pass, and ask questions
against the confirmed graph without any remote service requirement.

## Non-Negotiables

1. Local deterministic processing must work without a loaded model.
2. The page must never open the model selector for deterministic processing or deterministic graph chat.
3. Every long-running operation must show a visible progress surface and Activity log events.
4. The review gate must be clearly labeled as a reviewer confirmation step, not as processing.
5. Optional Gemma 4 work must be explicit: queued, running, complete, failed, or deterministic fallback.
6. Graph-chat must return a useful deterministic answer for common demo questions even when no model is loaded.
7. Every answer and extracted insight should point back to row IDs, paths, edge IDs, people, dates, payments, or document types.
8. Text must stay inside cards, trace boxes, tables, and log containers on mobile and desktop.
9. Sample bundles must be synthetic, judge-safe, and small enough for reliable Kaggle demos.
10. Exports must preserve reviewer notes and the local-only trust boundary.

## Demo Path

The primary short demo is `case_files_streamlined_demo.zip`.

Expected live path:

1. Click `Use streamlined demo`.
2. Click `Start processing`.
3. Watch server-side processing progress and Activity log events.
4. Inspect extracted people, payments, document types, journey points, typed edges, and graph.
5. Click `Mark review complete`.
6. Click `Run local Gemma edge pass`.
7. Watch the separate Gemma edge-pass progress timeline.
8. Ask a graph question such as:
   `Which rows support fee camouflage and restricted provider choice?`
9. Confirm the answer cites row/path evidence or clearly reports deterministic fallback.

## Evidence And Edge Quality

Bulk File Review should extract and display:

- document inventory
- parent/child rows or pages
- people and case IDs
- payment amounts and currencies
- locations and travel stages
- document types
- journey stages
- GREP and risk signals
- evidence edges
- typed graph edges
- RAG/KnowledgeObject candidates
- media/OCR/Gemma vision queue state

Good edge candidates name both relationship and evidence:

- `fee_camouflage_evidence`
- `salary_deduction_evidence`
- `provider_choice_restriction`
- `affiliate_or_common_control_signal`
- `document_control_signal`
- `retaliation_or_blacklist_signal`
- `journey_stage_observation`

## UX Rules

- No hidden model calls.
- No generic spinner without a current stage label.
- No final `100%` state that implies OCR/Gemma vision completed when those are only queued.
- No status strings such as `implemented_for_text_and_extractable_pdfs` as primary visible labels.
- No clipped paths, row IDs, source-node IDs, or trace details.
- Buttons that start model work must say so.
- Buttons that only confirm review must say so.
- Activity log must clear its idle line on first event.

## Acceptance Checks

Minimum verification before a demo:

- `/static/process.html` renders the guided demo path.
- The streamlined sample downloads and processes.
- `/api/process/batch/start` and `/api/process/batch/status/{job_id}` emit progress and events.
- `/api/process/graph-extract/start` and `/api/process/graph-extract/status/{job_id}` emit progress and events.
- `/api/process/graph-chat` answers common questions without requiring a loaded model.
- The edge pass returns `deterministic_no_model` instead of forcing a model popup when no model is loaded.
- Review confirmation unlocks graph chat/export and logs that no model call was started.
- Tests cover the streamlined sample, async process job, async edge job, and static UI contract.
