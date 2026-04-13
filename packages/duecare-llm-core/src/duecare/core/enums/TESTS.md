# Tests — Enums

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/core/enums

# or directly via pytest:
pytest src/forge/core/enums/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/core/enums --recursive
```

## Test files

- `tests/test_enum_ordinals.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/core/enums` to find modules that depend on
this one; their tests will exercise this module via their own flows.
