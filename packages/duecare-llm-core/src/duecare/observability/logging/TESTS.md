# Tests — Logging

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/observability/logging

# or directly via pytest:
pytest src/forge/observability/logging/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/observability/logging --recursive
```

## Test files

- `tests/test_logging.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/observability/logging` to find modules that depend on
this one; their tests will exercise this module via their own flows.
