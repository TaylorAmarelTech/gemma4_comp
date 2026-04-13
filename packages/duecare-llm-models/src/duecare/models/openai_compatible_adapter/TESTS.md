# Tests — OpenAI-Compatible Adapter

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/models/openai_compatible_adapter

# or directly via pytest:
pytest src/forge/models/openai_compatible_adapter/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/models/openai_compatible_adapter --recursive
```

## Test files

- `tests/test_adapter.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/models/openai_compatible_adapter` to find modules that depend on
this one; their tests will exercise this module via their own flows.
