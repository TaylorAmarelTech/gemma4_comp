# Aircraft, vessels, ports & relationship-graph sources — verified (2026-06-19)

> Two verified research passes (aircraft+vessel registries; ports+relationship data).
> Every endpoint was checked via WebSearch/WebFetch; unconfirmed items are marked
> **unverified**. Real-not-faked. Extends the entity-intelligence catalog from
> *entities* to their *registries by asset class* and their *relationships*.
> Already held — not repeated: Global Fishing Watch vessel identity, AU AMSA ships
> (onboarded `au_amsa_ships`), OFAC SDN (incl. vessels), the OpenOwnership BODS + GLEIF
> entity connectors, PH DMW agency→principal job-orders.

## 1 — Aircraft registries (tail number → owner)

| Source | Endpoint | Format | License | Access |
|---|---|---|---|---|
| **AU CASA register** | `casa.gov.au/.../data-files-registered-aircraft` → `acrftreg.csv` | **csv/zip** | public (CASR 47.030) | clean ✅ |
| **OFAC SDN aircraft feature** | `sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML` | xml/csv | US public domain | clean ✅ |
| **OpenSky aircraft DB** | `s3.opensky-network.org/data-samples/metadata/aircraftDatabase.csv` | csv | unlicensed (flag provenance) | clean ✅ |
| US FAA Releasable DB | `registry.faa.gov/database/ReleasableAircraft.zip` | zip (MASTER/ACFTREF…) | US public domain | **Akamai bot-walled** → browser tier |
| Isle of Man (M-) | `ardis.iomaircraftregistry.com/register/search` | html_table | public | best offshore-jet register w/ owner |
| Netherlands register | `data.europa.eu/data/datasets/luchtvaartuigregister` | open data | EU open | per-country (no EU-wide reg exists) |

**Opaque by design (the opacity is itself a signal — don't chase):** Bermuda VP-B, Cayman
VP-C (login), San Marino T7, Aruba P4 (only unofficial third-party lists). ADSBExchange is
now commercial → use OpenSky. EASA has no EU-wide register (national-only).

## 2 — Vessels / boats (IMO/MMSI → flag → owner)

| Source | Endpoint | Format | License | Access |
|---|---|---|---|---|
| **Combined IUU Vessel List (TMT)** | `iuu-vessels.org/Home/Download` | **xlsx** | free, attribute TMT | one file = ALL RFMO IUU lists ✅ |
| **UK FCDO Sanctions List** | `sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv` | csv/xml | **OGL v3** | filter `Group Type=Ship` ✅ |
| **USCG PSIX / CGMIX** | `cgmix.uscg.mil/xml/psixdata.asmx?WSDL` | SOAP/xml | US public | 650k+ vessels; needs a SOAP path |
| **Tokyo MoU APCIS** (detentions) | `apcis.tmou.org/isss/public_apcis.php?Mode=DetList` | html_table + params | public | best PSC-detention pick, paginate/discover ✅ |
| **UN SC Consolidated (1718 vessels)** | `main.un.org/securitycouncil/en/content/un-sc-consolidated-list` | xml | UN public | filter vessel entries ✅ |
| EU Fishing Fleet Register | `vessel-register.oceans-and-fisheries.ec.europa.eu` | export (csv/xml) | EU open | JS SPA; export URL **unverified** |

**Flag-of-convenience opacity (route via aggregators, don't scrape portals):** Liberia
LISCR, Marshall Islands IRI, Palau PISR, Comoros — **no public anonymous vessel lookup**
(client portals only); IMO GISIS + Equasis are **free-login-walled**, no API. These dark-
fleet flags dominate forced-labour-at-sea — absence of a public register is the signal.

## 3 — Ports / infrastructure

| Source | Endpoint | Format | License | Note |
|---|---|---|---|---|
| **UN/LOCODE** (clean mirror) | `github.com/datasets/un-locode/raw/refs/heads/main/data/code-list.csv` | **csv** | **PDDL (public domain)** | port/location codes + coords + `Function` flag — the join key ✅ |
| **World Port Index (NGA Pub 150)** | ArcGIS Hub `arctic-nga.opendata.arcgis.com/datasets/world-port-index` / HDX mirror | csv/geojson | **US public domain** | ~3,700 ports + harbor size/depth/facilities (msi.nga.mil 403s bots) ✅ |
| **GFW Events API** (port visits) | `api-doc.globalfishingwatch.org` + Python client | REST json | free key, CC-BY-NC | dynamic `port_visits` / carrier↔fishing encounters |
| FTZ / SEZ operators | WEPZA / UNCTAD WIR | html/pdf | mixed/paid | **no clean open dataset** — agentic-scrape tier |

Paid/no-free-tier: MarineTraffic, VesselFinder (AIS port-calls). Use GFW (free) or
AISStream/AISHub for raw positions.

## 4 — Relationship graph (agencies ↔ companies ↔ owners) — the high-value layer

A single source-agnostic **edge** shape every connector writes into (propose-only, dedup
on the triple):

```python
{ "subject_id", "predicate", "object_id",   # canonical entity ids
  "source", "weight",                        # provenance + confidence 0..1
  "qualifier": {"share": .., "interest_type": .., "rel_type": .., "start_date": ..} }
```
Predicate vocab: `parent_of`, `owns_or_controls`, `officer_of`, `registered_at`,
`intermediary_of`, `agency_recruits_for`, `operates_port`, `port_visited_by`.

| Source | Endpoint | Edge | License | Status |
|---|---|---|---|---|
| **OpenOwnership BODS** o-o-c | bulk JSONL (`oo-bodsdata.s3…`) | **owns_or_controls** (owner→company, % share) | CC-BY-4.0 *(prior pass said CC0 — verify)* | **BUILT ✓** `openownership_bods.parse_bods_edges` (`--edges`) |
| **GLEIF Level-2 RR** | API `api.gleif.org/api/v1/lei-records/{lei}/{direct,ultimate}-parent-relationship` | **parent_of** (`IS_(ULTIMATELY_)CONSOLIDATED_BY`) | **CC0** | **BUILT ✓** `scripts/gleif_rr.py` (by `--lei`/`--country`; same LEI keyspace as `gleif_lei.py`) |
| **US OFLC** H-2A/H-2B disclosure | `dol.gov/agencies/eta/foreign-labor/performance` | **agency_recruits_for** (employer↔agent) | US public domain | build next — US analogue of DMW job-orders |
| **ICIJ Offshore Leaks** | `offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip` | **officer_of / intermediary_of / registered_at** | ODbL + CC-BY-SA (cite, share-alike) | node+edge CSVs; confirm edge cols on fetch |
| **OpenSanctions** (FtM) | `opensanctions.org/datasets/` `statements.csv` | owns/directorship (reified) | CC-BY-**NC** | consolidated but NC-only free |
| OpenCorporates officers | `api.opencorporates.com` | officer_of | **not open** (paid) | AVOID — fails the open-license constraint |

**Built this turn:** the BODS connector now emits the ownership/control graph
(`person/company --owns_or_controls(share%)--> company`), verified live on the BODS
example package (Jennifer Hewitson-Smith → 100% → Profitech Ltd). The entity side already
existed; this un-skips the `ownershipOrControlStatement` records.

## Top "onboard next" (cleanest machine-readable)

1. ~~GLEIF Level-2 RR~~ **— BUILT** (`scripts/gleif_rr.py`, CC0 parent_of edges on the LEI keyspace).
2. **UN/LOCODE** (PDDL CSV) + **World Port Index** (public-domain CSV/GeoJSON) — port layer.
3. **AU CASA aircraft** (CSV) + **UK FCDO Sanctions** (OGL CSV, ships) + **Combined IUU
   List** (XLSX) — clean asset registries, `csv`/`xlsx` resolver specs.
4. **US OFLC** H-2A/H-2B (agency_recruits_for edges — extends the recruitment graph).
5. **Tokyo MoU APCIS** (html_table + params) — vessel-detention risk, paginate/discover.

License ledger: CC0 / US-public-domain / OGL are the cleanest (GLEIF RR, UN/LOCODE, WPI,
CASA, FCDO, OFLC); CC-BY-SA (ICIJ) inherits on redistribution; CC-BY-NC (OpenSanctions,
GFW) is fine non-commercial. OpenCorporates is not open — excluded.
