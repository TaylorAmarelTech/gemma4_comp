# Recruitment-screening pipeline (search → scrape → screen → verify → profile)

A defensive, propose-only pipeline for NGOs, regulators, and platform-safety
teams to triage recruitment material for trafficking-indicative signals. It
composes four offline-first scripts plus the existing harness. Nothing here
mass-scrapes, embeds a third-party key, or mutates live knowledge — every
stage analyses content the operator provides or pages the operator is
investigating, and writes only to gitignored `reports/` scratch.

```
  search/discover        scrape/fetch         extract facts        screen            verify              profile
  (keyless DDG, ──────►  (robots-respecting,  ──────►  agency      ──────►  GREP     ──────►  licensed   ──────►  risk dossier
   PII-filtered,          capped, opt-in)      names, phones,       suspicious        registry            (high/medium/low)
   review-only)                                clinics, addresses,  language          (DMW-seeded)        + local search
                                               job orders, fees
```

## The pieces

| Stage | Script / surface | What it does |
|---|---|---|
| **Discover** | `scripts/extract_agency_facts.py --discover "<query>"` | Keyless DuckDuckGo search (`research_tools.WebSearchTool`, PII-filtered) returns candidate URLs to **review** — it never auto-fetches them. |
| **Scrape** | `scan_recruitment_text.py --url` / `extract_agency_facts.py --url` | Robots-respecting, rate-limited, identifying-UA fetch, capped at 25 URLs. Offline-first: `--dir`/`--file`/`--text` need no network. |
| **Extract facts** | `extract_agency_facts.py` → `extract_facts()` | Pure deterministic extraction of agency name(s), licence-number claims, phones (deduped), emails, addresses, named medical clinics, job orders (position/destination/salary, parsed per line), and fee demands. |
| **Screen** | `scan_recruitment_text.py` → triage `screen_items()` | The deterministic GREP suspicious-language tier (the same first tier as the Platform Triage harness) — flags debt-bondage, fee-camouflage, document-retention, coercive-collection, etc., with ILO/statute citations. |
| **Verify** | `agency_registry.py` → `verify_agency()` | Checks a named agency against an official **licensed** registry (DMW-seeded). Not-found, or expired/cancelled/delisted/suspended, is a red flag (pairs with the GREP rule `licensed_agency_chop_passthrough`). |
| **Profile + search** | `extract_agency_facts.py` → `build_dossier()` / `search_dossiers()` | Per-page dossier with a `risk_tier`; local full-text + structured search (risk tier / licence status) over the staged set. |

## Quick start (offline)

```bash
# 1) screen a single ad for suspicious language
python scripts/scan_recruitment_text.py --text "Pay PHP 120,000 placement fee, we hold your passport..."

# 2) verify whether a recruiter is licensed
python scripts/agency_registry.py --query "Easternwind Workforce Solutions"
#   -> {"status": "licensed_red", "license_status": "cancelled", ...}

# 3) build full dossiers from a folder of saved pages, cross-checking licences
python scripts/extract_agency_facts.py --dir saved_pages/ \
    --registry data/agency_registry/sample_licensed_agencies.json

# 4) search the staged dossiers for the high-risk ones
python scripts/extract_agency_facts.py --search "" --risk high \
    --from reports/agency_dossier/dossier_<hash>.json
```

## Plugging in real data (operator-side)

- **Licensed registry.** Download an official export from the regulator's
  inquiry page — e.g. the Philippine DMW *Licensed Recruitment Agencies*
  inquiry (`https://dmw.gov.ph/inquiry/licensed-recruitment-agencies`) — and
  normalize it into the registry schema with
  `python scripts/agency_registry.py --ingest <export.json>`. The staged file
  lands in gitignored `reports/agency_registry/`; the committed default is a
  clearly-labelled **synthetic** sample. The DMW page is a Nuxt SPA that ships
  a public client API key; this tool embeds **no** key and does **not**
  mass-scrape the government API.
- **Discovery.** `--discover` uses keyless DuckDuckGo and returns URLs to
  review; the operator decides what to fetch. Live fetch (`--url`) honours
  robots.txt and is capped.

## Responsible-use boundary

- Output is **advisory**, never a verdict. A GREP hit means "review this";
  "no hit" means "nothing matched the rule set", not "safe". A licence verdict
  is a verification aid — licence status is volatile; confirm on the official
  page.
- This screens content the operator provides or a small list of pages the
  operator is investigating. It is **not** a mass crawler and **not** a tool
  for profiling arbitrary sites at scale.
- Reports are gitignored scratch (`reports/recruitment_scan/`,
  `reports/agency_dossier/`, `reports/agency_registry/`); the pipeline never
  mutates the live knowledge layer.

## Tests

`tests/test_scan_recruitment_text.py`, `tests/test_agency_registry.py`,
`tests/test_extract_agency_facts.py` — all offline (no network), covering
extraction accuracy, every licence verdict, the suspicious-language screen,
the dossier risk tiers, dossier search, and injected-searcher discovery.
