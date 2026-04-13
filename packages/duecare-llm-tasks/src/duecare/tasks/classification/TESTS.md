# Tests — Classification Task

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/tasks/classification

# or directly via pytest:
pytest src/forge/tasks/classification/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/tasks/classification --recursive
```

## Test files

- `tests/test_classification.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/tasks/classification` to find modules that depend on
this one; their tests will exercise this module via their own flows.
