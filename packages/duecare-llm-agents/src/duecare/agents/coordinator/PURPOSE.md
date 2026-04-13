# Purpose — Coordinator Agent

> Orchestrates the 12-agent swarm via a workflow DAG

## Long description

Special agent. In the default deployment, the Coordinator IS
Gemma 4 E4B using native function calling to schedule the
swarm - each other agent is exposed to it as a tool.

Falls back to a rule-based DAG walker if function calling is
not available on the configured model.

## Module id

`duecare.agents.coordinator`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.

## Notes

The Coordinator's tools are the other 11 agents.
