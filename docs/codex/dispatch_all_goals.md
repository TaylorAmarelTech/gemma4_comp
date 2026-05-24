# Dispatch-all-goals prompts

> Created 2026-05-24. Two prompts to dispatch the 9 pending Codex goals — pick the one that fits your Codex input budget.

## Short prompt (paste this)

```
Work through every PENDING goal in docs/codex/ following the order in
docs/codex/00_execution_order.md.

Loop per goal: read its handoff.md → follow sections 5, 6, 7 to make
the change → honor section 9's do-not-break checklist (links to
docs/codex/00_do_not_break.md) → run section 10's verification → check
section 8's acceptance criteria → commit + push → flip the goal's
"Status: PENDING" to "Status: DONE <date> in <SHA>" and update
docs/codex/README.md's status table.

Goal 10 is already DONE (92f45ac), skip. CLAUDE.md is protected, don't
touch. One commit per goal. Stop after Goal 4 and report progress.
```

## Long prompt (reference / fallback)

Use this when Codex needs more explicit scaffolding (e.g. a less-capable agent, or when the short prompt produces drift):

```
You are working on the gemma4_comp repo (TaylorAmarelTech/gemma4_comp).
Branch: master. Don't switch branches.

START by reading these three files in order:
  1. docs/codex/README.md  (directory map + 12-section template)
  2. docs/codex/00_do_not_break.md  (the protective contract — every
     change must honor it)
  3. docs/codex/00_execution_order.md  (recommended order + dependencies)

Then work through every PENDING goal in docs/codex/ in the order
specified by 00_execution_order.md:

  Goal 1  → docs/codex/goal_01_polish_button_search/handoff.md
  Goal 6  → docs/codex/goal_06_template_sample_bundle/handoff.md
  Goal 3  → docs/codex/goal_03_field_source_preview/handoff.md
  Goal 4  → docs/codex/goal_04_process_to_knowledge/handoff.md
  Goal 8  → docs/codex/goal_08_inline_diff/handoff.md
  Goal 5  → docs/codex/goal_05_auto_polish_queue/handoff.md
  Goal 2  → docs/codex/goal_02_multi_template_fill/handoff.md
  Goal 9  → docs/codex/goal_09_inline_vocab_normalize/handoff.md
  Goal 7  → docs/codex/goal_07_vocab_audit_script/handoff.md

Goal 10 is already DONE (commit 92f45ac) — skip it.

For each goal, follow this loop:

  1. Open the goal's handoff.md.
  2. Read every file listed in section 5 ("Files to read first") BEFORE
     making any edit. The handoff names exact paths and line ranges.
  3. Make the changes per section 6 ("Files to modify") and section 7
     ("Files to create"). Honor every item in section 9 ("Do-not-break
     checklist") — those reference specific sections of
     docs/codex/00_do_not_break.md.
  4. Run every command in section 10 ("Verification commands"). If any
     fail, fix the change. Don't proceed if verification is red.
  5. Check section 8 ("Acceptance criteria") one by one — every item
     must hold. If any don't, fix before proceeding.
  6. Confirm section 12 ("Out of scope") wasn't violated — if you
     touched something out of scope, revert it.
  7. Stage only the files this goal touches. Don't pick up unrelated
     working-tree changes.
  8. Commit with a structured message:
       <type>(<scope>): <subject>

       <body explaining what changed and why, referencing the goal>

       Co-Authored-By: Codex <noreply@openai.com>
     Use the appropriate <type>: feat for new endpoints/features,
     test for test-only additions, docs for doc updates.
  9. Push to origin/master.
 10. Update the goal's handoff.md: change "Status: PENDING" to
     "Status: DONE 2026-MM-DD in commit <SHA>". Update
     docs/codex/README.md goal-directory map with the same status.
     Commit + push that doc update separately (one commit per goal +
     one bookkeeping commit).
 11. Move to the next goal.

HARD RULES:

  - NEVER edit files listed as protected in
    docs/codex/00_do_not_break.md without re-scoping the change.
  - CLAUDE.md is protected setup metadata. Don't touch it.
  - NEVER rename existing API routes, DOM IDs, activity-log handles,
    or canonical vocab tuple entries. Add new things next to them.
  - NEVER use innerHTML for user-derived strings — use createElement +
    textContent.
  - NEVER bundle multiple goals into one commit unless the "Safe
    bundles" section of 00_execution_order.md explicitly says so.
  - If a verification command requires pytest and pytest fails to
    import on this machine, fall back to AST parsing + the standalone
    Python sanity checks the handoff provides (Goal 9's handoff has
    an example). Note in the commit body that pytest wasn't available
    locally and the tests will run in CI/Kaggle.
  - If you hit an OOM or a Gemma error during a runtime verification
    step that the handoff doesn't require, document it and continue —
    don't fix unrelated infrastructure as part of this dispatch.

STOP CONDITIONS:

  - Stop and report back if any goal's verification fails after a
    reasonable fix attempt.
  - Stop and report back if you discover a do-not-break item the
    handoff missed.
  - Stop and report back after Goal 4 completes (it's the largest;
    good checkpoint before continuing with the smaller follow-ups).

When all 9 goals are done, post a final summary listing every commit
SHA, the goals it covered, and any deferred follow-ups you surfaced
along the way.
```

## When to use which

- **Short prompt** for capable agents (Codex with file-read tools, modern Claude/GPT). The handoff packages themselves carry the discipline; the prompt only needs to point at them.
- **Long prompt** when you've seen drift in the short version, or when dispatching to a less-capable agent that needs explicit scaffolding.
