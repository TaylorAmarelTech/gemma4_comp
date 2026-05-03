# Pipeline — purpose

**Module id:** `duecare.domains.pipeline`

## One-line

DueCare document scraping and processing pipeline.

## Long-form

DueCare document scraping and processing pipeline.

Compartmentalized modules for fetching, extracting, classifying, and
storing documents related to labor trafficking and exploitation.

Each module is independently importable and testable.  Compose them
in any order -- they communicate only through Pydantic models, never
through direct imports of each other.

## See also

- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers
- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree
- [`STATUS.md`](STATUS.md) — completion state and TODO list
