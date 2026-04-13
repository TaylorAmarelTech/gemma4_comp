# Tests — Anonymization Task

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/tasks/anonymization

# or directly via pytest:
pytest src/forge/tasks/anonymization/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/tasks/anonymization --recursive
```

## Test files

- `tests/test_anonymization.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/tasks/anonymization` to find modules that depend on
this one; their tests will exercise this module via their own flows.
