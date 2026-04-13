# Tests — Exporter Agent

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/agents/exporter

# or directly via pytest:
pytest src/forge/agents/exporter/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/agents/exporter --recursive
```

## Test files

- `tests/test_exporter.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/agents/exporter` to find modules that depend on
this one; their tests will exercise this module via their own flows.
