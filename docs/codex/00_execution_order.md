# 00 - Execution order

> Created 2026-05-24. Updated 2026-05-24 after reviewing the handoff dependencies. Recommended order for working through the 10 Codex goals, plus dependency-safe multi-goal session packs.

## TL;DR

**Already done:** Goal 10 (`92f45ac` - polish endpoint E2E tests).

**Next pickup:** Goal 1 (polish button on search.html). Smallest, highest visible win. Reuses the contract Goal 10 locked in.

**No-stop order for remaining goals:** Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.

The important correction is Goal 5 before Goal 8. Goal 8's own handoff says it depends on Goal 1 and Goal 5 being landed, so do not run Goal 8 before Goal 5 in an all-goals dispatch.

## Recommended order

| Order | Goal | Why this position | Approx. session size |
|---|---|---|---|
| 1 | ~~Goal 10 (E2E tests for polish)~~ | **DONE.** Locked in the contract every subsequent goal depends on. | - |
| 2 | Goal 1 (Polish on search.html) | Same UX pattern as knowledge.html; immediate visible win. | Small |
| 3 | Goal 6 (Sample bundle for templates.html) | Unblocks first-time reviewer round-trip; pure UX, no Gemma cost. | Small |
| 4 | Goal 3 (Field-source preview) | Improves templates UX with no Gemma cost; pre-Generate visibility. | Small |
| 5 | Goal 4 (Process -> knowledge one-click) | Bridges two big surfaces; high reviewer impact. | Medium |
| 6 | Goal 5 (Auto-polish queue) | Power-user feature; depends on Goal 1 and reuses the same polish-call pattern. | Medium |
| 7 | Goal 8 (Inline word diff) | Polish UX refinement; depends on Goals 1 + 5 being in. | Small |
| 8 | Goal 2 (Multi-template fill) | Larger templates refactor; benefits from Goals 3 + 6 first. | Medium |
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

Every pack must run `python scripts/validate_main_kaggle_kernels.py` before each goal commit. That gate covers the three active submission kernels plus the two optional benchmark kernels; appendix and archived notebooks are out of scope unless Taylor says otherwise.

- **Full no-stop dispatch**: Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.
- **Post-pack architecture follow-up**: Goal 11. This is intentionally outside the current no-stop pack because it is Large: it changes Bulk File Review graph extraction, model-call scheduling, process logs, and process tests.
- **Reviewer-visible first wave**: Goal 1 -> Goal 6 -> Goal 3 -> Goal 4. Best when preparing a recording or judge walkthrough.
- **Templates deep pack**: Goal 6 -> Goal 3 -> Goal 2. Run in that sequence because Goal 2's selector benefits from the sample and dry-run preview being stable.
- **Polish pipeline pack**: Goal 1 -> Goal 5 -> Goal 8. Do not skip Goal 5 before Goal 8.
- **Vocab and diagnostics pack**: Goal 9 -> Goal 7. Keeps the read-only audit after the inline normalizer.

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
- **Large**: about 6+ hours; multiple modules, schema changes, broad test coverage. None of these 10 goals are Large.

## Post-completion bookkeeping

When Codex completes a goal:

1. Update the goal's `handoff.md` STATUS marker from PENDING to DONE with the commit SHA.
2. Update [`README.md`](README.md)'s goal-directory map with the same status.
3. Run `python scripts/validate_main_kaggle_kernels.py` and keep the five main non-archived Kaggle kernels green.
4. If the goal added a new route, DOM ID, sample artifact, or public contract, update [`00_do_not_break.md`](00_do_not_break.md) only if the new item is now load-bearing.
5. Taylor has allowed `CLAUDE.md` reconciliation edits. Update it only when a goal completion, kernel gate, or active operating brief needs to stay consistent; keep unrelated CLAUDE.md refactors out of goal commits.
