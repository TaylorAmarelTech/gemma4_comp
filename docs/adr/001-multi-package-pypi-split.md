# ADR-001: Multi-package PyPI split (17 wheels under `duecare.*` namespace)

- **Status:** Accepted
- **Date:** 2026-04-15
- **Deciders:** Taylor Amarel

## Context

Duecare's research codebase grew from a single 627-module `src/`
folder to 17 logically distinct packages: `core` (contracts +
schemas), `models` (8 backends), `domains` (3 packs), `tasks` (9
capability tests), `agents` (12 agents), `workflows` (DAG runner),
`publishing` (HF + Kaggle), `chat` (chat surface), `engine` (pipeline),
`benchmark`, `training` (Unsloth), `evidence-db`, `nl2sql`,
`research-tools`, `server`, `cli`, and the `duecare-llm` meta package.

Three audiences install Duecare:

1. **Kaggle notebooks** — install only what each notebook needs
   (e.g., the chat playground doesn't need `duecare-llm-training`)
2. **Research labs / NGOs** — typically want everything
3. **External integrators** — want one targeted layer (e.g., just
   the harness `duecare-llm-chat`, not the whole stack)

A single mega-package would force every consumer to install
multi-GB heavy deps (Unsloth, transformers, llama.cpp) for a
2 MB harness import.

## Decision

Split into **17 PyPI packages** under the **PEP 420 implicit
namespace package** `duecare.*`. Each package owns one folder under
`packages/`, has its own `pyproject.toml`, semver-tagged in lock-step
across all packages.

Heavy dependencies live in **optional extras**:

```bash
pip install duecare-llm-models[transformers]   # adds transformers + torch
pip install duecare-llm-models[unsloth]        # adds unsloth + peft + trl
pip install duecare-llm-models[llama-cpp]      # adds llama-cpp-python
pip install duecare-llm-server[observability]  # adds prometheus-client
```

The meta-package `duecare-llm` pulls all 17 in for "I want
everything" installs.

## Alternatives considered

- **Single mega-package.** Rejected because Kaggle notebooks would
  install 4-5 GB of deps for a 2 MB harness. Cold-start time would
  dominate the demo.
- **Two-package split (core + everything-else).** Rejected because
  it doesn't help the "I want only the harness" external integrator
  case.
- **Plugins / entry-points instead of packages.** Rejected because
  it complicates the typed-Protocol contract; plugins can violate
  contracts at import time.

## Consequences

**Positive:**
- Kaggle notebook cold start is ~30s instead of multi-minute
- External integrators install a clean 50-200 MB instead of multi-GB
- Each package can release independently (semver-disciplined)
- 17 separate test runs can parallelize in CI
- Clear bug-report routing (which package owns the bug)

**Negative:**
- Workspace tooling is more complex; we use `uv` workspace + a 17-row
  Helm chart for the multi-arch image build
- Cross-package refactors require careful version coordination
- New contributors face a 17-package mental model (mitigated by
  `docs/architecture.md` + `docs/adr/002-folder-per-module-pattern.md`)

## References

- `pyproject.toml` (uv workspace root with all 17 members)
- [`docs/integration_plan.md`](../integration_plan.md)
- [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/)
