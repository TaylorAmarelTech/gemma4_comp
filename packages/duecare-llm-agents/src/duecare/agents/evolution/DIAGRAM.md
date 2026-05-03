# DIAGRAM — `duecare.agents.evolution`

```
            ┌──────────────────────┐
            │    duecare.core      │ (contracts + schemas)
            └──────────┬───────────┘
                       │ implements / consumes
                       ▼
            ┌──────────────────────┐
            │  Evolution           │  ← THIS MODULE
            │  (duecare.agents.evolution)│
            └──────────┬───────────┘
                       │ exports
                       ▼
            ┌──────────────────────┐
            │  upstream consumers  │
            └──────────────────────┘
```

For the full system map see [`docs/system_map.md`](../../../../../../docs/system_map.md) or the interactive HTML version.
