# Benchmark — purpose

**Module id:** `duecare.benchmark`

## One-line

Bundled benchmark test sets + runner / aggregator.

## Long-form

Bundled benchmark test sets + runner / aggregator.

Each test set is a JSONL where each row has:
    id                  : str   (stable identifier)
    category            : str   (taxonomy bucket for per-category breakdown)
    locale              : str   (passed to the pipeline)
    text                : str   (the prompt to moderate)
    expected_verdict    : str   ("block" | "review" | "pass")
    expected_severity_min: int  (lower bound; runner counts severity_max if higher)
    expected_signals    : list[str] (signals that should fire; advisory)

## See also

- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers
- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree
- [`STATUS.md`](STATUS.md) — completion state and TODO list
