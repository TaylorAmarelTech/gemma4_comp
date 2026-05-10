# Duecare Harness — safety + grounding + audit trace

**Status: Built — this is the Kaggle submission.** Lives in
`packages/duecare-llm-chat/src/duecare/chat/`.

The Harness is the "why should I trust this?" layer. It turns Gemma
from a chatbot into an **auditable decision-support system**.

## Responsibilities

- Detect risk (deterministic regex + KB rules).
- Retrieve context (BM25 + optional dense + RRF + 1-hop citation graph).
- Structure evidence into the model's prompt.
- Ground model responses (citations, indicators, statutes).
- Prevent unsafe or ungrounded output (response policy).
- Produce audit traces (per-layer ms + final merged prompt + Gemma response).
- Provide deterministic, inspectable reasoning support around Gemma.

## Submodules (current count)

| Submodule | What | Where |
|---|---|---|
| Anonymizer | PII strip / generalize before storage / sharing | `harness/__init__.py` (planned curator block) |
| GREP / rule engine | 161 hand-curated regex rules across 31 categories | `harness/__init__.py` `GREP_RULES` |
| RAG database | 46-doc curated legal corpus + 46-edge citation graph | `harness/__init__.py` `RAG_CORPUS` + `_citations.json` |
| Tool layer | 5 function-calling lookups + 72 backing-table rows | `harness/__init__.py` `_TOOL_DISPATCH` + `CORRIDOR_FEE_CAPS` etc. |
| Contacts directory | 26-entry curator-block | `harness/_contacts.json` |
| Prompt / context builder | Converts signals + RAG into model context | `app.py` chat pipeline |
| Response policy | Bounds model behavior; no unsafe advice | persona + harness pre-context |
| Trace / audit layer | `▸ View pipeline` modal | `app.py` + `static/index.html` |
| Case summary layer | Reviewable intake notes (classifier surface) | `harness/__init__.py` classifier examples |

## Six harness layers (toggleable in chat UI)

| Layer | Color | Description |
|---|---|---|
| Persona | purple | 40-year anti-trafficking expert system prompt; user-extendable |
| GREP | red | 161 regex rules across 31 categories |
| RAG | blue | 46-doc corpus + 46-edge citation graph (BM25 + optional dense + RRF) |
| Imports | teal | User-attached evidence (images / docs / posts) |
| Tools | green | 5 function-calling lookups |
| Online | amber | Live web search (Brave / DDG fallback / Playwright) with cross-check warning |

## 11 dedicated viewer pages

`/static/harness.html` (landing) → `persona.html` · `grep-rules.html`
(sortable, severity filter, fire-count leaderboard, click-to-expand
patterns, category histogram) · **`grep-tester.html` (live regex
tester — paste any text, see which rules fire, no LLM call)** ·
`rag-corpus.html` (jurisdiction chips across 27 groups, citation
neighbors, recently-retrieved overlay) · `rag-graph.html`
(force-directed SVG, arrowheads, search, zoom/pan, ⬇ SVG export) ·
`tools.html` · `online.html` · **`hotlines.html` (26-entry contact
directory, click-to-call / mailto / form-URL, "the user submits — we
never auto-send" safety banner)** · **`search.html` (cross-layer
search across persona / GREP / RAG / tools)**.

## Single source of truth (v0.14.5)

`_brand.py` owns: product name, tagline, privacy promise, layer
metadata (key + label + color + short_desc + description +
viewer_path), version stamps, severity palette, jurisdiction
grouping (28 prefix → group rules), copy text. Exposed via
`/api/brand`. Adding a new layer or renaming a label is a one-file
edit.

## API surface

```
GET  /api/brand                — single source of truth
GET  /api/version              — chat-package + harness counts + 13 curator-block index
GET  /api/health-check         — wired layers + model info
GET  /api/rag/graph            — 46 nodes + 46 edges + jurisdiction groups
GET  /api/harness-catalog/{persona|grep|rag|tools|online}
POST /api/grep/test            — paste text, get firing rules
GET  /api/search-all?q=        — federated cross-layer search
GET  /api/contacts             — directory with corridor / country / category / language filters
GET  /api/governance{,/<name>} — curator-block index + raw JSON
```

## What it serves to each canonical lane

- **Platform safety:** moderation risk trace via `/api/grade` + per-message `▸ View pipeline` audit.
- **NGO & regulator:** case-intake console (the chat surface) + classifier surface + 26-entry contacts + `/static/hotlines.html`.
- **Individual worker / mobile:** 11-language analog classifier + 5 colored quick-action buttons + Imports for evidence attach.
- **Researcher:** 46-dim universal rubric + `/api/grade-deep` LLM-judge + reproducibility notebooks.
- **Developer / integration partner:** API endpoints, schema contracts, and trace payloads for embedding the harness in custom products.
