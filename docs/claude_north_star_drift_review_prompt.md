# Claude Prompt: North-Star Drift, Harness, And A-00 Review

You are Claude Code working in:
`C:\Users\amare\OneDrive\Documents\gemma4_comp`

Read these first:

1. `CLAUDE.md`
2. `docs/system_components_and_critical_paths.md`
3. `docs/harness_ecosystem.md`
4. `docs/harness_pattern.md`
5. `docs/harness_standard_contract.md`
6. `docs/model_loading_trace.md`
7. `docs/copilot_handoff_2026_05_16.md`

Perform a focused drift-hardening review. The goal is to move the repo
toward the north-star configuration without broad redesign or reviving
archived scope.

Review:

- `kaggle/01-duecare-exploration-workbench/kernel.py`
- `kaggle/02-live-demo/kernel.py`
- `kaggle/_archive/notebooks/A-00-omni-experiment-workbench/kernel.py`
- `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py`
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py`
- `packages/duecare-llm-chat/src/duecare/chat/static/`
- `apps/duecare-ai.com/app/templates/`
- active docs under `docs/`, excluding `docs/_archive/`
- relevant tests under `tests/` and `packages/*/tests/`

Answer and fix where low-risk:

1. Are any active docs or public pages still presenting archived
   notebook-era scope as current?
2. Are any static docs/pages still hardcoding fragile live inventory
   counts where they should say "100+", "50+", "registered harnesses",
   "tool bundle", or "runtime metadata"?
3. Are exact counts preserved only where they are measured evidence,
   generated reports, dynamic runtime metadata, or test fixture data?
4. Do Kernel 01, Kernel 02, and A-00 still share inference model
   loading through `Gemma4Runtime`?
5. Does A-00 consume the same GREP/RAG/tool/grading primitives as the
   Kernel 01 comparison page, without hardcoded duplicate logic that can
   diverge?
6. Are external judge backends routed through the universal model
   interface where practical, with normalized usage/latency recorded?
7. Does the post-search verification harness prevent external search
   results from entering downstream context as trusted facts without
   source-quality, relevance, contradiction, and deanonymization checks?
8. Are activity logs, reports, checkpoints, and exported artifacts
   discoverable and saved under Kaggle working paths for long A-00 runs?
9. Are tests flexible enough to allow catalog growth while still
   requiring the core harnesses, model adapters, routes, and active
   kernels?

Constraints:

- Do not edit archived docs or revive archived kernels unless a current
  active doc points to them incorrectly.
- Do not push to Kaggle.
- Do not run GPU/model-loading tests.
- Do not rewrite GREP rules or RAG corpus contents.
- Preserve exact measured benchmark numbers when they are clearly
  labeled as historical or reproducibility evidence.
- Prefer small, reviewable commits.

Start with findings ordered by severity and file/line references. Then
apply targeted fixes for low-risk drift issues. End with:

- Files changed
- Tests run
- Residual risks
- Verdict: PASS, PARTIAL, or FAIL
