# Tests — Multimodal Classification Task

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/tasks/multimodal_classification

# or directly via pytest:
pytest src/forge/tasks/multimodal_classification/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/tasks/multimodal_classification --recursive
```

## Test files

- `tests/test_multimodal_classification.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/tasks/multimodal_classification` to find modules that depend on
this one; their tests will exercise this module via their own flows.
