# duecare-llm-benchmark

Bundled benchmark test sets + scoring + aggregation for the Duecare
safety harness. Pure Python; no FastAPI, no GPU dependency. Both the
live-demo notebook (`taylorsamarel/duecare-live-demo`) and the
training/eval notebook (`taylorsamarel/duecare-bench-and-tune`) install
this wheel to share the same scoring logic and the same JSONL test
sets.

## What's inside

```
duecare/benchmark/
├── __init__.py        # list_sets() / load_set() / score_row() / aggregate()
└── smoke_25.jsonl     # 25 curated prompts (passport confiscation,
                          debt bondage, fee fraud, doxxing, kafala,
                          contract substitution, child labour,
                          multilingual variants + 3 legitimate-control
                          rows)
```

## Adding new test sets

Drop a new `<slug>.jsonl` next to `smoke_25.jsonl`. Each row needs:

```json
{"id": "...", "category": "...", "locale": "ph",
 "text": "...", "expected_verdict": "block",
 "expected_severity_min": 8, "expected_signals": ["passport_id"]}
```

`list_sets()` discovers it automatically.

## Public API

```python
from duecare.benchmark import list_sets, load_set, score_row, aggregate

sets = list_sets()                              # -> [BenchmarkSet, ...]
rows = load_set("smoke_25")                     # -> [dict, ...]
scored = [score_row(expected, result) for ...]  # per-row pass/miss
summary = aggregate(scored)                     # roll-up dict
```
