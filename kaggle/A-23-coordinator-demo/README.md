# A-23 — Coordinator demo (Gemma 4 native function calling)

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher · 05 Developer / integration partner

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Closes the last "not yet showcased" gap from `docs/gemma4_feature_showcase.md`: the Coordinator-as-function-calling-router pattern. Gemma 4 emits a multi-tool plan in ONE thinking step. |
| **What it does** | Three cached scenarios that each show Gemma 4 emitting 3-4 structured function calls, fanning out to DueCare lookup tools, and synthesizing a single grounded response. Speedup metric: ~3x vs the equivalent chat-loop pattern. |
| **Demo path** | Open the kernel, hit Save & Run All, scroll through the 3 orchestration timelines. Zero inference; renders in seconds. |
| **Audience** | Researchers verifying load-bearing native function calling; integration partners seeing how to wire the DueCare tool catalog. |
| **Inputs** | Bundled tool catalog (4 tools) + cached scenarios; no GPU; no Kaggle datasets; no secrets. |
| **Gemma 4 features** | **Native function calling** as the headline; orchestration via JSON tool-call lists emitted in a single Gemma turn. Per CLAUDE.md rule 4 ("load-bearing, not decorative"). |
| **Outputs** | v1.0 BundleEnvelope via `duecare.appendix_primitives.write_v1_bundle()` — 4 files (results.json + run.jsonl + metadata.json + bundle.zip with manifest+sha256). Each PerRow carries the full tool_plan + tool_results + synthesized_response. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, gemma4_feature_showcase.md, and public website. |

## What it does

Exercises Gemma 4's **native function-calling** capability as a
multi-tool orchestration router. Each scenario shows the canonical
Coordinator pattern:

1. User asks a compound question.
2. Gemma 4 plans the tool fan-out — 3-4 structured `{"name": ..., "args": {...}}`
   calls emitted in **one** thinking step.
3. The runtime fans out, tools return their structured results.
4. Gemma 4 re-enters with the tool outputs in context and emits **one**
   synthesized response with citations.

Distinct from a chat-loop pattern where each turn calls only one tool
(N turns + N first-token latencies). Headline: ~3x speedup vs the
chat-loop equivalent on the bundled scenarios.

Closes the "Coordinator-as-function-calling-router" gap noted in
[`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md)
section "Where each capability is not showcased yet".

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Load the bundled tool catalog (4 tools: `lookup_corridor_rules`,
   `lookup_fee_cap`, `lookup_statute_text`, `find_hotline`).
3. Load the 3 cached coordinator scenarios.
4. Emit the canonical v1.0 bundle via
   `duecare.appendix_primitives.write_v1_bundle()` (fourth reference
   implementation after A-19, A-21, A-22).
5. Launch the workbench shell with three orchestration timelines —
   each showing User → Gemma plan → tool fan-out → Gemma synthesis.

## Inputs

- **GPU:** NOT required (cached mode).
- **Internet:** ON (GitHub install only).
- **Kaggle Datasets:** none.
- **Secrets:** none.
- **Bundled tool catalog:** 4 lookup tools shipped as a `TOOLS` dict
  inside `kernel.py`.

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`:

- `<RUN>_results.json` — v1.0 BundleEnvelope; each PerRow carries
  `scenario_id` (row_id), `prompt_text`, `response` (synthesized),
  `citations[]`, plus extras `tool_plan[]`, `tool_results[]`,
  `elapsed_s_chat_loop_equivalent`.
- `<RUN>_run.jsonl` — one coordinator scenario per line.
- `<RUN>_metadata.json` — envelope minus `results[]`, plus scenario
  IDs, target_model.
- `<RUN>_bundle.zip` — all three above + `manifest.json` with sha256.
- `RUN_ID` format: `a23_coordinator_{ts}`
  (e.g., `a23_coordinator_2026-05-12T19-30-00Z`).

The `summary` envelope reports `total_tool_calls`,
`avg_tool_calls_per_scenario`, and `speedup_vs_chat_loop`.

## Where this slot lives

- **Canonical role:** A-23 Coordinator-as-function-calling-router demo
- **Folder path:** `kaggle/A-23-coordinator-demo/`
- **Kernel ID:** `a-23-coordinator-demo`
- **Reference for:** fourth use of `write_v1_bundle()` (after A-19,
  A-21, A-22); first use of PerRow's `extra='allow'` to carry rich
  per-row fields (tool_plan / tool_results).
- **Sister kernels:** A-19 multilingual, A-20 privacy-boundary,
  A-21 long-context, A-22 streaming (all zero-inference cached
  patterns suitable for video).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Gemma 4 feature showcase:** [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md).
- **User walkthrough:** [`docs/user_walkthrough.md`](../../docs/user_walkthrough.md).
- **Why Gemma 4 (feature showcases):** [duecare-ai.com/why-gemma](https://duecare-ai.com/why-gemma) -- this kernel demonstrates the native function-calling capability listed there.
- **BundleEnvelope schema:** [duecare-ai.com/technical-docs](https://duecare-ai.com/technical-docs) -- canonical emit shape used by this kernel.
- **Public website:** [duecare-ai.com](https://duecare-ai.com).
