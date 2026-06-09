# DueCare network federation — design + current state

> How independent DueCare nodes (Kaggle kernels, NGO laptops, on-prem
> deployments) share anonymized knowledge through one or more hubs.
> Implemented pieces are marked **live**; the rest is the roadmap.
> Code: `packages/duecare-llm-chat/src/duecare/chat/federation.py` (peer
> registry), `knowledge_taxonomy.py` (envelope contract), the hub app at
> `apps/duecare-ai.com/app/main.py`.

## The shape of the network

Hub-and-spoke, pull-first, human-curated:

```
 NGO node A (kernel)            NGO node B (laptop)         Researcher node C
   | anonymize -> submit          | anonymize -> submit       | sync (pull)
   v                              v                           v
            duecare-ai.com hub  (or any registered peer hub)
            schema gate -> PII re-gate -> dedup -> curator queue
                          -> vetted packs -> served to every node
```

Raw case files never federate. The only thing that crosses a node
boundary is a **KnowledgeObject v1.0 envelope** that already passed the
local anonymization gate, and the hub re-runs its own PII gate before
even queueing it for human curation. The hub stores submission metadata
plus content hashes for audit; distribution to other nodes happens
through curator-managed packs, never automatic re-broadcast.

## The envelope contract (live)

* One schema artifact, served identically by every node:
  `GET /static/envelope_schema.json` (kernel + hub) and live at
  `GET /api/knowledge/schema`. Generated from `KO_TYPE_CATALOG` by
  `scripts/build_envelope_schema.py`; drift fails
  `tests/test_envelope_schema_sync.py`.
* Per-type required content keys are **binding** at every entry point:
  kernel promote/import/sync and hub submit.
* Integrity: `provenance.content_sha256` = sha256 over sorted-key compact
  JSON of `content`, stamped at kernel promote time and at hub serve
  time. Any recipient can recompute it to detect tampering in transit.
* Identity: `provenance.created_by` carries the originating node id
  (`DUECARE_NODE_ID`, default `kernel-01`); the submit path also sends it
  as `X-DueCare-Source`.

## The peer registry (live)

`duecare.chat.federation` is the single source of truth for which remote
peers a node may contact:

* Built-in peers: `duecare-ai.com`, `www.duecare-ai.com`,
  `gemma4-comp.onrender.com` (the public hub + aliases).
* `DUECARE_PEERS="ngo-manila=https://manila.example.org,..."` adds peers
  at kernel start. https-only; http entries are dropped.
* The registry doubles as the **outbound allowlist** for
  `POST /api/knowledge/sync` and `POST /api/submit/knowledge` — kernels
  run behind unauthenticated tunnels, so every visitor-influenced
  outbound URL is checked (https, no userinfo, registered host) before a
  socket opens.
* Discovery: `GET /api/network/peers` returns the node id, the registry,
  and the sync contract.

## The flows

| Flow | Endpoint | State |
|---|---|---|
| Pull vetted packs | `GET <peer>/api/hub/knowledge/download?vetted=true` -> ZIP of `<type>/<id>.json` | live |
| Delta sync | `GET <peer>/api/hub/sync?since=<ISO-8601>` -> changed vetted packs (cursor in response) | live |
| Push anonymized envelopes | `POST <peer>/api/submit/knowledge` | live |
| Hub-side gates | schema-version + type + kebab id + required content keys + PII regex re-gate + duplicate `(type, id, content_sha256)` acknowledgement | live |
| Curation | `GET /api/curator/queue` + `POST /api/curator/decide/...` (admin-gated, metadata + hashes only) | live |
| Node identity | `DUECARE_NODE_ID` -> provenance + `X-DueCare-Source` | live |

## Privacy invariants

1. The hub persists **no raw submitted content** — submissions leave an
   audit row of `{type, id, content_sha256}` lists; curation decisions
   reference hashes.
2. Both sides run PII gates: the kernel anonymizes before submit; the hub
   re-runs its own regex gate and hard-rejects on any hit.
3. Distribution is curator-mediated. Nothing a node submits reaches
   another node without a human accept decision.

## Roadmap (not yet implemented)

* **Signing**: HMAC or keypair per node so the hub can verify
  `X-DueCare-Source` instead of trusting it. Today the node id is
  self-declared; curation is the trust boundary.
* **Retraction**: `UpdateStatus.retracted` exists in the hub model; a
  tombstone endpoint + client-side delete-on-sync is the missing half.
* **Hub-to-node push**: all sync is pull-only; a webhook/subscription
  channel would cut propagation latency for urgent advisories.
* **Cross-hub gossip**: hubs do not exchange packs with each other yet;
  multi-hub deployments are independent stars sharing the schema.

## Why this is domain-agnostic

Nothing in the envelope wrapper, the peer registry, or the gates assumes
anti-trafficking content. A wildlife-trafficking, elder-fraud, or
procurement-integrity network reuses the same contract with its own
domain pack (see `docs/domain_pack_framework.md`); the
`knowledge_object_type` taxonomy and the PII gates are the shared
substrate.
