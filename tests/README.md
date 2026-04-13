# tests/

Test layout per `docs/architecture.md` section 18:

- `unit/` - per-module unit tests, no I/O
- `integration/` - pipeline tests against real SQLite + small fixtures
- `fixtures/` - `mini_benchmark.sqlite`, `sample_items.json`, etc.
