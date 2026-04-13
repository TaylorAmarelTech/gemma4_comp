# Inputs & Outputs — Validator Agent

## Reads (inputs)

- `trained_model_path`
- `adversarial_probes`

## Writes (outputs)

- `validation_report`
- `no_harm_certificate`
- `regression_list`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`
- `duecare.agents.adversary`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
