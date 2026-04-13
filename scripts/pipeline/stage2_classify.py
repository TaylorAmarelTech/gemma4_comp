#!/usr/bin/env python3
"""Stage 2: Classify acquired documents using Gemma 4.

Uses Gemma 4 (via Ollama) to classify each document by:
  - Document type (convention, law, report, case study, guidance, news)
  - Relevance to trafficking domains (trafficking, labor, financial, regulatory)
  - Exploitation categories present (BFE, JHE, FCB, PIA, VRV)
  - Geographic scope (countries, corridors)
  - Quality/authority level (primary law, secondary guidance, opinion)

This is a Gemma 4 agentic use case — the model reads documents and
makes classification decisions autonomously.

Usage:
    python scripts/pipeline/stage2_classify.py --input data/acquired_documents/documents.jsonl
    python scripts/pipeline/stage2_classify.py --model gemma4:e4b --max-documents 20
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CLASSIFICATION_PROMPT = """You are a document classifier for a human trafficking prevention system.

Classify this document excerpt. Respond in JSON only:

{{
  "document_type": "<convention|national_law|regulation|court_case|report|guidance|news|academic|ngo_publication>",
  "trafficking_relevance": "<high|medium|low|none>",
  "exploitation_categories": ["<list of: business_framed_exploitation, jurisdictional_hierarchy, financial_crime, victim_revictimization, prompt_injection_amplification>"],
  "countries_mentioned": ["<ISO country codes>"],
  "corridors": ["<origin_destination pairs like PH_HK>"],
  "key_topics": ["<list of 3-5 key topics>"],
  "legal_instruments_cited": ["<list of laws/conventions cited>"],
  "authority_level": "<primary_law|secondary_regulation|international_standard|guidance|opinion|unknown>",
  "summary": "<2-3 sentence summary of the document's relevance to trafficking prevention>"
}}

DOCUMENT EXCERPT:
{text}

JSON CLASSIFICATION:"""


def classify_with_gemma(
    text: str,
    *,
    model: str = "gemma4:e4b",
    host: str = "http://localhost:11434",
) -> dict:
    """Send document to Gemma 4 for classification."""
    import httpx

    prompt = CLASSIFICATION_PROMPT.format(text=text[:3000])  # Cap input

    resp = httpx.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 512, "temperature": 0.0},
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    raw = resp.json().get("message", {}).get("content", "")

    # Parse JSON from response
    import re

    json_match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to parse classification", "raw": raw[:200]}


def classify_heuristic(text: str) -> dict:
    """Fallback heuristic classification (no model needed)."""
    text_lower = text.lower()

    categories = []
    if any(kw in text_lower for kw in ["recruitment fee", "placement fee", "agency fee"]):
        categories.append("business_framed_exploitation")
    if any(kw in text_lower for kw in ["jurisdiction", "cross-border", "bilateral"]):
        categories.append("jurisdictional_hierarchy")
    if any(kw in text_lower for kw in ["money laundering", "financial crime", "proceeds"]):
        categories.append("financial_crime")
    if any(kw in text_lower for kw in ["victim", "survivor", "exploitation", "abuse"]):
        categories.append("victim_revictimization")

    countries = []
    for code, name in [("PH", "philippines"), ("HK", "hong kong"), ("SA", "saudi"),
                       ("QA", "qatar"), ("AE", "emirates"), ("SG", "singapore"),
                       ("MY", "malaysia"), ("NP", "nepal"), ("BD", "bangladesh")]:
        if name in text_lower:
            countries.append(code)

    relevance = "high" if len(categories) >= 2 else "medium" if categories else "low"

    return {
        "document_type": "unknown",
        "trafficking_relevance": relevance,
        "exploitation_categories": categories,
        "countries_mentioned": countries,
        "authority_level": "unknown",
        "summary": f"Heuristic classification: {len(categories)} categories, {len(countries)} countries",
        "classified_by": "heuristic",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "data" / "acquired_documents" / "documents.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "classified_documents" / "classified.jsonl")
    parser.add_argument("--model", default="gemma4:e4b", help="Ollama model for classification")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--max-documents", type=int, default=0, help="0 = all")
    parser.add_argument("--heuristic", action="store_true", help="Use heuristic (no model)")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: {args.input} not found. Run stage1_acquire.py first.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Check Ollama if not heuristic
    use_gemma = not args.heuristic
    if use_gemma:
        try:
            import httpx
            httpx.get(f"{args.host}/api/tags", timeout=5)
        except Exception:
            print(f"Ollama not available at {args.host}. Using heuristic classification.")
            use_gemma = False

    documents = [json.loads(line) for line in args.input.open("r", encoding="utf-8")]
    if args.max_documents > 0:
        documents = documents[:args.max_documents]

    print(f"# Stage 2: Classify documents with {'Gemma 4' if use_gemma else 'heuristics'}")
    print(f"  Input: {len(documents)} documents")

    classified = []
    for i, doc in enumerate(documents):
        text = doc.get("content", "")[:5000]
        print(f"[{i+1}/{len(documents)}] {doc.get('url', '?')[:60]}...")

        if use_gemma:
            t0 = time.time()
            classification = classify_with_gemma(text, model=args.model, host=args.host)
            elapsed = time.time() - t0
            classification["classified_by"] = args.model
            print(f"  → {classification.get('trafficking_relevance', '?')} relevance ({elapsed:.1f}s)")
        else:
            classification = classify_heuristic(text)
            print(f"  → {classification.get('trafficking_relevance', '?')} relevance (heuristic)")

        doc["classification"] = classification
        classified.append(doc)

    # Save
    with args.output.open("w", encoding="utf-8") as f:
        for doc in classified:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    high = sum(1 for d in classified if d["classification"].get("trafficking_relevance") == "high")
    print(f"\n# Complete: {len(classified)} classified ({high} high relevance)")
    print(f"  Saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
