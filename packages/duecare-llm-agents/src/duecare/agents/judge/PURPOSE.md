# Purpose — Judge Agent

> Score model outputs against the domain rubric in 4 modes

## Long description

Scores the target model's outputs against the domain rubric
using four modes: rule-based (fast, deterministic), embedding
(similarity to graded examples), llm_judge (another LLM as
rubric executor), and hybrid (weighted ensemble).

Used both to populate graded examples for training and to
evaluate the fine-tuned judge at benchmark time.

## Module id

`duecare.agents.judge`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
