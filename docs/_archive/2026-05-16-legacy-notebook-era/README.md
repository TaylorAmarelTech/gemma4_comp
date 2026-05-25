# Legacy notebook-era docs (archived 2026-05-16)

This folder holds documentation that was authored when the DueCare
Kaggle submission was a 3-core + 23-appendix (26-notebook) bundle and
was reviewed via GPT-5x briefs. The submission was consolidated to the
current three-kernel set in 2026-05-11:

- `kaggle/01-duecare-exploration-workbench`
- `kaggle/02-live-demo`
- `kaggle/_archive/notebooks/A-00-omni-experiment-workbench`

The appendix kernels A-01 through A-24 and `03-duecare-video-pitch`
were moved to `kaggle/_archive/notebooks/` at the same time. These
documents are kept here for provenance and historical reference but
should not be used to make decisions about the active submission.

## What is in this folder

| File | Era | Replaced by |
|---|---|---|
| `gpt55x_notebook_iteration_brief.md` | 27-notebook scope brief for GPT-5.5x iteration | The four `docs/claude_*_review_prompt.md` files |
| `workbench_review_brief_for_gpt_5x.md` | GPT-5x design review of 27 notebooks | `docs/claude_north_star_harness_review_prompt.md` |
| `external_review_brief.md` | External GPT-5.5 review brief for the wider chat-package + harness | `docs/claude_a00_tool_dispatch_and_trace_review_prompt.md` and `docs/claude_harness_ecosystem_a00_review_prompt.md` |
| `kaggle_notebooks_rubric_audit.md` | 13-notebook Ã— 13-principle audit | `docs/harness_ecosystem.md` for inventory and `docs/harness_standard_contract.md` for the contract surface |
| `repo_cleanup_review_2026-05-10.md` | Point-in-time cleanup review | Superseded by the current trinity-doc approach to harness documentation |
| `notebook_index.md` | Former 11/26-notebook submission index | `kaggle/_INDEX.md` and `docs/current_kaggle_notebook_state.md` |
| `smoke_test_report_2026-05-02.md` | Point-in-time smoke report for the former notebook-era scope | `docs/copilot_handoff_2026_05_16.md` for the current in-scope test baseline |
| `SUBMISSION_READINESS_AUDIT.md` | Point-in-time 2026-05-10 readiness audit | `docs/copilot_handoff_2026_05_16.md` and `docs/PACKAGE_INVENTORY.md` |
| `appendix_artifact_schema.md` | Former A-series bundle/appendix artifact schema | `docs/FOR_PEER_REVIEW.md` for current A-00 evidence artifacts and `docs/harness_standard_contract.md` for the harness contract |
| `appendix_experiment_ladder.md` | Former appendix experiment ladder | `docs/current_kaggle_notebook_state.md` and `kaggle/_INDEX.md` |
| `bench_and_tune_readiness.md` | Former A7 adapter-training checklist | `docs/FOR_PEER_REVIEW.md#a-00-proof-path` and `docs/two_week_submission_plan.md` |
| `bench_and_tune_walkthrough.md` | Former A2/A7 bench-and-tune walkthrough | `docs/gemma4_feature_showcase.md` and `docs/model_loading_trace.md` |
| `data_compatibility_plan.md` | Former cross-notebook data-shape refactor plan | `docs/harness_standard_contract.md` and `docs/knowledge_module_schema.md` |
| `data_primitives.md` | Former website-side bundle primitive catalog | `docs/harness_standard_contract.md` and `docs/knowledge_module_schema.md` |
| `data_surface_inventory.md` | Former function/object inventory for the retired notebook ladder | `docs/harness_ecosystem.md` and `docs/PACKAGE_INVENTORY.md` |
| `notebook_qa_companion.md` | Former 11-notebook QA checklist | `docs/current_kaggle_notebook_state.md` and `docs/USER_TODO.md` |
| `project_status.md` | Former 77-notebook / 2026-05-02 status snapshot | `docs/project_status.md` |
| `release_checklist_v0_14_5.md` | Former v0.14.5 release checklist | `docs/USER_TODO.md` |
| `REPORT_CARD.md` | Former self-grade/status scorecard | `docs/readiness_dashboard.md` |
| `rubric_evaluation_v07.md` | Former rubric projection for the retired notebook scope | `docs/readiness_dashboard.md` |
| `submission_gate_checklist.md` | Former 13-phase checklist for the retired notebook scope | `docs/USER_TODO.md` |
| `submission_surface_audit_2026-05-10.md` | Point-in-time audit of A-01 through A-11 appendices | `docs/current_kaggle_notebook_state.md` |
| `004-six-plus-five-notebook-shape.md` | Superseded ADR for the 6+5 notebook-era shape | `docs/current_kaggle_notebook_state.md` |
| `006-two-plus-eleven-notebook-shape.md` | Superseded ADR for the later appendix notebook-era shape | `docs/current_kaggle_notebook_state.md` |

## Where to look now

For current state, see:

- `docs/harness_ecosystem.md` â€” the authoritative harness inventory
- `docs/harness_pattern.md` â€” the registered-module contract and 10-step recipe
- `docs/harness_standard_contract.md` â€” the `HarnessSpec` field shape
- `docs/model_loading_trace.md` â€” Gemma 4 runtime loading path
- The four `docs/claude_*_review_prompt.md` files for fresh review prompts
