# Tests — Judge Agent

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/agents/judge

# or directly via pytest:
pytest src/forge/agents/judge/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/agents/judge --recursive
```

## Test files

- `tests/test_judge.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/agents/judge` to find modules that depend on
this one; their tests will exercise this module via their own flows.
