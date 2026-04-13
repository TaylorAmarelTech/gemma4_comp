# duecare-llm-publishing

> Duecare publication: HF Hub, Kaggle Datasets/Models/Kernels, markdown reports, model cards.

Part of the **Duecare** multi-package distribution. See the
[main project README](../../README.md) and
[the_forge.md architecture doc](../../docs/the_forge.md) for the full
context.

## Install

```bash
pip install duecare-llm-publishing
```

## Optional extras

```bash
pip install duecare-llm-publishing[hf-hub]
```

```bash
pip install duecare-llm-publishing[kaggle]
```

```bash
pip install duecare-llm-publishing[all]
```


## What's in this package

Python imports provided:
- `duecare.publishing`

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

- Repository: https://github.com/taylorsamarel/gemma4_comp
- Documentation: https://github.com/taylorsamarel/gemma4_comp/blob/main/docs/the_forge.md
- License: MIT

## How to develop on this package

This package lives inside the Duecare workspace
(`gemma4_comp/packages/duecare-llm-publishing/`). The workspace root has a `uv` workspace
config that resolves all `duecare-llm-*` dependencies from sibling
packages instead of from PyPI, so editable installs work out of the box:

```bash
# from the workspace root
uv sync
uv run pytest packages/duecare-llm-publishing
```

You can also pip-install in editable mode without uv:

```bash
pip install -e packages/duecare-llm-publishing
```
