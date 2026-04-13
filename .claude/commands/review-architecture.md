---
description: Cross-check consistency across the architecture docs
---

Cross-check consistency across these architecture documents:

1. `docs/architecture.md`
2. `docs/the_forge.md`
3. `docs/project_phases.md`
4. `docs/integration_plan.md`
5. `docs/rubric_alignment.md`
6. `docs/kaggle_integration.md`
7. `docs/claude_code_integration.md`
8. `src/forge/PURPOSE.md` (if present)
9. `src/forge/AGENTS.md` (if present)
10. `CLAUDE.md` at the project root

Look specifically for:

- **Terminology drift.** Does "Coordinator" mean the same thing in every
  doc? Is "domain pack" defined the same way? Is "agent" consistent?
- **Scope drift.** Do all the docs agree on the 4 phases vs the Duecare
  agentic pitch? Where do they conflict and which one is authoritative?
- **Missing cross-links.** Does each doc link to the others where
  relevant, or is there an orphan doc nobody references?
- **Rubric alignment.** Does every doc contribute to at least one of
  the three overarching goals (Impact, Video, Tech)? Flag any doc that
  doesn't.
- **Staleness.** Are any docs dated before 2026-04-10? (Major shifts
  have happened since.) If so, flag them for update.

Produce a markdown report with:
- **Agreement summary** (where the docs align cleanly)
- **Conflicts** (specific term / scope / claim that differs across docs,
  with file:line citations)
- **Missing cross-links** (which doc should reference which)
- **Stale content**
- **Specific fix list** (ordered by impact — the highest-leverage fix
  first)

Keep under 1000 words. Do NOT edit any files — just report.
