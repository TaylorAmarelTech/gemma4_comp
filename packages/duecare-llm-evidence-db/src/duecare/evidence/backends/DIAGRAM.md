# DIAGRAM — `duecare.evidence.backends`

```
            ┌──────────────────────┐
            │    duecare.core      │ (contracts + schemas)
            └──────────┬───────────┘
                       │ implements / consumes
                       ▼
            ┌──────────────────────┐
            │  Backends            │  ← THIS MODULE
            │  (duecare.evidence.backends)│
            └──────────┬───────────┘
                       │ exports
                       ▼
            ┌──────────────────────┐
            │  upstream consumers  │
            └──────────────────────┘
```

For the full system map see [`docs/system_map.md`](../../../../../../docs/system_map.md) or the interactive HTML version.
