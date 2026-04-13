# Duecare module contract — folder-per-module pattern

> Auto-loaded at the project memory level.

Every module in the Duecare codebase is a **folder**, not a file. Every
module folder has the same structure, so any AI agent or human reviewer
can walk into any folder and immediately orient themselves.

## Required files in every module folder

| File | Who writes it | Purpose |
|---|---|---|
| `PURPOSE.md` | auto-generated | one-line + long-form description |
| `AGENTS.md` | auto-generated | agentic instructions for AI readers (standards-compliant) |
| `INPUTS_OUTPUTS.md` | auto-generated | context keys + protocols the module reads and writes |
| `HIERARCHY.md` | auto-generated | parent / siblings / children / dependencies / dependents |
| `DIAGRAM.md` | auto-generated | local ASCII diagram of position in system |
| `TESTS.md` | auto-generated | how to run tests for this module |
| `STATUS.md` | auto-generated | stub / partial / complete + TODO list |
| `__init__.py` | developer | Python package marker, may export public symbols |
| `<source>.py` (one or more) | developer | actual implementation |
| `tests/__init__.py` | generator | test package marker |
| `tests/test_<source>.py` | developer | at least one real test per module |

## How to add a new module

Do NOT create the folder by hand. Add an entry to the `MODULES` list in
`scripts/generate_forge.py`:

```python
{
    "id": "duecare.agents.my_new_agent",
    "path": "src/forge/agents/my_new_agent",
    "kind": "agent",
    "parent_id": "duecare.agents",
    "display_name": "My New Agent",
    "one_liner": "Brief one-line description",
    "description": "Longer description...",
    "reads": ["some_context_key"],
    "writes": ["produced_context_key"],
    "depends_on": ["duecare.core", "duecare.agents.base"],
    "source_files": ["__init__.py", "my_new_agent.py"],
    "test_files": ["test_my_new_agent.py"],
    "status": "stub",
},
```

Then run `python scripts/generate_forge.py`. The script creates the
folder, all meta files, the source stubs, and the test stubs.

## Why we enforce this

1. **Every folder is self-describing.** An AI agent (or a human who
   just joined the project) can navigate to any folder and understand
   its purpose, position, and contract without reading any other file.

2. **AGENTS.md is an emerging cross-tool standard.** Claude Code,
   Cursor, Copilot, Windsurf, Aider, Zed, Warp, RooCode — all of them
   read AGENTS.md files natively. Our structure gives every AI tool a
   grounded view of any subtree.

3. **Meta files are auto-generated so they stay in sync.** If the
   `MODULES` descriptor changes, one script re-run updates every
   cross-reference (siblings, children, dependents) across the whole
   tree. No manual maintenance burden.

4. **Tests live with the module.** Not in a far-away `tests/` folder.
   When you modify `src/forge/agents/judge/judge.py`, the tests are in
   `src/forge/agents/judge/tests/` — zero navigation cost.

## What not to do

- Do not add a module as a single `.py` file under a parent folder.
  Every module is a folder.
- Do not hand-edit meta files. Always regenerate.
- Do not import concrete classes across modules; use protocols from
  `duecare.core.contracts`.
- Do not add source files to the generator's auto-generation set — the
  generator only creates **stubs** that it never overwrites, so your
  implementation is safe.

## Duecare CLI commands for navigating the tree

```bash
duecare tree                              # full tree
duecare tree --layer agents               # just one layer
duecare review src/forge/agents/judge     # read a module's meta files
duecare test src/forge/agents/judge       # run its tests
duecare test src/forge/agents --recursive # run all agent tests
duecare status                            # completeness report for all modules
duecare deps src/forge/agents/judge       # what the judge depends on
duecare dependents src/forge/agents/judge # what depends on the judge
```

These commands read the meta files directly, so they always reflect
the current state of the tree.
