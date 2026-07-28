# CLAUDE.md - DueCare project context

> Claude Code project index. Root and package `AGENTS.md` files control local
> work. The durable closeout truth is
> [`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md).

## Current operating brief (2026-07-28)

Read these before broad edits:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md)
3. [`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)
4. [`.claude/rules/05_project_bible_pickup.md`](.claude/rules/05_project_bible_pickup.md)
5. [`docs/MAINTAINER_HANDOFF.md`](docs/MAINTAINER_HANDOFF.md)
6. [`docs/PUBLICATION_READINESS.md`](docs/PUBLICATION_READINESS.md)
7. [`docs/CLOSEOUT_RESOLUTIONS_2026_07_28.md`](docs/CLOSEOUT_RESOLUTIONS_2026_07_28.md)
8. [`docs/DEFERRED_WORK.md`](docs/DEFERRED_WORK.md)
9. [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md) only when deep
   benchmark, dataset, or autonomous-engine history is needed.

Claude Code, Codex, Fable 5-style agents, and other pickup tools should use the
same read order and authority boundary. Root [`Plans.md`](Plans.md) is a
compatibility bridge for older Claude Code handoffs, not a planning source.

Saved `.claude/state/` files are historical evidence only. Establish current
truth from live Git, filesystem, process, validator, and hosting state before
making a completion claim.

## Current boundaries

- Active branch: `master`.
- Primary Kaggle source surfaces: `01-duecare-exploration-workbench`,
  `02-live-demo`, and `A-00-omni-experiment-workbench`.
- Optional benchmark surfaces: `03-universal-llm-benchmark` and
  `04-kaggle-community-benchmark`.
- Notebook-era material under `kaggle/_archive/` is provenance, not an active
  release blocker.
- Public setup lanes remain exactly: Platform safety; NGO & regulator;
  Individual worker / mobile; Researcher; Anonymized knowledge sharing;
  Developer / integration partner.
- The entity-intelligence pipeline is propose-only and curator-gated. Its
  34-registry acquisition cascade, 1,111-source licensed-entity catalog, and
  532 migrant-support organizations remain research inventory, not worker
  advice, the live GREP/RAG layer, or accepted training data.
- The default comparable benchmark board remains v1/h1 batched evidence.
  Per-dimension, v2, h2, and benign-control evidence is isolated.
- The dated closeout receipt resolves all 11 inherited items without inventing
  missing evidence. The generated deferred-work register has zero current items.
- No trained adapter, package release, or new model-improvement claim is
  completed merely because the core repository gate is green.

## Model and deployment posture

The whole model/flywheel stack is expected to remain cost-stopped. During
deterministic maintenance set:

```powershell
$env:DUECARE_MAX_PLANNED_MODEL_CALLS = '0'
```

Do not start Ollama, remove stop sentinels, resume recurring tasks, spend model
or Kaggle quota, or publish a model-backed result without explicit current
authorization, immutable model identifiers, reviewed pricing, finite
attempt/token/cash caps, and a stop condition.

The public services intentionally coexist:

- [duecare-ai.com](https://duecare-ai.com/) is the Render-hosted website and
  mutable hub API surface.
- [duecare-ai-site](https://tayloramareltech.github.io/duecare-ai-site/) is the
  independent backend-free read-only continuity copy; it does not own
  production DNS.
- [gemma4_comp Pages](https://tayloramareltech.github.io/gemma4_comp/) is the
  MkDocs documentation site.

Do not deploy the marketing/continuity build over the documentation Pages site.
Do not retire Render or change DNS as an incidental cleanup action.

## Current validation discipline

Never reuse a saved suite count as current evidence. Run the smallest relevant
scope, then widen in proportion to risk:

```powershell
python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python scripts/validate_main_kaggle_kernels.py
py -3.12 scripts/validate_kaggle_page_sources.py
python scripts/validate_publication_readiness.py --scope handoff
python scripts/validate_publication_readiness.py --scope core
```

For a current full-suite claim, run `python -m pytest packages tests -q` and
report exact passes, skips, warnings, platform, and revision. Validators in the
handoff and core scopes are model-free and do not authorize model execution.

## Workbench and data rules

- Shared workbench chrome owns model loading through `window.dcWbModelService`.
  Do not add per-page loaders.
- Bulk File Review runs deterministic extraction first. Bundle synthesis and
  `hierarchical_gemma_graph` are distinct passes; preserve hierarchy-level
  provenance in review and exports.
- Keep raw worker cases, private contact details, secrets, tokens, and
  unredacted logs out of Git and public artifacts.
- Do not hardcode volatile hotlines, URLs, fee caps, wage rules, or office names
  into model outputs or training rows unless they exist as versioned knowledge
  objects.
- Candidate and model-generated data remains labeled and quarantined until
  source, rights, privacy, lineage, leakage, diversity, and admission gates
  pass.
- Update generated artifacts from their source descriptor or generator; do not
  hand-edit around a failing source-of-truth check.

## Auto-loaded rules

| File | Topic |
|---|---|
| [00_overarching_goals.md](.claude/rules/00_overarching_goals.md) | Impact, story, and technical execution goals |
| [05_project_bible_pickup.md](.claude/rules/05_project_bible_pickup.md) | Tracked handoff and pause-safe pickup |
| [10_safety_gate.md](.claude/rules/10_safety_gate.md) | PII, secrets, and artifact safety |
| [20_code_style.md](.claude/rules/20_code_style.md) | Python and package conventions |
| [30_test_before_commit.md](.claude/rules/30_test_before_commit.md) | Validation before publication |
| [40_forge_module_contract.md](.claude/rules/40_forge_module_contract.md) | Module structure |
| [50_publish_strategy.md](.claude/rules/50_publish_strategy.md) | GitHub, package, and Kaggle publication boundaries |
| [60_notebook_presentation.md](.claude/rules/60_notebook_presentation.md) | Kaggle-safe notebook presentation |
| [70_workbench_ui_primitives.md](.claude/rules/70_workbench_ui_primitives.md) | Progress, logs, samples, and trust boundaries |
| [80_active_surface.md](.claude/rules/80_active_surface.md) | Active and optional public surfaces |
| [81_canonical_runtime.md](.claude/rules/81_canonical_runtime.md) | Runtime, harness, and model-loading contracts |
| [82_project_structure.md](.claude/rules/82_project_structure.md) | Layout and archive hygiene |
| [83_kaggle_workflow.md](.claude/rules/83_kaggle_workflow.md) | Manual-by-default Kaggle workflow |

## Durable references

- [`docs/CLAUDE_CODE_HANDOFF.md`](docs/CLAUDE_CODE_HANDOFF.md) - current Claude
  Code pickup, live surfaces, recent receipts, exact safe next work, and a
  copy-ready successor prompt.
- [`docs/MAINTAINER_HANDOFF.md`](docs/MAINTAINER_HANDOFF.md) - operations,
  recovery, access transfer, incidents, and human acceptance.
- [`docs/PROJECT_TRANSITION_PLAN.md`](docs/PROJECT_TRANSITION_PLAN.md) - dated
  closeout and maintenance-mode plan.
- [`docs/PROVIDER_BUDGETING.md`](docs/PROVIDER_BUDGETING.md) - exact covered
  transports and non-universal model-budget boundary.
- [`docs/training_and_finetuning.md`](docs/training_and_finetuning.md) - strict
  dataset and training workflow.
- [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md)
  - regenerated knowledge counts and verification commands.
- [`docs/entity_intelligence_pipeline.md`](docs/entity_intelligence_pipeline.md)
  - propose-only research and entity-verification boundary.

Future model comparisons should treat Kimi K3 and Meta Muse Spark 1.1 as
required lanes, subject to current identifier, access, capability, and pricing
verification. Unavailable access must be reported, not silently substituted.
