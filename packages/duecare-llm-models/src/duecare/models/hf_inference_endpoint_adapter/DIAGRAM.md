# Diagram — HF Inference Endpoint Adapter

## Local position

```
          Models
                │
     ┌──────────┼──────────┐
     │          │          │
  Base  Transformers Adapter  llama.cpp Adapter  HF Inference Endpoint Adapter *
```

`*` = this module.

## Full-system diagram

See `src/forge/DIAGRAM.md` for the whole tree.
