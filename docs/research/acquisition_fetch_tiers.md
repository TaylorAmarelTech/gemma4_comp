# Acquisition fetch tiers — why some registries are hard, and how we reach them

> How DueCare pulls public licensed-entity registers, the obstacles each class of
> source throws up, and the escalating ladder of techniques that defeats them.
> Written 2026-06-18 after onboarding ~20 registries; grounded in real sources we
> hit, not theory.

The entity-intelligence pipeline turns *catalogued sources* (pointers in
`configs/duecare/research_monitor/licensed_entity_sources.yaml`) into *real entity
records* (recruiters, employers, lenders, hotels, individuals) that the screening
engine matches a name against. The hard part is rarely parsing — it is **getting
the bytes**. Government data portals range from a plain CSV anyone can `wget` to a
Cloudflare-guarded SPA that fights automation. This doc is the map.

## The ladder (cheapest → most powerful)

Each tier is slower / more fragile / more expensive than the one above it. We
always try the cheapest tier that works and only escalate when blocked.

| # | Tier | Beats | In this repo | Cost |
|---|------|-------|--------------|------|
| 1 | **Plain HTTP** (`urllib`) | most gov CSV / JSON / XLSX / PDF; CKAN & Socrata APIs | `registry_spec._urllib_fetch` | ~0 |
| 2 | **TLS impersonation** (`curl_cffi`, `impersonate=chrome`) | TLS-fingerprint WAFs that 403 a non-browser handshake | `registry_spec._curl_fetch` (auto-fallback) | ~0 |
| 3 | **Real browser fetch** (Playwright/Edge) | JS-rendered SPAs; header/behavioural WAFs; warmup-cookie gating | `browser_scrape.browser_fetch`, spec `fetch_via: browser` | seconds + RAM |
| 4 | **Challenge solving** (FlareSolverr / undetected browser / residential proxy) | Cloudflare *managed challenge*, hCaptcha interstitials | **not built** | seconds–minutes, $ |
| 5 | **Screenshot + vision OCR** (Gemma 4 multimodal) | sites where the HTML is unparseable, image-only, or the data is rendered to canvas/PDF | `llm_scrape.vision_extract` (Gemma 4), `build_synthetic_screenshots` | model tokens |
| 6 | **Agentic LLM browser** (Gemma 4 function-calling) | unknown sites needing discovery + human-like interaction (click/scroll/search) to even reach the data | `agentic_browse.py` (proven live driving Edge) | model tokens |

Tiers 5 and 6 are exactly the "screenshots, HTML analysis, better automation" the
brief calls for — and they **already exist** in the codebase from the scraping
work; this doc ties them to the fetch ladder so the spec engine can escalate into
them.

## The obstacles, by symptom

| Symptom | Cause | Beat it with | Real example |
|---|---|---|---|
| Works in `urllib`, clean CSV/JSON | none — ideal | Tier 1 | data.gov.sg BCA (24k), HK hotels CSV, CO ICA Socrata |
| `403` to urllib, fine in a browser | TLS-fingerprint WAF | Tier 2 | (class of `*.gob.*` portals) |
| Empty shell HTML, data via XHR | client-rendered SPA (DataTables/Nuxt) | Tier 3 (or find the XHR endpoint) | PH DMW (`master-api`, API-replay), BD MRA (ajax JSON in inline script) |
| Gated multi-step flow | cookies + CSRF + POST | Tier 3 with a scripted flow | HK EAA (`disclaimer`/`statement` cookies → token → `result.php`) |
| Date-stamped / multi-file data URL | no stable link | link-discovery (scrape landing page, pick latest) | GB Register of Sponsors, AMSA ships, CA TFWP quarterly |
| `403` even via headless browser | **Cloudflare managed challenge** | Tier 4/5/6 | **MV tour-guides + resort/guesthouse CSVs (UNSOLVED here)** |
| Data only in a rendered image / scanned PDF | no text layer | Tier 5 (vision) | scanned licence PDFs, image-table notices |

## Parsing obstacles (once you have the bytes)

Getting bytes is most of it, but the parsers earned scars too — captured as
regression tests in `registry_parsers`:
- **Decimal values dropped** by an integer-only regex → CN MARA undercounted
  142/167 (scores like `113.5`). Fix: `\d+(?:\.\d+)?`.
- **Descriptive title row** mistaken for the header because its prose contains a
  column word as a substring → CA TFWP. Fix: prefer EXACT cell matches.
- **BOM** on the first header → HK gov CSVs. Fix: strip the leading byte-order mark.
- **Collapsed bilingual columns** (English+Chinese in one text cell) → HK money
  lenders / CN MARA. Fix: split at the first CJK character.
- **Mangled hrefs** (doubled `https://`, concatenated suffix) → AMSA links. Fix:
  keep-from-last-`https://`, truncate after the extension.

## The unsolved case, concretely: tourism.gov.mv

The Maldives Ministry of Tourism publishes exactly what we want — **registered
tour guides (individuals)** plus resort/guesthouse CSVs — but behind a Cloudflare
managed challenge. It `403`s Tier 1 and Tier 2, and Tier 3 (headless Edge with a
warmup navigation + a wait for the challenge to auto-clear, then both
`ctx.request.get` and a direct `page.goto`) still `403`s. Headless browsers are
detectable and the JS challenge is not auto-solving.

Realistic ways through, in increasing order of effort:
1. **Tier 6 agentic browser** — `agentic_browse.py` drives a *real, non-headless*
   Edge session (already proven against DMW). A human-like interactive session is
   far likelier to clear the challenge; the Gemma agent then navigates to the
   download and reports the link.
2. **Tier 4 challenge solver** — route the fetch through FlareSolverr (a headless
   service that solves CF challenges) or an undetected-chromedriver profile, with
   a residential/clean IP. This is the standard production answer.
3. **Tier 5 vision fallback** — if the data renders on screen but resists
   download, screenshot the table and run `llm_scrape.vision_extract` (Gemma 4
   multimodal) to read it. Slowest, but format-agnostic.

None of these fabricate data — they are all ways to obtain the *same official
public bytes* a human browser would. We did **not** ship a broken MV spec; it
waits on wiring one of the above as a `fetch_via:` mode.

## How a spec selects a tier

A `registry_specs.yaml` block already chooses Tiers 1–3 declaratively:

```yaml
fetch_via: browser             # Tier 3 (default omitted = Tier 1, auto-falls back to Tier 2)
warmup_url: https://site/page  # navigate here first to clear a JS gate
discover:                      # link-discovery for dynamic URLs
  page: https://site/dataset
  link_pattern: '...\.csv'
  pick: latest
paginate: {size_param: limit, offset_param: offset, size: 5000}  # CKAN/Socrata
```

Adding Tiers 4–6 is a matter of new `fetch_via:` values (`solver`, `vision`,
`agentic`) that route through the modules listed in the ladder table — the parse
side does not change, because every tier returns the same bytes the parsers
already understand.

## Operating principle

Escalate only as far as the source forces you, prefer the deterministic tiers,
and **never substitute fabricated data for a blocked fetch** — log the block, drop
to the next tier, or leave the source pending. A short verified pull beats a long
invented one. (See also `docs/safe_text_layer.md`, the `10_safety_gate` rule.)
