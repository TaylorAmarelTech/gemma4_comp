# Inputs & Outputs — Trainer Agent

## Reads (inputs)

- `train_jsonl`
- `val_jsonl`
- `next_curriculum`

## Writes (outputs)

- `lora_adapters`
- `merged_fp16`
- `training_log`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`
- `duecare.models.unsloth_adapter`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
