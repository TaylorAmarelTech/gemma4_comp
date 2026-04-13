# Purpose — Duecare

> Agentic, universal LLM safety harness

## Long description

Duecare is an agentic LLM safety harness. You give it a model and a
domain pack; a swarm of autonomous agents generates synthetic probes,
mutates them adversarially, evaluates the target model, identifies
failure modes, generates corrective training data, fine-tunes the
model, validates the fine-tune, and publishes the results - all
without human intervention.

Model-agnostic (any HF / GGUF / OpenAI-compatible).
Domain-agnostic (pluggable domain packs).
See docs/the_forge.md for the full architecture.

## Module id

`duecare`

## Kind

root

## Status

`partial`

See `STATUS.md` for the TODO list and completion criteria.
