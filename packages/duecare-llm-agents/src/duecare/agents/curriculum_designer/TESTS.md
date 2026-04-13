# Tests — CurriculumDesigner Agent

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/agents/curriculum_designer

# or directly via pytest:
pytest src/forge/agents/curriculum_designer/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/agents/curriculum_designer --recursive
```

## Test files

- `tests/test_curriculum_designer.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/agents/curriculum_designer` to find modules that depend on
this one; their tests will exercise this module via their own flows.
