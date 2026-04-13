#!/usr/bin/env python3
"""Stage 1: Acquire authoritative materials on human exploitation.

Uses web search, seed URLs, and spidering to download documents from
authoritative sources: ILO, UN OHCHR, US State Dept TIP reports,
POEA, court databases, NGO publications.

This is a data pipeline agent — it gathers raw material that later
stages will classify, extract from, and generate prompts against.

Usage:
    python scripts/pipeline/stage1_acquire.py --max-documents 50
    python scripts/pipeline/stage1_acquire.py --source ilo --max-documents 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "data" / "acquired_documents"

# ── Authoritative seed URLs ──

SEED_SOURCES = {
    "ilo_conventions": {
        "description": "ILO Conventions on forced labor and migrant workers",
        "urls": [
            "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C029",
            "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C181",
            "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C189",
            "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C097",
            "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C143",
        ],
        "category": "international_law",
        "authority": "high",
    },
    "us_tip_reports": {
        "description": "US State Department Trafficking in Persons reports",
        "urls": [
            "https://www.state.gov/trafficking-in-persons-report/",
        ],
        "category": "government_report",
        "authority": "high",
    },
    "un_ohchr": {
        "description": "UN OHCHR trafficking guidance",
        "urls": [
            "https://www.ohchr.org/en/trafficking-in-persons",
        ],
        "category": "international_guidance",
        "authority": "high",
    },
    "poea_philippines": {
        "description": "Philippine POEA regulations and advisories",
        "urls": [
            "https://www.dmw.gov.ph/",
        ],
        "category": "national_regulation",
        "authority": "high",
    },
    "polaris_project": {
        "description": "Polaris Project trafficking indicators and data",
        "urls": [
            "https://polarisproject.org/human-trafficking/",
            "https://polarisproject.org/resources/",
        ],
        "category": "ngo_research",
        "authority": "medium",
    },
    "ijm": {
        "description": "International Justice Mission case data",
        "urls": [
            "https://www.ijm.org/what-we-do/",
        ],
        "category": "ngo_research",
        "authority": "medium",
    },
    "fatf_guidance": {
        "description": "FATF guidance on money laundering and trafficking",
        "urls": [
            "https://www.fatf-gafi.org/en/topics/money-laundering.html",
        ],
        "category": "financial_regulation",
        "authority": "high",
    },
}

# ── Search queries for Brave/Google ──

SEARCH_QUERIES = [
    "ILO forced labor indicators migrant workers",
    "recruitment fee regulations Philippines domestic workers",
    "kafala system reform Gulf states workers rights",
    "human trafficking indicators employment agencies",
    "debt bondage migrant workers legal framework",
    "passport confiscation employer migrant worker law",
    "contract substitution overseas workers legal protection",
    "anti-trafficking laws Southeast Asia migrant workers",
    "predatory lending migrant workers Hong Kong money lenders",
    "ILO C181 private employment agencies implementation",
    "POEA regulations overseas Filipino workers fees",
    "wage theft migrant domestic workers legal remedies",
    "forced labor fishing industry Thailand Myanmar",
    "modern slavery act supply chain due diligence",
    "trafficking in persons report tier rankings methodology",
]


def fetch_url(url: str, *, timeout: float = 30.0) -> dict[str, Any] | None:
    """Fetch a URL and return structured document data."""
    try:
        import httpx

        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()

        content = resp.text
        # Strip HTML tags for basic text extraction
        import re
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "content": text[:50000],  # Cap at 50K chars
            "content_hash": hashlib.sha256(text[:10000].encode()).hexdigest()[:16],
            "fetched_at": datetime.now().isoformat(),
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "size_bytes": len(content),
        }
    except Exception as e:
        print(f"  FAILED: {url}: {e}")
        return None


def web_search(query: str, *, max_results: int = 5) -> list[str]:
    """Search for URLs using a simple search approach.

    In production, this would use Brave Search API or Google Custom Search.
    For now, returns seed URLs that match the query topic.
    """
    # Match query keywords to seed sources
    results = []
    query_lower = query.lower()
    for source_id, source in SEED_SOURCES.items():
        if any(word in source["description"].lower() for word in query_lower.split()):
            results.extend(source["urls"])
    return results[:max_results]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-documents", type=int, default=50)
    parser.add_argument("--source", choices=list(SEED_SOURCES.keys()) + ["all", "search"], default="all")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--heuristic", action="store_true", help="(ignored, pipeline compat)")
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"# Stage 1: Acquire authoritative documents")
    print(f"  Source: {args.source}")
    print(f"  Max documents: {args.max_documents}")
    print(f"  Output: {args.output_dir}")

    documents = []
    seen_hashes = set()

    # Collect URLs from seed sources
    urls_to_fetch = []
    if args.source == "all":
        for source_id, source in SEED_SOURCES.items():
            for url in source["urls"]:
                urls_to_fetch.append((url, source["category"], source["authority"]))
    elif args.source == "search":
        for query in SEARCH_QUERIES[:args.max_documents]:
            found = web_search(query)
            for url in found:
                urls_to_fetch.append((url, "search_result", "medium"))
    else:
        source = SEED_SOURCES[args.source]
        for url in source["urls"]:
            urls_to_fetch.append((url, source["category"], source["authority"]))

    # Fetch documents
    for i, (url, category, authority) in enumerate(urls_to_fetch[:args.max_documents]):
        print(f"\n[{i+1}/{min(len(urls_to_fetch), args.max_documents)}] {url[:80]}...")
        doc = fetch_url(url)
        if doc and doc["content_hash"] not in seen_hashes:
            doc["category"] = category
            doc["authority"] = authority
            documents.append(doc)
            seen_hashes.add(doc["content_hash"])
            print(f"  OK: {doc['size_bytes']:,} bytes, hash={doc['content_hash']}")
        time.sleep(1)  # Rate limiting

    # Save
    manifest = {
        "stage": "acquire",
        "created_at": datetime.now().isoformat(),
        "n_documents": len(documents),
        "sources": list(set(d["category"] for d in documents)),
    }

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    docs_path = args.output_dir / "documents.jsonl"
    with docs_path.open("w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"\n# Complete")
    print(f"  Documents fetched: {len(documents)}")
    print(f"  Saved to: {docs_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
