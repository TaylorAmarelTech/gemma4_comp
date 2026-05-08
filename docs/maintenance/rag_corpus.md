# Maintaining the RAG corpus

> The RAG layer is BM25 retrieval over a 46-doc in-kernel corpus of
> ILO conventions, national statutes, and NGO briefs. This guide
> explains how to add new documents, refresh amended ones, and
> handle the BM25 reindex cycle.

## Where the corpus lives

```
packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
↓
RAG_CORPUS = [
    {
        "id":     "ilo_c181_art7",
        "title":  "ILO C181 Art. 7 — Private Employment Agencies",
        "snippet": "...",     # ~600-1500 chars indexed for retrieval
        "full_text": "...",   # full document body (used for citation context)
        "source": "https://www.ilo.org/dyn/normlex/en/...",
        "topic":  "private_employment_agencies",
        "jurisdiction": "ILO"
    },
    ...
]
```

**Status:** Currently still inline Python. A v3.7 task is to migrate
to `_rag_corpus.jsonl` (one doc per line) for stakeholder PRs
without Python edits.

## What's in the corpus today

The 46 docs cluster into:

- **ILO conventions** (12 docs) — C029, C095, C097, C143, C181,
  C188, C189, C190, P029, R201, ILO conference resolution
- **PH** (4 docs) — RA 8042, RA 10022, RA 9208, POEA MC 14-2017
- **HK** (4 docs) — Cap. 57 (Employment Ord), Cap. 163 (Money
  Lenders), Cap. 57A (Employment Agency Reg), Cap. 200 (Crimes Ord)
- **ID** (2 docs) — BP2MI Reg 9/2020, Permenaker
- **NP / BD** (3 docs) — Nepal FEA, BD OEA, NP cabinet decisions
- **Gulf** (5 docs) — Saudi MoHR, Saudi LRI 2024, Lebanon Cabinet
  Decree 13166/2021, Kuwait Decree 19/2018, Qatar reforms 2018-2020
- **International** (3 docs) — Palermo Protocol, ICRMW, FATF Rec. 32

## When to add a document

Good triggers:

- **Major statute amendment.** Example: in 2022 RA 11641 elevated
  POEA from a regulator to a cabinet-level Department of Migrant
  Workers; needs a dedicated doc.
- **New corridor + controlling instrument.** Example: when adding
  Vietnam-Japan corridor coverage, need Vietnam Migrant Worker Act
  69/2020.
- **Authoritative NGO brief that's frequently cited.** Example:
  Polaris Typology of Modern Slavery 2017.
- **Court decision that sets a binding interpretation.** Example: a
  Hong Kong Court of Final Appeal decision on bond requirements.

Bad triggers:

- News articles, blog posts, opinion pieces — these don't belong in
  RAG. Use the Online layer instead (live web search).
- A document that's only relevant to one corridor when corridor-
  specific knowledge is already in the GREP rules. The GREP rules
  flag the corridor; the RAG provides the citation; both are
  needed but for different layers.

## How retrieval works

```
USER PROMPT
    ↓
_rag_call(prompt_text, top_k=5)
    ↓
1. Tokenize prompt + each corpus doc snippet
2. BM25 score each doc against the prompt
3. Return top-k docs sorted by score
    ↓
{"docs": [{"id", "title", "snippet", "source"}, ...], "elapsed_ms"}
    ↓
prepended to Gemma's context as:
    "RAG sources:
     ### ILO C181 Art. 7 — Private Employment Agencies
     [snippet text]
     ..."
```

The model is instructed to cite by `id` or `title`; the citation
grounding check (`_check_citations_against_corpus`) verifies the
citation exists in this corpus + the `_AUTHORITATIVE_STATUTES_ALLOWLIST`.

## Document format

```python
{
    # 1. Stable id used for grounding checks + tests
    "id":        "ilo_c181_art7",

    # 2. Human-readable title for the citation header
    "title":     "ILO C181 Art. 7 — Private Employment Agencies",

    # 3. Snippet — INDEXED for BM25 retrieval, surfaced to the model
    "snippet":   "Article 7 of ILO Convention No. 181 (1997)...",

    # 4. Full text — full document body. Used for follow-up citation
    #    context when the model asks for more detail.
    "full_text": "Convention No. 181 — Convention concerning Private...",

    # 5. Source URL — the official authoritative source
    "source":    "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_INSTRUMENT_ID:312326",

    # 6. Topic — used for filtering in the harness inspector
    "topic":     "private_employment_agencies",

    # 7. Jurisdiction — for the multi-jurisdiction-coverage dim
    "jurisdiction": "ILO"  # ILO | PH | HK | ID | NP | BD | SA | AE | QA | KW | LB | UN | EU | US | doctrine
}
```

## Snippet length

The snippet is indexed for retrieval AND surfaced to the model.
Tradeoff:

- **Too short** (< 200 chars): retrieval hit rate drops; model may
  not have enough context to cite properly.
- **Too long** (> 2000 chars): every retrieval blows the context
  window; latency increases; the model paraphrases instead of
  citing precisely.
- **Sweet spot:** 600-1500 chars per snippet. Pull the operative
  paragraphs (the article text itself, not the preamble).

## Adding a document (workflow)

1. **Verify it doesn't already exist:**
   ```bash
   grep -E "ra_11641|department.*migrant.*workers" packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
   ```

2. **Find an authoritative source URL.** Prefer the official
   government / ILO / NGO portal; avoid third-party PDF mirrors.

3. **Extract the operative paragraph(s)** — the actual article text
   that establishes the rule. Trim preamble, recitals, transitional
   provisions.

4. **Add to `RAG_CORPUS`:**
   ```python
   {
       "id":        "ra_11641_dmw_act",
       "title":     "RA 11641 — Department of Migrant Workers Act 2021",
       "snippet":   "Section 3 of Republic Act No. 11641 establishes...",
       "full_text": "[full text from official source]",
       "source":    "https://lawphil.net/statutes/repacts/ra2021/ra_11641_2021.html",
       "topic":     "ph_migrant_worker_governance",
       "jurisdiction": "PH"
   }
   ```

5. **Add to `_authoritative_statutes.json`** so the grader recognises
   citations to this statute as authoritative:
   ```json
   {"name": "ra 11641", "jurisdiction": "PH", "topic": "department of migrant workers act",
    "added_by": "your-name", "added_date": "2026-05-15", "rationale": "Supersedes POEA MC 14-2017 framework"}
   ```

6. **Add to `_known_statute_sections.json`** with the section range
   so the grader catches "RA 11641 §99" hallucinations:
   ```json
   {"key": "ra 11641", "min": 1, "max": 38, "name": "PH Department of Migrant Workers Act 2021"}
   ```

7. **Run the validator:**
   ```bash
   python scripts/validate_curator_blocks.py
   python scripts/verify.py
   ```

8. **Add a smoke test** that this doc retrieves on a relevant prompt:
   ```python
   def test_rag_retrieves_ra_11641_on_dmw_prompt() -> None:
       h = _load_harness()
       r = h._rag_call("What is the Department of Migrant Workers Act?", top_k=5)
       ids = {d["id"] for d in r["docs"]}
       assert "ra_11641_dmw_act" in ids
   ```

9. **PR.** Reviewer: jurist for the legal claim + methodologist for
   the snippet quality.

## Refreshing an amended document

When a statute is amended:

1. **Keep the old document** with `last_amended` and `superseded_by`
   metadata.
2. **Update the snippet** to reflect the current text + flag the
   amendment.
3. **Add the amending instrument** as a new doc.
4. **Cross-reference** in both directions.

Example — RA 8042 (1995) amended by RA 10022 (2010):

```python
# Original
{
    "id":        "ra_8042",
    "title":     "RA 8042 — Migrant Workers Act 1995 (as amended)",
    "snippet":   "Section 6 prohibits illegal recruitment...",
    "full_text": "...",
    "source":    "https://lawphil.net/statutes/repacts/ra1995/ra_8042_1995.html",
    "topic":     "ph_migrant_worker_governance",
    "jurisdiction": "PH",
    "last_amended": "2010 (RA 10022)",
    "amended_by":   "ra_10022"
},
# Amending instrument
{
    "id":        "ra_10022",
    "title":     "RA 10022 — Amendment to RA 8042 (2010)",
    "snippet":   "Section 15 imposes joint-and-several liability...",
    "full_text": "...",
    "source":    "https://lawphil.net/statutes/repacts/ra2010/ra_10022_2010.html",
    "topic":     "ph_migrant_worker_governance",
    "jurisdiction": "PH",
    "amends": "ra_8042"
}
```

## Reindexing BM25

The BM25 index is built on-the-fly per request (the corpus is small;
no pre-indexing needed). When you add or modify a doc, no reindex
step is required — the next request picks up the change.

For larger corpora (>200 docs), pre-indexing into a sklearn
TfidfVectorizer or a simple inverted index would reduce latency.
**Currently out of scope** because 46 docs fits comfortably.

## How big can the corpus get?

- **At 50 docs:** retrieval latency ~30ms (acceptable)
- **At 200 docs:** retrieval latency ~150ms (still OK)
- **At 1000 docs:** need to switch to pre-indexed retrieval (~30ms)
- **At 10000 docs:** vector embeddings + FAISS becomes worthwhile

Current 46 docs is well below the inflection point. Add docs freely.

## Common pitfalls

1. **Snippet too long.** Trim to operative text only. Preamble and
   recitals don't help retrieval.

2. **Multiple articles in one doc.** Better to have separate docs
   per article (`ilo_c181_art7`, `ilo_c181_art8`, etc.) than one
   monolithic `ilo_c181`. Per-article docs retrieve more precisely.

3. **No `source` URL.** The grader's `provenance_per_claim` dim
   checks for inline source citation; if your doc has no source,
   the model can't cite it.

4. **Source URL is paywalled or proprietary.** Use a free authoritative
   source (lawphil.net, ilo.org, etc.) over a paid law-firm summary.

5. **Forgetting to add to `_authoritative_statutes.json`.** If the
   doc is in RAG but the statute isn't on the allowlist, the
   grader's citation-grounding check will FALSELY flag citations
   to it.

## See also

- [`grep_rules.md`](grep_rules.md) — companion GREP rules that
  flag prompts where this doc should retrieve
- [`../contributing_curator_blocks.md`](../contributing_curator_blocks.md)
  — for the curator-JSON edits (allowlist + section ranges)
- [`../component_diagram.md`](../component_diagram.md) — how the
  RAG layer fits in the request flow
