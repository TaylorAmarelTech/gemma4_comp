# Tests — Pack

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/domains/pack

# or directly via pytest:
pytest src/forge/domains/pack/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/domains/pack --recursive
```

## Test files

- `tests/test_file_domain_pack.py`

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/domains/pack` to find modules that depend on
this one; their tests will exercise this module via their own flows.
