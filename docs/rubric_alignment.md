# Rubric Alignment

Current as of 2026-05-17.

## Safety & Trust

DueCare targets migrant-worker exploitation risk with local Gemma 4 reasoning
wrapped in inspectable safety layers. The strongest evidence is the A-00 report
bundle: baseline, harnessed, optional fine-tuned, and final combined judging
outputs.

Active Kaggle path:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`
- `kaggle/A-00-omni-experiment-workbench/`

## Technical Depth

| Area | Current Evidence |
|---|---|
| Local Gemma 4 inference | Shared `Gemma4Runtime.load()` path. |
| Harnessing | Kernel 01 and A-00 use Persona + GREP + RAG/context + deterministic tools. |
| Fine-tuning | A-00 LoRA smoke path with checkpoint/resume and adapter save/load. |
| Evaluation | Combined rule + LLM judging. |
| Exports | HTML/Markdown/JSON reports, activity logs, charts, prompt/response rows, and evidence manifest. |

## Impact

The product story is privacy-first assistance for workers, NGOs, regulators,
and researchers. The harness makes model answers auditable by surfacing the
rules, context, and tools used before generation.

## Current Risks

- Long A-00 runs may hit Kaggle runtime limits; checkpoint/resume and artifact
  downloads mitigate this.
- Larger Gemma/frontier judges may score better but are optional, credentialed
  paths.
- Online grounding should remain opt-in behind anonymization and post-search
  verification.

## Active References

- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- [`readiness_dashboard.md`](readiness_dashboard.md)
- [`gemma4_feature_showcase.md`](gemma4_feature_showcase.md)
- [`harness_ecosystem.md`](harness_ecosystem.md)
