# Duecare Exchange — privacy-preserving knowledge sharing

**Status: Hub scaffolded at [duecare-ai.com](https://duecare-ai.com); signed-pack distribution is roadmap.**
The web service that anchors Exchange is live in this repo at
[`apps/duecare-ai.com/`](../../apps/duecare-ai.com/) and deploys to
Render via the repo-root `render.yaml`. The signed-pack format and
multi-partner distribution layer are post-hackathon.

Today, the equivalent of Exchange runs through:

1. **Curator-block PRs** into `harness/_*.json` files reviewed by humans.
2. **Hub signal intake** at `POST /api/hub/signals` (anonymized
   pattern signals, raw-PII rejector in front, JSONL persistence on
   Render disk) and `GET /api/hub/knowledge-packs` (knowledge-pack
   metadata listing).

Exchange formalizes the curator-block + hub-intake pair into a
partner-pluggable, versioned, signed distribution layer.

## Why it exists

Without Exchange, each Duecare deployment is a static snapshot. Laws
change. NGOs publish new advisories. Recruiter scams evolve.
Continuously updating becomes dangerous if it becomes centralized
surveillance — Exchange is designed to make updates safe to share
and safe to consume.

> **Local cases create anonymized signals; public / verified sources
> create shared knowledge.**

## Shared object types

| Shared object | Example |
|---|---|
| `RagDocumentProposal` | New regulation, labor advisory, court case, NGO report |
| `GrepRuleProposal` | New coded recruitment-scam phrase or pattern |
| `RubricDimensionProposal` | New scoring criterion (e.g. contract substitution) |
| `ContactUpdateProposal` | Updated regulator hotline / complaint form |
| `AnonymizedCaseSignal` | "3 cases this month mention passport deposit + TikTok recruiter" |
| `EvaluationResult` | Model X failed 17 / 50 domestic-worker fee-manipulation prompts |
| `CorridorPatternUpdate` | New PH → Gulf recruitment pattern |
| `PolicyChangeNotice` | New law / regulation affects scoring |

## Privacy default

Exchange does **not** collect raw case data. The flow:

```text
raw case
  ↓ local anonymizer
redacted signal / aggregate pattern / hashed provenance
  ↓ explicit partner opt-in
Duecare Exchange
  ↓ human + automated validation
signed knowledge pack
  ↓ pulled by clients
local harness update
```

## Sharing-protocol invariants

- No raw PII.
- No raw worker chats by default.
- All submissions have provenance.
- Every update has contributor type + review status.
- Every published pack is versioned and signed.
- Clients can pin versions.
- Sensitive cases stay local unless explicitly consented and anonymized.

## Pack format (planned)

Each signed pack is a tar/zip with:

```
duecare-pack-<name>-<version>.tar.gz
├─ manifest.json        # name, version, schema, contributors, signatures
├─ provenance.json      # source URLs, review log, automated-check results
├─ rules/<id>.json      # GrepRuleProposal entries
├─ rag/<id>.json        # RagDocumentProposal entries
├─ contacts/<id>.json   # ContactUpdateProposal entries
├─ rubrics/<id>.json    # RubricDimensionProposal entries
├─ evals/<id>.json      # EvaluationResult records
└─ signature.sig        # Sigstore / cosign signature over manifest + content
```

Clients verify the signature against a published key before applying
the pack to their local Harness.

## Tiered access

| Actor | Submit | Approve | Publish |
|---|---:|---:|---:|
| Individual migrant worker | optional anonymized feedback | no | no |
| NGO partner | yes | maybe (own jurisdiction) | no / global limited |
| Government / regulator | yes | maybe (official contacts/laws) | no / global limited |
| Researcher | yes | benchmark / RAG proposals | no / global limited |
| Maintainer | yes | yes | yes |

## Today's bridge

Until signed-pack distribution ships, the same workflow is
approximated by two layers:

**Repo-side (chat package, runs on Kaggle / local / edge):**

- **Curator-block JSONs** in `harness/_*.json` — 13 versioned files
  with `schema`, `version`, `last_updated`, `curator`, `entries[]`
  envelopes. Stakeholders submit single-file PRs.
- **`scripts/validate_curator_blocks.py`** — schema validation gate.
- **`scripts/v141_validate_contacts.py`** — pings web URLs in
  `_contacts.json` (read-only, doesn't email or call).
- **`/api/governance` + `/api/governance/<name>`** — exposes the
  full provenance tuple to any consumer.

**Hub-side (`apps/duecare-ai.com/`, deploys to duecare-ai.com):**

- **`POST /api/hub/signals`** — anonymized pattern-signal intake
  with raw-PII rejector. Signals persist as JSONL on a Render disk.
- **`GET /api/hub/knowledge-packs`** — knowledge-pack metadata
  endpoint listing RAG / GREP / contacts / rubrics / examples /
  tools / jurisdictions packs available to consumers.
- **`GET /api/hub/trends`** — aggregate trend counters (raw cases
  never leave the originating deployment).
- **`GET /api/hub/status`** — service status, privacy mode,
  counters.

The Exchange roadmap is to wrap these into a signed-pack format
(Sigstore / cosign over the manifest + content tree) with a
partner-discoverable index hosted at `duecare-ai.com`.
