# Entity-intelligence tooling catalogue (2026-06-13)

> Compiled by the `intel-tooling-catalog` research swarm (9 web agents x slice, URL-verified, deduped). REAL tools/endpoints/data-sources for deeper migration-world entity intelligence + negative-news screening. Nothing fabricated; `verified` = a swarm agent fetched the URL this session. Provenance for the adverse-media + scraping build.

**106 tools** across 11 categories. Access tiers: {'free': 75, 'freemium': 23, 'api_key': 3, 'paid': 4, 'manual': 1}.

Already adopted in this repo: **GDELT** (scripts/adverse_media.py), **OpenSanctions/yente** (adverse_media, key-gated), **Playwright** (scripts/browser_scrape.py, agentic_browse.py), **curl_cffi** (research monitor). The rest are the build-out backlog.

## Contents

- [negative_news_source](#negative_news_source) (10)
- [news_api](#news_api) (7)
- [sanctions_source](#sanctions_source) (13)
- [court_records](#court_records) (6)
- [backend_endpoint](#backend_endpoint) (15)
- [llm_browser_agent](#llm_browser_agent) (10)
- [playwright_variation](#playwright_variation) (7)
- [browsing_technique](#browsing_technique) (6)
- [scraping_tool](#scraping_tool) (16)
- [osint_tool](#osint_tool) (7)
- [entity_resolution](#entity_resolution) (9)


## negative_news_source

### GDELT DOC 2.0 API  `free` (verified)
Free, keyless REST API over GDELT's global news monitor (~hundreds of thousands of articles/day in 65+ languages, machine-translated to English). Full-text search with Boolean, phrase, domain, country, language, tone, and GKG theme operators. Returns article lists, timelines (volume/tone), tone charts, word clouds, and image collages. The single best free starting point for adverse-media screening of any named entity.

- **URL:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- **Repo:** https://github.com/alex9smith/gdelt-doc-api
- **License/ToS:** GDELT data is '100% free and open' for use including commercial; attribute 'The GDELT Project'. No API key, but be polite (single-threaded, no hammering). Underlying article text is owned by publishers — GDELT returns metadata + URL, you fetch the page yourself.
- **Integrate:** GET https://api.gdeltproject.org/api/v2/doc/doc?query=%22Acme%20Manpower%22%20(trafficking%20OR%20%22forced%20labour%22%20OR%20%22wage%20theft%22)&mode=ArtList&format=json×pan=12m&maxrecords=250&sort=hybridrel . JSON gives articles[] with url,title,domain,seendate,sourcecountry,language,tone. Operators: theme:, domain:, sourcecountry:, sourcelang:, tone<-5 (negative). startdatetime/enddatetime=YYYYMMDDHHMMSS (last ~3mo for DOC). Python: pip install gdeltdoc (alex9smith) — gd.
- **Why:** Negative-news core: query a recruitment agency / employer / clinic name + an exploitation lexicon (trafficking, forced labour, illegal recruitment, debarment, fraud) and rank by negative tone. Keyless = zero onboarding friction for the pipeline; tone score is a built-in adverse-media signal.

### GDELT Global Knowledge Graph (GKG) 2.0 raw files  `free` (verified)
The raw 15-minute CSV stream behind GDELT. Every monitored article is annotated with GKG themes, named persons/organizations/locations, counts, and document-level tone (V2TONE: tone, positive, negative, polarity). Themes are curated taxonomies (CrisisLex, WorldBank, plus GDELT's own) that bucket thousands of phrases under one label — exactly how you catch trafficking/forced-labour coverage that a keyword would miss.

- **URL:** https://www.gdeltproject.org/data.html
- **Repo:** https://github.com/CatoMinor/GDELT-GKG-Themes
- **License/ToS:** Free and open (incl. commercial) with attribution. Article body text remains publisher-owned; GKG stores annotations + URLs, not full text.
- **Integrate:** Master list: http://data.gdeltproject.org/gdeltv2/masterfilelist.txt (cols: size, hash, URL). Pull the *.gkg.csv.zip rows; each 15-min file ~ tens of MB. Tab-delimited; key cols V2Themes, V2Locations, V2Persons, V2Organizations, V2Tone, DocumentIdentifier(=article URL). Filter rows where V2Themes contains your target org name's coverage. Full taxonomy: GET http://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT (theme<TAB>count). Also mirrored to Google BigQuery (gdel
- **Why:** Theme-level recall for exploitation news. Relevant GKG themes include TRAFFICKING, SLAVERY, MOVEMENT_GENERAL/MOVEMENT_FORCED, plus WorldBank WB_* labour/migration themes and CRISISLEX categories — far higher recall than a raw 'trafficking' keyword for screening corridor-specific employers.

### Common Crawl News (CC-NEWS)  `free` (verified)
Free, keyless AWS Open Data archive of worldwide news articles as WARC files, updated daily since 2016. Full raw HTML of articles (not just metadata), so you can build your own historical adverse-media corpus and back-test entity screening over years of coverage.

- **URL:** https://data.commoncrawl.org/crawl-data/CC-NEWS/index.html
- **Repo:** https://github.com/fhamborg/news-please
- **License/ToS:** Hosted under AWS Open Data Sponsorship; Common Crawl Terms of Use permit research and broad reuse. Individual article copyrights remain with publishers — treat extracted text as fair-use snippets / indexing, not redistribution.
- **Integrate:** Path: s3://commoncrawl/crawl-data/CC-NEWS/yyyy/mm/CC-NEWS-yyyymmddHHMMSS-nnnnn.warc.gz (no AWS creds: --no-sign-request, or HTTPS https://data.commoncrawl.org/<path>). List: https://data.commoncrawl.org/crawl-data/CC-NEWS/yyyy/mm/warc.paths.gz . Parse with news-please (pip install news-please; news_please.NewsPlease.from_warc(record)) which extracts title/text/date/source, or warcio for raw records. Filter extracted text for entity name + exploitation lexicon, store hits.
- **Why:** Builds a private, license-clean historical negative-news index for back-testing the screener and for corridors/agencies that current news APIs don't retain. Keyless and bulk — ideal for the offline NGO-deployable story.

### BHRRC Migrant Worker Allegations Database  `freemium` (verified)
Business & Human Rights Resource Centre's structured tracker of publicly reported abuse allegations linked to named companies, classified across ~8 categories / 20+ indicators (forced labour, modern slavery, human trafficking, wage theft, recruitment-fee charging, contract substitution, passport withholding, debt bondage). 747 migrant-worker cases recorded in 2025; updated monthly. Each record links the company and the underlying news source.

- **URL:** https://www.business-humanrights.org/en/big-issues/labour-rights/migrant-workers-in-global-supply-chains/migrant-worker-allegations-tracker-methodology/
- **License/ToS:** BHRRC content is copyrighted; non-commercial research/advocacy reuse is generally permitted with attribution but commercial redistribution needs permission. BHRRC explicitly does NOT independently verify allegations and is English-source-biased — store as 'alleged', not adjudicat
- **Integrate:** No public API and no self-service download link on the methodology page; download/data is request-based ('contact us'). For automated monitoring, scrape the public latest-news allegation pages (e.g. /en/latest-news/) and the Gulf migrant-worker landing page by company/sector; for the structured dataset, request the file from BHRRC and refresh monthly. Match on company name; carry their indicator tags into your risk schema.
- **Why:** Best single curated, company-attributed adverse-media dataset specifically for migrant-worker abuse — directly maps named employer/brand entities to ILO-indicator-tagged allegations, exactly DueCare's screening target.

### Philippines DMW Advisories & Licensed Agency Verification  `free` (verified)
The Philippine Department of Migrant Workers (DMW, successor to POEA) publishes labour advisories and warning issuances that name illegal recruiters, blacklisted/closed agencies, and fraudulent online job schemes, plus a verification surface for licensed land-based agencies with valid job orders. The /archives/v1/issuances/advisories path lists advisory issuances; the main site hosts the licensed-agency lookup.

- **URL:** https://dmw.gov.ph/archives/v1/issuances/advisories
- **License/ToS:** Philippine government public records; no commercial-use license stated. Treat as public-domain government data; cite source + retrieval date.
- **Integrate:** No JSON API. The advisories index is a JS-rendered SPA (WebFetch returned only the app shell), so use Playwright to render and scrape the advisory list + PDFs, then OCR/parse named agency entities. For licensed-agency status, scrape the agency-verification page. Re-crawl daily; diff against prior snapshot to detect new advisories/blacklistings.
- **Why:** PH is the single largest origin corridor; DMW advisories are the authoritative government naming of illegal recruiters and the canonical licensed-agency allowlist for PH-origin recruitment-agency entities.

### GDELT Context 2.0 API  `free` (verified)
Companion to the DOC API that returns the surrounding sentence/snippet of text where your query terms actually appear in each article, not just the article-level match. Lets the pipeline see the exploitation context ('the agency charged workers $4,000 in illegal fees') without fetching every page first.

- **URL:** https://blog.gdeltproject.org/announcing-the-gdelt-context-2-0-api/
- **License/ToS:** Free/open, same GDELT terms; snippets are short fair-use context windows.
- **Integrate:** GET https://api.gdeltproject.org/api/v2/context/context?query=%22Acme+Manpower%22+%22forced+labour%22&format=json×pan=12m&maxrecords=75 . Returns the matched snippet + url + tone per article, so you can pre-rank/triage adverse hits by the actual matched context before spending a Playwright fetch.
- **Why:** Cuts false positives and crawl cost in negative-news triage: read the matched sentence to confirm it's about exploitation by THIS entity before pulling the full article. Keyless.

### BHRRC Gulf Migrant Worker Allegations Tracker  `freemium` (verified)
Region-scoped BHRRC tracker covering the six GCC states (Saudi Arabia, UAE, Qatar, Kuwait, Bahrain, Oman). Records publicly reported cases against named businesses across 8 categories / 20 indicators; downloadable dataset plus browsable tracker, with a methodology explainer. Covers Jan 2022 onward.

- **URL:** https://www.business-humanrights.org/en/big-issues/labour-rights/allegations-of-labour-abuse-against-gulf-migrant-workers/
- **License/ToS:** Same as BHRRC global DB — attribution, non-commercial-friendly, commercial use needs permission; allegations are unverified/'alleged'.
- **Integrate:** Page states 'The data is currently downloadable, along with an explanation of our methodology.' Pull the downloadable file periodically and also scrape the tracker page for new GCC company allegations. Filter by destination country = GCC; join to employer entities in your graph. Same monthly cadence as the global DB.
- **Why:** The Gulf is the dominant destination for BD/NP/LK/IN/PH corridors; this is the densest company-attributed adverse-media source for Gulf-employer entities, which rarely appear in origin-country government feeds.

### GDELT GEO 2.0 API  `free` (verified)
Geographic companion to GDELT: returns news matching a query mapped to the locations mentioned, as GeoJSON. Useful for corridor/destination-aware adverse-media screening (e.g. forced-labour coverage clustered in a specific Gulf or SEA region).

- **URL:** https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/
- **License/ToS:** Free/open, same GDELT terms.
- **Integrate:** GET https://api.gdeltproject.org/api/v2/geo/geo?query=(%22forced+labour%22+OR+trafficking)+sourcecountry:QA&format=geojson×pan=3m . Returns GeoJSON features with location + article count + tone, plottable or joinable to a corridor geofence.
- **Why:** Adds a geographic prior to entity screening — surface where exploitation coverage concentrates along a specific migration corridor, complementing the entity-name DOC query. Keyless.

### Migrant-Rights.org  `free` (unverified)
Independent investigative/advocacy outlet focused exclusively on migrant workers in the Gulf/GCC (kafala abuses, wage theft, recruitment-fee fraud, deaths, employer/agency naming, enforcement gaps). Produces reported stories, data visualisations, and country statistics. The canonical migrant-rights.org domain now 301-redirects to mrrors.org.

- **URL:** https://www.migrant-rights.org/
- **License/ToS:** Editorial content under copyright; quote/attribute for screening evidence, do not redistribute full articles commercially. Respect robots/anti-bot — low crawl rate.
- **Integrate:** Confirmed live via a 301 from migrant-rights.org to mrrors.org, but the site returns HTTP 403 to WebFetch (anti-bot). Use Playwright with a real browser fingerprint (or curl_cffi TLS-impersonation) to fetch; check for a WordPress feed at /feed/ or /en/feed/ for an RSS monitor. Scrape article bodies for entity names; treat as journalistic 'alleged' evidence.
- **Why:** Primary specialist adverse-media source for the Gulf destination side of every South-Asian corridor; surfaces named recruiters/employers and systemic abuse patterns that government feeds suppress.

### ICIJ.org Investigations Feed (cross-border reporting)  `free` (unverified)
International Consortium of Investigative Journalists publishes cross-border investigations and an articles feed covering labour exploitation, trafficking, fraud, and corporate misconduct, often naming companies and intermediaries with structured follow-the-money detail.

- **URL:** https://www.icij.org/
- **License/ToS:** Editorial copyright; quote/attribute for evidence, no full-text commercial redistribution.
- **Integrate:** Monitor the WordPress-backed articles feed (try /feed/ for RSS) and the investigations index; scrape headlines + entity mentions for the screening pipeline. Pair with the Offshore Leaks DB above for structured corroboration. Verify the RSS path before wiring a monitor.
- **Why:** High-credibility long-form adverse-media on entities and networks (incl. labour-supply and trafficking-adjacent fraud) that pre-dates or supplements the Offshore Leaks structured data.


## news_api

### newspaper4k  `free` (verified)
Actively maintained successor to the abandoned newspaper3k for news article discovery + extraction (title, authors, publish date, text, top image, keywords/NLP), with strong multilingual support. Latest v0.9.5 (2026-02-28), MIT.

- **URL:** https://pypi.org/project/newspaper4k/
- **Repo:** https://github.com/AndyTheFactory/newspaper4k
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install newspaper4k. One call: `import newspaper; a = newspaper.article('https://.../story'); a.download(); a.parse(); a.title, a.authors, a.publish_date, a.text`. Use newspaper3k's name only historically — install newspaper4k. For best body-text accuracy, trafilatura still edges it; newspaper4k wins on convenience fields + language coverage.
- **Why:** Quick per-article adverse-media extraction with batteries-included author/date/keyword parsing — useful when screening an entity against a known news URL and you want named-entity-friendly fields without configuring a full crawler.

### NewsAPI.org (/v2/everything)  `freemium` (verified)
Widely-used news search API over ~150k sources with rich Boolean query, date range, language, sources, and domain filters. The de-facto baseline news API; easiest to prototype an adverse-media keyword screen against.

- **URL:** https://newsapi.org/docs/endpoints/everything
- **Repo:** https://github.com/mattlisiv/newsapi-python
- **License/ToS:** Free 'Developer' plan is non-commercial / development only, capped at 100 requests/day, results delayed ~24h, and limited to ~1 month look-back. Commercial + live + historical requires a paid plan. Returns metadata + truncated content; full text is publisher-owned.
- **Integrate:** GET https://newsapi.org/v2/everything?q=%22Acme+Manpower%22+AND+(trafficking+OR+%22illegal+recruitment%22+OR+debarred)&from=2026-05-13&language=en&sortBy=publishedAt&pageSize=100&apiKey=KEY (or header X-Api-Key). Response articles[] {source,author,title,description,url,publishedAt,content}. Python: pip install newsapi-python.
- **Why:** Fast prototype layer for the negative-news keyword screen; the Boolean q is well-suited to '<entity> AND <exploitation lexicon>'. Note non-commercial cap — for production an NGO/commercial deployment must upgrade or prefer GDELT/CC-NEWS.

### news-please  `free` (verified)
News crawler + extractor that composes Scrapy, newspaper and readability, and uniquely can pull historical articles from the CommonCrawl news archive (news-please-commoncrawl). ~2.5k stars, Apache-2.0; install via PyPI (git tags rather than GitHub Releases).

- **URL:** https://github.com/fhamborg/news-please
- **Repo:** https://github.com/fhamborg/news-please
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install news-please. Single article: `from newsplease import NewsPlease; NewsPlease.from_url('https://.../article')` returns title/authors/date_publish/maintext. For archive mining use the CommonCrawl extractor module (heavier, batch-oriented). Pull from PyPI, not GitHub Releases (the repo publishes none).
- **Why:** The path to retrospective negative-news at scale: mine CommonCrawl's multi-year news archive for past mentions of a recruitment agency/employer/broker rather than only crawling live pages — strong for building an adverse-media history on an entity.

### GNews API  `freemium` (verified)
Simple REST news API aggregating 60,000+ sources in 22 languages, with search and top-headlines endpoints. Clean JSON, good language/country filters — a low-friction supplement to GDELT for current adverse-media hits.

- **URL:** https://docs.gnews.io/
- **License/ToS:** Free tier is non-commercial only (and limited requests/day with truncated article content); commercial use requires a paid plan. Article text is publisher-owned.
- **Integrate:** GET https://gnews.io/api/v4/search?q=%22Acme%20Manpower%22%20AND%20(trafficking%20OR%20%22forced%20labour%22)&lang=en&country=qa&from=2025-01-01T00:00:00Z&max=10&apikey=YOUR_KEY . Also /api/v4/top-headlines. Returns articles[] {title,description,content,url,publishedAt,source{name,url}}. Free plan ~100 req/day, content field truncated — use url to fetch full page via Playwright.
- **Why:** Recent-news layer for an entity dossier when you want clean, source-attributed hits without parsing GDELT. Country filter maps to migration corridors (Gulf/SEA destinations).

### Event Registry (NewsAPI.ai)  `freemium` (verified)
News intelligence API with concept/entity-level search (not just keywords): articles are linked to Wikidata concepts and clustered into 'events', with sentiment, source, language, and category filters. Lets you screen by the entity concept rather than fragile name strings.

- **URL:** https://github.com/EventRegistry/event-registry-python
- **Repo:** https://github.com/EventRegistry/event-registry-python
- **License/ToS:** Free registration with limited monthly token allowance; non-commercial/eval on free tier, paid for commercial/high-volume. Article text publisher-owned.
- **Integrate:** pip install eventregistry; er = EventRegistry(apiKey=KEY); q = QueryArticlesIter(keywords=QueryItems.AND(['Acme Manpower','forced labour']), lang='eng', dataType=['news']); for a in q.execQuery(er, sortBy='date', maxItems=200): a has url,title,body,date,source,sentiment. Concept search: keywords can be a Wikidata concept URI for disambiguated entity matching. Raw REST: POST https://eventregistry.org/api/v1/article/getArticles.
- **Why:** Concept/entity resolution reduces false positives on common agency names and links coverage across languages/corridors. Sentiment + event clustering give a richer adverse-media dossier than flat keyword APIs.

### Marketaux News API  `freemium` (unverified)
News API with built-in entity extraction and per-entity sentiment scoring. Although finance-oriented, its entity tagging + sentiment returns make it useful for structured adverse-media signals when the target is a registered/listed company.

- **URL:** https://www.marketaux.com/documentation
- **License/ToS:** Free tier ~100 requests/day for build/test, non-commercial; paid plans for production/commercial. Article text publisher-owned.
- **Integrate:** GET https://api.marketaux.com/v1/news/all?search=%22Acme+Holdings%22+%7C+trafficking&language=en&countries=qa,ae&published_after=2026-01-01&filter_entities=true&api_token=KEY . Returns data[] articles each with entities[] {name,type,sentiment_score} and url. Use entities[].sentiment_score as an adverse-media signal; fetch url for full text. (Docs host returns 403 to generic bots — open in a real browser/with UA.)
- **Why:** Where a screened employer is a listed/registered company, entity-linked negative sentiment is a cleaner signal than raw keyword hits. Secondary to GDELT for general migration-world brokers.

### mediastack API  `freemium` (unverified)
apilayer REST news API over 7,500+ sources across 50 countries / 13 languages with keyword, category, country, language, and date filters. Cheap, simple JSON; a budget supplementary current-news source.

- **URL:** https://mediastack.com/documentation
- **License/ToS:** Free tier ~100-500 requests/month, non-commercial, HTTP-only and no sources/sentiment; paid plans (from ~$10/mo) add HTTPS + commercial use. Article text publisher-owned.
- **Integrate:** GET https://api.mediastack.com/v1/news?access_key=KEY&keywords=Acme%20Manpower,trafficking&countries=qa,ae,sa&languages=en&date=2026-01-01,2026-06-13&sort=published_desc&limit=100 . Returns data[] {title,description,url,source,published_at,country,language}. No full text/sentiment — fetch url for body.
- **Why:** Low-cost breadth across Gulf/SEA destination-country sources for corridor-specific employer screening. Lacks sentiment, so pair with GDELT tone or your own classifier.


## sanctions_source

### OpenSanctions (opensanctions/opensanctions)  `freemium` (verified)
Open database aggregating 250+ international sanctions lists, politically-exposed-persons (PEP) registers, and persons/companies of criminal/economic interest into a single normalized FollowTheMoney dataset. Daily-rebuilt; produces consolidated entities (people, companies, vessels) with sanctions/debarment/crime topics, aliases, IDs, and relationships. This is the upstream DATA + crawler pipeline that feeds yente/nomenklatura.

- **URL:** https://github.com/opensanctions/opensanctions
- **Repo:** https://github.com/opensanctions/opensanctions
- **License/ToS:** Code MIT; DATA is CC-BY-NC 4.0 (NonCommercial). Commercial/production screening REQUIRES a paid OpenSanctions data license — the free bulk data may NOT be used commercially. This is the single most important license gotcha in this slice.
- **Integrate:** Don't scrape — consume the prebuilt FtM data. Free non-commercial: download bulk at data.opensanctions.org/datasets/latest/default/entities.ftm.json (newline-delimited FtM JSON) or targeted/sanctions/peps subsets. For commercial DueCare deployment, buy the data license and either use the hosted API (api.opensanctions.org) or self-host yente. Parse with `pip install followthemoney` + `nomenklatura`.
- **Why:** Core screening dataset for adverse-status checks: an employer/recruitment-agency/broker name can be matched against sanctions, debarment, and crime/PEP entities. Directly relevant to migration-world entities (Gulf labour brokers, shell recruiters) appearing on consolidated lists.

### yente (opensanctions/yente)  `free` (verified)
Self-hostable FastAPI screening service ('data match-making API') over OpenSanctions + arbitrary FtM datasets. Fuzzy entity search, single-record /match scoring, and bulk matching of a whole collection; implements the W3C Reconciliation API spec so it plugs into OpenRefine. Runs fully on-prem as a KYC appliance so no customer/worker data leaves your infra — a strong privacy fit for DueCare.

- **URL:** https://github.com/opensanctions/yente
- **Repo:** https://github.com/opensanctions/yente
- **License/ToS:** MIT (code). Bundling OpenSanctions data for commercial use still needs the OpenSanctions data license; self-hosting the SOFTWARE is unrestricted.
- **Integrate:** Docker: ghcr.io/opensanctions/yente; needs Elasticsearch/OpenSearch. POST /match/{dataset} with {"queries":{"q1":{"schema":"Company","properties":{"name":["Al Noor Manpower"],"country":["ae"]}}}} returns scored candidates; GET /search/{dataset}?q=... for free-text; /reconcile/{dataset} for OpenRefine. Active: v5.4.0 (May 2026).
- **Why:** Lets DueCare run a private sanctions/PEP screen on a laptop or server with zero data egress — exactly the on-device privacy posture the project wants. Can also index your own scraped registry/watchlist as a custom FtM dataset and screen against it.

### OpenSanctions (consolidated sanctions, PEPs, debarment, crime lists)  `freemium` (verified)
Aggregated, deduplicated dataset of 80+ source lists: OFAC SDN + non-SDN, EU consolidated financial sanctions, UN Security Council, UK HMT/OFSI, World Bank debarred, national debarment/wanted lists, and PEP registers. Entities use the FollowTheMoney (FtM) data model with resolved aliases. Offers a hosted match/search API and daily bulk files. This is the single highest-leverage adverse-signal source for screening recruitment agencies, employers, brokers, and their owners.

- **URL:** https://www.opensanctions.org/datasets/
- **Repo:** https://github.com/opensanctions/opensanctions
- **License/ToS:** CC-BY-NC 4.0 for the open data (NON-COMMERCIAL only). Commercial use (incl. most paid SaaS deployment) requires a paid commercial license / API agreement. DueCare as a public-good NGO tool likely qualifies non-commercial, but confirm before any paid/SaaS offering.
- **Integrate:** Bulk (free, NC): GET https://data.opensanctions.org/datasets/latest/index.json then per-collection files, e.g. https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv (tabular) or entities.ftm.json (structured). Default/all-entities collection at .../latest/default/. Match API (paid key): POST https://api.opensanctions.org/match/default with {queries:{q1:{schema:'Company',properties:{name:['ACME Recruitment']}}}}. Compose: load CSV into SQLite/pandas, fuzz
- **Why:** Covers OFAC SDN, EU/UN consolidated, UK HMT, World Bank debarred AND national debarment lists in ONE normalized feed — directly flags sanctioned/debarred recruiters, brokers, and their beneficial owners.

### OpenSanctions API (+ yente self-host)  `freemium` (verified)
Consolidated, de-duplicated database of sanctioned entities, PEPs, and persons/companies linked to crime/debarment, aggregated from 250+ official sources (OFAC SDN, EU, UN, UK HMT, World Bank debarment, Interpol, etc.). The /match endpoint does query-by-example fuzzy entity resolution with risk 'topics' tags; the open-source 'yente' server + bulk data let you run it keyless and offline.

- **URL:** https://www.opensanctions.org/docs/api/
- **Repo:** https://github.com/opensanctions/yente
- **License/ToS:** Data CC-BY-NC 4.0 (free for non-commercial; journalists/activists/academics get free keys). Commercial use requires a paid data license. Self-hosting the open-source 'yente' code is MIT, but the bulk DATA you load into it is still under the NC license for commercial use.
- **Integrate:** Hosted: POST https://api.opensanctions.org/match/default with header 'Authorization: ApiKey YOUR_KEY' (also accepts ?api_key=), body {"queries":{"q1":{"schema":"Company","properties":{"name":["Acme Manpower Services"],"country":["qa"]}}}}. Response ranks candidates with .properties.topics (sanction, role.pep, debarment, crime, sanction.linked). Self-host: docker run ghcr.io/opensanctions/yente + load the daily 'default' dataset bulk export — identical /match + /search API, fu
- **Why:** Debarment + sanctions + crime screening for employers, brokers, and recruiters — World Bank/ADB debarment lists alone catch many bad-actor labour contractors. yente offline mode keeps sensitive migrant-case queries on-prem (no third-party leakage).

### Moov Watchman (moov-io/watchman)  `free` (verified)
High-performance Go sanctions-screening service exposing an HTTP API, a Go library, AND an MCP server. Downloads and indexes OFAC SDN/Consolidated, US CSL, EU consolidated, UK OFSI, UN consolidated, and FinCEN 311 lists (plus OpenSanctions-formatted data) and fuzzy-matches names/addresses/IDs with confidence scores. Apache-2.0, so unrestricted commercial use of the SOFTWARE.

- **URL:** https://github.com/moov-io/watchman
- **Repo:** https://github.com/moov-io/watchman
- **License/ToS:** Apache-2.0 (code). Underlying govt lists (OFAC/EU/UN/UK) are public-domain/open — no NC restriction like OpenSanctions data, making this the cleaner license path for commercial DueCare screening against the core govt watchlists.
- **Integrate:** `docker run moov/watchman` then `GET /v2/search?name=Al%20Noor%20Manpower&type=business&limit=10&minMatch=0.85` → JSON entities with match scores; `/mcp` endpoint for agent use. Active: v0.63.3 (Jun 2026).
- **Why:** A drop-in, commercially-clean sanctions/debarment screen for recruiters/employers against the official OFAC/EU/UN/UK lists without OpenSanctions' NC clause. Lightweight enough to run as a sidecar to the Python pipeline.

### US OFAC Sanctions List Service (SDN + Consolidated direct files)  `free` (unverified)
Authoritative U.S. Treasury source for the Specially Designated Nationals (SDN) list and the Consolidated (non-SDN) list. Published as flat files (CSV, XML, fixed-field, pipe/at-delimited) plus the enhanced XML with richer identifiers and the newer Sanctions List Service (SLS) JSON.

- **URL:** https://ofac.treasury.gov/sanctions-list-service
- **License/ToS:** U.S. Government work — public domain (not copyrighted). Free for commercial and non-commercial use. No API key.
- **Integrate:** Legacy flat files (stable, scriptable): https://www.treasury.gov/ofac/downloads/sdn.csv , .../sdn.xml , .../sdn_enhanced.xml , and consolidated .../consolidated/cons_prim.csv (+ cons_add/cons_alt/cons_comments). Enhanced XML carries DOB/passport/address for stronger matching. Schedule a daily pull; diff against prior snapshot. Authoritative primary source to cite when OpenSanctions flags an SDN hit.
- **Why:** Primary, citable adverse signal for sanctioned brokers/employers/vessels; public-domain so safe to redistribute in DueCare reports.

### US CBP Forced-Labor enforcement (WROs/Findings + UFLPA Entity List)  `free` (unverified)
Two CBP/DHS adverse-signal sets: (1) Withhold Release Orders and Findings naming producers/goods tainted by forced labour, and (2) the UFLPA Entity List (FLETF-maintained) of entities whose goods are presumptively barred from US import under the Uyghur Forced Labor Prevention Act.

- **URL:** https://www.cbp.gov/trade/forced-labor/enforcement
- **License/ToS:** U.S. Government work — public domain. The UFLPA Entity List is published in the Federal Register / DHS site; CBP pages are HTML. No key.
- **Integrate:** WROs/Findings: CBP HTML table (scrape) or OpenSanctions us_cbp_forced_labor (daily CSV/JSON). UFLPA Entity List: DHS https://www.dhs.gov/uflpa-entity-list (HTML/PDF; FLETF additions in the Federal Register, which has a JSON API at federalregister.gov/api/v1/documents.json?conditions[term]=UFLPA). Match company names to flag forced-labour-tainted employers/suppliers.
- **Why:** Direct forced-labour signal — the single most on-mission adverse-media-adjacent dataset for the trafficking/forced-labour use case.

### World Bank Listing of Ineligible (Debarred) Firms & Individuals  `free` (unverified)
Official World Bank Group register of firms and individuals debarred/cross-debarred (under the MDB cross-debarment agreement) for fraud and corruption in Bank-financed projects, including the sanction period. Strong proxy for procurement-integrity risk among contractors/labour suppliers.

- **URL:** https://www.worldbank.org/en/projects-operations/procurement/debarred-firms
- **License/ToS:** World Bank open data / Terms of Use — free to reuse with attribution. No key.
- **Integrate:** No clean official JSON API; the public page is a server-rendered table (Playwright-scrapeable; updates ~every few hours). Easiest path: consume OpenSanctions dataset worldbank_debarred (daily CSV/JSON at data.opensanctions.org/datasets/latest/worldbank_debarred/) and cite the World Bank page as primary. Match on firm name + country + address.
- **Why:** Flags debarred recruitment/construction/agriculture contractors that fund migrant-labour pipelines; cross-debarment widens coverage to ADB/AfDB/EBRD/IADB.

### UK Modern Slavery Statement Registry (CSV bulk download)  `free` (verified)
UK Home Office central registry of mandatory modern-slavery statements (~33k organisations, ~21k unique statements, updated daily). Publishes per-year CSV 'statement summaries' of organisations' answers to standardised modern-slavery questions (policies, due diligence, risk areas, training, KPIs).

- **URL:** https://modern-slavery-statement-registry.service.gov.uk/download
- **License/ToS:** UK GOV.UK Open Government Licence (OGL) — free for commercial use with attribution.
- **Integrate:** Direct annual CSV (no API): https://downloads.modern-slavery-statement-registry.service.gov.uk/publicdownloads/StatementSummaries{YEAR}.csv for 2020-2026. Pull yearly, parse with pandas, key on organisation name; score completeness of the standardised answers as a due-diligence signal. Registry data updates daily.
- **Why:** Maps named companies (incl. those sourcing from high-risk migrant-labour corridors) to their self-declared modern-slavery posture; gaps/weak answers are a structured risk feature, and the entity list seeds an employer/buyer graph.

### Sri Lanka SLBFE Recruitment Agency Registry (+ Suspended/Cancelled list)  `free` (verified)
Sri Lanka Bureau of Foreign Employment public lookup for authorised manpower recruitment agencies — searchable by licence number, agency name, address, district, and destination country. Critically, it also publishes a curated list of TEMPORARILY SUSPENDED or CANCELLED agencies and a 1-5 star Agency Grading System, with dated valid-licence snapshots.

- **URL:** https://applications.slbfe.lk/feb/la/la_main.asp
- **License/ToS:** Sri Lankan government public registry; no commercial-use restriction stated. Cite source + snapshot date (lists are dated).
- **Integrate:** Classic ASP form lookup (no JSON). POST the search form via requests/Playwright; separately scrape the 'temporarily suspended or cancelled agencies' list and the dated valid-licence list. Map valid vs suspended/cancelled to allow/deny + capture the star grade as a risk feature. Daily/weekly diff catches new suspensions.
- **Why:** Rare government source that publishes a de facto debarment list (suspended/cancelled) plus a quality grade — directly actionable negative signals for LK-origin recruitment-agency entities, not just an allowlist.

### EU Consolidated Financial Sanctions List (FSF)  `free` (unverified)
The European Union's consolidated list of persons, groups and entities subject to EU financial sanctions, maintained via the EU Financial Sanctions Files (FSF) database run by the European Commission (FISMA). Distributed as XML/CSV/PDF.

- **URL:** https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions
- **License/ToS:** EU open data — generally reusable; the download itself historically required a free token/registration via the Commission's restricted-token system. Treat as free, attribute the European Commission.
- **Integrate:** Token-based download from the Commission's webgate (FSF) returns full XML; or pull the same content via OpenSanctions (dataset eu_fsf) to avoid the token dance. Cite the EU FSF as the authoritative primary when an EU listing is the signal.
- **Why:** Authoritative EU-side sanctions signal for destination-country employers/agencies operating in EU corridors.

### Bangladesh BMET / BOESL Licensed Recruitment Agency Lists  `free` (unverified)
Bangladesh Bureau of Manpower, Employment and Training (BMET) issues, renews, and monitors recruiting-agency (RA) licences and publishes the licensed-agency list (~2,600+ RAs); BOESL is the state recruiter. Embassy mirrors (e.g. Bangladesh Embassy Riyadh) host downloadable PDF lists of BMET/BOESL-approved agencies.

- **URL:** https://www.bangladeshembassy.org.sa/downloads/listRecruitingA.pdf
- **License/ToS:** Bangladesh government public records; no commercial-use restriction stated. Embassy PDFs are public downloads.
- **Integrate:** BMET's own site (bmet.gov.bd) hosts the live licensed-RA database; the embassy PDF mirrors are easy stable downloads to parse with pdfplumber for name+licence-number rows. Build an allowlist; flag entities not present. Note BD does not publicly publish a blacklist, so derive risk from absence + corroborating adverse media. Verify the live BMET URL before relying on the embassy mirror.
- **Why:** Authoritative allowlist for BD-origin recruitment-agency entities (the largest South-Asian outflow corridor); an agency absent from BMET licensing is itself a high-risk signal for illegal recruitment.

### Nepal DoFE Licensed Recruitment Agencies (~416 RAs)  `free` (unverified)
Nepal's Department of Foreign Employment (DoFE, dofe.gov.np) licenses and regulates ~416 recruitment agencies and publishes licensed-agency information plus blacklisting/action notices against agencies that violate the Foreign Employment Act.

- **URL:** https://dofe.gov.np/
- **License/ToS:** Nepal government public records; no commercial-use restriction stated.
- **Integrate:** No documented JSON API; scrape the DoFE site's licensed-agency listing and the notices/blacklist section with Playwright (Nepali + English). Build allowlist + capture action notices as negative signals. Cross-check the live URL — Nepal gov sites change paths; confirm before crawling.
- **Why:** Authoritative allowlist + enforcement source for NP-origin recruitment-agency entities; Nepal is a major corridor to the Gulf and Malaysia and DoFE periodically publishes agency action/blacklist notices.


## court_records

### CourtListener / RECAP REST API v4 (Free Law Project)  `freemium` (verified)
Largest free database of US case law plus the RECAP Archive of PACER federal court documents (dockets, opinions, parties, attorneys, oral arguments). v4 REST API with search, dockets, opinions, people, and a recap-fetch endpoint that pulls fresh PACER content on demand. Also offers bulk CSV exports and webhooks for new filings.

- **URL:** https://www.courtlistener.com/help/api/rest/
- **Repo:** https://github.com/freelawproject/courtlistener
- **License/ToS:** Underlying court data is largely public domain; CourtListener metadata reuse is permitted. As of May 2026, full programmatic API access is bundled with a Free Law Project membership (donation). Bulk data downloads remain freely available.
- **Integrate:** Base https://www.courtlistener.com/api/rest/v4/ with header 'Authorization: Token <token>'. Search: GET /api/rest/v4/search/?q=%22labor+trafficking%22&type=o . Dockets/parties: /api/rest/v4/dockets/ , /api/rest/v4/people/ . On-demand PACER: POST /api/rest/v4/recap-fetch/ . Rate ~5,000 req/hr (membership-gated now). Bulk: https://www.courtlistener.com/help/api/bulk-data/ (CSV of opinions/dockets/people). Token at /profile/api-token/.
- **Why:** Finds US civil/criminal trafficking, forced-labour, FLSA, and illegal-recruitment cases naming defendant employers/recruiters — citable court-record adverse signal.

### Indian Kanoon API (Indian case law & statutes)  `freemium` (verified)
Search API over 1.4M+ Indian laws and judgments (Supreme Court, 24 High Courts, 17 tribunals). Returns search results, full documents, and document fragments as JSON. India is a major migrant-labour origin corridor.

- **URL:** https://api.indiankanoon.org/
- **License/ToS:** Pay-per-call with credits; Rs 500 free trial on signup and up to Rs 10,000/month free for verified non-commercial use cases (admin-approved). Commercial use is paid. See https://api.indiankanoon.org/terms/.
- **Integrate:** POST to https://api.indiankanoon.org/search/?formInput=<query>&pagenum=0 and https://api.indiankanoon.org/doc/<docid>/ with header 'Authorization: Token <token>'. Apply for a key on the site; request the non-commercial allowance for an NGO tool. Search e.g. 'emigration act fraud recruitment agent' to find named-agent judgments.
- **Why:** Origin-corridor court signal — Emigration Act / illegal-recruitment / bonded-labour judgments naming Indian recruiting agents and sub-agents.

### CanLII API (Canadian case law & legislation metadata)  `api_key` (verified)
Read-only REST API over the Canadian Legal Information Institute collection: case databases, decision metadata, citators, and legislation across all Canadian jurisdictions. Returns JSON.

- **URL:** https://github.com/canlii/API_documentation
- **Repo:** https://github.com/canlii/API_documentation
- **License/ToS:** Free API key granted on request (CanLII reviews scope; research/NGO use favoured). Reuse governed by CanLII terms — metadata access, not bulk redistribution of full texts.
- **Integrate:** GET https://api.canlii.org/v1/caseBrowse/en/?api_key=KEY (list databases) then /v1/caseBrowse/en/{databaseId}/?api_key=KEY and /caseCitator/ for citations. Request a key via the CanLII feedback form (https://www.canlii.org/en/feedback/feedback.html) describing the project. API gives metadata/links; fetch decision text from the returned URLs.
- **Why:** Canadian corridor — surfaces immigration-consultant fraud, TFW-program abuse, and forced-labour decisions naming employers/recruiters operating into Canada.

### PACER (US federal courts) via RECAP Fetch  `paid` (unverified)
The authoritative US federal court records system (district, appellate, bankruptcy). Primary source behind RECAP. Paid per-page ($0.10/page, capped), but DueCare can pull individual dockets/documents through CourtListener's recap-fetch rather than scraping PACER directly.

- **URL:** https://pacer.uscourts.gov/
- **License/ToS:** Public court records; PACER charges access fees ($0.10/page, $3.00/document cap; waived under $30/quarter). Documents themselves are public domain once retrieved.
- **Integrate:** Don't scrape PACER directly. Use CourtListener POST /api/rest/v4/recap-fetch/ with your PACER credentials to fetch a docket/PDF (cost billed to your PACER account, then mirrored free into RECAP). For bulk discovery use CourtListener search first; only spend PACER fees on the specific docket you need to cite.
- **Why:** Authoritative federal docket source for citing the exact trafficking/forced-labour case and defendant entity in a DueCare risk report.

### BAILII (British & Irish Legal Information Institute)  `free` (unverified)
Free repository of UK and Ireland case law and legislation (incl. Employment Tribunal and EAT decisions where published). No official API; HTML site with stable per-case URLs, suitable for targeted Playwright fetches.

- **URL:** https://www.bailii.org/
- **License/ToS:** Free access for research/personal use; BAILII terms PROHIBIT systematic/bulk crawling and commercial redistribution. Use targeted, rate-limited fetches and cite, do not mirror.
- **Integrate:** No API — use the search at https://www.bailii.org/cgi-bin/lucy_search_1.cgi?query=... and fetch individual case pages (e.g. /ew/cases/EWHC/...). Respect robots.txt, throttle hard, fetch only specific cases you cite. Pair with a Google/Bing site:bailii.org query to find candidates before fetching.
- **Why:** UK corridor — labour-exploitation, Modern Slavery Act, and gangmaster/employment-tribunal decisions naming UK employers and labour providers.

### AustLII (Australasian Legal Information Institute)  `free` (unverified)
Free database of Australian (and NZ via NZLII) case law, legislation, and tribunal decisions, including Fair Work and migration matters. HTML site with stable URLs and a documented search; no key.

- **URL:** https://www.austlii.edu.au/
- **License/ToS:** Free for non-commercial research; AustLII terms restrict bulk/automated harvesting and commercial reuse. Targeted fetch + citation only. Some bulk access available via formal data-access agreement.
- **Integrate:** No open REST API. Use the Sino search front-end: https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?query=<terms>&method=auto and fetch returned case URLs (e.g. /cgi-bin/viewdoc/au/cases/cth/FCA/...). Throttle and obey robots. For systematic use, request a data agreement rather than scraping at scale.
- **Why:** Australia/NZ corridor — Fair Work underpayment, migration-agent misconduct, and forced-labour cases naming sponsors/employers of temporary migrant workers.


## backend_endpoint

### GDELT DOC 2.0 API  `free` (verified)
Full-text search API over a rolling 3-month window of worldwide online news in 65+ languages, with article-list, timeline, and tone modes. Keyless, JSON output. Ideal for adverse-media / negative-news screening of named entities (recruitment agencies, employers, brokers).

- **URL:** https://api.gdeltproject.org/api/v2/doc/doc
- **Repo:** https://github.com/alex9smith/gdelt-doc-api
- **License/ToS:** GDELT is free for any use including commercial; attribution requested. No API key. Soft rate limits (recommend <=1 req/sec, exponential backoff on 429).
- **Integrate:** GET, returns JSON directly: https://api.gdeltproject.org/api/v2/doc/doc?query=%22Acme%20Manpower%22%20(trafficking%20OR%20%22forced%20labour%22)&mode=artlist&format=json×pan=3m&maxrecords=250&sort=datedesc . Params: query (supports quotes, OR, domain:, sourcelang:, sourcecountry:), mode (artlist|timelinevol|tonechart), format=json, timespan (e.g. 1w/3m/24h), maxrecords (max 250), sort=datedesc|relevance. requests.get(url, params={...}).json(); paginate by narrowing timespan s
- **Why:** Primary negative-news engine: search '"Acme Manpower" (trafficking OR "forced labour" OR "wage theft" OR "illegal recruitment")' across global press without paying a news API. 3-month rolling window means it catches current adverse media; pair with the 15-min-updated GKG/events files for historical 

### OpenSanctions API (api.opensanctions.org) + yente self-host  `freemium` (verified)
Consolidated sanctions, PEP, debarment and watchlist entity graph (FollowTheMoney schema) with /search/{scope}, /match/{scope} (bulk fuzzy entity matching), and /entities/{id} endpoints. The open-source 'yente' server (MIT) can run the same API on-prem so no entity data leaves your infra.

- **URL:** https://api.opensanctions.org/openapi.json
- **Repo:** https://github.com/opensanctions/yente
- **License/ToS:** Software (yente) MIT. DATA is free for non-commercial / journalists / academics / anti-corruption only; commercial use requires a paid bulk-data license. Hosted API needs an API key. CRITICAL: a defensive NGO/regulator tool is fine non-commercially, but a commercial DueCare deplo
- **Integrate:** Hosted: GET https://api.opensanctions.org/search/default?q=Acme+Manpower with header 'Authorization: ApiKey <key>'. Bulk screening: POST https://api.opensanctions.org/match/default with JSON {"queries":{"q1":{"schema":"Company","properties":{"name":["Acme Manpower"],"country":["ph"]}}}}. Self-host: docker compose up yente + Elasticsearch, then point at http://localhost:8000; full OpenAPI at /openapi.json. Bulk FtM data also downloadable as JSON/CSV from opensanctions.org/data
- **Why:** Single best keyless-to-cheap source for sanctions + debarment + PEP screening of employers/brokers/clinics. Includes us_sam_exclusions (US procurement debarment) as a dataset, so you get federal exclusions normalized into the same entity model as global sanctions and PEPs.

### SAM.gov Exclusions API (federal debarment)  `api_key` (verified)
Official US System for Award Management exclusions/debarment list: firms, individuals, vessels barred from federal awards. JSON or CSV, filterable by name, classification, exclusion type, country/state. Companion Entity Extracts API offers bulk file download.

- **URL:** https://open.gsa.gov/api/exclusions-api/
- **License/ToS:** US Government public-domain data; free. Requires a free api.data.gov / SAM.gov API key (~10 business days for a system account; DEMO_KEY works for testing). Public extracts available without per-entity auth.
- **Integrate:** GET https://api.sam.gov/entity-information/v4/exclusions?api_key=<KEY>&q=Acme&classification=Firm&format=JSON&page=0&size=100 . Params: q (free text AND/OR/wildcard), classification (Firm|Individual|Vessel|Special Entity Designation), exclusionType, country (3-char), stateProvince, exclusionName, page/size. For full nightly snapshot use the Entity/Exclusions Extracts API (open.gsa.gov/api/sam-entity-extracts-api/) which returns a downloadable ZIP rather than paged JSON.
- **Why:** Authoritative debarment signal for any entity touching US contracts (clinics, staffing firms, suppliers in supply-chain due diligence). 'Ineligible (Proceedings Completed)' and 'Prohibition/Restriction' flags are direct risk inputs for the screening rubric.

### CKAN Action API (data.gov / data.gov.uk / hundreds of national portals)  `free` (verified)
Standard JSON API exposed by every CKAN-powered open-data portal. /api/3/action/package_search to discover datasets, package_show for metadata+resource URLs, and datastore_search to query tabular data rows directly without downloading the file.

- **URL:** https://docs.ckan.org/en/2.9/api/
- **Repo:** https://github.com/ckan/ckan
- **License/ToS:** CKAN software is AGPL; the DATA terms vary per portal (most US/UK/EU gov portals are open / public-domain). datastore_search needs no key on most public instances.
- **Integrate:** Discover: GET https://catalog.data.gov/api/3/action/package_search?q=recruitment+agency+license&rows=50 . Resolve resources: GET .../api/3/action/package_show?id=<dataset-id>. Query rows live: GET .../api/3/action/datastore_search?resource_id=<rid>&q=Acme&limit=100 (also supports filters={...} and SQL via datastore_search_sql). All return {success, result:{records|results}}. Note: data.gov's hosted catalog also at https://api.gsa.gov/technology/datagov/v3/action/package_searc
- **Why:** One client pattern unlocks bulk-download + row-level query across data.gov, data.gov.uk, EU member-state portals, and many labor-ministry / licensed-recruiter registries that publish via CKAN. Find a 'licensed recruitment agencies' dataset once, then datastore_search it live for entity verification.

### USASpending.gov API + bulk_download endpoint  `free` (unverified)
Keyless REST API over all US federal awards/contracts/grants. /api/v2/search/spending_by_award/ for filtered queries and /api/v2/bulk_download/awards/ to generate large CSV/ZIP extracts by agency, award type, and date range.

- **URL:** https://api.usaspending.gov/docs/endpoints
- **Repo:** https://github.com/fedspendingtransparency/usaspending-api
- **License/ToS:** US Government public-domain; no API key, no auth. Open-source server (CC0/public domain) at fedspendingtransparency/usaspending-api.
- **Integrate:** POST JSON, not GET: POST https://api.usaspending.gov/api/v2/search/spending_by_award/ with body {"filters":{"recipient_search_text":["Acme Manpower"],"award_type_codes":["A","B","C","D"]},"fields":["Award ID","Recipient Name","Award Amount"],"limit":100}. Bulk: POST https://api.usaspending.gov/api/v2/bulk_download/awards/ -> returns a file_url to poll. Recipient profile lookup: GET /api/v2/recipient/duns/{uei}/. Composes cleanly with requests + a Playwright fallback only if C
- **Why:** Maps the contract/funding footprint of an employer or staffing agency: who they do business with, dollar volume, recipient hierarchy (UEI/DUNS). Cross-reference recipients against SAM exclusions and adverse media to surface 'debarred yet still funded' or shell-recipient patterns.

### SQLite FTS5  `free` (unverified)
Built-in full-text search engine shipped inside SQLite itself (FTS5 virtual tables) — BM25 ranking, prefix/phrase/NEAR queries, custom tokenizers, highlight/snippet functions. Zero external service, zero extra dependency beyond the stdlib sqlite3 module.

- **URL:** https://www.sqlite.org/fts5.html
- **License/ToS:** Public Domain (SQLite)
- **Integrate:** Stdlib: CREATE VIRTUAL TABLE docs USING fts5(entity, title, body, url UNINDEXED); INSERT then SELECT ... FROM docs WHERE docs MATCH 'forced NEAR labour' ORDER BY bm25(docs). Coexists in the same DB as reader/changedetection state. Note: FTS5 + sqlite-vec can live in one DB for hybrid keyword+vector retrieval.
- **Why:** The cheapest possible searchable index for collected articles + registry rows + screening notes. A propose-only monitor that already keeps state in one SQLite file gets keyword retrieval ('forced labour' near an entity name, debarment terms) for $0 and no ops — ideal before reaching for Meilisearch.

### Apprise  `free` (verified)
Unified Python notification library — one URL syntax to push alerts to 100+ services: Slack, Telegram, Discord, email/SMTP, SMS gateways, Matrix, Microsoft Teams, generic JSON/form webhooks, and more. CLI + library, async delivery, attachment support.

- **URL:** https://github.com/caronc/apprise
- **Repo:** https://github.com/caronc/apprise
- **License/ToS:** BSD-2-Clause (OSS)
- **Integrate:** pip install apprise. a = apprise.Apprise(); a.add('slack://tokA/tokB/tokC/#alerts'); a.add('tgram://bottoken/chatid'); a.notify(title='New adverse media: ABC Manpower', body=summary_url). Same URLs work as changedetection.io notification_urls. v1.11.0 (May 2026).
- **Why:** The alerting fan-out for a propose-only monitor: when a new high-risk negative-news hit or registry change clears review, push it to the reviewer's channel of choice with one call. Also the notification backend changedetection.io already speaks natively (drop an apprise:// URL into a watch).

### US DOL Wage & Hour Division (WHD) enforcement data API  `api_key` (unverified)
Every concluded WHD compliance action since FY2008: employer name/address, NAICS, whether FLSA/H-2A/H-2B/MSPA violations were found, back-wages owed, employees due back wages, and civil money penalties. The authoritative US wage-theft / illegal-recruitment enforcement signal for employers of migrant labour.

- **URL:** https://developer.dol.gov/wage-and-hour-division/whd-compliance/
- **License/ToS:** U.S. Government work — public domain data. Free API key required (rate-limited). Reusable commercially and non-commercially.
- **Integrate:** GET https://api.dol.gov/V1/Compliance/WHD/<dataset>?format=json with header 'X-API-KEY: <key>' (or KEY query param); responses default XML, send Accept: application/json. Free key at https://devtools.dol.gov/developer . Bulk alternative: enforcedata.dol.gov whd_whisard tables (CSV). Filter by naic_cd / h2a / h2b flags to surface migrant-worker cases; join employer name to your entity graph.
- **Why:** Names specific employers caught in wage theft and H-2A/H-2B visa-program violations — a core DueCare adverse signal that adverse-media often misses.

### sqlite-vec  `free` (verified)
Vector-search SQLite extension in pure C, no dependencies — stores float/int8/binary vectors in vec0 virtual tables and does KNN with MATCH ... ORDER BY distance. Runs in-process inside the same SQLite DB as your relational + FTS5 data. Loadable from Python.

- **URL:** https://github.com/asg017/sqlite-vec
- **Repo:** https://github.com/asg017/sqlite-vec
- **License/ToS:** Apache-2.0 / MIT dual (OSS)
- **Integrate:** pip install sqlite-vec; import sqlite_vec; db.enable_load_extension(True); sqlite_vec.load(db). CREATE VIRTUAL TABLE vec_docs USING vec0(embedding float[384]); query SELECT rowid, distance FROM vec_docs WHERE embedding MATCH ? ORDER BY distance LIMIT 10. CAVEAT: pre-v1 (v0.1.9, Mar 2026) — 'expect breaking changes', pin the version.
- **Why:** Lets the monitor do semantic retrieval ('articles semantically about wage-withholding / passport confiscation near this entity') over embeddings WITHOUT a separate vector server — keeps the whole propose-only pipeline as one cheap SQLite file alongside FTS5 keyword search for hybrid retrieval.

### arq  `free` (verified)
Minimal asyncio + Redis job queue and RPC for Python. Tiny footprint, workers run inside the async event loop, jobs are coroutines, supports delayed jobs, retries/abort, result storage, and built-in cron jobs (no separate scheduler/Beat process).

- **URL:** https://github.com/python-arq/arq
- **Repo:** https://github.com/python-arq/arq
- **License/ToS:** MIT (OSS)
- **Integrate:** pip install arq. Define async def screen(ctx, entity): ...; class WorkerSettings: functions=[screen]; cron_jobs=[cron(poll_feeds, hour={0,6,12,18})]; run with `arq module.WorkerSettings`. Enqueue via redis.enqueue_job('screen', entity). NOTE: repo is in maintenance-only mode (stable, not actively featured) — fine for this use, but factor it in.
- **Why:** Right-sized scheduler/worker for an I/O-bound monitor (fetch feeds, hit registry endpoints, call screening APIs) — its native cron() means the whole 'poll every N hours, enqueue per-entity screening jobs' loop needs only Redis, not a Celery+Beat stack. Async fits Playwright/httpx fan-out.

### Meilisearch  `freemium` (unverified)
Lightweight, ready-to-use open-source search engine (Rust). Sub-50ms typo-tolerant full-text search with filtering, faceting, geo, and multi-language out of the box — install, create index, push JSON docs, query. Single binary or Docker; REST API.

- **URL:** https://github.com/meilisearch/meilisearch
- **Repo:** https://github.com/meilisearch/meilisearch
- **License/ToS:** MIT self-host (no restrictions); optional paid Meilisearch Cloud
- **Integrate:** docker run -p 7700:7700 getmeili/meilisearch. Python: pip install meilisearch; client.index('entities').add_documents([...]); index.search('manpower', {'filter':'risk>=0.7 AND corridor="ID-MY"'}). Define filterableAttributes once. Self-host stays free under MIT.
- **Why:** When the corpus of collected adverse-media + registry records outgrows SQLite FTS5 and a reviewer needs typo-tolerant faceted search ('show high-risk hits, sector=fishing, corridor=ID-MY, last 30d'), Meilisearch is the low-ops upgrade — facets map directly onto the risk/sector/corridor labels DueCar

### LanceDB  `freemium` (verified)
Embedded (in-process, serverless) multimodal retrieval library on the Lance columnar format. Vector similarity + full-text + SQL filtering in one engine, persists to local disk or S3, scales to large corpora with IVF_PQ indexing and a low memory footprint. No server to run.

- **URL:** https://github.com/lancedb/lancedb
- **Repo:** https://github.com/lancedb/lancedb
- **License/ToS:** Apache-2.0 (embedded OSS); optional managed LanceDB Cloud
- **Integrate:** pip install lancedb. db = lancedb.connect('./lance'); tbl = db.create_table('news', data); tbl.search(query_vec).where('risk > 0.7').limit(10).to_pandas(). Embedded, zero-copy Arrow. v0.33.x beta (Jun 2026) — Python API still pre-1.0, pin it.
- **Why:** The next tier up from sqlite-vec when embeddings + metadata filtering + FTS need to coexist at scale for entity intelligence (millions of article chunks across many corridors) while staying ops-free — fits DueCare's local-first, propose-only posture (runs on the same box, no managed DB bill).

### GitHub Actions scheduled workflows (cron)  `free` (unverified)
Free serverless cron for public repos: a workflow with `on: schedule: cron` runs on GitHub-hosted runners at no cost (public repos), with state persisted back by committing the updated crawl-state/SQLite/JSON to a branch (the 'stateful action' pattern) or via artifacts. The repo diff becomes a built-in human review queue.

- **URL:** https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule
- **License/ToS:** GitHub Actions ToS (free for public repos; 2,000 min/mo private free tier)
- **Integrate:** In .github/workflows/monitor.yml: `on: { schedule: [{cron: '0 */6 * * *'}] }`; job checks out, runs the python monitor, then `git add state.db proposals/ && git commit && git push` (or actions/upload-artifact). CAVEATS: min interval ~5-15 min, scheduled runs auto-disable after 60 days repo inactivity, and the trigger can lag minutes under load — design idempotent + commit-state.
- **Why:** Lets DueCare run the entire entity+news monitor continuously for $0 infra: scheduled job fetches feeds/registries, screens, and opens a PR / commits proposed alerts — perfectly matching the propose-only, human-in-the-loop posture (a reviewer approves the PR diff). No server, no Redis to host.

### EU Open Data Portal (data.europa.eu) REST + SPARQL endpoints  `free` (unverified)
Pan-European catalogue aggregating 1M+ datasets from EU institutions and member states, queryable via a REST search API and a DCAT SPARQL endpoint for precise metadata graph queries; legacy CKAN API still available.

- **URL:** https://data.europa.eu/euodp/en/developerscorner
- **License/ToS:** Predominantly CC-BY 4.0 / open; free, no key. Reuse permitted including commercial with attribution per each dataset's stated license.
- **Integrate:** SPARQL: POST/GET https://data.europa.eu/sparql?query=<urlencoded DCAT query>&format=application/sparql-results+json . REST search base: https://data.europa.eu/api/hub/search/ (returns JSON facets + dataset hits). Legacy CKAN: https://data.europa.eu/api/hub/repo/ . Use SPARQL when you need to filter by publisher/theme (e.g. 'labour') precisely; use REST search for keyword discovery.
- **Why:** Gateway to EU/member-state registries relevant to migrant-worker corridors entering Europe: posted-worker enforcement data, company registers (BRIS), labour-inspection and sanctions lists published by national authorities.

### RQ + Celery (heavier queue alternatives)  `free` (unverified)
RQ (Redis Queue) is a simple synchronous Redis-only job queue (scheduling via the separate rq-scheduler package). Celery is the mature, battle-tested distributed task queue with multiple brokers, Celery Beat scheduling, rate-limiting, retries, and Flower monitoring; benchmarks show higher sustained throughput/lower p95 latency than RQ.

- **URL:** https://github.com/rq/rq
- **Repo:** https://github.com/rq/rq
- **License/ToS:** BSD (RQ) / BSD (Celery) — both OSS
- **Integrate:** RQ: pip install rq; q.enqueue(screen, entity); run `rq worker`; schedule via rq-scheduler. Celery: pip install celery[redis]; @app.task screen; beat_schedule for cron; run `celery -A app worker -B`; monitor with Flower. Both Redis-backed so they slot into the same infra as arq.
- **Why:** Fallback queue options if the monitor's work is CPU-bound/synchronous (RQ — simplest) or grows into multi-worker workflow orchestration with rate-limited external-API calls and monitoring (Celery + Beat + Flower). Listed so the choice is honest: arq for async-light, Celery only when its workflow pri


## llm_browser_agent

### browser-use  `free` (verified)
Python framework that turns any LLM into an autonomous web agent: the model is given a serialized DOM + screenshot and emits click/type/scroll/extract actions over Playwright until a natural-language goal is met. Highest-adoption open agent (98.7k stars), 89% on WebVoyager. Has a structured-output/extraction mode that returns Pydantic-typed JSON from a page.

- **URL:** https://github.com/browser-use/browser-use
- **Repo:** https://github.com/browser-use/browser-use
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install browser-use ; pip install 'browser-use[cli]'. Point at Gemma via Ollama: from browser_use import Agent, ChatOllama; agent = Agent(task='search this registry for X and return status', llm=ChatOllama(model='gemma3')) ; await agent.run(). Composes directly with your Playwright pipeline (it drives Playwright under the hood; you can pass an existing browser context). Gotcha: small local models are markedly weaker at long action chains than GPT-4o/Claude — keep tasks sh
- **Why:** Best-fit for DueCare's hardest registry targets: JS-walled / login-gated / paginated agency & employer directories (Gulf labour-ministry portals, DMW/POEA licensee lists, court-record search UIs) where a static scraper breaks. The agent navigates 'search agency name -> open result -> read license st

### Crawl4AI (LLMExtractionStrategy)  `free` (verified)
Open-source async Playwright crawler purpose-built for LLM pipelines: fast crawl -> clean Markdown, plus an LLMExtractionStrategy that runs structured (schema-driven) or free-form extraction through LiteLLM, so ANY provider including local Ollama works. Also has a no-LLM JsonCssExtractionStrategy for cheap deterministic extraction. 68.4k stars, very active.

- **URL:** https://github.com/unclecode/crawl4ai
- **Repo:** https://github.com/unclecode/crawl4ai
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install -U crawl4ai && crawl4ai-setup. Local Gemma: from crawl4ai import LLMConfig, LLMExtractionStrategy; cfg=LLMConfig(provider='ollama/gemma3', api_token='no-token'); strat=LLMExtractionStrategy(llm_config=cfg, schema=MyEntity.model_json_schema(), extraction_type='schema'). Run inside AsyncWebCrawler(...).arun(url, config=CrawlerRunConfig(extraction_strategy=strat)). v0.8.x patched a Docker-server SSRF — if you self-host the API server, pin >=0.8.9.
- **Why:** The workhorse middle layer for DueCare: bulk-crawl public registry pages, NGO debarment lists, and adverse-media articles into Markdown, then LLM-extract entity fields (agency name, license no, address, status, sanction reason) into JSON with a local Gemma so sensitive screening text never leaves th

### ScrapeGraphAI  `free` (verified)
Python library that builds LLM + graph-logic scraping pipelines: you give a prompt ('extract all recruitment agencies with license status') and a URL/local doc, and a graph of nodes (fetch -> parse -> LLM-extract) returns JSON — no CSS/XPath. SmartScraperGraph / SearchGraph / OmniScraperGraph variants. 27.2k stars, MIT, actively released.

- **URL:** https://github.com/ScrapeGraphAI/Scrapegraph-ai
- **Repo:** https://github.com/ScrapeGraphAI/Scrapegraph-ai
- **License/ToS:** MIT (commercial use OK; there is also a separate paid hosted API, but the OSS lib is unrestricted)
- **Integrate:** pip install scrapegraphai && playwright install. Local Gemma config: graph_config={'llm':{'model':'ollama/gemma3','model_tokens':8192,'format':'json'}}; SmartScraperGraph(prompt='...', source=url, config=graph_config).run(). Pure-Python, composes with your Playwright fetch (can pass fetched HTML as source=local file/string). Note the hosted 'ScrapeGraph API' is a separate paid product — don't confuse it with the free library.
- **Why:** Prompt-driven entity extraction without per-site selector maintenance — ideal when DueCare onboards a new origin-country registry weekly. SearchGraph can fan a negative-news query across results and extract structured adverse-media hits (who/what/when/source) for a screened employer or broker.

### Skyvern  `free` (verified)
Vision-LLM + computer-vision browser agent: instead of DOM selectors it screenshots the page and a vision model decides where to click/type, so it survives layout changes and obfuscated/anti-bot registry UIs. Playwright-compatible SDK + self-hostable server + MCP support. 21.9k stars.

- **URL:** https://github.com/skyvern-ai/skyvern
- **Repo:** https://github.com/skyvern-ai/skyvern
- **License/ToS:** AGPL-3.0 (copyleft — self-hosting fine for internal/defensive use; offering it as a hosted service to third parties triggers source-disclosure. Commercial license available from Skyvern.)
- **Integrate:** Self-host via docker; configure LLM through .env (ships env.ollama.example). It routes models through LiteLLM, so a local Gemma vision model via Ollama or any OpenAI-compatible endpoint works (set ENABLE_OLLAMA / LLM_KEY + the Ollama base URL). AGPL is the key gotcha for DueCare: keep it as an internal screening tool, or buy the commercial license before exposing it as a SaaS to NGO partners.
- **Why:** DueCare's fallback for the worst targets: scanned/image-heavy government licensee portals, CAPTCHA-adjacent court search forms, and registries that block DOM scrapers. Vision approach pairs with Gemma's multimodal story for the on-device pitch.

### Agent-E  `free` (verified)
Hierarchical-planning web-navigation agent (built on the AG2/AutoGen framework) that decomposes a goal into browser skills. Notable for accuracy: ~73% on the full 643-task WebVoyager set, beating the original multimodal WebVoyager agent. Research-grade but MIT and reusable.

- **URL:** https://github.com/EmergenceAI/Agent-E
- **Repo:** https://github.com/EmergenceAI/Agent-E
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** Clone + install from repo (uv/poetry). Local models supported via LiteLLM and Ollama, but the maintainers explicitly flag local-LLM runs as 'not thoroughly tested' — expect to validate Gemma on your tasks before trusting it. Headline WebVoyager numbers were produced with GPT-4-Turbo on the nested_chat_for_hierarchial_planning branch, so treat local-model accuracy as unproven and benchmark it yourself.
- **Why:** A higher-accuracy navigation option for multi-step registry lookups (search -> filter -> open detail -> extract) where browser-use's single-agent loop stalls. Useful as a benchmark-backed alternative to compare success rate on DueCare's own registry tasks.

### Stagehand (Browserbase)  `freemium` (verified)
TypeScript browser-automation framework with three LLM primitives over Playwright — act('click X'), extract({schema}) for typed data, and observe() — letting you mix deterministic Playwright code with AI steps. 23.1k stars, MIT. Built on the Vercel AI SDK provider interface.

- **URL:** https://github.com/browserbase/stagehand
- **Repo:** https://github.com/browserbase/stagehand
- **License/ToS:** MIT (lib). Optional Browserbase cloud-browser backend is a paid/freemium hosted service; running Stagehand on local Playwright is free.
- **Integrate:** npm install @browserbasehq/stagehand. LLM access is via the Vercel AI SDK, which DOES have community Ollama/OpenAI-compatible providers — so a local Gemma is technically wireable (createAISDKClient with an ollama provider + custom modelName), but it is NOT first-class: docs and defaults target OpenAI/Anthropic/Gemini and Browserbase recommends frontier models for reliability. Treat local-Gemma support as possible-but-unsupported. Set LOCAL=true to use your own Playwright brow
- **Why:** Relevant only if a DueCare component is TypeScript/Node; extract({schema}) is a clean typed entity-extraction call and act() handles the navigation hop. The Python pipeline can shell out to it or use the HTTP/Browserbase path, but for a Python-first stack browser-use/Crawl4AI are the more direct fit

### Firecrawl (/extract, /scrape, /agent)  `freemium` (verified)
Hosted + self-hostable web API that crawls/renders JS and returns clean Markdown or LLM-structured JSON. /scrape with formats:['json'] does schema-driven LLM extraction; /agent (spark-1 models) does autonomous multi-page gathering. 132k stars. Cloud is the main product; an open-source self-host exists.

- **URL:** https://github.com/firecrawl/firecrawl
- **Repo:** https://github.com/firecrawl/firecrawl
- **License/ToS:** AGPL-3.0 (core; SDKs MIT). Cloud at firecrawl.dev is freemium/paid (free tier + credit-metered paid plans).
- **Integrate:** Cloud: POST https://api.firecrawl.dev/v2/scrape with {url, formats:[{type:'json', schema:{...}}]} (or /v2/extract with {urls, prompt, schema}) + Bearer API key. pip install firecrawl-py then FirecrawlApp(api_key=...).scrape_url(url, formats=[...]). Local-model caveat: the LLM extraction runs SERVER-SIDE on Firecrawl's models — the cloud does NOT call your Gemma. To keep screening text on-device, self-host the AGPL core; even then its built-in LLM steps assume an OpenAI-compat
- **Why:** Fastest path to 'URL -> structured entity JSON' for adverse-media articles and registry pages when you want managed JS-rendering and don't want to babysit Playwright. Good for the negative-news ingestion lane (batch-scrape article URLs into {entity, allegation, date, source}).

### Amazon Nova Act  `paid` (verified)
Amazon's Python SDK for reliable UI-automation agents: act() calls run a proprietary Nova browser-action model over a Playwright session, with structured (Pydantic) extraction support. SDK is Apache-2.0 but the model is a closed AWS/nova.amazon.com service.

- **URL:** https://github.com/aws/nova-act
- **Repo:** https://github.com/aws/nova-act
- **License/ToS:** Apache-2.0 (SDK only). The Nova Act model is a paid AWS service governed by nova.amazon.com Terms of Use — no local/open-model option.
- **Integrate:** pip install nova-act ; requires a nova.amazon.com API key or AWS IAM creds (NOVA_ACT_API_KEY). from nova_act import NovaAct; with NovaAct(starting_page=url) as n: n.act('find agency X status'); n.act('return as JSON', schema=MyModel.model_json_schema()). Cannot be pointed at a local model — exclude from the privacy-preserving path; use only if a cloud, high-reliability comparison arm is wanted.
- **Why:** Mostly a NEGATIVE finding for DueCare's privacy thesis: it is frontier-only and cloud-only, so sensitive screening prompts would leave the device. Listed for completeness/benchmarking — its act()+Pydantic-extract ergonomics are a useful reliability reference, but it cannot run on Gemma/Ollama and so

### LaVague  `free` (verified)
Large Action Model framework (built on LlamaIndex) that compiles a natural-language objective into Selenium/Playwright actions via a World Model + Action Engine. Apache-2.0, ~6.4k stars.

- **URL:** https://github.com/lavague-ai/LaVague
- **Repo:** https://github.com/lavague-ai/LaVague
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install lavague. Because it is built on LlamaIndex, you can in principle swap in LlamaIndex's Ollama LLM + a local embedding model (llm=Ollama(model='gemma3')) when constructing the context — but the project's docs center on OPENAI_API_KEY and a dedicated Ollama integration page was not found this session (404), so treat local-Gemma as DIY/unverified. Also verify maintenance freshness before adopting; momentum trails the leaders. Prefer browser-use unless you specifically
- **Why:** A possible navigation-agent option, but lower-priority for DueCare: it defaults to OpenAI and local-Gemma support is not clearly documented, while browser-use/Crawl4AI cover the same need with first-class, tested Ollama paths.

### trafilatura + local LLM (composition pattern)  `free` (unverified)
Not a single tool but the cheapest reliable pattern: trafilatura (a fast, well-maintained Python library, GPLv3) strips boilerplate from a fetched HTML page to clean main-text/Markdown, which you then pass to a local Gemma via Ollama for structured extraction. Deterministic boilerplate removal up front means the LLM sees only the relevant article/registry body, cutting tokens and hallucination.

- **URL:** https://github.com/adbar/trafilatura
- **Repo:** https://github.com/adbar/trafilatura
- **License/ToS:** GPL-3.0 (library is widely used in research/commercial; GPL applies if you redistribute — internal use is unrestricted). Verify the current license/version before relying on it.
- **Integrate:** pip install trafilatura ; downloaded=trafilatura.fetch_url(url); text=trafilatura.extract(downloaded, output_format='markdown', with_metadata=True) -> then ollama.chat(model='gemma3', messages=[{'role':'user','content':extraction_prompt+text}]). Composes trivially with Playwright (pass page.content() to trafilatura.extract instead of fetch_url for JS-rendered pages). url_verified=false: repo/license/version not fetched this session — confirm before depending on it.
- **Why:** The leanest negative-news ingestion primitive for DueCare: trafilatura gives clean article text + metadata (title/date/author) with no API cost, then a single local-Gemma call extracts {entity, allegation_type, ILO-indicator, source, date}. Keeps sensitive screening fully on-device and avoids paying


## playwright_variation

### patchright (patchright-python)  `free` (verified)
Patched, undetected drop-in replacement for Playwright (Chromium only). Eliminates the Runtime.enable CDP execution-context leak, removes automation command flags, and handles closed shadow roots so the page cannot detect Playwright via JS. API-identical to Playwright, so existing sync/async code works by changing only the import. Latest release v1.60.0 (2026-06-03), actively tracking upstream Playwright versions.

- **URL:** https://github.com/Kaliiiiiiiiii-Vinyzu/patchright
- **Repo:** https://github.com/Kaliiiiiiiiii-Vinyzu/patchright
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install patchright && patchright install chromium. Then `from patchright.sync_api import sync_playwright` (or async_api) — drop-in for `playwright`. Pairs with playwright-captcha's click solver for Turnstile. Chromium-only; for Firefox stealth use Camoufox.
- **Why:** Most practical upgrade path for an existing Playwright registry-scraper: defeats Cloudflare/Datadome/Akamai/Kasada/Shape gates on government and recruitment-agency registries that block stock Playwright, with zero code rewrite.

### nodriver  `free` (verified)
Official async successor to undetected-chromedriver. Drives Chrome/Edge/Brave directly over CDP (no Selenium/WebDriver, no chromedriver binary), which both speeds it up and removes the most common WAF detection vectors. Best-practice defaults let you launch in 1-2 lines. 4.4k stars, fully asynchronous.

- **URL:** https://github.com/ultrafunkamsterdam/nodriver
- **Repo:** https://github.com/ultrafunkamsterdam/nodriver
- **License/ToS:** AGPL-3.0 (copyleft — review before bundling into a closed-source service; internal/defensive use is fine)
- **Integrate:** pip install nodriver; `import nodriver as uc; browser = await uc.start(); page = await browser.get(url)`. Not Playwright-API-compatible (its own CDP API), so it lives beside, not inside, a Playwright pipeline. AGPL-3.0 is the licensing gotcha vs Patchright's Apache-2.0.
- **Why:** Strong default for politely passing Cloudflare IUAM / Imperva / hCaptcha interstitials on public registries when a full Playwright stack is overkill; the no-chromedriver CDP path is the cleanest low-detection Chromium driver.

### Camoufox (daijro/camoufox)  `free` (verified)
Open-source anti-detect browser: a custom Firefox build for scraping/AI agents. Playwright's Page Agent is sandboxed/isolated so JS cannot detect Playwright; fingerprint, navigator, screen, fonts, and locale are spoofed at the C++ level (harder to detect than Chromium). Exposes a drop-in Playwright-compatible Python API. 9.2k stars, MPL-2.0, active development resumed in 2026 (also forked at CloverLabsAI/VulpineOS).

- **URL:** https://github.com/daijro/camoufox
- **Repo:** https://github.com/daijro/camoufox
- **License/ToS:** MPL-2.0 (commercial use OK; file-level copyleft)
- **Integrate:** pip install -U camoufox[geoip] (or cloverlabs-camoufox for the actively-developed alpha). `from camoufox.sync_api import Camoufox; with Camoufox() as b: page=b.new_page()`. Supply proxy + os/locale to the Camoufox() constructor. Note: had a ~year maintenance gap; verify current Firefox-base fingerprint freshness before relying on it.
- **Why:** Firefox engine is detected far less than any Chromium variant, so Camoufox is the highest-evasion option for the hardest-protected migration-world targets (DataDome/Cloudflare-heavy job boards). Geolocation/locale spoofing helps when a corridor registry is geo-walled.

### rebrowser-playwright (rebrowser-patches)  `free` (verified)
Playwright (and Puppeteer) fork that patches the Runtime.enable CDP leak using one of three techniques (addBinding, isolated contexts, or enable/disable cycling) so execution contexts get unknown IDs and don't flag as automation. Drop-in replacement package. Core patches repo at v1.0.19 (2025-05-09); a Python `rebrowser-playwright` exists on PyPI.

- **URL:** https://github.com/rebrowser/rebrowser-patches
- **Repo:** https://github.com/rebrowser/rebrowser-patches
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install rebrowser-playwright (Python) or npm i rebrowser-playwright (Node). Drop-in for the `playwright` import. Patch cadence is slower than Patchright (last core release mid-2025), so treat as secondary; benchmark both against your target list.
- **Why:** Alternative to Patchright for the single highest-signal CDP detection vector; useful as an A/B fallback when Patchright's bundled Chromium version hard-blocks on a specific Cloudflare target (the two use different patch strategies + Chromium builds).

### playwright-stealth (Python)  `free` (verified)
Python port of the Puppeteer stealth plugin: applies evasions (navigator.webdriver masking, language/platform/UA override, selective evasion config) to a Playwright context. v2.0.3 (2026-04-04), supports sync + async via apply_stealth_async / use_async context managers. Maintainer explicitly warns it only defeats the simplest bot detection.

- **URL:** https://pypi.org/project/playwright-stealth/
- **Repo:** https://github.com/AtuboDad/playwright_stealth
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install playwright-stealth; `from playwright_stealth import Stealth` then wrap the context. Patches were written for older Chrome eras — use as a complement, not a Cloudflare bypass. Persistent-context support is still on its TODO.
- **Why:** Cheap baseline hardening for low-protection registries (many government/NGO sites use no WAF). Good first layer, but for Cloudflare/Akamai targets it is insufficient alone — escalate to Patchright/Camoufox. Documented here so the pipeline doesn't over-rely on it.

### playwright-captcha  `freemium` (reverification required)
Captcha-solving orchestration layer for Playwright. Solves Cloudflare Turnstile + Interstitial and reCAPTCHA v2/v3 via either a click-based solver (no external service) or API solvers (2Captcha / TenCaptcha). Works with stock Playwright, Patchright, and Camoufox. v0.1.5 (2026-05-21), MIT.

- **URL:** https://pypi.org/project/playwright-captcha/
- **Repo:** The previously recorded upstream URL returned 404 on 2026-07-27.
  Do not adopt this package until its source, maintainer, and license are
  independently reverified from current PyPI metadata.
- **License/ToS:** MIT (library); API solving requires a paid 2Captcha/TenCaptcha key
- **Integrate:** pip install playwright-captcha; `await solver.solve_captcha(captcha_container=page, captcha_type=CaptchaType.CLOUDFLARE_TURNSTILE)`. Click mode is keyless; API mode takes a 2Captcha key. Designed to wrap Patchright/Camoufox directly. Use only on sites you are authorized to crawl.
- **Why:** The glue that lets the scraper clear Turnstile gates on public registries it is legitimately permitted to access. Click-solver path needs no paid service when paired with Patchright/Camoufox, keeping cost at zero for most targets.

### undetected-playwright (QIN2DIM)  `free` (verified)
Stealth injector for Playwright Python providing Tarnished (sync) and Malenia (async) helpers that patch a browser context to pass Sannysoft and basic Cloudflare checks. v0.3.0 (2024-05-19), Apache-2.0.

- **URL:** https://pypi.org/project/undetected-playwright/
- **Repo:** https://github.com/QIN2DIM/undetected-playwright
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install -U undetected-playwright; `from undetected_playwright import Malenia; await Malenia.apply_stealth(context)`. Note: last release 2024 — staler than Patchright; prefer Patchright for anything Cloudflare-grade, keep this for browserforge-paired moderate targets.
- **Why:** Lightweight mid-tier evasion that browserforge also supports as an injection target (browserforge.injectors.undetected_playwright), so it composes cleanly with fingerprint generation for moderate-protection targets.


## browsing_technique

### changedetection.io  `freemium` (verified)
Self-hosted website change-detection + monitoring service. Watches non-feed pages (registry result tables, agency status pages, debarment lists) and fires on text/visual/structural change. Supports XPath/CSS filters, JSONPath/jq for JSON-API endpoints, a Playwright/Chromium fetcher for JS-rendered pages, restock/price/defacement use-cases, and 100+ notification targets.

- **URL:** https://github.com/dgtlmoon/changedetection.io
- **Repo:** https://github.com/dgtlmoon/changedetection.io
- **License/ToS:** Apache-2.0 self-host (commercial use OK); separate optional paid SaaS ($8.99/mo) and a Commercial Licence file for hosted resale
- **Integrate:** docker run -p 5000:5000 -v ./datastore:/datastore ghcr.io/dgtlmoon/changedetection.io. Add watches via its API (POST /api/v1/watch) with include_filters XPath/CSS; set notification_urls to an Apprise URL or your webhook. Use the playwright-chrome fetcher container for JS pages. Latest v0.55.7 (May 2026).
- **Why:** Many migration-world registries (licensed-recruiter lists, MOL/DMW/POEA status pages, blacklists) have NO feed/API — they're HTML tables that change occasionally. changedetection.io turns 'did this agency get added to the blacklist / lose its licence?' into a webhook event without writing a bespoke 

### Hidden-API discovery via DevTools Network tab + HAR capture  `free` (unverified)
Core technique for SPA-backed gov registries: open the registry, record the Network tab filtered to Fetch/XHR, perform a search, and read the underlying JSON request (URL, query params, required headers). Export the session as a .har to replay/diff requests programmatically.

- **URL:** https://developer.chrome.com/docs/devtools/network
- **License/ToS:** Technique, not a product. No license.
- **Integrate:** Workflow: DevTools > Network > filter 'Fetch/XHR' (or 'mime-type:application/json') > interact > right-click the JSON request > Copy as cURL / Save all as HAR. Inspect Request Headers for the minimal set (often just accept + referer + a session cookie). Then in Python: replicate with requests.Session(); for header/cookie-gated endpoints, drive one Playwright session to mint the cookie via page.context.cookies() and inject into requests. Parse HAR with the 'haralyzer' PyPI lib
- **Why:** Most labour-ministry / licensed-recruiter / company registries render as a React/Angular shell that fetches JSON from an undocumented /api/ endpoint. Capturing that one XHR turns a 'JS-walled, un-scrapable' SPA into a clean JSON source you call directly with requests, skipping Playwright entirely.

### Scraping hidden/private JSON APIs (Scrapfly methodology)  `free` (unverified)
Systematic guide to locating and calling the private JSON/XHR APIs that power dynamic sites: identify the backend call in Network, reconstruct auth/pagination params, and hit it directly for clean structured data far faster than HTML scraping.

- **URL:** https://scrapfly.io/blog/posts/how-to-scrape-hidden-apis
- **License/ToS:** Article/technique (Scrapfly is a paid product but the method is provider-agnostic and usable with plain requests/httpx).
- **Integrate:** Method: (1) find the XHR in Network, (2) note pagination (page/limit/offset/cursor) and any X-* / token headers, (3) replay with httpx/requests, (4) loop pagination until empty. For sites that sign requests in JS, intercept with mitmproxy or run the page in Playwright and capture page.on('response') for application/json bodies, then graduate to keyless requests once params are understood.
- **Why:** Directly applicable to brokered registry SPAs that expose paginated /api/agencies?page=N&status=licensed style endpoints. Pulling the JSON API yields stable, schema'd records (license number, status, address) instead of brittle DOM scraping that breaks on every UI change.

### GraphQL endpoint discovery + introspection  `free` (unverified)
Probe common suffixes (/graphql, /api/graphql, /v1/graphql, /query) and, if introspection is enabled, run the __schema introspection query to dump every type/field/query the registry backend exposes — then build precise data-pull queries.

- **URL:** https://portswigger.net/web-security/graphql/lab-graphql-find-the-endpoint
- **Repo:** https://github.com/mindedsecurity/graphqlschema2payload
- **License/ToS:** Technique. Tools referenced (graphqlschema2payload) are open source.
- **Integrate:** Detect: GET https://site/api with no body — a 'Query not present' error implies a GraphQL handler. Introspect: POST {"query":"{__schema{types{name fields{name}}}}"}. If blocked, insert whitespace/newline after __schema to bypass naive regex filters, or recover queries from the JS bundle (DevTools Sources). Use the 'gql'/'sgqlc' Python clients to call discovered queries; persisted-query sites force-error with a bad hash to leak the query text (PersistedQueryNotFound).
- **Why:** A growing number of modern gov/registry SPAs use GraphQL. Introspection reveals filterable fields (license status, sanction flags, ownership edges) you can query in one round-trip, which is far richer than guessing REST routes for entity-resolution graph building.

### Mobile-app API reuse via mitmproxy  `free` (unverified)
Many gov/registry mobile apps talk to cleaner, less-defended JSON backends than the website. Run the app through mitmproxy (or mitmweb) to intercept and document those endpoints, headers, and auth tokens, then call them from Python.

- **URL:** https://github.com/mitmproxy/mitmproxy
- **Repo:** https://github.com/mitmproxy/mitmproxy
- **License/ToS:** mitmproxy is MIT (open source). Free.
- **Integrate:** pip install mitmproxy; run `mitmweb`, set the device proxy to your host:8080, install the mitm CA on the device (handle cert-pinning with frida/objection if needed), exercise the app, read flows in mitmweb. Export with a mitmproxy addon (response.json) or 'Copy as cURL', then port to requests/httpx. Compose into the pipeline as a one-time discovery step; the resulting endpoint goes straight into the keyless requests path.
- **Why:** When a registry's web SPA is Cloudflare/WAF-protected but its companion app isn't, the app's API often returns the same entity records with simpler auth — a reliable fallback for licensed-recruiter or worker-protection registries that ship a mobile app but no docs.

### Endpoint surface probing: sitemap.xml / robots.txt / llms.txt / /api/ enumeration  `free` (unverified)
Low-effort reconnaissance to map a registry's hidden surface before scraping: pull sitemap.xml(.gz) for the full URL inventory, read robots.txt Disallow paths (often point straight at /api/ or /export/), check the new llms.txt convention, and fuzz common API roots.

- **URL:** https://www.sitemaps.org/protocol.html
- **License/ToS:** Open web standards/conventions. Free. Respect robots.txt scope and site ToS for defensive, low-rate use.
- **Integrate:** Fetch https://site/robots.txt (parse Disallow + Sitemap: lines), https://site/sitemap.xml and nested sitemap indexes (gzipped .xml.gz common) with the stdlib 'urllib.robotparser' + 'advertools.sitemap_to_df'. Probe candidates: /api, /api/v1, /api/v2, /graphql, /export, /data, /rest, /odata, /llms.txt, /.well-known/. Confirm by Accept: application/json and inspecting the response shape. Keep request rate low and obey robots for a defensive tool.
- **Why:** Fast way to find bulk-download routes and undocumented JSON endpoints on a labour-ministry registry: a sitemap enumerates every agency detail page (seed your crawl), and robots.txt Disallow entries frequently leak /api/v1/ or /downloads/ paths the UI never links.


## scraping_tool

### Scrapy  `free` (verified)
Mature, production-grade crawling framework: request scheduler, auto-throttle, retries, middlewares, item pipelines, robots.txt handling, and dupe filtering. Latest v2.16.0 (2026-05-19), maintained by Zyte + community, requires Python 3.10+.

- **URL:** https://pypi.org/project/Scrapy/
- **Repo:** https://github.com/scrapy/scrapy
- **License/ToS:** BSD-3-Clause (commercial use OK)
- **Integrate:** pip install scrapy. Define a Spider with parse() yielding items; run via `scrapy crawl <name> -O out.jsonl`. Item pipelines are the natural place to write to a staging/propose store (never live RAG). Pairs with scrapy-playwright for JS pages and scrapy-impersonate/curl_cffi adapters for anti-bot sites.
- **Why:** The durable backbone for breadth-first crawls of public registries (recruitment-agency lists, debarment/sanctions index pages, NGO directories) where polite throttling, retry, and pipeline staging matter more than JS rendering — the 'propose-only' staging maps naturally onto item pipelines.

### feedparser  `free` (verified)
The de-facto Python RSS/Atom/RDF/JSON feed parser. Auto-detects feed format (RSS 0.9x-2.0, Atom 0.3/1.0, RDF) and normalizes every feed into one consistent dict structure with sanitized HTML, parsed dates, and ETag/Last-Modified support for conditional GETs. 15+ years of edge-case handling.

- **URL:** https://github.com/kurtmckee/feedparser
- **Repo:** https://github.com/kurtmckee/feedparser
- **License/ToS:** BSD-2-Clause (OSS, no commercial restriction)
- **Integrate:** pip install feedparser. Poll with ETag/modified to avoid re-downloading: d = feedparser.parse(url, etag=prev_etag, modified=prev_mod); then store d.etag / d.modified and iterate d.entries (each has .id/.link/.title/.published_parsed). Pure-Python, composes trivially in a scheduled worker.
- **Why:** Many negative-news / sanctions / regulator sources publish RSS/Atom: court-listing feeds, NGO press feeds, government debarment bulletins, Google News RSS queries scoped to an agency name. feedparser is the cheapest possible ingestion: no API key, no scraping, polite conditional GETs.

### trafilatura  `free` (verified)
High-accuracy main-content + metadata extractor (title, author, date, sitename, tags) with a fallback extraction chain; tops F1 in independent article-extraction benchmarks and is multilingual. Latest v2.1.0 (2026-06-07), very actively maintained.

- **URL:** https://pypi.org/project/trafilatura/
- **Repo:** https://github.com/adbar/trafilatura
- **License/ToS:** Apache-2.0 as of v1.8.0+ (earlier versions GPLv3+) — use >=1.8.0 to avoid GPL for commercial use
- **Integrate:** pip install 'trafilatura>=2.1'. One-liner: `from trafilatura import fetch_url, extract; extract(fetch_url(url), output_format='json', with_metadata=True)`. Can also take HTML you already fetched (via curl_cffi) — pass the HTML string to extract(). LICENSE GOTCHA: pin >=1.8.0 so you get Apache-2.0, not the old GPLv3+.
- **Why:** The workhorse for negative-news ingestion: strips boilerplate from an adverse-media article and returns clean body text + publish date + author, which is exactly the structured signal DueCare needs to attribute a trafficking/wage-theft allegation to an entity and timestamp it.

### crawl4ai  `free` (verified)
Async LLM-oriented web crawler/scraper that renders pages (Playwright under the hood) and emits clean Markdown + structured JSON, with built-in content filtering (BM25/pruning), link/media extraction, and optional LLM-driven extraction strategies. Latest v0.8.9 (2026-06-04), 68.4k stars, very actively maintained.

- **URL:** https://github.com/unclecode/crawl4ai
- **Repo:** https://github.com/unclecode/crawl4ai
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install -U crawl4ai && crawl4ai-setup (downloads Playwright browsers). Use: `async with AsyncWebCrawler() as c: r = await c.arun(url=...); r.markdown`. Async-native so it drops into a propose-only asyncio pipeline; pin the version for reproducibility. Heavy dep (bundles Playwright) — gate behind an optional extra.
- **Why:** Turns a recruitment-agency profile page, ILO/court page, or adverse-media article into RAG-ready Markdown in one call, ideal for feeding negative-news text straight into DueCare's extraction/entity-resolution layer without hand-writing a parser per source.

### curl_cffi  `free` (verified)
HTTP client (requests-like + async) that impersonates real browser TLS/JA3 and HTTP/2 (and HTTP/3) fingerprints via a curl-impersonate binding, defeating fingerprint-based bot walls. Latest v0.15.x (2026-06-05), 5.8k stars, on par with aiohttp for speed.

- **URL:** https://github.com/lexiforest/curl_cffi
- **Repo:** https://github.com/lexiforest/curl_cffi
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install curl_cffi. Drop-in: `from curl_cffi import requests; requests.get(url, impersonate='chrome')`; async via `curl_cffi.requests.AsyncSession`. Use as the fetch layer beneath trafilatura/selectolax. Note: this is the maintained lexiforest fork (the original yifeikong repo is also real but the fork is the active one).
- **Why:** Already adopted by DueCare's Research Monitor — the fix for WAF/Cloudflare 403s on government registry and adverse-media domains that block plain requests/httpx. Keeps public-data fetches reaching their target without a full browser.

### MarkItDown  `free` (verified)
Microsoft utility converting HTML, PDF, DOCX/PPTX/XLSX, images (EXIF+OCR), audio, CSV/JSON/XML, EPUB and ZIP into LLM-friendly Markdown. Latest v0.1.6 (2026-05-26), ~153k stars, MIT.

- **URL:** https://github.com/microsoft/markitdown
- **Repo:** https://github.com/microsoft/markitdown
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install 'markitdown[all]'. Use: `from markitdown import MarkItDown; MarkItDown().convert('filing.pdf').text_content`. Convert accepts a path/URL/stream. Heavier than trafilatura for plain article HTML (trafilatura is better at boilerplate removal) — use MarkItDown for the Office/PDF/multi-format long tail, trafilatura for news articles.
- **Why:** Normalizes the heterogeneous document evidence DueCare collects on an entity — a PDF court filing, a DOCX NGO report, an XLSX debarment list, a scanned ID — into one Markdown shape for the extraction/knowledge layer, so downstream prompts don't branch per file type.

### selectolax  `free` (verified)
Hyper-fast Cython HTML5 parser with CSS selectors, wrapping the Lexbor (preferred) and Modest engines; benchmarked up to ~30x faster than BeautifulSoup. Latest v0.4.10 (2026-05-26), MIT, ~1.6k stars.

- **URL:** https://github.com/rushter/selectolax
- **Repo:** https://github.com/rushter/selectolax
- **License/ToS:** MIT (commercial use OK)
- **Integrate:** pip install selectolax. Use the Lexbor backend (Modest's C lib is unmaintained): `from selectolax.lexbor import LexborHTMLParser; t = LexborHTMLParser(html); t.css_first('h1#title').text()`. Pure parser — pair with curl_cffi/httpx for fetching. Excellent default for table/list scraping in the propose pipeline.
- **Why:** For high-throughput parsing of millions of registry rows / search-result pages where BeautifulSoup is the bottleneck — e.g. paging a sanctions or debarment index and pulling entity name + status cells fast.

### browserforge  `free` (verified)
Python reimplementation of Apify's fingerprint-suite: a Bayesian generative network that produces realistic, in-the-wild-frequency browser headers (User-Agent, sec-ch-ua, Accept-Language, fetch-metadata) and full fingerprints (screen, navigator, codecs, GPU, fonts, battery). v1.2.4 (2026-02-03), Apache-2.0, Python 3.8-3.14.

- **URL:** https://pypi.org/project/browserforge/
- **Repo:** https://github.com/daijro/browserforge
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install browserforge[all]. Playwright: `from browserforge.injectors.playwright import AsyncNewContext; ctx = await AsyncNewContext(browser, fingerprint=fp)` (replaces browser.new_context). Header-only: HeaderGenerator().generate(). Note: fingerprint INJECTION is deprecated upstream in favor of Camoufox — use browserforge for header/fingerprint GENERATION and let Camoufox apply it.
- **Why:** Generates consistent, realistic per-session fingerprints + headers so a registry-screening crawler rotating across many agencies doesn't reuse one detectable signature. Header generation alone is useful even for a pure-httpx (non-browser) tier of the pipeline.

### crawlee-python  `free` (verified)
Apify's unified crawling library exposing one interface over HTTP and browser crawling: BeautifulSoupCrawler, ParselCrawler, HttpCrawler, and PlaywrightCrawler, plus persistent request queues, datasets, session pools, and proxy rotation. Latest v1.7.2 (2026-06-04), 9.2k stars, fully type-hinted.

- **URL:** https://github.com/apify/crawlee-python
- **Repo:** https://github.com/apify/crawlee-python
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** python -m pip install 'crawlee[all]' && playwright install. Subclass/instantiate a crawler, register a request handler with `@crawler.router.default_handler`, push results via `context.push_data(...)` into a Dataset (export later). Resumable RequestQueue persists to disk — good for long registry sweeps.
- **Why:** Lets DueCare start a source on cheap HTTP crawling and escalate the same crawler to a real browser only when a registry hides data behind JS — without rewriting the spider — while built-in queues/datasets give resumable, propose-only staging out of the box.

### parsel  `free` (verified)
Standalone extraction library (the engine inside Scrapy) for querying HTML/XML with XPath and CSS, JSON with JMESPath, plus regex, all chainable on one Selector. Latest v1.11.0 (2026-01-29), BSD-3-Clause.

- **URL:** https://pypi.org/project/parsel/
- **Repo:** https://github.com/scrapy/parsel
- **License/ToS:** BSD-3-Clause (commercial use OK)
- **Integrate:** pip install parsel. Usage: `from parsel import Selector; sel = Selector(text=html); sel.css('h1::text').get(); sel.xpath('//span[@class="license"]/text()').get(); sel.jmespath('@')`. Stateless and fetch-agnostic — feed it HTML from curl_cffi/httpx. Use over selectolax when you need XPath or JSON-LD/JMESPath, not just CSS.
- **Why:** Precise field extraction from semi-structured registry pages (e.g. an agency's license number via XPath, a status badge via CSS, an embedded JSON-LD blob via JMESPath) without pulling in all of Scrapy — clean fit for a lightweight propose-only extractor module.

### reader (lemon24/reader)  `free` (verified)
A higher-level Python feed-reader library that wraps feedparser and persists all feed + entry state into a single SQLite file. Handles incremental updates, marks entries read/important, tags feeds, dedups already-seen entries by feed+id, and ships a built-in full-text search over entries. Plugin system for custom processing.

- **URL:** https://github.com/lemon24/reader
- **Repo:** https://github.com/lemon24/reader
- **License/ToS:** BSD-3-Clause (OSS)
- **Integrate:** pip install reader. r = make_reader('feeds.db'); r.add_feed(url); r.update_feeds(); then iterate r.get_entries(read=False) to find NEW items, process, r.mark_entry_as_read(e). The SQLite DB is the incremental-crawl state — no extra dedup store needed for feed sources.
- **Why:** Gives the 'have I already seen this article about this agency?' state layer for free, in SQLite, so a propose-only monitor never re-alerts on the same adverse-media item. Per-feed tags map cleanly onto per-entity watchlists (one feed = one Google News query for an employer/broker).

### CapSolver (Cloudflare Turnstile API)  `paid` (verified)
AI-based captcha-solving SaaS. AntiTurnstileTaskProxyLess returns a valid Cloudflare Turnstile token in <3s; also handles reCAPTCHA, Datadome, AWS WAF. Pay-per-successful-solve, ~$1.2 per 1k Turnstile tokens. REST API + Python SDK + browser extension.

- **URL:** https://www.capsolver.com/products/cloudflare
- **License/ToS:** Commercial SaaS ToS — third-party solving service; confirm target-site authorization before use
- **Integrate:** REST: POST https://api.capsolver.com/createTask then poll POST https://api.capsolver.com/getTaskResult with {"clientKey":"API_KEY"}. Python SDK available (pip install capsolver). Feed the returned cf-turnstile token into the page. API key required; budget per-solve, not subscription.
- **Why:** Backstop for the minority of authorized targets where click-solving fails. Token-based solve works even with stock Playwright, decoupling captcha from the browser stack. Price leader vs 2Captcha (~$3/1k) for high-volume corridor-registry sweeps.

### Crawlee for Python (PlaywrightCrawler)  `free` (verified)
Apify's production web-scraping framework. PlaywrightCrawler gives a managed browser pool with integrated proxy rotation, session/cookie management, automatic retries on block, and request routing over a unified HTTP+headless interface. v1.7.2 (2026-06-04), 9.2k stars, Apache-2.0.

- **URL:** https://github.com/apify/crawlee-python
- **Repo:** https://github.com/apify/crawlee-python
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install 'crawlee[all]' && playwright install. Use PlaywrightCrawler with browser_pool + ProxyConfiguration for residential-proxy rotation and automatic session management; plug a stealth browser via the browser-launcher hook. Camoufox integration tracked in apify/crawlee-python#684.
- **Why:** Supplies the scale/reliability scaffolding (pooling, proxy + session rotation, retry-on-block, concurrency) that a multi-registry entity-screening crawler needs, instead of hand-rolling browser pooling. Composes with the stealth browsers above and has open Camoufox-integration work.

### httpx  `free` (unverified)
Modern sync+async HTTP client with HTTP/2 support, connection pooling, timeouts, and a requests-compatible API. The standard async fetch layer for Python scraping pipelines (Encode/community maintained, BSD-3-Clause).

- **URL:** https://www.python-httpx.org/
- **Repo:** https://github.com/encode/httpx
- **License/ToS:** BSD-3-Clause (commercial use OK)
- **Integrate:** pip install httpx (or httpx[http2] for HTTP/2). Async: `async with httpx.AsyncClient(http2=True, timeout=30) as c: r = await c.get(url)`. Compose with asyncio.gather + a semaphore for polite concurrency in the propose pipeline. Note: httpx does NOT impersonate browser fingerprints — that's curl_cffi's job.
- **Why:** The default async fetcher for registry/API endpoints that don't fight you — concurrent GETs across many entity pages with one AsyncClient, before handing HTML to parsel/selectolax/trafilatura. Escalate to curl_cffi only when a site blocks on TLS fingerprint.

### 2Captcha (Cloudflare Turnstile API)  `paid` (verified)
Long-established captcha-solving service with a documented Cloudflare Turnstile endpoint returning a solve token (~$3 per 1k, 10-30s). Broad coverage (reCAPTCHA, hCaptcha, Turnstile, image). Official Python client (2captcha-python).

- **URL:** https://2captcha.com/api-docs/cloudflare-turnstile
- **Repo:** https://github.com/2captcha/2captcha-python
- **License/ToS:** Commercial SaaS ToS — third-party solving service; use only on authorized targets
- **Integrate:** pip install 2captcha-python; `from twocaptcha import TwoCaptcha; TwoCaptcha(API_KEY).turnstile(sitekey=..., url=...)`. Directly selectable inside playwright-captcha. Pricier and slower than CapSolver but more battle-tested; API key required.
- **Why:** Mature, widely-integrated alternative to CapSolver (playwright-captcha supports it natively as TwoCaptcha). Worth keeping as a redundant provider so a single vendor outage doesn't stall an authorized registry sweep.

### python-readability (readability-lxml)  `free` (unverified)
Python port of arc90's Readability that isolates the main article body + title from a cluttered HTML page using lxml. Mature, widely used (it's one of the extractors news-please composes), Apache-2.0.

- **URL:** https://github.com/buriy/python-readability
- **Repo:** https://github.com/buriy/python-readability
- **License/ToS:** Apache-2.0 (commercial use OK)
- **Integrate:** pip install readability-lxml (imports as `readability`). Usage: `from readability import Document; doc = Document(html); doc.title(); doc.summary()` (summary() returns cleaned article HTML — run it back through selectolax/parsel for text). Best used as a fallback tier behind trafilatura, not the primary extractor. Not fetched this session — verify version before pinning.
- **Why:** A lightweight, dependency-light fallback for main-content extraction on adverse-media pages where trafilatura under-extracts — good as a second opinion in an extraction-chain so a negative-news hit is never missed due to one extractor's boilerplate heuristics.


## osint_tool

### OCCRP Aleph (alephdata/aleph)  `freemium` (verified)
Investigative data platform that indexes both unstructured documents (PDF/Word/HTML, with OCR + NER) and structured data (CSV/XLS/SQL) into Elasticsearch, extracts people/companies, and cross-references them against watchlists and 250+ public datasets (leaks, corporate registries, sanctions). The public instance at data.occrp.org is a free OSINT search surface for migration-world entities.

- **URL:** https://github.com/alephdata/aleph
- **Repo:** https://github.com/alephdata/aleph
- **License/ToS:** MIT.
- **Integrate:** Self-host via docker-compose (heavy: ES + Postgres + Redis + workers). API key from any instance → `GET /api/2/entities?q=...&filter:schema=Company` and `/api/2/match` for xref. IMPORTANT STATUS: classic Aleph maintenance ends 2025-12-31; team is moving to 'Aleph Pro'. Use the public hosted instance + alephclient now; pin a commit if self-hosting the legacy stack.
- **Why:** Adverse-media + leak + registry search engine for a broker/employer name. Self-host to ingest your own scraped corpus and auto-cross-reference against sanctions/PEP lists; or query the public data.occrp.org corpus for negative news and corporate filings.

### alephclient (alephdata/alephclient)  `free` (verified)
CLI + Python API for OCCRP Aleph: bulk-crawl a local directory and upload documents, stream/write FtM entities into a collection, and run cross-reference jobs over the Aleph API without server access. The scriptable bridge between a Python/Playwright scraping pipeline and an Aleph instance.

- **URL:** https://github.com/alephdata/alephclient
- **Repo:** https://github.com/alephdata/alephclient
- **License/ToS:** MIT.
- **Integrate:** `pip install alephclient`; set ALEPHCLIENT_HOST + ALEPHCLIENT_API_KEY. `alephclient crawldir ./case_files --foreign-id mycase` to ingest; `alephclient write-entities -i entities.ijson -f collxn` to stream FtM; Python `AlephAPI().match(entity)` for xref. Active: v2.7.0 (Mar 2026).
- **Why:** How DueCare would push scraped registry rows / case documents into Aleph and pull back entity matches programmatically, keeping the whole loop in Python.

### SpiderFoot (smicallef/spiderfoot)  `freemium` (verified)
OSINT automation platform with 200+ modules that takes a seed (domain, email, name, phone, username, IP, crypto address) and auto-pivots across DNS, breach databases, social media, dark-web, threat-intel and registry sources, correlating results into an entity graph. Web UI + CLI (sfcli.py); runs headless in Docker.

- **URL:** https://github.com/smicallef/spiderfoot
- **Repo:** https://github.com/smicallef/spiderfoot
- **License/ToS:** MIT (open-source edition). Many high-value modules need third-party API keys (free tiers to paid); SpiderFoot HX is the paid cloud version.
- **Integrate:** Docker `spiderfoot/spiderfoot`; start with `python sf.py -l 127.0.0.1:5001` for the web API or `sf.py -s target.com -m sfp_dnsresolve,sfp_whois -o json`. Scriptable but heavy; best as a background enrichment service. Latest tagged release v4.0 (2022) though repo still referenced; pin and test modules you rely on.
- **Why:** Footprinting a suspect recruitment-agency's web/email/phone infrastructure — surfacing linked domains, shared registrant emails, and breach exposure that connect shell recruiters. A reconnaissance complement to formal registry/sanctions screening.

### theHarvester (laramies/theHarvester)  `freemium` (verified)
Reconnaissance tool that gathers emails, subdomains, hostnames, names, IPs and URLs for a target domain from 50+ passive sources (search engines, certificate-transparency logs, DNS/threat-intel DBs). Lightweight, fast, Python-native, scriptable.

- **URL:** https://github.com/laramies/theHarvester
- **Repo:** https://github.com/laramies/theHarvester
- **License/ToS:** GPL-2.0 (note: copyleft — affects redistribution if embedded; calling it as a subprocess is fine). Some modules need API keys.
- **Integrate:** `pip install` via the repo (uv-based) or `git clone` + `python theHarvester.py -d agency.com -b duckduckgo,crtsh -f out.json`. JSON/XML output parses cleanly into a Python pipeline as a subprocess. Active: v4.11.1 (Jun 2026), needs Python 3.12+.
- **Why:** Quick domain-to-contacts enrichment for an employer/agency's website — pulls associated emails/subdomains that help cluster related entities and find contact footprints during due diligence.

### Sherlock (sherlock-project/sherlock)  `free` (verified)
Username-enumeration OSINT tool that checks a single handle across 400+ social/web platforms and returns where accounts exist. CLI plus importable Python; outputs CSV/XLSX/JSON; supports proxies and site filtering.

- **URL:** https://github.com/sherlock-project/sherlock
- **Repo:** https://github.com/sherlock-project/sherlock
- **License/ToS:** MIT.
- **Integrate:** `pip install sherlock-project` then `sherlock <username> --json out.json`, or import the package for in-process use. Treat results as leads, not proof (false positives on common handles). Active: v0.16.0 (Sep 2025), 85k+ stars.
- **Why:** SOCMINT pivot when an individual broker/recruiter operates under a handle — maps their presence across platforms to corroborate identity and surface adverse posts/reviews. Narrow but useful for person-level (not org-level) entity intelligence.

### OCCRP Aleph  `freemium` (unverified)
OCCRP's global investigative archive — 1B+ records / datasets from 180+ countries: sanctions lists, corporate registries, court filings, leaks, and adverse-media collections, with full-text search and a documented HTTP/JSON API and Python client (followthemoney / alephclient).

- **URL:** https://aleph.occrp.org/
- **Repo:** https://github.com/alephdata/alephclient
- **License/ToS:** Mixed: aggregates third-party datasets each under their own terms; OCCRP restricts bulk reuse and commercial redistribution — read per-dataset terms and OCCRP's API ToS before any commercial use.
- **Integrate:** Public browse needs no account; the API (GET /api/2/entities?q=... and /api/2/search) and bulk features require a free API key (Authorization: ApiKey <key>). Python: pip install alephclient; alephclient also supports reconciliation. Rate-limited for unauthenticated/free tiers. Verify aleph.occrp.org before integrating (host occasionally changes).
- **Why:** Entity-resolution + cross-border corporate/leak/sanctions search to enrich a flagged recruiter/employer/broker — link a Gulf employer to offshore structures, watchlists, or prior reporting beyond what corridor feeds show.

### Verité CUMULUS Forced Labor Screen & Recruitment Cost Calculator  `manual` (unverified)
Verité (NGO) offers CUMULUS, a membership platform that maps labour supply chains and screens operations/recruiters/portfolios against ILO forced-labour indicators using gathered workforce + recruitment-agent data; plus a public Recruitment Cost Calculator giving up-to-date corridor recruitment-fee benchmarks (debt-bondage red-flag thresholds).

- **URL:** https://verite.org/initiative/cumulus/
- **License/ToS:** Verité content copyrighted; tools/reports free for reference with attribution, CUMULUS data is members-only and not redistributable. Partnership/permission required for any data reuse.
- **Integrate:** CUMULUS is membership/partner-gated (no open API) — engage as a methodology reference / partnership, not a scrape target. The Recruitment Cost Calculator and Fair Recruitment toolkit pages are publicly browsable; extract published per-corridor fee figures into your fee-cap knowledge pack and cite Verité. Confirm the CUMULUS URL is live before relying on it.
- **Why:** Authoritative ILO-indicator methodology + corridor fee benchmarks; the Cost Calculator gives DueCare an objective 'fees above licit ceiling => debt-bondage risk' signal per corridor, the core economic indicator of illegal recruitment.


## entity_resolution

### FollowTheMoney + nomenklatura (opensanctions/nomenklatura)  `free` (verified)
followthemoney is the JSON entity/relationship data model (schemas: Person, Company, Organization, LegalEntity, Address, plus edges Ownership/Directorship/Sanction) used across the OCCRP/OpenSanctions ecosystem. nomenklatura is the framework on top: blocking + inverted-index candidate generation, FtM comparison scoring, a Resolver graph of same/different/undecided judgements, dataset merging, and an enrichment framework that links your entities to external sources (e.g. OpenCorporates, the OpenSanctions API).

- **URL:** https://github.com/opensanctions/nomenklatura
- **Repo:** https://github.com/opensanctions/nomenklatura
- **License/ToS:** MIT (both followthemoney and nomenklatura).
- **Integrate:** `pip install followthemoney nomenklatura`. Build entities via followthemoney's `model.make_entity('Company')`; CLI `nomenklatura xref entities.ijson` → `nomenklatura dedupe` (review merges) → `nomenklatura apply -o merged.ijson`. Programmatic: Dataset/Store/Index/Resolver classes. Enrichers (`nomenklatura.enrich`) call OpenSanctions/OpenCorporates to pull matches.
- **Why:** The entity-resolution backbone for DueCare: dedupe the same recruitment agency scraped from POEA/DMW, a court filing, and a news article into one canonical entity, then enrich it against sanctions/registry sources. Same data model yente and Aleph speak, so everything composes.

### dedupe (dedupeio/dedupe)  `free` (verified)
Mature Python library for fuzzy matching, deduplication, and record linkage using active-learning logistic regression over field comparators (string/exact/geo/price). You label a small set of candidate pairs interactively; it learns blocking predicates and a match scorer that scales to larger structured datasets.

- **URL:** https://github.com/dedupeio/dedupe
- **Repo:** https://github.com/dedupeio/dedupe
- **License/ToS:** MIT (library). dedupe.io the hosted SaaS is separate/paid; the library is free.
- **Integrate:** `pip install dedupe`. Define fields = [{'field':'name','type':'String'},{'field':'address','type':'String'}]; `deduper.prepare_training(data)`, `dedupe.console_label(deduper)`, `deduper.train()`, then `deduper.partition(data, threshold)` → clusters. For two-source linkage use the RecordLink class.
- **Why:** Generic entity resolution when entities aren't in FtM form — e.g. dedupe a scraped table of agency names/addresses/license numbers across POEA, DMW, and Gulf registries into canonical employers before screening.

### datasketch (MinHash / LSH)  `free` (verified)
Probabilistic data structures for similarity + cardinality: MinHash, Weighted MinHash, LSH, LSH Forest, LSH Ensemble, HNSW, HyperLogLog++. MinHash+LSH gives sub-linear near-duplicate detection over large text sets; LSH Ensemble/Forest do approximate nearest-neighbour by Jaccard.

- **URL:** https://github.com/ekzhu/datasketch
- **Repo:** https://github.com/ekzhu/datasketch
- **License/ToS:** MIT (OSS)
- **Integrate:** pip install datasketch. Build per-doc MinHash(num_perm=128) over word/char shingles; insert into MinHashLSH(threshold=0.8); lsh.query(mh) returns near-dup keys. For names, shingle on char 3-grams. v1.10.0 (Apr 2026). Pure-Python, persists LSH index to Redis/Cassandra if needed.
- **Why:** Two jobs in one monitor: (1) DEDUP — collapse the same adverse-news story syndicated across 20 outlets so a reviewer sees one proposed alert, not 20; (2) ENTITY RESOLUTION — MinHash-LSH over normalized agency/employer name shingles to cluster 'ABC Manpower Pte', 'ABC Man Power', 'A.B.C. Manpower' in

### recordlinkage (J535D165/recordlinkage)  `free` (verified)
Pandas-native toolkit for record linkage and deduplication: blocking / sorted-neighbourhood indexing to generate candidate pairs, a Compare API with string (Jaro-Winkler/Levenshtein), numeric, geo and date comparators, and supervised + unsupervised (ECM, k-means) classifiers. No interactive labeling required — fully programmatic, good for batch pipelines.

- **URL:** https://github.com/J535D165/recordlinkage
- **Repo:** https://github.com/J535D165/recordlinkage
- **License/ToS:** BSD-3-Clause.
- **Integrate:** `pip install recordlinkage`. `indexer = recordlinkage.Index(); indexer.block('country')`; `compare = recordlinkage.Compare(); compare.string('name','name',method='jarowinkler')`; `features = compare.compute(pairs, dfA, dfB)`; threshold or fit a classifier. Last release v0.16 (2023) but stable and widely used.
- **Why:** Lighter, code-first alternative to dedupe for linking two scraped registries (e.g. match a court-case defendant table to a licensed-agency registry) directly inside a pandas/Playwright pipeline.

### OpenRefine Reconciliation API  `free` (verified)
An open HTTP+JSON spec (now a W3C Community Group standard) for entity reconciliation: POST a name (+ optional type/properties) to a /reconcile endpoint and get back a ranked list of candidate entities with scores. OpenRefine the desktop tool is the reference client, but the spec is the real asset — yente, Wikidata (wikidata.reconci.link), VIAF, and many registries expose compatible endpoints.

- **URL:** https://openrefine.org/docs/technical-reference/reconciliation-api
- **Repo:** https://github.com/OpenRefine/OpenRefine
- **License/ToS:** OpenRefine BSD-3-Clause; the reconciliation spec is open (W3C CG).
- **Integrate:** POST to e.g. https://wikidata.reconci.link/en/api with queries={"q0":{"query":"Al Noor Manpower","type":"Q4830453"}} → ranked candidates with QIDs. yente serves /reconcile/{dataset} in the same shape. Drive it from Python with reconciler libraries or raw requests; OpenRefine GUI for human-in-the-loop batches.
- **Why:** A common interface so DueCare can reconcile a scraped entity name against ANY reconciliation-compatible source — Wikidata for canonical org IDs, yente for sanctions, a custom registry service — with one client shape. Lets bulk cleanup of scraped registry dumps before screening.

### GDELT GKG Theme Lookup (LOOKUP-GKGTHEMES.TXT)  `free` (unverified)
Authoritative flat list of every GKG theme that has appeared in GDELT, with occurrence counts. Use it to pick the exact uppercase theme strings to filter on (e.g. for forced-labour / trafficking / migration coverage) instead of guessing them.

- **URL:** http://data.gdeltproject.org/api/v2/guides/LOOKUP-GKGTHEMES.TXT
- **Repo:** https://github.com/CatoMinor/GDELT-GKG-Themes
- **License/ToS:** Free/open, same as GDELT.
- **Integrate:** GET the TXT (theme<TAB>count, one per line). Grep for TRAFFIC, SLAVERY, FORCED, BONDED, MIGRAN, SMUGGL, WB_*JOBS, CRISISLEX to assemble your theme allow-list, then pass them to the DOC API (theme:NAME) or filter raw GKG rows. A CSV mirror lives in the CatoMinor repo ('GDELT THEMES LIST.csv') if you prefer to load it as a table. NOTE: the canonical host serves the TXT but currently has a TLS SAN mismatch on data.gdeltproject.org — fetch with cert-name verification relaxed or u
- **Why:** Turns fuzzy adverse-media intent ('exploitation news about this agency') into a concrete, reproducible theme filter — the difference between 30% and 90% recall on corridor-specific coverage.

### yente (OpenSanctions self-hosted matching API)  `free` (unverified)
The open-source FastAPI service that powers api.opensanctions.org. Run it yourself against the free CC-BY-NC bulk data to get name/entity matching, fuzzy scoring, and a /search and /match endpoint without paying for the hosted API. Backed by Elasticsearch/OpenSearch.

- **URL:** https://www.opensanctions.org/docs/yente/
- **Repo:** https://github.com/opensanctions/yente
- **License/ToS:** MIT (the yente software). The DATA it indexes is still CC-BY-NC 4.0 — software license and data license are separate.
- **Integrate:** docker compose up (yente + index). Ingest the free bulk feed, then POST /match/default with FtM query entities (Company/Person) and read scored candidates; GET /search/default?q=name for free-text. Lets DueCare's Python/Playwright pipeline call a local screening endpoint instead of the paid SaaS — keeps sensitive query names on-prem.
- **Why:** Keyless, on-prem sanctions/PEP/debarment screening — fits the migrant-worker privacy boundary (entity names never leave the box) and composes natively with a Python service.

### GLEIF Level 1 + Golden Copy / LEI API (entity resolution backbone)  `free` (unverified)
Global Legal Entity Identifier Foundation: authoritative open registry of legal entities with LEIs, including legal name, registered address, registration authority/company number, and Level 2 parent/ownership relationships. Not an adverse list itself, but the canonical key for de-duplicating and linking employers/agencies across the court and sanctions sources.

- **URL:** https://www.gleif.org/en/lei-data/gleif-golden-copy/download-the-golden-copy
- **License/ToS:** CC0 1.0 (public domain) — fully free for commercial and non-commercial use, no attribution required. Among the most permissive of all these sources.
- **Integrate:** Live search API: GET https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=ACME%20Recruitment (JSON:API). Bulk: Golden Copy file-download API https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest.csv (also XML/JSON; relationship records under rr/repex). Use the LEI + legal name + registered address to canonicalize entities before matching against OpenSanctions/World-Bank/court records.
- **Why:** Resolves 'is this the same agency?' across corridors and links subsidiaries to parents/owners — the glue that turns scattered adverse hits into a coherent entity-risk profile.

### ICIJ Offshore Leaks Database (REST + Reconciliation API)  `free` (verified)
Searchable database of 810,000+ offshore entities (Pandora/Paradise/Bahamas/Panama Papers + Offshore Leaks) linking people and companies across 200+ countries, with officers, intermediaries, and addresses. Exposes a REST API schema and an OpenRefine-compatible Reconciliation API.

- **URL:** https://offshoreleaks.icij.org/
- **License/ToS:** Open Database License (ODbL) for the DB; contents under CC BY-SA. Commercial use permitted WITH mandatory ICIJ attribution and share-alike on derived data.
- **Integrate:** REST schema at https://offshoreleaks.icij.org/schema/oldb and Reconciliation API at https://offshoreleaks.icij.org/docs/reconciliation (point an OpenRefine/Playwright reconcile call at named entities). Snapshot data (records up to 2020), so use for historical link enrichment, not live monitoring.
- **Why:** Beneficial-ownership / shell-company resolution for opaque recruitment brokers and labour-supply intermediaries — surfaces hidden corporate links and offshore exposure behind a flagged migration-world entity.
