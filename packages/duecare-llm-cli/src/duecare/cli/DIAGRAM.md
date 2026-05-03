# DIAGRAM — `duecare.cli`

```
            ┌──────────────────────┐
            │    duecare.core      │ (contracts + schemas)
            └──────────┬───────────┘
                       │ implements / consumes
                       ▼
            ┌──────────────────────┐
            │  Cli                 │  ← THIS MODULE
            │  (duecare.cli   )│
            └──────────┬───────────┘
                       │ exports
                       ▼
            ┌──────────────────────┐
            │  upstream consumers  │
            └──────────────────────┘
```

For the full system map see [`docs/system_map.md`](../../../../../../docs/system_map.md) or the interactive HTML version.
