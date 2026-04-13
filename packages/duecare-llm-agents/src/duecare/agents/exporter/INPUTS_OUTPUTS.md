# Inputs & Outputs — Exporter Agent

## Reads (inputs)

- `merged_fp16`
- `no_harm_certificate`

## Writes (outputs)

- `gguf_paths`
- `litert_paths`
- `hf_hub_url`
- `kaggle_model_url`

## Depends on (other modules)

- `duecare.core`
- `duecare.agents.base`
- `duecare.publishing`

## Contract

The public surface of this module (its stable contract) is defined
by the protocol(s) in `src/forge/core/contracts/` that it implements,
plus any symbols listed in its `__init__.py` under `__all__`.

Changes that affect any of the above require updating `HIERARCHY.md`
on every dependent module (listed in `HIERARCHY.md`).
