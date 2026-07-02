#!/usr/bin/env python3
"""Validate source-grounding manifests for cross-domain benchmark packs.

The domain registry tells the benchmark what a domain is. A grounding manifest
is the stricter companion file that tells the runner which legal/regulatory
sources are actually verified enough to use in a prompt preamble, and which
jurisdiction rows are only placeholders pending source review.

This module is intentionally dependency-free and conservative: a local law row
is never promoted just because the domain exists.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_SAFE_URL = re.compile(r"^https://", re.IGNORECASE)
_VERIFIED_STATUSES = {"verified_international_anchor", "verified_local_law"}
_PENDING_STATUSES = {"needs_source", "needs_archive", "unsafe_without_archive"}
_ALLOWED_STATUSES = _VERIFIED_STATUSES | _PENDING_STATUSES
_REQUIRED_SOURCE_KEYS = (
    "id",
    "title",
    "jurisdiction",
    "source_type",
    "authority",
    "url",
    "verification_status",
    "verified_date",
    "coverage_tags",
    "use_limitations",
)


class GroundingError(ValueError):
    """Raised when a grounding manifest is structurally unsafe."""


def _date_or_none(value: Any, *, row_id: str) -> str | None:
    if value in ("", None):
        return None
    if not isinstance(value, str):
        raise GroundingError(f"{row_id}: verified_date must be YYYY-MM-DD or null")
    try:
        _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise GroundingError(f"{row_id}: verified_date must be YYYY-MM-DD") from exc
    return value


def _clean_list(values: Any, *, row_id: str, key: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise GroundingError(f"{row_id}: {key} must be a non-empty list")
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise GroundingError(f"{row_id}: {key} contains a blank/non-string value")
        out.append(" ".join(value.split())[:120])
    return out


def _clean_required_text(value: Any, *, row_id: str, key: str, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GroundingError(f"{row_id}: {key} must be a non-empty string")
    return " ".join(value.split())[:max_len]


def validate_grounding_manifest(doc: dict[str, Any], *, path: pathlib.Path | None = None) -> dict[str, Any]:
    """Validate and normalize a source-grounding manifest.

    Verified rows require an HTTPS URL and ISO date. Pending rows must not carry
    a verification date. ``verified_local_law`` is allowed by the schema but is
    intentionally absent from the seed worker-protection manifest until curated
    country source objects exist.
    """
    if not isinstance(doc, dict):
        raise GroundingError("manifest root must be an object")
    meta = doc.get("_meta")
    if not isinstance(meta, dict):
        raise GroundingError("manifest missing _meta object")
    if not isinstance(meta.get("domain"), str) or not meta["domain"].strip():
        raise GroundingError("manifest _meta.domain must be a non-empty string")
    _date_or_none(meta.get("last_updated"), row_id="_meta")
    rows = doc.get("sources")
    if not isinstance(rows, list) or not rows:
        raise GroundingError("manifest sources must be a non-empty list")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise GroundingError(f"source row {i} must be an object")
        missing = [key for key in _REQUIRED_SOURCE_KEYS if key not in row]
        row_id = str(row.get("id") or f"row {i}")
        if missing:
            raise GroundingError(f"{row_id}: missing required keys {missing}")
        if row_id in seen:
            raise GroundingError(f"{row_id}: duplicate source id")
        seen.add(row_id)

        status = row.get("verification_status")
        if status not in _ALLOWED_STATUSES:
            raise GroundingError(f"{row_id}: unsupported verification_status {status!r}")
        url = str(row.get("url") or "").strip()
        verified_date = _date_or_none(row.get("verified_date"), row_id=row_id)
        if status in _VERIFIED_STATUSES:
            if not _SAFE_URL.match(url):
                raise GroundingError(f"{row_id}: verified rows require an HTTPS url")
            if verified_date is None:
                raise GroundingError(f"{row_id}: verified rows require verified_date")
        if status in _PENDING_STATUSES and verified_date is not None:
            raise GroundingError(f"{row_id}: pending rows must not carry verified_date")
        if status == "verified_local_law" and row.get("source_type") == "country_law_placeholder":
            raise GroundingError(f"{row_id}: placeholder rows cannot be verified_local_law")

        normalized.append({
            "id": row_id,
            "title": _clean_required_text(row["title"], row_id=row_id, key="title", max_len=240),
            "jurisdiction": _clean_required_text(
                row["jurisdiction"], row_id=row_id, key="jurisdiction", max_len=80
            ),
            "source_type": _clean_required_text(row["source_type"], row_id=row_id, key="source_type", max_len=80),
            "authority": _clean_required_text(row["authority"], row_id=row_id, key="authority", max_len=160),
            "url": url,
            "verification_status": status,
            "verified_date": verified_date,
            "coverage_tags": _clean_list(row["coverage_tags"], row_id=row_id, key="coverage_tags"),
            "use_limitations": _clean_required_text(
                row["use_limitations"], row_id=row_id, key="use_limitations", max_len=500
            ),
        })
    return {"_meta": dict(meta), "sources": normalized, "_path": str(path) if path else None}


def load_grounding_manifest(path: pathlib.Path) -> dict[str, Any]:
    """Read, validate, and normalize one grounding manifest."""
    return validate_grounding_manifest(json.loads(path.read_text(encoding="utf-8")), path=path)


def summarize_grounding(doc: dict[str, Any], *, limit: int = 8) -> dict[str, Any]:
    """Return the compact, promptset-safe summary used by runners and judges."""
    rows = doc["sources"]
    verified = [r for r in rows if r["verification_status"] in _VERIFIED_STATUSES]
    pending = [r for r in rows if r["verification_status"] in _PENDING_STATUSES]
    pending_jurisdictions = sorted({r["jurisdiction"] for r in pending if r["jurisdiction"]})
    return {
        "schema_version": doc["_meta"].get("schema_version"),
        "status": doc["_meta"].get("status"),
        "last_updated": doc["_meta"].get("last_updated"),
        "verified_source_count": len(verified),
        "pending_source_count": len(pending),
        "pending_jurisdictions": pending_jurisdictions,
        "verified_sources": [
            {
                "id": r["id"],
                "title": r["title"],
                "jurisdiction": r["jurisdiction"],
                "authority": r["authority"],
                "url": r["url"],
                "coverage_tags": r["coverage_tags"],
                "use_limitations": r["use_limitations"],
            }
            for r in verified[:limit]
        ],
    }


def load_domain_grounding(domain_id: str) -> dict[str, Any] | None:
    """Resolve and summarize a domain's grounding manifest, if the registry names one."""
    from domain_registry import get_domain

    spec = get_domain(domain_id)
    rel = spec.get("grounding_manifest")
    if not rel:
        return None
    path = pathlib.Path(rel)
    if not path.is_absolute():
        path = _ROOT / path
    doc = load_grounding_manifest(path)
    summary = summarize_grounding(doc)
    summary["manifest_path"] = str(path.relative_to(_ROOT))
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate a benchmark domain grounding manifest.")
    ap.add_argument("path")
    args = ap.parse_args(argv)
    doc = load_grounding_manifest(pathlib.Path(args.path))
    print(json.dumps(summarize_grounding(doc), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
