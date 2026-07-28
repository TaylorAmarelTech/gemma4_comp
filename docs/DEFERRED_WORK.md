# Deferred Work Register

This document is generated from
[`configs/duecare/deferred_work.json`](../configs/duecare/deferred_work.json).
It is the canonical boundary between work that can be completed in a
model-free repository change and work that requires private access, human
review, owner authorization, provider spend, or Kaggle quota.

**Current as of:** 2026-07-28

**Maintenance posture:** No current deferred item is actionable after the dated 11-item closeout disposition. Public surfaces remain running, the model and flywheel stack remains cost-stopped, and source freshness reopens on 2026-10-28 or earlier when a volatile fact changes.

## Completion Policy

An item leaves this outstanding register only after a dated resolution records whether it was executed, declined, excluded from claims, retained by the current owner, or closed with explicit residual risk.

Zero outstanding items must not be described as proof that declined, excluded, private, human-review, provider, notebook, training, or publication work was performed.

No past resolution or future register item authorizes removal of stop sentinels, re-enabling scheduled tasks, provider calls, Kaggle quota use, or registry publication.

Private receipts retain account, billing, recovery, and reviewer identity details outside Git; public evidence records only dates, categories, decisions, hashes, and pass or fail state.

If work reopens, its status must record the real authorization boundary;
empty fields, fabricated approvals, guessed versions, and undated claims are
rejected by
`python scripts/validate_deferred_work.py`.

## Summary

**No outstanding items.** The 11 inherited closeout items received
dated dispositions in
[`CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md).
That receipt distinguishes completed maintenance from declined work,
claim exclusions, retained ownership, and retained risk.

## Pickup Order

No pickup sequence is active. To reopen work safely:

1. Preserve the whole-stack cost stop and establish live Git, process,
   scheduler, provider, and publication truth.
2. Confirm a specific reopen condition in the dated receipt is met.
3. Add a bounded item with a named owner role, prerequisites, actions,
   acceptance gates, evidence, and an explicit cost/network boundary.
4. Validate the register and closeout receipt before starting the item;
   preserve the prior receipt as immutable dated history.

**Ready for model-free repository work:** None.

**Recurring maintenance:** None.

**Externally or human gated:** None.

## Updating This Register

1. Edit `configs/duecare/deferred_work.json`.
2. Run `python scripts/build_deferred_work_register.py`.
3. Run `python scripts/validate_deferred_work.py`.
4. Run `python scripts/validate_publication_readiness.py --scope core`
   and the smallest tests for any affected surface.
5. Change an item to a completed historical receipt only in a separate
   dated document after every acceptance gate has evidence; remove it from
   this outstanding-work registry in the same reviewed change.
