# Cleanup archive — 2026-05-10

This archive folder holds files moved out of the active review surface during the 2026-05-10 cleanup pass. Nothing here was deleted; files were moved so the active repo is easier to reason about before the Gemma 4 Good Hackathon submission.

## Moved here

| Archive path | Original path | Why archived |
|---|---|---|
| `deployment_hf_spaces/` | `deployment/hf_spaces/` | Older generic Hugging Face Spaces runbook. Superseded by the two explicit root Space bundles: `hf_space/` for Harness Chat and `hf-space/` for Live Demo. |
| `docs_handoff_prompts/` | `docs/COPILOT_HANDOFF_REVIEW_PROMPT.md`, `docs/GPT55_AUTOPILOT_BRIEF.md`, `docs/GPT55_GO_NOW_FOLLOWUP.md`, `docs/GPT55_HANDOFF_EXECUTION_PROMPT.md` | Old single-session handoff and autopilot prompts. Superseded by `CLAUDE.md`, `.claude/rules/`, and current root continuation prompts. |
| `docs_prompts_legacy/` | `docs/prompts/` | Legacy notebook prompt ladder with stale publish-oriented instructions. Superseded by active Kaggle builders, validators, `CLAUDE.md`, `.claude/rules/`, and current continuation prompts. |
| `docs_stale_planning/` | `docs/CHECKPOINT_2026-04-19.md`, `docs/github_action_list.md`, `docs/notebook_action_list.md` | Older checkpoint/action-list docs that referenced superseded publish flows and old deployment paths. Superseded by current readiness, package, Kaggle, and cleanup docs. |

## Notes

- Archived docs may contain stale commands, old counts, or outdated paths by design.
- Do not use this folder as active submission evidence unless a file is explicitly restored or quoted for historical context.
- The active Hugging Face Space folders `hf_space/` and `hf-space/` remain live and intentionally separate.