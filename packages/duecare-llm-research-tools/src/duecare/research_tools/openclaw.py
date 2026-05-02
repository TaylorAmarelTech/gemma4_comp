"""OpenClaw integration -- web research with strict PII filtering.

OpenClaw is treated as an HTTP API. The wrapper takes the structured
arguments Gemma's tool_call emits, runs them through PIIFilter, and
issues the upstream call. Modes:

  online  -- real HTTP call (requires OPENCLAW_API_KEY + httpx).
  mock    -- return a deterministic stub (for tests / off-Kaggle dev).

Configurable via env vars:
  OPENCLAW_API_KEY    -- API key (no hardcoded value)
  OPENCLAW_BASE_URL   -- base URL (default https://api.openclaw.io/v1)
  OPENCLAW_MODE       -- "online" (default) | "mock"
  OPENCLAW_TIMEOUT    -- seconds (default 30)

Public methods (each returns a ResearchResult, each runs PII filter
before any network call):
  search(query, max_results=10)
  court_judgments(org_name, jurisdiction, since_year=None)
  news_check(query, kind="negative", max_results=10)
  law_lookup(statute, jurisdiction)
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

from duecare.research_tools.pii_filter import PIIFilter, PIIRejectionError
from duecare.research_tools.protocol import ResearchResult


class OpenClawTool:
    """The default research tool. Implements ResearchTool protocol via
    duck-typing (name, description, query)."""

    name: str = "openclaw"
    description: str = (
        "Web research via OpenClaw. PII-filtered. Methods: "
        "search, court_judgments, news_check, law_lookup.")

    def __init__(self,
                  api_key: Optional[str] = None,
                  base_url: str = "https://api.openclaw.io/v1",
                  mode: str = "online",
                  timeout: float = 30.0,
                  pii_filter: Optional[PIIFilter] = None,
                  allow_org_names: Optional[list[str]] = None) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.mode = mode
        self.timeout = timeout
        self.pii = pii_filter or PIIFilter(
            allow_org_names=allow_org_names or [])

    @classmethod
    def from_env(cls,
                  allow_org_names: Optional[list[str]] = None) -> "OpenClawTool":
        return cls(
            api_key=os.environ.get("OPENCLAW_API_KEY"),
            base_url=os.environ.get(
                "OPENCLAW_BASE_URL", "https://api.openclaw.io/v1"),
            mode=os.environ.get("OPENCLAW_MODE", "online"),
            timeout=float(os.environ.get("OPENCLAW_TIMEOUT", "30")),
            allow_org_names=allow_org_names,
        )

    # -- generic dispatch (matches ResearchTool.query) -----------------------
    def query(self, **kwargs: Any) -> ResearchResult:
        """Generic query entrypoint. Dispatches to a specific method
        via the `endpoint` kwarg, defaulting to `search`."""
        endpoint = kwargs.pop("endpoint", "search")
        method = getattr(self, endpoint, None)
        if method is None or endpoint.startswith("_"):
            return ResearchResult(
                tool_name=self.name, query=kwargs, success=False,
                error=f"unknown endpoint: {endpoint}")
        return method(**kwargs)

    # -- public methods ------------------------------------------------------
    def search(self, query: str, max_results: int = 10) -> ResearchResult:
        args = {"query": query, "max_results": max_results}
        try:
            self.pii.validate(args)
        except PIIRejectionError as e:
            return self._reject(args, str(e))
        return self._call("search", args)

    def court_judgments(self, org_name: str, jurisdiction: str,
                          since_year: Optional[int] = None) -> ResearchResult:
        args = {
            "org_name": org_name,
            "jurisdiction": jurisdiction,
            "since_year": since_year,
        }
        try:
            self.pii.validate({k: v for k, v in args.items() if v is not None})
        except PIIRejectionError as e:
            return self._reject(args, str(e))
        return self._call("court_judgments", args)

    def news_check(self, query: str, kind: str = "negative",
                    max_results: int = 10) -> ResearchResult:
        args = {"query": query, "kind": kind, "max_results": max_results}
        try:
            self.pii.validate(args)
        except PIIRejectionError as e:
            return self._reject(args, str(e))
        return self._call("news_check", args)

    def law_lookup(self, statute: str, jurisdiction: str) -> ResearchResult:
        args = {"statute": statute, "jurisdiction": jurisdiction}
        try:
            self.pii.validate(args)
        except PIIRejectionError as e:
            return self._reject(args, str(e))
        return self._call("law_lookup", args)

    # -- internals -----------------------------------------------------------
    def _reject(self, args: dict, reason: str) -> ResearchResult:
        return ResearchResult(
            tool_name=self.name, query=args, success=False,
            error=f"pii_rejected: {reason}",
            summary="(blocked locally; query contained PII)")

    def _call(self, endpoint: str, args: dict) -> ResearchResult:
        if self.mode == "mock":
            return self._mock(endpoint, args)
        if not self.api_key:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error="OPENCLAW_API_KEY not set; "
                      "use mode='mock' for offline testing.")
        try:
            import httpx   # type: ignore
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"httpx not installed: {e}. Install with: "
                      f"pip install duecare-llm-research-tools[http]")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/{endpoint}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=args,
                )
            if resp.status_code != 200:
                return ResearchResult(
                    tool_name=self.name, query=args, success=False,
                    error=f"http {resp.status_code}: {resp.text[:300]}")
            payload = resp.json()
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"http call FAILED: {type(e).__name__}: {e}")
        items = payload.get("items") or payload.get("results") or []
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=items if isinstance(items, list) else [],
            summary=payload.get("summary", ""),
            raw=payload if isinstance(payload, dict) else {"raw": payload},
        )

    def _mock(self, endpoint: str, args: dict) -> ResearchResult:
        """Deterministic stub for off-Kaggle development. Returns a
        plausible-shaped response so tests + UI flows work without a
        real OpenClaw account."""
        items = []
        if endpoint == "court_judgments":
            items = [{
                "title": f"In re: {args.get('org_name', 'org')} licensing review",
                "jurisdiction": args.get("jurisdiction", ""),
                "year": args.get("since_year") or 2024,
                "url": "https://example.invalid/mock-judgment",
                "snippet": "[mock] Agency licence suspended pending "
                           "investigation of recruitment-fee practices.",
            }]
        elif endpoint == "news_check":
            items = [{
                "title": f"[mock] {args.get('query', '')}: review",
                "url": "https://example.invalid/mock-news",
                "snippet": "[mock] No corroborated reports.",
                "kind": args.get("kind", "neutral"),
            }]
        elif endpoint == "law_lookup":
            items = [{
                "statute": args.get("statute"),
                "jurisdiction": args.get("jurisdiction"),
                "url": "https://example.invalid/mock-law",
                "snippet": "[mock] Statute text would appear here.",
            }]
        else:
            items = [{
                "title": f"[mock search] {args.get('query', '')}",
                "url": "https://example.invalid/mock-search",
                "snippet": "[mock] Web search result would appear here.",
            }]
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=items, summary=f"[mock] {endpoint} -> {len(items)} item(s)",
            raw={"mock": True, "endpoint": endpoint},
        )
