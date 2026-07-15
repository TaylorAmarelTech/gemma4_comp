# Claude Code Prompt: North-Star Harness, Runtime, and A-00 Review

Copy/paste this into Claude Code from the repo root:

```text
You are Claude Code working in:
C:\Users\amare\OneDrive\Documents\gemma4_comp

Read these first:
- CLAUDE.md
- docs/model_loading_trace.md
- docs/harness_ecosystem.md
- docs/harness_standard_contract.md
- docs/harness_pattern.md
- docs/claude_omni_fastmodel_review_prompt.md
- docs/claude_harness_ecosystem_a00_review_prompt.md

Context:
We consolidated the project around three active Kaggle kernels:
- kaggle/01-duecare-exploration-workbench
- kaggle/02-live-demo
- kaggle/A-00-omni-experiment-workbench

The remaining archived scope is intentional:
- kaggle/03-duecare-video-pitch is archived for this push.
- Retired notebook-era surfaces are archived for this push.
- Do not revive archived notebooks, broad Kaggle publishing, or unrelated packages unless a failing contract directly requires it.

Recent implemented direction:
- Local Gemma 4 inference should load through duecare.chat.gemma4_runtime.Gemma4Runtime.load().
- Known-good local Gemma recipe is Unsloth FastModel with dtype=None, load_in_4bit=True, full_finetuning=False, gemma-4-thinking, temperature=1.0, top_p=0.95, top_k=64, and device_map balanced for large 2x T4 models.
- The registered harness ecosystem now exposes HarnessSpec logic_paths, knowledge_packs, logic_packs, model_io, model_targets, input_verification, output_verification, and privacy_boundaries.
- packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py now provides UniversalModelRequest, UniversalModelResponse, normalize_model_messages(), and call_model_backend().
- /api/harnesses and /static/harness.html should expose model_targets.
- A-00 default proof path should use Kernel 01 comparison parity: baseline none, treatment chat_no_online, same GREP/RAG/tools/persona/default grading primitives, no internet/import in the default proof path.
- A-00 should be easy: home page has two cards only, Preconfigured Harness/Training/Evaluation and Custom. Preconfigured exposes only the selected model and prompt count before run. Advanced controls belong on Custom.

Goal:
Review the current codebase and continue making targeted edits toward a north-star configuration:
1. Harnesses are universal, provider-neutral, and testable.
2. Local Kaggle proof runs still use the stable Gemma4Runtime/FastModel path.
3. Harnesses can also work with DueCare model adapters, Ollama, OpenAI-compatible endpoints, Anthropic, Gemini, HF endpoints, local transformers/Unsloth/llama.cpp, or no model where appropriate.
4. No duplicated hardcoded harness logic should diverge from the canonical Kernel 01 comparison/default_harness primitives.
5. A-00 should produce reproducible, downloadable, review-ready evidence: activity log, prompts, responses, traces, grades, synthetic rows, training logs/checkpoints, adapter paths, report HTML/Markdown/JSON, and a zip bundle under /kaggle/working.
6. Long A-00 runs should be resumable or at least checkpoint-safe before Kaggle's runtime limit.

Review and edit these primary files:
- packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py
- packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
- packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py
- packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py
- packages/duecare-llm-chat/src/duecare/chat/harnesses/*/__init__.py
- packages/duecare-llm-chat/src/duecare/chat/harnesses/_layers.py
- packages/duecare-llm-chat/src/duecare/chat/experiment_contracts.py
- packages/duecare-llm-chat/src/duecare/chat/app.py
- packages/duecare-llm-chat/src/duecare/chat/static/harness.html
- kaggle/01-duecare-exploration-workbench/kernel.py
- kaggle/02-live-demo/kernel.py
- kaggle/A-00-omni-experiment-workbench/kernel.py
- tests/test_harness_standard_contract.py
- tests/test_harness_universal_model_contract.py
- tests/test_a00_runtime_and_parity_contract.py
- tests/test_a00_notebook_contract.py
- packages/duecare-llm-chat/tests/test_harness_workbench.py
- packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py

North-star checks:
1. Runtime/model abstraction
   - Confirm Kernel 01, Kernel 02, and A-00 inference paths use Gemma4Runtime.load() for local Gemma inference.
   - Confirm direct FastModel.from_pretrained inference paths do not bypass Gemma4Runtime, except A-00 fine-tuning scripts where FastModel.get_peft_model() is required.
   - Confirm model_interface.py can normalize strings, chat messages, duecare.core ChatMessage objects, DueCare model adapters, .chat/.complete objects, and direct callables.
   - Improve model_interface.py if it lacks clean error handling, usage extraction, tool-call extraction, or provider-neutral generation parameters.

2. Universal harness contract
   - Every registered harness must declare model_targets with realistic transport, role, capabilities, trust_boundary, and default/required flags.
   - Harnesses with deterministic defaults must keep transport="none" as default.
   - External/frontier targets must explicitly document privacy boundary and credential env vars.
   - /api/harnesses must serialize the full contract.
   - /static/harness.html must make the contract understandable without overwhelming reviewers.

3. Harness parity and no divergence
   - Trace Kernel 01 comparison/default harness setup.
   - Trace A-00 preconfigured path: /preconfigured -> JS run function -> /api/a00/pipeline/run -> PipelineRequest -> _run_pipeline_job().
   - Confirm A-00 chat_no_online uses the same Persona + GREP + RAG/context + deterministic tool primitives as Kernel 01, with internet/import off.
   - Remove or adapt duplicated local fallbacks only if they risk divergence. Keep defensive fallbacks when they protect Kaggle runs, but label them as fallbacks in traces.
   - Confirm A-00 grading uses the same combined rule + LLM grading primitives as Kernel 01.

4. A-00 UX and evidence artifacts
   - Home page must remain two navigation cards only.
   - Preconfigured page should expose only selected Gemma model and prompt count before run.
   - No duplicate model-selection lightbox if the model was already selected on the page.
   - Activity log should show explicit numbered steps, substeps, exact prompt IDs/text, response excerpts/full artifacts links, model load/unload events, training progress, grading progress per prompt/run, and saved artifact paths.
   - Add or verify download links for report HTML/Markdown/JSON, full activity log, run bundle zip, prompts/responses JSONL, grades JSON/CSV, synthetic rows, training logs, and checkpoint/adapter paths.
   - Make sure artifacts are clearly saved under /kaggle/working, preferably /kaggle/working/a00_runs and /kaggle/working/a00_training.

5. Checkpoints and long runs
   - Confirm A-00 training script saves checkpoints at a reasonable interval.
   - Confirm resume_from_checkpoint is supported where possible.
   - Confirm the activity/report bundle records checkpoint paths and adapter output paths.
   - If missing, add minimal checkpoint/resume configuration and tests/contracts.
   - Do not add huge training defaults. Keep default fast, but make longer runs clearly configurable in Custom or advanced settings.

6. External judge/provider options
   - Keep Kaggle default runnable without paid API keys.
   - If external judges are exposed, they must be optional and gated by credentials.
   - Add clearly labeled options/contracts for Ollama/OpenAI-compatible/Anthropic/Gemini/frontier grading if the architecture already supports it.
   - Do not send raw PII to external endpoints. Require anonymization/search_safety gates for any external boundary.

7. Tests/contracts
   - Add or update focused tests for every behavior you change.
   - Prefer contract tests that prevent regression without running GPU model loads.
   - Suggested gates:
     python -m py_compile packages/duecare-llm-chat/src/duecare/chat/harnesses/base.py packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py packages/duecare-llm-chat/src/duecare/chat/app.py kaggle/A-00-omni-experiment-workbench/kernel.py
     $env:PYTHONPATH='packages/duecare-llm-chat/src;packages/duecare-llm-core/src;packages/duecare-llm-models/src'; python -m pytest tests/test_harness_universal_model_contract.py tests/test_harness_standard_contract.py tests/test_harness_imports.py packages/duecare-llm-chat/tests/test_harness_workbench.py packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py tests/test_a00_runtime_and_parity_contract.py tests/test_a00_notebook_contract.py packages/duecare-llm-models/tests/test_models_package_smoke.py -q

Output requirements:
- Start with findings ordered by severity with file/line references.
- Then make targeted edits directly in the repo.
- Preserve the working Gemma4Runtime/FastModel path.
- Do not broaden scope into archived notebooks.
- Do not rewrite unrelated UI or package infrastructure.
- After edits, run the focused tests above.
- If full-suite tests fail on unrelated pre-existing cross-package issues, list them separately and do not block the harness/A-00 change on them.
- End with:
  - Summary of edits.
  - Tests run and results.
  - Remaining risks.
  - Verdict: PASS, PARTIAL, or FAIL.
```
