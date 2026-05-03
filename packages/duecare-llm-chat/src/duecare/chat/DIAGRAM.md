# DIAGRAM — `duecare.chat`

```
            ┌──────────────────────┐
            │    duecare.core      │ (contracts + schemas)
            └──────────┬───────────┘
                       │ implements / consumes
                       ▼
            ┌──────────────────────┐
            │  Chat                │  ← THIS MODULE
            │  (duecare.chat  )│
            └──────────┬───────────┘
                       │ exports
                       ▼
            ┌──────────────────────┐
            │  upstream consumers  │
            └──────────────────────┘
```

For the full system map see [`docs/system_map.md`](../../../../../../docs/system_map.md) or the interactive HTML version.
