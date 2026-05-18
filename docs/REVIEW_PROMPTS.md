# Review prompts and AI handoff index

DueCare ships several specialized review prompts and AI-handoff snapshots
in `docs/`. Each is paste-ready into a fresh chat session. This file is
the index — read it first when you want to launch a focused audit or hand
off active work to another agent.

## Review prompts

These are scoped audit prompts you paste into a fresh chat (Claude Code,
Claude API, or any frontier model). Each starts with required reading,
defines a specific audit window, and ends with a PASS/PARTIAL/FAIL
verdict format.

| Prompt | Audit window | When to use |
|---|---|---|
| [`docs/claude_omni_fastmodel_review_prompt.md`](claude_omni_fastmodel_review_prompt.md) | Original Gemma 4 runtime + A-00 preconfigured pipeline parity. | Verify `Gemma4Runtime` is wired correctly across the three active kernels and A-00 follows the Unsloth FastModel recipe. |
| [`docs/claude_harness_ecosystem_a00_review_prompt.md`](claude_harness_ecosystem_a00_review_prompt.md) | Harness ecosystem language + broader inventory. | Verify the documentation trinity (`harness_ecosystem.md`, `harness_pattern.md`, `harness_standard_contract.md`) is consistent and naming hygiene is preserved. |
| [`docs/claude_north_star_harness_review_prompt.md`](claude_north_star_harness_review_prompt.md) | Universal harness contract: `HarnessSpec`, `MODEL_TRANSPORTS`, `model_targets`, checkpoint readiness. | Verify every registered harness declares the full standardized contract and the universal model interface is wired. |
| [`docs/claude_a00_tool_dispatch_and_trace_review_prompt.md`](claude_a00_tool_dispatch_and_trace_review_prompt.md) | Per-tool dispatch (`_format_shared_tool_call`) + tools-layer trace consistency + harness.html model-target surface + the six contract tests. | Verify the A-00 tool rendering / trace honesty hardening pass landed cleanly. |
| [`docs/claude_north_star_drift_review_prompt.md`](claude_north_star_drift_review_prompt.md) | Drift hardening: archived-scope leakage, fragile inventory counts, kernel parity, judge factory routing, post-search verification, artifact discoverability. | Wide drift audit that prevents quietly stale references from accumulating. |
| [`docs/claude_bulk_file_review_demo_prompt.md`](claude_bulk_file_review_demo_prompt.md) | Bulk File Review demo verification: streamlined demo path, async progress, deterministic fallbacks, idle log clearing, text overflow. | Verify the live Bulk File Review demo path works end-to-end without a loaded model. |

## AI handoff snapshots

These are self-contained "where are we right now" docs you paste at the
start of a new agent session (Copilot, Codex, or any IDE-side AI) so it
can pick up DueCare work without the prior chat history.

| Handoff | HEAD ref at write | Purpose |
|---|---|---|
| [`docs/copilot_handoff_2026_05_16.md`](copilot_handoff_2026_05_16.md) | `8141134` (updated through `5c145ab`) | Full Copilot handoff: scope, runtime, harness contract, suggested next work, hard constraints, verification commands. |
| [`docs/codex_handoff_2026_05_17.md`](codex_handoff_2026_05_17.md) | `965e1f9` | Codex handoff: action-oriented version of the above, focused on the next concrete pickup items after the 16K context bump. |

## Operational docs

These are not review prompts but are the runtime / contract references
the prompts above point at. Read them when you need ground truth.

| Doc | What it covers |
|---|---|
| [`docs/system_components_and_critical_paths.md`](system_components_and_critical_paths.md) | Stable map of the active submission: three kernels, main components, critical paths, drift rules. |
| [`docs/harness_ecosystem.md`](harness_ecosystem.md) | **Authoritative** registered harness inventory + broader harness families. |
| [`docs/harness_pattern.md`](harness_pattern.md) | Required module contract + 10-step recipe for adding a new registered harness. |
| [`docs/harness_standard_contract.md`](harness_standard_contract.md) | `HarnessSpec` field shape, `HarnessLogicPath`, `HarnessPackContract`, `HarnessModelTarget`. |
| [`docs/model_loading_trace.md`](model_loading_trace.md) | Canonical Gemma 4 / Unsloth FastModel loading path across the three kernels. |
| [`docs/bulk_file_review_north_star.md`](bulk_file_review_north_star.md) | Bulk File Review contract: non-negotiables, demo path, UX rules, acceptance checks. |
| [`docs/bulk_file_review_demo_script.md`](bulk_file_review_demo_script.md) | Step-by-step walkthrough of the live Bulk File Review demo against `case_files_streamlined_demo.zip`. |

## How to pick the right prompt

Need a quick guide? Use this decision flow:

```
- Want a fresh deep audit of the whole system?
  -> docs/claude_north_star_drift_review_prompt.md

- Want to verify the Gemma 4 runtime is wired correctly?
  -> docs/claude_omni_fastmodel_review_prompt.md

- Want to verify the registered-harness contract holds?
  -> docs/claude_north_star_harness_review_prompt.md

- Want to verify documentation naming + ecosystem labeling?
  -> docs/claude_harness_ecosystem_a00_review_prompt.md

- Want to verify the A-00 tool rendering / trace honesty hardening?
  -> docs/claude_a00_tool_dispatch_and_trace_review_prompt.md

- Want to verify the live Bulk File Review demo path?
  -> docs/claude_bulk_file_review_demo_prompt.md

- Want to hand off active work to Copilot in VS Code?
  -> docs/copilot_handoff_2026_05_16.md

- Want to hand off active work to Codex CLI/agent?
  -> docs/codex_handoff_2026_05_17.md
```

## Keeping this index honest

Whenever a new `docs/claude_*_review_prompt.md` lands or a new handoff
snapshot is written, add a row to the matching table above. Stale
prompts can be moved to `docs/_archive/` with a redirect entry in the
relevant archive README.
