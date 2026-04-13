# Tests — Publishing

## Run tests for this module only

```bash
# via forge CLI (preferred):
duecare test src/forge/publishing

# or directly via pytest:
pytest src/forge/publishing/tests/ -v
```

## Run tests for this module plus all children

```bash
duecare test src/forge/publishing --recursive
```

## Test files

- (none yet)

## What each test validates

(Fill in as tests are written.)

## Integration tests that pull in this module

Run `duecare dependents src/forge/publishing` to find modules that depend on
this one; their tests will exercise this module via their own flows.
