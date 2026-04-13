# Purpose — Agents

> The 12-agent Duecare swarm

## Long description

Autonomous actors that compose tasks into workflows. Each agent
has a role (from duecare.core.enums.AgentRole), a model it uses
internally, a set of tools it can call, declared inputs/outputs,
and a cost budget.

Agents are the only layer that makes decisions. Tasks compute;
agents decide; the Coordinator orchestrates.

## Module id

`duecare.agents`

## Kind

layer

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
