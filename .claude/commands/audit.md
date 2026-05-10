---
description: Run the public-surface audit (drift, route 200s, lane order, Kaggle lane labels)
---

Run the public-surface audit and report the result.

## Steps

1. Run the audit:

```bash
.venv/Scripts/python.exe scripts/validate_public_surface.py
```

   On non-Windows machines without the project venv, fall back to whichever
   working python has the hub deps installed (FastAPI + Pydantic v2). The
   system pythons on this machine are broken; prefer the project venv.

2. If the audit exits 0:
   - Report "Public-surface audit clean: <N> checks, 0 findings."
   - Note any files skipped via `audit-allow-file:drift` (these are
     intentional opt-outs — list them so the user can review).

3. If the audit exits non-zero:
   - Group findings by check (`drift_terms`, `hub_routes_200`,
     `five_lane_order`, `kaggle_lane_labels`).
   - For each finding, recommend a fix using the `suggestion` field.
   - Decide per finding whether the right action is:
     - **Fix the surface** (preferred)
     - **Add an `audit-allow:drift` marker** (only when the term is
       intrinsic to the file's purpose — e.g. an env-var table
       documenting a literal third-party env var name, or a doc
       explaining the rename itself). See [`docs/AUDIT.md`](../../docs/AUDIT.md)
       for the convention.
   - Do not silently mark intentional bugs as allowed.

4. After making fixes, re-run the audit and confirm it returns 0
   findings before commit.

## Inputs to read

- [`docs/AUDIT.md`](../../docs/AUDIT.md) — convention + allowlist syntax
- [`scripts/validate_public_surface.py`](../../scripts/validate_public_surface.py) — the audit logic itself

## What not to do

- Do not skip a finding without an allowlist marker explaining why.
- Do not edit `_archive/`, `docs/adr/`, dated `CHECKPOINT_*`, or
  `_reference/` even if the audit reaches them — they're frozen.
  (The script already excludes these by default.)
- Do not run the audit against a worktree with uncommitted user
  changes you didn't intend to touch — `git status --short` first.
