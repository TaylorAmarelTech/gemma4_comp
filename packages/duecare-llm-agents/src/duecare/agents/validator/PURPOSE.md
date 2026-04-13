# Purpose — Validator Agent

> Red-team the trained model, issue the no-harm certificate

## Long description

After the Trainer agent produces a fine-tuned model, Validator
runs a held-out adversarial suite against it. Before/after
delta per capability test. Hard stop: if the trained model is
more harmful than the base on any category, Validator aborts
the release and Historian writes the incident report.

## Module id

`duecare.agents.validator`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
