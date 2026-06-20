# Acquisition pipeline — operator runbook

> How to grow the RAG corpus from public sources toward the 10k-doc goal.
> The pipeline is **propose-only**: it stages candidates for review and never
> mutates the live corpus. A human/curator imports the reviewed bundle.
>
> **See also:** [`entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md) — the
> sibling entity / registry / graph layer (recruiter & employer verification against 32
> official government registries) that complements this RAG-corpus growth pipeline.

## What it does

```
harvest sitemaps ─▶ candidates ─▶ acquire (fetch→extract→chunk→dedup→scrub→graph)
                                        │
                                        ▼
                                  staged chunks + doc graph
                                        │
                                   promote (cap per-doc)
                                        ▼
                          importable knowledge bundle (.zip)
                                        │
                              curator review → /api/knowledge/import
```

All stages are deterministic and offline-testable (network fetch is injected).
Modules live in `duecare-llm-research-tools`; runners in `scripts/`.

| Stage | Module | Runner |
|---|---|---|
| Frontier expansion | `sitemap.py` | `scripts/harvest_sitemaps.py` |
| Crawl politeness (robots + rate limit) | `politeness.py` | — |
| Fetch + PDF/HTML extract | `docfetch.py` | — |
| Chunk | `chunker.py` | — |
| Dedup (exact + LSH SimHash) | `dedup.py` | — |
| Persistent store (dedup index + FTS5 + crawl ledger + graph) | `store.py` | — |
| Entity/co-mention graph | `graph.py` | — |
| Orchestrate + stage | `acquire.py` | `scripts/run_acquisition.py` |
| Promote to bundle | `promote.py` | `scripts/promote_acquisition.py` |

## Run it

The recovery-env Python is required (see `docs/local_test_env.md`). Set
`PYTHONPATH` to every package `src`, e.g. (bash):

```bash
py="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"
export PYTHONPATH=$(ls -d packages/*/src | tr '\n' ';')
```

**1. Harvest the frontier** (sitemap/robots seeds → candidate URLs):

```bash
HARVEST_TOTAL=4000 HARVEST_PER_SEED=60 "$py" scripts/harvest_sitemaps.py
# -> reports/acquisition/harvested_candidates.jsonl  (small / JSONL)
```

**1b. Million-scale frontier** (deep, resumable, streaming walk into a SQLite
queue — for hundreds-of-thousands to millions of URLs):

```bash
HARVEST_DB=reports/acquisition/frontier.db HARVEST_MAX=2000000 \
HARVEST_MAX_FETCHES=50000 HARVEST_DEPTH=8 "$py" scripts/harvest_frontier.py
# -> frontier.db table `frontier` (status='pending'); resumable via the sitemaps ledger
```

Then acquire drains the frontier instead of a jsonl:

```bash
ACQ_FRONTIER_DB=reports/acquisition/frontier.db ACQ_OUT=reports/acquisition \
"$py" scripts/run_acquisition.py
# pulls pending -> acquires -> marks 'acquired' (resume-safe). Politeness rate-
# limits real fetches, so a huge frontier drains incrementally over many runs.
```

**2. Acquire** (fetch → stage chunks + graph). Resumable; skips URLs already in
the corpus, already staged, or in `done_urls.json`:

```bash
ACQ_CANDIDATES=reports/acquisition/harvested_candidates.jsonl \
ACQ_OUT=reports/acquisition "$py" scripts/run_acquisition.py
# -> reports/acquisition/{staged_chunks.jsonl, graph.json, manifest.json, ...}
```

(Default `ACQ_CANDIDATES` is the 308-URL spider frontier
`configs/duecare/benchmarks/research_spider/source_candidates.jsonl`.)

**3. Promote** (balanced, importable bundle):

```bash
ACQ_OUT=reports/acquisition PROMOTE_MAX_PER_DOC=120 "$py" scripts/promote_acquisition.py
# -> reports/acquisition/knowledge_bundle.zip  (+ knowledge_envelopes.jsonl, promote_summary.json)
```

**4. Import** (curator step — grows the live corpus): review
`knowledge_envelopes.jsonl`, then upload `knowledge_bundle.zip` via the
workbench Sync/Knowledge page (`/api/knowledge/import`). Entries are
`rag_doc` + `citation_edge` envelopes pathed `<type>/<id>.json`.

## Env knobs

| Var | Default | Meaning |
|---|---|---|
| `HARVEST_TOTAL` | 4000 | total candidate cap |
| `HARVEST_PER_SEED` | 80 | per-domain cap (balance) |
| `HARVEST_TIMEOUT` | 20 | per-fetch seconds |
| `ACQ_CANDIDATES` | spider frontier | input candidates `.jsonl` |
| `ACQ_OUT` | `reports/acquisition` | staging dir |
| `ACQ_LIMIT` | 0 (all) | max new candidates this run |
| `ACQ_BATCH` | 20 | candidates per progress tick |
| `ACQ_TIMEOUT` | 25 | per-fetch seconds |
| `ACQ_MIN_INTERVAL` | 1.0 | per-host seconds between requests (politeness) |
| `ACQ_RESPECT_ROBOTS` | 1 | honor robots.txt `Disallow` (0 to disable) |
| `PROMOTE_MAX_PER_DOC` | 120 | cap chunks per source page |

## Storage & scaling

`run_acquisition` opens a SQLite store at `ACQ_OUT/corpus.db` (stdlib, WAL) as
the **system of record**: chunks, a persisted **SimHash band index** (near-dup
dedup stays O(bucket) — never re-reads the whole corpus), a crawl ledger
(resume), the doc graph, and an **FTS5** full-text index. On first creation it
seeds the dedup baseline from the live RAG corpus and reconciles any prior
`staged_chunks.jsonl` (no re-fetch). JSONL remains the git-reviewable export +
import-bundle format.

The store backend is swappable: for the **multi-writer server deployment**
(NGO-network / government), point it at Postgres via
`duecare-llm-evidence-db[postgres]` — same method surface, no caller change.
SQLite is the right default for a single-box, single-curator corpus up to
~millions of rows.

Query the staged corpus (FTS5):

```python
from duecare.research_tools.store import AcquisitionStore
with AcquisitionStore("reports/acquisition/corpus.db") as s:
    print(s.stats())
    for hit in s.search("passport retention", limit=10):
        print(hit["chunk_id"], hit["snippet"])
```

## Safety invariants

- **Propose-only.** Nothing here writes to the live corpus or packs. Output is
  staged under `reports/acquisition/` (gitignored). Import is a deliberate
  human step.
- **PII scrub.** Extracted text has emails / phones / passport- and
  account-shaped tokens redacted (`acquire.scrub_text`). Volatile facts
  (numbers, contacts) carry a `verification_note` — use tools, don't memorize.
- **Public sources only.** No raw private case intake.
- **Dedup** against the live corpus (URL + sha256 + SimHash) and within a batch.

## Run 1 (2026-06-06)

308-URL frontier → 206 reachable docs → 26,608 staged chunks (1,827 deduped,
87 unreachable) → 6,683 balanced `rag_doc` envelopes (10.8 MB bundle), 0 PII
leaks. ~30 min.

## Known follow-ups

- Curator import of the bundle to actually grow the live retrievable corpus.
- Relevance scoring of harvested URLs before promotion.
- Scanned-PDF OCR (text-PDF extraction works; image-only PDFs need OCR).
- Scheduled worker + review dashboard (Component 5 production deliverables).
