# Canonical Gemma 4 runtime + harness abstraction + workbench UI source of truth

> Auto-loaded by Claude Code at the project memory level. Extracted
> from CLAUDE.md so the per-rule files stay scoped.

## Canonical Gemma 4 runtime and A-00 proof path (2026-05-16)

The source of truth for local Gemma 4 loading is
`packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py` and the trace
doc at `docs/model_loading_trace.md`.

All active Kaggle kernels must use the shared `Gemma4Runtime.load()` primitive
for inference model loading. It follows the known-working Unsloth FastModel
recipe:

```python
from unsloth import FastModel

model, tokenizer = FastModel.from_pretrained(
    model_name=resolved_model_ref,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
    device_map=device_map,  # "balanced" for 31B / 26B-A4B on 2x T4; "auto" otherwise
)
```

After loading, the runtime applies `get_chat_template(...,
chat_template="gemma-4-thinking")`; generation defaults to
`temperature=1.0`, `top_p=0.95`, and `top_k=64`.

Path trace:

- Kernel 01: `/api/load-model` -> `load_gemma()` -> `Gemma4Runtime.load()`.
- Kernel 02: `/api/live/model/load` and startup -> `load_gemma_shared()` ->
  `_LIVE_MODEL_RUNTIME.load()`.
- A-00: `/api/a00/pipeline/run` -> `_create_pipeline_job()` ->
  `_run_pipeline_job()` -> `_prepare_base_model_for_pipeline()` /
  `_load_model_runtime()` -> `A00_MODEL_RUNTIME.load()`.

A-00 fine-tuning is the exception because adapter training uses the Unsloth
training path, not the inference path: `FastModel.from_pretrained()` ->
`FastModel.get_peft_model()` -> `SFTTrainer/SFTConfig` ->
`train_on_responses_only()`.

### A-00 preconfigured pipeline contract

- No dry-run default. The selected Gemma model loads automatically when the
  user starts the preconfigured pipeline.
- No top-banner model/custom buttons. The banner can show status and shutdown
  only if needed; model choice lives in the page body.
- Default model path is the small Gemma path for Kaggle T4 proof runs
  (`google/gemma-4-2b-it` resolving to `unsloth/gemma-4-E2B-it` unless a
  Kaggle-attached model exists).
- Default prompt set is `chat_safety_core`, default prompt count is 2 for the
  fastest real smoke proof.
- Baseline arm uses `baseline_harness_profile="none"`.
- Harnessed arms use `harness_profile="chat_no_online"`: Persona + GREP +
  RAG/context + deterministic tools. Internet and Import are off for the
  default proof path.
- Final scoring uses the same grading primitives as Kernel 01:
  `duecare.chat.harness.grade_response_combined` and
  `grade_response_universal`, with combined rule + LLM judging at the end.
- The activity log should show clear user-facing steps: check loaded model,
  unload/clear memory if needed, check/clean disk, download/load selected
  model with shared FastModel runtime, preflight generation, run baseline,
  run harnessed, generate synthetic rows, fine-tune, save adapter, load
  adapter, run fine-tuned baseline/harnessed arms, reload normal Gemma for
  grading, run combined grading, generate report, save report.

Kernel 01 comparison page remains the behavior reference for harness parity:
`create_app(**default_harness())` wires Persona, GREP, RAG, Tools, and Online
surfaces; A-00's preconfigured proof intentionally uses the offline subset
`chat_no_online` so the run is reproducible and does not require web/search
credentials.

## Universal harness/model abstraction (2026-05-16)

Do not describe DueCare as one hardcoded Gemma harness. The registered
harnesses expose a provider-neutral contract through `HarnessSpec`:

- `logic_paths`: named workflow paths and verification checks.
- `knowledge_packs`: facts/context a harness consumes.
- `logic_packs`: prompts, schemas, tools, rubrics, and backend registries.
- `model_io`: what reaches a model and what comes back.
- `model_targets`: local Gemma, DueCare adapter, Ollama,
  OpenAI-compatible, Anthropic, Gemini, HF endpoint, frontier API, callable,
  or no-model targets.
- `input_verification`, `output_verification`, and `privacy_boundaries`.

The implementation source is
`packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py`.
The portable model caller is
`packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`.

For Kaggle proof runs, local Gemma 4 still uses `Gemma4Runtime.load()`.
For broader deployments, harnesses should call a configured model through
the universal request/response shape or a `duecare-llm-models` adapter rather
than hardcoding a provider-specific SDK in a route handler. External frontier
targets must receive only redacted, generalized, or policy-approved content.

## Workbench model-loading UI source of truth (2026-05-19)

Kernel 01 uses one universal browser-side model service. Do not add model
selectors, load buttons, logs, or lightboxes directly to individual pages.

Source files:

- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html`
- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js`
- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
- `packages/duecare-llm-chat/src/duecare/chat/static/models.html`

Contract:

- The top status strip shows only concise model state.
- The body-level model layer owns the selector, progress bar, status text,
  load log, refresh, close, and load-selected actions.
- Pages call `window.dcWbModelService.open()`, `.refresh()`,
  `.loadSelected()`, `.loadVariant(id)`, `.ensureReady()`, or `.status()`.
- `_nav.js` removes stale duplicate chrome if older templates inject more than
  one shell or a nested model popover.
- Tests that cover this contract live in
  `packages/duecare-llm-chat/tests/test_compare.py` and
  `packages/duecare-llm-chat/tests/test_harness_workbench.py`.

## Multi-harness architecture (2026-05-14)

Every reviewer-facing safety surface in the kernel is a harness module: a
self-contained component exposing `name`, `applied_layers: tuple[str, ...]`,
`consumes`, `emits`, and `register_routes(app)`.

Current contract:

- PRIMARY Gemma-backed harnesses: `chat`, `process`, `extraction`
- PRIMARY hard safety gates: `anonymization`, `search_safety`, `post_search_verification`
- SECONDARY utilities: `search`, `import_corpus`

Use the word "harness" carefully. `search` and `import_corpus` are utility
surfaces unless they are feeding a Gemma-backed harness. `anonymization` and
`search_safety` are safety gates because their main job is protecting trust
boundaries before model or third-party calls.

Bulk File Review is now the process harness name. It accepts ZIP, CSV, JSONL,
text, images, and PDFs. Text and extractable PDF pages are chunked locally.
Scanned PDFs and images become explicit OCR plus Gemma 4 vision work items so
the UI never pretends a media file has been read when it has only been queued.

Each handler should call `harnesses._training_log.log_interaction(...)` at
completion when it produces model-relevant input or output. The harness
boundary is also the per-task fine-tuning data boundary: one JSONL stream per
harness at `/kaggle/working/training/<harness>.jsonl`.

Full pattern plus 10-step recipe for new harnesses and multi-rubric review:
@docs/harness_pattern.md

Broader project inventory and wording rules:
@docs/harness_ecosystem.md

Standard fields for generalized logic paths, knowledge packs, logic packs,
model I/O, input/output verification, and privacy boundaries:
@docs/harness_standard_contract.md

### A-00 synthetic data and small-model retraining

A-00 is the control plane for technical proof. It should be able to:

- generate rubric-polished SFT and DPO rows with `generator_mode=rubric_polisher`
- mark stable knowledge for memorization and volatile facts for tool calls
- create a tiny E2B or E4B fine-tune smoke job before a full Kaggle GPU run
- export prompt, response, trace, grade, timing, cost, and provenance bundles

Training data should teach structure, not stale phone numbers. Memorize stable
reasoning habits, refusal behavior, ILO indicator categories, privacy
boundaries, and evidence-first response shape. Use tools or vetted knowledge
packs for hotline numbers, addresses, current advisories, fee caps, wage rules,
and fresh statutes.

### Naming convention (post-Phase 9)

The word **"harness"** is used three ways. Be explicit:

| Term | Refers to | Example |
|---|---|---|
| **harness module** | A subfolder under `harnesses/<name>/` | `chat/`, `process/`, `extraction/` |
| **safety layer** | One callable in `applied_layers` tuple | "the GREP layer fired" |
| **harness ecosystem** | The full DueCare substrate around Gemma 4: runtime, privacy, search, graph, synthetic-data, training, judging, and report harnesses | "DueCare is a Gemma 4 harness ecosystem" |

The legacy singular module `duecare.chat.harness` (no `s`) is the
ORIGINAL implementation — `default_harness()`, `GREP_RULES`, `RAG_CORPUS`,
`_TOOL_DISPATCH`. New work goes in `duecare.chat.harnesses` (with `s`).
Both coexist; see @docs/MIGRATION_HARNESS_PATTERN.md.
