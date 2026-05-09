# Bulk NGO case-file ingestion + local knowledge database

> **Status:** plan, not built. The wheel today supports single-message
> chat against pasted text. This document describes the next iteration:
> a deployment can drop in a ZIP of casework files, the local Gemma
> goes through them on its own schedule, builds a queryable local
> knowledge database, and only ever sends anonymized aggregates to the
> public hub when the operator clicks "share".

## Why this matters

Right now, NGO partners have casework files sitting on their machines
that nobody can search across, surface patterns from, or use to
strengthen the public corridor packs. The website's privacy story
already says "raw cases stay local; anonymized signals can opt out to
the hub" — but there's no actual ingestion pipeline behind that
promise. This is the pipeline.

## Hard constraints

These are non-negotiable; everything below the line obeys them.

1. **Nothing leaves the device until an operator explicitly clicks
   "share."** No autosync. No background uploads. The local KB is
   purely local.
2. **Local processing is opt-in or idle-only.** The operator picks
   between *foreground* ("process now, I'll wait") and *queued*
   ("process when the machine is idle"). No silent CPU spin.
3. **Anonymization is a hard gate before any share.** Even when the
   operator clicks share, the payload runs through the same anonymizer
   shown in `/static/anonymization-preview.html` — local GREP + regex
   redaction first, then the LLM safety pass, then a "preview what
   gets sent" confirmation, then send.
4. **Works outside Kaggle.** Kaggle's per-session VRAM and 12-hour
   limits make bulk processing impractical. This pipeline targets a
   self-hosted deployment (NGO laptop, on-prem GPU box, or a private
   Render service).

## Two ingestion modes

The pipeline has the same downstream shape regardless of how files
arrive. What differs is the source.

| Mode | Audience | Source | Trigger |
|---|---|---|---|
| **ZIP upload** | Demo, Kaggle, one-time batch | Drag-drop in `/static/local-ingest.html` | Operator picks the file |
| **Folder watch** | Real NGO deployment | A directory already on the operator's machine (e.g. `~/casework/`) | Operator picks the folder once; the runtime indexes it on demand or watches it |

The ZIP mode is the demo path: browser-friendly, works inside Kaggle,
shows the flow end-to-end. The folder mode is the production path:
caseworkers already have their files organized in folders, they don't
want to ZIP-and-upload thousands of files every time. The wheel's
FastAPI runtime can read directly from a configured directory because
it runs on the operator's machine.

**Folder mode** has two sub-modes:

1. **One-time scan.** Operator hits "Index this folder" and the runtime
   walks every file under the path once. New files added later are
   ignored until the operator re-scans.
2. **Continuous watch.** Same scan, plus the runtime registers a
   filesystem watcher (`watchdog` on Python, native `fsevents` on
   macOS, `inotify` on Linux). New or modified files get queued
   automatically — but they still go through the per-file processor
   the operator picked (foreground vs queued), so processing never
   silently happens during active chat use.

Both folder modes obey the same hard contract: the path is a runtime
config (`~/.duecare/config.toml`'s `local_kb.watch_paths`), nothing
in that config ever travels to the hub, and the operator can flip
the watcher off any time without affecting the indexed KB.

## Pipeline shape

```
Source: ZIP upload OR folder pick OR folder watch
  → unpack / enumerate to local staging
  → per-file dispatcher
        ├─ classifier (corridor / sector / case-type)
        ├─ entity extractor (employer, recruiter, jurisdiction, fees)
        ├─ relationship builder (entity → entity edges)
        └─ summary generator (one paragraph + tags)
  → write per-file record + relationships to local KB
        (SQLite + a small graph index; nothing fancy)
  → operator can search, browse, and visualize the local KB
  → "Share aggregates" button (optional, opt-in)
        → anonymizer (regex + LLM PII pass)
        → preview confirmation page
        → POST /api/hub/client/submission with kind="custom" or
          kind="grep" if the operator turned the pattern into a rule
```

## Data model (local KB)

Three tables in a local SQLite file at `~/.duecare/local-kb/cases.db`:

| Table | Columns | Purpose |
|---|---|---|
| `case` | `case_id`, `source_filename`, `ingested_at`, `corridor`, `sector`, `summary`, `summary_hash` | One row per ingested file |
| `entity` | `entity_id`, `case_id`, `kind` (employer/recruiter/worker_role/agency), `name_hash`, `attributes_json` | Extracted entities |
| `edge` | `edge_id`, `from_entity_id`, `to_entity_id`, `kind` (employed_by / placed_by / received_fee_from / similar_pattern), `case_id` | Relationships |

`name_hash` only — never the raw name. Operator can decrypt locally
because they have the salt; the hub can't even if they got the file.

## UI surfaces (in the wheel)

Five new viewer pages under `/static/`:

1. `/static/local-kb.html` — list of ingested files, filter by
   corridor / sector, click to open one
2. `/static/local-case.html?id=...` — single-case view: summary,
   entities, edges, "share anonymized" button
3. `/static/local-graph.html` — force-directed graph of entity
   relationships across the whole local KB
4. `/static/local-ingest.html` — two intake panes side-by-side: one
   for drag-drop ZIP (demo path), one for "Pick a folder" + "Watch
   for new files" (production NGO path). Both feed the same queue.
5. `/static/local-share.html` — preview what aggregates would ship
   and why (ties into `/static/anonymization-preview.html`)

These are wheel-only pages. The public hub's static pages stay focused
on coordination; bulk casework lives behind the privacy boundary on
the operator's own deployment.

## Server-side changes (none for the local KB itself)

The local KB is purely client-side. The hub only sees what the operator
explicitly chooses to share, which goes through the existing endpoints:

- `POST /api/hub/signals` — for aggregate counts ("36 cases this month
  matched the fee_excess pattern in PHL-KWT")
- `POST /api/hub/client/submission` — for proposed knowledge-pack
  diffs ("we observed a recurring recruiter pattern; here's a draft
  GREP rule")
- `POST /api/hub/client/submission/retract` — operator can pull a
  submission before it's vetted

No new server endpoints. The local KB is a *consumer* of the hub APIs,
not the other way around.

## What needs building (rough sizing)

| Piece | Estimated complexity | Notes |
|---|---|---|
| Local SQLite schema + migrations | Small | Stdlib `sqlite3` is enough |
| File-upload endpoint in wheel runtime | Small | New POST route on the chat package's FastAPI app, multipart upload (ZIP path) |
| Folder-scan endpoint in wheel runtime | Small | POST takes an absolute path, returns a job id; refuses paths outside an operator-configured allowlist for safety |
| Folder-watcher (continuous mode) | Small | `watchdog` library; one observer per configured path; the runtime keeps a small in-memory dedupe so a single edit doesn't enqueue twice |
| Per-file processor (classifier + entity extractor) | Medium | Calls local Gemma synchronously for foreground; a thread pool for queued |
| Relationship builder | Medium | Heuristic name-match across cases, entity-resolution |
| Local-KB browser pages (5 listed above) | Medium | Same chrome as the existing 11 viewer pages |
| Anonymization confirmation flow | Already shipped | `/static/anonymization-preview.html` covers the pattern |
| Tests | Small | Mock LLM, fixture ZIP with 3 composite case files |

Order of build: schema first, then upload endpoint, then foreground
processor, then UI, then queued processor + idle-time scheduler, then
share flow.

## Open questions

1. **Idle-time detection.** Browser visibilityState is the obvious
   signal for client-driven UIs; for an NGO running this on a laptop,
   "idle" might just mean "no chat request in the last N minutes."
   Pick a definition before building the queued path.
2. **Entity resolution across cases.** Same recruiter under different
   spellings is a real problem. Start with exact-match on the
   anonymized hash; defer fuzzy match.
3. **Local-KB encryption.** The SQLite file holds anonymized hashes,
   not raw names — but a stolen laptop is still a real risk. Default
   to OS-level disk encryption guidance; add a passphrase prompt as a
   second pass if operators ask.
4. **Deletion / right-to-erasure.** Operator must be able to wipe the
   local KB without uninstalling the wheel. Build a one-button
   "Forget everything" in `/static/local-kb.html`.

## Naming

In line with the website rule of dropping unowned product names: this
feature is called **"Local case knowledge base"** in user copy, and
**"local KB"** in shorthand. No project-name dependencies.
