# Purpose — Runner

> Executes a Workflow by walking the agent DAG

## Long description

Resolves agents from agent_registry, walks the DAG in topological order, calls each agent's execute(), merges outputs, handles retries and budget caps.

## Module id

`duecare.workflows.runner`

## Kind

module

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
