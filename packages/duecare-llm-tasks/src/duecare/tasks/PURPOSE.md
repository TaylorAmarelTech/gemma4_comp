# Purpose — Tasks

> Capability tests runnable against any (Model, DomainPack) pair

## Long description

A task is a pure function: (model, domain, config) -> TaskResult.
Tasks do not call tools, maintain state, or make decisions -
decisions live in agents. Every task declares its required
capabilities (text, vision, function_calling) and will refuse
to run against a model that doesn't support them.

## Module id

`duecare.tasks`

## Kind

layer

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
