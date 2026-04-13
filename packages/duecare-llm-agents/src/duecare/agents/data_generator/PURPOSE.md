# Purpose — DataGenerator Agent

> Synthesize probes + graded response examples using a strong teacher model

## Long description

Calls a strong teacher model (Claude Haiku 4.5 or Gemini Flash
by default; configurable) to generate synthetic probes tailored
to the domain pack's taxonomy, plus graded response examples
(worst/bad/neutral/good/best) for each probe.

Uses self-consistency: generate N candidate responses, let the
Judge agent pick the best, mark the unselected as lower grades.

## Module id

`duecare.agents.data_generator`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.

## Notes

Budget-capped at $20/run by default.
