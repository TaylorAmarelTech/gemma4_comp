# Tests — Schemas

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/core/schemas

# or directly via pytest:
pytest src/forge/core/schemas/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/core/schemas --recursive
```

## Test files

- `tests/test_schemas_roundtrip.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/core/schemas` to find modules that depend on
this one; their tests will exercise this module via their own flows.
