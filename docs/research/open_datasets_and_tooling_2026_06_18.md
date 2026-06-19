# Open datasets, registries & tooling — verified research (2026-06-18)

> Synthesis of three verified research passes (a `tooling-scout` run + two
> general-research agents). Every star/license/endpoint below was checked live via
> `gh`, PyPI, vendor docs, or a direct endpoint probe on 2026-06-18; items that
> could not be confirmed are marked **unverified** and must be re-checked before use.
> Real-not-faked: nothing here is assumed. Pairs with
> `scraping_tooling_adoptions_2026_06_18.md` (fetch ladder + OpenSanctions specs) and
> `entity_intelligence_tooling_2026_06_13.md` (GDELT / news / sanctions data).

Constraints every recommendation respects: Python-first, permissive licence
(MIT/Apache/BSD/CC0), actively maintained, **no Node runtime, no AGPL/GPL, no large
model downloads**, fragile Windows box + system Edge. Output stays **propose-only**.

## 1 — Tooling (libraries / SDKs / MCP)

| Tool | slug | ★ | licence | verdict | integration point |
|---|---|---|---|---|---|
| **RapidFuzz** | rapidfuzz/RapidFuzz | 3962 | MIT | **ADOPTED ✓** | `entity_screen._seq_ratio` — word-order-invariant `token_sort_ratio`, prebuilt Windows wheels; guarded import w/ difflib fallback (done this session) |
| **splink** | moj-analytical-services/splink | 2211 | MIT | **ADOPTED ✓** | probabilistic record-linkage (DuckDB, no server) → `scripts/entity_link.py` joins registry entities to GLEIF on the canonical **LEI** (block on reg-number + name-token/jurisdiction; compare name JaroWinkler + identifier/jurisdiction exact). Real-data proof: 243 GLEIF GB × 30 perturbed registry rows → 96.7% linked, **100% correct LEI** |
| **followthemoney** | opensanctions/followthemoney | 73 | MIT | **ADOPT** | the FtM entity schema — normalise `entity_kb` output into the OpenSanctions/Aleph shape; unlocks offline screening |
| **nomenklatura** | opensanctions/nomenklatura | 246 | MIT | **ADOPT** | `xref`/dedup against locally-downloaded FtM sanctions data → offline screening in `entity_screen` (keeps case queries on-prem) |
| **frictionless-py** | frictionlessdata/frictionless-py | 826 | MIT | **ADOPT** | a `format: datapackage` resolver path + `validate()` row-schema gate before KB ingest (catches gov-CSV column drift) |
| **pandas-gbq** | googleapis/python-bigquery-pandas | 488 | BSD-3 | **ADOPT (when BQ wired)** | thin BigQuery read path (`read_gbq()` → DataFrame); much lighter than full `google-cloud-bigquery` |
| **BODS data-standard** | openownership/data-standard | 77 | Apache-2.0 | **USE-DATA / PORT** | beneficial-ownership schema + a **register-of-BO-registers** source list → a BODS analogue of `harvest_opensanctions_sources.py` |
| **dedupe** | dedupeio/dedupe | 4482 | MIT | CONSIDER | active-learning dedup (the "AGPL" reputation is a myth — verified MIT); splink fits our batch model better |
| **pygleif** | ggravlingen/pygleif | 21 | MIT | CONSIDER | thin GLEIF LEI client — or just `urllib` the LEI REST API directly |

**AVOID (verified blockers):** `openownership/bodsdata` (**AGPL-3.0** — use the Apache
`data-standard` instead), `OData/odatapy-client` (archived 2020, C++ — hit OData
`$format=json` directly with a `list_path` JSON spec, as `br_bcb_disqualified` does),
`yente` / `moov-io/watchman` (fine licences but Docker/Go services, not Python libs),
`modelcontextprotocol/servers` collection + most search MCPs (**Node**), `SearXNG`
(**AGPL**), Firecrawl (Node + AGPL engine).

**5-step adoption plan:** (1) RapidFuzz ✓ done → (2) followthemoney as canonical schema
→ (3) nomenklatura offline screening (honour CC-BY-NC data boundary) → (4) `format:
datapackage` + frictionless validate gate → (5) splink propose-only merge tier. BigQuery
(`pandas-gbq` + `LucasHild/mcp-server-bigquery`, MIT) deferred until GDELT-via-BQ is wired.

## 2 — Open datasets (bulk / API)

Top-10 "onboard next", ranked by migrant-labour relevance × low access friction. ✅ =
clean JSON/CSV/API (resolver-ready) · ⚠️ = needs a thin connector · ❌ = gated/paywalled.

| # | Dataset | Endpoint | Entities | Licence | Fit |
|---|---|---|---|---|---|
| 1 | **GLEIF LEI** ✓ built | `api.gleif.org/api/v1/lei-records` (by-country/name, paginated) — `scripts/gleif_lei.py` | ~2.5M legal entities + ownership | **CC0** | ✅ the global entity backbone + canonical join-key |
| 2 | **Global Fishing Watch — Vessel Identity** | `gateway.api.globalfishingwatch.org` (v3 vessels) | fishing vessels: IMO/MMSI, flag, **owner+operator** | CC-BY-NC-SA (free token) | ✅ key — **forced-labour-at-sea** |
| 3 | **OpenOwnership BODS** ✓ built | `oo-bodsdata.s3.amazonaws.com/data/<dataset>/...` — parser `scripts/openownership_bods.py` (BODS 0.4+0.2) | beneficial owners ↔ companies (UK PSC, ROE, GLEIF-BODS) | **CC0** | ✅ JSON/ndjson bulk |
| 4 | **OpenSanctions Consolidated** | `data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv` | OFAC+EU+UN+80 sources (persons/cos/**vessels**) | **CC-BY-NC** ⚠ | ✅ but NC-data boundary (we currently port *metadata* only) |
| 5 | **SEC `sec_quarterly_financials`** (BigQuery) | `bigquery-public-data.sec_quarterly_financials` | public companies: name, CIK, **SIC industry**, address | public domain | ⚠️ BigQuery |
| 6 | **Patents `patents.publications`** (BigQuery) | `patents-public-data.patents.publications` | harmonised corporate **assignees + country** (~98M) | mixed/public | ⚠️ BigQuery |
| 7 | **ICIJ Offshore Leaks** | offshoreleaks.icij.org/pages/database (CSV/Neo4j) | 810k offshore entities, officers, intermediaries | ODbL + CC-BY-SA ⚠ | ⚠️ graph-CSV connector |
| 8 | **Open Supply Hub** | `opensupplyhub.org/api/facilities` | named **production facilities** (garment+) | CC-BY-SA, free cap 5k ⚠ | ⚠️ key, capped |
| 9 | **GDELT GKG** (BigQuery) | `gdelt-bq.gdeltv2.gkg` | orgs/persons in news w/ `FORCED_LABOR`/`TRAFFICKING` themes | open (cite) | ⚠️ BQ, noisy |
| 10 | **FEC** (BigQuery) | `bigquery-public-data.fec` | committees + donors w/ **employer/occupation** | public domain | ⚠️ BigQuery |

Cleanest first onboards (no key, no BQ): **GLEIF (CC0)** and **OpenOwnership BODS
(CC0)**. **Do NOT assume in BigQuery** (agent-flagged, unverified there): GLEIF, USPTO
trademarks, USASpending, Census County Business Patterns. **Unverified as open bulk:**
IMO GISIS, ITF seafarer/manning files, OpenCorporates bulk (paywalled since 2023) — GFW
(#2) is the open vessel-ownership substitute.

## 3 — Search SDKs / MCP / Claude skills

| Pick | pkg / source | key? | free tier | licence | note |
|---|---|---|---|---|---|
| **Common Crawl** | `cdx-toolkit` | no | free (AWS Open Data) | Apache-2.0 | best keyless web-scale index |
| **DDGS** | `ddgs` | no | free, soft-limited | MIT | keyless meta-search; wrap w/ backoff (replaces AGPL SearXNG) |
| **Tavily** | `tavily-python` | key | 1,000/mo recurring | MIT client | cleanest hosted AI-search drop-in |
| **Exa** | `exa-py` | key | ~20,000 req/mo | MIT client | largest free monthly headroom |
| **mcp-server-fetch** | modelcontextprotocol/servers `/fetch` | no | — | MIT | **Python** URL→markdown MCP |
| **duckduckgo-mcp-server** | nickclyde/duckduckgo-mcp-server | no | — | MIT | **Python** search+fetch MCP |
| **PAI OSINT skill** | danielmiessler/…/OSINT | — | — | MIT | **PORT its 300+ source catalog + ethics gate** into `entity_sources.yaml` (goldmine) |
| **scrapling-skill** | daymade/claude-code-skills | — | — | MIT | drives Scrapling (Python, no Node) |

For Node-only search MCPs (Exa/Tavily/Brave), **skip the MCP, call the REST API from
Python** — the `adverse_media.py` pattern. **Dead/avoid:** Bing Search API (retired
2025-08), SearXNG (AGPL), Firecrawl MCP (Node+AGPL). Anthropic's own `skills`/`plugins`
ship nothing for scraping (and the plugins repo is proprietary ToS — do not vendor).

## 4 — New migrant-corridor registries (verified, onboard-next)

`gb_modern_slavery_statements` (UK MSR, 11,718 orgs, OGL) **onboarded this session** as
proof. The rest are the verified queue, with the resolver mapping the agent identified:

| Registry | endpoint | format / fetch_via | machine-readable? |
|---|---|---|---|
| **UK Modern Slavery CSV** ✓ | `downloads.modern-slavery-statement-registry.service.gov.uk/publicdownloads/StatementSummaries{YEAR}.csv` | `csv` / urllib | ✅ (done; 75 cols incl. ILO indicators) |
| **BGMEA members** (BD garment) | `bgmea.com.bd/page/member-list?page=1..214` | `html_table` / urllib, paginate | ✅ HTML (4,275 verified) |
| **SEC EDGAR submissions/EFTS** | `data.sec.gov/submissions/CIK##########.json`; `efts.sec.gov/LATEST/search-index?q=...` | `json` / urllib + descriptive UA | ✅ JSON (UA required) |
| **SLBFE agencies** (LK recruiters) | `applications.slbfe.lk/feb/la/la_details.asp?agency=A..Z` | `html_table` / urllib, 26 calls | ✅ HTML |
| **BP2MI SISKOP2MI P3MI** (ID recruiters) | `siskop2mi.bp2mi.go.id/profil/lembaga/list_lembaga/p3mi` → detail/{id} | `html_table` / urllib, two-step | ⚠️ HTML, no JSON |
| **JTKSM APS** (MY agencies) | `jtksm.mohr.gov.my/en/services/private-employment-agencies/...` | `html_table` / urllib, ~126 pp | ⚠️ HTML |
| **Bahrain Open Data (LMRA)** | `data.gov.bh/explore/dataset/.../api/records/...` | `json` / urllib | ✅ JSON (but work-permit *aggregates*) |
| **BEOE OEPs** (PK recruiters) | `beoe.gov.pk/list-of-oeps?show=active` | `html_table` / **curl_cffi** (WAF 403s urllib) | ⚠️ needs impersonation tier (~2,757) |
| **DOL Sweat & Toil** | `apiprod.dol.gov/v4/get/sweat_toil_country_goods/...` | `json` / urllib (free key) | ✅ JSON |
| **Nepal DoFE agencies** | `foreignjob.dofe.gov.np/Home/RecruitmentAgency` | **browser tier** (capture XHR, DMW playbook) | ❌ AJAX/DataTables |

**Browser/agentic tier (do not urllib):** Nepal DoFE, DOLAB Vietnam, MARINA + India
MEA (per-run PDF URL discovery → camelot). **Key-gated, high-value:** Open Supply Hub
(garment, all SE-Asia; CC-BY-SA), GFW Vessels (fishing; CC-BY-NC — honour it).
**Unverified — do not catalogue yet:** Thai DOF fishing white-list, Saudi Open Data
commercial registration, Gulf DW lookups (Musaned/Tadbeer/PAM/ADLSA — verify-only).

## 5 — Onboarded this session + next actions

- **Onboarded:** `gb_modern_slavery_statements` (11,718 UK orgs, OGL) — cascade now 30
  registries. **RapidFuzz** adopted into `entity_screen`. **GLEIF** (`scripts/gleif_lei.py`,
  LEI Records API, CC0 — parameterised by country/name; live-pulled real NP entities) and
  **OpenOwnership BODS** (`scripts/openownership_bods.py`, BODS 0.4+0.2 — parses any bulk
  slice; verified on the data-standard example) connectors built. Both are *parameterised*
  (by-country / by-file), so they live as standalone connectors, not zero-arg `--registry`
  cascade entries.
- **Highest-leverage next:** BGMEA / SLBFE / SEC-EDGAR / BP2MI as `html_table`/`json`
  specs (clean, no key); `followthemoney` as the canonical entity schema; PORT the PAI
  OSINT 300-source catalog into `entity_sources.yaml`; join the new registries on the
  GLEIF LEI as the canonical id.
- **Licence ledger:** CC0 (GLEIF, OpenOwnership), public-domain (SEC/FEC/UK-OGL) are the
  cleanest; CC-BY-NC (OpenSanctions, GFW) fine for the non-commercial NGO framing but
  flagged; share-alike (ICIJ, OSM, OpenSupplyHub) inherits on redistribution.
