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
