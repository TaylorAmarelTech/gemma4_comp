# Kaggle scraping-notebook review (2026-06-13)

> Reviewed Kaggle **kernels** (notebooks that actively scrape/pull data), not
> just static datasets, to learn techniques for the LLM + browser scraper.
> Searched 8 queries (web scraping / selenium / playwright / beautifulsoup /
> scrapy / requests / scrape website / data collection) -> ~39 unique kernels;
> pulled + read the 5 most relevant in depth. Findings drove `scripts/llm_scrape.py`.

## Notebooks read in depth

| Kernel | Stack | Techniques that matter |
|---|---|---|
| `migrantworkerdatahub/ph-website-scraper` | selenium + bs4 + requests + chromedriver, headless, `apt-get` | DOMAIN-relevant (PH). Installs a browser on Kaggle, renders, parses `page_source` with BeautifulSoup. |
| `raedaddala/imdb-scraping-using-crawl4ai` | **crawl4ai** over Playwright, headless | The modern pattern: an LLM extracts structured data from the rendered page — no per-site selectors. Exactly the approach asked for. |
| `dierickx3/kaggle-web-scraping-via-headless-firefox-selenium` | selenium + geckodriver, headless, **`xvfb`**, **screenshot** | How to run a real browser on Kaggle (virtual display via xvfb) and capture **screenshots** — the input for vision extraction. |
| `taylorsamarel/create-bronze-layer-philippines-jurisprudence` | requests + bs4, User-Agent | Operator's own: polite requests + BeautifulSoup -> a "bronze layer" raw store (propose-only staging mirrors this). |
| `cristaliss/selenium-on-kaggle-easy-tutorial` | selenium + chromedriver, headless, `apt-get` | Canonical browser-on-Kaggle bootstrap. |

Other notable kernels in the sweep: `taylorsamarel/flight-apis`,
`taylorsamarel/philippines-laws-and-jurisprudence` (operator's API/scrape
kernels), plus many BeautifulSoup/requests tutorials (IMDb, Amazon, weather,
Fortune 500, Twitter, Google Scholar).

## Techniques distilled

1. **Run a real browser on Kaggle.** `apt-get install -y chromium-driver`
   (or firefox/geckodriver) + headless + `xvfb-run` for a virtual display.
   DueCare's connector instead launches **system Edge via `channel="msedge"`**
   (the bundled chromium crashes on the dev box) — same idea, different binary.
2. **LLM extraction beats per-site selectors** (crawl4ai). Render -> hand the
   model the page -> get structured fields. Generalises to any registry.
3. **Screenshots feed vision.** A page whose DOM is opaque (canvas, images, odd
   markup) is still readable from a picture — and Gemma 4 is multimodal.
4. **Clean the HTML first.** BeautifulSoup (or a stdlib parser) strips
   script/style/nav so the model sees signal, not markup.
5. **Polite + staged.** Identified User-Agent, a raw "bronze" store, review
   before promotion — DueCare's propose-only convention.

## What was adopted -> `scripts/llm_scrape.py`

The crawl4ai pattern + the screenshot recipe + BeautifulSoup cleaning, combined
into one tool: **render (Playwright) -> screenshot (Gemma 4 vision) + clean HTML
(stdlib) -> LLM extract the requested fields as JSON**. The renderer and the
text/vision model callables are injectable (offline-tested); live text + vision
extraction both verified against a real page with `gemma4:31b` via Ollama-cloud.

Browser-on-Kaggle note for a kernel deployment: the `xvfb` + `apt-get` recipe
from `dierickx3` / `cristaliss` is the bootstrap to run `llm_scrape.py` inside a
Kaggle notebook (where system Edge is absent) — install chromium + `playwright
install chromium`, no display needed in headless mode.
