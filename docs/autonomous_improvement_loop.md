# DueCare's autonomous improvement loop

> DueCare does not sit still between releases. It runs an automated loop that
> **collects** new public information, **solicits** field knowledge from opted-in
> experts, and **proposes** updates — while a human stays in the loop for every
> promotion. Nothing auto-merges into the live safety layer. The loop is
> autonomous in *collection and drafting*; **promotion is always human-gated.**

```
   ┌──────────── propose-only, human-gated promotion ────────────┐
   │                                                             │
Collect ──▶ Detect gaps ──▶ Solicit ──▶ Observe ──▶ Prioritise ──▶ Propose ──▶ (human) Promote
(scrape)    (what's stale)  (email)    (vet reply)  (rank)        (curator)
```

Why this matters: a local, on-device safety evaluator is only as good as the
corridor facts, fee caps, statutes, and recruiter records it knows. Those change
constantly. This loop keeps the knowledge fresh **without** centralising raw case
data and **without** letting unreviewed data reach the model.

---

## 1. Collect — automated scraping (propose-only)

A scheduled GitHub Actions workflow, **`.github/workflows/entity-harvest.yml`**,
runs every Monday (05:23 UTC) and on demand. It runs `scripts/harvest.py --all
--screen`, which fans out over the **acquisition cascade** — the 34 official
government registries (licensed-recruiter lists, fishing-vessel and money-lender
registers, sanctions / debarment lists, GLEIF + OpenOwnership corporate
ownership) plus the catalogued long tail — and the adverse-media screen.

- **Tiers of scraping.** Most sources are deterministic (a server-rendered table,
  a JSON API, a downloadable CSV/XLSX/PDF → a config `registry_spec`). JS-walled
  sites escalate to a real browser (`scripts/browser_scrape.py`, Playwright via
  system Edge), and the hardest sites escalate to a **Gemma 4 function-calling
  browser agent** (`scripts/agentic_browse.py`) — "Gemma proposes, code disposes"
  — which makes native function calling load-bearing, not decorative.
- **Propose-only.** Every collected record is staged to gitignored
  `reports/entity_kb/` (combined entity store + a unified `edges.jsonl` graph +
  manifest) and uploaded as a **workflow artifact** for a human to review. It
  never mutates the live GREP rules / RAG corpus or the demo.
- **Acquisition pipeline.** For narrative/document sources, the
  `duecare-llm-research-tools` pipeline (fetch → extract → chunk → dedup → scrub →
  graph → stage) likewise stages proposals to `reports/acquisition/`.

How to add a source: [`maintenance/entity_sources.md`](maintenance/entity_sources.md).
The full map: [`entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md).

## 2 & 3. Detect gaps + Solicit — the civil-society email oracle

The public hub does not only wait for submissions; it **actively asks** the
people best placed to answer. The oracle lives in
`apps/duecare-ai.com/app/outreach.py` and is visible at the **`/outreach`** page.

| Stage | Function | What happens |
|---|---|---|
| **Detect** | `detect_context_gaps()` | Surfaces field-answerable verification asks (a corridor fee cap, an emerging payment rail, a statute change), re-ranked as observations corroborate. |
| **Solicit** | `draft_campaign()` | Targets **opted-in** subscribers by topic/role and drafts a specific email. It **sends only if `DUECARE_SMTP_*` is configured, otherwise it honestly reports "drafted"** — never a fake "sent". |
| **Observe** | `ingest_observation()` | Vets each reply through the same **PII + intent gate** the rest of DueCare uses, then records a *weighted* context signal. |
| **Prioritise** | `prioritized_context()` | Ranks the gaps by corroboration and proposes a candidate **grading dimension**, so outreach feeds the rubric, not just retrieval. |

Routes: `GET/POST /api/outreach/{gaps,campaign,observe,priorities}`.

**Privacy boundary (load-bearing).** Subscribers opt in; their email address is
stored as **`sha256` only** (never plaintext). Replies pass the PII/intent gate
before anything is recorded. Civil society contributes by **replying to one
email** — never by learning a new login or UI. Detail:
[`deployment/oracle_email_solicitation.md`](deployment/oracle_email_solicitation.md)
and the [Information Sharing Architecture](information_sharing_architecture.md).

## 4. Propose → Promote — the human gate

Everything above produces **proposals**, never live changes:

- Scraped entities + edges → `reports/entity_kb/` artifacts.
- Solicited observations → weighted context signals + prioritised gaps.
- A **curator** (human) reviews and promotes; only then does a vetted pack update,
  a new corridor fact, or a candidate grading dimension enter the shared layer.

This is the safety-by-design heart of the loop: the model is improved by a
pipeline that is *autonomous in effort* but *conservative in authority*. It
mirrors DueCare's standing invariants — propose-only, no raw PII in git/logs/
artifacts, official/public sources only, on-device operation first-class.

## How the standards are kept honest

- **Counts are derived, not typed.** `scripts/entity_counts.py --write` regenerates
  the numbers the docs + `/source-verification` page quote;
  `tests/test_entity_count_drift.py` fails CI on drift.
- **CI runs the pipeline.** The `entity-pipeline` job (`.github/workflows/ci.yml`)
  runs the full entity suite on every PR.
- **Real, not faked.** The email oracle never claims a send it did not make; the
  scraper labels OCR/vision work it only queued; propose-only is enforced by
  staging to gitignored paths.

## See also

- [`outreach`](https://duecare-ai.com/outreach) — the live outreach page
- [Information Sharing Architecture](information_sharing_architecture.md)
- [Entity-intelligence pipeline](entity_intelligence_pipeline.md) · [Acquisition pipeline](acquisition_pipeline.md)
- [Contributing a data source](maintenance/entity_sources.md)
