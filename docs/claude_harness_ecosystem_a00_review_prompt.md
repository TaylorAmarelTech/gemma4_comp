# Claude Code Review Prompt: Harness Ecosystem and A-00 Omni Workbench

You are Claude Code working in:

`C:\Users\amare\OneDrive\Documents\gemma4_comp`

Read these first:

1. `CLAUDE.md`
2. `docs/harness_ecosystem.md`
3. `docs/harness_pattern.md`
4. `docs/model_loading_trace.md`
5. `docs/claude_omni_fastmodel_review_prompt.md` if present

## Review Goal

Perform a focused code review of the current DueCare harness ecosystem and the A-00 omni experiment workbench after the recent edits. I need to know whether the implementation, documentation, website copy, tests, and Kaggle notebooks are coherent enough for the competition submission and for a long A-00 proof run.

Use this broad definition:

> A DueCare harness is any named, repeatable set of steps around Gemma 4 or a trust boundary that transforms inputs, adds context, calls tools, evaluates outputs, protects privacy, generates training data, or emits auditable artifacts for a specific goal.

## Active Scope

Review active notebooks and runtime paths only:

- `kaggle/01-duecare-exploration-workbench/kernel.py`
- `kaggle/02-live-demo/kernel.py`
- `kaggle/A-00-omni-experiment-workbench/kernel.py`
- `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py`
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/`
- `packages/duecare-llm-chat/src/duecare/chat/experiment_contracts.py`
- `packages/duecare-llm-chat/src/duecare/chat/app.py`
- `packages/duecare-llm-server/src/duecare/server/`
- `apps/duecare-ai.com/app/templates/`
- `docs/harness_ecosystem.md`
- `docs/harness_pattern.md`
- relevant tests under `tests/` and `packages/duecare-llm-chat/tests/`

Do not revive or broaden into archived notebook-era surfaces. Retired appendix
and video-pitch notebooks should remain out of scope except as historical
references.

## Specific Questions To Answer

1. **Harness inventory**
   - Does `docs/harness_ecosystem.md` accurately enumerate the implemented harnesses and planned harnesses?
   - Does it clearly distinguish registered `duecare.chat.harnesses` modules from broader A-00/report/training/evaluation harnesses?
   - Does it avoid overstating partially implemented items such as civil-society email intake and post-search verification?

2. **Core harness parity**
   - Does A-00 `chat_no_online` use the same authoritative GREP, RAG, tools, and grading primitives as Kernel 01â€™s harness comparison page?
   - Confirm A-00 is not using stale hardcoded duplicate GREP/RAG/tool logic except as a defensive fallback.
   - Confirm default A-00 preconfigured pipeline uses:
     - baseline harness: `none`
     - treatment harness: `chat_no_online`
     - layers: Persona + GREP + RAG/context + deterministic tools
     - internet/search off
     - import off
     - combined rule + LLM grading at the end

3. **Model runtime parity**
   - Do Kernel 01, Kernel 02, and A-00 inference paths load Gemma 4 through `Gemma4Runtime.load()`?
   - Are there any direct `FastModel.from_pretrained` inference paths that bypass the shared runtime, other than the A-00 training script where direct training setup is expected?
   - Does `Gemma4Runtime` still match the known-working Unsloth/FastModel recipe:
     - `dtype=None`
     - `load_in_4bit=True`
     - `full_finetuning=False`
     - `device_map="balanced"` or an equivalent safe T4x2 strategy where needed
     - `gemma-4-thinking`
     - `temperature=1.0`
     - `top_p=0.95`
     - `top_k=64`

4. **A-00 preconfigured pipeline**
   Trace:
   - `/preconfigured`
   - `runPreconfiguredPipeline()`
   - `/api/a00/pipeline/run`
   - `_create_pipeline_job()`
   - `_run_pipeline_job()`
   - model load/unload, prompt runs, synthetic data, training, adapter load, judging, report generation, activity export

   Verify the user-facing steps are clear and map to real code:
   - checking loaded model
   - unloading model when needed
   - disk checks / cleanup if present
   - downloading/loading model
   - preflight model test
   - clearing model context
   - base Gemma without harness
   - base Gemma with harness
   - synthetic data generation
   - fine-tuning
   - checkpoint saving/resume
   - adapter saving
   - fine-tuned without harness
   - fine-tuned with harness
   - evaluator model loading
   - combined rule + LLM judging
   - report generation
   - artifact/activity export

5. **Checkpoint and long-run readiness**
   - Confirm A-00 can save training checkpoints under `/kaggle/working`.
   - Confirm checkpoint paths, adapter paths, run outputs, reports, and activity logs survive normal Kaggle output persistence.
   - Confirm resume-from-checkpoint behavior is wired clearly enough for multiple Kaggle runs.
   - Identify any risk that a run hitting Kaggleâ€™s 12-hour limit loses critical artifacts.

6. **External judge options**
   - Confirm A-00 supports local Gemma judging, Ollama/OpenAI-compatible judging, and Anthropic/Claude judging without breaking the no-API-key default path.
   - Confirm official model IDs and API shapes are not obviously wrong.
   - Confirm external judging is optional and clearly described as a speed/quality path, not a competition requirement.

7. **Online grounding harness**
   - Confirm the docs and UI describe online grounding as privacy-gated and not enabled by default in A-00.
   - Confirm the intended architecture is represented correctly:
     `Prompt -> Gemma-anonymized query -> search -> page markdown -> Gemma verification -> KnowledgeObjects -> final prompt context`
   - Identify whether post-search verification is implemented or only planned/hardened in docs.
   - Flag any place where search results could be injected directly without enough source-quality, relevance, contradiction, or deanonymization checks.

8. **Activity logs and artifacts**
   - Confirm A-00 saves enough information for writeup-quality proof:
     - exact prompts
     - final prompts sent to model where safe
     - model responses
     - harness traces
     - synthetic rows
     - training config
     - training log
     - checkpoints/adapters
     - judge prompts/results
     - comparison report
     - full activity log
   - Identify anything still only visible in the browser but not saved under `/kaggle/working`.
   - Identify whether report links/downloads are obvious enough in the UI.

9. **Website/product language**
   - Confirm public copy now says â€œharness ecosystemâ€ where appropriate.
   - Confirm we still use â€œcore content harnessâ€ or â€œchat harnessâ€ when specifically referring to persona/GREP/RAG/tools around a prompt.
   - Search for stale misleading language like â€œone harness,â€ â€œsingle content-safety harness,â€ or broad claims that imply all harnesses are fully implemented.

10. **Tests/contracts**
    - Confirm the existing tests pin the important contracts.
    - Identify missing tests that should be added before submission.
    - Pay attention to:
      - `tests/test_harness_ecosystem_docs.py`
      - `tests/test_harness_imports.py`
      - `tests/test_multi_harness_integration.py`
      - `tests/test_a00_notebook_contract.py`
      - `tests/test_a00_runtime_and_parity_contract.py`
      - `packages/duecare-llm-chat/tests/test_kaggle_kernel01_portability.py`

## Constraints

- Do not run long GPU training.
- Do not run internet-dependent tests unless explicitly necessary.
- Do not redesign UI broadly.
- Do not change archived notebooks.
- Do not remove flexibility or advanced options unless they clearly conflict with the default competition path.
- If you make code edits, keep them narrowly scoped and list every changed file.
- Preserve the current competition-ready path: copy/paste the two primary demo kernels, run on T4x2, get a Cloudflare URL, and treat active A-00 as the optional quantitative proof/training path under `/kaggle/working`.

## Suggested Fast Checks

Run only focused checks unless you find a reason to expand:

```powershell
python -m py_compile kaggle\_archive\notebooks\A-00-omni-experiment-workbench\kernel.py
python -m pytest tests\test_harness_ecosystem_docs.py tests\test_harness_imports.py tests\test_multi_harness_integration.py tests\test_a00_notebook_contract.py tests\test_a00_runtime_and_parity_contract.py packages\duecare-llm-chat\tests\test_kaggle_kernel01_portability.py -q
```

If you change website copy, also search:

```powershell
rg -n "one harness|single content-safety harness|Run the Gemma 4 safety harness|DueCare is a Gemma 4 safety harness|A safety harness around Gemma 4" README.md docs apps packages
```

## Expected Output Format

Start with findings, ordered by severity. Use file and line references.

For each finding include:

- severity: blocker / high / medium / low
- file:line
- what is wrong
- why it matters for the competition or long A-00 run
- recommended fix

Then include:

1. **Verdict:** PASS / PARTIAL / FAIL
2. **Harness parity summary**
3. **A-00 long-run readiness summary**
4. **Artifact/report readiness summary**
5. **Tests run**
6. **Changed files**, if you made edits

Do not bury critical findings in a narrative summary.
