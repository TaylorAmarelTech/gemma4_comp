# Inputs & Outputs — Curator Agent

## Reads (inputs)

- `clean_probes`

## Writes (outputs)

- `train_jsonl`
- `val_jsonl`
- `test_jsonl`
- `split_stats`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
