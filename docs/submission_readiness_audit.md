# Submission Readiness Audit -- 2026-05-17

> Status snapshot of the DueCare submission ahead of recording and
> Kaggle upload. Lists every active surface, what is built, what is
> verified, and what still needs human verification or work.
>
> HEAD ref at write: `5becafb` (slide-deck demo surface for recording).
> Use this doc as a punch list. Re-run `python -m pytest` and `git log`
> before recording to confirm the items below are still accurate.

## How to read this doc

Each row is in one of three states:

| State | Meaning |
|---|---|
| **Built + verified** | Implementation exists, tests pass, behavior was confirmed locally. |
| **Built, needs verification** | Implementation exists and tests pass locally, but the end-to-end behavior on Kaggle GPU / a real recording / a real reviewer flow has not been confirmed yet. |
| **Remaining** | Not built. |

Verification is the bottleneck. Most rows below are **Built, needs
verification** -- the code is in `master`, but a human walkthrough on
Kaggle or in a browser has not happened yet.

## 1. Live-demo entry surface (`kaggle/02-live-demo/`)

### 1.1 Two-tile landing `/start`

* **State:** Built + verified (local pytest).
* **Files:** `packages/duecare-llm-server/src/duecare/server/static/start.html`,
  route added in `app.py`.
* **Verified:** 13 tests in
  `packages/duecare-llm-server/tests/test_slides_surface.py`.
* **Needs verification on Kaggle:**
  * Open `{public_url}/start` and confirm both tiles render with hover
    states and pills (recommended-for-recording, prep-before-recording).
  * Confirm both links navigate to `/slides` and `/slides/setup`.
  * Confirm the workbench links at the bottom (Hub homepage, Public
    demo page, Bulk File Review, Harness Workbench) all return 200.

### 1.2 Full-screen pitch deck `/slides`

* **State:** Built + verified (local pytest).
* **Files:**
  `packages/duecare-llm-server/src/duecare/server/static/slides.html`.
* **Slides:** 10 total -- title, worker, stakes, solution, demo-chat,
  demo-bulk, architecture, results, video, closing.
* **Verified:** keyboard handlers, demo-chat anchor, localStorage key.
* **Needs verification on Kaggle:**
  * Keyboard navigation: arrows, space, PageUp/PageDown, Home/End, F.
  * The cached-row pill on slide 5 says "cached" when a row is stored
    and "default" when not.
  * Results-slide numbers (slide 8: +27pp / -68% / +44%) are flagged
    as placeholders inline. Decide whether to replace them with real
    A-00 numbers before recording or keep them as illustrative.
  * Video slide 9 -- `walkthrough.mp4` is a placeholder. Decide whether
    to drop a real screen recording or remove the slide.
* **Remaining:** real numbers on slide 8 once A-00 has been run on the
  current branch; optional final screen recording on slide 9.

### 1.3 Cached I/O generator `/slides/setup`

* **State:** Built + verified (local pytest).
* **Files:**
  `packages/duecare-llm-server/src/duecare/server/static/slides-setup.html`,
  `packages/duecare-llm-server/src/duecare/server/slides_cache.py`,
  endpoint `POST /api/slides/cached-io`.
* **Verified:** deterministic per (audience, use_case); prompt override
  works; 4 input-validation paths; pill reflects localStorage state.
* **Coverage:** 6 audiences x 7 use cases = 42 valid combinations.
  Default prompts written for all 7 use cases. Audience tailoring
  written for all 6 audiences.
* **Needs verification on Kaggle:**
  * Generate at least one row per intended slide before recording.
  * Save each row, then verify the deck picks it up.
  * Try a prompt override and confirm the "(Prompt override used. ...)"
    preamble appears.

### 1.4 Kernel banner

* **State:** Built + verified (local read).
* **Files:** `kaggle/02-live-demo/kernel.py` lines around the `[8/8]
  DUECARE IS LIVE` banner.
* **What changed in this branch:**
  * Banner now prints `{public_url}/start` as the recording entry
    point.
  * Alternate entry points list `/slides`, `/slides/setup`, legacy `/`.
  * API list adds `/api/slides/cached-io`.
* **Needs verification on Kaggle:** re-paste `kernel.py` into the
  Kaggle notebook and confirm the banner reads `/start` first. A stale
  paste is why the slides surface looked missing in the last run.

## 2. DueCare App (`kaggle/01-duecare-app/`)

### 2.1 Bulk File Review

* **State:** Built + verified (local pytest, async path, deterministic
  flagship branch).
* **Files:**
  `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/`,
  `packages/duecare-llm-chat/src/duecare/chat/static/process.html`,
  `packages/duecare-llm-chat/src/duecare/chat/static/samples/case_files_streamlined_demo.zip`.
* **Verified:** demo script `docs/bulk_file_review_demo_script.md` walks
  the 8-step happy path; 5 contract tests pin the flagship behavior.
* **Needs verification on Kaggle:**
  * Upload the streamlined demo bundle, watch the async progress.
  * Ask the flagship graph-chat question and confirm the deterministic
    branch returns `analysis_kind="fee_camouflage_and_provider_choice"`.
  * Optional local-Gemma edge pass returns
    `status=deterministic_no_model` when no model is loaded.

### 2.2 Chat harness comparison (`/static/harness.html`)

* **State:** Built. Last full verification predates the universal model
  interface work.
* **Files:** `packages/duecare-llm-chat/src/duecare/chat/static/harness.html`,
  `packages/duecare-llm-chat/src/duecare/chat/harnesses/chat/`.
* **Needs verification on Kaggle:**
  * Send a PH-HK prompt and confirm `applied_layers` show
    persona/grep/rag/tools firing.
  * Trace card surfaces the matched GREP rule IDs and the cited RAG
    docs.
  * The "stock Gemma vs harnessed" delta is visible.

### 2.3 Knowledge / Search / Sync / Share / Import surfaces

* **State:** Built + cross-page UX audit landed in `80c2e90`.
* **Files:** `knowledge.html`, `search.html`, `sync.html`, `share.html`,
  `import.html`.
* **Verified:** happy-path step pattern (Step 1 open, advanced details
  collapsed); Step 3 share button label honest about Gemma availability;
  shared `.dc-activity-log` + `_activity_log.js`.
* **Needs verification on Kaggle:**
  * Each page's activity log clears its idle line on the first event.
  * Each page's "Use sample" button round-trips the sample artifact
    under `/static/samples/`.

## 3. DueCare Fine-tuning and Evaluation (`kaggle/A-00-omni-experiment-workbench/`)

### 3.1 Preconfigured pipeline

* **State:** Built + happy-path landing.
* **Files:** `kaggle/A-00-omni-experiment-workbench/kernel.py`.
* **Verified locally:**
  * `Gemma4Runtime.load(...)` is the inference loader.
  * 16K context constant `A00_INFERENCE_MAX_SEQ_LENGTH` is in place.
  * `chat_no_online` profile wires persona + GREP + RAG + tools with
    internet + import off.
  * Tool dispatch goes through `_format_shared_tool_call` per tool with
    error tracking.
  * `tests/test_a00_runtime_and_parity_contract.py` (16 tests) pins the
    invariants.
* **Needs verification on Kaggle GPU:**
  * Default proof run with E2B/E4B completes within the expected budget.
  * Combined rule + LLM judging produces a 4-arm comparison table when
    fine-tuning is enabled.
  * Report exports under `/kaggle/working/a00_outputs/` include
    activity log, prompts, responses, traces, grades, charts, and a
    manifest.

### 3.2 Synthetic data + LoRA training

* **State:** Built; T4 path documented.
* **Files:** A-00 `_generate_synthetic`, `_training_script`,
  `SYNTHETIC_GENERATION_PROFILES`, `TRAINING_PROFILES`,
  `packages/duecare-llm-training/`.
* **Needs verification on Kaggle GPU:**
  * One real synthetic-row generation run finishes and the JSONL is
    pickable by the trainer.
  * One real LoRA training job runs to a checkpoint that the inference
    runtime can re-load.

## 4. Harness ecosystem (`packages/duecare-llm-chat/src/duecare/chat/harnesses/`)

### 4.1 Registered surfaces

* **State:** Built + verified (contract tests).
* **Surfaces:** `chat`, `process`, `extraction`, `anonymization`,
  `search_safety`, `post_search_verification`, `search`, `import_corpus`.
* **Verified:** `tests/test_harness_imports.py`,
  `tests/test_route_contract.py`, `tests/test_compose_layers.py`;
  per-task JSONL training-log emission.

### 4.2 Universal model interface

* **State:** Built.
* **Files:**
  `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`,
  `HarnessSpec.model_targets`, `MODEL_TRANSPORTS`.
* **Verified:** transports declared (local Gemma runtime, DueCare
  adapter, Ollama, OpenAI-compatible, Anthropic, Gemini, HF endpoint,
  callable, none).
* **Needs verification:**
  * Smoke-test at least one non-Gemma transport (Anthropic or
    OpenAI-compatible) end-to-end if the submission narrative wants to
    claim provider-neutrality. If not, mark the claim as roadmap and
    keep the default Gemma path as the only verified one.

### 4.3 Anonymization + search-safety + post-search-verification

* **State:** Built.
* **Files:** corresponding harness modules under `harnesses/`.
* **Needs verification on Kaggle:**
  * `/api/anonymize` redacts PII at the boundary; audit log captures
    `sha256(original)` only.
  * `/api/search/sanitize` returns a redacted/generalized query before
    any third-party search runs.
  * `/api/search/verify-results` deterministic gate returns a verdict
    on a candidate result set before injection.
  * If online grounding is enabled at recording time, all three gates
    must fire in order.

## 5. Documentation surface

### 5.1 Harness documentation trinity

* **State:** Built + reconciled.
* **Files:** `docs/harness_ecosystem.md`, `docs/harness_pattern.md`,
  `docs/harness_standard_contract.md`.
* **Verified:** review prompts in `docs/REVIEW_PROMPTS.md` cover each.

### 5.2 Demo scripts

* **State:** Bulk-review script is current; live-demo script for the
  slide deck needs to be written.
* **Built:** `docs/bulk_file_review_demo_script.md`.
* **Remaining:**
  * `docs/slide_deck_demo_script.md` -- step-by-step recording walk
    through the 10 slides with timing notes.
  * `docs/video_script.md` -- currently still names old workbench
    surfaces (`/static/grep-tester.html`, `/static/rag-graph.html`,
    `/static/hotlines.html`). Either rewrite it to walk the slide deck,
    or archive it and replace with a slide-deck-specific script.

### 5.3 Writeup

* **State:** Built; word cap respected.
* **Files:** `docs/writeup_draft.md` (currently ~1486 / 1500 word cap).
* **Built additions in `5fa5c97`:** "Live Bulk File Review Walkthrough"
  section.
* **Needs verification:**
  * Read end to end with the slide deck open.
  * Confirm every claim in the writeup is reproducible from the active
    code path (no faked numbers, no stale surface references).
  * If you replace the slide-8 placeholder numbers with real A-00
    output, mirror them into the writeup.

### 5.4 Handoff snapshots

* **State:** Up to date.
* **Files:** `docs/codex_handoff_2026_05_17.md`,
  `docs/copilot_handoff_2026_05_16.md`, `docs/REVIEW_PROMPTS.md`.

## 6. Tests

### 6.1 Focused gate

* **State:** Green.
* **Command:** the focused run used during the slides surface work is:

  ```
  python -m pytest \
    packages/duecare-llm-server/tests/ \
    packages/duecare-llm-chat/tests/test_harness_workbench.py \
    packages/duecare-llm-chat/tests/test_process_bulk_review.py \
    tests/test_route_contract.py \
    tests/test_a00_runtime_and_parity_contract.py \
    -q
  ```
* **Result at HEAD:** 137 passed.

### 6.2 Full suite

* **State:** Last full run was earlier in the session: 448 passed across
  22 suites.
* **Needs verification:** re-run `make test` (or the equivalent
  pytest invocation) before recording to confirm no regression has
  slipped in.

## 7. Kaggle publication

* **State:** Manual copy-paste workflow (CLAUDE.md rule). Claude Code
  does not push kernels.
* **Built:** `kaggle/02-live-demo/kernel.py`,
  `kaggle/01-duecare-app/kernel.py`,
  `kaggle/A-00-omni-experiment-workbench/kernel.py`; each folder has a
  `README.md` and a kernel-metadata file.
* **Needs human action before recording:**
  1. Re-paste the updated `02-live-demo/kernel.py` into the Kaggle UI
     for the existing kernel slug. The banner change in this commit is
     why the previous run did not show the slides surface.
  2. Confirm `DUECARE_COMMIT_SHA` is unset or set to `master` so the
     pip install pulls latest. (For a frozen final submission, replace
     with the immutable commit SHA at recording time.)
  3. Run on T4 x2 (or T4 single for E4B). Watch the banner.
  4. Open `{public_url}/start` and walk through the slide deck.

## 8. Out of scope for this submission push

These items are explicitly archived or deferred per CLAUDE.md and
earlier user directives. Do not touch them without an explicit ask:

* All folders under `_archive/`.
* All folders under `kaggle/_archive/`.
* All folders under `kaggle/kernels/`.
* The skunkworks notebooks under
  `_archive/legacy-research-2026-05-09/skunkworks/`.
* The original 77-notebook research pipeline under
  `_archive/legacy-research-2026-05-09/legacy_notebooks/`.

## 9. Recording-blocking punch list

This is the minimum set that must be true to start a recording take:

1. [ ] Kaggle 02-live-demo banner shows `/start` first (re-paste
       `kernel.py`).
2. [ ] `/start` loads two tiles on Kaggle's Cloudflare URL.
3. [ ] `/slides/setup` generates at least one cached row per slide that
       embeds chat I/O.
4. [ ] `/slides` keyboard navigation tested by a human on the laptop
       that will record.
5. [ ] Bulk File Review streamlined demo bundle uploads and processes
       end to end without an error toast.
6. [ ] Results-slide numbers (slide 8) either replaced with current
       A-00 output or kept as placeholders with the inline caveat shown.
7. [ ] `docs/video_script.md` either rewritten to walk the slide deck
       or archived; otherwise the script and the deck disagree.
8. [ ] `make test` is green at the commit you are recording against.

## 10. Post-recording (not required to record, but listed for completeness)

* Public Kaggle URL added to the writeup.
* HF Hub model card link added to the writeup (if a fine-tune adapter
  is published).
* GitHub release tagged at the recorded commit.
* Final YouTube link added to the writeup.

## Cross-references

* [`docs/REVIEW_PROMPTS.md`](REVIEW_PROMPTS.md) -- index of focused
  review prompts and handoff snapshots.
* [`docs/system_components_and_critical_paths.md`](system_components_and_critical_paths.md)
  -- stable map of the active submission surfaces.
* [`docs/harness_ecosystem.md`](harness_ecosystem.md) -- authoritative
  registered harness inventory.
* [`docs/bulk_file_review_demo_script.md`](bulk_file_review_demo_script.md)
  -- Bulk File Review demo path.
* `kaggle/02-live-demo/README.md` -- live-demo recording walkthrough.
