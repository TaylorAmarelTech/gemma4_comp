# Tests — Tool Use Task

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/tasks/tool_use

# or directly via pytest:
pytest src/forge/tasks/tool_use/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/tasks/tool_use --recursive
```

## Test files

- `tests/test_tool_use.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/tasks/tool_use` to find modules that depend on
this one; their tests will exercise this module via their own flows.
