# Publish strategy — public GitHub + multi-package PyPI + Kaggle Notebooks

> Auto-loaded at the project memory level.

The project ships as **three synchronized publication channels**, each
with a different audience. Every action that produces a deliverable
should target all three or explicitly document which ones it skips.

## Channel 1: Public GitHub repository

**Audience:** hackathon judges (Technical Depth & Execution verification),
open-source developers, future contributors.

- `github.com/taylorsamarel/gemma4_comp` (or equivalent — the actual slug
  is TBD)
- MIT license
- CI on every PR: `ruff check`, `mypy`, `duecare test src/forge --recursive`
- GitHub Actions: `@claude` PR review via
  `anthropics/claude-code-action@v1`
- `_reference/` is `.gitignore`d (contains proprietary benchmark material)
- `data/`, `models/`, `logs/`, `checkpoints/` are `.gitignore`d
- Meta files (PURPOSE, AGENTS, INPUTS_OUTPUTS, HIERARCHY, DIAGRAM, TESTS,
  STATUS) are committed — they are load-bearing documentation for the
  folder-per-module pattern

## Channel 2: Multi-package PyPI distribution

**Audience:** Kaggle notebooks, research labs, NGO deployers, future
re-users.

**Split.** The codebase ships as **7 PyPI packages under the `duecare-llm-*`
namespace**, all sharing the `duecare` Python import namespace (PEP 420
implicit namespace packages):

| PyPI package | Python import | Contents |
|---|---|---|
| `duecare-llm-core` | `duecare.core.*` | contracts, schemas, enums, registry, provenance, observability |
| `duecare-llm-models` | `duecare.models.*` | all 8 model adapters (with optional extras for heavy deps) |
| `duecare-llm-domains` | `duecare.domains.*` | domain pack loader + pack base |
| `duecare-llm-tasks` | `duecare.tasks.*` | 9 capability tests |
| `duecare-llm-agents` | `duecare.agents.*` | 12-agent swarm |
| `duecare-llm-workflows` | `duecare.workflows.*` | DAG loader + runner |
| `duecare-llm-publishing` | `duecare.publishing.*` | HF Hub, Kaggle, reports, model cards |
| `duecare-llm` (meta) | `duecare.cli` (+ re-exports) | installs all of the above + the `duecare` CLI entry point |

**Why multiple packages, not one:**

- **Kaggle notebooks can install only what they need.** A Phase 1
  baseline notebook runs `!pip install duecare-llm-core duecare-llm-models
  duecare-llm-tasks duecare-llm-domains` — ~300 MB of deps instead of
  multi-GB with everything.
- **Modularity and extensibility.** A research team that only wants
  the Judge agent doesn't need to pull in the Trainer's Unsloth stack.
- **Independent release velocity.** The core contracts stabilize
  first; agents churn fast in week 2-3. Different release cadences.
- **External re-use.** Someone builds a new domain pack for medical
  misinformation without ever touching our agents layer.

**Optional extras** inside each package pull in heavy dependencies only
when needed:

```bash
pip install duecare-llm-models[transformers]     # adds transformers + torch
pip install duecare-llm-models[unsloth]          # adds unsloth + peft + trl
pip install duecare-llm-models[llama-cpp]        # adds llama-cpp-python
pip install duecare-llm-models[all]              # everything above
pip install duecare-llm-publishing[hf-hub]       # adds huggingface_hub
pip install duecare-llm-publishing[kaggle]       # adds kaggle CLI
```

**Workspace layout** (target after the restructure):

```
gemma4_comp/
├── packages/
│   ├── duecare-llm-core/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/forge/core/
│   │   │   └── (folder-per-module, same as today)
│   │   └── tests/
│   ├── duecare-llm-models/
│   ├── duecare-llm-domains/
│   ├── duecare-llm-tasks/
│   ├── duecare-llm-agents/
│   ├── duecare-llm-workflows/
│   ├── duecare-llm-publishing/
│   └── duecare-llm/             # meta, pulls in all above
├── pyproject.toml             # uv workspace root
└── ...
```

## Channel 3: Kaggle Notebooks

**Audience:** hackathon judges (one-click reproducibility), Kaggle
researchers.

Per-phase notebooks pinned in `kaggle/kernels/<phase>/<name>.ipynb`,
kept in sync via jupytext with their `.py` source-of-truth. Each
notebook starts with `!pip install` for only the Duecare packages it
needs, plus a few targeted extras:

```python
# phase1_exploration/phase1_exploration.ipynb
!pip install duecare-llm-core duecare-llm-models[transformers] \
             duecare-llm-tasks duecare-llm-domains
```

```python
# phase3_finetune/phase3_finetune.ipynb
!pip install duecare-llm-core duecare-llm-models[unsloth] \
             duecare-llm-agents duecare-llm-publishing[hf-hub]
```

**Submission notebook** is the only notebook that installs the meta
package:

```python
# submission/submission.ipynb
!pip install duecare-llm
```

## Synchronization rules

1. **Every PyPI release is tagged in git** (`v0.1.0`, `v0.1.1`, ...). A
   tag triggers a CI job that publishes all 7 packages with the same
   version.
2. **Kaggle notebooks pin specific PyPI versions** so reruns months
   later still work: `!pip install duecare-llm-core==0.1.0`.
3. **The model on HF Hub is tagged to match**: the Phase 3 weights
   live at `taylorsamarel/gemma-4-e4b-safetyjudge-v0.1.0`.
4. **The writeup links to all three channels.** GitHub for tech depth,
   PyPI for reusability, Kaggle notebook for reproducibility.

## Release cadence (through the hackathon)

- v0.1.0-alpha — end of Week 1 (Phase 1 baseline pipeline working)
- v0.1.0-beta — end of Week 2 (Phase 2 comparison complete)
- v0.1.0-rc — end of Week 3 (Phase 3 fine-tune + first model on HF Hub)
- **v0.1.0 — during Week 5 before submission (all three channels synced)**
- v0.1.1 and onward — post-hackathon, normal semver

## Why this maps to the rubric

- **Impact & Vision** (40): reusability via PyPI packages is how this
  tool reaches more than one NGO. The bigger the potential reach, the
  bigger the vision score.
- **Video Pitch & Storytelling** (30): "`pip install duecare-llm` and
  run it on your laptop" is a single line of voiceover with visible
  payoff in the demo.
- **Technical Depth & Execution** (30): a clean multi-package split
  with namespace packages, typed protocols, auto-generated docs, and
  CI-verified tests is exactly the kind of engineering hygiene that
  signals "real, not faked for demo."
