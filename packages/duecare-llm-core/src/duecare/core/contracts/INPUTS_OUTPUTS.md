# Inputs & Outputs — Contracts

## Reads (inputs)

- `duecare.core.enums`
- `duecare.core.schemas`

## Writes (outputs)

- `Model`
- `DomainPack`
- `Task`
- `Agent`
- `Coordinator`

## Depends on (other modules)

- `duecare.core.enums`
- `duecare.core.schemas`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
