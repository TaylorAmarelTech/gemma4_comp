---
description: Run Duecare tests scoped to a path (module, layer, or whole tree)
argument-hint: <path> [--recursive]
---

Run the Duecare test suite scoped to `$ARGUMENTS`.

1. Determine the scope from the arguments:
   - If the path points to a single module folder, run
     `pytest $ARGUMENTS/tests/ -v`
   - If the path points to a layer folder and `--recursive` is passed,
     run `pytest $ARGUMENTS -v` (pytest will discover all tests/ subdirs)
   - If the path is `src/forge` and `--recursive` is passed, run the full
     suite: `pytest src/forge -v`

2. Report the results in this structure:
   - Total tests run
   - Passed / failed / skipped / xfailed counts
   - For any failure: the test name, file, and a one-line summary of
     the failure
   - Overall pass/fail verdict

3. If any test fails:
   - Do NOT attempt to fix the failure automatically — report it and
     stop.
   - Cite the rule from `.claude/rules/30_test_before_commit.md`: fix
     broken tests before they accumulate.

4. If all tests pass, suggest the next thing the user might want to
   test in a broader scope (e.g., "you just tested `judge`; the next
   integration layer up is `src/forge/agents` with `--recursive`").

Keep the output under 300 words. Use a table for the test result counts.
