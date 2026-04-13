# Purpose — Registry

> Generic plugin registry used by models, domains, agents, tasks

## Long description

A single generic Registry[T] class. Every plugin kind (models,
domains, agents, tasks) has its own registry instance but shares
the same underlying code. Plugins register themselves on import
via @registry.register("id").

## Module id

`duecare.core.registry`

## Kind

module

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
