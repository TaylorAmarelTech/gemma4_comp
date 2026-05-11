# Maintaining the Online search layer

> The Online layer is a fallback web-search hook that fires when
> the local corpus is silent on a topic. This guide explains how to
> configure providers, add a new provider, and the BYOK (bring
> your own key) flow for cloud APIs.

## Where the layer lives

The online layer is **kernel-side** (not in the chat package wheel).
Each kernel.py defines its own `online_search_call` and registers it
with the FastAPI app.

```
kaggle/<slug>/kernel.py
↓
def _online_search(query: str, top_n: int = 5) -> dict:
    """Returns {results: [{rank, title, url, snippet}], source, elapsed_ms}"""
    ...

app.state.online_search_call = _online_search
```

The chat package's harness module receives a callable; it doesn't
care which provider implements it.

## Provider chain (bundled defaults)

| Provider | Cost | API key needed | Notes |
|---|---|---|---|
| **DuckDuckGo HTML** | Free | No | Default fallback. HTML-scrape, no API. Rate-limited; flaky. |
| **Wikipedia** | Free | No | First-class encyclopedia search. Stable. |
| **Brave Search** | Free tier 2k/mo | Yes (`BRAVE_API_KEY`) | High-quality results, fast |
| **Tavily** | Free tier 1k/mo | Yes (`TAVILY_API_KEY`) | LLM-optimised search, AI-summarised results |
| **Serper** | Free tier 2.5k/mo | Yes (`SERPER_API_KEY`) | Google search wrapped |
| **Playwright agentic** | Free | No (browser only) | Real-browser scraping. Slow (~10s) but bypasses bot detection. Used in A-09 appendix. |
| **Custom URL fetch** | Free | No | Direct httpx GET on a URL the user supplies |

The bundled order in `kaggle/01-duecare-exploration-workbench/kernel.py`:

1. Try Tavily if `TAVILY_API_KEY` set
2. Try Brave if `BRAVE_API_KEY` set
3. Try Serper if `SERPER_API_KEY` set
4. Fall back to DuckDuckGo HTML
5. Always check Wikipedia in parallel (cheap; merges into results)

## When to add a provider

Good triggers:

- **Better quality for a specific domain.** Example: legal
  databases (CaseText, LexisNexis) for jurisprudence research.
- **Better quality for a region.** Example: Yandex for
  Russian-language sources.
- **Bypass rate limit.** When DuckDuckGo + Wikipedia hit ratelimit
  during a heavy demo session.

Bad triggers:

- "I want this one specific URL." Use the URL fetch tool, not a
  new provider.
- "I want a smarter LLM-search." Use Tavily — it already does that.

## How a search call flows

```
USER PROMPT (e.g., "What's the latest POEA enforcement on agency X?")
    ↓
toggles.online == True
    ↓
_online_search(query=text, top_n=5)
    ↓
Provider chain (try in order, merge results):
  1. Tavily  → 3 results
  2. Brave   → 5 results
  3. Wikipedia → 1 result
  Total → top 5 by relevance score
    ↓
{"results": [{rank, title, url, snippet}, ...], "source": "tavily+wikipedia",
 "elapsed_ms": 1234}
    ↓
prepended to Gemma's context as:
  "Online search results (treat as candidate evidence; require
   URL attribution; do not assume ground truth):
   [1] (tavily) https://... — POEA penalises agency X...
   [2] (brave) https://... — Agency X license suspended..."
```

The model is explicitly told to **treat results as candidate
evidence requiring URL attribution**, not as ground truth — this is
load-bearing because online search returns adversarial /
hallucinated content sometimes.

## Provider response shape (contract)

Every provider must return:

```python
{
    "results": [
        {
            "rank":    1,                    # int, 1-indexed
            "title":   "Article title",      # string
            "url":     "https://...",         # string, must be a real URL
            "snippet": "First 200 chars...",  # string, ~150-300 chars
            "source":  "tavily"               # which provider produced this
        },
        ...
    ],
    "source":     "tavily+brave+wikipedia",   # comma-joined providers used
    "elapsed_ms": 1234
}
```

A provider that fails should **return empty results**, not raise.
The dispatcher catches the empty list and falls through to the
next provider in the chain.

## Adding a new provider

Example: adding a CaseText-style legal-search provider.

### Step 1: Implement the provider function

```python
import httpx

def _search_casetext(query: str, top_n: int = 5) -> dict:
    """Provider function. Same contract as DuckDuckGo / Tavily / etc."""
    api_key = os.getenv("CASETEXT_API_KEY")
    if not api_key:
        return {"results": [], "source": "casetext_disabled"}
    try:
        r = httpx.get(
            "https://api.casetext.com/search",
            params={"q": query, "limit": top_n},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if r.status_code != 200:
            return {"results": [], "source": "casetext_error"}
        data = r.json()
        return {
            "results": [
                {
                    "rank":    i + 1,
                    "title":   item["case_name"] + " — " + item["citation"],
                    "url":     item["url"],
                    "snippet": item["holding"][:300],
                    "source":  "casetext"
                }
                for i, item in enumerate(data.get("cases", [])[:top_n])
            ],
            "source":     "casetext",
            "elapsed_ms": int((r.elapsed.total_seconds()) * 1000),
        }
    except Exception as e:
        return {"results": [], "source": f"casetext_error: {type(e).__name__}"}
```

### Step 2: Add to the provider chain

```python
def _online_search(query: str, top_n: int = 5) -> dict:
    """Compose providers in order; merge results."""
    all_results = []
    sources = []
    elapsed = 0
    # Try high-quality first
    for provider_fn in [
        _search_tavily, _search_brave, _search_serper,
        _search_casetext,  # NEW
        _search_duckduckgo,
    ]:
        r = provider_fn(query, top_n=top_n)
        if r["results"]:
            all_results.extend(r["results"])
            sources.append(r["source"])
            elapsed += r.get("elapsed_ms", 0)
            if len(all_results) >= top_n:
                break
    # Always parallel-merge Wikipedia
    wiki = _search_wikipedia(query, top_n=2)
    if wiki["results"]:
        all_results.extend(wiki["results"])
        sources.append("wikipedia")
    # Truncate + return
    return {
        "results":    all_results[:top_n],
        "source":     "+".join(sources),
        "elapsed_ms": elapsed,
    }
```

### Step 3: BYOK config

Document the env var in `docs/maintenance/online_search.md` (this
file). Users set `CASETEXT_API_KEY` in their Kaggle secrets and the
provider activates automatically.

### Step 4: Test

```python
def test_casetext_provider_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("CASETEXT_API_KEY", raising=False)
    r = _search_casetext("passport retention HK", top_n=5)
    assert r["results"] == []
    assert "casetext_disabled" in r["source"]
```

## Configuring providers per-deployment

Three configuration paths:

### Path 1: Kaggle Secrets (recommended)

In the Kaggle notebook editor:
- **Add-ons → Secrets → New Secret**
- Add: `BRAVE_API_KEY`, `TAVILY_API_KEY`, `SERPER_API_KEY`, etc.
- The kernel.py reads via `os.getenv("BRAVE_API_KEY")`

### Path 2: Environment variable in the kernel cell

```python
import os
os.environ["TAVILY_API_KEY"] = "..."  # before create_app()
```

### Path 3: HF Space or VPS deployment

Use the platform's secrets manager. For HF Spaces:
- **Settings → Variables and Secrets**
- Add the secret + redeploy

## Rate limits + reliability

- **DuckDuckGo HTML:** ~30 req/min before HTML-blocked. Switches to
  empty-results gracefully.
- **Wikipedia:** ~20 req/sec before throttle. Almost never hit in
  practice.
- **Brave:** 2k/mo on free tier. Burst-limited at ~5/sec.
- **Tavily:** 1k/mo on free tier. ~3/sec.
- **Playwright agentic:** Slow (~10s per query). No rate limit.
  Skips bot detection.

The provider chain handles transient failures: any provider that
returns empty is skipped, falling through to the next.

## Privacy implications

Online search inherently sends the worker's prompt to a third-party
provider. **By default, the Online layer is OFF.** When a user
toggles it on, they're consenting to send the prompt to whichever
providers are configured.

For privacy-first deployments (Topology D — Android on-device):
- **Don't enable Online.** Use Persona + GREP + RAG + Tools only.
- The on-device LLM has the bundled corpus; current statutes are
  only as fresh as the last RAG corpus update.

For NGO deployments (Topology B):
- Enable Online but configure ONLY corporate-tier providers (Brave
  paid tier, Tavily paid tier) where the request is not used for
  ad targeting.
- Document which provider is configured in the NGO's privacy
  posture.

## Common pitfalls

1. **Provider raises instead of returning empty.** Wrap every API
   call in try/except; return `{"results": [], ...}` on error.

2. **No timeout on httpx.** A slow provider blocks the whole chat
   request. Always set `timeout=10.0` or shorter.

3. **No URL attribution in the prepended context.** The model can't
   distinguish between providers if the URL isn't surfaced. Always
   include `url` in the snippet text Gemma sees.

4. **Cache busting.** Some providers return stale cached results.
   For news/current-events queries, append `&fresh=24h` or
   equivalent if the provider supports it.

5. **Treating online results as authoritative.** The model is
   instructed NOT to do this; the prepended context says "treat
   as candidate evidence requiring URL attribution". Don't override
   that instruction in your persona.

## See also

- [`grep_rules.md`](grep_rules.md) — GREP fires before Online; if
  GREP catches a pattern, the model often doesn't need Online
- [`rag_corpus.md`](rag_corpus.md) — RAG is the static-corpus
  alternative to Online; when in doubt, prefer RAG (it's offline +
  authoritative)
- [`../component_diagram.md`](../component_diagram.md) — how Online
  fits in the layer order
