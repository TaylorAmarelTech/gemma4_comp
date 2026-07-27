# ADR-001: Multi-package PyPI split (original 17 wheels; 18 current)

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

Split into **17 intended registry packages** under the **PEP 420 implicit
namespace package** `duecare.*`. Each package owns one folder under
`packages/` and has its own `pyproject.toml`. The original decision proposed
lock-step semantic versions. The 2026-07-27 amendment below replaces that
proposal with manifest-backed independent SemVer before the first registry
publication.

Heavy dependencies live in **optional extras**:

The commands below show the post-release interface. Today, install the source
workspace with `uv sync --all-packages`.

```bash
pip install duecare-llm-models[transformers]   # adds transformers + torch
pip install duecare-llm-models[unsloth]        # adds unsloth + peft + trl
pip install duecare-llm-models[llama-cpp]      # adds llama-cpp-python
pip install duecare-llm-server[observability]  # adds prometheus-client
```

The original decision intended the meta-package `duecare-llm` as the
"I want everything" entry point.

## Amendment — 2026-07-26

The independent `duecare-llm-kit` reporting/corpus toolkit is now the 18th
workspace member. The `duecare-llm` meta-package remains intentionally scoped
to the seven-package workflow core listed in its `pyproject.toml`; it does not
silently add the kit, server, training, or other specialist surfaces. Source
reviewers who need the complete graph should run `uv sync --all-packages`.

## Amendment — 2026-07-27

None of the 18 distributions is published on PyPI. The packages adopt
**independent semantic versions** because `duecare-llm-chat` already has a
public notebook-compatibility cadence (`0.17.0`), `duecare-llm-server` is
`0.1.2`, and the other workspace packages are `0.1.0`. Artificially raising
unrelated packages or downgrading chat would obscure compatibility history.

`configs/duecare/package_release.toml` is the reviewed release cohort and first
publication order. A production tag has the form
`package-NAME-vMAJOR.MINOR.PATCH`, selects exactly one manifest row, and must
match that package's `pyproject.toml`. Manual workflow runs may build all rows
or a selected package and may use TestPyPI, but cannot publish to production.
`.github/workflows/pypi-publish.yml` remains the sole OIDC publisher; direct
token/twine publication is not part of this decision.

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
- 18 separate package test surfaces can parallelize in CI
- Clear bug-report routing (which package owns the bug)

**Negative:**
- Workspace tooling is more complex; we use a `uv` workspace, an explicit
  release manifest, and a multi-package build order
- Cross-package refactors require careful version coordination
- New contributors face an 18-package mental model (mitigated by
  `docs/architecture.md` + `docs/adr/002-folder-per-module-pattern.md`)

## References

- `pyproject.toml` (uv workspace root with all 18 current members)
- [`docs/integration_plan.md`](../integration_plan.md)
- [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/)
