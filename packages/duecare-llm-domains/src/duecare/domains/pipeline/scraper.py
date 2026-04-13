"""
Generic web scraper using httpx.

Fetches HTML and PDF documents from arbitrary URLs with rate-limiting,
retry logic, and basic text extraction.  No browser engine required.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RawDocument(BaseModel):
    """A document fetched from the web."""

    url: str
    content_hash: str = ""
    content_type: str = "text/html"
    text: str = ""
    raw_bytes: bytes = b""
    title: str = ""
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    status_code: int = 0
    language: str = "en"

    class Config:
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Rate-limiting helper
# ---------------------------------------------------------------------------

_last_request_time: float = 0.0
_MIN_INTERVAL: float = 1.0  # seconds between requests


def _rate_limit() -> None:
    """Block until the minimum interval between requests has elapsed."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_title(html: str) -> str:
    """Pull the <title> text out of an HTML page."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _strip_tags(html: str) -> str:
    """Crude tag-strip for plain-text extraction from HTML."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_pdf_text(raw: bytes) -> str:
    """Best-effort PDF text extraction.  Falls back to empty string."""
    try:
        import pdfplumber  # optional dependency

        import io
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages).strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_url(
    url: str,
    *,
    timeout: float = 30.0,
    headers: Optional[dict[str, str]] = None,
) -> RawDocument:
    """
    Fetch a URL and return a RawDocument.

    Handles HTML (tag-stripped text) and PDF (pdfplumber extraction).
    Raises ``httpx.HTTPStatusError`` on 4xx/5xx responses.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.
        headers: Extra HTTP headers to send.

    Returns:
        A populated ``RawDocument``.
    """
    _rate_limit()

    default_headers = {
        "User-Agent": "DueCare-Pipeline/0.1 (research; +https://github.com/taylorsamarel/duecare)",
        "Accept": "text/html,application/pdf,*/*",
    }
    if headers:
        default_headers.update(headers)

    response = httpx.get(url, headers=default_headers, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    raw_bytes = response.content
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    if "pdf" in content_type.lower():
        text = _extract_pdf_text(raw_bytes)
        title = url.rsplit("/", 1)[-1]
    else:
        html = response.text
        title = _extract_title(html)
        text = _strip_tags(html)

    return RawDocument(
        url=url,
        content_hash=content_hash,
        content_type=content_type.split(";")[0].strip(),
        text=text,
        raw_bytes=raw_bytes,
        title=title,
        status_code=response.status_code,
    )
