# duecare-llm-tasks

> Duecare capability tests: guardrails, anonymization, classification, fact extraction, grounding, multimodal classification, adversarial multi-turn, tool use, cross-lingual.

Part of the **Duecare** multi-package distribution. See the
[main project README](../../README.md) and
[the_forge.md architecture doc](../../docs/the_forge.md) for the full
context.

## Install

```bash
pip install duecare-llm-tasks
```

## Optional extras

```bash
pip install duecare-llm-tasks[anonymization]
```

```bash
pip install duecare-llm-tasks[embedding]
```


## What's in this package

Python imports provided:
- `duecare.tasks`

## Position in the Duecare stack

```
duecare-llm (meta)
    |
    +-- duecare-llm-publishing
    +-- duecare-llm-workflows
    |       |
    +-------+ duecare-llm-agents
                |
                +-- duecare-llm-tasks
                        |
                        +-- duecare-llm-models
                        +-- duecare-llm-domains
                                |
                                +-- duecare-llm-core *
```

## Source

- Repository: https://github.com/TaylorAmarelTech/gemma4_comp
- Documentation: https://github.com/TaylorAmarelTech/gemma4_comp/blob/main/docs/the_forge.md
- License: MIT

## How to develop on this package

This package lives inside the Duecare workspace
(`gemma4_comp/packages/duecare-llm-tasks/`). The workspace root has a `uv` workspace
config that resolves all `duecare-llm-*` dependencies from sibling
packages instead of from PyPI, so editable installs work out of the box:

```bash
# from the workspace root
uv sync
uv run pytest packages/duecare-llm-tasks
```

You can also pip-install in editable mode without uv:

```bash
pip install -e packages/duecare-llm-tasks
```
