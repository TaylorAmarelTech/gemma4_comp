# Tests — HF Hub

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/publishing/hf_hub

# or directly via pytest:
pytest src/forge/publishing/hf_hub/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/publishing/hf_hub --recursive
```

## Test files

- `tests/test_hf_hub.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/publishing/hf_hub` to find modules that depend on
this one; their tests will exercise this module via their own flows.
