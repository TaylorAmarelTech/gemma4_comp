# Diagram — Models

## Local position

```
          Duecare
                │
     ┌──────────┼──────────┐
     │          │          │
  Core  Domains  Tasks  Models *
                │
                ├── Base
                ├── Transformers Adapter
                ├── llama.cpp Adapter
                ├── Unsloth Adapter
                ├── Ollama Adapter
                ├── OpenAI-Compatible Adapter
                ├── Anthropic Adapter
                ├── Google Gemini Adapter
                ├── HF Inference Endpoint Adapter
```

`*` = this module.

## Full-system diagram

See `src/forge/DIAGRAM.md` for the whole tree.
