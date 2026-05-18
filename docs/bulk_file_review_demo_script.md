# Bulk File Review demo script

This is the canonical step-by-step walkthrough of the live Bulk File Review
demo as wired into commit `2687a6a` and later. Use it to drive a Kaggle
session, validate any UI/UX regression, or storyboard reviewer flow before
external review.

The companion contract is [`docs/bulk_file_review_north_star.md`](bulk_file_review_north_star.md);
this document is the operational script for running the demo against the
shipped `case_files_streamlined_demo.zip` bundle.

## Preconditions

- DueCare exploration workbench is running on Kaggle (or local equivalent)
  at the printed Cloudflare URL.
- No Gemma 4 model needs to be loaded for the deterministic happy path.
- Browser DevTools network panel is optional but useful for confirming
  async polling cadence.

## Demo path (eight clicks, ~90 seconds without a model)

### 1. Open Bulk File Review

Navigate to `/static/process.html`. The top of the page should show:

- Hub nav with active "Bulk File Review" tab.
- Hero text describing local case-intake and evidence-graph review.
- Trust boundary note: bundles stay on the kernel; nothing leaves.

The activity log card (bottom) reads "No activity yet. Click Start
processing to begin." The shared `_activity_log.js` helper will clear
this idle line on the first event.

### 2. Use the streamlined demo sample

Click **Use streamlined demo**. The page fetches
`/static/samples/case_files_streamlined_demo.zip` (~75 KB, five PH-HK
domestic-worker documents under a single composite case ID
`DC-DEMO-PH-HK-501`) and attaches it to the file picker.

Expected activity log row:
```
[ts] ok  Sample loaded. Click Start processing.
[ts] ok  primary streamlined sample attached
        case_files_streamlined_demo.zip | <bytes>
```

### 3. Start processing

Click **Start processing**. The page POSTs the bundle to
`/api/process/batch/start`, captures the returned `job_id`, then polls
`/api/process/batch/status/{job_id}` every ~600ms.

The progress tile shows real server-side phases:
- `received` -> `parsing` -> `grep_scan` -> `entity_attrs` -> ...
  -> `brief` (deterministic case brief synthesized)
  -> `complete` (`pct=100`)

The final completion event reads:

> Deterministic parsing complete; 0 media asset(s) remain queued for OCR
> or Gemma 4 vision review. Bundle cached for graph chat.

The streamlined demo bundle is text-heavy and emits no queued media
items. The media-rich sample emits non-zero `media asset(s) remain
queued`; the completion text always reflects reality.

### 4. Inspect extracted intelligence

The "Extracted intelligence" panels populate with:

- **Document inventory:** five documents under
  `streamlined_demo/DC-DEMO-PH-HK-501_Lina_Santos/`
  (`01_chat/recruiter_chat.txt`, `02_contract/contract.md`,
  `03_payment/payment_ledger.csv`, `04_complaint/complaint.json`,
  `manifest.json`).
- **People:** composite name `Lina Santos`, case ID `DC-DEMO-PH-HK-501`.
- **Payment amounts:** PHP-denominated values mapped to recruitment-fee
  buckets.
- **Document types:** chat, contract, ledger, complaint, manifest.
- **Journey stages:** recruitment, contract signing, deployment, complaint.
- **Typed edges (42 total) by count:**
  | edge_type | count |
  |---|---|
  | `dated_evidence` | 11 |
  | `journey_stage_observation` | 9 |
  | `fee_amount_observed` | 6 |
  | `filed_under` | 6 |
  | `located_at` | 5 |
  | `salary_deduction_signal` | 5 |

The intelligence graph SVG renders. The graph-detail side panel sits idle
until a node is clicked.

### 5. Mark review complete

Optionally enter notes in the review-textarea, then click **Mark review
complete**. This is purely a client-side state change:

- Sets `wbIntelligenceConfirmed = true`
- Records timestamp + notes
- Enables the graph-chat ask button
- Logs to activity log:
  ```
  [ts] ok  Review gate marked complete | no notes; no processing or
                                          model call was started
  ```

No fetch fires. No model is touched.

### 6. (Optional) Run local Gemma edge pass

If a Gemma 4 model is loaded, clicking **Run local Gemma edge pass** POSTs
to `/api/process/graph-extract/start` and polls
`/api/process/graph-extract/status/{job_id}`. The worker emits phases:

- `queued` -> `starting` -> `seed_edges` -> `prompt_build` ->
  `model_call` -> `parse_model_output` -> `complete`

If **no model is loaded**, the same click still works. The endpoint
returns:

```json
{
  "status": "deterministic_no_model",
  "model_edges": [],
  "seed_typed_edges": [...],
  "uncertainties": [
    "No local Gemma 4 model is loaded; deterministic typed edges and
     RAG candidates are returned for review."
  ]
}
```

The UI updates the edge-pass progress to `deterministic_fallback` at
`pct=100` and keeps the deterministic edges visible.

### 7. Ask the flagship question

Type into the graph-chat input:

> Which rows support fee camouflage and restricted provider choice?

Click **Ask**. The page POSTs to `/api/process/graph-chat`. The new
dedicated branch trips immediately and returns
`analysis_kind="fee_camouflage_and_provider_choice"`. The answer body has
two named sections plus a closing summary:

```
Fee camouflage candidates

Deterministic proxies for fee camouflage are fee_amount_observed,
salary_deduction_signal, and rule_hit edges with placement/training/
medical/repayment language. Explicit fee_camouflage_evidence edges
come from the optional local Gemma edge pass.

- `streamlined_demo/.../recruiter_chat.txt` | edge: fee_amount_observed
  | label: PHP 45,000 placement loan | quote: "Worker agrees to a PHP
  45,000 processing loan deducted from salary..."
- `streamlined_demo/.../payment_ledger.csv` | edge: salary_deduction_signal
  | label: monthly deduction | quote: "Monthly deduction PHP 1,875..."
  ...

Restricted provider choice candidates

Deterministic proxies for restricted provider choice are located_at,
filed_under, and journey_stage_observation edges, plus risk signals
naming a single provider, agency control, or limited choice. Explicit
provider_choice_restriction edges come from the optional local Gemma
edge pass.

- `streamlined_demo/.../manifest.json` | edge: journey_stage_observation
  | label: recruitment
  ...

Both fee camouflage and restricted provider choice are TIP indicators.
The combination strongly suggests recruitment-fee concealment that
the worker cannot avoid. Run the local Gemma edge pass to upgrade
these proxies into explicit fee_camouflage_evidence and
provider_choice_restriction edges, and confirm with original receipts,
contract clauses, and broker/recipient identifiers before any
escalation.
```

The cited rows come exclusively from typed_edges or
people.risk_signals on the bundle. The deterministic branch never
invents row IDs.

### 8. Optional: download artifacts

The page already exposes:
- **Download graph SVG** in the Intelligence graph card.
- **JSON / Markdown** evidence-set downloads in the Typed edges card.

For a full bundle export, the existing `/api/process/batch` response
payload includes everything (intelligence, people, typed_edges,
processing_plan, harness_trace, summary) and is saved under
`/kaggle/working/.duecare-process/`.

## What success looks like

After this 8-step path the reviewer has:

- Watched a real bundle parse end to end with no model required.
- Seen a 42-edge intelligence graph derived from public-source synthetic
  evidence.
- Confirmed a review gate that is honest about not running any model.
- Optionally exercised the local Gemma edge pass with a clear
  deterministic-fallback behavior.
- Received a deterministic answer to the demo's flagship TIP-indicator
  question with cited row IDs, no hallucinations, and an explicit
  upgrade path documented inline.

## Where this can fail and how the page handles it

| Failure | How the page reacts |
|---|---|
| Browser cannot fetch the sample ZIP | activity log shows `err` with HTTP detail; user can still upload manually. |
| `/api/process/batch/start` returns non-200 | activity log shows `err` with short preview; no spinner left running. |
| Gemma edge pass throws | worker emits `status=error` with detail; UI shows `degraded` step; deterministic edges remain visible. |
| Graph chat asks an unknown question | deterministic branch returns `None`; if a model is loaded, layered Gemma chat runs; if no model, returns the fallback summary message with `fallback: "no_model_loaded"`. |
| Model returns reasoning leak | `_looks_like_reasoning_leak` detects it; UI shows the deterministic case brief instead with `fallback: "reasoning_leak_suppressed"`. |

## Pinned tests

The demo script above is pinned by:

- `packages/duecare-llm-chat/tests/test_process_bulk_review.py`
  - `test_process_batch_returns_intelligence_for_streamlined_demo`
  - `test_process_batch_async_job_returns_media_rich_result`
  - `test_process_graph_chat_answers_fee_camouflage_and_provider_choice`
  - `test_process_batch_completion_detail_honestly_reports_queued_media`
  - `test_graph_chat_deterministic_branch_uses_typed_edges_only`
- `packages/duecare-llm-chat/tests/test_static_sample_bundles.py`
- `packages/duecare-llm-chat/tests/test_harness_workbench.py`
- `tests/test_route_contract.py`

A regression in any step of this script trips one of these tests.

## Out of scope for this script

- The Gemma edge pass with a real loaded model — needs Kaggle GPU.
- LoRA fine-tuning — belongs in A-00.
- Online search and hub submission — separate harnesses
  (`search`, `search_safety`, `post_search_verification`,
  `anonymization`).
