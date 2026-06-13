# GitHub tools for JS-compatible scraping + LLM browsing/searching (survey, 2026-06)

A scouting survey for upgrading DueCare's recruitment pipeline beyond the
current stdlib/curl_cffi fetch — specifically for **JavaScript-rendered**
registries (the DMW inquiry is a Nuxt SPA) and **LLM-powered** browsing/search.
Mapped to the project's constraints and the defensive, propose-only, official-
public-sources-only mission.

> Star counts and licences are approximate, drawn from the 2026 sources cited
> at the bottom; **verify the licence on each repo before adopting** —
> several flipped to AGPL/Business-Source over time.

## Constraints (what "fits" means here)

- The local box is fragile (OneDrive-corrupted system Python); heavy Node
  stacks and model-download deps are avoided locally and pushed to Kaggle/CI.
- Pipeline is deterministic-offline-first; network tools are **optional
  extras** with a stdlib fallback (this is how `curl_cffi` is already wired).
- Mission is **defensive + official/public sources only**: robots-respecting,
  no stealth-against-ToS, no mass crawling, redact before any external LLM.
- Anything LLM-in-the-loop adds per-page cost; the deterministic extractor
  stays the default, LLM extraction is an escalation for hard pages.

## 1. JavaScript / headless-browser rendering (the JS-wall escalation)

| Tool | Lang | Licence (verify) | ~Stars | Fit for DueCare |
|---|---|---|---|---|
| **Playwright** | Python / TS | Apache-2.0 | 60k+ | **GREEN escalation.** The standard for JS-heavy SPAs; Python binding fits the repo. Auto-wait, network interception (can grab the SPA's own JSON XHR directly). Use as an opt-in `--render` path for `_fetch_url` when a page is JS-walled. Heavy (browser download) → Kaggle/CI, not the fragile local box. |
| **Crawl4AI** | Python | Apache-2.0 | 30k+ | **GREEN.** Local-first, LLM-ready **markdown** output, Apache-2.0 (cleaner than Firecrawl's AGPL self-host). Pairs with the pipeline: render → clean markdown → `extract_facts`/`screen`. |
| **nodriver** | Python | AGPL-ish (verify) | 10k+ | YELLOW. Successor to undetected-chromedriver; stealth TLS/CDP. Powerful but the **stealth/anti-detection angle conflicts with the official-sources-only, robots-respecting boundary** — only consider for a public page that blocks a declared UA, never to evade a ToS. |
| **Crawlee** | Node/TS | Apache-2.0 | 17k+ | YELLOW. Best open anti-detection + fingerprint rotation, but Node stack (off the Python path) and anti-detection is mostly unneeded for official pages. |
| Puppeteer | Node | Apache-2.0 | 90k+ | YELLOW. Playwright's predecessor; prefer Playwright-Python. |
| Scrapy | Python | BSD | 53k+ | Context: static/high-volume crawling; not a JS renderer (pair with playwright). Not needed — we don't mass-crawl. |

## 2. LLM-powered browser agents (browse like a human)

| Tool | Lang | Licence (verify) | ~Stars | Fit |
|---|---|---|---|---|
| **browser-use** | Python | MIT (verify) | 50k+ | YELLOW (high-value, heavy). Turns any LLM into a full browser agent (multi-tab, memory); WebVoyager ~89%. Python-native. Genuinely useful for a registry behind a multi-step form the JSON API doesn't expose — but it's LLM-in-the-loop (cost) + a browser. Evaluate as an operator-side tool, not the default path. |
| **Skyvern** | Python | AGPL-3.0 (verify) | 13k+ | YELLOW. **Vision-first** (reads screenshots, not DOM) → resilient to DOM changes, best at **form-filling** (the DMW inquiry is a search form). AGPL + vision-LLM cost are the catches. |
| **Stagehand** | TS | MIT (verify) | 14k+ | YELLOW. Clean `act/extract/observe/agent` primitives on Playwright, but TypeScript — off the repo's Python stack. |
| Agent-E / LaVague / Nanobrowser | mixed | mixed | — | Watch. DOM-based agents / browser-extension agents; smaller, less proven. |

DOM-based (browser-use, Stagehand, Agent-E) are cheaper/faster; vision-first
(Skyvern) survives DOM churn but needs a vision model. For DueCare, prefer
**grabbing the SPA's JSON XHR with Playwright network-interception** over a
full LLM agent — same result, no per-page model cost.

## 3. LLM-powered extraction (page → structured data by prompt)

| Tool | Lang | Licence (verify) | ~Stars | Fit |
|---|---|---|---|---|
| **ScrapeGraphAI** | Python | MIT | 23k+ | **GREEN escalation.** NL-prompt extraction; **BYO-LLM incl. local Ollama** (no external egress) → fits the privacy boundary. Use as the optional LLM-assisted extractor for pages the deterministic `extract_facts` can't parse; redact first, prefer local Gemma/Ollama. |
| **llm-reader** (m92vyas) | Python | MIT | small | GREEN (lightweight). Webpage → LLM-friendly text, MIT, Firecrawl/Jina-Reader alternative. A tiny dependency to normalize a rendered page before extraction. |
| **Firecrawl** | TS | **AGPL-3.0 self-host** | 30k+ | RED for embedding. Great crawl→markdown, but the self-host licence is **AGPL** — incompatible with this MIT repo. Use only as an external API the operator runs, never vendored. |
| Jina Reader (`r.jina.ai`) | API | — | — | YELLOW. Keyless URL→markdown API; convenient but external egress (only public pages). |

## 4. LLM-powered browsing/searching (discovery + answer engines)

| Tool | Lang | Licence (verify) | ~Stars | Fit |
|---|---|---|---|---|
| **SearxNG** | Python | AGPL-3.0 | 17k+ | **GREEN (self-hosted sidecar).** Privacy metasearch aggregating many engines, keyless, no tracking. A strict upgrade to the current keyless-DDG `discover_candidates` — more sources, more robust. Run as the operator's own instance (AGPL is fine for a separate self-hosted service, not vendored). |
| **Perplexica** (now "Vane") | TS | MIT | 33k+ | YELLOW. Open Perplexity alternative = SearxNG + an LLM; **runs 100% local with Ollama**. A good operator-side "ask the web" console for an investigator, but a Docker/Next.js service, not a library to embed. |
| Morphic | TS | — | — | RED. Vercel + OpenAI lock-in; not truly self-hostable/local. |

## Recommended integration into the existing pipeline

The pipeline is `discover → fetch → extract → screen → verify`. Concrete, low-
risk upgrades that keep the deterministic core and add optional escalations:

1. **`discover` → SearxNG.** Add a `searxng` backend to `discover_candidates`
   (operator points at their self-hosted instance via env). Keeps the keyless
   DDG path as the zero-config fallback. **GREEN.**
2. **`fetch` → Playwright/Crawl4AI `--render` escalation.** When a page is a
   JS wall (empty body / SPA shell, like the DMW Nuxt page), an opt-in render
   path returns the hydrated HTML — or, better, intercepts the SPA's own JSON
   XHR. Heavy dep → Kaggle/CI or an operator box, never the fragile local one.
   **GREEN, optional extra.**
3. **`extract` → ScrapeGraphAI + local Ollama escalation.** For pages the
   deterministic `extract_facts` can't parse, an opt-in LLM extractor with a
   **local** model (no external egress); redact first. Deterministic stays the
   default. **GREEN, optional.**
4. **Operator console → Perplexica (local).** For an investigator who wants to
   "ask the web" interactively. Sidecar, not embedded. **YELLOW.**

## What to avoid

- **Firecrawl self-host (AGPL)** vendored into this MIT repo — licence
  conflict. External-API use by the operator only.
- **Stealth/anti-detection** (nodriver, Crawlee fingerprinting) used to evade a
  site's ToS — off-mission. Official/public sources + robots only.
- **Model-download / heavy-browser deps on the local box** — push to Kaggle/CI.
- **LLM-in-the-loop as the default** — keep it an escalation; the deterministic
  GREP/extractor path is cheaper, auditable, and offline.

## Sources

- Firecrawl — Best Open-Source Web Scraping Libraries / Crawlers 2026:
  <https://www.firecrawl.dev/blog/best-open-source-web-scraping-libraries>,
  <https://www.firecrawl.dev/blog/best-open-source-web-crawler>,
  <https://www.firecrawl.dev/blog/best-browser-agents>
- Apify — Top open-source web crawlers 2026:
  <https://blog.apify.com/top-11-open-source-web-crawlers-and-one-powerful-web-scraper/>
- awesome-autonomous-web: <https://github.com/Agent-Tools/awesome-autonomous-web>
- AIMultiple — Open Source Web Agents 2026: <https://aimultiple.com/open-source-web-agents>
- Framework wars (browser-use / Stagehand / Skyvern):
  <https://dev.to/stevengonsalvez/browser-tools-for-ai-agents-part-2-the-framework-wars-browser-use-stagehand-skyvern-4gn>
- Stagehand: <https://github.com/browserbase/stagehand> · Skyvern:
  <https://github.com/skyvern-ai/skyvern> · browser-use:
  <https://github.com/browser-use/browser-use> · Crawlee:
  <https://github.com/apify/crawlee>
- ScrapeGraphAI: <https://scrapegraphai.com/blog/api-crawl-for-ai> · llm-reader:
  <https://github.com/m92vyas/llm-reader>
- Perplexica: <https://github.com/ItzCrazyKns/Perplexica> · SearxNG topic:
  <https://github.com/topics/searxng>
- eesel — Firecrawl alternatives 2026: <https://www.eesel.ai/blog/firecrawl-alternatives>
