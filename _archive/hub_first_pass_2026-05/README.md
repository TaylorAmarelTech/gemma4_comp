# `_archive/hub_first_pass_2026-05/` — superseded duecare-ai.com hub scaffolds

> **Why this is archived, not deleted:** these were the first-pass
> scaffolds for the `duecare-ai.com` public hub. They were superseded
> by `apps/duecare-ai.com/` (the production hub Render deploys today),
> but the scaffolds contain useful design intent and reference
> implementations worth keeping for context.

## What's here

```
hub_first_pass_2026-05/
├── src_hub/                    ← was packages/.../src/hub/
│   ├── __init__.py
│   └── app.py                  ← initial FastAPI hub with anonymized
│                                  signal intake + OpenClaw/OpenCrawl
│                                  proposal endpoints + PII-rejection regex
├── deployment_render/          ← was deployment/render/
│   ├── Dockerfile              ← CPU-only Render image (CPU-only image
│   │                              build pattern, kept here as reference)
│   ├── README.md
│   ├── render.yaml             ← service: "duecare-llm-hub" (older name)
│   └── requirements.txt
└── test_hub_app.py             ← was tests/unit/test_hub_app.py
                                   ← imported `from src.hub.app import …`;
                                     would fail now that src.hub is moved
```

## What replaced it

The production hub lives at:

```
apps/duecare-ai.com/             ← production hub deployed to duecare-ai.com
├── app/                         ← FastAPI app code
├── Dockerfile                   ← Render builds this
├── tests/test_app.py            ← active test suite (do not run the
│                                  archived test_hub_app.py)
├── README.md
└── ...

render.yaml                      ← root-level config
                                   ← rootDir: apps/duecare-ai.com
                                   ← service: "duecare-ai-hub"
                                   ← branch: master, autoDeploy: true
```

The repo-root `render.yaml` is what Render actually uses. The
`render.yaml` inside `_archive/hub_first_pass_2026-05/deployment_render/`
is no longer referenced.

## What's retained from this scaffold (still useful design intent)

- **OpenClaw / OpenCrawl proposal pattern** — `app.py` here shows the
  shape of a proposal-ingestion endpoint (`POST /api/hub/opencrawl/updates`).
  The production hub adopts the same shape with the same
  human-in-the-loop boundary.
- **PII-rejection regex** — the email / phone / ID-pattern rejector
  in this scaffold's `detect_pii()` is conceptually correct; production
  may extend it but starts from the same baseline.
- **Anonymized-signal envelope** — the `SignalIngest` Pydantic model
  defined the canonical shape for partner submissions. Production
  inherits this contract.

## Why we are not deleting

1. **Reference implementation.** When future Sentinel work picks up,
   the proposal-validation regex + envelope shape are reusable.
2. **Audit trail.** Reviewers / partners may ask "what did the hub
   look like at v0.14.x?" — the archive is the answer.
3. **Cheap to keep.** ~25 KB, no maintenance burden, doesn't run, can't
   leak secrets (no env files, no credentials).

## Reactivation rules

If anyone tries to reactivate any code from this folder:

- Do **not** import `from src.hub` — that path is gone. Production
  is `from apps.duecare-ai.com.app import …` (or whatever the
  active package path is).
- Do **not** point Render at `_archive/hub_first_pass_2026-05/deployment_render/Dockerfile`
  — Render's autodeploy uses the repo-root `render.yaml` which points
  at `apps/duecare-ai.com/Dockerfile`.
- Do **not** run `pytest _archive/hub_first_pass_2026-05/test_hub_app.py`
  — its imports are stale and will fail.

## Date / version anchor

- **Archived:** 2026-05-08
- **chat-package version at archive time:** v0.14.7
- **Render branch / service at archive time:** `master` →
  `apps/duecare-ai.com/` → `duecare-ai-hub` → `https://duecare-ai.com`
