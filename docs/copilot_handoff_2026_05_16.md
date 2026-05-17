# Copilot handoff — DueCare Gemma 4 harness ecosystem (snapshot 2026-05-16, HEAD=8141134)

Paste this into GitHub Copilot Chat (or open it alongside the file you
want Copilot to work on) when picking up DueCare work after this
Claude Code session.

This is a self-contained snapshot. You do not need the prior chat
history.

Follow-up note: this file was originally captured at commit `8141134`.
Later commits may have completed items from the "Suggested next work"
section; use `git log --oneline -10` for the live HEAD.

---

## Where we are

Repo: `C:\Users\amare\OneDrive\Documents\gemma4_comp`
Branch: `master` (clean, in sync with `origin/master`)
HEAD: `8141134 Add Copilot handoff snapshot for 2026-05-16 session`

Test baseline (last verified):
- North-star contract gate: 149 passed
- Broader regression sweep (kernel01 portability + smoke + harness + compose
  + per-harness tools + route + multi-harness + UI audit + end-to-end flywheel
  + ecosystem docs): 245 passed
- Combined: **394 tests passing**, 0 failures from current scope

Three pre-existing failures in `tests/test_kaggle_notebook_utils.py`
(auto-generated `docs/notebook_guide.md` drift vs current `kaggle/`
inventory) predate this session's work and are unrelated to the
harness / A-00 surface. Skip unless explicitly asked to regenerate
`notebook_guide.md` via `scripts/generate_notebook_guide.py`.

## Active competition scope

The Gemma 4 Good Hackathon submission is built around exactly three
Kaggle kernels. Treat any work outside these as out of scope unless
Taylor explicitly asks:

- `kaggle/01-duecare-exploration-workbench/kernel.py` — broad reviewer
  workbench with chat, compare, bulk file review, knowledge extraction,
  search, search safety, anonymization, grading, layer toggles. Uses
  `duecare.chat.create_app(**default_harness())`.
- `kaggle/02-live-demo/kernel.py` — focused interactive demo path. Uses
  `duecare.chat.gemma4_runtime.Gemma4Runtime` via `_LIVE_MODEL_RUNTIME`
  and `duecare.server.create_app` for the live-demo surface.
- `kaggle/A-00-omni-experiment-workbench/kernel.py` — quantitative
  control plane for benchmark / synthetic-data / fine-tuning / judging /
  reports. Uses `Gemma4Runtime` via `A00_MODEL_RUNTIME`.

**Out of scope** (archived for the current submission push):
- `kaggle/_archive/notebooks/A-01..A-24/`
- `kaggle/_archive/notebooks/03-duecare-video-pitch/`
- `docs/_archive/2026-05-16-legacy-notebook-era/` (5 legacy doc files)

Do not revive these.

## Canonical Gemma 4 runtime

All local inference goes through
`packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py::Gemma4Runtime.load(Gemma4LoadSpec(...))`.
The known-working Unsloth recipe:

```python
from unsloth import FastModel
model, tokenizer = FastModel.from_pretrained(
    model_name=resolved_model_ref,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
    device_map="balanced",  # for 26B/31B on 2x T4; "auto" otherwise
)
```

Backend generation defaults: `temperature=1.0`, `top_p=0.95`, `top_k=64`.
Chat template: `gemma-4-thinking`.

The **only acceptable direct `FastModel.from_pretrained`** in an active
kernel is inside `_training_script` in A-00 (training, not inference).

## Universal harness contract

`packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py` declares:

- `HarnessBase` Protocol — every harness exposes `name`,
  `applied_layers`, `register_routes(app)`.
- `BaseHarness` opt-in class — `compose`, `load_knowledge`,
  `emit_training_row`.
- `HarnessSpec` — `logic_paths`, `knowledge_packs`, `logic_packs`,
  `model_io`, `model_targets`, `input_verification`,
  `output_verification`, `privacy_boundaries`.
- `HarnessLogicPath`, `HarnessPackContract`, `HarnessModelTarget`.
- `MODEL_TRANSPORTS` (13): `none` / `callable` / `gemma4_runtime` /
  `duecare_model_adapter` / `transformers` / `unsloth` / `llama_cpp` /
  `ollama` / `openai_compatible` / `anthropic` / `google_gemini` /
  `hf_inference_endpoint` / `frontier_api`.
- `MODEL_CAPABILITIES` (16).

`packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`
provides `UniversalModelRequest`, `UniversalModelResponse`,
`normalize_model_messages(...)`, `call_model_backend(...)`. The portable
caller supports `duecare-llm-models` adapters with `.generate(...)`,
objects with `.chat(...)` or `.complete(...)`, and direct callables.

Registered harnesses in
`packages/duecare-llm-chat/src/duecare/chat/harnesses/__init__.py`:

**Primary (6):**
1. `chat` — free-form prompt with persona / GREP / RAG / tools / online / imports
2. `process` — bulk file review, graph extraction, graph-chat
3. `extraction` — drafts typed `KnowledgeObject` envelopes
4. `anonymization` — PII gate (regex-only by design; optional Gemma review)
5. `search_safety` — outbound query sanitization before third-party search
6. `post_search_verification` — verifies sanitized search results before prompt injection

**Secondary (2):**
7. `search` — runs sanitized search after `search_safety`
8. `import_corpus` — local evidence import utility

`/api/harnesses` serializes the full contract.
`/static/harness.html` renders it (including `trust_boundary` and
`notes` per model target since commit 76e44a1).

## Harness documentation trinity (read as a set)

Three documents define the DueCare harness system. All three now
cross-link to each other (since commit ab2e7a6):

- **`docs/harness_ecosystem.md`** — vocabulary, registered inventory,
  broader harness families, naming. **Authoritative** for the
  registered-harness inventory; if the other two disagree, update them
  to match this one.
- **`docs/harness_pattern.md`** — required module contract
  (`name`, `applied_layers`, `register_routes`), per-task JSONL
  training-data flow, 10-step recipe for adding a new registered harness.
- **`docs/harness_standard_contract.md`** — `HarnessSpec` field shape,
  the `HarnessLogicPath` / `HarnessPackContract` / `HarnessModelTarget`
  data classes, model-transport vocabulary.

Plus, for harness families beyond the registered:
- Core layer composer (persona + GREP + RAG + tools + online + imports)
- A-00 offline default proof harness (`chat_no_online`)
- Online grounding harness (privacy-gated)
- Post-search verification harness (implemented deterministic gate)
- Knowledge ingestion harness (import / extraction / governance)
- Research graph harness (entities, edges, timelines, risks)
- Synthetic data generator harness (A-00)
- Rubric-polish training-data harness (A-00)
- Fine-tuning / checkpoint harness (A-00 + duecare-llm-training)
- Evaluation / judge harness (rule, LLM, combined)
- Report / export harness (A-00)
- Model runtime primitive (`gemma4_runtime.py`)

## Recent commit chain (most recent first)

1. **`ab2e7a6` Cross-link harness doc trinity and archive legacy notebook-era docs** (this session)
   - Added "See also (the harness documentation trinity)" header to all
     three harness docs so reviewers find the others without grepping.
   - Moved 5 legacy notebook-era docs to
     `docs/_archive/2026-05-16-legacy-notebook-era/` with `git mv` so
     history is preserved. Archive README maps each file to its
     current replacement.

2. **`1bde14b` Tighten A00 tool dispatch trace and add focused review prompt** (this session)
   - `_format_shared_tool_call` widens `articles[:2]` to `articles[:4]`
     so C189 Art. 9 (travel / identity documents), C188 Art. 22 (no-fee
     fishing), and C190 Art. 9 (employer duties) surface in the
     rendered tool note.
   - `_build_harness_prompt` tracks `tools_had_error` independently of
     `tools_source`. New source value `heuristic_after_shared_error`.
     Step status stays `degraded` when shared raised, even after a
     heuristic recovery.
   - `test_process_and_extraction_harnesses_declare_local_gemma_default_target`
     now imports the modules and walks `spec.model_targets` so a
     regression that moved `default=True` off the local Gemma target
     would actually trip rather than passing on text presence.
   - Added `docs/claude_a00_tool_dispatch_and_trace_review_prompt.md`.

3. **`76e44a1` Harden A00 tool rendering and harness contract surface** (this session)
   - `_format_shared_tool_call` dispatches by tool name. Per-tool
     branches for `lookup_corridor_fee_cap`, `lookup_fee_camouflage`,
     `lookup_ilo_indicator`, `lookup_ngo_intake`, `lookup_ilo_convention`.
     Unknown tools fall through to a generic-key extractor.
   - `_build_harness_prompt` always emits `trace["tools"]` when the
     tools layer is enabled. Source markers: `skipped` / `shared` /
     `shared_empty` / `shared_error` / `heuristic`.
   - `harness.html` renders `trust_boundary` and `notes` per model
     target.
   - Six new contract tests in
     `tests/test_a00_runtime_and_parity_contract.py`.

4. **`aeec136` Add north-star Claude harness review prompt**
5. **`7b7d9d2` Add universal harness model targets**
6. **`3c04673` Standardize harness contract metadata**
7. **`4fe1933` Add Claude harness ecosystem review prompt**
8. **`f3bae04` Document DueCare harness ecosystem**

## A-00 preconfigured pipeline contract (current state)

`PipelineRequest` defaults in `kaggle/A-00-omni-experiment-workbench/kernel.py:1085`:

- `preset_id = "synthetic_train_benchmark_cycle"`
- `model_a_ref = A00_SMALL_MODEL_REF` (`google/gemma-4-2b-it`)
- `judge_model_source = "hf"` / `judge_model_ref = ""` /
  `judge_model_adapter_ref = ""` (judge defaults to local Gemma reuse)
- `harness_profile = "chat_no_online"` (Persona + GREP + RAG + tools, no internet)
- `baseline_harness_profile = "none"`
- `limit = 4` / `synthetic_count = 4`
- `execute_training = False` / `llm_judge = True` / `unload_between_steps = True`
- `training_save_steps = 10` / `training_save_total_limit = 3`
- `training_resume_from_checkpoint = ""`

External judge options (gated by env-var credentials):
- `_configure_ollama_judge_for_pipeline` (cloud requires `OLLAMA_API_KEY`)
- `_configure_anthropic_judge_for_pipeline` (requires `ANTHROPIC_API_KEY`)
- Both hand-roll HTTP via `requests.post(...)` today; future improvement
  is to route through `call_model_backend(...)` from `model_interface.py`.
  See "Suggested next work" below.

Activity log step ids (in `_run_pipeline_job`):
1. Check current model
2. Unload memory if needed
3. Check disk space
4. Clean disk if low
5. Download selected Gemma
6. Load via shared Unsloth FastModel
7. Preflight
8. Clear context
9. Run baseline (no harness)
10. Run harnessed
11. Generate synthetic training data
12. Fine-tune (optional)
13-14. Save / load adapter
15-16. Run fine-tuned arms
17. Unload fine-tuned
18. Load judge model
19. Combined rule + LLM judging
20. Generate final report
21. Save report

Report title is conditional: `stock vs stock+harness` when
`execute_training=False` or fewer than 4 arms ran; full
`stock/fine-tuned/harness matrix` only when both conditions are met.

## Files that matter most

Code:
- `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py`
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
  (10.6k lines — the canonical GREP rules, RAG corpus, tool dispatch,
  combined grading. **Do not rewrite GREP rules or RAG corpus.**)
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/*/__init__.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/_layers.py`
- `packages/duecare-llm-chat/src/duecare/chat/experiment_contracts.py`
- `packages/duecare-llm-chat/src/duecare/chat/app.py`
- `packages/duecare-llm-chat/src/duecare/chat/static/harness.html`
- `kaggle/01-duecare-exploration-workbench/kernel.py`
- `kaggle/02-live-demo/kernel.py`
- `kaggle/A-00-omni-experiment-workbench/kernel.py`

Docs to read first:
- `CLAUDE.md` (protected setup metadata — **flag changes, do not auto-edit**)
- `docs/model_loading_trace.md`
- `docs/harness_ecosystem.md` (authoritative inventory)
- `docs/harness_pattern.md`
- `docs/harness_standard_contract.md`

Tests:
- `tests/test_a00_runtime_and_parity_contract.py` (16 tests)
- `tests/test_a00_notebook_contract.py`
- `tests/test_harness_universal_model_contract.py`
- `tests/test_harness_standard_contract.py`
- `tests/test_harness_imports.py`
- `tests/test_harness_ecosystem_docs.py`
- `tests/test_compose_layers.py`
- `tests/test_per_harness_tools.py`
- `tests/test_route_contract.py`
- `tests/test_multi_harness_integration.py`
- `tests/test_ui_audit_contract.py`
- `tests/test_end_to_end_flywheel.py`
- `packages/duecare-llm-chat/tests/test_kaggle_kernel01_portability.py`
- `packages/duecare-llm-chat/tests/test_smoke.py`
- `packages/duecare-llm-chat/tests/test_harness_behavior.py`
- `packages/duecare-llm-chat/tests/test_harness_v3_6.py`
- `packages/duecare-llm-chat/tests/test_compare.py`
- `packages/duecare-llm-chat/tests/test_harness_workbench.py`
- `packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py`
- `packages/duecare-llm-models/tests/test_models_package_smoke.py`

## Suggested next work (ordered by impact)

Pick any one. Each is small enough to commit independently.

### 1. Migrate A-00 external judge factories to `call_model_backend`

`kaggle/A-00-omni-experiment-workbench/kernel.py:2057-2147` currently
hand-roll HTTP for Ollama and Anthropic. Replace with the
`model_interface.call_model_backend(...)` path so usage / latency /
tool calls normalize through `UniversalModelResponse`. Keep the
factories' callable-returning shape so `STATE["judge_model_call"]` and
`_grading_model_call` stay drop-in. Add a contract test that asserts
grading payloads carry `usage` keys when the judge supports it.
Estimated diff: ~80 LOC in kernel.py, ~30 LOC in tests.

### 2. Batch-2 legacy docs archive

Completed in a follow-up cleanup pass after this snapshot. The legacy
top-level docs were moved to
`docs/_archive/2026-05-16-legacy-notebook-era/`, incoming links were
rewired, and the archive README was updated:

- `docs/_archive/2026-05-16-legacy-notebook-era/notebook_index.md`
- `docs/_archive/2026-05-16-legacy-notebook-era/smoke_test_report_2026-05-02.md`
- `docs/_archive/2026-05-16-legacy-notebook-era/SUBMISSION_READINESS_AUDIT.md`

### 3. Align GREP and RAG layer step status with new `pass/noop/degraded`

In `kaggle/A-00-omni-experiment-workbench/kernel.py::_build_harness_prompt`,
the tools layer now emits `pass` / `noop` / `degraded` step statuses
(commit 76e44a1 + 1bde14b). Completed in a follow-up cleanup pass:
GREP and RAG now emit `noop` when they run but find zero hits/facts,
while exceptions still emit `degraded`.

### 4. `harness.html` external-trust-boundary visual cue

Completed in a follow-up cleanup pass. `/static/harness.html` now
renders model-target trust boundaries as explicit pills, with a
distinct external-boundary style pinned by a workbench test.

### 5. Post-search verification harness

Completed in commit 5c145ab. `harnesses/post_search_verification/` is
now a registered primary safety gate. It takes a sanitized query plus
normalized search result cards and emits accepted/review/blocked
envelopes with source-quality, relevance, contradiction, and
deanonymization signals. Default trust boundary is `local`, default
model transport is `none`. The harness is wired in
`packages/duecare-llm-chat/src/duecare/chat/app.py` and pinned by
`packages/duecare-llm-chat/tests/test_harness_workbench.py`. Out of
scope for the default A-00 proof path (Online stays off there).

### 6. Regenerate `docs/notebook_guide.md` to fix pre-existing test failures

Resolved in commit e2d3857 ("Reduce doc drift and tighten harness
traces"). `docs/notebook_guide.md` was regenerated against the active
three-kernel inventory and the four `tests/test_kaggle_notebook_utils.py`
tests now pass.

### 7. `tests/unit/*` collection errors

Pre-existing missing-module errors against `duecare.tasks`. Investigate
whether the missing package is intentional (it never shipped) or
whether it should be added / stubbed. Out of scope for harness / A-00
work unless Taylor asks.

## Hard constraints

- **Do not push to Kaggle.** Local validation only. Taylor handles
  Kaggle push manually.
- **Do not edit `CLAUDE.md`.** Protected setup metadata. If a finding
  requires a `CLAUDE.md` change, flag it and propose the diff inline.
- **Do not revive archived kernels** under `kaggle/_archive/notebooks/*`.
- **Do not revive archived docs** under
  `docs/_archive/2026-05-16-legacy-notebook-era/` without explicit
  reason.
- **Do not skip git hooks** with `--no-verify`. Fix the underlying issue.
- **Do not redesign the UI broadly.** Only touch the rendering block
  you are explicitly working on.
- **Do not rewrite GREP rules or RAG corpus** in
  `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`.
  You may read tool result schemas to validate dispatch.
- **Do not run long GPU loads** in local tests. Stay on contract /
  static / TestClient tests.

## Verification commands (PowerShell)

```powershell
cd C:\Users\amare\OneDrive\Documents\gemma4_comp
git fetch origin
git status --short --branch
git log --oneline -10

python -m py_compile kaggle\A-00-omni-experiment-workbench\kernel.py

$env:PYTHONPATH='packages/duecare-llm-models/src;packages/duecare-llm-chat/src;packages/duecare-llm-core/src'

# Focused north-star gate (~149 tests, ~15s):
python -m pytest `
  tests/test_a00_runtime_and_parity_contract.py `
  tests/test_a00_notebook_contract.py `
  tests/test_harness_universal_model_contract.py `
  tests/test_harness_standard_contract.py `
  tests/test_harness_imports.py `
  packages/duecare-llm-chat/tests/test_harness_workbench.py `
  packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py `
  packages/duecare-llm-models/tests/test_models_package_smoke.py `
  -q

# Broader regression sweep (~245 tests, ~3 min):
python -m pytest `
  packages/duecare-llm-chat/tests/test_kaggle_kernel01_portability.py `
  packages/duecare-llm-chat/tests/test_smoke.py `
  packages/duecare-llm-chat/tests/test_harness_behavior.py `
  packages/duecare-llm-chat/tests/test_harness_v3_6.py `
  packages/duecare-llm-chat/tests/test_compare.py `
  tests/test_compose_layers.py `
  tests/test_per_harness_tools.py `
  tests/test_route_contract.py `
  tests/test_multi_harness_integration.py `
  tests/test_ui_audit_contract.py `
  tests/test_end_to_end_flywheel.py `
  tests/test_harness_ecosystem_docs.py `
  -q
```

## Available specialized review prompts

If you want a fresh deep-audit, paste any of these into a fresh chat:

- `docs/claude_north_star_harness_review_prompt.md` — universal model
  contract / model_targets / checkpoint readiness.
- `docs/claude_harness_ecosystem_a00_review_prompt.md` — harness
  ecosystem language + broader inventory.
- `docs/claude_omni_fastmodel_review_prompt.md` — original Gemma 4
  runtime + A-00 preconfigured pipeline parity.
- `docs/claude_a00_tool_dispatch_and_trace_review_prompt.md` — most
  recent: per-tool dispatch + tools-layer trace consistency +
  harness.html model-target surface + the six new contract tests.

## What Claude finished this session

- Verified commit 76e44a1 against the actual `_tool_lookup_*` result
  schemas. Found three real issues:
  1. `articles[:2]` silently dropped C189 Art. 9, C188 Art. 22, C190
     Art. 9 — the most-cited articles for kafala / fishing / employer
     duty discussions. Fixed by widening to `articles[:4]` to match
     the data-table cap. Per-article truncation widened from 200 to
     240 chars to fit the full article text.
  2. `tools_source` was overwritten to `"heuristic"` when the
     heuristic recovered after a shared `_tools_call` failure,
     hiding the partial failure from step status. Fixed by tracking
     `tools_had_error` independently and adding the explicit
     `heuristic_after_shared_error` source value. Step status stays
     `degraded` whenever shared raised.
  3. The process/extraction default-target test was string-presence
     only. Tightened to import each harness module and walk
     `spec.model_targets`, asserting the default target's transport
     is `gemma4_runtime` or `none` and trust boundary is `local`.
- Cross-linked the harness documentation trinity so reviewers find
  all three docs from any one of them.
- Archived 5 clearly-legacy notebook-era docs to
  `docs/_archive/2026-05-16-legacy-notebook-era/` with an explanatory
  README. Used `git mv` so history follows.
- Landed three commits: `76e44a1`, `1bde14b`, `ab2e7a6`.
- All 394 in-scope tests still green. The 3 pre-existing
  `tests/test_kaggle_notebook_utils.py` failures are unrelated and
  predate this session.

You are now in a good place to pick any item from "Suggested next work"
without unblocking work. Start with item 1, 2, or 4 — they are the
smallest and most independent.
