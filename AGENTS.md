# DueCare Agent Guide

This is the root orientation file for AI coding agents working in this
repository. More specific `AGENTS.md` files inside `packages/` may add local
constraints; closest file wins.

## Current Truth

- Active branch: `master`.
- Active Kaggle submission surfaces: `kaggle/01-duecare-exploration-workbench`,
  `kaggle/02-live-demo`, and `kaggle/A-00-omni-experiment-workbench`.
- Optional endpoint-comparison surface: `kaggle/03-universal-llm-benchmark`.
  It is for external API benchmarking with DueCare prompts and Claude Opus
  judging; it is not part of the primary recording path unless Taylor says so.
- Archived notebook-era surfaces under `kaggle/_archive/` are provenance, not
  blockers, unless Taylor explicitly asks to restore or migrate them.
- The public setup lanes are exactly six, in this order: Platform safety,
  NGO & regulator, Individual worker / mobile, Researcher, Anonymized
  knowledge sharing, Developer / integration partner.
- The workspace contains 17 `duecare-llm*` package directories. Run pytest
  collection before changing published test claims; do not claim a full test
  pass unless the full suite actually ran.
- Public files should have an obvious reason to exist. If you add a new
  top-level directory, Kaggle kernel, package surface, or long-lived document,
  update the relevant purpose map (`README.md`, `kaggle/_INDEX.md`,
  `docs/REPO_LAYOUT.md`, or `docs/FILE_PURPOSE_GUIDE.md`).

## Safety And Claims

- Never commit raw PII, real worker contact details, private case files, API
  keys, Kaggle tokens, or unredacted logs.
- Do not hardcode volatile hotlines, URLs, fee caps, wage rules, or office
  names into model outputs or training data unless they also exist as
  versioned knowledge objects.
- For public docs, prefer dated, reproducible statements: include the command
  or artifact behind a metric.
- Keep generated report leftovers out of commits unless the user explicitly
  asks to publish them.

## Workbench UI Rules

- Model loading is owned by the shared workbench chrome:
  `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html`,
  `_nav.js`, and `_chrome.css`.
- Do not add per-page model-loading popovers. Pages should call the universal
  `window.dcWbModelService` methods exposed by `_nav.js`.
- Bulk File Review, Knowledge Extraction, Search, and Anonymization & Sharing
  should expose visible progress, activity logs, replay/export artifacts, and a
  plain trust boundary.

## Validation Commands

Run the smallest relevant test scope, then the documentation/link audit for
public docs:

```bash
python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
```

For workbench UI changes, also run the affected chat package tests, for
example:

```bash
python -m pytest packages/duecare-llm-chat/tests/test_compare.py -q
```
