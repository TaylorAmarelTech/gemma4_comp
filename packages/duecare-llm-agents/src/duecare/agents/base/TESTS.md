# Tests — Base

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/agents/base

# or directly via pytest:
pytest src/forge/agents/base/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/agents/base --recursive
```

## Test files

- `tests/test_base.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/agents/base` to find modules that depend on
this one; their tests will exercise this module via their own flows.
