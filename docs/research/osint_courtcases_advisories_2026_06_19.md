# OSINT tooling, court cases, advisories & MO studies — verified (2026-06-19)

> Three verified research passes (a tooling-scout run + two research agents) answering:
> domain/WHOIS/OSINT tooling; court cases & case databases to mine; and LE advisories /
> typology-MO studies / abuse feeds. Every star/license/endpoint checked live via
> `gh`/WebFetch; unconfirmed items marked **unverified**; real-not-faked. Feeds the
> config resolver, `entity_kb`/`entity_screen`, the `{subject,predicate,object,source,
> weight,qualifier}` edge schema, and the GREP-rule + RAG knowledge layers.

## 1 — OSINT / domain / WHOIS tooling

| Tool | slug | ★ | license | verdict | role |
|---|---|---|---|---|---|
| **whoisit** (RDAP) | meeb/whoisit | 129 | BSD-3 | **ADOPTED ✓** | structured registrant/registrar → `scripts/domain_intel.py` |
| **dnspython** | rthalley/dnspython | 2665 | ISC | **ADOPTED ✓** | NS/MX pivots → infra edges (domain_intel) |
| **asyncwhois** | pogzyb/asyncwhois | 94 | MIT | ADOPT | WHOIS+RDAP fallback for non-RDAP TLDs |
| **ipwhois** | secynic/ipwhois | 593 | BSD-2 | ADOPT | IP→ASN/abuse-contact edge |
| **censys-python** | censys/censys-python | 465 | Apache-2.0 | ADOPT (key) | CT-cert / shared-host pivoting |
| **Phishing.Database** | mitchellkrogza/Phishing.Database | — | **MIT** | **USE-DATA** | ~496k scam domains, keyless `.lst` → adverse_media / GREP host-match |
| **socid-extractor** | soxoj/socid-extractor | 1012 | MIT | PORT | handle → structured entity attrs |

**AVOID (verified blockers):** theHarvester (**GPL-2.0**, CLI-only), recon-ng / holehe / ivre
(**GPL-3.0**), SpiderFoot (MIT but heavy server, stale), amass (**Go** binary), shodan-python
(proprietary-ish + paid), certstream public server (flaky). **URLhaus/ThreatFox (abuse.ch) went
key-walled 2025-06-30** — prefer the MIT Phishing.Database for keyless scam-domain bulk.
**Goldmine:** `jivoi/awesome-osint` (27k★) — PORT its source URLs, don't vendor.

**Built this session — `scripts/domain_intel.py`** (+6 tests): a domain → registrant/registrar +
NS/MX infra enricher emitting the shared edge schema, so scam domains link to the org behind
them and cluster on shared infrastructure, then screen against the registries. Honest about
GDPR: most gTLD registrant fields are "DATA REDACTED" → skipped + a `registrant_redacted` flag;
registrar + DNS still pivot. Live-proven on a real domain (registrar edge + NS/MX, registrant
redacted). RDAP/DNS lookups injectable (offline-tested); live mode via whoisit+dnspython.

## 2 — Court cases & prosecutions (named defendants, MO)

PII rule throughout: **victim names never stored**; named defendant companies/agencies in public
court records are allowed *with a case number*.

| Source | Endpoint | Format | License | Mine |
|---|---|---|---|---|
| **DOJ press releases** | `justice.gov/api/v1/press_releases.json` (HQ + 93 USAOs) | **JSON API**, no key | US public domain | **BUILT ✓** `scripts/doj_press.py` (`--title`/`--match`, offense-tagged docs) |
| **CourtListener bulk** | `com-courtlistener-storage.s3…/bulk-data/` (opinions/dockets/**parties**) | bulk CSV (S3, no auth) | public-domain mark | **FIRST** (REST v4 is 5 req/min — lookups only) |
| **DOL WHD enforcement** | `apiprod.dol.gov/v4/` (Compliance Action) | **JSON API**, free key | US public domain | **best labour entities** — employer + back-wage $ + NAICS + H-2A/B |
| **CTDC synthetic** | `ctdatacollaborative.org/global-victim-perpetrator-synthetic-dataset` | CSV | IOM ToU (attribute) | recruiter/broker role, control means, corridor — **no PII gate (synthetic)** |
| **US TIP Report** | `state.gov/reports/2025-trafficking-in-persons-report/` | PDF/HTML | US public domain | named global prosecutions (LLM extraction) |
| **UNODC SHERLOC** | `sherloc.unodc.org/cld/` (no API) | HTML scrape | UN © (extract+attribute) | `State v. <Defendant>` + MO, ~1k cases |
| **EUR-Lex / CELLAR** | `publications.europa.eu/webapi/rdf/sparql` | SPARQL+REST | **CC-BY-4.0** | cleanest EU API (CJEU labour/THB) |
| **HUDOC (ECtHR)** | `hudoc.echr.coe.int/app/query/results` | JSON+PDF | unverified | Art.4 judgments; use Apache-2.0 `echr-extractor` pattern |
| **UK Find Case Law** | `caselaw.nationalarchives.gov.uk` + API | **LegalDocML XML** + bulk | Open Justice Licence | the sanctioned UK route (Modern Slavery Act defendants) |

**DO NOT SCRAPE (verified ToS/robots forbid AI/bulk):** **BAILII, AustLII, NZLII, WorldLII,
SAFLII** — ideal content, legally off-limits; route around them (UK→Find Case Law, Canada→CanLII
API). EOIR/TRAC skipped (no company names + PII / paywall).

## 3 — Advisories, MO/typology studies (→ GREP + RAG)

| Source | Endpoint | Format | License | Yields |
|---|---|---|---|---|
| **ILO Indicators of Forced Labour** (11) | `ilo.org/.../wcms_203832.pdf` | PDF | © ILO | **1:1 → GREP** (the C029 backbone) |
| **ILO Fair Recruitment / fee taxonomy** | `ilo.org/.../wcms_703485.pdf` | PDF | © ILO | prohibited-fee enum → fee-camouflage + corridor caps |
| **FinCEN FIN-2020-A008** | `fincen.gov/.../Advisory%20Human%20Trafficking%20508%20FINAL_0.pdf` | PDF | US public domain | 20 indicators + 4 typologies + SAR keywords |
| **FATF financial flows (2018)** | `fatf-gafi.org/.../Human-Trafficking-2018.pdf` | PDF | © FATF (attribute) | money-flow red flags → financial GREP rules |
| **Polaris Typology** (25 types) | `polarisproject.org/.../Polaris-Typology-of-Modern-Slavery-1.pdf` | PDF | © Polaris | densest MO taxonomy (recruitment/control/profile) |
| FATF / FinCEN / Europol EMSC / FBI IC3 / DHS Blue / NCA / AUSTRAC / GRETA | (see doc) | PDF/HTML | mixed | RAG narrative + corridor MO |

## 4 — Tabular / enforcement datasets & scam-domain feeds (config resolver)

| Source | Endpoint | Format | License | Note |
|---|---|---|---|---|
| **DOL Sweat & Toil (TVPRA)** | `apiprod.dol.gov/v4/get/sweat_toil_country_goods/...` | JSON API (key) | US public domain | 204 goods × 82 countries × child/forced flag |
| **OpenSanctions CBP-Forced-Labor** | `data.opensanctions.org/datasets/<date>/us_cbp_forced_labor/targets.simple.csv` | CSV/JSON | CC-BY-NC | clean form of the JS-walled CBP WRO list |
| **OpenSanctions UFLPA** | `…/us_dhs_uflpa/targets.simple.csv` | CSV/JSON | CC-BY-NC | 144 entities, daily |
| **DOL OFLC/WHD debarment** | `dol.gov/.../Debarment_List.pdf`, `H1BDebarmentList.xls` | PDF/XLS | US public domain | debarred employers |
| **SAM.gov Exclusions** | `api.sam.gov/entity-information/v4/download-exclusions` | JSON/CSV (key) | US public domain | all active federal exclusions |
| **AU Fair Work litigation / AUSTRAC actions** | `fairwork.gov.au/.../litigation/...`, `austrac.gov.au/.../enforcement-actions` | HTML-table | CC-BY-4.0 | respondent + penalty + outcome |
| **Phishing.Database** | `phish.co.za/latest/ALL-phishing-domains.lst` | TXT | **MIT** | ~496k scam domains, keyless |

## 5 — Built this session + onboard-next

- **Built:** `scripts/domain_intel.py` (whoisit+dnspython → domain entity/infra edges).
- **Built:** `scripts/doj_press.py` — DOJ press releases → offense-tagged prosecution docs
  (live-proven on real forced-labour cases: Onetaste/Daedone, multi-state racketeering, etc.).
- **Built:** `scripts/dol_whd.py` — DOL WHD enforcement (dataset 10362, `api.dol.gov/v4/get/WHD/
  enforcement/json`, **free X-API-KEY**) → employer-violation entities surfacing H-2A/H-2B/H-1B/
  **MSPA**/SRAW + child-labour violation counts. Parser verified on the dataset's keyless preview
  (real rows: Central Avenue Bakery $12,136 back-wages, etc.); only the live pull needs the key.
- **Mine-next:** **OpenSanctions CBP/UFLPA** (fold into `opensanctions_to_specs.py`), then Gemma
  entity extraction over the DOJ docs (defendant↔company↔office edges).
- **GREP-next (indicator PDFs):** ILO 11-indicator + Fair-Recruitment, FinCEN FIN-2020-A008,
  Polaris Typology, FATF 2018 — each yields 10–40 deduped candidate rules citing the source.
- **adverse_media-next:** Phishing.Database (MIT) as a keyless scam-domain feed.

### PDF → GREP + RAG (methodology)
Fetch via the `curl_cffi → Edge` ladder (the `.gov`/FATF/ILO PDFs 403 a plain fetcher) → extract
with `pdfplumber` (born-digital) / `camelot` (tabular debarment lists). **Indicator-dense PDFs**
(ILO/FinCEN/FATF/Polaris/IRIS) → split on the numbered/bulleted indicator list; author a regex
over *paraphrase surface forms* citing the source id (e.g. ILO "document retention" →
`\b(passport|ID|document)s?\b.{0,30}\b(held|confiscat|retain|withh)`, cite `ILO Forced Labour
Indicator 5`) → dedup against the existing rules. **Narrative PDFs** (TIP/GLOTIP/GRETA/EMSC/IC3)
→ chunk → scrub → stage to RAG (propose-only). Tabular enforcement sources are entity *data*, not
regex source.

**License ledger:** public-domain / OGL / CC-BY-4.0 are cleanest (DOJ, CourtListener, DOL,
SAM.gov, EUR-Lex, AU); CC-BY-NC (OpenSanctions) is fine non-commercial; **cite-only / no-scrape**:
BAILII+the LIIs, HTI, TRAC; abuse.ch is now key-walled — use MIT Phishing.Database instead.
