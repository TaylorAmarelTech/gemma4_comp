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

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A23 appendix — Coordinator demo (Gemma 4 native function calling)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Runtime vs weights safety study](../A-10-runtime-vs-weights-safety-study/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- **[#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)**
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
