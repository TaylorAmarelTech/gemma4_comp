# Tests — Contracts

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/core/contracts

# or directly via pytest:
pytest src/forge/core/contracts/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/core/contracts --recursive
```

## Test files

- `tests/test_protocols_runtime_checkable.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/core/contracts` to find modules that depend on
this one; their tests will exercise this module via their own flows.
