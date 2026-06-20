# Maintenance guide — data sources & entity-verification registries

> Audience: the same stakeholders as the rest of `docs/maintenance/` — NGO
> partners, jurists, OSINT analysts, regulators, and developers who want to add
> an **official data source** (a licensed-recruiter register, a sanctions list, a
> beneficial-ownership feed, a support-org directory) so DueCare can verify the
> recruiters, employers, and owners behind a case. Most contributions here are
> **config, not code.**

## What this layer is (and what it is NOT)

The **entity-intelligence pipeline** is a *propose-only* verification layer:
`discover sources → scrape/resolve → normalise → entity_kb (dedup/merge) → query`.
It verifies the **entities** behind recruitment fraud against official public
records. Canonical map: [`../entity_intelligence_pipeline.md`](../entity_intelligence_pipeline.md);
exhaustive reference: [`../entity_intelligence_complete_reference.md`](../entity_intelligence_complete_reference.md).

Two hard boundaries make this safe to contribute to:

- **Propose-only.** Everything you add resolves into gitignored
  `reports/entity_kb/` for a human curator to review — it **never** mutates the
  live trafficking knowledge layer (GREP rules / RAG corpus) or the demo.
  Adding a source does not change any safety count.
- **Separate from the safety layer.** The entity layer is a *different corpus*
  from the trafficking GREP/RAG knowledge. A registry spec is not a safety rule.
- **Official / public sources only**, robots-respecting, **no embedded secrets,
  no mass-scraping.** Public-register *individual* names are allowed in the
  gitignored output; scripts embed no real names.

## Three ways to contribute (easiest first)

| # | You have… | You add… | Code? |
|---|---|---|---|
| 1 | A source URL + what it lists | a row in a **catalog YAML** (via a merge script) | none |
| 2 | A source whose page is a **server-rendered table / JSON API / downloadable file** | a **registry spec** (a YAML block) | none |
| 3 | A source behind a **JS-walled DataTables / unknown ajax endpoint** | a **deterministic resolver** (a small Python connector) | ~1 file |

The decision rule for #2 vs #3 (memorise this):
**server-rendered HTML table, a JSON API, or a downloadable CSV/XLSX/PDF →
build a config spec (#2). A DataTables grid with an unknown ajax endpoint, or a
SPA that needs a real browser → a resolver / browser tier (#3).**

---

## Level 1 — catalog a source (no resolver yet)

Two catalogs under `configs/duecare/research_monitor/`:

- `licensed_entity_sources.yaml` — official **entity** registers (recruiters,
  fishing vessels, money lenders, sanctions/debarment, corporate ownership).
- `migrant_support_orgs.yaml` — **protective** orgs (helplines, shelters,
  legal aid, migrant unions) used for referral.

**Do not hand-edit the YAML** — the dedup key is content-based and ids are
regenerated. Add your rows to a small input file and run the merge script,
which dedups, ensures unique ids, and ASCII-sanitises:

```bash
python scripts/merge_entity_sources.py   # entity registers
python scripts/merge_support_orgs.py      # support orgs
```

A catalog row is just metadata: `name`, `url`, `country`, `industry`/`type`,
`license` (the data licence), and a one-line `note`. That's enough for the
source to show up in the work-queue and be picked up later for a resolver.

---

## Level 2 — onboard a registry as a config spec (the common path)

This is the engine that lets the long tail of catalogued endpoints be onboarded
**as config instead of code**: `scripts/registry_spec.py` fetches a URL, parses
it with `scripts/registry_parsers.py`, and stamps canonical entity records — the
same shape the hand-written resolvers emit.

Add a block to `configs/duecare/research_monitor/registry_specs.yaml`:

```yaml
- id: ph_dmw_branches          # unique, snake_case
  url: https://example.gov/licensed-agencies
  format: html_table           # html_table | json | csv | xlsx | pdf
  entity_type: recruitment_agency
  jurisdiction: PH             # ISO-2 country
  fields:                      # canonical_field: source_column_or_json_key
    name: "Agency Name"
    license_no: "License No"
    address: "Office Address"
    status: "Status"
  row_filter: {field: license_no, pattern: "^RL"}   # optional — keep matching rows
  default_status: licensed                          # optional — when no status column
  note_fields: [validity]                           # optional — appended to notes
  source: "PH DMW — licensed recruitment agencies"
```

Format picker:

| `format` | Use when the source is… |
|---|---|
| `html_table` | a server-rendered `<table>` on the page |
| `json` | a JSON API (use `list_path` if the rows are nested) |
| `csv` | a downloadable CSV |
| `xlsx` | a downloadable Excel file (pure-stdlib reader, no openpyxl needed) |
| `pdf` | a tabular PDF (`row_regex` + `groups`, or `pdf_table` with `pdf_flavor`) |

**Test your spec** (no PR needed to try it):

```bash
python scripts/registry_spec.py --list                 # see all specs
python scripts/registry_spec.py --id ph_dmw_branches   # parse + preview rows
python scripts/acquisition_cascade.py --registry ph_dmw_branches   # run through the cascade
# bounded slices for big sources (e.g. GLEIF): --arg country=AE --arg limit=300
```

Your spec is automatically addressable as `--registry <id>` and is picked up by
the weekly `entity-harvest` workflow's `cascade` collector — no further wiring.

---

## Level 3 — a hand-written resolver (tricky sites)

When a site is JS-walled (DataTables with an unknown ajax endpoint, a SPA that
401s without a captured token), write a small connector under `scripts/` that
exposes `collect() -> list[record]` + `records_to_entities(...)`, then register
it in `scripts/acquisition_cascade.py` (`REGISTRY_RESOLVERS` + `PROVEN_REGISTRIES`).
The shipped resolvers (`bd_oep_agencies`, `hk_money_lenders`, `cn_mara_dwf`,
`au_afma_concessions`, …) are the templates. Split the bytes-decoder from the
row-interpreter so parsing is unit-testable offline with a fixture. For a real
browser, `scripts/browser_scrape.py` (Playwright, `channel="msedge"`) and the
Gemma-4 function-calling agent `scripts/agentic_browse.py` are the escalation tiers.

---

## Canonical output & interop (free, once you've added a source)

Resolved records flow through the shared pipeline automatically:

- **Dedup / link** — `scripts/entity_link.py` clusters the same entity across
  registries (RapidFuzz + splink on a shared identifier; GLEIF LEI is the key).
- **Relationship graph** — `scripts/entity_edges.py` unifies ownership /
  control / registration / same-as edges into one `edges.jsonl`.
- **Canonical schema** — emit **FollowTheMoney** EntityProxies (Aleph /
  OpenSanctions interoperable) with the `--ftm` flag on `gleif_lei`,
  `openownership_bods`, `dol_whd`, or `acquisition_cascade --registry <id> --ftm`.
- **Screening** — `scripts/entity_screen.py` + `scripts/adverse_media.py`.

## Counts stay honest automatically

Every count the docs and the public **`/source-verification`** page quote
(registries, catalogued sources, support orgs) is **derived**, never hand-typed.
After adding a source/registry, regenerate the source of truth:

```bash
python scripts/entity_counts.py --write    # -> app/static/entity_counts.json
```

`tests/test_entity_count_drift.py` fails CI if any doc/page literal drifts from
the live counts, so you cannot ship a stale number.

## Before you open a PR

```bash
# the entity suite (the CI 'entity-pipeline' job runs the same):
python -m pytest tests/test_registry_spec.py tests/test_acquisition_cascade.py \
                 tests/test_entity_count_drift.py -q
# public-surface audit (0 findings expected):
python scripts/validate_public_surface.py
```

CI's **`entity-pipeline`** job (in `.github/workflows/ci.yml`) installs the real
deps (rapidfuzz / splink / opencv) and runs the full entity test suite, plus
re-runs `entity_counts.py --write` and fails on drift.

## PR checklist

- [ ] Source is **official / public**, with the data licence noted in the row/spec
- [ ] No embedded secrets; no mass-scraping; robots respected
- [ ] Spec tested live (`registry_spec.py --id …` returns real rows) **or** the
      resolver has an offline fixture test
- [ ] `entity_counts.py --write` re-run; counts updated where surfaced
- [ ] One-paragraph PR body: the source, what it lists, and the licence

## References

- [`../entity_intelligence_pipeline.md`](../entity_intelligence_pipeline.md) — the canonical map
- [`../entity_intelligence_complete_reference.md`](../entity_intelligence_complete_reference.md) — every script, source, and tool
- [`../acquisition_pipeline.md`](../acquisition_pipeline.md) — the fetch→extract→chunk→stage acquisition path
- Live surface: the render app's `/source-verification` page (registry map + licence ledger)
