# Contribute knowledge to the central DueCare hub

DueCare is a hub-and-spoke network. A hub (the public one runs at
`https://duecare-ai.com`, or your own self-hosted `apps/duecare-ai.com`
instance) curates a shared library of **knowledge objects**: detection
rules, grounding documents, corridor fee profiles, NGO directories, ILO
citations, and so on. Any node -- a Kaggle kernel, an NGO laptop, a
partner service -- can:

- **pull** vetted knowledge packs from a hub, and
- **push** new anonymized knowledge back for a curator to review.

This folder is the smallest possible working example of the push side:
one synthetic envelope plus a script that validates it and POSTs it.

| File | What it is |
|---|---|
| `example_envelope.json` | One synthetic, schema-valid KnowledgeObject v1.0 envelope (a `grep_rule` red-flag detector). Composite content only -- no real people, cases, or organizations. |
| `submit_knowledge.py` | A dependency-light client: validate -> stamp provenance -> `POST /api/submit/knowledge` -> print the receipt. `--dry-run` validates and prints without sending. |

Nothing here adds server logic. It builds a request the existing hub
endpoint (`apps/duecare-ai.com` -> `POST /api/submit/knowledge`) already
accepts.

## The flow

```
  build an envelope            (example_envelope.json, or your own)
        |
        v
  validate locally             (against static/envelope_schema.json)
        |
        v
  stamp provenance             (created_at, created_by, content_sha256)
        |
        v
  POST /api/submit/knowledge   (to a hub in the peer allowlist)
        |
        v
  receipt                      (accepted / rejected_schema / rejected_pii / duplicates)
        |
        v
  curator review               (proposed -> vetted -> published as a pack)
```

## Quick start

Use the project Python (or any Python 3.11+). Validate the bundled
example without sending anything:

```bash
python submit_knowledge.py --dry-run
```

Expected: `OK item 0: grep_rule/grep-passport-retention-red-flag-example
(validated via jsonschema ...)` and the exact JSON body that would be
sent, then `dry run complete: 1 envelope(s) valid, nothing sent.`

Send it to the default public hub:

```bash
python submit_knowledge.py
```

Send your own envelope to your own hub:

```bash
DUECARE_HUB_URL=https://hub.example.org python submit_knowledge.py --envelope my_rule.json
```

### Environment variables (all optional)

| Variable | Default | Purpose |
|---|---|---|
| `DUECARE_HUB_URL` | `https://duecare-ai.com` | Base URL of the hub to submit to. |
| `DUECARE_SUBMIT_TOKEN` | (none) | Bearer token, if the hub requires one. |
| `DUECARE_NODE_ID` | `kernel-01` | Stamped into `provenance.created_by`. |
| `DUECARE_SCHEMA_PATH` | auto-discovered | Override the `envelope_schema.json` location. |

## The envelope contract

Every knowledge object is a **KnowledgeObject v1.0 envelope**. The
canonical schema is
`packages/duecare-llm-chat/src/duecare/chat/static/envelope_schema.json`
(served live at `<hub>/static/envelope_schema.json`). The wrapper is
fixed; the `content` keys depend on the type.

**Required wrapper fields (every type):**

| Field | Rule |
|---|---|
| `schema_version` | must be the string `"1.0"` |
| `knowledge_object_type` | one of the 28 enum types (`grep_rule`, `rag_doc`, `extracted_fact`, `corridor_profile`, `ngo_directory`, `citation_edge`, ...) |
| `id` | kebab-case: `^[a-z0-9][a-z0-9\-_]*$` |
| `content` | an object; the required keys inside depend on the type |

**Optional wrapper fields:** `version`, `tags`, `extensions`, and
`provenance` (`created_at`, `created_by`, `content_sha256`, `vetted`).

**Per-type `content` requirements** come from the schema `if/then`
clauses. A few examples:

| Type | Required `content` keys |
|---|---|
| `grep_rule` | `pattern` |
| `rag_doc` | `title`, `text` |
| `extracted_fact` | `fact_type` |
| `corridor_profile` | `corridor`, `label` |
| `ngo_directory` | `name`, `jurisdiction` |
| `citation_edge` | `from_statute`, `to_statute`, `relation` |

`provenance.content_sha256` is `sha256` over the sorted-key, compact JSON
of `content`. The client recomputes and stamps it on every run, so any
recipient can verify the content was not altered after it was hashed.

## What the hub does with your submission

The receiver (`POST /api/submit/knowledge`) runs the first stages of the
vetting pipeline before anything is trusted:

1. **Validate** each envelope shape and per-type required keys.
2. **PII hard gate (Stage 03):** a server-side regex re-scan rejects any
   item that still contains an email, phone number, ID number, or a
   titled person name -- even though items should already be anonymized.
3. **Deduplicate** on `(type, id, content_sha256)`: an identical
   resubmission is acknowledged, not re-queued.

Accepted items land as `status="proposed"`. A human curator reviews them
(Stage 04) and signs vetted releases (Stage 05) that other nodes can
then pull. Your submission is a **proposal**, not an instant publish.

The receipt tells you exactly what happened:

```json
{
  "ok": true,
  "submission_id": "hub_submit_2026-07-21T17-35-53Z",
  "n_items": 1,
  "n_accepted": 1,
  "n_rejected_schema": 0,
  "n_rejected_pii": 0,
  "n_duplicates": 0,
  "status": "proposed",
  "note": "Accepted 1 of 1 items into Stage 01 (Proposed) ..."
}
```

## The federation model

The peer registry (`packages/duecare-llm-chat/src/duecare/chat/federation.py`)
is the single outbound allowlist. It governs who a node may talk to:

- **https-only.** Non-https targets are refused; userinfo tricks in the
  URL are refused.
- **Allowlisted hosts only.** A node will only submit to (or pull from) a
  host that is a registered peer. The built-in peers are the public
  `duecare-ai.com` hub and its aliases.
- **Add a peer** by setting, before the node starts:

  ```bash
  export DUECARE_PEERS="my-hub=https://hub.example.org,partner=https://partner.example.net"
  ```

  The same registry backs sync, submit, and the `GET /api/network/peers`
  discovery endpoint, so one variable extends every flow at once.

- **Only public, pre-anonymized envelopes leave a node.** Raw worker
  chats, IDs, contact details, and private documents never cross this
  boundary. The client strips process-internal bookkeeping and the hub
  re-gates for PII regardless.

## Updating knowledge (versioning, never overwrite)

Knowledge is **append-only and versioned**. You do not edit a published
vetted object in place; you publish a newer version and let the curator
mark the prior one superseded.

1. Copy the envelope, keep a **stable `id`**, and bump `version`
   (`v1` -> `v2`). Because the hub deduplicates on
   `(type, id, content_sha256)`, changed content is a *new* proposal, not
   a duplicate -- it will be accepted for review.
2. Record the supersession relationship explicitly. Either:
   - add `extensions.superseded_by` / `extensions.supersedes` to point at
     the other version id, or
   - emit a `citation_edge` envelope whose `content.relation` is
     `supersedes` (a first-class relation in the taxonomy).
3. Resubmit with `submit_knowledge.py`. The curator publishes the new
   version and marks the old one superseded.
4. **Re-sync** on every node so the new version propagates. A node pulls
   with `POST /api/knowledge/sync` (which fetches the hub vetted pack)
   or directly from `GET <hub>/api/hub/knowledge/download?vetted=true`.
   Matching-knowledge rules (like `grep_rule`) go live for the *next*
   prompt after a sync; other branches re-digest on the next node boot.

## Safety

- Example and test content must be **composite/synthetic**. No real
  names, phone numbers, ID numbers, emails, addresses, or case numbers.
  See `.claude/rules/10_safety_gate.md`.
- The bundled `example_envelope.json` is deliberately synthetic and is
  designed to pass the hub PII gate. If you adapt it, keep it that way.

## Related

- Deployment guide (run a hub yourself): [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md)
- Envelope schema: `packages/duecare-llm-chat/src/duecare/chat/static/envelope_schema.json`
- Federation / peer allowlist: `packages/duecare-llm-chat/src/duecare/chat/federation.py`
- Safe-text / anonymization layer: [`docs/safe_text_layer.md`](../../docs/safe_text_layer.md)