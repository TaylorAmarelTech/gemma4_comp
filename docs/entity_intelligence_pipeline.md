# Entity-intelligence pipeline — canonical map

> The single index for DueCare's recruitment / entity-intelligence layer: the connectors,
> the registry catalog, the relationship graph, the screening + linkage engines, and the
> tooling behind them. Built in `scripts/` + `configs/` + `docs/research/`. This is operator
> research tooling that produces **proposed** knowledge for human review — it is **not** wired
> into the live demo or the model path. Every count below is reproducible from the source it
> cites (real-not-faked).
>
> **Sibling pipelines:** [`recruitment_pipeline.md`](recruitment_pipeline.md) (triage recruitment
> material: search→scrape→screen→verify→profile) and [`acquisition_pipeline.md`](acquisition_pipeline.md)
> (grow the RAG corpus from public sources). This doc covers the **entity / registry / graph**
> layer those two draw on.

## What it is

A pipeline that builds a knowledge base of the entities in the migration world —
recruitment / manning agencies, employers, brokers, lenders, debarred suppliers, forced-
labour-listed companies, beneficial owners, vessels — from **official public registries**,
then links and screens them. It answers: *is this recruiter licensed? has this employer
been debarred or cited for H-2A/MSPA violations? is this company on a forced-labour list?
who owns it?*

Two hard invariants:

- **Propose-only.** Every resolver/connector stages output to gitignored `reports/`
  (`reports/entity_kb/`, `reports/opensanctions_sources/`, `reports/acquisition/`). Nothing
  mutates the live trafficking knowledge layer (GREP rules / RAG corpus) or the demo. A human
  reviews and promotes.
- **Real-not-faked.** Field maps are authored against the *live* source response, never
  guessed; a source that blocks or returns no parseable data is skipped and logged, never
  fabricated. Public-register entity names are allowed (output gitignored); scripts embed no
  real names or secrets.

## Flow

```
 discover sources ──▶ resolve (fetch+parse) ──▶ normalize ──▶ link (LEI) ──▶ screen ──▶ propose
   catalogs            acquisition cascade        entity_kb     entity_link   entity_    reports/
   (1,111 + 532)       (34 registries)                          + cluster      screen
```

## Connectors (built this session)

All under `scripts/`, offline-tested (injectable fetch), sibling-loaded via importlib.

| Connector | Produces | Source | License | Tests |
|---|---|---|---|---|
| `gleif_lei.py` | legal entities (LEI = canonical id) | GLEIF LEI Records API | CC0 | 5 |
| `gleif_rr.py` | corporate **parent_of** edges | GLEIF Level-2 Relationship Records | CC0 | 5 |
| `openownership_bods.py` | beneficial owners + **owns_or_controls** edges | OpenOwnership BODS bulk | CC0 | 12 |
| `entity_link.py` | registry→GLEIF LEI links + clusters (splink) | — (linkage engine) | — | 11 |
| `cluster_registries.py` | cross-registry same-entity clusters | the cascade | — | 3 |
| `domain_intel.py` | domain→registrant/registrar + NS/MX edges | RDAP (whoisit) + DNS (dnspython) | — | 6 |
| `doj_press.py` | offense-tagged prosecution documents | DOJ press-releases JSON API | US public domain | 8 |
| `dol_whd.py` | employer-violation entities (H-2A/MSPA/child-labour) | DOL WHD Enforcement (v4 API) | US public domain | 5 |
| `harvest_opensanctions_sources.py` | 400 government-registry source pointers | OpenSanctions dataset metadata | MIT (metadata) | 10 |
| `opensanctions_to_specs.py` | draft resolver specs (verification queue) | the harvest | — | 8 |
| `tooling_scout.py` | ranked ADOPT/AVOID repo report | `gh search` | — | 10 |
| `image_enhance.py` | pre-OCR/vision image enhancement | OpenCV (ported from OpenSearch-VL) | — | 16 |

Plus the prior-session substrate: `entity_kb.py` (11-type entity KB, tier-merge dedup),
`entity_screen.py` (fuzzy SANCTIONED/FLAGGED/LICENSED/NOT_FOUND screen), `adverse_media.py`
(negative-news), `scrape_agency_sources.py`, `browser_scrape.py` (Playwright SPA),
`agentic_browse.py` (Gemma-4 function-calling browser agent), `acquisition_cascade.py`,
`registry_spec.py` + `registry_parsers.py` (the config-driven resolver), `harvest.py`.

## The acquisition cascade — 34 addressable registries

`scripts/acquisition_cascade.py` resolves each registry by id (`--registry <id>`):
**11 deterministic resolvers/presets** + **23 config specs** in
`configs/duecare/research_monitor/registry_specs.yaml`. A new registry is usually a YAML
block, not Python. **GLEIF** (`--registry gleif_lei`) and **OpenOwnership BODS**
(`--registry openownership_bods`) are also addressable as bounded slices via `--arg`
(e.g. `--arg country=AE --arg limit=300`). Verified per-registry counts (live, this session):

**Recruitment / labour (corridor):** PH DMW licensed agencies 3,788 · BD OEP/BMET 2,834 ·
BD MRA microfinance 904 · TW MOL manpower 3,377 · GB licensed sponsors 141,980 ·
CA TFWP positive-LMIA employers · HK EAA employment agencies.

**Forced-labour / debarment / sanctions:** US CBP Withhold Release Orders 59 · US DHS
**UFLPA** 144 · US DoD Chinese-military companies 397 · US special legislative exclusions
515 · UK Modern Slavery Statement Registry 11,718 (w/ disclosed risks + ILO indicators) ·
AfDB debarred 1,334 · World Bank debarred 1,241 · OFAC SDN · NBIM exclusions 205 · OHCHR
settlement companies 158 · TW strategic-trade entities 11,655 · PH GPPB blacklist 114.

**Company / corporate / sector:** SI KPK business restrictions 7,927 · BR BCB disqualified
426 · AU Victoria building practitioners · SG BCA contractors · CO ICA · HK licensed hotels
1,812 · HK money lenders 1,877 · CN MARA distant-water fishing 167 · AU AFMA fishery
concessions · AU AMSA ships 7,527.

The all-registry cross-source cluster run (cap 2,000/registry) pooled **37,566 entities →
27,810 deduped clusters, 3,510 cross-source** — an entity that appears on two or more lists
(e.g. Huawei/SMIC/Hikvision flagged by both US DoD and the special-exclusions list).

## Source catalogs (pointers, not scraped data)

- `licensed_entity_sources.yaml` — **1,111** official registries / 95 countries / 18
  industries (swarm-verified, propose-only; grow via `merge_entity_sources.py`).
- `migrant_support_orgs.yaml` — **532** protective orgs / 49 regions (helplines, shelters,
  legal aid, unions, IOM/ILO/Polaris/ITF; grow via `merge_support_orgs.py`).
- `entity_sources.yaml` — **72** monitored sources (Research Monitor).
- `reports/opensanctions_sources/` — 400 harvested OpenSanctions source pointers + the
  draft-spec verification queue (propose-only).

## Relationship graph

A source-agnostic edge shape every connector writes into (propose-only, dedup on the triple):

```python
{ "subject_id", "predicate", "object_id",   # canonical entity ids
  "source", "weight",                        # provenance + confidence 0..1
  "qualifier": {"share": .., "rel_type": .., "interest_type": .., "start_date": ..} }
```

Predicate vocabulary: `parent_of`, `owns_or_controls`, `registers` / `registrar_of` /
`hosted_on` / `mail_via` (domain), `agency_recruits_for`, `officer_of`, `operates_port`,
`port_visited_by`. Built edge sources: **GLEIF Level-2 RR** (`parent_of`, CC0),
**OpenOwnership BODS** (`owns_or_controls` with % share, CC0), **domain_intel** (registrant /
infra). Build-next: US OFLC H-2A/H-2B (`agency_recruits_for`), ICIJ Offshore Leaks
(`officer_of`).

## Screening + linkage

- `entity_screen.py` — fuzzy name match (RapidFuzz `token_sort_ratio`, word-order invariant,
  difflib fallback) → SANCTIONED / FLAGGED / LICENSED / NOT_FOUND.
- `entity_link.py` — **splink** probabilistic linkage joining registry entities to GLEIF on
  the canonical **LEI** (block on reg-number + name-token/jurisdiction; identifier-anchored).
  Live proof: 243 GLEIF GB × 30 perturbed registry rows → 96.7% linked, **100% correct LEI**.
- `entity_link.cluster_entities` — cross-registry dedup (deterministic reg-number + core-name
  union + RapidFuzz fuzzy; splink is *not* used here — on homogeneous registry names its EM
  can't discriminate). Name merges require a shared non-blank jurisdiction (precision guard).

The **GLEIF LEI** is the reliable cross-jurisdiction key: link each list to GLEIF, then
cluster by LEI.

## Canonical schema — FollowTheMoney (FtM)

`scripts/ftm_schema.py` normalises every connector record into the **FtM** entity model
(`alephdata/followthemoney`, MIT) — the same schema OpenSanctions, Aleph, and nomenklatura
speak — so the KB is interoperable with that ecosystem. Output is an FtM `EntityProxy`
dict (`{"id", "schema", "properties": {prop: [values]}}`) loadable straight into Aleph.

- `entity_type` → FtM schema: `company`/`employer`/`lender` → **Company**, `individual` →
  **Person**, agencies/clinics/NGOs → **Organization**, `regulator` → **PublicBody**,
  `sanctioned_entity` → **LegalEntity**, `vessel` → **Vessel**.
- fields → real FtM properties: `name`/`alias`/`country`(ISO-2)/`address`/`publisher` (Thing);
  `leiCode`/`licenseNumber`/`registrationNumber`/`taxNumber`/`jurisdiction`/`status`/`sector`
  (LegalEntity); plus `topics` (`sanction`/`debarment`/`export.control`). The **LEI** is the
  canonical id when present (`lei-<LEI>`), else a deterministic content hash.
- The FtM **library** pulls in PyICU, which can't build on this Windows box, so the
  serialiser is **pure-Python** (property names verified against the upstream schema YAMLs);
  `to_ftm(record, validate=True)` routes through the library when it *is* installed (same
  shape either way). Live-proven on real GLEIF + DOL WHD pulls.

## Tooling adopted (permissive, Windows-clean, no Node / no AGPL / no model downloads)

`rapidfuzz` (MIT, name matching) · `splink` + `duckdb` (MIT, record linkage) · `whoisit`
(BSD-3, RDAP) · `dnspython` (ISC, DNS) · `patchright` (Apache-2.0, stealth Playwright/Edge) ·
`camelot` + `pdfplumber` (MIT, PDF tables) · `curl_cffi` (MIT, TLS-impersonation fetch).
The fetch ladder: `urllib → curl_cffi → patchright(Edge) → screenshot+Gemma-4 vision →
agentic Gemma-4 browser`. Selection is repeatable via `tooling_scout.py` +
`.claude/agents/tooling-scout.md`.

## License ledger

Cleanest (use freely): **CC0** (GLEIF LEI + RR, OpenOwnership BODS), **US public domain**
(DOJ, DOL, OFAC, SAM.gov, CourtListener), **OGL** (UK Modern Slavery). Non-commercial only:
**CC-BY-NC** (OpenSanctions data exports — fine for this defensive NGO/regulator framing;
the underlying CBP/DHS lists are US public domain). Share-alike on redistribution: ICIJ,
OSM, Open Supply Hub. Excluded (not open): OpenCorporates bulk. Do-not-scrape (ToS forbid
AI/bulk): BAILII / AustLII / NZLII / WorldLII / SAFLII — routed around.

## Research provenance

- [`docs/research/scraping_tooling_adoptions_2026_06_18.md`](research/scraping_tooling_adoptions_2026_06_18.md) — fetch ladder, patchright/camelot, OpenSanctions specs.
- [`docs/research/open_datasets_and_tooling_2026_06_18.md`](research/open_datasets_and_tooling_2026_06_18.md) — GLEIF/BODS/GFW datasets, splink, search kits.
- [`docs/research/aircraft_vessels_ports_relationships_2026_06_19.md`](research/aircraft_vessels_ports_relationships_2026_06_19.md) — asset-class registries + the relationship graph.
- [`docs/research/osint_courtcases_advisories_2026_06_19.md`](research/osint_courtcases_advisories_2026_06_19.md) — OSINT tools, court cases, advisories → GREP/RAG.
- [`docs/research/entity_intelligence_tooling_2026_06_13.md`](research/entity_intelligence_tooling_2026_06_13.md) — earlier tooling survey.

## Run it (operator)

```bash
PY=...                                              # recovery venv python
# resolve one registry (propose-only)
$PY scripts/acquisition_cascade.py --registry us_dhs_uflpa
# GLEIF entities + corporate parents for a country
$PY scripts/gleif_lei.py --country NP --limit 200 --out reports/entity_kb/gleif_np.jsonl
$PY scripts/gleif_rr.py  --country NP --limit 200
# cross-registry clustering (cross-source = the high-value signal)
$PY scripts/cluster_registries.py --cap 2000
# screen a name across everything collected
$PY scripts/entity_screen.py --query "Sunrise Overseas Manpower"
# court-case + enforcement feeds
$PY scripts/doj_press.py --title "forced labor" --match "pleaded|sentenced|indict"
$PY scripts/dol_whd.py --migrant-only            # needs free DOL_API_KEY
```

## Honest boundaries (what this is *not*)

- Not wired into the live demo, the render app, or the model path — it is acquisition /
  research tooling that produces **proposed** records under `reports/`.
- Not a real-time lookup service. It pulls bounded slices on demand.
- Does not replace the trafficking knowledge layer (GREP 451 rules / RAG 859 docs); it is a
  *separate* entity layer that could feed it after human review.
- Post-GDPR most domain registrant fields are redacted — `domain_intel` is honest about it.
