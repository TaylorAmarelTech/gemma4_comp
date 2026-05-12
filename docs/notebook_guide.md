# DueCare Kernel Guide

[`kaggle/_INDEX.md`](../kaggle/_INDEX.md) is the authoritative active-kernel inventory. This guide is the human-readable purpose map and review queue generated from the same metadata plus `scripts/kaggle_live_slug_map.json` for public live status.

## Notebook Artifact Policy

Do not create `.ipynb` notebooks for the judge-facing submission by default. Treat `kernel.py` plus the folder README as the source of truth. Historical notebook wrappers have been archived under `_archive/kaggle-notebook-previews-2026-05-11/`; do not recreate them in active `kaggle/*/` folders unless Taylor explicitly asks for recovery work.

Every judge-facing Kaggle bundle must make its own bootstrap path explicit: print required Kaggle settings, fail fast on missing GPU/secrets/datasets/model sources, install DueCare from attached Kaggle wheels first, then pinned PyPI, then immutable GitHub release assets or commit-pinned archives only as a fallback, and print the resolved DueCare version before loading Gemma 4. Never rely on `_reference/`, local `.venv`, root-level legacy mirrors, untracked files, or a moving GitHub branch such as `main`.

## Review order

- Active script kernels: **13**
- Public-live Kaggle kernels in `kaggle_live_slug_map.json`: **4**
- Pending-publication kernels: **9**

| Priority | Kernels / modules | Why review in depth |
|---|---|---|
| P0 | 000 / 005 / 010 / 600 / 610 | Judge path: index, glossary, quickstart, proof dashboard, and capstone walkthrough. |
| P0 | 520 / 525 / 527 / 530 / 540 | Fine-tuning proof: curriculum, graded data, rubrics, Unsloth training, and delta visualization. |
| P1 | 150 / 152 / 155 / 160 / 180 / 190 | Visible Gemma 4 features: chat, tool calling, multimodal document analysis, and retrieval inspection. |
| P1 | 200-270 / 300-460 / 500-550 | Technical depth: cross-domain proof, model comparisons, adversarial testing, judge grading, and agent swarm. |
| P1 | 620 / 650 / 660 / 670 / 680 / 690 / 695 | Implementation surfaces: API tour, custom-domain adoption, and deployment-application narratives. |
| P2 | Tracked drafts and skunkworks | Keep structurally valid and documented; publish only if they strengthen the video story. |

## Kernel Purpose Map

| ID | Title | Status | Kaggle URL | Purpose |
|---|---|---|---|---|
| `010` | 010: DueCare Quickstart in 5 Minutes | Live | [https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes](https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes) | Install DueCare and run the smallest end-to-end safety smoke test. |
| `200` | 200: DueCare Cross-Domain Proof | Live | [https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof](https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof) | Show the same harness working across trafficking, tax evasion, and financial crime. |
| `500` | 500: DueCare 12-Agent Gemma 4 Safety Swarm | Live | [https://www.kaggle.com/code/taylorsamarel/duecare-500-agent-swarm-deep-dive](https://www.kaggle.com/code/taylorsamarel/duecare-500-agent-swarm-deep-dive) | Walk through the 12-agent Gemma 4 safety swarm orchestration. |
| `610` | 610: DueCare Submission Walkthrough | Archived live mirror | [https://www.kaggle.com/code/taylorsamarel/610-duecare-submission-walkthrough](https://www.kaggle.com/code/taylorsamarel/610-duecare-submission-walkthrough) | Historical capstone mirror that stitched the four public kernel surfaces and five deployment shapes together. |
| `660` | 660: DueCare Enterprise Moderation | Archived draft mirror | Pending publication | Plain-English deployment mirror for screening risky recruitment posts, ads, and recruiter outreach at queue scale. |
| `670` | 670: DueCare Private Client-Side Checker | Archived draft mirror | Pending publication | Plain-English individual worker / mobile mirror that evaluates one suspicious message or document at a time. |
| `680` | 680: DueCare NGO API Triage | Archived draft mirror | Pending publication | Plain-English deployment mirror for the software-to-software NGO triage API story. |
| `690` | 690: DueCare Migration Case Workflow | Archived draft mirror | Pending publication | Plain-English deployment mirror for the multi-document case-bundle workflow with timelines, grounded findings, and draft complaint materials. |
| `695` | 695: DueCare Custom Domain Adoption | Archived draft mirror | Pending publication | Plain-English deployment mirror for partner adoption into a new safety domain without Python changes. |

## Module deep-review queue

1. **Public hub IA and forms** — `apps/duecare-ai.com/app/main.py`, templates, pack filters, contribute flow, admin logs, and Render notes.
2. **Wheel chat/runtime** — `packages/duecare-llm-chat/src/duecare/chat/app.py`, static viewers, classifier, harness data, and Cloudflare notebook launchers.
3. **Fine-tuning data spine** — active A-06/A-07/A-11 kernels plus archived 520/525/527/530/540 mirrors, `data/training*`, Unsloth settings, SFT/DPO wording, and artifact provenance.
4. **Archived notebook builders and presentation gates** — `scripts/build_notebook_*.py`, `scripts/_notebook_display.py`, no lossy previews, Kaggle-safe HTML, and generated metadata.
5. **Publishing and package split** — `packages/duecare-llm-*`, wheel metadata, Kaggle wheel datasets, README/package version consistency.
6. **Demo surfaces** — `src/demo`, Cloudflare A-series kernels, archived deployment mirrors 660-695, cached demo examples, and no-wait recording flow.
7. **Safety/privacy gates** — PII detectors, local-KB storage, anonymization previews, admin redaction, and public copy claims.

Generated by `python scripts/generate_notebook_guide.py`.
