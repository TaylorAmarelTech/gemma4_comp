---
description: Completeness report for all Duecare modules (meta files + source + tests)
---

Generate a completeness report for every module under `src/forge/`.

1. Walk `src/forge/` recursively. For each folder containing a
   `PURPOSE.md`, record the module as a row in the report.

2. For each module, check the presence of:
   - All 7 meta files (PURPOSE, AGENTS, INPUTS_OUTPUTS, HIERARCHY,
     DIAGRAM, TESTS, STATUS)
   - At least one source `.py` file (not counting `__init__.py`)
   - A `tests/` folder with at least one test file
   - Whether the source files contain more than a docstring + `TODO` stub

3. Tally the modules by `STATUS.md` declared state (`stub`, `partial`,
   `complete`).

4. Produce a markdown table with columns: `module_id`, `meta_complete`
   (Yes/No), `has_source`, `has_tests`, `declared_status`,
   `next_action`.

5. Report aggregate counts:
   - Total modules: N
   - Fully meta-complete: X / N
   - Has implementation beyond stub: Y / N
   - Has real tests: Z / N
   - By declared status: stub=A, partial=B, complete=C

6. Identify the top 3 modules that are blocking P0 progress (refer to
   `docs/project_phases.md` for priorities). Be specific: module id +
   one-line reason.

7. Close with the overarching-goals check: which of these modules
   directly produce output that lands in the hackathon video?

Keep under 800 words. Make the table readable on a standard terminal.
