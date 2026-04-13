# Purpose — Trainer Agent

> Run Unsloth + LoRA fine-tune on the curated dataset

## Long description

Loads the base model via the Unsloth adapter, applies the LoRA
config, runs SFTTrainer (or DPO as a stretch goal), checkpoints
periodically, and saves LoRA adapters + merged fp16 weights.

## Module id

`duecare.agents.trainer`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
