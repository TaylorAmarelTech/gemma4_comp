#!/usr/bin/env python3
"""Safe optional search-provider wrappers for public research.

Default behavior is no-network. Networked providers must be explicitly enabled
and are written so tests can inject fake HTTP responses. Private case text,
local casefile paths, emails, phone-like strings, and passport-like identifiers
are rejected before any provider sees the query.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = (
    REPO_ROOT
    / "configs"
    / "duecare"
    / "benchmarks"
    / "research_spider"
    / "search_provider_registry.json"
)
DEFAULT_USER_AGENT = "DueCarePublicSearchProvider/0.1 (public benchmark research only)"
_MAJOR_CASES_WINDOWS = re.escape("C:" + "\\" + "projects" + "\\" + "major_cases")
_MAJOR_CASES_POSIX = re.escape("/projects/" + "major_cases")

BLOCKED_QUERY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_case_root", re.compile(rf"(?:{_MAJOR_CASES_WINDOWS}|{_MAJOR_CASES_POSIX})", re.I)),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{7,}\d)(?!\w)")),
    ("passport", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b", re.I)),
    ("api_key_fragment", re.compile(r"\b(?:sk-|AQ\.|ghp_|xoxb-|AIza)[A-Za-z0-9_.-]{8,}\b")),
)


class QueryPolicyError(ValueError):
    """Raised when a query violates the public-source-only boundary."""


def blocked_query_reasons(query: str) -> list[str]:
    return [name for name, pattern in BLOCKED_QUERY_PATTERNS if pattern.search(query)]


def enforce_public_query(query: str) -> None:
    reasons = blocked_query_reasons(query)
    if reasons:
        raise QueryPolicyError(f"query contains blocked private or secret-like terms: {', '.join(reasons)}")


def manual_search_url(query: str, *, engine: str = "google") -> str:
    enforce_public_query(query)
    encoded = urllib.parse.urlencode({"q": query})
    if engine == "github":
        return "https://github.com/search?" + urllib.parse.urlencode({"q": query, "type": "repositories"})
    if engine == "brave":
        return "https://search.brave.com/search?" + encoded
    return "https://www.google.com/search?" + encoded


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def provider_config(provider_id: str, registry: dict | None = None) -> dict:
    registry = registry or load_registry()
    for provider in registry.get("providers", []):
        if provider["tool_id"] == provider_id:
            return provider
    raise KeyError(f"unknown search provider: {provider_id}")


def _default_request_json(url: str, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec: public URLs only after policy checks
        return json.loads(response.read().decode("utf-8"))


def _fallback(provider_id: str, query: str, status: str) -> dict:
    engine = "github" if provider_id == "github_search_api" else "brave" if provider_id == "brave_search_api" else "google"
    return {
        "provider": provider_id,
        "status": status,
        "fallback": "manual_search_url",
        "manual_search_url": manual_search_url(query, engine=engine),
    }


def _result(provider_id: str, *, title: str, url: str, snippet: str, rank: int) -> dict:
    return {
        "provider": provider_id,
        "rank": rank,
        "title": title or "",
        "url": url or "",
        "snippet": snippet or "",
        "synthetic_or_public_only": True,
    }


def _search_brave(
    query: str,
    *,
    env: dict[str, str],
    request_json: Callable[[str, dict[str, str]], dict],
    max_results: int,
) -> tuple[list[dict], dict]:
    key = env.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        return [], _fallback("brave_search_api", query, "missing_api_key")
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": max_results})
    data = request_json(
        url,
        {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-Subscription-Token": key,
        },
    )
    results = []
    for rank, item in enumerate(data.get("web", {}).get("results", [])[:max_results], start=1):
        results.append(
            _result(
                "brave_search_api",
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                rank=rank,
            )
        )
    return results, {"provider": "brave_search_api", "status": "ok", "count": len(results)}


def _search_github(
    query: str,
    *,
    env: dict[str, str],
    request_json: Callable[[str, dict[str, str]], dict],
    max_results: int,
) -> tuple[list[dict], dict]:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": max_results}
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    token = env.get("GITHUB_TOKEN", "").strip() or env.get("GH_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = request_json(url, headers)
    results = []
    for rank, item in enumerate(data.get("items", [])[:max_results], start=1):
        results.append(
            _result(
                "github_search_api",
                title=item.get("full_name", ""),
                url=item.get("html_url", ""),
                snippet=item.get("description", ""),
                rank=rank,
            )
        )
    return results, {"provider": "github_search_api", "status": "ok", "count": len(results)}


def run_search_provider(
    provider_id: str,
    query: str,
    *,
    allow_network: bool = False,
    env: dict[str, str] | None = None,
    request_json: Callable[[str, dict[str, str]], dict] | None = None,
    max_results: int = 10,
) -> tuple[list[dict], dict]:
    enforce_public_query(query)
    env = env or dict(os.environ)
    request_json = request_json or _default_request_json
    _ = provider_config(provider_id)

    if provider_id == "manual_dork_queue":
        return [], _fallback(provider_id, query, "manual_only")
    if not allow_network:
        return [], _fallback(provider_id, query, "network_disabled")
    if provider_id == "brave_search_api":
        return _search_brave(query, env=env, request_json=request_json, max_results=max_results)
    if provider_id == "github_search_api":
        return _search_github(query, env=env, request_json=request_json, max_results=max_results)
    return [], _fallback(provider_id, query, "adapter_not_implemented")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--provider", default="manual_dork_queue")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--max-results", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    hits, status = run_search_provider(
        args.provider,
        args.query,
        allow_network=args.allow_network,
        max_results=args.max_results,
    )
    print(json.dumps({"status": status, "hits": hits}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
