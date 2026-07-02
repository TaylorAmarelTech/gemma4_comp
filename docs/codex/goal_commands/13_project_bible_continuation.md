# Goal command 13 - project bible continuation loop

Use this when you want Claude Code, Codex, or a similar coding agent to resume
from the current project bible and keep improving the repo in coherent,
validated slices without restarting the paused autonomous judging engine.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and continue improving the DueCare project from the current project bible. Read, in order: AGENTS.md, CLAUDE.md, .claude/rules/05_project_bible_pickup.md, docs/codex/PROJECT_BIBLE.md, docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, docs/codex/00_execution_order.md, and docs/codex/goal_commands/README.md. Inspect the current worktree and `python scripts\autonomous_engine.py --status` before relying on old session state, and treat `lock.state: "stale"` or `latest_preflight.saved_lock_state.state: "stale"` as handoff/status evidence, not proof of a live judging run. Do not remove reports/autonomous_engine.stop, do not start scripts/autonomous_engine.py in run/once mode, do not call Ollama, and do not promote candidate dimensions unless Taylor explicitly asks in the current session and the normal preflight/review gates pass. Pick the next highest-impact safe improvement from docs/codex/PROJECT_BIBLE.md: harden validators between generated research artifacts and active rubric/model behavior, add aggregate-only diagnostics, keep handoff docs synced with actual runtime evidence, improve offline sister-project/domain benchmark planning, or repair small wiring/doc gaps that are directly supported by tests. Make one coherent slice at a time, add or update deterministic tests, run focused tests plus python scripts\validate_project_bible_pickup.py, python scripts\validate_sister_project_planning.py when the slice touches sister-project/domain planning, python scripts\validate_global_protections_saved_artifacts.py and python -m pytest tests -q -k "global_protections or regulatory_miss_pattern" when the slice touches global-protections or regulatory-miss planning, python scripts\validate_public_surface.py, python -m pytest packages --collect-only -q, python scripts\validate_main_kaggle_kernels.py, and py -3.12 scripts\validate_kaggle_page_sources.py when relevant. Keep private data out of git, stage only scoped files, preserve unrelated dirty worktree changes, and continue to the next safe gap until a genuine blocker appears. Final report must include changed files, validation commands/results, autonomous-engine status, whether Ollama was touched, remaining high-value branches, and any unresolved blocker.
```

## Default loop order

1. Read the project bible and live engine status.
   Treat `lock.state: "stale"` or
   `latest_preflight.saved_lock_state.state: "stale"` as handoff/status
   evidence, not proof of a live judging run.
2. Identify the smallest current-state gap that advances the project bible.
3. Inspect the owning files and tests before editing.
4. Implement a scoped improvement.
5. Run focused tests and the relevant public/Kaggle gates.
6. Report exact evidence, then continue to the next safe gap.

## Hard boundaries

- The project bible is a pickup map, not permission to resume judging.
- Candidate dimensions remain propose-only until the packet builder, validator,
  and human review path allow promotion.
- Handoff diagnostics must stay aggregate-only and avoid row text, case text,
  private paths, local hidden paths, API keys, or contact details.
- Public docs should make dated, reproducible claims tied to commands or
  artifacts.
