# Inputs & Outputs — Core

## Reads (inputs)

- (none — leaf module)

## Writes (outputs)

- `Model protocol`
- `DomainPack protocol`
- `Task protocol`
- `Agent protocol`
- `Coordinator protocol`
- `all shared schemas`

## Depends on (other modules)

- (none)

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
