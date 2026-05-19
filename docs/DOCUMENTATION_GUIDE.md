# Documentation Guide

Use this guide when editing README, GitHub metadata, Kaggle READMEs, package
READMEs, and Claude/Codex handoff files.

## Canonical Public Facts

Keep these facts consistent across public-facing docs:

| Topic | Canonical wording |
|---|---|
| Project | DueCare: a Gemma 4 safety ecosystem for migrant-worker protection |
| Public hub | `https://duecare-ai.com` |
| Active Kaggle path | `01-duecare-exploration-workbench`, `02-live-demo`, `A-00-omni-experiment-workbench` |
| Optional benchmark kernels | `03-universal-llm-benchmark` for arbitrary endpoint comparisons; `04-kaggle-community-benchmark` for Kaggle Community Benchmark tasks and model-proxy quota |
| Six lanes | Platform safety; NGO & regulator; Individual worker / mobile; Researcher; Anonymized knowledge sharing; Developer / integration partner |
| Package shape | 17 `duecare-llm*` package directories in the workspace |
| Current local collection | 675 package tests collected on 2026-05-19 |
| Headline smoke matrix | 2026-05-18: stock 2B 29.5%, stock+harness 35.6%, fine-tuned 26.4%, fine-tuned+harness 41.2% |

Do not describe A-01 through A-24 or `03-duecare-video-pitch` as the active
submission path. They are archived reference material.

## Claims Policy

- Use exact dates for metrics and smoke runs.
- Do not say tests "pass" unless the exact full command was run in this pass.
  If only collection was verified, say "collected."
- Do not paste live worker PII, real private case facts, or unversioned
  hotline/contact details into docs.
- For legal and policy claims, link to the artifact or source doc that supports
  the statement.
- Prefer readable link text over raw file paths in public tables.
- New durable files need a clear purpose paragraph or an entry in the nearest
  purpose map. Root-level files also need a reason in `ROOT_FILES.md`; see
  `docs/FILE_PURPOSE_GUIDE.md`.
- Generated package metadata files may contain `STATUS.md` TODO sections by
  design. Treat those as module completion notes, not public placeholder copy.

## Link And Surface Hygiene

Before committing public documentation changes, run:

```bash
python scripts/validate_public_surface.py
```

This checks route drift, six-lane order, Kaggle labels, v1 bundle envelope
markers, manifest checksums, and repo-local links.

For outbound links, list or probe external URLs with:

```bash
python scripts/check_external_links.py --list
python scripts/check_external_links.py --check --timeout 8 --max 100
```

For recording or UI-polish claims, use `docs/SCREENSHOT_AUDIT.md` to track the
required desktop, tablet, and mobile screenshots.

For changed package claims, also run:

```bash
python -m pytest packages --collect-only -q
```

## Workbench Documentation

When documenting the Kaggle workbench, keep these boundaries explicit:

- Model loading is shared, not per-page.
- Raw case files stay in the Kaggle kernel until the user exports or submits.
- Bulk File Review deterministic passes are separate from optional Gemma
  review passes.
- Knowledge Extraction drafts suggestions only; promotion is reviewer gated.
- Anonymization & Sharing is the consent and redaction gate before hub upload.
