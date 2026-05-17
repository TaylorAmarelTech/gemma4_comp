"""Post-search verification harness handler.

The search harness returns candidate public results. This harness keeps those
results out of prompt context until they have a local verification envelope:
source quality, relevance, contradiction indicators, and deanonymization risk.
"""
from __future__ import annotations

import re
import hashlib
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


_DIRECT_IDENTIFIER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
    ("passport", re.compile(r"\b(passport|hkid|national\s*id|id\s*number)\b\s*(number|no\.?|#|:)?\s*[A-Z0-9-]*\d[A-Z0-9-]{4,}\b", re.I)),
    ("address", re.compile(r"\b(unit|flat|room)\s+[A-Z0-9-]{1,8}\b|\b\d{1,5}\s+[A-Za-z0-9 .'-]{2,40}\s+(street|road|avenue|barangay|building)\b", re.I)),
)

_HIGH_AUTHORITY_DOMAINS = (
    "ilo.org",
    "iom.int",
    "ohchr.org",
    "un.org",
    "gov",
    "gov.hk",
    "dmw.gov.ph",
    "migrantworkersoffice.com",
)

_LOW_QUALITY_MARKERS = (
    "sponsored",
    "advertisement",
    "forum",
    "social media",
    "unverified",
    "rumor",
)


def _tokens(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", value.lower()) if t not in {"the", "and", "for", "with"}}


def _source_quality(url: str, title: str, snippet: str) -> tuple[str, list[str]]:
    host = urlparse(url or "").netloc.lower()
    text = f"{title} {snippet}".lower()
    reasons: list[str] = []
    if any(marker in host for marker in _HIGH_AUTHORITY_DOMAINS):
        reasons.append("recognized public/official source domain")
        return "high", reasons
    if host.endswith(".org"):
        reasons.append("organization domain")
    if any(marker in text for marker in _LOW_QUALITY_MARKERS):
        reasons.append("contains low-quality marker")
        return "low", reasons
    if reasons:
        return "medium", reasons
    return "unknown", ["source not in authority allow-list"]


def _relevance_score(query: str, title: str, snippet: str) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    body = _tokens(f"{title} {snippet}")
    return round(len(q & body) / max(1, len(q)), 3)


def _identifier_risk(value: str) -> tuple[str, list[str]]:
    hits = [label for label, pat in _DIRECT_IDENTIFIER_PATTERNS if pat.search(value or "")]
    if hits:
        return "high", hits
    return "low", []


def _contradiction_flags(result_text: str, corpus_text: str) -> list[str]:
    text = result_text.lower()
    flags: list[str] = []
    no_fee = bool(re.search(r"\b(no|zero|prohibit(?:ed)?|illegal)\b.{0,80}\b(fee|placement fee|recruitment fee)\b", text))
    fee_allowed = bool(re.search(r"\b(fee|placement fee|recruitment fee)\b.{0,80}\b(allowed|permitted|chargeable)\b", text))
    if no_fee and "fee_allowed" in corpus_text:
        flags.append("conflicts with another result that appears to permit fees")
    if fee_allowed and "no_fee" in corpus_text:
        flags.append("conflicts with another result that appears to prohibit fees")
    if "outdated" in text or "archived" in text:
        flags.append("result may be outdated or archived")
    return flags


def _fee_stance(text: str) -> str:
    lower = text.lower()
    if re.search(r"\b(no|zero|prohibit(?:ed)?|illegal)\b.{0,80}\b(fee|placement fee|recruitment fee)\b", lower):
        return "no_fee"
    if re.search(r"\b(fee|placement fee|recruitment fee)\b.{0,80}\b(allowed|permitted|chargeable)\b", lower):
        return "fee_allowed"
    return ""


def verify_search_results(query: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    stances = " ".join(_fee_stance(f"{r.get('title', '')} {r.get('snippet', '')}") for r in results)
    verified: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for idx, item in enumerate(results):
        title = str(item.get("title") or "")
        url = str(item.get("url") or item.get("href") or "")
        snippet = str(item.get("snippet") or item.get("text") or "")
        combined = f"{query} {title} {url} {snippet}"
        quality, quality_reasons = _source_quality(url, title, snippet)
        relevance = _relevance_score(query, title, snippet)
        risk, risk_hits = _identifier_risk(combined)
        contradictions = _contradiction_flags(f"{title} {snippet}", stances)
        status = "accepted"
        if risk == "high":
            status = "blocked"
        elif relevance < 0.12:
            status = "review"
        elif quality == "low" or contradictions:
            status = "review"
        row = {
            "index": idx,
            "title": title,
            "url": url,
            "snippet": snippet,
            "status": status,
            "source_quality": quality,
            "source_quality_reasons": quality_reasons,
            "relevance_score": relevance,
            "contradiction_flag": bool(contradictions),
            "contradiction_reasons": contradictions,
            "deanonymization_risk": risk,
            "deanonymization_hits": risk_hits,
        }
        (blocked if status == "blocked" else verified).append(row)
    return {
        "query_sha256": hashlib.sha256(query.encode("utf-8", errors="ignore")).hexdigest() if query else "",
        "n_results": len(results),
        "n_accepted": sum(1 for row in verified if row["status"] == "accepted"),
        "n_review": sum(1 for row in verified if row["status"] == "review"),
        "n_blocked": len(blocked),
        "verified_results": verified,
        "blocked_results": blocked,
        "policy": "Results are candidates until status=accepted or a reviewer promotes them to KnowledgeObjects.",
    }


def register_routes(app: Any) -> None:

    @app.post("/api/search/verify-results")
    async def api_search_verify_results(request: Request) -> Any:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        query = str(body.get("query") or "")
        results = body.get("results") or []
        if not isinstance(results, list):
            raise HTTPException(400, "results must be a list")
        out = verify_search_results(query, [r for r in results if isinstance(r, dict)])
        try:
            from .._training_log import log_interaction
            log_interaction(
                "post_search_verification",
                input_payload={"query_sha256": out.get("query_sha256", ""), "n_results": len(results)},
                output_payload={
                    "n_accepted": out["n_accepted"],
                    "n_review": out["n_review"],
                    "n_blocked": out["n_blocked"],
                },
                applied_layers={},
                trace={"policy": out["policy"]},
                extra={},
            )
        except Exception:
            pass
        return JSONResponse(out)

    @app.get("/api/search/verification-info")
    def api_search_verification_info() -> Any:
        return {
            "harness": "post_search_verification",
            "purpose": "Verify search result candidates before they are injected into chat, extraction, or knowledge packs.",
            "fields": [
                "source_quality",
                "relevance_score",
                "contradiction_flag",
                "deanonymization_risk",
                "status",
            ],
            "accepted_status": "accepted",
            "review_status": "review",
            "blocked_status": "blocked",
        }


__all__ = ["register_routes", "verify_search_results"]
