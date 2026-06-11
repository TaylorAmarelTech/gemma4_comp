# DueCare deployment paths

Four audience-specific implementation paths. Pick the one whose
audience description matches yours and skip to the linked brief.

> See also: [`docs/deployment_modes.md`](../deployment_modes.md) for
> the three **architectural** modes (Enterprise integration / Worker-
> side tool / Agency dashboard). The docs in this folder are
> **audience-first**; that one is **architecture-first**. They
> describe the same system from two angles.

## Pick your path

| Path | Audience | Surface | Trust boundary | Time-to-value |
|------|----------|---------|----------------|---------------|
| [Path 1](01_ngo_pilot_brief.md) | **Single NGO** — 5 to 50 caseworkers | Kernel 01 workbench on a laptop or shared workstation | All PII local; redacted envelopes optional | 1 day install + 1 week training |
| [Path 2](02_network_hub_bootstrap.md) | **NGO network** — 50 to 200+ member organisations | Anonymized knowledge hub + per-member Kernel 01 | Case PII stays at member NGO; only sanitized GREP/RAG/templates flow to the hub | 2 to 4 weeks bootstrap |
| [Path 3](03_government_workbench.md) | **Government office** — labour regulator, anti-trafficking unit, foreign-employment authority | Audit workbench (field path) or duecare-llm-server API (bulk path) | Government data stays in government infrastructure; local Gemma 4 only | 30 to 60 days workbench / 90 to 180 days API |
| [Path 4](04_platform_specialist_tier.md) | **Platform safety** — Meta, ByteDance, Reddit, Discord, Snap, classifieds boards | Specialist tier behind primary classifier; Gemma 4 LoRA self-hosted by the platform | Platform keeps all user content; DueCare team ships model + rubric updates only | 30 to 60 day pilot / 6 to 12 months full integration |

## What every path shares

- **Gemma 4 E2B or E4B** as the inference model. E2B (~2B effective)
  fits 16 GB consumer hardware; E4B (~4B effective) needs ~24 GB or
  a small GPU but produces stronger results on hard scenarios.
- **The DueCare knowledge layer** — 439 GREP rules, 859 RAG documents
  (+ a separate 610-doc multidomain corpus), 36 templates, 37 personas,
  38 corridor fee caps, 36 NGO contact bundles, 16 ILO conventions,
  74,640 trafficking seed prompts. (Counts verified via
  `scripts/verify_knowledge_surfaces.py`.)
  Versioned and verifiable via
  `python scripts/verify_knowledge_surfaces.py`.
- **The harness ecosystem** — chat, process, extraction,
  anonymization, search-safety, post-search-verification. Each
  harness is a self-contained module (see
  `.claude/rules/80_active_surface.md` for the contract).
- **Reproducibility floor** — every claim in a generated report cites
  back to a versioned knowledge object. No black-box outputs.

## What every path treats differently

| Concern | Path 1 (NGO) | Path 2 (Network) | Path 3 (Government) | Path 4 (Platform) |
|---------|--------------|------------------|---------------------|-------------------|
| Hardware | One laptop, 16 GB RAM | One laptop per member | Tablet/laptop per inspector OR internal server for API | Cluster with GPU specialist tier behind primary classifier |
| Operator | Caseworker | Each member NGO + 1 coordinator | Investigator + IT staff | Trust & Safety engineers |
| Data ingress | Case files, chat screenshots, contracts | Knowledge envelope submissions from members | Job ads, recruitment contracts, complaint intake | All user-generated content via primary pipeline |
| Data egress | Optional sanitized envelopes only | Curated knowledge pack to member NGOs | Audit reports, enforcement decisions | Enrichment metadata to primary moderation queue |
| Update cadence | Manual `pip install` upgrade quarterly | Sync from hub weekly | Quarterly rubric refresh per agency review | Continuous, governed by joint review board |
| Cost model | Free OSS / staff time | Shared hub hosting + curator role | Procurement + self-host | Their compute + license/support if commercialised |

## Path priority for the next 30 days

1. **Path 1** is the highest-confidence delivery. The workbench
   already exists. Two named-NGO pilots before submission turn the
   project from "interesting hackathon entry" into "two real
   organisations using it."
2. **Path 4** is the highest-impact pitch *in the video*. A 30 to 60
   second demo of "Facebook Marketplace job ad → DueCare flags fee-
   camouflage + ILO C181 violation → suggested enforcement action"
   is exactly the artifact the Impact & Vision rubric rewards.
3. **Paths 2 and 3** are post-hackathon multipliers. The
   infrastructure exists; the gating factor is partner
   relationships, which is bandwidth work that does not fit inside
   the submission window.

## Repository pointers

- `kaggle/01-duecare-exploration-workbench/` — Kernel 01 source for
  paths 1, 3
- `packages/duecare-llm-server/` — the FastAPI server package
  consumed by path 3 (API mode) and path 4
- `packages/duecare-llm-chat/` — workbench harnesses consumed by
  paths 1, 2, 3
- `packages/duecare-llm-publishing/` — HF Hub + Kaggle Dataset
  publishing for path 2 knowledge hub
- `scripts/verify_knowledge_surfaces.py` — knowledge layer
  verification used by all paths

## Implementation status

The deployment docs describe the **target** end-state. Some
referenced CLI subcommands and packages do not yet exist as
shipped code; they are tracked as follow-up work.

| Command / package | Status (as of 2026-05-22) | Tracking |
|---|---|---|
| `duecare init` / `doctor` / `demo` / `process` / `ingest` / `query` / `serve` / `moderate` / `worker` | Implemented | `packages/duecare-llm-cli/` |
| `duecare workbench` | Planned — alias for existing Kernel 01 FastAPI app launcher | Follow-up task |
| `duecare model pull <name>` | Planned — wraps existing Gemma 4 download path | Follow-up task |
| `duecare knowledge sync` / `export` / `search` | Planned — knowledge-pack publishing + sync wire-up | Follow-up task #118-related |
| `duecare anonymise envelope` | Planned — anonymisation gate CLI surface | Follow-up task |
| `duecare oracle subscribers` / `send-questions` | Planned — `packages/duecare-llm-oracle/` package not yet built | Follow-up task #124 |
| `packages/duecare-llm-oracle/` | Planned | Follow-up task #124 |

The reference architecture, schemas, trust boundaries, and
workflows in these docs are stable. The CLI surface is the
remaining gap; existing functionality is reachable through the
Kernel 01 FastAPI workbench while the CLI catches up.

## Cross-cutting components

- [**Email oracle**](oracle_email_solicitation.md) — server-side
  agent that proactively solicits knowledge contributions from
  civil society stakeholders by email. Civil society won't learn
  another login; the oracle inverts the model so stakeholders just
  reply when they have time. Powers paths 2 and 3.

## Questions to ask before picking a path

1. **Whose data is it?** If the answer is "the worker's", path 1.
   If "the platform's users", path 4. If "the government's
   regulated entities", path 3.
2. **Where does the data live after analysis?** If it must never
   leave a single organisation, path 1 or 3. If sanitized
   intelligence should travel, path 2. If platform-scale,
   path 4.
3. **What is the operator's existing tooling?** If a case-
   management system, path 1 + integration. If a regulatory
   intake system, path 3. If a Trust & Safety pipeline, path 4.
4. **What is the time horizon?** Days, path 1. Weeks, path 2.
   Months, path 3 or 4.
