# 00 — Execution order

> Created 2026-05-24. Recommended order for working through the 10 codex goals, plus the explicit dependency graph so you can pick a different order safely.

## TL;DR

**Already done:** Goal 10 (`92f45ac` — polish endpoint E2E tests).

**Next pickup:** Goal 1 (polish button on search.html). Smallest, highest visible win. Reuses the contract Goal 10 locked in.

## Recommended order

| Order | Goal | Why this position | Approx. session size |
|---|---|---|---|
| 1 | ~~Goal 10 (E2E tests for polish)~~ | **DONE.** Locked in the contract every subsequent goal depends on. | — |
| 2 | Goal 1 (Polish on search.html) | Same UX pattern as knowledge.html; immediate visible win. | Small |
| 3 | Goal 6 (Sample bundle for templates.html) | Unblocks first-time reviewer round-trip; pure UX, no Gemma cost. | Small |
| 4 | Goal 3 (Field-source preview) | Improves templates UX with no Gemma cost; pre-Generate visibility. | Small |
| 5 | Goal 4 (Process → knowledge one-click) | Bridges two big surfaces; high reviewer-impact. | Medium |
| 6 | Goal 8 (Inline word diff) | Polish UX polish; depends on goals 1 + 5 being in. | Small |
| 7 | Goal 5 (Auto-polish queue) | Power-user feature; depends on Goal 1 (the same polish-call pattern). | Medium |
| 8 | Goal 2 (Multi-template fill) | Larger refactor; benefits from goals 3 + 6 first. | Medium |
| 9 | Goal 9 (Inline vocab normalize) | Surface polish; can land anytime. | Small |
| 10 | Goal 7 (Vocab audit script) | Diagnostic tool; not urgent unless you're auditing saved envelopes. | Small |

## Dependency graph

```
Goal 10 (E2E tests) ──── DONE ─── (everything else inherits the locked contract)
                          │
                          ├──────► Goal 1 (search.html polish button)
                          │            │
                          │            ├──► Goal 5 (auto-polish queue)
                          │            │
                          │            └──► Goal 8 (inline word diff)
                          │                     ▲
                          │                     │
                          ├──────► Goal 4 (process → knowledge) ─┘
                          │
                          ├──────► Goal 6 (sample bundle) ──► Goal 3 (field-source preview)
                          │                                       │
                          │                                       └──► Goal 2 (multi-template fill)
                          │
                          ├──────► Goal 9 (inline vocab normalize)  [standalone]
                          │
                          └──────► Goal 7 (vocab audit script)      [standalone]
```

Goals 7 and 9 are leaf nodes — pick them up whenever convenient.

## Bundling for one Codex session

If you want to dispatch more than one goal in a single Codex session, only bundle goals that share a code surface AND don't introduce circular dependencies. Safe bundles:

- **Templates polish pack**: Goal 6 (sample bundle) + Goal 3 (field-source preview). Both touch `templates.html` and `templates.py`.
- **Polish UX pack**: Goal 1 (search polish button) + Goal 8 (inline diff). Both touch the polish-rendering JS.
- **Knowledge bridge pack**: Goal 4 (process → knowledge) + Goal 5 (auto-polish queue). Both extend the knowledge-fact pipeline.

Unsafe bundles:

- Goal 2 (multi-template fill) + Goal 6 (sample bundle): the sample bundle's structure affects the multi-template selector logic; sequence them, don't bundle them.
- Goal 7 (vocab audit) + anything that changes vocabularies: the audit needs the vocab stable to compute correctly.

## What to skip

If you only have time for two or three goals, prioritize:

1. **Goal 1** (search.html polish button) — visible reviewer win.
2. **Goal 6** (templates sample bundle) — required by `.claude/rules/70_workbench_ui_primitives.md` rule 7.
3. **Goal 4** (process → knowledge one-click) — connects two surfaces reviewers already use.

Goals 5, 8, 9, 7 are polish-on-top-of-polish. Skip them under time pressure.

## What "session size" means

- **Small**: ~1-2 hours; one file touched, one Codex prompt.
- **Medium**: ~3-4 hours; 2-4 files, may need a follow-up prompt for tests.
- **Large**: ~6+ hours; multiple modules, schema changes, broad test coverage. None of these 10 goals are Large.

## Post-completion bookkeeping

When Codex completes a goal:

1. Update the goal's `handoff.md` STATUS marker from PENDING → DONE with the commit SHA.
2. Update [`README.md`](README.md)'s goal-directory map with the same status.
3. If the goal added a new vocabulary item, route, or DOM ID, update [`00_do_not_break.md`](00_do_not_break.md) accordingly.
4. Update `CLAUDE.md`'s operating-brief bullet if the change is reviewer-visible.
