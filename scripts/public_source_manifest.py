#!/usr/bin/env python3
"""Plan safe public-source fetch/extraction work from spider candidates.

This does not fetch the internet. It turns source candidate metadata into a
deterministic queue that a later crawler can consume only after manual source
review and robots/rate-limit checks.
"""

from __future__ import annotations

import argparse
import collections
import json
import urllib.parse
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
SCHEMA_VERSION = "public_source_fetch_manifest.v1"
DOMAIN_SCHEMA_VERSION = "public_source_domain_frontier.v1"
DEFAULT_USER_AGENT = "DueCarePublicFetchExtract/0.1 (public benchmark research only)"


class SourceManifestError(ValueError):
    """Raised when source metadata is not safe to put in the public queue."""


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceManifestError("only http/https public URLs can enter the fetch manifest")
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    keep_query = [
        (key, value)
        for key, value in query_pairs
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    query = urllib.parse.urlencode(keep_query, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", query, ""))


def content_kind(url: str) -> str:
    path = urllib.parse.urlsplit(url).path.lower()
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith((".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx")):
        return "office_document"
    if path.endswith((".json", ".jsonl")):
        return "structured_json"
    if path.endswith((".html", ".htm")) or "." not in Path(path).name:
        return "html"
    return "plain_or_unknown"


def extractor_plan(kind: str) -> dict:
    plans = {
        "pdf": {
            "primary": "pdfplumber_optional",
            "fallbacks": ["pypdf_optional", "metadata_only"],
            "captures_tables": True,
        },
        "office_document": {
            "primary": "markitdown_optional",
            "fallbacks": ["metadata_only"],
            "captures_tables": True,
        },
        "structured_json": {
            "primary": "stdlib_json",
            "fallbacks": ["plain_text_redacted"],
            "captures_tables": False,
        },
        "html": {
            "primary": "trafilatura_optional",
            "fallbacks": ["stdlib_html"],
            "captures_tables": False,
        },
        "plain_or_unknown": {
            "primary": "plain_text_redacted",
            "fallbacks": ["metadata_only"],
            "captures_tables": False,
        },
    }
    return plans[kind]


def manifest_rows(candidates: list[dict]) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for cand in sorted(candidates, key=lambda row: (-int(row.get("score", 0)), row.get("url", ""))):
        normalized = normalize_url(cand.get("url", ""))
        if normalized in seen:
            continue
        seen.add(normalized)
        parsed = urllib.parse.urlsplit(normalized)
        kind = content_kind(normalized)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_candidate_id": cand.get("id", ""),
                "url": normalized,
                "domain": parsed.netloc,
                "source_family": cand.get("source_family", ""),
                "source_tier": cand.get("source_tier", ""),
                "jurisdictions": cand.get("jurisdictions", []),
                "score": cand.get("score", 0),
                "signals": cand.get("signals", []),
                "content_kind": kind,
                "extractor_plan": extractor_plan(kind),
                "fetch_policy": {
                    "network_fetch_default": False,
                    "requires_robots_check": True,
                    "requires_manual_source_review": True,
                    "user_agent": DEFAULT_USER_AGENT,
                    "polite_delay_seconds": 3,
                    "max_bytes": 8_000_000,
                    "sitemap_first": True,
                },
                "status": "queued_for_manual_review_and_robots_check",
                "privacy": {
                    "public_url_metadata_only": True,
                    "raw_private_cases_ingested": False,
                    "private_case_paths_allowed": False,
                    "pii_redaction_required": True,
                },
                "planned_artifacts": [
                    "public_fetch_extract_result.v1",
                    "source_fetch_manifest_entry.v1",
                    "redacted_text_excerpt_only_if_published",
                ],
            }
        )
    return rows


def domain_frontier_rows(manifest: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for row in manifest:
        grouped[row["domain"]].append(row)

    rows: list[dict] = []
    for domain, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        scheme = urllib.parse.urlsplit(items[0]["url"]).scheme or "https"
        signal_counts: collections.Counter[str] = collections.Counter()
        families = set()
        jurisdictions = set()
        for item in items:
            signal_counts.update(item.get("signals", []))
            families.add(item.get("source_family", ""))
            jurisdictions.update(item.get("jurisdictions", []))
        rows.append(
            {
                "schema_version": DOMAIN_SCHEMA_VERSION,
                "domain": domain,
                "source_count": len(items),
                "source_families": sorted(f for f in families if f),
                "jurisdictions": sorted(j for j in jurisdictions if j),
                "top_signals": [signal for signal, _count in signal_counts.most_common(8)],
                "robots_url": f"{scheme}://{domain}/robots.txt",
                "sitemap_candidates": [
                    f"{scheme}://{domain}/sitemap.xml",
                    f"{scheme}://{domain}/sitemap_index.xml",
                ],
                "queue_policy": {
                    "network_fetch_default": False,
                    "sitemap_first": True,
                    "manual_review_before_fetch": True,
                    "respect_robots_txt": True,
                    "polite_delay_seconds": 3,
                },
            }
        )
    return rows


def run_pipeline(out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    candidates = load_jsonl(out_dir / "source_candidates.jsonl")
    manifest = manifest_rows(candidates)
    domains = domain_frontier_rows(manifest)
    write_jsonl(out_dir / "source_fetch_manifest.jsonl", manifest)
    write_jsonl(out_dir / "source_domain_frontier.jsonl", domains)
    summary = {
        "schema_version": "public_source_manifest_summary.v1",
        "source_fetch_manifest": len(manifest),
        "source_domain_frontier": len(domains),
        "content_kinds": dict(collections.Counter(row["content_kind"] for row in manifest)),
        "privacy": {
            "network_fetch_default": False,
            "raw_private_cases_ingested": False,
            "manual_review_before_fetch": True,
        },
    }
    (out_dir / "source_manifest_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_pipeline(Path(args.out_dir))
    print(
        "public-source-manifest: "
        f"sources={summary['source_fetch_manifest']} "
        f"domains={summary['source_domain_frontier']} "
        f"kinds={summary['content_kinds']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
