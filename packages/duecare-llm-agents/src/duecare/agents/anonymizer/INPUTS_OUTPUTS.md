# Inputs & Outputs — Anonymizer Agent

## Reads (inputs)

- `synthetic_probes`
- `adversarial_probes`

## Writes (outputs)

- `clean_probes`
- `anon_audit`
- `quarantine`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
