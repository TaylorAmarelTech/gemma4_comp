---
description: Review a Duecare module folder — reads its meta files and summarizes
argument-hint: <path-to-module-folder>
---

You are reviewing the Duecare module at `$ARGUMENTS`.

1. Read the following meta files in order and summarize each:
   - `$ARGUMENTS/PURPOSE.md`
   - `$ARGUMENTS/INPUTS_OUTPUTS.md`
   - `$ARGUMENTS/HIERARCHY.md`
   - `$ARGUMENTS/DIAGRAM.md`
   - `$ARGUMENTS/STATUS.md`

2. List the Python source files in `$ARGUMENTS` and describe each one's
   current state (stub, partial implementation, or complete).

3. List the test files in `$ARGUMENTS/tests/` and describe what each
   test covers.

4. Report whether the module's implementation matches its PURPOSE and
   INPUTS_OUTPUTS. Flag any drift.

5. Suggest the next highest-value concrete action for this module,
   grounded in `docs/project_phases.md` (is this module P0, P1, or P2?)
   and in `.claude/rules/00_overarching_goals.md` (does the next action
   advance Impact / Video / Tech)?

Keep the output under 500 words. Use markdown headers for each section.
