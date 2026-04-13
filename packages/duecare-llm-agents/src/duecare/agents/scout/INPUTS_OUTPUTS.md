# Inputs & Outputs — Scout Agent

## Reads (inputs)

- `domain_pack (via ctx.domain_id)`

## Writes (outputs)

- `domain_readiness_score`
- `domain_gaps`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`
- `duecare.domains`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
