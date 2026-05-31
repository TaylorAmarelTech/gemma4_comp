# 00 - Execution order

> Created 2026-05-24. Updated 2026-05-25 after the active Kaggle surface review. Recommended order for the original polish goals plus the next-phase Kaggle surface goals.

## TL;DR

**Already done from the original reviewer-visible pack:** Goals 1, 2, 3, 4, 5, 6, 8, and 10.

**Remaining original goals:** Goal 9 (inline vocab normalize) and Goal 7 (vocab audit script).

**Next pickup for the current Kaggle review:** Goal 12 (Kernel 01 page polish and page-source gate), then Goal 13 (Kernel 02 recording polish).

**No-stop order for remaining original goals:** Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.

**Next-phase Kaggle surface order:** Goal 12 -> Goal 13 -> Goal 11 -> Goal 14 -> Goal 15. For a few-hour no-stop run, use `docs/codex/goal_commands/06_kaggle_surface_long_run.md`.

The important correction is Goal 5 before Goal 8. Goal 8's own handoff says it depends on Goal 1 and Goal 5 being landed, so do not run Goal 8 before Goal 5 in an all-goals dispatch.

## Recommended order

| Order | Goal | Why this position | Approx. session size |
|---|---|---|---|
| 1 | ~~Goal 10 (E2E tests for polish)~~ | **DONE.** Locked in the contract every subsequent goal depends on. | - |
| 2 | ~~Goal 1 (Polish on search.html)~~ | **DONE.** Same UX pattern as knowledge.html; immediate visible win. | Small |
| 3 | ~~Goal 6 (Sample bundle for templates.html)~~ | **DONE.** Unblocks first-time reviewer round-trip; pure UX, no Gemma cost. | Small |
| 4 | ~~Goal 3 (Field-source preview)~~ | **DONE.** Improves templates UX with no Gemma cost; pre-Generate visibility. | Small |
| 5 | ~~Goal 4 (Process -> knowledge one-click)~~ | **DONE.** Bridges two big surfaces; high reviewer impact. | Medium |
| 6 | ~~Goal 5 (Auto-polish queue)~~ | **DONE.** Power-user feature; depends on Goal 1 and reuses the same polish-call pattern. | Medium |
| 7 | ~~Goal 8 (Inline word diff)~~ | **DONE.** Polish UX refinement; depends on Goals 1 + 5 being in. | Small |
| 8 | ~~Goal 2 (Multi-template fill)~~ | **DONE.** Larger templates refactor; benefits from Goals 3 + 6 first. | Medium |
| 9 | Goal 9 (Inline vocab normalize) | Surface polish; can land anytime after the larger reviewer flows. | Small |
| 10 | Goal 7 (Vocab audit script) | Diagnostic tool; best after vocab-affecting code is stable. | Small |

## Dependency graph

```text
Goal 10 (E2E tests) - DONE
  |
  +--> Goal 1 (search.html polish button)
  |      |
  |      +--> Goal 5 (auto-polish queue)
  |              |
  |              +--> Goal 8 (inline word diff)
  |
  +--> Goal 4 (process -> knowledge)
  |
  +--> Goal 6 (sample bundle)
  |      |
  |      +--> Goal 3 (field-source preview)
  |              |
  |              +--> Goal 2 (multi-template fill)
  |
  +--> Goal 9 (inline vocab normalize)  [standalone]
          |
          +--> Goal 7 (vocab audit script) [diagnostic follow-up]
```

Goal 9 does not strictly depend on the feature goals, but it should run before Goal 7 if you want the audit script to inspect the most current normalizer behavior.

## Multi-goal session packs

These packs are meant for one long Codex session that continues automatically, not for one combined commit. Keep one implementation commit per goal plus any required status/bookkeeping update.

Every pack must run `python scripts/validate_main_kaggle_kernels.py` before each goal commit. That gate covers the Kaggle root layout, the active `01`, `02`, and `A-00` submission kernels, plus the two optional benchmark kernels; archived appendix notebooks are out of kernel compatibility unless Taylor says otherwise.

- **Full no-stop dispatch**: Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.
- **Post-pack Kaggle surface follow-up**: Goal 12 -> Goal 13 -> Goal 11 -> Goal 14 -> Goal 15. This sequence first stabilizes the active `01`/`02` reviewer and recording pages, then takes the larger Bulk File Review hierarchy architecture, then improves the optional benchmark proof surfaces.
- **Post-pack architecture follow-up**: Goal 11. This remains intentionally outside the original no-stop pack because it is Large: it changes Bulk File Review graph extraction, model-call scheduling, process logs, and process tests.
- **Reviewer-visible first wave**: Goal 1 -> Goal 6 -> Goal 3 -> Goal 4. Best when preparing a recording or judge walkthrough.
- **Templates deep pack**: Goal 6 -> Goal 3 -> Goal 2. Run in that sequence because Goal 2's selector benefits from the sample and dry-run preview being stable.
- **Polish pipeline pack**: Goal 1 -> Goal 5 -> Goal 8. Do not skip Goal 5 before Goal 8.
- **Vocab and diagnostics pack**: Goal 9 -> Goal 7. Keeps the read-only audit after the inline normalizer.
- **Iterative research frontier pack**: `docs/codex/goal_commands/11_iterative_branching_research_frontier.md`. Run after or alongside the major-case/global research packs when the priority is hours of source-frontier branching, dorks, public knowledge objects, dimensions, prompts, multi-turn conversations, tests, validation, commits, and resumable handoff state.

## Unsafe combinations

- Goal 8 before Goal 5: Goal 8's handoff says it depends on Goal 5.
- Goal 2 before Goals 6 and 3: it can be done, but it makes the templates refactor harder and weakens reviewer verification.
- Goal 7 in the same commit as vocabulary changes: the audit needs stable vocab/alias behavior to produce meaningful output.
- Any multi-goal commit: even in a no-stop run, keep commits small and goal-scoped.

## What to skip under time pressure

If you only have time for two or three goals, prioritize:

1. **Goal 1** (search.html polish button) - visible reviewer win.
2. **Goal 6** (templates sample bundle) - required by `.claude/rules/70_workbench_ui_primitives.md` rule 7.
3. **Goal 4** (process -> knowledge one-click) - connects two surfaces reviewers already use.

Goals 5, 8, 9, and 7 are polish-on-top-of-polish. Skip them under time pressure.

## What "session size" means

- **Small**: about 1-2 hours; one file touched, one Codex prompt.
- **Medium**: about 3-4 hours; 2-4 files, may need a follow-up prompt for tests.
- **Large**: about 6+ hours; multiple modules, schema changes, broad test coverage. Goal 11 is Large; Goals 12-15 range from Small to Medium unless the implementation expands beyond the handoff.

## Post-completion bookkeeping

When Codex completes a goal:

1. Update the goal's `handoff.md` STATUS marker from PENDING to DONE with the commit SHA.
2. Update [`README.md`](README.md)'s goal-directory map with the same status.
3. Run `python scripts/validate_main_kaggle_kernels.py` and keep the active and optional root Kaggle kernels plus the Kaggle root layout green.
4. If the goal touches Kernel 01/02 pages or optional benchmark kernels, run `py -3.12 scripts/validate_kaggle_page_sources.py`.
5. If the goal added a new route, DOM ID, sample artifact, or public contract, update [`00_do_not_break.md`](00_do_not_break.md) only if the new item is now load-bearing.
6. Taylor has allowed `CLAUDE.md` reconciliation edits. Update it only when a goal completion, kernel gate, or active operating brief needs to stay consistent; keep unrelated CLAUDE.md refactors out of goal commits.
