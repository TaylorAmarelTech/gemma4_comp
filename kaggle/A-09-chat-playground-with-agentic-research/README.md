# DueCare — Agentic-research chat (BYOK + Playwright) (#A09 appendix)

**Proof-of-concept.** Same chat playground as
`chat-playground-with-grep-rag-tools`, with a **fifth toggle tile**
for agentic web research. Demonstrates that GREP / RAG / Tools can
be supplemented with on-demand web search to pull fresh context that
isn't in the bundled knowledge base.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)).
Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research *(TBD)* |
| **Title** | "Duecare Chat Playground with Agentic Research" |
| **Slug** | `taylorsamarel/duecare-chat-playground-with-agentic-research` |
| **Wheels dataset** | `taylorsamarel/duecare-chat-playground-with-agentic-research-wheels` *(TBD)* |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b,26b-a4b,31b}-it/1` |
| **GPU** | T4 ×2 (default E4B-it; works on single T4) |
| **Internet** | **REQUIRED** (the agentic loop calls the web) |
| **Secrets** | `HF_TOKEN` |
| **Expected runtime** | ~30 sec startup; ~10-15 sec per chat turn with agentic ON |

## What's new vs `chat-playground-with-grep-rag-tools`

A 5th toggle tile (orange — Agentic Research) added next to the
existing 4 (Persona / GREP / RAG / Tools). When ON:

1. Before Gemma generates the chat response, an **inner loop** runs
   (max 5 steps).
2. **Step 1:** Gemma reads the user question and decides whether the
   web is needed at all (responds with strict JSON: `{"action": "done"}`
   or `{"action": "tool", "tool": "<name>", "args": {...}}`).
3. **Step 2-5:** if Gemma chose a tool, the tool runs, the result is
   summarized into the agent's working context, and Gemma is asked to
   decide again.
4. When Gemma says `done` (or step-limit hits), the accumulated
   findings are appended to the pre-context Gemma sees alongside
   GREP / RAG / Tools — same shape as the existing layers.

The agent steps + the merged pre-context are surfaced in a side panel
so judges can see exactly which queries fired and which URLs were
fetched.

## Search tools (real browser default + BYOK fast paths)

All tools live in `packages/duecare-llm-research-tools/src/duecare/research_tools/`.

**No-key default — `BrowserTool` (Playwright + headless Chromium):**

| Engine | Real browser URL | Notes |
|---|---|---|
| Brave | `search.brave.com/search?q=...` | default; full real browsing |
| DuckDuckGo | `duckduckgo.com/html/?q=...` | alternative |
| Ecosia | `ecosia.org/search?q=...` | alternative |

The agent doesn't just scrape — it can `navigate(url)`, `click(selector)`,
`fill(selector, value)`, `extract_text(selector?)`, `get_links()`, and
`screenshot()` (returns base64 PNG that Gemma 4 can read multimodally).

**BYOK — bring-your-own-key fast paths (optional, paste in UI panel):**

| Backend | Free tier | Latency | Where to get a key |
|---|---|---|---|
| Tavily | 1000/mo, no card | ~200-400 ms | https://app.tavily.com |
| Brave Search API | 2000/mo (CC required) | ~200-400 ms | https://api.search.brave.com |
| Serper (Google) | paid (~$50/100k) | ~200-400 ms | https://serper.dev |

**Keys are stored ONLY in your browser's localStorage**, sent on each
`/api/chat` request as a `byok_keys` dict. Nothing is persisted
server-side or written to Kaggle Secrets. Click "Clear all" in the
BYOK panel to wipe them from your machine.

The dispatcher's precedence per turn: `tavily key` > `brave key` >
`serper key` > BrowserTool (Playwright) > DuckDuckGo HTML (last resort).

**Other always-available tools:**

| Tool | Notes |
|---|---|
| `web_fetch` | Fetch + extract Markdown via `trafilatura` (stdlib fallback) |
| `wikipedia` | Wikipedia REST API — best for ILO conventions, statutes |

## Privacy: hard PII gate + audit log

Every outbound query passes through `PIIFilter` BEFORE the network call:

- Rejects emails, passport numbers, phone numbers, financial accounts
- Rejects honorifics ("Mr ", "Dr ", "Atty ", etc.)
- Rejects 2-3 word capitalised name pairs unless explicitly whitelisted
  as a public organisation (e.g. recruitment agencies in a government
  registry)
- Logs every search to `/kaggle/working/duecare_search_audit.jsonl`
  with **only the sha256 hash** of the query (never plaintext) +
  timestamp + backend + result count + pii_blocked flag

A "🔒 PII filter ACTIVE" badge sits at the top of the UI and a
"View search audit" button surfaces the recent log so you can see
exactly what queries left the box (by hash, not content).

## Why this is APPENDIX, not core

- Adds ~10 sec latency per agentic turn (vs ~2 sec for GREP/RAG/Tools-only)
- Requires Internet ON (the other 4 chat toggles work offline)
- Doesn't replace the bundled harness; it *supplements* it
- The live-demo (#6) doesn't depend on this — judges can verify the
  full submission without ever loading this kernel

This is a **proof** that agentic web research integrates cleanly with
the existing harness. If it lands well, it gets folded into the
live-demo's Tools dispatch as a 5th tool (alongside the 4 in-house
lookup functions).

## Files in this folder

```
chat-playground-with-agentic-research/
├── kernel.py              ← source-of-truth (paste into Kaggle)
├── notebook.ipynb         ← built artifact
├── kernel-metadata.json   ← Kaggle kernel config
├── README.md              ← this file
└── wheels/                ← dataset-metadata.json (3 wheels: core, models, chat,
                              + duecare-llm-research-tools when published separately)
```

## Status

**Built 2026-04-29.** The agentic loop, the 3 web tools, and the chat
UI all work end-to-end. The wheels dataset
(`duecare-chat-playground-with-agentic-research-wheels`) needs 3
wheels uploaded: `duecare-llm-core`, `duecare-llm-models`,
`duecare-llm-chat`. The research tools (`duecare-llm-research-tools`)
are pulled in transitively via the chat package's deps.

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#A09 appendix — Agentic-research chat (BYOK + Playwright)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-harness-chat/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Original 4-toggle subset playground](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Gemma generates evaluation prompts](../A-06-prompt-generation/README.md)
- [#A07 appendix: Unsloth fine-tune + GGUF export pipeline](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- **[#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)**
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Grading-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
