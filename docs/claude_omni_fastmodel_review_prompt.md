# Copy/Paste Prompt For Claude Code: A-00 FastModel + Harness Parity Review

You are Claude Code working in:

`C:\Users\amare\OneDrive\Documents\gemma4_comp`

Please read `CLAUDE.md` first, then read `docs/model_loading_trace.md`.

Task: perform a focused code review of the Gemma 4 model loading path and the A-00 omni experiment workbench preconfigured pipeline. I need to know whether A-00 truly follows the same runtime, harness configuration, prompt/response paths, and grading primitives as the Kernel 01 exploration workbench comparison page.

Scope:

- `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py`
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
- `packages/duecare-llm-chat/src/duecare/chat/experiment_contracts.py`
- `packages/duecare-llm-chat/src/duecare/chat/app.py`
- `kaggle/01-duecare-exploration-workbench/kernel.py`
- `kaggle/02-live-demo/kernel.py`
- `kaggle/A-00-omni-experiment-workbench/kernel.py`
- Relevant tests under `packages/duecare-llm-chat/tests/` and `tests/`

Questions to answer:

1. Model loading parity:
   - Does Kernel 01 load local Gemma 4 through `Gemma4Runtime.load()`?
   - Does 02 live demo load local Gemma 4 through `Gemma4Runtime.load()`?
   - Does A-00 load local Gemma 4 through `A00_MODEL_RUNTIME.load()` / `Gemma4Runtime.load()`?
   - Are there any active direct `FastModel.from_pretrained(...)` inference paths that bypass `Gemma4Runtime`, other than the A-00 fine-tuning script where `FastModel.get_peft_model()` is required?
   - Does `Gemma4Runtime` match the known-working Unsloth FastModel recipe: `dtype=None`, `load_in_4bit=True`, `full_finetuning=False`, `device_map="balanced"` for 31B/26B-A4B on 2x T4, `gemma-4-thinking` chat template, `temperature=1.0`, `top_p=0.95`, `top_k=64`?

2. Kernel 01 comparison-page behavior:
   - Trace how Kernel 01 wires the comparison page and chat harness via `create_app(**default_harness())`.
   - Identify the actual request/API path used by `/static/compare.html`.
   - Identify which layers are enabled for the comparison page defaults.
   - Confirm which grading functions Kernel 01 uses for rule-based, LLM-based, and combined scoring.

3. A-00 preconfigured pipeline parity:
   - Trace `/preconfigured` UI -> `runPreconfiguredPipeline()` -> `/api/a00/pipeline` -> `PipelineRequest` -> `_run_pipeline_job()`.
   - Confirm the default selected model, prompt set, prompt count, baseline harness, treatment harness, synthetic row count, training behavior, and final grading mode.
   - Confirm the default harnessed path is `chat_no_online`: Persona + GREP + RAG/context + deterministic tools; no internet and no import.
   - Confirm the baseline path is truly no harness.
   - Confirm final scoring uses `duecare.chat.harness.grade_response_combined` / `grade_response_universal`, the same grading primitives as Kernel 01.
   - Confirm the final report compares all intended arms: base without harness, base with harness, fine-tuned without harness, fine-tuned with harness.

4. User clarity and runtime UX:
   - Does the A-00 home page show only two cards, with advanced controls hidden until Custom?
   - Does `/preconfigured` avoid duplicate model-selection lightboxes?
   - Does selecting a model on `/preconfigured` cause that selected model to be loaded automatically when the pipeline runs?
   - Does the activity log show clear, numbered user-facing steps rather than vague labels like "teacher/base model"?
   - Does the activity log avoid a manual Refresh button if polling is automatic?
   - Are training failures surfaced with the child training job error and useful log tail?

5. Contract and tests:
   - Are there tests/contracts proving the shared FastModel runtime and A-00 preconfigured parity?
   - If tests are missing, propose focused assertions.
   - Run the narrow relevant tests if feasible. If not feasible, list exact commands to run.

Important constraints:

- Do not broaden into archived notebooks, broad UI redesigns, or Kaggle publishing.
- Do not revive A-01 through A-24 or `03-duecare-video-pitch`; they are archived for the current push.
- Do not change model source semantics unless you find a concrete bug.
- If you patch code, keep changes targeted and list every changed file.

Deliverable:

Start with findings ordered by severity, with file/line references. Then give a short verdict:

- `PASS`: A-00 preconfigured pipeline is runtime/harness/grading equivalent to Kernel 01 comparison expectations.
- `PARTIAL`: mostly aligned, but specific gaps remain.
- `FAIL`: meaningful divergence that could invalidate the A-00 proof run.

Include a concise remediation plan or patch summary if you make changes.
