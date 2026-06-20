# DueCare Entity-Intelligence — Complete Reference Dump

> A single, portable, exhaustive reference for the whole entity-intelligence / recruitment-
> verification subsystem: every script, every website/endpoint, every GitHub repo/library,
> every tool call, what each is for, its capabilities, and the **fragility** of each (does it
> block, need a key, JS-wall, forbid scraping, drift?). Built 2026-06-13 → 2026-06-19.
> Self-contained — drop it into another project as-is.
>
> **Two hard invariants govern everything below:**
> - **Propose-only.** Every connector stages output to gitignored `reports/` (`reports/entity_kb/`,
>   `reports/opensanctions_sources/`, `reports/acquisition/`). Nothing mutates a live KB / model /
>   demo. A human reviews and promotes.
> - **Real-not-faked.** Field maps are authored against the *live* source response, never guessed;
>   a source that blocks or returns nothing parseable is skipped + logged, never fabricated.
>   Public-register entity names are allowed (output gitignored); scripts embed no secrets.
>
> **Environment constraints that shape every tool choice:** Python 3.11/3.12, Windows box where the
> system Python is OneDrive-corrupted (run via a uv venv at `%LOCALAPPDATA%\gemma4-testenv\venv`);
> **no Node runtime, no AGPL/GPL deps, no large model downloads, no compiled deps that need a
> toolchain** (e.g. PyICU won't build). Optional deps are guarded so the pure-stdlib path always works.

---

## 0. Architecture in one line

```
discover sources ──▶ resolve (fetch+parse) ──▶ normalize ──▶ link (GLEIF LEI) ──▶ screen ──▶ FtM ──▶ propose
  catalogs            34-registry cascade        entity_kb     entity_link        entity_     ftm_     reports/
  (1,111 + 532 + 72)  (tier ladder + archive)                  + cluster          screen     schema
```

Verified counts (reproduce with the commands in §8): **34 addressable registries** (23 config specs
+ 11 deterministic resolvers/presets) · **1,111** licensed-entity source pointers (95 countries, 18
industries) · **532** migrant-support orgs (49 regions) · **72** monitored Research-Monitor sources ·
all-registry cluster run pooled **37,566 entities → 27,810 clusters, 3,510 cross-source**. Separate
from the trafficking knowledge layer (GREP 451 rules / RAG 859 docs — *unchanged* by this subsystem).

---

## 1. Scripts / connectors (every tool — purpose, source, license, fragility)

All under `scripts/`, offline-tested (injectable fetch/lookup), sibling-loaded via `importlib`.
**Fragility key:** 🟢 stable (CC0/public-domain API or static file) · 🟡 needs a key / impersonation /
periodic re-verify · 🔴 JS-walled / volatile / blocks.

### Core engine
| Script | Purpose | Source / endpoint | License | Fragility |
|---|---|---|---|---|
| `registry_spec.py` | Config-driven resolver: a YAML spec (`url`+`format`+`fields`) → entity records. New registry = a YAML block, not Python. | (engine) | — | 🟢 |
| `registry_parsers.py` | One parser interface for `html_table`/`csv`/`xlsx`/`json`/`pdf_table`. Header auto-detect (exact-first, substring fallback); stdlib XLSX reader (zipfile+ElementTree, no openpyxl); camelot for PDF tables. | (engine) | — | 🟢 |
| `acquisition_cascade.py` | Multi-layer escalation: tier1 deterministic → tier2 LLM → tier3 agentic → tier4 vision; cheapest-wins, fault-isolated, archives every outbound URL. `--registry <id>` + `--arg KEY=VALUE`. | (engine) | — | 🟢 |
| `entity_kb.py` | Migration-world entity KB. 11 `ENTITY_TYPES`; merge key = (type, normalize_name, jurisdiction); tier precedence official>secondary>community. Default store synthetic. | (engine) | — | 🟢 |
| `entity_screen.py` | Screen a name across every collected register → SANCTIONED/FLAGGED/LICENSED/NOT_FOUND. RapidFuzz `token_sort_ratio` (word-order invariant) + content-token Jaccard; difflib fallback. | (engine) | — | 🟢 |
| `entity_link.py` | splink probabilistic linkage → join registry entities to GLEIF on the canonical **LEI**; + `cluster_entities` (deterministic reg-no + core-name union + RapidFuzz; NOT splink — its EM can't discriminate homogeneous names). | (engine) | — | 🟡 needs splink+duckdb |
| `cluster_registries.py` | Resolve all cascade registries → pool tagged-by-source → cluster → cross-source clusters (entity on ≥2 lists). | (the cascade) | — | 🟡 network-heavy |
| `ftm_schema.py` | **Canonical schema**: normalize any connector record → FollowTheMoney EntityProxy `{id,schema,properties}` (Aleph-loadable). Pure-Python (FtM lib optional). | upstream FtM schema YAMLs | MIT | 🟢 |
| `harvest.py` | Routine harvester: runs every collector, merges, optional adverse screen, timestamped manifest. Weekly GitHub-Actions cron. | (orchestrator) | — | 🟢 |

### Deterministic registry collectors (proven, bulk)
| Script | Registry | Endpoint | Count | Fragility |
|---|---|---|---|---|
| `bd_oep_agencies.py` | BD OEP/BMET licensed recruiters | `https://www.oep.gov.bd/agencies` | 2,834 | 🟢 server-rendered HTML |
| `bd_mra_mfi.py` | BD MRA licensed microfinance | `https://ndb.mra.gov.bd/mra_web/everify/mfi-list` | 904 | 🟢 JSON API (in inline script) |
| `cn_mara_dwf.py` | CN MARA distant-water-fishing compliance | `https://www.moa.gov.cn/govpublic/YYJ/202504/t20250417_6473317.htm` | 167 | 🟡 dated URL drifts yearly |
| `au_afma_concessions.py` | AU AFMA fishery concession holders | `https://www.afma.gov.au/commercial-fishers/resources/concession-holders-and-sfr-conditions` (XLSX) | 1,200+ | 🟢 XLSX via stdlib reader |
| `hk_money_lenders.py` | HK CR licensed money lenders | HK Companies Registry PDF | 1,877 | 🟡 PDF (camelot/pypdf) |
| `dmw_representatives.py` | PH DMW agency reps → individuals | (from DMW agency notes) | 3,573 distinct | 🟢 derived |
| `browser_scrape.py` | DMW preset → 3,788 agencies | `https://master-api.dmw.gov.ph/api/v1/public/licensed-agencies` (SPA JS-walled; API-replay-paginate, forward captured auth header) | 3,788 | 🔴 SPA, 401 tokenless |

Also addressable as deterministic resolvers in the cascade: `hk_eaa` (HK employment agencies,
`eaa.org.hk` result.php), `ofac_sdn` (`treasury.gov/ofac/downloads/sdn.csv`), `worldbank_debarred`
(World Bank debarred firms JSON, 1,241).

### CC0 bulk / ownership connectors
| Script | Purpose | Endpoint | License | Fragility |
|---|---|---|---|---|
| `gleif_lei.py` | GLEIF legal entities (LEI = canonical id). Paginate by country/name/status. | `https://api.gleif.org/api/v1/lei-records` | **CC0** | 🟢 no key; `filter[entity.legalName]` is EXACT not fuzzy → name pools sparse, join on reg-number |
| `gleif_rr.py` | GLEIF Level-2 **parent_of** edges. | `…/lei-records/{lei}/{direct,ultimate}-parent-relationship` | **CC0** | 🟢 most entities report no parent (only group subsidiaries) |
| `openownership_bods.py` | Beneficial-ownership entities + **owns_or_controls** edges (`--edges`). BODS 0.4 + 0.2. | `oo-bodsdata.s3.amazonaws.com` bulk / data-standard example | **CC0** | 🟢 bulk is ~GB; cascade pulls a bounded slice |

### Court / enforcement / OSINT connectors
| Script | Purpose | Endpoint | License | Fragility |
|---|---|---|---|---|
| `doj_press.py` | DOJ press releases → offense-tagged prosecution docs (named defendants, MO). | `https://www.justice.gov/api/v1/press_releases.json` | US public domain | 🟢 no key; only `title=`+`sort=date` filter works (`topic`/`search`/`keyword` IGNORED); charges in plain language not USC |
| `dol_whd.py` | DOL Wage&Hour enforcement → employer-violation entities (H-2A/H-2B/MSPA/SRAW/child-labour). | data `https://api.dol.gov/v4/get/WHD/enforcement/json` (needs key); metadata `https://apiprod.dol.gov/v4/datasets/10362` (keyless) | US public domain | 🟡 full data needs free `DOL_API_KEY` (dataportal.dol.gov); `--preview` is keyless (metadata dataset_preview rows); v4 metadata endpoints KEYLESS, data endpoints 403 w/o key |
| `domain_intel.py` | Scam/recruitment domain → registrant + NS/MX edges (cluster sibling domains). | RDAP (`whoisit`) + DNS (`dnspython`) | — | 🟡 post-GDPR most gTLD registrant fields "DATA REDACTED" (handled: skip + flag); registrar+DNS still pivot |
| `adverse_media.py` | Negative-news / sanctions screening. Google News RSS workhorse (keyless, 7× recall vs GDELT), GDELT, OpenSanctions. Gemma precision filter. | `news.google.com/rss/search` + GDELT + OpenSanctions | mixed | 🟡 GDELT 429s on complex queries (quote name only, ~5s pace); OpenSanctions hosted API now needs a key |

### Acquisition / research / utility
| Script | Purpose | License | Fragility |
|---|---|---|---|
| `harvest_opensanctions_sources.py` | Read a local OpenSanctions clone's `datasets/<cc>/*.yml` → 400 government-registry source pointers (classify registry/debarment/sanctions/pep/regulatory). **Never fetches the CC-BY-NC data** (MIT metadata only). | MIT (metadata) | 🟢 needs a local clone |
| `opensanctions_to_specs.py` | Scaffold draft resolver specs from the harvest (`fields: TODO` + `_needs_verification`, never guessed). Recognizes the 2 onboarded data-dataset specs. | — | 🟢 |
| `tooling_scout.py` | `gh search repos`/`code` across queries → score vs constraints → ranked ADOPT/CONSIDER/AVOID. Driven by `.claude/agents/tooling-scout.md`. | — | 🟡 needs `gh` authed |
| `image_enhance.py` | Deterministic pre-OCR/vision enhancement (deskew/denoise+sharpen/clahe/upscale + crop + 4-pt perspective). Ported technique from OpenSearch-VL. OpenCV (camelot already pulls it). | — | 🟢 cv2 optional (no-op if absent) |
| `scrape_agency_sources.py` | HTML-table/JSON-list/CSV connectors → AgencyProfile. | — | 🟡 env-keyed live |
| `agentic_browse.py` | Gemma-4 function-calling browser agent ("Gemma proposes, code disposes"). Proven: Gemma paginated all 76 DMW pages → 3,788. | — | 🔴 needs Ollama + Edge |
| `sweep_registries.py` | Run the connector across catalogued registries → access matrix (extracted/endpoint_only/no_data/error). | — | 🟢 |
| `ingest_kaggle_agencies.py` | Ingest the operator's own Kaggle agency datasets (richer than live scraping): 7,500 agency DB + 3,732 data + 24,000 job orders → 2,924 foreign employers. | — | 🟡 Kaggle `kaggle/` dir shadows the pip package → strip cwd from sys.path |
| `llm_scrape.py` | render → screenshot+HTML → model extracts structure (vision waterfall; `enhance_image=True` opt-in). | — | 🔴 Playwright |

---

## 2. Websites / registries / data endpoints (the 23 config specs + more)

Every config-spec registry (`configs/duecare/research_monitor/registry_specs.yaml`), id · format · URL ·
verified count · fragility. Field maps were authored against the LIVE response (real-not-faked).

| id | fmt | URL | n | Fragility |
|---|---|---|---|---|
| `ph_gppb_blacklist` | json | `onlineblacklistingportal.gppb.gov.ph/obp-backend/cbr/cbr_public/` | 114 | 🟢 flat JSON |
| `si_kpk_business_restrictions` | json | `registri.kpk-rs.si/registri/omejitve_poslovanja/seznam/omejitve.json` | 7,927 | 🟢 flat JSON (name=`ps_naziv`) |
| `br_bcb_disqualified` | json | `olinda.bcb.gov.br/olinda/servico/Gepad_QuadrosGeraisInternet/versao/v1/odata/QuadroGeralInabilitados` | 426 | 🟢 OData (`list_path: value`); CPF masked at source |
| `tw_strategic_trade_entities` | csv | `publicinfo.trade.gov.tw/icp/Download.action?file=…` | 11,655 | 🟡 CJK/bilingual headers (`名稱name`) |
| `afdb_debarred` | html_table | `afdb.org/en/projects-operations/debarment-and-sanctions-procedures` | 1,334 | 🟢 HTML table |
| `no_nbim_exclusions` | html_table | `nbim.no/en/responsible-investment/exclusion-of-companies/` | 205 | 🟢 HTML table |
| `us_dod_chinese_military` | csv | `docs.google.com/spreadsheets/d/e/…/pub?output=csv` | 397 | 🟡 OpenSanctions-crawled Google Sheet |
| `us_special_legislative_excl` | csv | `docs.google.com/spreadsheets/d/e/…/pub?output=csv` | 515 | 🟡 Google Sheet (Huawei etc.) |
| `ohchr_settlement_companies` | csv | `docs.google.com/spreadsheets/d/e/…/pub?output=csv` | 158 | 🟡 Google Sheet |
| `gb_modern_slavery_statements` | csv | `downloads.modern-slavery-statement-registry.service.gov.uk/publicdownloads/StatementSummaries{YEAR}.csv` | 11,718 | 🟢 OGL; year-templated; group rows put co-number in OrgName |
| `us_cbp_forced_labor` | csv | `data.opensanctions.org/datasets/latest/us_cbp_forced_labor/targets.simple.csv` | 59 | 🟡 CC-BY-NC data (gov list public domain) |
| `us_dhs_uflpa` | csv | `data.opensanctions.org/datasets/latest/us_dhs_uflpa/targets.simple.csv` | 144 | 🟡 CC-BY-NC data |
| `bd_oep_cfg` | html_table | `oep.gov.bd/agencies` | 2,834 | 🟢 (reproduces `bd_oep`) |
| `bd_mra_cfg` | json | `ndb.mra.gov.bd/mra_web/everify/mfi-list` | 904 | 🟢 |
| `cn_mara_cfg` | html_table | `moa.gov.cn/govpublic/YYJ/202504/t20250417_6473317.htm` | 167 | 🟡 dated URL |
| `au_vic_building` | csv | `vicopendatavba.blob.core.windows.net/vicopendata/BPR.csv` | ~48,215 | 🟢 Azure blob CSV |
| `sg_bca_contractors` | json | `data.gov.sg/api/action/datastore_search?resource_id=…` | ~24,014 | 🟢 CKAN (paginate) |
| `co_ica_bpa` | json | `datos.gov.co/resource/wusb-7b8z.json` | 1,345 | 🟢 Socrata |
| `gb_licensed_sponsors` | csv | UK Register of Licensed Sponsors (Home Office; discover-latest CSV) | ~141,980 | 🟡 `discover:` latest-link |
| `au_amsa_ships` | xlsx | AMSA Australian Register of Ships | 7,527 | 🟢 XLSX |
| `ca_tfwp_positive_lmia` | csv | Canada TFWP positive-LMIA employers (Open Government) | 7,476 | 🟢 CSV (title-row quirk) |
| `hk_licensed_hotels_guesthouses` | csv | `hadla.gov.hk/psi/licensed-hotels-and-guesthouses/…csv` | 1,812 | 🟢 BOM in first header |
| `tw_mol_manpower` | json | `apiservice.mol.gov.tw/OdService/download/A17000000J-020002-LkO` | 3,377 | 🟢 data.gov.tw |

**Deterministic-resolver / preset endpoints (the other 11):** `dmw_lra` (`master-api.dmw.gov.ph/api/v1/public/licensed-agencies`, 3,788 🔴 SPA), `hk_eaa` (`eaa.org.hk` result.php), `hk_money_lenders` (HK CR PDF, 1,877 🟡), `bd_oep`/`bd_mra`/`cn_mara`/`au_afma` (see §1), `ofac_sdn` (`treasury.gov/ofac/downloads/sdn.csv` 🟢), `worldbank_debarred` (World Bank debarred JSON, 1,241 🟢), `gleif_lei` + `openownership_bods` (CC0, bounded via `--arg`).

**Source catalogs (pointers, not scraped data):**
- `configs/duecare/research_monitor/licensed_entity_sources.yaml` — **1,111** official registries / 95 countries / 18 industries (grow via `scripts/merge_entity_sources.py`; dedup on CONTENT key).
- `configs/duecare/research_monitor/migrant_support_orgs.yaml` — **532** protective orgs / 49 regions (helplines OWWA 1348 / IACAT 1343, shelters, legal aid, unions, IOM/ILO/Polaris/ITF; grow via `merge_support_orgs.py`).
- `configs/duecare/research_monitor/entity_sources.yaml` — **72** monitored sources (Research Monitor; swarm-verified).
- `reports/opensanctions_sources/` — 400 harvested OpenSanctions source pointers + a 341-endpoint draft-spec verification queue (gitignored, propose-only).

---

## 3. GitHub repos & libraries (every adoption + every AVOID, with reasons)

Stars/licenses verified live via `gh repo view` during the research passes (2026-06).

### ADOPTED (permissive, Windows-clean, in use)
| Repo / pkg | License | Role | Fragility |
|---|---|---|---|
| `lexiforest/curl_cffi` | MIT | TLS/JA3 impersonation fetch (beats Cloudflare fingerprinting); auto-fallback tier | 🟢 optional `fetch` extra |
| `Kaliiiiiiiiii-Vinyzu/patchright-python` | Apache-2.0 | drop-in Playwright that patches the `Runtime.enable` CDP leak; Edge channel, no Node | 🟡 browser tier |
| `camelot-dev/camelot` | MIT | tabular-PDF extraction (`format: pdf_table`); pure Windows wheels (opencv-headless+pypdfium2, no Ghostscript) | 🟢 text-PDF only |
| `jsvine/pdfplumber` | MIT | ruleless-PDF fallback behind camelot | 🟢 |
| `rapidfuzz/RapidFuzz` (3962★) | MIT | name matching (`token_sort_ratio`); prebuilt Windows wheels; in `entity_screen` + cluster | 🟢 |
| `moj-analytical-services/splink` (2211★) | MIT | probabilistic record-linkage (DuckDB backend, no server) in `entity_link` GLEIF join | 🟡 EM degenerates on homogeneous names → used only for the LEI join, not clustering |
| `meeb/whoisit` (129★) | BSD-3 | structured RDAP (registrant/registrar) in `domain_intel` | 🟢 |
| `rthalley/dnspython` (2665★) | ISC | NS/MX pivots in `domain_intel` | 🟢 |
| `alephdata/followthemoney` | MIT | the canonical entity SCHEMA (we use the schema; lib optional — see fragility) | 🔴 **lib won't build on Windows: PyICU needs ICU C lib (`KeyError: ICU_VERSION`)** → pure-Python serializer, schema YAMLs fetched from upstream |
| `opensanctions/opensanctions` (97 country dirs) | MIT code / **CC-BY-NC data** | source-list goldmine (`datasets/<cc>/*.yml` ≈ our spec) + consolidated screening data | 🟡 data is non-commercial |
| `shawn0728/OpenSearch-VL` (222★) | Apache-2.0 | **technique ported** (crop/perspective/super_resolution/sharpen) into `image_enhance` — NOT the Qwen3-VL/Megatron stack | n/a |

### USE-DATA / source-list goldmines (consume, don't vendor)
- `jivoi/awesome-osint` (27k★) — curated OSINT-source index; PORT the source URLs.
- `danielmiessler/Personal_AI_Infrastructure` → PAI **OSINT skill** (MIT) — a **300+ source catalog** + ethics gate to port into `entity_sources.yaml`.
- `openownership/data-standard` (Apache-2.0) — BODS schema + a register-of-BO-registers.
- `mitchellkrogza/Phishing.Database` (MIT) — ~496k keyless scam domains (`phish.co.za/latest/ALL-phishing-domains.lst`).
- `elliotwutingfeng/ThreatFox-IOC-IPs` (BSD-3) — hourly IP blocklist.

### ADOPT-NEXT (verified, not yet wired)
`pogzyb/asyncwhois` (MIT, WHOIS+RDAP fallback) · `secynic/ipwhois` (BSD-2, IP→ASN) · `censys/censys-python`
(Apache-2.0, CT-cert pivots, key) · `frictionlessdata/frictionless-py` (MIT, `format: datapackage` + validate) ·
`googleapis/python-bigquery-pandas` (BSD-3, thin BigQuery read) · `opensanctions/nomenklatura` (MIT, offline FtM screening) ·
`openaddresses/pyesridump` (MIT, ArcGIS paging — PORT ~600 LOC) · `ckan/ckanapi` + `afeld/sodapy` (MIT, portal clients) ·
`maastrichtlawtech/echr-extractor` (Apache-2.0, HUDOC pattern).

### AVOID (verified blockers — do not take as deps)
| Repo | Reason |
|---|---|
| `laramies/theHarvester` | GPL-2.0, CLI-only |
| `lanmaster53/recon-ng`, `megadose/holehe`, `ivre/ivre` | GPL-3.0 |
| `owasp-amass/amass` | Go binary, not Python-importable |
| `achillean/shodan-python` | proprietary-ish + paid key |
| `searxng/searxng` | **AGPL-3.0** (use `ddgs` MIT instead) |
| `firecrawl/firecrawl-mcp-server` | Node + AGPL engine |
| `openownership/bodsdata` | **AGPL-3.0** (use the Apache `data-standard` schema instead) |
| OpenCorporates bulk | not open (paywalled since 2023) |
| scrapegraphai / crawl4ai / tabula-py | py≥3.12-only / browser+torch-heavy / needs JVM |
| FlareSolverr, undetected-chromedriver, nodriver/zendriver, cloudscraper | Docker sidecar / GPL+stale / AGPL / defeated by modern CF |
| `abuse.ch` URLhaus/ThreatFox | **key-walled since 2025-06-30** (prefer Phishing.Database) |
| Bing Search API | **retired 2025-08-11** |

---

## 4. Datasets researched (bulk / API / BigQuery) — access + license + fragility

### Bulk / API (resolver-ingestible)
| Dataset | Endpoint | License | Fragility |
|---|---|---|---|
| **GLEIF LEI Golden Copy / Records API** | `api.gleif.org/api/v1/lei-records` · `goldencopy.gleif.org/api/v2/.../latest.csv` | **CC0** | 🟢 — the global entity backbone + the canonical join key |
| **GLEIF Level-2 RR** | `leidata.gleif.org/api/v1/concatenated-files/rr/...` · per-LEI parent endpoints | **CC0** | 🟢 parent_of edges |
| **OpenOwnership BODS** | `oo-bodsdata.s3.amazonaws.com/data/<dataset>/...` (Parquet/CSV/JSON) | **CC0** | 🟢 ~GB bulk |
| **OpenSanctions consolidated** | `data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv` | **CC-BY-NC** | 🟡 OFAC+EU+UN+80 sources |
| **Global Fishing Watch — Vessel Identity** | `gateway.api.globalfishingwatch.org` (v3) | CC-BY-NC-SA, free token | 🟡 forced-labour-at-sea |
| **ICIJ Offshore Leaks** | `offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip` | ODbL + CC-BY-SA | 🟡 graph-CSV, cite ICIJ |
| **Open Supply Hub** | `opensupplyhub.org/api/facilities` | CC-BY-SA, free cap 5k | 🟡 key, capped |
| **UN/LOCODE** | `github.com/datasets/un-locode/raw/main/data/code-list.csv` | **PDDL** | 🟢 port/location join key |
| **World Port Index (NGA Pub 150)** | ArcGIS Hub `arctic-nga.opendata.arcgis.com/datasets/world-port-index` / HDX | **US public domain** | 🟢 (`msi.nga.mil` 403s bots) |
| **US DOL Sweat & Toil (TVPRA)** | `apiprod.dol.gov/v4/get/sweat_toil_country_goods/...` | US public domain | 🟡 free key |
| **US SAM.gov Exclusions** | `api.sam.gov/entity-information/v4/download-exclusions` | US public domain | 🟡 key+token |

### BigQuery public datasets (query, not download; free 1TB/mo; needs a GCP project)
`bigquery-public-data.sec_quarterly_financials` (companies+SIC) · `patents-public-data.patents.publications`
(harmonised assignees+country) · `bigquery-public-data.fec` (donors w/ employer/occupation) ·
`gdelt-bq.gdeltv2.gkg` (orgs/persons w/ FORCED_LABOR/TRAFFICKING themes) · `bigquery-public-data.geo_openstreetmap`
(POIs ODbL) · `bigquery-public-data.world_bank_wdi` (corridor context CC-BY). Adopt `pandas-gbq` for the read path.
**Unverified in BigQuery (do not assume):** GLEIF, USPTO trademarks, USASpending, Census County Business Patterns.

### Aircraft / vessels / ports (asset-class registries)
- **Aircraft:** AU CASA (`casa.gov.au/.../acrftreg.csv`, 🟢), OFAC SDN aircraft-feature (XML 🟢), OpenSky DB
  (`s3.opensky-network.org/.../aircraftDatabase.csv` 🟢 unlicensed), FAA Releasable (🔴 Akamai-walled), Isle-of-Man
  ARDIS (html, offshore-jet owner). Offshore VP-B/VP-C/T7/P4 = opaque-by-design = a signal.
- **Vessels:** Combined IUU List (TMT `iuu-vessels.org/Home/Download` xlsx 🟢), UK FCDO ships csv (OGL 🟢), USCG
  PSIX (SOAP `cgmix.uscg.mil/xml/psixdata.asmx?WSDL` 🟡), Tokyo MoU APCIS detentions (html_table+params 🟢), UN 1718
  vessels (xml 🟢). FoC dark-fleet flags (Liberia/Marshall/Palau/Comoros) = NO public register = a signal.

### Court cases / advisories (mine for entities/MO/indicators)
**Mine-first (clean, public-domain, no key):** DOJ press-releases JSON API · CourtListener bulk CSV (S3 no-auth;
REST is 5/min) · DOL WHD API. Plus CTDC synthetic dataset (no PII gate), UNODC SHERLOC (HTML), US TIP Report (PDF),
EUR-Lex/CELLAR (SPARQL, CC-BY), HUDOC ECtHR (JSON), UK Find-Case-Law (LegalDocML XML, Open Justice Licence).
**→ GREP-rule sources (indicator PDFs):** ILO 11-indicator `wcms_203832.pdf`, ILO Fair-Recruitment `wcms_703485.pdf`,
FinCEN FIN-2020-A008, Polaris Typology (25 types), FATF Financial-Flows-2018.

---

## 5. Schemas — relationship edges + canonical FtM

**Relationship-edge schema** (source-agnostic, propose-only, dedup on the triple):
```python
{ "subject_id", "predicate", "object_id",   # canonical entity ids
  "source", "weight",                        # provenance + confidence 0..1
  "qualifier": {"share": .., "rel_type": .., "interest_type": .., "start_date": ..} }
```
Predicates: `parent_of` · `owns_or_controls` · `registers`/`registrar_of`/`hosted_on`/`mail_via` (domain) ·
`agency_recruits_for` · `officer_of` · `operates_port` · `port_visited_by`.
Built edge sources: **GLEIF Level-2 RR** (`parent_of`, CC0), **OpenOwnership BODS** (`owns_or_controls` w/ % share,
CC0), **domain_intel** (registrant/infra). Build-next: US OFLC H-2A/H-2B (`agency_recruits_for`), ICIJ (`officer_of`).

**Canonical FtM schema** (`ftm_schema.py`): entity record → FtM EntityProxy `{id, schema, properties:{prop:[values]}}`.
`entity_type` → schema (Company/Person/Organization/PublicBody/LegalEntity/Vessel). Real FtM props (verified from
upstream YAMLs): `name`/`alias`/`country`(ISO-2)/`address`/`publisher`/`topics` (Thing); `leiCode`/`licenseNumber`/
`registrationNumber`/`taxNumber`/`jurisdiction`/`status`/`sector` (LegalEntity). id = `lei-<LEI>` or `dc-<sha1>`.
**Topics mapped conservatively:** `sanction`, `debarment`, `export.control` (forced-labour). Aleph-loadable.

---

## 6. Fetch ladder + fragility / gotcha catalog (READ THIS before reusing)

**Fetch escalation ladder** (escalate only as far as the source forces):
`urllib → curl_cffi (TLS impersonation) → patchright/Playwright Edge (headless) → fetch_via:agentic (headed) →
[+ optional DUECARE_PROXY residential IP] → screenshot + Gemma-4 vision → agentic Gemma-4 browser`.

**Resolver rule of thumb:** server-rendered table / JSON API / downloadable file → build a deterministic spec
(split bytes-decoder from row-interpreter for testability). DataTables w/ unknown ajax endpoint → agentic/browser tier.

**Gotchas (every one is real, hit live this project):**
- **PyICU / followthemoney**: lib won't build on Windows (`KeyError: ICU_VERSION`) → pure-Python FtM serializer.
- **Cloudflare ASN/IP reputation** (e.g. `tourism.gov.mv`): 403s urllib + curl_cffi + headed patchright alike — it's
  datacenter-IP reputation, not fingerprint. Only a residential proxy (or an official API/allowlist) fixes it.
  Free proxies/Tor/free-VPN/WARP all lose to CF (WARP egresses CF's own AS13335).
- **GLEIF** `filter[entity.legalName]` is EXACT not fuzzy → name-query pools are sparse; join on the reg-number/LEI.
- **DOL v4**: data endpoints 403 "Missing Authentication Token" without `X-API-KEY`; the `/v4/datasets/{id}` METADATA
  (incl. `dataset_metadatum` = 110 cols + `dataset_preview` = real rows) is **KEYLESS** — use it to author field maps
  + sample. Full data = free key from dataportal.dol.gov. Old keyless bulk (`enfxfr.dol.gov`) is now a JS SPA shell.
- **DOJ API**: `topic=`/`search=`/`keyword=` params are IGNORED; only `title=` substring + `sort=date&direction=DESC`.
  Charges are plain-language (USC sections live in the indictment) → tag on offense vocabulary, not statute regex.
- **OpenSanctions**: hosted API now needs a key (`OPENSANCTIONS_API_KEY`); self-host `yente` keyless. Data is CC-BY-NC.
- **GDELT**: 429s on complex queries → quote the entity name only, ~5s pace. Google News RSS is the keyless workhorse.
- **abuse.ch** URLhaus/ThreatFox: key-walled since 2025-06-30.
- **DMW** SPA is JS-walled, 401s tokenless → API-replay-paginate forwarding the captured auth header.
- **Kaggle ingest**: the repo's own `kaggle/` dir shadows the pip package → strip cwd + `gemma4_comp` from `sys.path`.
- **cp1252 stdout** crashes printing non-ASCII → `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
- **Playwright bundled chromium** crashes on this box → `channel="msedge"`.
- **Swarm rate limits**: big `Workflow` fan-outs trip account session-limit + transient throttle → resume via
  `{scriptPath, resumeFromRunId}` (caches done agents); only merge a resume if its count exceeds the live run.
- **Cluster honesty**: splink EM can't discriminate homogeneous registry names (identical strings scored ~0.12) →
  clustering uses deterministic union + RapidFuzz core-name, NOT splink. Name merges require a shared non-blank
  jurisdiction (else "BLUE LAGOON" false-merges across a ship + an OFAC entry + a trade list).
- **GateGuard** (this repo's hook): blocks the first Bash/session + the first Edit/Write per file → present 4 facts
  (caller, no-dup, data fields, instruction) then retry. CLAUDE.md/AGENTS.md also trip a protected-path WARNING.

---

## 7. License ledger (what you may freely reuse)

**Cleanest (use freely):** **CC0** (GLEIF LEI+RR, OpenOwnership BODS), **US public domain** (DOJ, DOL, OFAC, SAM.gov,
CourtListener, SEC/FEC/Census/Patents-mostly), **OGL** (UK Modern Slavery), **PDDL** (UN/LOCODE), **MIT/Apache/BSD/ISC**
(all the libraries above). **Non-commercial only:** **CC-BY-NC** (OpenSanctions data exports, GFW — fine for a
defensive NGO/regulator framing; underlying gov lists are public domain). **Share-alike on redistribution:** ICIJ,
OSM, Open Supply Hub. **Excluded (not open):** OpenCorporates bulk. **DO-NOT-SCRAPE (ToS/robots forbid AI/bulk):**
BAILII, AustLII, NZLII, WorldLII, SAFLII — route around (UK→Find Case Law, Canada→CanLII API).

---

## 8. Commands cheat-sheet

```bash
PY="%LOCALAPPDATA%\gemma4-testenv\venv\Scripts\python.exe"   # recovery venv; PYTHONUTF8=1
# resolve one registry (propose-only) + list all addressable
$PY scripts/acquisition_cascade.py --registry us_dhs_uflpa
$PY scripts/acquisition_cascade.py --list-registries
# GLEIF / BODS via the cascade (bounded slices)
$PY scripts/acquisition_cascade.py --registry gleif_lei --arg country=AE --arg limit=300
$PY scripts/acquisition_cascade.py --registry openownership_bods --arg bods_url=<https json/jsonl>
# standalone CC0 connectors
$PY scripts/gleif_lei.py --country NP --limit 200 --out reports/entity_kb/gleif_np.jsonl
$PY scripts/gleif_rr.py  --country NP --limit 200          # parent_of edges
$PY scripts/openownership_bods.py --file bods.jsonl --edges # owns_or_controls edges
# screen / link / cluster
$PY scripts/entity_screen.py --query "Sunrise Overseas Manpower"
$PY scripts/cluster_registries.py --cap 2000               # cross-source = high-value
# court / labour / OSINT
$PY scripts/doj_press.py --title "forced labor" --match "pleaded|sentenced|indict"
$PY scripts/dol_whd.py --preview                            # keyless live sample
$PY scripts/dol_whd.py --migrant-only --out reports/entity_kb/dol_whd.jsonl   # needs DOL_API_KEY in .env
$PY scripts/domain_intel.py --domain suspicious-jobs.example
# normalize to the canonical FtM schema (Aleph-loadable)
$PY scripts/ftm_schema.py --in reports/entity_kb/gleif_np.jsonl --out reports/entity_kb/gleif_np.ftm.json
# OpenSanctions metadata harvest -> draft specs
gh repo clone opensanctions/opensanctions ../opensanctions
$PY scripts/harvest_opensanctions_sources.py --clone ../opensanctions --out reports/opensanctions_sources/proposed_sources.yaml
$PY scripts/opensanctions_to_specs.py --category registry,debarment,regulatory --out reports/opensanctions_sources/draft_specs.yaml
# repo/tool discovery
$PY scripts/tooling_scout.py -q "cloudflare bypass" -q "pdf table extraction" --json
# counts
$PY scripts/verify_knowledge_surfaces.py                    # GREP/RAG (separate layer)
```

---

## 9. Honest boundaries — what this is NOT

- **Not wired into the live demo / render app / model path.** It is acquisition/research tooling producing
  **proposed** records under gitignored `reports/`. A curator reviews before any worker-facing use.
- **Not a real-time lookup service.** Bounded slices on demand.
- **Not the trafficking knowledge layer.** GREP 451 rules / RAG 859 docs are a separate subsystem, unchanged here.
- **No DOL_API_KEY held** (the `.env` has Kaggle/Mistral/OpenRouter/Anthropic/OpenAI/HF/Ollama only). The connector
  auto-loads `.env` and works keylessly via `--preview`; the full pull needs the free key added by a human.
- **PyICU/followthemoney library not installed** (can't build on Windows). The FtM *output* is conformant regardless.
- **Counts drift.** Registries update; re-run the resolvers. Verify any number before quoting it elsewhere.

---

*Provenance: this dump synthesizes `docs/entity_intelligence_pipeline.md` (the concise canonical map) and the five
`docs/research/*.md` passes (scraping_tooling_adoptions_2026_06_18, open_datasets_and_tooling_2026_06_18,
aircraft_vessels_ports_relationships_2026_06_19, osint_courtcases_advisories_2026_06_19,
entity_intelligence_tooling_2026_06_13). Every endpoint/repo/count was verified live during 2026-06-13→19; treat
fragility flags as a 2026-06 snapshot and re-verify before relying on them.*
