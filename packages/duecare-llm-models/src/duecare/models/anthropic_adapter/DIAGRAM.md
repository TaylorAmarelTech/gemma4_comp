# Diagram — Anthropic Adapter

## Local position

```
          Models
                │
     ┌──────────┼──────────┐
     │          │          │
  Base  Transformers Adapter  llama.cpp Adapter  Anthropic Adapter *
```

`*` = this module.

## Full-system diagram

See `src/forge/DIAGRAM.md` for the whole tree.
