# Scraping & ingestion tooling — GitHub research and adoption decisions

> 2026-06-18. Three verified GitHub research passes (anti-bot/stealth fetch,
> structured/PDF ingestion, proxy/clean-IP) → concrete ADOPT/PORT/AVOID calls and
> what we wired in. All stars/licenses/dates were pulled live via `gh repo view`
> on 2026-06-18 — not estimates. Pairs with `acquisition_fetch_tiers.md` (the
> escalation ladder this populates).

We build our own thin tools on top of proven libraries rather than taking heavy
frameworks — the box is fragile (no Node, no AGPL, no large model downloads,
Windows + system Edge). The pattern: adopt a focused, permissively-licensed,
pure-Python library for the hard primitive, wrap it behind our config-driven
`registry_spec` / `registry_parsers` so the spec side never changes.

## Adopted this session

| Tool | Slug | License | Role | Status |
|---|---|---|---|---|
| **patchright** | `Kaliiiiiiiiii-Vinyzu/patchright-python` | Apache-2.0 | drop-in Playwright that patches the `Runtime.enable` CDP leak (top 2026 bot signal); used by `browser_fetch` when present | **wired** (guarded import → optional) |
| **camelot** | `camelot-dev/camelot` | MIT | tabular-PDF extraction → `registry_parsers.parse_pdf_table` (`format: pdf_table`); unlocks the ~116 PDF endpoints | **wired** |
| **pdfplumber** | `jsvine/pdfplumber` | MIT | ruleless-PDF fallback behind camelot | installed |
| **curl_cffi** | `lexiforest/curl_cffi` | MIT | TLS/JA3 impersonation; the auto-fallback fetch tier | already in use |

## 1 — Anti-bot / stealth fetch

The 2026 reality: Cloudflare keys on (a) TLS/JA3 fingerprint, (b) the `Runtime.enable`
CDP leak / headless tells, and (c) **ASN/IP reputation**. Different tiers beat
different layers; nothing beats (c) except changing the egress IP (see §3).

- **ADOPT — patchright** (~1.4k★, Apache-2.0, active): pure-pip Playwright fork,
  supports `channel="msedge"`, avoids `Runtime.enable` entirely. The license-clean,
  no-Node way to lower the automation fingerprint. Wired into `browser_fetch`.
- **KEEP — curl_cffi** (5.8k★, MIT): make it the default tier; most registers fall
  to TLS impersonation with no browser at all.
- **ADOPT (selective) — Scrapling** (`D4Vinci/Scrapling`, 64k★, BSD-3): great
  `StealthyFetcher` + retry framework, **but its stealth backend is Camoufox (a
  Firefox download)** → adopt only on a non-fragile host / CI, not the main box.
- **PORT technique only — rebrowser-patches** (Node, no license): the canonical
  `Runtime.enable` fix; consume it *via* patchright, don't vendor it.
- **AVOID here:** FlareSolverr (Docker sidecar; can't solve Turnstile),
  undetected-chromedriver (GPL, stale, Selenium-based), nodriver/zendriver (AGPL),
  cloudscraper (defeated by modern CF), playwright_stealth (abandoned; JS-injection
  is itself a detection vector), camoufox direct (Firefox download), primp (Rust;
  duplicates curl_cffi).

## 2 — Structured ingestion & PDF tables

The biggest untapped data is the **116 catalogued PDF endpoints** and the
CKAN/Socrata/ArcGIS portal families.

- **ADOPT — camelot** (~3.8k★, MIT, *now ships pure Windows wheels* —
  opencv-headless + pypdfium2, no Ghostscript): the PDF-table extractor. Wired as
  `format: pdf_table`. Proven live on the HK CR money-lender PDF (lattice → clean
  `MLR No / English Name / Chinese Name / Expiry` rows). Text-PDF only; scanned PDFs
  route to OCR/vision.
- **ADOPT — pdfplumber** (10.4k★, MIT): fallback for ruleless tables (explicit
  column x-coords) when camelot's `stream` mis-aligns.
- **ADOPT — ckanapi** (`ckan/ckanapi`, MIT) + **sodapy** (`afeld/sodapy`, MIT):
  first-class CKAN Action-API and Socrata SODA clients → stop hand-rolling
  `offset/limit` and `$offset/$limit` per portal. (We already paginate both
  generically; these are the clean upgrade when a portal misbehaves.)
- **PORT — pyesridump** (`openaddresses/pyesridump`, MIT, ~600 LOC): ArcGIS
  FeatureServer paging (`exceededTransferLimit` + OID fallback) → a future
  `format: arcgis`.
- **ADOPT as small utils:** jmespath (declarative JSON field paths — make the JSON
  column map a JMESPath string), selectolax (fast HTML tables if it ever gets hot).
- **AVOID for ingestion:** scrapegraphai (requires py≥3.12; we're 3.11; nondeterministic),
  crawl4ai (browser+litellm+torch-heavy), trafilatura (discards tables — it's for
  the *news/RAG* line, not registers), tabula-py (needs a JVM), datasette (publish,
  not ingest).

## 3 — Proxy / clean-IP (for ASN-reputation blocks like MV)

`tourism.gov.mv` 403s us even with a stealth headed browser because the block is
**ASN/subnet reputation** (datacenter IP), which fingerprinting cannot fix. The
honest landscape:

- **FIRST, $0 — look for the API / open-data backend, or request allowlisting.**
  This is the DMW `master-api.dmw.gov.ph` pattern already in this project. A public
  `.gov` licensed-entity register is public-interest data; an allowlist request from
  a named anti-trafficking project is the cleanest, most durable fix. Try this on MV
  before spending anything.
- **The real technical fix — a cheap PAYG residential proxy** behind a tiny custom
  rotator. Real ISP IPs are scored low-risk by CF. Picks (pricing approx, verify):
  **Evomi** (~$0.49/GB, genuine no-card free trial → start here), **IPRoyal** (1 GB
  non-expiring, ideal for bursty civic scraping), **PacketStream / DataImpulse**
  (strong consent-based sourcing ethics — load-bearing for *this* project). ~$0–5/mo
  at our volume. Integration is just `user:pass@host:port`.
- **Free options — one quick probe each, expect to fail:** Tor (every exit IP is on
  a list CF ingests → usually challenged; `torproject/stem` is the NEWNYM lever,
  curl_cffi via `socks5h://127.0.0.1:9050` keeps TLS impersonation), Windscribe-free
  / ProtonVPN-free (datacenter IPs, brand-flagged). **Never route a CF target through
  Cloudflare WARP** — it egresses Cloudflare's own AS13335, which CF-fronted sites
  block.
- **AVOID — free public-proxy pools entirely:** ~all are datacenter IPs already
  CF-scored high-risk, 95%+ dead in a day, and carry MITM/honeypot risk that is
  unacceptable for an anti-trafficking tool. (Borrow the `jhao104/proxy_pool`
  getter→tester→API *architecture* only, pointed at a paid residential source.)
- **Rotation: write ~15 lines, don't take a dependency** — every middleware lib
  loses to a small provider-agnostic rotator on a fragile Windows box.

### Integration shape (provider-agnostic)
The IP source is what you pay for; the wiring is trivial and identical across
sources — only the egress IP changes, the TLS impersonation stays:
```python
# curl_cffi (any http/https/socks5h proxy):
requests.get(url, proxies={"https": "http://user:pwd@host:port"}, impersonate="chrome")
# Playwright/Edge (note: Chromium ignores inline user:pass and SOCKS-with-auth):
chromium.launch(channel="msedge", proxy={"server": "http://host:port",
                                          "username": "user", "password": "pwd"})
```
Wired as an env-configured proxy (`DUECARE_PROXY`) in the fetch tier so a
residential proxy or Tor can be slotted in without code changes.

## The integrated fetch ladder (after this session)

1. `urllib` → 2. `curl_cffi` (TLS impersonation) → 3. `patchright`/Playwright Edge
(headless) → **`fetch_via: agentic`** headed patchright → 4. *(+ optional
`DUECARE_PROXY` residential IP at any tier)* → 5. screenshot + Gemma-4 vision
(`llm_scrape.vision_extract`) → 6. agentic Gemma-4 browser (`agentic_browse`).

Operating principle unchanged: escalate only as far as the source forces, prefer
deterministic tiers, request official access before fighting IPs, and **never
fabricate a blocked fetch** — log it, drop a tier, or leave it pending.

## 4 — Company-registry / source-list goldmine: OpenSanctions (built)

The highest-leverage find from the company-registry research pass is not a library
but a **curated source list**. `opensanctions/opensanctions` (MIT *code/metadata*;
the consolidated *data* is CC-BY-NC) maintains ~445 per-registry crawler definitions
under `datasets/<cc>/<name>/<name>.yml` across 97 country dirs. Each YAML names a
real official SOURCE — landing `url`, `data.url` + `data.format` endpoint,
`publisher` (with an `official` flag + country), update frequency, and classifying
`tags` (`list.sanction` / `list.pep` / `list.debarment` / `reg.warn` / …). That is a
ready-made directory of government registries and screening lists we can fold into
our own catalog.

**Built — `scripts/harvest_opensanctions_sources.py`** (+10 tests on verbatim
GPPB/GovHK fixtures): reads the metadata YAMLs from a local clone, classifies each
(registry / debarment / sanctions / pep / regulatory / other), maps it to our
catalog-source shape, and writes a **propose-only** staging file under
`reports/opensanctions_sources/` (gitignored). It **never** downloads the CC-BY-NC
entity data — only the source pointers (MIT metadata) — and never touches the live
catalog; merge is the separate explicit `merge_entity_sources.py` step.

Live result against the real clone (2026-06-18): **400 source pointers, 371 with a
usable data endpoint, 347 official** — 49 direct registries/debarment/regulatory
(e.g. *AU Sanctions on Sponsors of Skilled Foreign Worker Visas*, *Brazil CEIS
disreputable/suspended companies*, *Cyprus company registry*, *Czech Business
Register*) plus 199 PEP/sanctions screening lists that feed `entity_screen.py` /
`adverse_media.py`. Run:

```bash
gh repo clone opensanctions/opensanctions ../opensanctions      # ~445 YAMLs
python scripts/harvest_opensanctions_sources.py --clone ../opensanctions --stats
python scripts/harvest_opensanctions_sources.py --clone ../opensanctions \
    --out reports/opensanctions_sources/proposed_sources.yaml   # propose-only
```

**Onboarded as runnable specs (verified live).** The harvest gives `data.url` +
`format` but not the field map (that's in OpenSanctions' `crawler.py`, not the
metadata), so onboarding is: harvest → fetch the endpoint → author the field map
against the *real* response → test it resolves. **9 onboarded** into
`registry_specs.yaml` (= **22,729 entities**), each proven against the live source:

| spec id | entities | what |
|---|---|---|
| `tw_strategic_trade_entities` | 11,655 | TW MOEA strategic high-tech-commodity entity list (official CSV) |
| `si_kpk_business_restrictions` | 7,927 | SI businesses barred from public-sector contracting (KPK JSON) |
| `afdb_debarred` | 1,334 | African Development Bank debarred entities (official HTML table) |
| `us_special_legislative_excl` | 515 | US statutory exclusions — Huawei etc. (crawled Google Sheet CSV) |
| `br_bcb_disqualified` | 426 | BR persons disqualified from senior financial roles (BCB Gepad OData) |
| `us_dod_chinese_military` | 397 | US DoD §1260H Chinese military companies (crawled Google Sheet CSV) |
| `no_nbim_exclusions` | 205 | Norwegian sovereign-fund (NBIM) exclusion list (official HTML table) |
| `ohchr_settlement_companies` | 158 | UN OHCHR settlement-linked business enterprises (crawled Google Sheet CSV) |
| `ph_gppb_blacklist` | 112 | PH suppliers debarred from govt procurement (GPPB CBR JSON) |

All auto-wire into the acquisition cascade (`--registry <id>`; 29 registries total).
Provenance is honest per spec: official-portal (TW/AfDB/NBIM/PH/SI/BR) vs.
OpenSanctions-crawled published Google Sheet (US/OHCHR). The remaining endpoints are
scaffolded as a verification work-queue by **`scripts/opensanctions_to_specs.py`**
(+8 tests; excludes already-promoted endpoints by url so the queue shrinks as we go):
it fills url/format/entity_type/jurisdiction from the harvest and leaves `fields:` an
explicit `TODO` + `_needs_verification: true` (never a fabricated map), writing
propose-only `reports/opensanctions_sources/draft_specs.yaml`. Queue after batch 2:
**332 structured endpoints** (151 html_table, 84 json, 57 csv, 27 xlsx, 13 pdf_table);
**22** registry/debarment/regulatory remain. Probed-but-skipped (no fabrication): AU
ABF / GB PSC bulk / CA / SHU / GE / TJ / FinCEN / DC (JS-rendered or narrative, no
parseable table), GB-disq / GB-FCA / SEC / WorldBank / IADB / Kosovo / EBRD (401/403/
406/500), FR AMF (entity in free text), CY / US-SAM (two-step download), ADB / SK
(empty / needs OData pagination). Promote a draft by fetching it, mapping the keys,
and moving the block into `registry_specs.yaml`.

Adjacent, not yet built: **GLEIF LEI Golden Copy** (CC0 bulk; canonical entity-id to
join registries on) and **nomenklatura / followthemoney** (MIT; entity dedup +
screening data model) — both clean adoptions for the screening side.

## Reusable capability — the tooling scout (built)

So the next "find proven tools/repos for X" pass is a repeatable command, not a
bespoke research run: **`scripts/tooling_scout.py`** (`gh search` across many
queries → score vs these constraints → ranked ADOPT/CONSIDER/AVOID with blocker
flags) driven by the **`tooling-scout` agent** (`.claude/agents/tooling-scout.md`,
invoke via the Agent tool) which gh+web-verifies the top picks and cross-checks this
doc so it never re-pitches what we already adopted.

## 5 — Pre-OCR image enhancement (built, ported from OpenSearch-VL)

`shawn0728/OpenSearch-VL` (222★, Apache-2.0, active — a Qwen3-VL multimodal
deep-search agent recipe) is **AVOID as a stack** for us: Qwen3-VL-centric (we're
Gemma 4), and its Megatron/verl/sglang training needs multi-GPU on 8–32B —
impossible on the box, violates "no large model downloads". But its **tool
environment** is a clean **PORT**: the agent recovers from imperfect inputs with
`crop` / `perspective_correct` / `super_resolution` / `sharpen` *before* reading
them. We had the opposite gap — the process/extraction harness queued blurry, skewed
document photos straight to Gemma-4 vision.

**Built — `scripts/image_enhance.py`** (+16 tests): deterministic, CPU-only,
quality-gated enhancement on the OpenCV camelot already pulls in (no new dep, no
model). `quality_report()` measures blur (variance of Laplacian), skew, resolution,
contrast; `enhance_for_ocr()` applies only what's needed — `deskew` /
`denoise+sharpen` / `clahe` (contrast) / Lanczos `upscale` — plus `crop` and 4-point
`perspective_correct`. Every op returns a new array (immutability) and degrades to a
logged no-op if cv2 is absent. `enhance_b64()` sits exactly at the
`llm_scrape.vision_extract` base64 boundary and is wired in as an **opt-in**
`scrape_page(..., enhance_image=True)` step that records `vision_enhanced_ops` and
can never break the vision path. Live proof on a degraded synthetic scan: skew
−7.2°→0.1°, 460×300→1533×1000, contrast 4.3→13.3. This also enriches the Gemma-4
multimodal + function-calling story: the agent gains `crop`/`enhance` tools to
recover a bad input before answering.

NOTE for a future training pass: OpenSearch-VL's **fatal-aware GRPO** (mask tokens
after a fatal tool failure instead of penalizing the whole rollout) is a good idea
for our agentic trajectory curation; its open SearchVL-SFT-36k / RL-8k datasets
(Apache-2.0) are reference tool-use data, though general-VQA not trafficking.
