#!/usr/bin/env python3
"""Stage 3: Extract facts, policies, relationships from documents using Gemma 4.

Uses Gemma 4 to read classified documents and extract structured knowledge:
  - Legal provisions (law name, section, what it prohibits/requires)
  - Policy requirements (who must do what, penalties)
  - Entity relationships (agencies, governments, workers, employers)
  - Trafficking indicators (ILO forced labor indicators mentioned)
  - Monetary thresholds (fee caps, wage minimums, penalty amounts)
  - Geographic applicability (which countries/corridors)

Output feeds into Stage 4 (knowledge base) and Stage 5 (prompt generation).

Usage:
    python scripts/pipeline/stage3_extract.py --input data/classified_documents/classified.jsonl
    python scripts/pipeline/stage3_extract.py --model gemma4:e4b --heuristic
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EXTRACTION_PROMPT = """You are a legal/policy fact extractor for a human trafficking prevention knowledge base.

Extract ALL factual claims, legal provisions, policy requirements, and relationships from this document.

For each fact, provide:
- fact_type: legal_provision | policy_requirement | indicator | threshold | relationship | statistic | definition
- content: the extracted fact (1-2 sentences)
- source_law: if applicable, the law/convention (e.g., "ILO C181 Art. 7")
- countries: applicable countries
- confidence: high | medium | low
- category: which exploitation category this relates to

Respond as a JSON array of facts:

[
  {{"fact_type": "legal_provision", "content": "...", "source_law": "...", "countries": [...], "confidence": "high", "category": "..."}},
  ...
]

DOCUMENT TEXT:
{text}

EXTRACTED FACTS (JSON array):"""


def extract_with_gemma(
    text: str,
    *,
    model: str = "gemma4:e4b",
    host: str = "http://localhost:11434",
) -> list[dict]:
    """Use Gemma 4 to extract facts from document text."""
    import httpx

    prompt = EXTRACTION_PROMPT.format(text=text[:4000])
    resp = httpx.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 1024, "temperature": 0.0},
        },
        timeout=180.0,
    )
    resp.raise_for_status()
    raw = resp.json().get("message", {}).get("content", "")

    # Parse JSON array from response
    json_match = re.search(r"\[[\s\S]*\]", raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return [{"error": "Failed to parse extraction", "raw": raw[:200]}]


def extract_heuristic(text: str) -> list[dict]:
    """Heuristic fact extraction (no model needed)."""
    from duecare.domains.pipeline.extractor import extract_facts

    raw_facts = extract_facts(text)
    return [
        {
            "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
            "content": f.value,
            "context": f.context[:100] if hasattr(f, "context") else "",
            "confidence": "medium",
            "extracted_by": "heuristic",
        }
        for f in raw_facts
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "data" / "classified_documents" / "classified.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "extracted_facts" / "facts.jsonl")
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--max-documents", type=int, default=0)
    parser.add_argument("--heuristic", action="store_true")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: {args.input} not found. Run stage2_classify.py first.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    documents = [json.loads(line) for line in args.input.open("r", encoding="utf-8")]
    # Filter to high/medium relevance
    documents = [d for d in documents if d.get("classification", {}).get("trafficking_relevance") in ("high", "medium", None)]
    if args.max_documents > 0:
        documents = documents[:args.max_documents]

    print(f"# Stage 3: Extract facts from {len(documents)} documents")

    all_facts = []
    for i, doc in enumerate(documents):
        text = doc.get("content", "")[:5000]
        url = doc.get("url", "?")[:60]
        print(f"[{i+1}/{len(documents)}] {url}...")

        if args.heuristic:
            facts = extract_heuristic(text)
        else:
            t0 = time.time()
            facts = extract_with_gemma(text, model=args.model, host=args.host)
            print(f"  → {len(facts)} facts ({time.time()-t0:.1f}s)")

        for fact in facts:
            fact["source_url"] = doc.get("url", "")
            fact["source_hash"] = doc.get("content_hash", "")
            all_facts.append(fact)

    # Save
    with args.output.open("w", encoding="utf-8") as f:
        for fact in all_facts:
            f.write(json.dumps(fact, ensure_ascii=False) + "\n")

    print(f"\n# Complete: {len(all_facts)} facts extracted")
    print(f"  Saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
