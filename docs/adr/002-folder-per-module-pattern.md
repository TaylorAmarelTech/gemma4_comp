# ADR-002: Folder-per-module pattern with auto-generated meta files

- **Status:** Accepted
- **Date:** 2026-04-15
- **Deciders:** Taylor Amarel

## Context

After ADR-001 split the codebase into 17 packages, each package itself
contains 3-50 logical modules (agents, tasks, generators, evaluators,
adapters). At that scale, Python's flat `module.py` per concept loses
the locality between code, tests, and docs.

A new contributor (human or AI) hitting `src/duecare/agents/judge.py`
needs to understand:
- What the judge does
- What other agents it depends on
- What types it produces
- How to run its tests

That information lived in disparate places (a top-level `docs/`
file, a `tests/agents/` folder, `__init__.py` exports). Drift was
constant.

## Decision

Every module is a **folder**, not a file. Every module folder
contains the same canonical 7 files:

```
src/duecare/agents/judge/
├── __init__.py            (developer-written; exports public API)
├── judge.py               (developer-written; the implementation)
├── PURPOSE.md             (auto-generated; one-line + long-form)
├── AGENTS.md              (auto-generated; AI-reader instructions)
├── INPUTS_OUTPUTS.md      (auto-generated; protocols read/written)
├── HIERARCHY.md           (auto-generated; parents/siblings/children/deps)
├── DIAGRAM.md             (auto-generated; ASCII diagram)
├── TESTS.md               (auto-generated; how to run tests)
├── STATUS.md              (auto-generated; stub/partial/complete + TODO)
└── tests/
    └── test_judge.py      (developer-written)
```

The 7 meta files are auto-generated from a `MODULES` descriptor list
in `scripts/generate_forge.py`. To add or modify a module, edit the
descriptor and re-run the script — never hand-edit the meta files.

## Alternatives considered

- **Flat `module.py` per concept.** Original layout. Rejected for
  drift between code + tests + docs at scale.
- **Sphinx auto-doc only.** Generates docs but doesn't enforce a
  canonical structure; AI readers can't navigate by convention.
- **README.md per folder, no other meta files.** Considered, but
  AGENTS.md is a recognized standard now (Cursor / Claude Code /
  Copilot read it natively); shipping the standard is cheap.

## Consequences

**Positive:**
- Any folder is self-describing: walk in, read 7 files, oriented
- AI agents (Claude Code, Cursor, Copilot, Aider) all read AGENTS.md
  natively — Duecare gets a grounded view per subtree without bespoke
  tooling
- Tests live with the module; zero navigation cost when fixing a bug
- Cross-references (siblings, dependents) stay in sync — one script
  re-run propagates a change everywhere
- New contributor onboarding doc is "read PURPOSE + AGENTS + try
  the test" instead of "skim 5 files across 3 directories"

**Negative:**
- Boilerplate-looking; folders feel heavy at first glance
- Generator script is 600 lines of Python the team must maintain
- Re-running the generator after every descriptor change is an
  extra step (mitigated by `make generate` Makefile target)

## References

- `scripts/generate_forge.py` (the auto-generator)
- `.claude/rules/40_forge_module_contract.md` (the contract)
- [AGENTS.md spec](https://agents.md/) — the cross-tool standard we
  comply with
