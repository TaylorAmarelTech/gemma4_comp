# Codex handoff — DueCare Gemma 4 (snapshot 2026-05-17, HEAD=965e1f9)

Paste this into your Codex session when picking up DueCare work after
the Claude Code pass that ended at commit `965e1f9`. Self-contained —
you do not need the prior session's chat history.

---

## Where we are right now

Repo: `C:\Users\amare\OneDrive\Documents\gemma4_comp`
Branch: `master`, clean, in sync with `origin/master`.
HEAD: `965e1f9 Bump A00 inference context to 16K for grading and full-harness prompts`

Test baseline (last verified at HEAD=965e1f9):

- North-star contract gate: **173 passed** (16K context test added in this commit)
- Broader regression sweep: **243 passed**
- Combined: **416 tests passing**, 0 failures from current scope

Pre-existing `tests/unit/*` collection errors are unrelated missing-
module errors against `duecare.tasks` and stay out of scope unless
explicitly asked.

## Active scope

Three Kaggle kernels are the entire competition surface:

- `kaggle/01-duecare-exploration-workbench/kernel.py` — interactive
  reviewer workbench. Uses `duecare.chat.create_app(**default_harness())`.
- `kaggle/02-live-demo/kernel.py` — focused demo. Uses
  `_LIVE_MODEL_RUNTIME = Gemma4Runtime(...)` and `duecare.server.create_app`.
- `kaggle/A-00-omni-experiment-workbench/kernel.py` — quantitative
  control plane (benchmark / synthetic-data / fine-tune / judge / report).
  Uses `A00_MODEL_RUNTIME = Gemma4Runtime(...)`.

Archived (do not revive):
- `kaggle/_archive/notebooks/A-01..A-24/`
- `kaggle/_archive/notebooks/03-duecare-video-pitch/`
- `docs/_archive/2026-05-16-legacy-notebook-era/`

## Canonical Gemma 4 runtime

All inference goes through
`packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py::Gemma4Runtime.load(Gemma4LoadSpec(...))`.
Unsloth recipe:

```python
from unsloth import FastModel
model, tokenizer = FastModel.from_pretrained(
    model_name=resolved_model_ref,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
    device_map="balanced",  # 26B/31B on 2x T4; "auto" otherwise
)
```

Backend defaults: `temperature=1.0`, `top_p=0.95`, `top_k=64`. Chat
template: `gemma-4-thinking`. The **only** acceptable direct
`FastModel.from_pretrained` in an active kernel is inside
`_training_script` in A-00 (training, not inference).

A-00 inference is now loaded at **16384** max_seq_length via
`A00_INFERENCE_MAX_SEQ_LENGTH = int(os.environ.get(
"DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH", "16384"))` so the combined
rule + LLM judge has enough context for the 17-dimension rubric, full
prompt, full response, and harness trace without silent truncation.

## Universal harness contract

`packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py` exports:
- `HarnessBase` Protocol — every harness exposes `name`,
  `applied_layers`, `register_routes(app)`.
- `BaseHarness` opt-in class.
- `HarnessSpec` with `logic_paths`, `knowledge_packs`, `logic_packs`,
  `model_io`, `model_targets`, `input_verification`,
  `output_verification`, `privacy_boundaries`.
- `MODEL_TRANSPORTS` (13) and `MODEL_CAPABILITIES` (16).

`packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`
provides `UniversalModelRequest`, `UniversalModelResponse`,
`normalize_model_messages(...)`, `call_model_backend(...)` — supports
`duecare-llm-models` adapters with `.generate(...)`, objects with
`.chat(...)` or `.complete(...)`, and direct callables.

Registered harnesses in
`packages/duecare-llm-chat/src/duecare/chat/harnesses/__init__.py`:

**Primary (6):**
1. `chat` — persona / GREP / RAG / tools / online / imports
2. `process` — bulk file review, graph extraction, graph-chat
3. `extraction` — drafts typed `KnowledgeObject` envelopes
4. `anonymization` — regex PII gate; optional Gemma review
5. `search_safety` — outbound query sanitization
6. `post_search_verification` — verifies search results before prompt injection

**Secondary (2):**
7. `search` — sanitized search execution
8. `import_corpus` — local evidence import

External judge factories (Ollama / Anthropic) route through
`call_model_backend(...)` via `_OllamaJudgeBackend` and the
`model_interface` shape — no hand-rolled HTTP remaining.

## Harness documentation trinity

Three docs define the system, all cross-linked at the top:
- `docs/harness_ecosystem.md` — authoritative inventory.
- `docs/harness_pattern.md` — module contract + 10-step recipe.
- `docs/harness_standard_contract.md` — `HarnessSpec` field shape.

If they disagree about a registered harness, `harness_ecosystem.md`
wins. Update the other two to match it.

## Recent commit chain (most recent first)

1. **`965e1f9` Bump A00 inference context to 16K** (last commit)
   - New constant `A00_INFERENCE_MAX_SEQ_LENGTH` (default 16384,
     env-overridable via `DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH`).
   - `_load_model_runtime` now passes the constant to
     `Gemma4LoadSpec.max_seq_length` instead of the training profile's
     4096. Training script keeps its own (intentionally tighter)
     max_seq_length on the smoke LoRA profile.
   - `test_a00_inference_uses_at_least_16k_context_window` pins the
     invariant (constant exists, defaults >= 16384, referenced inside
     `_load_model_runtime`, old training fallback no longer reachable
     from the inference loader).

2. **`37b8b67` Refresh handoff and neutralize archived-kernel doc references**
   - `docs/copilot_handoff_2026_05_16.md` Suggested next work items #5
     (PSV harness) and #6 (notebook_guide regeneration) marked
     complete with pointers to the implementing commits.
   - `docs/harness_pattern.md` example uses neutral
     `knowledge-builder-kernel` instead of archived `A-04`.
   - `docs/maintenance/online_search.md` no longer cites archived
     `A-09` as if active.

3. **`5c145ab` Harden harness drift contracts**
   - Removed fragile inventory counts from active docs.
   - Slimmed `apps/duecare-ai.com/app/templates/kernels.html` from
     ~280 to ~84 lines.
   - Migrated external judge factories to `call_model_backend`.
   - Tightened multiple test pins.

4. **`73c220a` Archive superseded notebook ADRs**
5. **`e0c3643` Archive legacy status docs and refresh current narrative**
6. **`6def92e` Reconcile current docs with A00 proof path**
7. **`e2d3857` Reduce doc drift and tighten harness traces** (regenerated `notebook_guide.md`)
8. **`5a8027e` Fix Copilot handoff HEAD metadata**
9. **`8141134` Add Copilot handoff snapshot for 2026-05-16 session**
10. **`ab2e7a6` Cross-link harness doc trinity and archive legacy notebook-era docs**

## A-00 preconfigured pipeline contract

`PipelineRequest` defaults at
`kaggle/A-00-omni-experiment-workbench/kernel.py:1085`:

- `preset_id = "synthetic_train_benchmark_cycle"`
- `model_a_ref = A00_SMALL_MODEL_REF` (`google/gemma-4-2b-it`)
- `judge_model_source = "hf"` (local Gemma reuse by default)
- `harness_profile = "chat_no_online"` (Persona + GREP + RAG + tools, no internet)
- `baseline_harness_profile = "none"`
- `limit = 4` / `synthetic_count = 4`
- `execute_training = False` / `llm_judge = True` / `unload_between_steps = True`
- `training_save_steps = 10` / `training_save_total_limit = 3`

External judges (env-var gated):
- `_configure_ollama_judge_for_pipeline` — requires `OLLAMA_API_KEY` for cloud
- `_configure_anthropic_judge_for_pipeline` — requires `ANTHROPIC_API_KEY`

Both now route through `call_model_backend(...)` from
`duecare.chat.harnesses.model_interface`.

Activity log: 21 numbered steps from model check through final report
save. Step 18 loads the judge model; step 19 runs combined rule + LLM
judging via `grade_response_combined` from `duecare.chat.harness`.
Report title is conditional (`stock vs stock+harness` vs full
`stock/fine-tuned/harness matrix`) based on whether
`execute_training=True` and at least 4 arms ran.

## Files that matter most

Code:
- `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py`
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
  (~10.6k lines, canonical GREP rules + RAG corpus + tool dispatch +
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
- `CLAUDE.md` (**protected setup metadata — flag changes, do not auto-edit**)
- `docs/system_components_and_critical_paths.md`
- `docs/model_loading_trace.md`
- `docs/harness_ecosystem.md` / `docs/harness_pattern.md` / `docs/harness_standard_contract.md`

Available specialized review prompts:
- `docs/claude_north_star_drift_review_prompt.md` — drift-hardening audit
- `docs/claude_north_star_harness_review_prompt.md` — universal contract / model_targets / checkpoint
- `docs/claude_harness_ecosystem_a00_review_prompt.md` — ecosystem language + inventory
- `docs/claude_omni_fastmodel_review_prompt.md` — original runtime parity
- `docs/claude_a00_tool_dispatch_and_trace_review_prompt.md` — per-tool dispatch + trace consistency
- `docs/copilot_handoff_2026_05_16.md` — broader handoff with more context

## One outstanding flag

**`CLAUDE.md:279`** — primary safety gates list is stale. Apply this
diff manually (CLAUDE.md is protected setup metadata that should not
be auto-edited):

```diff
- - PRIMARY hard safety gates: `anonymization`, `search_safety`
+ - PRIMARY hard safety gates: `anonymization`, `search_safety`, `post_search_verification`
```

## Suggested next work

Pick any of these. Each is small enough to commit independently.

1. **Apply the CLAUDE.md primary-gates diff** (above). Single-line fix
   to bring the protected metadata in sync with the registered
   inventory.

2. **`harness.html` external-trust-boundary visual cue** — verify the
   recent pill/color treatment renders clearly across all 8 harnesses
   on the page, especially for `chat`'s `frontier_chat_or_judge`
   target and `post_search_verification`'s `external_result_reviewer`.

3. **Add a grading-budget sanity test.** With the new 16K context,
   verify the LLM judge in `_combined_grade` still has enough
   `max_new_tokens` (currently `900` at kernel.py around line 2534)
   to emit per-dimension scores + rationales for all 17 rubric
   dimensions. If the JSON output ever truncates, scores drop. A
   contract test that bounds `max_new_tokens >= 1500` (or measures
   the worst-case output length) would prevent silent regression.

4. **`tests/unit/*` collection errors.** Investigate whether the
   missing `duecare.tasks` module is intentional or should be added /
   stubbed. Out of scope for harness / A-00 work unless Taylor asks.

5. **Document the new env override** in
   `docs/system_components_and_critical_paths.md` or
   `docs/model_loading_trace.md` — `DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH`
   should be listed alongside the other A-00 env knobs
   (`A00_TRAINING_TIMEOUT_SEC`, `DUECARE_A00_ALLOW_DRY_RUN`,
   `DUECARE_A00_SMALL_MODEL_REF`, etc.) so reviewers can find it.

## Hard constraints

- **Do not push to Kaggle.** Local validation only. Taylor pushes manually.
- **Do not edit `CLAUDE.md`.** Protected setup metadata. Flag the diff;
  do not apply it.
- **Do not revive archived kernels** under `kaggle/_archive/notebooks/*`.
- **Do not revive archived docs** under
  `docs/_archive/2026-05-16-legacy-notebook-era/` without explicit reason.
- **Do not skip git hooks** with `--no-verify`. Fix the underlying issue.
- **Do not redesign UI broadly.** Touch only what you are explicitly working on.
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

$env:PYTHONPATH = 'packages/duecare-llm-models/src;packages/duecare-llm-chat/src;packages/duecare-llm-core/src'

# Focused north-star gate (~173 tests, ~13s):
python -m pytest `
  tests/test_a00_runtime_and_parity_contract.py `
  tests/test_a00_notebook_contract.py `
  tests/test_harness_universal_model_contract.py `
  tests/test_harness_standard_contract.py `
  tests/test_harness_imports.py `
  tests/test_harness_ecosystem_docs.py `
  packages/duecare-llm-chat/tests/test_harness_workbench.py `
  packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py `
  packages/duecare-llm-models/tests/test_models_package_smoke.py `
  -q

# Broader regression sweep (~243 tests, ~3 min):
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
  -q
```

## What Claude finished in the prior session

- **16K inference context.** Added `A00_INFERENCE_MAX_SEQ_LENGTH` with
  env override, wired through `_load_model_runtime`, pinned by a new
  contract test. Grading and full-harness prompts no longer silently
  truncate.
- **Drift cleanup.** Refreshed stale "Suggested next work" items in
  the Copilot handoff (PSV harness done, notebook_guide regenerated),
  neutralized archived `A-04` and `A-09` references in active docs.
- **Confirmed three "residual cracks" already resolved upstream:**
  external judge factories now use `call_model_backend`, GREP/RAG step
  status now emits `pass/noop/degraded` aligned with the tools layer,
  and three legacy docs already moved to `_archive/`.

Pick from "Suggested next work" — items 1 and 5 are the smallest;
item 3 is the most directly load-bearing if you want to harden the
grading path further.

Commit pushed: `965e1f9`. Working tree clean. Tests green.
