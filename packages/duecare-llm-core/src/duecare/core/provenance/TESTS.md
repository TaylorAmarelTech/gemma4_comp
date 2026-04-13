# Tests — Provenance

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/core/provenance

# or directly via pytest:
pytest src/forge/core/provenance/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/core/provenance --recursive
```

## Test files

- `tests/test_provenance.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/core/provenance` to find modules that depend on
this one; their tests will exercise this module via their own flows.
