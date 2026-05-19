# Screenshot Audit

Purpose: track the visual evidence needed before recording or public review.
This is a checklist, not a generated artifact. Store screenshots outside git
unless Taylor explicitly selects a small set for documentation.

## Required Viewports

Use at least:

- Desktop: 1440 x 900
- Tablet: 1024 x 768
- Mobile: 390 x 844

## Workbench Screens

| Surface | Desktop | Tablet | Mobile | Notes |
|---|---:|---:|---:|---|
| Shared model selector | [ ] | [ ] | [ ] | One universal selector only; no duplicate page-local loader. |
| Chat | [ ] | [ ] | [ ] | Prompt, response, trace, score, and activity log visible. |
| Harness Comparison | [ ] | [ ] | [ ] | Both arms visible; model readiness comes from shared selector. |
| Bulk File Review | [ ] | [ ] | [ ] | Upload, progress, graph/rows, graph chat, replay/export controls. |
| Knowledge Extraction | [ ] | [ ] | [ ] | Source processing, draft progress, promoted envelopes, export path. |
| Search | [ ] | [ ] | [ ] | Sanitized query, backend status, result-to-knowledge handoff. |
| Anonymization & Sharing | [ ] | [ ] | [ ] | Redaction, consent checks, local privacy review, hub target. |
| Recording page | [ ] | [ ] | [ ] | Cached traces and recording checklist visible. |
| UI Audit page | [ ] | [ ] | [ ] | Manifest and route coverage readable. |

## Kaggle Optional Benchmarks

| Surface | Evidence Needed | Status |
|---|---|---|
| `03-universal-llm-benchmark` | Local UI or run output showing `results.json`, `calls.jsonl`, and `summary.md`. | [ ] |
| `04-kaggle-community-benchmark` | Kaggle task page plus `/kaggle/working/duecare-kbench/<run_id>/results.json`. | [ ] |

## Acceptance Checks

- Text fits inside controls and cards at each viewport.
- Activity logs show the current action and do not appear frozen.
- Long-running work shows phase, elapsed time, and fallback/queued status.
- Trust-boundary copy is visible on Bulk File Review, Knowledge Extraction,
  Search, and Anonymization & Sharing.
- Screenshots do not show raw PII, secrets, real private case facts, or local
  tokens.
- The model selector shows CUDA/GPU state clearly when local Gemma loading is
  attempted.
