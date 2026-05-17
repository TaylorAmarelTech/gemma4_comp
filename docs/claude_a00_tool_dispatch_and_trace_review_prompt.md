# Claude Code Review Prompt: A-00 Tool Dispatch and Tools-Trace Hardening (commit 76e44a1)

Paste the block below into a fresh Claude / Claude Code session opened
on this repo. The reviewer audits the focused hardening pass landed in
commit `76e44a1` ("Harden A00 tool rendering and harness contract
surface") plus its companion test additions and the
`harness.html` model-target surface.

This is a follow-up to:
- `docs/claude_north_star_harness_review_prompt.md` (universal harness
  contract + model targets + checkpoint readiness)
- `docs/claude_harness_ecosystem_a00_review_prompt.md` (harness
  ecosystem language + broader inventory)
- `docs/claude_omni_fastmodel_review_prompt.md` (original Gemma 4
  runtime + A-00 preconfigured pipeline parity)

The prior prompts answer "is the universal contract in place" and "do
the harnesses fit the ecosystem language." This one answers "did the
2026-05-16 validation pass actually improve trace quality, tool
context, and reviewer visibility — and can it regress silently?"

---

## Paste-ready prompt

You are Claude Code working in:
C:\Users\amare\OneDrive\Documents\gemma4_comp

Read these first, in order:
1. CLAUDE.md (project context, canonical Gemma 4 runtime, A-00
   preconfigured pipeline contract)
2. docs/harness_standard_contract.md (standard fields: logic_paths,
   knowledge_packs, logic_packs, model_io, model_targets,
   input/output_verification, privacy_boundaries)
3. docs/harness_ecosystem.md (broader harness inventory and naming)
4. docs/model_loading_trace.md (Gemma4Runtime trace across the three
   active kernels)

Also skim the prior review prompts so you do not duplicate their
coverage:
- docs/claude_omni_fastmodel_review_prompt.md
- docs/claude_harness_ecosystem_a00_review_prompt.md
- docs/claude_north_star_harness_review_prompt.md

Context — what commit 76e44a1 changed:

- `kaggle/A-00-omni-experiment-workbench/kernel.py`
  - `_format_shared_tool_call` was rewritten to dispatch by tool name.
    Each of the five deterministic tools from
    `duecare.chat.harness._heuristic_tool_calls` now has a per-name
    branch that surfaces the fields a Gemma 4 prompt actually
    benefits from (statute, max-fee, matched ILO indicators, NGO
    hotlines, ILO convention title/year/articles). Unknown tools fall
    through to a generic-key extractor instead of a 200-char JSON
    truncation.
  - `_build_harness_prompt` now always emits `trace["tools"]` when
    the tools layer is enabled, with distinct source markers
    (`skipped`, `shared`, `shared_empty`, `shared_error`,
    `heuristic`) and step status (`pass` / `noop` / `degraded`).
    Previously the trace silently omitted the tools entry on a
    no-fire path.
- `packages/duecare-llm-chat/src/duecare/chat/static/harness.html`
  - The Harness Workbench now renders `trust_boundary` (local /
    external / configurable) and `notes` for each model target so
    reviewers can read the provider boundary and intent without
    opening `/api/harnesses` in DevTools.
- `tests/test_a00_runtime_and_parity_contract.py`
  - Six new contract tests pin: per-tool dispatch in
    `_format_shared_tool_call`, tools-layer trace consistency,
    external judge factory dispatch + privacy disclosures, local
    Gemma judge as the credential-free default, process plus
    extraction declaring the local `gemma4_runtime` default target,
    and a py_compile smoke for the kernel.

Active scope — review only these surfaces:

Primary code:
- `kaggle/A-00-omni-experiment-workbench/kernel.py`
  - `_format_shared_tool_call` and its five per-tool branches
  - `_build_harness_prompt`'s tools branch and trace assembly
  - `_pack_rules_as_grep_extras`, `_pack_facts_as_rag_extras`
  - The external-judge factories: `_is_ollama_judge_source`,
    `_is_ollama_cloud_source`, `_is_anthropic_judge_source`,
    `_is_external_judge_source`, `_ollama_model_call_factory`,
    `_anthropic_model_call_factory`,
    `_configure_ollama_judge_for_pipeline`,
    `_configure_anthropic_judge_for_pipeline`,
    `_configure_external_judge_for_pipeline`, `_grading_model_call`
- `packages/duecare-llm-chat/src/duecare/chat/static/harness.html`
  (the `model-target-list` rendering block)
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
  (the five tools `_tool_lookup_*` and `_heuristic_tool_calls` — to
  validate that `_format_shared_tool_call`'s per-tool field
  extraction matches the actual result schemas)

Tests:
- `tests/test_a00_runtime_and_parity_contract.py` (the six new
  tests plus the earlier 10)
- `tests/test_harness_universal_model_contract.py`
- `tests/test_harness_standard_contract.py`
- `tests/test_compose_layers.py`
- `packages/duecare-llm-chat/tests/test_harness_workbench.py`
- `packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py`

Out of scope (do not broaden):
- Archived kernels under `kaggle/_archive/notebooks/*` and
  `kaggle/_archive/notebooks/03-duecare-video-pitch/*`.
- Kaggle publish actions. Local validation only.
- The `duecare.chat.harness` 10k-line module's internal logic. You
  may read tool result schemas but do not rewrite GREP rules or RAG
  corpus.
- Other UI redesigns. Only touch the rendering block under review.

Specific questions to answer:

Group A — `_format_shared_tool_call` correctness

A1. Walk the five per-tool branches end to end. For each tool, name
    the actual result schema returned by
    `duecare.chat.harness._tool_lookup_*` and confirm the renderer's
    field extraction matches. Flag any field that is present in the
    tool output but missing from the renderer's display path. Flag
    any field the renderer reads that does not exist in the tool
    output schema (silent miss).

A2. The renderer caps unknown-tool fallbacks at 400 characters via
    `json.dumps(...)[:400]`. Is that limit reasonable for the actual
    tool output sizes? If the largest known result exceeds 400
    chars, would the truncated JSON leave the model unable to act
    on the result?

A3. The `lookup_ngo_intake` branch surfaces up to three hotline
    rows. Verify that the trimming is intentional and document why
    three is the right cap. Is there a risk that a critical fourth
    contact gets dropped silently?

A4. The `lookup_ilo_convention` branch surfaces the first two
    `key_articles`. Confirm two is enough for citation cross-check.
    For C189 (domestic workers) the relevant article for travel
    document retention is Art. 9 — verify that surfaces in the
    first two entries.

A5. Are there opportunities for the renderer to add value beyond
    the current per-tool branches? For example, a multi-hit
    deduplication pass when multiple corridor-fee-cap calls fire
    for the same corridor, or a length-aware concatenation when
    the rendered context approaches a model context window.

Group B — Tools-layer trace consistency

B1. Confirm `trace["tools"]` is always set when `"tools"` is in
    `layers`. Walk the four code paths: shared with results,
    shared with zero results, shared raises, heuristic fires after
    shared returned zero. For each, name the resulting `source`
    value and the `step.status` value.

B2. The heuristic block at the end overwrites `tools_source` to
    `"heuristic"` even if the shared call raised. The `tools_error`
    is preserved separately in `trace["tools"]["error"]`. Is this
    the right precedence? Should the source instead be
    `"heuristic_after_shared_error"` so a reviewer can tell that
    both paths ran?

B3. `step.status` is currently `pass` / `noop` / `degraded`. Is
    `degraded` still emitted when heuristic recovers after a
    shared error, or does the recovered path silently mark `pass`?

B4. The pre-existing GREP and RAG branches use `pass` / `degraded`
    too, but they do not have a `noop` status — they always emit
    `pass` even when zero hits/facts. Should they be aligned with
    the tools layer's pass/noop/degraded scheme for cross-layer
    consistency? Pros vs cons.

Group C — harness.html model-target surface

C1. Read the rendering block in
    `packages/duecare-llm-chat/src/duecare/chat/static/harness.html`
    and confirm `trust_boundary` and `notes` render only when
    present. Pass the page through TestClient against
    `create_app()` and inspect the rendered HTML — does the absence
    of `notes` produce a clean line break or a dangling separator?

C2. Five harnesses declare `model_targets`. Render each via the
    `model-target-list` block (paste the JSON returned by
    `/api/harnesses` for that harness, then mentally apply the
    template). Are the rendered lines readable? Any visual
    regressions from the addition of `trust_boundary` and `notes`?

C3. The `trust_boundary` value can be `local`, `external`, or
    `configurable`. The `harness.html` does not visually
    distinguish these (e.g., color, pill). Should it? If yes,
    propose minimal CSS that reinforces "external" as the
    privacy-sensitive boundary.

Group D — New contract tests

D1. For each of the six new contract tests in
    `tests/test_a00_runtime_and_parity_contract.py`
    (`test_a00_external_judge_factories_preserve_provider_routing_contract`,
    `test_a00_external_judge_keeps_local_default_runnable_without_credentials`,
    `test_process_and_extraction_harnesses_declare_local_gemma_default_target`,
    `test_a00_external_judge_factories_compile_without_runtime_deps`,
    `test_format_shared_tool_call_dispatches_by_tool_name`,
    `test_a00_tools_layer_always_emits_trace_for_consistency`),
    confirm:
    - The assertion targets a line that genuinely exists in the
      current code (not a near-match that could break with a
      whitespace change).
    - The assertion is specific enough to catch the regression it
      claims to prevent.
    - The assertion is not so specific that a benign refactor
      breaks it.

D2. The
    `test_process_and_extraction_harnesses_declare_local_gemma_default_target`
    test reads each harness `__init__.py` and asserts
    `"gemma4_runtime"` and `"default=True"` are both present. Is
    this strong enough to catch a regression where `default=True`
    is moved off the local Gemma target and onto a frontier
    target? If not, propose a tighter assertion that pins the
    pairing (e.g., parse the `HarnessSpec` and check that the
    default target's transport is `gemma4_runtime`).

D3. The
    `test_a00_external_judge_factories_preserve_provider_routing_contract`
    test pins the privacy-note literal "Final grading sends
    benchmark prompts, model responses, and harness traces to
    [Ollama|Anthropic]". If a future contributor rephrases the
    note for clarity, this test breaks. Is the privacy-note text
    truly load-bearing (must not change without review) or is it
    cosmetic? If load-bearing, document why.

Group E — Cross-cutting

E1. Run the full focused gate and report results (PowerShell):
    ```powershell
    $env:PYTHONPATH='packages/duecare-llm-models/src;packages/duecare-llm-chat/src;packages/duecare-llm-core/src'
    python -m pytest `
      tests/test_a00_runtime_and_parity_contract.py `
      tests/test_a00_notebook_contract.py `
      tests/test_harness_universal_model_contract.py `
      tests/test_harness_standard_contract.py `
      tests/test_harness_imports.py `
      tests/test_compose_layers.py `
      tests/test_per_harness_tools.py `
      tests/test_route_contract.py `
      tests/test_multi_harness_integration.py `
      tests/test_ui_audit_contract.py `
      tests/test_end_to_end_flywheel.py `
      tests/test_harness_ecosystem_docs.py `
      packages/duecare-llm-chat/tests/test_kaggle_kernel01_portability.py `
      packages/duecare-llm-chat/tests/test_smoke.py `
      packages/duecare-llm-chat/tests/test_harness_behavior.py `
      packages/duecare-llm-chat/tests/test_harness_v3_6.py `
      packages/duecare-llm-chat/tests/test_compare.py `
      packages/duecare-llm-chat/tests/test_harness_workbench.py `
      packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py `
      packages/duecare-llm-models/tests/test_models_package_smoke.py `
      -q
    ```
    Expected baseline: ~394 passed. Report any failure with the
    failing assertion text. Skip the pre-existing `tests/unit/*`
    collection errors — they are unrelated missing-module failures.

E2. Run the kernel compile smoke alone:
    ```powershell
    python -m py_compile kaggle\A-00-omni-experiment-workbench\kernel.py
    ```
    Must compile cleanly. Report the exit code.

E3. Walk `git show 76e44a1 --stat` and confirm exactly three files
    changed: A-00 kernel, harness.html, and the contract test
    file. Flag any unrelated change that slipped in.

E4. The validation pass deliberately left one architectural
    improvement out of scope: A-00's external judge factories
    (`_ollama_model_call_factory`, `_anthropic_model_call_factory`)
    still hand-roll HTTP via `requests.post(...)` instead of
    routing through
    `packages/duecare-llm-chat/src/duecare/chat/harnesses/model_interface.py::call_model_backend(...)`.
    Is this still acceptable, or has the integration cost dropped
    enough that the migration is now worth doing? Specifically:
    estimate the lines of code that would change in
    `_grading_model_call` plus the two factories if migrated, and
    name any risk to the running pipeline.

Expected output format

Open with **findings ordered by severity** (CRITICAL / HIGH /
MEDIUM / LOW) with file:line references.

For each finding include:
- severity
- file:line
- what is wrong or weak
- why it matters for either the demo, the long A-00 run, or the
  reviewer's audit trail
- recommended fix or test addition

End with:

1. **Verdict** per group: PASS / PARTIAL / FAIL
   - Group A — `_format_shared_tool_call` correctness
   - Group B — Tools-layer trace consistency
   - Group C — `harness.html` model-target surface
   - Group D — New contract tests
   - Group E — Cross-cutting
2. **Overall verdict** in one line.
3. **Tests run + result line** (e.g., "394 passed in 211s").
4. **Changed files** (if you made any edits during the review).
5. **Remaining risks** (max five bullets).

Constraints:
- Do not run long GPU loads.
- Do not run internet-dependent tests unless explicitly necessary.
- Do not redesign UI broadly. Only the existing
  `model-target-list` block may be tightened in Group C if a
  finding warrants it.
- Do not edit CLAUDE.md (protected setup metadata). If a finding
  requires a CLAUDE.md change, flag it and propose the diff inline
  instead of applying it.
- Do not broaden into the archived `kaggle/_archive/notebooks/*`.
- Keep any new tests narrowly scoped to behavior introduced by
  76e44a1.
