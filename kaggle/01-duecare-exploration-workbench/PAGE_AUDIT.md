# DueCare Exploration Workbench Page Audit

Review date: 2026-05-14

Scope: `kaggle/01-duecare-exploration-workbench` and the static UI bundled from `packages/duecare-llm-chat/src/duecare/chat/static`.

This audit documents the pages a judge sees after running the Kaggle script kernel and opening the Cloudflare URL. It is based on the local source tree, not the private Kaggle edit UI. The Kaggle URL runs `kernel.py`, which serves the FastAPI workbench and the static pages listed below.

## Product Role

The exploration workbench is the broadest DueCare surface. Its job is not to be the shortest demo. Its job is to prove that the project is real, inspectable, locally runnable, and technically deep:

- A judge can load one Gemma 4 model and use it across every workflow.
- A reviewer can inspect every harness layer rather than trusting a black box.
- A technical evaluator can compare baseline, harnessed, graded, searched, imported, anonymized, and synced flows from the same kernel.
- A domain reviewer can see how legal rules, civil-society contacts, corridor facts, grading rubrics, and local case evidence are treated as maintainable knowledge, not hardcoded magic.
- A privacy reviewer can see where data stays local and where only redacted proposals cross to a public hub.

## Design Philosophy

The workbench uses a "civic operations" design language:

- Clear over decorative: dense but readable panels, restrained colors, compact status labels, and visible evidence.
- Guided but inspectable: common workflows use accordion-style steps while raw JSON, logs, traces, and catalogs remain available.
- Local-first by default: pages must say whether information stays in the browser, stays in the Kaggle kernel, or can be sent to a hub.
- One model state: all pages share the same top model selector and loader status because Kaggle sessions are usually constrained to one resident model.
- Harness transparency: every Gemma-facing workflow should show what layers ran, what was injected, what rules fired, and what was emitted.
- Knowledge-pack maintainability: laws, contact details, rubrics, evaluator prompts, RAG docs, GREP rules, and tool facts should be replaceable through packs where practical.
- Judge-friendly proof: every page should support a demo story, but also expose the details a skeptical evaluator would inspect.

## Dependency Legend

| Label | Meaning |
|---|---|
| No model | Works without Gemma 4. Useful before GPU load. |
| Optional Gemma | Works deterministically first, improves when Gemma is loaded. |
| Gemma required | Primary value depends on a loaded model. |
| External optional | May call web or hub endpoints only when the user requests it. |
| Redirect | Compatibility page that forwards to the current workflow. |

## Global Shell

The shared shell comes from `_nav.html`, `_nav.js`, `_chrome.css`, and `showcase.css`.

Core functions:

- Shows active model, package version, and GPU state.
- Provides one global model selector for chat, compare, grading, process graph chat, and knowledge extraction.
- Groups navigation into Overview, primary workbench workflows, and System pages.
- Links to the DueCare hub and exposes a shutdown control.
- Polls `/api/version`, `/api/model-info`, and `/api/load-model/status`.

Design intent:

- Keep global chrome short enough for Kaggle/Cloudflare viewports.
- Avoid duplicate per-page model selectors.
- Make model state visible even when users enter a deep page directly.

Current audit status:

- Good: model selector is global, compare can be entered directly, and system pages are grouped.
- Watch: standalone older layer pages still have some legacy title punctuation and should be cleaned after the primary demo flow is stable.

## 2026-05-15 Validation Snapshot

Local FastAPI smoke testing covered every static route bundled in
`packages/duecare-llm-chat/src/duecare/chat/static` and the core JSON API
surface used by Chat, Harness Comparison, Bulk File Review, Knowledge
Extraction, Search, Anonymization and Sharing, Sync, Status, and the layer
catalog pages.

Confirmed locally:

- 38 static routes return HTTP 200 or intentionally redirect to the current
  workflow page.
- Pages without a bespoke activity log receive the shared bottom activity log
  from `_nav.js`; primary workflow pages keep their explicit logs.
- `/api/harness-catalog/import` now serves local imported evidence metadata
  so the Chat Import layer has a real inspectable catalog endpoint.
- The sample case bundle serves from `/static/samples/case_files_sample.zip`;
  `/api/process/batch` and `/api/process/graph-chat` return stable local
  results without requiring a remote service.
- `/api/knowledge/draft-envelope`, `/api/import/*`, `/api/anonymize`,
  `/api/contacts`, `/api/grep/test`, `/api/retrieval/config`, and the main
  harness catalogs respond under `TestClient`.

Still requires live Kaggle review before recording:

- Model loading and model-required lightboxes on direct deep links.
- Real Gemma 4 generation paths, including process case briefs and graph chat.
- Browser screenshots at desktop, tablet, and mobile widths.
- Web search with the selected backend or the kernel search hook.
- A-00 synthetic generation plus tiny fine-tune smoke bundle on GPU.

## Primary Pages

| Page | Route | Dependency | Purpose | Main Functions | Design Notes |
|---|---:|---|---|---|---|
| Getting Started | `/` | No model | Home and orientation page for first-time reviewers. | Explains workbench purpose, trust boundaries, workflow entry points, and endpoint reference. | Should be calm, short, and orienting. It is intentionally not a marketing landing page. |
| Chat | `/static/chat.html` | Gemma required | Primary chat harness for abusive content, worker questions, and corridor reasoning. | Message input, image upload, examples, layer toggles, SSE generation, pipeline trace, grading. | The richest harness. UI should feel like an analyst cockpit but still be usable as a chat. |
| Harness Comparison | `/static/compare.html` | Gemma required | Side-by-side A/B comparison of two harness configurations on the same prompt. | Shared examples, prompt input, variant layer toggles, SSE responses, grading, timing, trace comparison. | The key proof page for "harness moved the answer". It should inherit model state from top chrome. |
| Bulk File Review | `/static/process.html` | Optional Gemma | Upload a case bundle, extract deterministic intelligence, build a graph, and ask questions over it. | ZIP/CSV/JSONL/TXT/PDF/image upload, sample bundle, GREP scan, entity extraction, journey points, graph visualization, graph chat. | This is the local research and case-intake story. It must show document hierarchy, entities, edges, and critical journey points clearly. |
| Knowledge Extraction | `/static/knowledge.html` | Gemma required for best draft | Convert raw text into structured knowledge-object envelopes. | Auto-suggest leaf types, draft envelopes, validate fields, promote to local knowledge store, export packs. | UI should hide taxonomy complexity until advanced mode. Default path should be "paste text, review suggested objects". |
| Search | `/static/search.html` | External optional | Search public sources safely, then convert useful results into draft knowledge. | Query input, page-side sanitization, backend selection, search results, draft knowledge action. | Search must clearly show sanitization before any third-party backend. |
| Anonymization and Sharing | `/static/share.html` | Optional Gemma | Review files, redact PII, and submit safe proposals to the hub. | File input, row selection, redaction preview, audit hash, local submit, hub submit. | The trust boundary is the product. Raw case data stays local; hub submission is redacted and curated. |

## System and Governance Pages

| Page | Route | Dependency | Purpose | Main Functions | Design Notes |
|---|---:|---|---|---|---|
| Sync Knowledge Packs | `/static/sync.html` | External optional | Pull vetted or unvetted knowledge packs into the local runtime. | Sync source selection, envelope validation, hot-load, result review, manual import. | Should make provenance obvious: bundled, local, vetted hub, or unvetted hub. |
| Status | `/static/status.html` | No model | Show local instance health and knowledge state. | Refresh runtime state, counts, sync history, backend state, model state. | Should be the single source of truth for whether the kernel is ready. |
| Harness Workbench | `/static/harness.html` | No model | Contract registry for the seven harnesses. | Harness selector, primary vs secondary classification, routes, consumed inputs, emitted outputs, test links. | Important for nomenclature: only Gemma-facing safety surfaces should be called harnesses. Utilities should be labeled utility surfaces. |
| UI Audit | `/static/ui-audit.html` | No model | Pre-recording checklist for pages, kernels, controls, and gaps. | Reads `ui_audit_manifest.json`, lists kernel/page checklists and backlog. | This is the internal quality gate before video recording. |
| Settings | `/static/settings.html` | No model | Configure retrieval, online search, and model loading behavior. | RAG mode, candidate counts, parent expansion, graph expansion, online BYOK backend config, model load mode. | Advanced surface. Guided steps help users avoid thinking every knob is required. |
| Models | `/static/models.html` | Optional Gemma | Inspect and load supported model variants. | Variant cards, current model state, GPU state, load logs, loader polling. | Should reinforce single-model Kaggle constraint and use the same loader state as top chrome. |
| Logs | `/static/logs.html` | No model | Inspect runtime event logs. | Tail logs, filter by level/kind/layer, auto-refresh, clear. | Must remain privacy-safe and avoid logging raw case data. |
| All Tools | `/static/all-tools.html` | No model | Flat index of all workbench capabilities. | Links grouped by chat/classification, layer transparency, worker/NGO utilities, system. | Useful fallback when nav hides a page. It still needs punctuation cleanup in a later pass. |

## Use-Case and Story Pages

These pages align the Kaggle workbench with the public project narrative. They are not the main technical proof, but they tell judges why each capability matters.

| Page | Route | Dependency | Purpose | Main Functions | Design Notes |
|---|---:|---|---|---|---|
| Use Cases | `/static/use-cases.html` | No model | Hub for six audience lanes. | Links to platform, NGO/regulator, worker, researcher, knowledge-sharing, and developer pages. | Should match the public site and guide users into runnable workbench actions. |
| Platform Safety | `/static/showcase-platform.html` | Gemma required through linked chat | UGC moderation lane for marketplaces and high-volume queues. | Scenario links into chat and compare. | Emphasizes screening, explanation, and handoff to existing review pipeline. |
| NGO and Regulator | `/static/showcase-ngo.html` | Optional Gemma through linked pages | Case intake and triage lane. | Links to bulk review, chat, and knowledge extraction. | Should emphasize local device processing and worker privacy. |
| Individual Worker | `/static/showcase-worker.html` | Gemma required through linked chat | Plain-language rights and referral lane. | Scenario prompts into chat. | Must avoid overclaiming legal advice or encouraging unsafe direct action. |
| Researcher | `/static/showcase-researcher.html` | Optional Gemma | Corridor research and citation lane. | Links to RAG, graph, bulk review, and hash/citation flows. | Should highlight reproducibility, versioned packs, and citeable outputs. |
| Developer | `/static/showcase-developer.html` | No model | Integration partner lane. | Links to API/harness contract pages and deployment explanation. | Should make client/server, local, and enterprise deployment modes concrete. |
| Ecosystem Map | `/static/ecosystem.html` | No model | Architecture and solution ecosystem narrative. | Runtime map, deployment modes, harness map, evaluation/training flywheel. | This is the system design proof page. It should not make claims unsupported by runnable pages or notebooks. |

## Evaluation and Grading Pages

| Page | Route | Dependency | Purpose | Main Functions | Design Notes |
|---|---:|---|---|---|---|
| Grade a Response | `/static/grade.html` | Optional Gemma | Standalone evaluator for prompt/response pairs. | Prompt input, response input, rule-based judge, LLM judge, combined judge, score table. | Applicability should be prompt-driven. The response should not score better merely by causing dimensions to be N/A. |
| GREP Tester | `/static/grep-tester.html` | No model | Test deterministic trafficking-pattern rules live. | Text input, sample prompts, rule hit summary, latency. | Useful for explaining that GREP is not RAG and not an LLM. |
| GREP Rules | `/static/grep-rules.html` | No model | Browse the rule pack. | Filter rules, inspect patterns, citations, severity, categories. | Supports maintainability and knowledge-pack story. |
| RAG Corpus | `/static/rag-corpus.html` | No model | Browse bundled legal and factual evidence. | Search/filter docs, recent retrieval highlighting, source/citation display. | Should show RAG as evidence retrieval, not deterministic rule firing. |
| Citation Graph | `/static/rag-graph.html` | No model | Visualize corpus relationships and citations. | Force-directed graph, node inspector, linked sources. | Good for technical depth and researcher lane. |
| Tools Layer | `/static/tools.html` | No model | Inspect lookup tables and function-call data. | Corridor fee caps, ILO indicators, hotline/contact tables, camouflage labels. | Phone numbers and mutable contacts should be knowledge-pack backed and verifiable. |
| Persona Library | `/static/persona.html` | No model | Explain model stance and safety response style. | Persona list and schema version. | Shows how Gemma is instructed to refuse harmful operational help while supporting workers. |
| Online Layer | `/static/online.html` | External optional | Inspect online search provider configuration. | Backend status, BYOK notes, search provider metadata. | Should distinguish online from RAG and search safety. |
| Search Safety | `/static/search-safety.html` | Optional Gemma | Sanitize outbound search queries before third-party search. | Strict redaction, optional Gemma rephrase, trace output. | Primary privacy proof for outbound search. |
| Hotlines and Contacts | `/static/hotlines.html` | No model | Browse contact pathways. | Filter contacts, show verification metadata. | Contact details are volatile and should be sourced from updateable packs. |

## Data, Import, and Sharing Pages

| Page | Route | Dependency | Purpose | Main Functions | Design Notes |
|---|---:|---|---|---|---|
| Local Import Corpus | `/static/import.html` | No model | CRUD over user-attached local evidence. | Upload, paste snippet, list, delete, clear. | Utility surface, not a Gemma harness. It prepares evidence for local retrieval. |
| Anonymization Preview | `/static/anonymization-preview.html` | No model | Preview redacted payload before hub submission. | Paste text, regex redaction, outbound JSON preview, optional send. | Shares design language with `share.html`; could eventually be merged after demo. |
| Upload Redirect | `/static/upload.html` | Redirect | Backward-compatible route to Bulk File Review. | Redirects users to `/static/process.html`. | Keep while external links may exist. |
| Submit Redirect | `/static/submit.html` | Redirect | Backward-compatible route to Anonymization and Sharing. | Redirects users to `/static/share.html`. | Keep while external links may exist. |
| Insights Redirect | `/static/insights.html` | Redirect | Backward-compatible route to Bulk File Review or insight outputs. | Redirects away from stale standalone dashboard. | Consolidation already started. |

## Page-by-Page Function Notes

### Getting Started

Purpose: orient first-time judges and collaborators.

Functions:

- Defines DueCare as a local Gemma 4 safety workbench.
- Points to the primary flows.
- Explains local, enterprise, and networked hub deployment ideas.

Design philosophy:

- Use as a map, not a sales page.
- Keep the first screen actionable.
- Make the model selector visible globally so direct deep links still work.

Audit notes:

- Good page to start a manual demo if the judge has no context.
- Should not duplicate the public website in detail.

### Chat

Purpose: demonstrate the main safety harness for free-form user interaction.

Functions:

- Sends user prompts to `/api/chat/send` over SSE.
- Optional image upload via `/api/chat/upload-image`.
- Toggles Persona, GREP, RAG, Tools, Online, and Import context.
- Shows examples, pipeline traces, grading, and response metadata.

Design philosophy:

- "Power-user chat" for a technical judge.
- Show the complete harness without hiding the mechanics.
- Keep examples aligned with compare.

Audit notes:

- Highest priority page for video polish.
- Hover and tile expansion stability must stay fixed.
- Example picker parity with compare is a regression gate.

### Harness Comparison

Purpose: prove the value of harnessing with the same prompt and same loaded model.

Functions:

- Runs Variant A and Variant B with different layer configurations.
- Streams both answers.
- Grades both answers and summarizes per-dimension deltas.
- Shows timing and harness trace differences.

Design philosophy:

- Side-by-side evidence first, explanations second.
- No separate model picker; use shared model state.
- Make prompt and layer differences visible.

Audit notes:

- Use this for judge-facing "before and after" proof.
- Score interpretation should emphasize applicable dimensions and not raw N/A count.

### Bulk File Review

Purpose: support local case intake, investigative triage, and research graph construction.

Functions:

- Accepts ZIP, CSV, JSONL, text, PDF, and image bundles.
- Enumerates file structure and treats folder names as evidence context.
- Chunks text and extractable PDF pages.
- Queues scans and images for OCR plus Gemma vision extraction where available.
- Extracts people, agencies, employers, amounts, dates, locations, statutes, case IDs, and journey stages.
- Builds evidence edges and lets the user chat against the graph.

Design philosophy:

- This page should feel like a lightweight investigative document workbench.
- It must distinguish implemented deterministic passes from queued OCR/multimodal work.
- Visual graph, journey map, table, timeline, and graph chat should reinforce each other.

Audit notes:

- The sample bundle must include realistic synthetic images, screenshots, scans, PDFs, and document photos, not just text/CSV.
- Graph chat needs activity log entries and row citations.
- Avoid meaningless `?` edge labels; use named unknown categories or hide low-confidence empty labels.
- Maps may be useful for location intelligence if locations are normalized and privacy-safe.

### Knowledge Extraction

Purpose: convert unstructured domain text into structured knowledge objects.

Functions:

- Sends text to `/api/knowledge/draft-envelope`.
- Auto-suggests useful leaf types.
- Shows validation notes.
- Promotes approved envelopes into local knowledge.
- Supports import/export/sync of knowledge packs.

Design philosophy:

- Default should be simple: paste text, get suggested objects.
- Manual taxonomy selection belongs in advanced settings.
- The user should not need to understand all 21 leaf types before drafting.

Audit notes:

- Continue reducing front-loaded taxonomy complexity.
- Leaf type names should be documented for advanced users but not block first-run success.

### Search

Purpose: safely use public web search and turn useful findings into knowledge.

Functions:

- Sanitizes queries before external search.
- Runs selected search backend.
- Displays results and trace.
- Lets the user draft selected results as knowledge objects.

Design philosophy:

- Search safety is part of the workflow, not a footnote.
- Result-to-knowledge should happen without leaving the page.
- Search should be clearly separate from RAG and GREP.

Audit notes:

- Good target for more guided step progression.
- Search result promotion should include source URL, retrieval date, snippet, and confidence.

### Anonymization and Sharing

Purpose: move redacted, consented knowledge proposals from local runtime to hub review.

Functions:

- Loads files or text.
- Lets user select rows.
- Runs anonymization.
- Shows redacted output and audit hashes.
- Submits locally or to the configured hub.

Design philosophy:

- The user must always know what can leave the kernel.
- Human review and vetting are part of the trust story.
- This page represents networked civil-society collaboration.

Audit notes:

- Should remain the canonical sharing page.
- `anonymization-preview.html` can stay as a narrow teaching surface or be merged later.

### Sync

Purpose: pull knowledge from the hub into a local runtime.

Functions:

- Syncs vetted and unvetted packs.
- Validates envelope shape.
- Hot-loads runtime extras.
- Shows imported counts and result status.

Design philosophy:

- Trust is based on provenance.
- Vetted and unvetted should never be visually ambiguous.
- Sync is pull-based and controlled by the local operator.

Audit notes:

- This is important for the civil-society vetting loop in the writeup.

### Status

Purpose: answer "is this instance ready and what is loaded?"

Functions:

- Shows package version, model state, knowledge counts, and backend state.
- Links to deeper pages.

Design philosophy:

- Status should be compact, factual, and easy to screenshot.

Audit notes:

- Keep counts aligned with `/api/version`, `/api/brand`, and pack imports.

### Harness Workbench

Purpose: document the fixed contracts for the seven named surfaces.

Functions:

- Lists harness names, kind, applied layers, consumed inputs, emitted outputs, and routes.
- Separates primary Gemma safety surfaces from secondary utility surfaces.

Design philosophy:

- Contract language must be precise.
- "Harness" should mean a surface that harnesses Gemma or a safety gate, not generic CRUD.

Audit notes:

- Use this page when explaining architecture to technical judges.

### UI Audit

Purpose: internal pre-recording and pre-submission checklist.

Functions:

- Reads a JSON manifest.
- Lists kernels, static pages, global gates, and backlog.

Design philosophy:

- Treat the UI as a tested product surface, not just demo scaffolding.

Audit notes:

- This page should be updated as improvements land.

### Use Cases and Showcase Pages

Purpose: map technical capabilities to the six audience lanes.

Functions:

- Use Cases page gives overview.
- Showcase pages route to specific workflows and prompts.

Design philosophy:

- Human narrative first, then runnable proof.
- Avoid making unsupported claims that are not backed by a page or appendix notebook.

Audit notes:

- These pages are useful in the video pitch and for judges who arrive from the public website.

### Ecosystem

Purpose: explain how local runtime, enterprise deployment, public hub, knowledge packs, evaluation, synthetic data, and fine-tuning fit together.

Functions:

- Shows architecture and flywheel.
- Links to implementation proof pages.

Design philosophy:

- This should be a technical diagram in HTML, not a marketing infographic.

Audit notes:

- Any future generated diagram should match this page, not replace the runnable proof.

### Grade

Purpose: inspect the evaluator independently of chat and compare.

Functions:

- Rule-based grading.
- LLM judge grading.
- Combined grading with disagreement panel.

Design philosophy:

- Evaluation should be transparent and debuggable.
- Dimensions should be applicable based on prompt and scenario.
- Scores should use 0 to 10 or percentage-style granularity, not only pass/partial/fail.

Audit notes:

- Contact accuracy, regulator contact accuracy, civil-society contact quality, retaliation-risk warnings, and referral boundary dimensions are important.

### Layer Transparency Pages

Purpose: make each safety layer inspectable.

Functions:

- Persona: system prompt stance.
- GREP Rules: deterministic pattern pack.
- GREP Tester: live deterministic rule testing.
- RAG Corpus: legal/factual evidence store.
- RAG Graph: citation relationships.
- Tools: deterministic lookup functions and tables.
- Online: public web backend configuration.
- Search Safety: outbound query sanitizer.
- Hotlines: contact pack browser.

Design philosophy:

- Let judges audit the ingredients.
- Keep mutable facts like contacts and phone numbers in packs.
- Make degradation modes visible.

Audit notes:

- Some older layer pages still use legacy typography/title punctuation and can be normalized later.

### Import, Upload, Submit, and Insights

Purpose: support evidence lifecycle and backward compatibility.

Functions:

- Import is the current local CRUD page for user evidence.
- Upload redirects to Bulk File Review.
- Submit redirects to Anonymization and Sharing.
- Insights redirects to the newer bulk-review intelligence flow.

Design philosophy:

- Keep canonical workflows clear.
- Keep redirects until old links no longer matter.

Audit notes:

- After the competition demo, consider removing or hiding redirect pages from navigation docs.

## API Surface Behind the Pages

Most important APIs:

| API | Used By | Purpose |
|---|---|---|
| `/api/load-model`, `/api/load-model/status`, `/api/load-model/logs` | top chrome, Models | Global model loading and observability. |
| `/api/chat/send`, `/api/chat/upload-image`, `/api/chat/image/{sid}` | Chat, Compare | Gemma chat and multimodal attachment flow. |
| `/api/grade`, `/api/grade-deep`, `/api/grade-combined` | Chat, Compare, Grade | Rule, LLM, and combined evaluation. |
| `/api/process/batch`, `/api/process/graph-chat` | Bulk File Review | Case-bundle processing and graph-grounded questions. |
| `/api/knowledge/draft-envelope`, `/api/knowledge/promote`, `/api/knowledge/import`, `/api/knowledge/export`, `/api/knowledge/sync` | Knowledge, Sync, Search | Knowledge-object drafting, promotion, import/export, and pack sync. |
| `/api/search/sanitize`, `/api/search/safety-info` | Search Safety, Search | Query redaction and optional rephrase before third-party search. |
| `/api/search/client`, `/api/search/server`, `/api/search/backends` | Search | Web search utility. |
| `/api/import/upload`, `/api/import/snippet`, `/api/import/list`, `/api/import/{doc_id}` | Import | Local evidence CRUD. |
| `/api/anonymize`, `/api/submit/knowledge`, `/api/submit/local` | Share, Anonymization Preview | Redaction and submission workflows. |
| `/api/brand`, `/api/version`, `/api/model-info`, `/api/harnesses`, `/api/harness/inventory` | Shell, Status, Harness, Layer pages | Runtime introspection. |
| `/api/rag/graph`, `/api/grep/test`, `/api/contacts`, `/api/search-all` | Layer pages | RAG graph, rule testing, contacts, and cross-layer search. |

## Recommended Demo Path Through Pages

1. Start at `/` to explain local-first scope.
2. Open global model selector and load E2B or E4B.
3. Use `/static/chat.html` for the primary abusive-content or worker-support prompt.
4. Use `/static/compare.html` to prove harness lift on the same prompt.
5. Use `/static/process.html` with the sample bundle to show local case-file intelligence.
6. Use `/static/knowledge.html` to convert extracted text into maintainable knowledge.
7. Use `/static/search.html` to show safe public research and result-to-knowledge.
8. Use `/static/share.html` to show redaction before hub submission.
9. Use `/static/sync.html` to show knowledge-pack updates coming back into the local runtime.
10. Use `/static/ui-audit.html` and `/static/status.html` as quality and readiness proof.

## Consolidation Opportunities

Highest value next refinements:

1. Normalize legacy titles and punctuation on older layer pages: `all-tools.html`, `grep-rules.html`, `grep-tester.html`, `hotlines.html`, `index.html`, `logs.html`, `online.html`, `persona.html`, `rag-corpus.html`, `rag-graph.html`, and `tools.html`.
2. Keep `share.html` as canonical and decide whether `anonymization-preview.html` remains a teaching page or merges into share.
3. Keep `process.html` as canonical and hide `upload.html` and `insights.html` from any visible index.
4. Continue moving volatile contacts and legal details into knowledge packs with verification metadata.
5. Add richer sample evidence for Bulk File Review: PDFs, scans, screenshots, ID-card images, document photos, chat screenshots, and folder names that encode entities.
6. Add an entity-resolution review UI for people, agencies, employers, phones, wallets, and locations.
7. Add map and timeline views only after location normalization and privacy controls are solid.
8. Make evaluation knowledge packs explicit: dimensions, evaluator prompts, weights, applicability logic, and contact-verification rules.

## Final Assessment

The architecture is coherent for the competition:

- Chat and Compare prove the core harness thesis.
- Bulk File Review proves local research and case-intake utility.
- Knowledge, Sync, Share, and Import prove the maintainable knowledge-pack loop.
- Grade and UI Audit prove evaluation discipline.
- Use-case and Ecosystem pages connect the technical system to the six judge-facing audiences.

The remaining risk is not architectural. It is polish and proof density:

- Bulk File Review needs more realistic multimodal evidence examples.
- Grading needs continued refinement around applicability, dynamic weights, contacts, retaliation risk, and response templates.
- Legacy layer pages need one more visual normalization pass.
- The A-00 appendix should generate quantitative reports that tie back to these exact pages.
