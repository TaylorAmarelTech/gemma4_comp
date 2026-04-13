# Purpose — Core

> Contracts, schemas, enums, registries - imported by every other layer

## Long description

Core holds the cross-layer contracts. No concrete implementations
live here. Every other layer (models, domains, tasks, agents,
workflows, publishing, observability) imports from duecare.core and
from nothing else above it.

If a type belongs in more than one layer, it belongs in core.

## Module id

`duecare.core`

## Kind

layer

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
