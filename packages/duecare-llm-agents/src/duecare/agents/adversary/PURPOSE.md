# Purpose — Adversary Agent

> Mutate probes through 631 prompt-injection mutators + 126 attack chains

## Long description

Pure rule-based agent (no LLM calls) that imports the reference
framework's prompt_injection registry and chain_detection seeds
as a sidecar dependency. Takes probes from DataGenerator and
produces adversarial variants stress-testing the target model.

## Module id

`duecare.agents.adversary`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.

## Notes

Depends on the reference framework as a sidecar path dependency.
