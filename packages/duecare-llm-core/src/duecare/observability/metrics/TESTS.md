# Tests — Metrics

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/observability/metrics

# or directly via pytest:
pytest src/forge/observability/metrics/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/observability/metrics --recursive
```

## Test files

- `tests/test_metrics.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/observability/metrics` to find modules that depend on
this one; their tests will exercise this module via their own flows.
