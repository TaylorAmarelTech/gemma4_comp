"""Document fetch + extraction for acquisition: fetch raw bytes, detect PDF vs
HTML, and return a ``FetchResult`` whose ``.text`` is ready for chunking (PDF
text via pypdf; HTML decoded for trafilatura downstream).

This is a distinct layer from ``monitor`` (text-only change-detection fetch):
documents genuinely need bytes (PDFs) and content-type routing, while the
monitor only hashes decoded text. The raw byte fetch is injectable, so routing /
extraction are deterministic and testable offline; pypdf is optional (a PDF
yields empty text rather than crashing when pypdf is absent).
"""
from __future__ import annotations

import io
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from .monitor import _BROWSER_HEADERS, FetchResult, _decode_bytes

try:
    from curl_cffi import requests as _curl_requests  # type: ignore
    _HAVE_CURL = True
except Exception:  # noqa: BLE001
    _HAVE_CURL = False

try:
    import pypdf  # type: ignore
    _HAVE_PYPDF = True
except Exception:  # noqa: BLE001
    _HAVE_PYPDF = False

# (ok, status, content_bytes, content_type, error)
RawResult = tuple[bool, int, bytes, str, str | None]


def looks_like_pdf(url: str, content_type: str, head: bytes) -> bool:
    """True if a response is a PDF (by magic bytes, content-type, or URL)."""
    if head[:5] == b"%PDF-":
        return True
    if "application/pdf" in (content_type or "").lower():
        return True
    return (url or "").lower().split("?")[0].endswith(".pdf")


def pdf_to_text(content: bytes, *, max_pages: int = 200) -> str:
    """Extract text from PDF bytes via pypdf. Returns '' if pypdf is missing or
    the bytes don't parse (graceful -- never raises)."""
    if not _HAVE_PYPDF or not content:
        return ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        parts: list[str] = []
        for page in reader.pages[:max_pages]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 -- skip an unreadable page
                pass
        return "\n\n".join(p.strip() for p in parts if p.strip())
    except Exception:  # noqa: BLE001 -- not a parseable PDF
        return ""


def _raw_curl(url: str, timeout: float) -> RawResult:
    try:
        r = _curl_requests.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        ok = 200 <= int(r.status_code) < 300
        ct = ""
        try:
            ct = r.headers.get("content-type", "") or ""
        except Exception:  # noqa: BLE001
            ct = ""
        return (ok, int(r.status_code), r.content if ok else b"", ct,
                None if ok else f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        return (False, 0, b"", "", f"{type(e).__name__}: {str(e)[:120]}")


def _raw_urllib(url: str, timeout: float, _redirects: int = 4) -> RawResult:
    req = urllib.request.Request(url, headers=dict(_BROWSER_HEADERS))
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 -- public URLs
                ct = r.headers.get("content-type", "") if r.headers else ""
                return (True, getattr(r, "status", 200), r.read(8_000_000), ct or "", None)
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            if e.code in (301, 302, 303, 307, 308) and loc and _redirects > 0:
                return _raw_urllib(urllib.parse.urljoin(url, loc), timeout, _redirects - 1)
            return (False, int(e.code), b"", "", f"HTTP {e.code}")
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt == 1:
                continue
            return (False, 0, b"", "", f"{type(e).__name__}: {str(e)[:120]}")
        except Exception as e:  # noqa: BLE001
            return (False, 0, b"", "", f"{type(e).__name__}: {str(e)[:120]}")
    return (False, 0, b"", "", "retry exhausted")


def default_raw_fetch(url: str, timeout: float = 25.0) -> RawResult:
    """Fetch raw bytes + content-type (curl_cffi preferred, urllib fallback)."""
    if _HAVE_CURL:
        ok, status, content, ct, err = _raw_curl(url, timeout)
        if ok or status:
            return (ok, status, content, ct, err)
    return _raw_urllib(url, timeout)


def fetch_document(
    url: str,
    *,
    raw_fetch: Callable[[str, float], RawResult] | None = None,
    timeout: float = 25.0,
) -> FetchResult:
    """Fetch a document and return a ``FetchResult`` with extracted ``.text``:
    PDF bytes -> pypdf text; everything else -> charset-decoded body (HTML, ready
    for trafilatura). ``raw_fetch`` is injectable for offline tests."""
    rf = raw_fetch or default_raw_fetch
    ok, status, content, ctype, err = rf(url, timeout)
    if not ok:
        return FetchResult(ok=False, status=status, error=err)
    if looks_like_pdf(url, ctype, content[:5]):
        return FetchResult(ok=True, status=status, text=pdf_to_text(content))
    return FetchResult(ok=True, status=status, text=_decode_bytes(content)[:2_000_000])
