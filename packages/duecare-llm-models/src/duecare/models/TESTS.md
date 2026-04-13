# Tests — Models

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/models

# or directly via pytest:
pytest src/forge/models/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/models --recursive
```

## Test files

- `tests/test_model_registry_populated.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/models` to find modules that depend on
this one; their tests will exercise this module via their own flows.
