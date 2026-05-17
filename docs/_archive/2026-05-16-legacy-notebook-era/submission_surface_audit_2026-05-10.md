<!-- audit-allow-file:drift
reason: dated 2026-05-10 audit snapshot. Historical content;
the literal phrase '2 core + 11 appendix' captures the roster
as it stood when this audit ran. Updating it would falsify the
frozen audit record. Use docs/copilot_handoff_2026_05_16.md or
the canonical kaggle/_INDEX.md for the current roster; the older
submission readiness audit is archived under
docs/_archive/2026-05-16-legacy-notebook-era/.
-->

# DueCare submission surface audit — 2026-05-10

Scope requested: website/server/frontend/backend and context docs; primary submission notebooks; appendix submission notebooks; writeup.

This is a readiness audit, not a publish action. Kaggle publishing remains manual.

## Implementation pass — 2026-05-10

- Implemented the typed client-submission envelope in the public hub API: `visibility`, `attribution_mode`, `submitter`, `labels[]`, `consent`, validated contact email, recursive payload PII scan, anonymous-attribution guardrails, and hashed private contact storage.
- Updated website docs to include the full public API surface, CORS behavior, local-KB routes, redacted admin logs, and client-controlled label semantics.
- Set judge-facing Kaggle metadata to public-ready locally without pushing or publishing anything; final Kaggle publication remains manual.
- Reframed A-06 as a prototype appendix, replaced stale `TBD` / `needs upload` README wording with manual-publication status, and documented A-11's script-kernel/model-source shape as intentional.
- Clarified the writeup's 13-notebook judge path versus the broader 77-kernel provenance suite, and narrowed GGUF/LiteRT wording to export/deployment targets.

## Validation run

| Check | Result | Notes |
|---|---:|---|
| Website FastAPI tests | PASS | `28 passed, 1 warning` for `apps/duecare-ai.com/tests` |
| Public messaging validator | PASS | `scripts/validate_public_messaging.py` |
| Public-surface validator | PASS | `scripts/validate_public_surface.py`, 4 checks, 0 findings |
| 77 active Kaggle kernel parser | PASS | `scripts/validate_notebooks.py`, 77 notebooks validated |
| 13 submission folder structural audit | PASS | 2 core + 11 appendix folders have metadata, README, kernels, parseable notebook wrappers where expected, and local wheels |
| Writeup body word count | PASS | 1,026 / 1,500 body words, 474-word margin |
| Editor diagnostics | PASS | No diagnostics in website Python modules or writeup |
| MkDocs build | NOT RUN | `mkdocs` is not installed in the active venv |

## 1. Render website, server, frontend, backend, docs/context

### Strong state

- Website backend is a focused FastAPI hub with a file-backed Render-friendly store, health checks, pack APIs, anonymized signal intake, client submission/retract endpoints, local-KB endpoints, redacted admin logs, robots, and sitemap.
- Website test suite passed: 23 tests cover health, page routes, PII rejection, pack registry, anonymized signal acceptance, admin token gating/redaction, client submission consent, and retraction behavior.
- Public route audit passed: 41 routes probed successfully through the public-surface validator.
- PII handling is concrete: summaries are rejected by schema validators before storage, admin output suppresses payloads and redacts detector-class PII, and raw body text is hashed rather than stored for inbound email.
- Render shape is production-oriented: Docker runtime, `/api/health`, `/healthz`, persistent disk, and no API keys required for the initial public hub.

### Findings

| Priority | Finding | Suggested action |
|---|---|---|
| P0 | The new submission-labeling policy is documented, but the live `ClientSubmissionIn` schema does not yet expose `visibility`, `attribution_mode`, `labels[]`, or consent flags like `allow_training_use` / `allow_public_display`. | Implement a typed submission envelope and tests before presenting client-controlled labels as live UI/API behavior. |
| P1 | `ClientSubmissionIn.payload` is intentionally generic and stored for curator review. Admin views suppress payload keys, but the payload itself is not schema-validated beyond the summary automation gate. | Add per-kind payload schemas or a second recursive PII/safety scan before appending to `updates.jsonl`. |
| P1 | Optional `contact_email` is a plain string and may be persisted when `contact_publication_consent=True`. | Use typed email validation and make publication consent visually explicit in the UI. |
| P2 | CORS is open for public integration. This is defensible but should be documented as intentional. | Add a short README/security note: open CORS is acceptable because the hub exposes public metadata and rejects raw case content. |
| P2 | Admin page is visible while logs are token-gated. That is secure, but judges may find the disabled state confusing. | Add clear copy on `/admin`: logs are disabled unless `DUECARE_ADMIN_TOKEN` is set. |
| P2 | No MkDocs build was run because `mkdocs` is absent from the active environment. | Run the docs build in the environment that owns docs dependencies before final video recording. |

## 2. Primary submission notebooks

Primary folders audited:

1. `kaggle/01-duecare-exploration-workbench`
2. `kaggle/02-live-demo`

### Strong state

- Both primary folders have valid `kernel-metadata.json`, source kernels, local wheels, README docs, and expected Kaggle model/data references.
- `01-duecare-exploration-workbench` is a script kernel with 3 local wheels and built-in freshness checks for the chat harness thresholds.
- `02-live-demo` is a notebook kernel with a parseable `notebook.ipynb`, 17 local wheels, and all four Gemma 4 model variants declared.
- Dataset slugs in kernels and metadata are consistent with the local folder purpose.

### Findings

| Priority | Finding | Suggested action |
|---|---|---|
| P0 | `kaggle/02-live-demo/kernel-metadata.json` has `is_private: true`. | Flip to `false` before the final manual Kaggle push/publish. |
| P1 | The primary notebooks use app-style HTML/CSS patterns such as `display:flex` and bounded overflow. These are good for run-mode apps but can be stripped or degraded by Kaggle's saved-output viewer. | For final judge screenshots, verify run-mode UX directly; for saved-output cells, avoid relying on flex/overflow for critical explanatory content. |
| P2 | Some progress/error logs intentionally truncate stderr or exception strings. This is acceptable at the output boundary, but should not be used for prompt/response artifacts. | Keep truncation out of saved response artifacts; progress-only truncation is fine. |

## 3. Appendix submission notebooks

Appendix folders audited: `kaggle/A-01-*` through `kaggle/A-11-*`.

### Strong state

- All 11 appendix folders have required source files and local wheels.
- All notebook wrappers parse where present.
- A-07 correctly carries additional training-related wheels; A-08 is correctly CPU-oriented.
- A-01, A-02, A-03, A-04, A-05, A-06, A-09, A-10, and A-11 share the standard chat/core/model wheel shape where expected.

### Findings

| Priority | Finding | Suggested action |
|---|---|---|
| P0 | Most appendix `kernel-metadata.json` files still have `is_private: true`; A-11 is public. | Before final manual publication, deliberately choose public/private state for each appendix and update metadata consistently. |
| P0 | A-06 is explicitly marked `STATUS: PLACEHOLDER` in code and README while listed as a submission appendix. | Either finish it, rename the status to `prototype appendix`, or move it out of the judge-facing appendix set. |
| P1 | Several appendix READMEs still say `TBD`, `not yet pushed`, `needs upload`, or `kernel needs creation` even though local wheels and metadata exist. | Replace stale wording with `manual publication pending` or final public URLs after Taylor publishes. |
| P1 | A-11 is an outlier: script kernel, `is_private: false`, no `model_sources`, and a shorter README than peers. | Document that this is intentional, or regenerate as a notebook kernel with matching model metadata. |
| P1 | A-10 uses external jailbroken/abliterated model references rather than Kaggle model attachments. | Confirm this is allowed and that the kernel failure mode is graceful if Hugging Face access fails. |
| P2 | A-03, A-04, A-09 and others use Kaggle-viewer-fragile HTML patterns (`display:flex`, `max-height` + overflow). | Verify in Kaggle saved-output view and replace critical explanatory blocks with Markdown or table output if needed. |
| P2 | A-09 has many display truncations for web-search snippets and tool results. | Accept if they are progress/debug summaries; do not use them as final evidence artifacts. |

## 4. Writeup

### Strong state

- Body word count is safe: 992 / 1,500 words.
- The story is clear: DueCare is infrastructure, not a replacement for NGOs/regulators/caseworkers.
- Gemma 4 features are load-bearing in the narrative: native function calling, multimodal inputs, and local deployment.
- Privacy boundary is stated concretely and aligns with the submission-labeling policy added today.
- Count claims were verified directly from `duecare-llm-chat` harness assets: 161 GREP rules, 46 RAG docs, 5 tools, 587 prompts, 207 5-tier rubrics, 6 required rubrics, 54 classifier examples, 46 universal rubric dimensions, and 21 evaluation-question groups.

### Findings

| Priority | Finding | Suggested action |
|---|---|---|
| P0 | The writeup says the final submission path is 13 notebooks while also mentioning 49 public-live research kernels and 77 tracked kernels. This is technically explainable, but judges may confuse submission path vs evidence archive. | Add one clarifying sentence: `The 13 notebooks are the judge-facing submission path; the larger 77-kernel pipeline is supporting research/provenance.` |
| P1 | The line that the architecture can run through Kaggle, laptop, llama.cpp/GGUF, or LiteRT-style mobile can be read as all modes are live now. | Rephrase as: Kaggle/laptop are live; GGUF/LiteRT are export/deployment targets unless already validated. |
| P1 | The writeup does not yet mention the new client-controlled labeling envelope. | Add one sentence in the public hub/privacy section about anonymous, pseudonymous, organization-tagged, and aggregate-only sanitized submissions. |
| P2 | The closing `Going deeper` links are good, but the privacy claim should point to the new labeling policy or anonymization policy. | Add `submission_labeling_policy.md` or `anonymization_policy.md` to the link row if space permits. |

## Recommended next actions

1. Implement the submission-labeling envelope in the website API and tests.
2. Decide final Kaggle public/private state for all 13 submission folders; at minimum set the two primary notebooks public before final manual publishing.
3. Clean stale appendix README status language (`TBD`, `needs upload`, `PLACEHOLDER`) so judges see intentional maturity labels.
4. Clarify the writeup's 13-vs-77 notebook wording and GGUF/LiteRT live-vs-roadmap status.
5. Run final checks again: website tests, public messaging validator, public-surface validator, submission folder audit, writeup word count, and a docs build in an environment with MkDocs installed.
