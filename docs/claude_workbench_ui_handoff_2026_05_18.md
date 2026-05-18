# Claude Workbench UI Handoff - 2026-05-18

This handoff is for Claude Design, Claude Code, or another implementation
agent reviewing the DueCare workbench UI. It focuses on the four recording
surfaces that must feel consistent, local-first, and safe under slow Gemma 4
loads:

- Bulk File Review: `/static/process.html`
- Knowledge Extraction: `/static/knowledge.html`
- Search: `/static/search.html`
- Anonymization & Sharing: `/static/share.html`

The goal is not a visual redesign. The goal is a standardized operator
experience for local deterministic work, optional Gemma 4 jobs, progress,
fallbacks, evidence provenance, and recording-ready state clarity.

## Current Architecture Snapshot

The active Kaggle split is:

| Kernel | Kaggle slug | Purpose |
|---|---|---|
| `01-duecare-exploration-workbench` | `taylorsamarel/duecare-app` | Main operational workbench. Owns chat, process, knowledge, search, share, model picker, replay JSON, and `/static/demo-recording.html`. |
| `02-live-demo` | `taylorsamarel/duecare-live-demo` | Focused judge walkthrough and slides. Owns `/start`, `/slides`, `/slides/setup`, and slide recording APIs. |
| `A-00-omni-experiment-workbench` | `taylorsamarel/duecare-fine-tuning-and-evaluation` | Benchmark, synthetic data, LoRA fine-tuning, grading, and reports. |

Key UI files:

| Surface | File |
|---|---|
| Bulk File Review | `packages/duecare-llm-chat/src/duecare/chat/static/process.html` |
| Knowledge Extraction | `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` |
| Search | `packages/duecare-llm-chat/src/duecare/chat/static/search.html` |
| Anonymization & Sharing | `packages/duecare-llm-chat/src/duecare/chat/static/share.html` |
| Recording checklist | `packages/duecare-llm-chat/src/duecare/chat/static/demo-recording.html` |
| Shared activity log | `packages/duecare-llm-chat/src/duecare/chat/static/_activity_log.js` |
| Shared stepper | `packages/duecare-llm-chat/src/duecare/chat/static/_workflow.js` |
| Shared nav/chrome | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js`, `_chrome.css` |

Key backend files:

| Capability | File |
|---|---|
| Bulk processing, graph chat, Gemma edge pass | `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` |
| Knowledge drafting | `packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py` |
| Anonymization and hub submit | `packages/duecare-llm-chat/src/duecare/chat/harnesses/anonymization/handler.py` |
| Search | `packages/duecare-llm-chat/src/duecare/chat/harnesses/search/handler.py`, `search_safety/handler.py` |

## Important Design Truths

Use these truths consistently in copy and UI state:

1. Deterministic local processing always comes first.
2. Gemma 4 is local and optional. It must be explicit when requested.
3. An upload step should not hide a long model call.
4. Long jobs need visible phase, percent, elapsed time, event history, cancel or abandon control, and deterministic fallback.
5. A completed deterministic pass is not the same as completed OCR, media vision, or Gemma synthesis.
6. Every answer or export should preserve row IDs, file paths, evidence edges, typed edges, or explicit queued-media status.
7. The hub only receives sanitized proposals or anonymized signals after explicit user action.

## Current Risk Areas

These are the most likely sources of user confusion during recording:

- A page says "Gemma" even when only deterministic logic ran.
- A page shows a text-only phase such as `model_or_fallback` without a progress bar.
- A model job appears stuck but there is no cancel or deterministic retry.
- Bulk File Review ranks an `UNKNOWN` bucket above a real case ID.
- Knowledge Extraction lets a large source summary enter Gemma refinement without a strong loading state.
- Anonymization & Sharing makes the Gemma privacy review feel mandatory, when deterministic redaction is the required first control and Gemma is a second local check.
- Search lacks the same step/progress vocabulary as Process, Knowledge, and Share.

## Standard UI Contract

Each of the four pages should use the same mental model:

1. Step panel:
   - Short action title.
   - One-sentence summary.
   - State pill: `Ready`, `Active`, `Done`, `Waiting`, `Failed`, or `Deferred`.
   - Advanced controls collapsed by default.

2. Trust boundary:
   - State exactly what stays local.
   - State exactly when a remote call can happen.
   - Do not say "Gemma reviewed" unless a model call actually ran.

3. Progress box:
   - Stage title.
   - Detail text.
   - Percent label.
   - Horizontal progress bar.
   - Progress note with elapsed time or fallback guidance.
   - Event tiles derived from the backend job event stream.

4. Long-job controls:
   - Primary action starts the job.
   - Secondary action cancels or abandons browser polling.
   - Fallback action reruns deterministic-only path.
   - Cancel language should be "Abandon polling" when the Python worker cannot be safely interrupted.

5. Completion state:
   - Say what completed.
   - Say what did not run.
   - Say what is queued or deferred.
   - Expose replay/export JSON where possible.

## Async Job Contract

Use this contract for any long-running operation:

```json
{
  "job_id": "string",
  "status": "queued | running | complete | error | abandoned",
  "phase": "short_machine_phase",
  "pct": 0,
  "detail": "human readable detail",
  "events": [
    {
      "ts": "2026-05-18T00:00:00Z",
      "status": "running",
      "phase": "parsing",
      "pct": 24,
      "detail": "Enumerating files..."
    }
  ],
  "result": {},
  "late_result": {}
}
```

Preferred route pattern:

| Operation | Start | Status | Cancel or abandon |
|---|---|---|---|
| Bulk process | `POST /api/process/batch/start` | `GET /api/process/batch/status/{job_id}` | `POST /api/process/batch/cancel/{job_id}` |
| Gemma edge pass | `POST /api/process/graph-extract/start` | `GET /api/process/graph-extract/status/{job_id}` | Add only if needed; currently progress exists. |
| Knowledge draft | `POST /api/knowledge/draft-envelope/start` | `GET /api/knowledge/draft-envelope/status/{job_id}` | `POST /api/knowledge/draft-envelope/cancel/{job_id}` |
| Anonymize | `POST /api/anonymize/start` | `GET /api/anonymize/status/{job_id}` | `POST /api/anonymize/cancel/{job_id}` |

If a worker completes after the browser abandoned polling, preserve the late
result under `late_result`. Do not flip the user-visible job back to
`complete`; that makes the UI feel inconsistent.

## Standard Copy Vocabulary

Use these phrases:

- "Deterministic processing"
- "Local Gemma 4"
- "Optional Gemma edge pass"
- "Gemma refinement requested"
- "Gemma privacy review if loaded"
- "Queued for OCR/media review"
- "Queued for Gemma 4 vision review"
- "Deterministic fallback"
- "Abandon polling"
- "Retry deterministic"
- "Review before submit"
- "No remote call"
- "Hub submit is the first remote POST"

Avoid these phrases unless they are literally true:

- "Gemma reviewed this" when model call did not run.
- "OCR complete" when media was only queued.
- "Vision complete" when no multimodal model processed the image.
- "Processing complete" without saying whether model/media work was deferred.
- "Cancel job" if only browser polling is abandoned.

## Component Guidelines

### Progress Box

Use one visual shape across all pages. Existing page-specific names are okay,
but behavior should match.

Required elements:

- `*-progress-box`
- `*-progress-stage`
- `*-progress-detail`
- `*-progress-label`
- `*-progress-fill`
- `*-progress-note`
- `*-progress-events`

Required behavior:

- Hidden until an operation starts.
- Adds `active` while polling.
- Percent clamped from 0 to 100.
- Event tiles append only once per backend event.
- Failure keeps the box visible with the failed phase and recovery action.

### Activity Log

Use `window.dcActivityLog.attach(...)` and the existing `wbLog` wrapper pattern.
Do not hand-roll activity log HTML unless the shared helper cannot be used.

### Stepper

Use `window.dcWorkflow.createStepper(...)` where the page has a linear flow.
Do not keep all advanced panels open by default. The happy path should be
visible first.

### HTML Safety

If using `innerHTML`, escape dynamic values through the local `escapeHtml` or
`wbEsc` helper. Tests and audit tooling look for known safe patterns. Do not
add unescaped response JSON directly into the DOM.

## Page-Level Guidance

### Bulk File Review

What it should show:

- Upload/source staging.
- Deterministic parsing, GREP, entity extraction, document typing, folder edges, journey mapping.
- Deterministic case brief by default.
- Optional local Gemma edge pass after reviewer confirmation.
- Graph chat that is deterministic first and Gemma only when needed/available.
- Explicit queued OCR/media and Gemma 4 vision work.

Must not imply:

- Inline Gemma ran during upload unless `run_inline_gemma_text=true` and model calls were attempted.
- OCR/media vision completed when only queued.

Recommended UX:

- Keep "Run local Gemma edge pass" as an explicit button after Step 3.
- Keep deterministic retry visible after failures.
- Prefer named cases over `UNKNOWN` evidence buckets in priority rankings.
- For graph answers, always show cited rows and evidence-edge counts.

### Knowledge Extraction

What it should show:

- Source bundle processing through the same local Process harness.
- Source progress bar.
- Draft progress bar.
- Deterministic-only drafting as the recording-safe default.
- Optional Gemma refinement with a clear model phase and cancel/abandon control.
- Promote buttons per draft.
- Finish review after useful drafts are promoted or reviewed.

Must not imply:

- Gemma is required for drafting.
- The model has verified legal facts, phone numbers, or contact details.
- Drafted objects are authoritative before human promotion.

Recommended UX:

- Make "Draft deterministic only" visible next to "Draft knowledge objects".
- If `use_gemma=true`, show "Gemma refinement requested" and elapsed time.
- If stalled, suggest deterministic draft rather than leaving the user at a text-only phase.

### Search

What it should show:

- Query sanitization before search.
- Search backend selected.
- Public-source results.
- Optional verification or knowledge-drafting handoff.
- Clear warning that Search does not require Gemma and is not local-only if network search is enabled.

Must not imply:

- Search results are vetted knowledge.
- A live web result has been verified just because it was retrieved.
- Private worker data should be searched externally.

Recommended UX:

- Align Search steps with the same stepper/progress/event visual language.
- Add a compact progress box for sanitize, search, verify, and handoff stages.
- Keep "Draft into Knowledge" as a review action, not an automatic import.

### Anonymization & Sharing

What it should show:

- Source bundle processing.
- Selected facts.
- Deterministic regex redaction.
- Optional Gemma residual-PII review over already-redacted text.
- Redaction diff table.
- Hub submit target and audit log.
- Remote submit status.

Must not imply:

- Gemma privacy review is mandatory.
- Gemma privacy review guarantees no residual PII.
- Anything left the kernel before Step 4.

Recommended UX:

- Keep "Run deterministic only" available.
- Use `/api/anonymize/start` for visible progress when Gemma review is requested.
- Step 4 should be the only remote POST and should show target URL, SHA, audit path, remote status, and any remote error.

## Implementation Guardrails for Claude Code

Before editing:

1. Read this handoff.
2. Inspect the current page and matching tests.
3. Search before changing route names:

```powershell
rg -n "process/batch/start|draft-envelope/start|anonymize/start|graph-extract/start" packages tests docs
```

Do not:

- Rename API routes without updating tests and replay docs.
- Remove `demo_replay` payloads.
- Remove row IDs, evidence edges, or typed-edge provenance.
- Change sample ZIP contents unless rebuilding sample tests.
- Add external network calls to Process, Knowledge, Search, or Share outside existing explicit submit/search paths.
- Put a model call back inside an upload flow by default.
- Change `is_private` or Kaggle metadata casually.

Do:

- Keep deterministic paths fast and default.
- Put Gemma work behind explicit controls.
- Surface `events` from backend jobs.
- Add or update static-page tests when changing visible labels or controls.
- Preserve current page routes.
- Keep copy concise and concrete.
- Use the shared activity log and workflow helpers.

## Validation Commands

Run these before handing work back:

```powershell
.venv\Scripts\pytest.exe -q packages/duecare-llm-chat/tests/test_process_bulk_review.py packages/duecare-llm-chat/tests/test_harness_workbench.py --basetemp .pytest-workbench-tmp
.venv\Scripts\pytest.exe -q packages/duecare-llm-server/tests/test_slides_surface.py --basetemp .pytest-slides-tmp
.venv\Scripts\pytest.exe -q packages/duecare-llm-chat/tests/test_static_sample_bundles.py packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py tests/test_ui_audit_contract.py --basetemp .pytest-inventory-tmp
.venv\Scripts\python.exe -m py_compile packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py packages/duecare-llm-chat/src/duecare/chat/harnesses/anonymization/handler.py
.venv\Scripts\python.exe scripts/validate_public_surface.py
.venv\Scripts\python.exe scripts/validate_public_messaging.py
git diff --check
```

Expected current baseline:

- Process + workbench focused tests: green.
- Slides tests: green.
- Static samples, inventory, UI audit: green.
- Public surface audit: zero findings.
- Public messaging validation: pass.

Pytest cache warnings on Windows are not functional failures.

## Acceptance Criteria

The UI revision is acceptable only if:

- All four pages use a consistent step/progress/activity pattern.
- Slow Gemma phases are visible and have fallback controls.
- Deterministic-only paths can complete without a model.
- Gemma 4 edge creation remains explicit in Bulk File Review.
- Gemma 4 refinement remains explicit in Knowledge Extraction.
- Gemma 4 privacy review remains explicit in Anonymization & Sharing.
- Search clearly separates sanitization, retrieval, verification, and knowledge handoff.
- No page falsely says OCR/media/Gemma completed when it was queued or skipped.
- Tests and validators listed above pass.

## Claude Design Prompt

Paste this into Claude Design if a visual consistency pass is needed:

```text
You are Claude Design. Review the DueCare workbench pages:

- /static/process.html
- /static/knowledge.html
- /static/search.html
- /static/share.html

Create a consistent local-first workbench UX for deterministic processing,
optional local Gemma 4 jobs, progress bars, event logs, abandon polling,
deterministic retry, and recording-safe completion states.

Do not redesign the product as a marketing site. Keep it compact,
utilitarian, evidence-oriented, and suited for repeated case review.

Required semantics:
- Deterministic processing runs first and must be fast.
- Gemma 4 is optional, local, and explicit.
- Upload steps must not hide long model calls.
- OCR/media/Gemma vision can be queued or deferred; never imply completion
  unless it actually ran.
- Hub submission is the first remote POST in Anonymization & Sharing.

Return:
1. Unified component spec.
2. Revised microcopy.
3. Page-by-page layout guidance.
4. Error/loading/success/deferred states.
5. Engineering acceptance criteria.
```

## Claude Code Implementation Prompt

Paste this into Claude Code for implementation:

```text
You are Claude Code working in the DueCare repo.

Read docs/claude_workbench_ui_handoff_2026_05_18.md first. Then improve
consistency across Bulk File Review, Knowledge Extraction, Search, and
Anonymization & Sharing without changing route contracts or privacy
semantics.

Scope:
- Update page UI and copy only where needed for consistency.
- Use existing shared helpers: _activity_log.js, _workflow.js, _nav.js,
  _chrome.css.
- Preserve deterministic-first defaults.
- Keep Gemma 4 work explicit, local, observable, cancelable/abandonable,
  and fallback-safe.
- Update tests that assert visible UI contract.

Do not:
- Rename routes.
- Remove demo_replay.
- Add remote calls outside explicit search or submit paths.
- Hide long model calls inside upload steps.
- Claim Gemma/OCR/media work completed unless it actually did.

Run the validation commands from the handoff before final response.
Summarize changed files, behavior changes, and any residual risk.
```
