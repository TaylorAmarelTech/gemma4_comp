# DueCare UI/UX Pre-Recording Audit

This is the operator checklist for the final demo pass. The runnable audit
manifest lives at
`packages/duecare-llm-chat/src/duecare/chat/static/ui_audit_manifest.json`
and is rendered in Kernel 01 at `/static/ui-audit.html`.

## Blocking Gates

- Run Kernel 01 and open the Cloudflare URL.
- Open `/static/ui-audit.html` and confirm the manifest renders.
- Visit every static page listed in the audit page.
- Run the Playwright suite in `kaggle/01-duecare-exploration-workbench/tests`.
- Capture desktop, tablet, and mobile screenshots for Chat, Harness Comparison,
  Bulk File Review, Knowledge Extraction, Search, Anonymization, Status,
  Harnesses, Ecosystem Map, and UI Audit.
- Run A-00 quick proof: baseline export, harness export, comparison report.
- Run A-00 rubric-polished synthetic generation, then create the tiny fine-tune
  smoke bundle for E2B or E4B.
- Save the A-00 HTML report and JSON bundles for the writeup.

## Manual Control Audit

For every screen:

- Every button has a visible action, loading state, and completion state.
- Every input has a label, example value, and validation/error state.
- Every output has an empty state, success state, and failure state.
- Every model-dependent action states whether Gemma 4 is required.
- Every upload/download states the local trust boundary.
- Every graph, table, and card has a source, count, or row ID.
- Every activity log is at the end of the main workflow.

## Bulk File Review Follow-Up

The current implementation now detects text chunks, extractable PDF pages,
images, scanned PDFs, media assets, OCR/multimodal work queues, people,
payments, locations, evidence edges, timeline events, and journey-stage
critical points. The next implementation step is wiring real OCR and Gemma 4
multimodal extraction per page/image, then feeding those extracted facts back
into entity resolution and graph chat.

## Synthetic Data And Fine-Tune Follow-Up

A-00 has the required control-plane path:

- generate `rubric_polisher` SFT and DPO rows
- export prompt tests, knowledge facts, manifest, and bundle ZIP
- create a tiny 5-step training script as a smoke test
- run the full Unsloth job only on Kaggle or another CUDA host

The training target should teach response structure and judgement. It should
not memorize volatile contacts, current advisories, fee caps, wage rules, or
fresh statutes. Those remain tool calls or vetted knowledge-pack facts.

## Known Improvement Backlog

- Add OCR for PDFs and images.
- Add Gemma 4 vision extraction for each media asset.
- Add entity-resolution review UI.
- Add a graph visualization focused on fee points across the worker journey.
- Move grading rubrics, judge prompts, weights, and evaluation dimensions into
  downloadable knowledge packs.
- Run the Kaggle E2B/E4B fine-tune smoke path with `rubric_polisher` output.
- Consolidate redundant helper pages after the video is recorded.
