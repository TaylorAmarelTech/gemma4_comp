# TESTS — `duecare.chat.harness`

## Run the module's tests

```bash
# from repo root
python -m pytest packages/duecare-llm-chat/tests -q
```

## Run all package tests

```bash
make test
```

## Test conventions

- Tests live at `packages/duecare-llm-chat/tests/test_*.py`
- One test file per source module where practical
- Mock external I/O in unit tests; integration tests hit real SQLite + small fixtures
- See `.claude/rules/30_test_before_commit.md` at the repo root
