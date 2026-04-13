# Inputs & Outputs — Anonymization Task

## Reads (inputs)

- `duecare.core.contracts.Model`
- `duecare.core.contracts.DomainPack`

## Writes (outputs)

- `TaskResult with PII span recall, precision, false positive rate`

## Depends on (other modules)

- `duecare.core`
- `duecare.tasks.base`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
