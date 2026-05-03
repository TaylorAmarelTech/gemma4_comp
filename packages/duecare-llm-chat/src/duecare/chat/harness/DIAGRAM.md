# DIAGRAM — `duecare.chat.harness`

```
            ┌──────────────────────┐
            │    duecare.core      │ (contracts + schemas)
            └──────────┬───────────┘
                       │ implements / consumes
                       ▼
            ┌──────────────────────┐
            │  Harness             │  ← THIS MODULE
            │  (duecare.chat.harness)│
            └──────────┬───────────┘
                       │ exports
                       ▼
            ┌──────────────────────┐
            │  upstream consumers  │
            └──────────────────────┘
```

For the full system map see [`docs/system_map.md`](../../../../../../docs/system_map.md) or the interactive HTML version.
