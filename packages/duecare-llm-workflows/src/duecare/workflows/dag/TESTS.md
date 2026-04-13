# Tests — DAG

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/workflows/dag

# or directly via pytest:
pytest src/forge/workflows/dag/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/workflows/dag --recursive
```

## Test files

- `tests/test_dag.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/workflows/dag` to find modules that depend on
this one; their tests will exercise this module via their own flows.
