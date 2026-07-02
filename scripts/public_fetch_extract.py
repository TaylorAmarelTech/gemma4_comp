#!/usr/bin/env python3
"""Fetch/extract public-source text with conservative local fallbacks.

The module is no-network by default when used from tests or as a local file
extractor. Optional libraries such as trafilatura, pdfplumber, pypdf, and
MarkItDown are used only when installed and only for already-fetched public
content or explicit local fixture files. It rejects private case roots and
redacts obvious contact/document identifiers before returning text.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER_AGENT = "DueCarePublicFetchExtract/0.1 (public benchmark research only)"
_MAJOR_CASES_WINDOWS = re.escape("C:" + "\\" + "projects" + "\\" + "major_cases")
_MAJOR_CASES_POSIX = re.escape("/projects/" + "major_cases")

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{7,}\d)(?!\w)")),
    ("passport", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b", re.I)),
    ("ssn_like", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
)


class PublicExtractionError(ValueError):
    """Raised when extraction would violate the public-source boundary."""


def stable_hash(value: bytes | str, *, n: int = 16) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8", errors="replace")
    return hashlib.sha256(value).hexdigest()[:n]


def reject_private_path(path: Path) -> None:
    raw = str(path)
    if re.search(rf"(?:{_MAJOR_CASES_WINDOWS}|{_MAJOR_CASES_POSIX})", raw, re.I):
        raise PublicExtractionError("private case root is not allowed")


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    redacted = text
    for label, pattern in PII_PATTERNS:
        redacted, count = pattern.subn(f"[REDACTED_{label.upper()}]", redacted)
        if count:
            counts[label] = count
    return redacted, counts


def normalize_public_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PublicExtractionError("only http/https public URLs are allowed")
    if re.search(rf"(?:{_MAJOR_CASES_WINDOWS}|{_MAJOR_CASES_POSIX})", url, re.I):
        raise PublicExtractionError("private case URL/path is not allowed")
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))


def html_to_text_stdlib(content: bytes) -> str:
    raw = content.decode("utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?is)</(p|div|li|h[1-6]|tr)>", "\n", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def extract_html(content: bytes) -> tuple[str, str]:
    if importlib.util.find_spec("trafilatura") is not None:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(content.decode("utf-8", errors="replace"))
        if extracted:
            return extracted, "trafilatura"
    return html_to_text_stdlib(content), "stdlib_html"


def extract_pdf(content: bytes) -> tuple[str, str]:
    if importlib.util.find_spec("pdfplumber") is not None:
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text, "pdfplumber"
        except Exception:
            pass
    if importlib.util.find_spec("pypdf") is not None:
        try:
            import pypdf  # type: ignore

            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text, "pypdf"
        except Exception:
            pass
    return "", "pdf_metadata_only_no_optional_extractor"


def extract_markitdown(path: Path) -> tuple[str, str]:
    if importlib.util.find_spec("markitdown") is None:
        return "", "markitdown_not_installed"
    from markitdown import MarkItDown  # type: ignore

    result = MarkItDown().convert(str(path))
    return getattr(result, "text_content", "") or "", "markitdown"


def extract_content(
    content: bytes,
    *,
    source_url: str = "",
    content_type: str = "",
    max_chars: int = 16000,
) -> dict:
    if source_url:
        source_url = normalize_public_url(source_url)
    content_type_l = content_type.lower()
    source_path = urllib.parse.urlsplit(source_url).path.lower() if source_url else ""
    method = "plain_text"
    if "html" in content_type_l or source_path.endswith((".html", ".htm")) or content.lstrip().startswith(b"<"):
        text, method = extract_html(content)
    elif "pdf" in content_type_l or source_path.endswith(".pdf") or content.startswith(b"%PDF"):
        text, method = extract_pdf(content)
    else:
        text = content.decode("utf-8", errors="replace")
    redacted, counts = redact_text(text)
    redacted = redacted[:max_chars]
    return {
        "schema_version": "public_fetch_extract_result.v1",
        "source_url": source_url,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "content_bytes": len(content),
        "extractor": method,
        "text": redacted,
        "text_chars": len(redacted),
        "pii_redactions": counts,
        "privacy": {
            "raw_private_cases_ingested": False,
            "public_or_synthetic_fixture_only": True,
        },
    }


def extract_local_file(path: Path, *, source_url: str = "", max_chars: int = 16000) -> dict:
    reject_private_path(path)
    suffix = path.suffix.lower()
    if suffix in {".docx", ".pptx", ".xlsx"}:
        text, method = extract_markitdown(path)
        redacted, counts = redact_text(text)
        return {
            "schema_version": "public_fetch_extract_result.v1",
            "source_url": source_url,
            "local_fixture_name": path.name,
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "content_bytes": path.stat().st_size,
            "extractor": method,
            "text": redacted[:max_chars],
            "text_chars": len(redacted[:max_chars]),
            "pii_redactions": counts,
            "privacy": {
                "raw_private_cases_ingested": False,
                "public_or_synthetic_fixture_only": True,
            },
        }
    return extract_content(path.read_bytes(), source_url=source_url, content_type=suffix.lstrip("."), max_chars=max_chars)


def fetch_public_url(
    url: str,
    *,
    request_bytes: Callable[[str, dict[str, str]], bytes] | None = None,
) -> tuple[bytes, dict]:
    normalized = normalize_public_url(url)
    request_bytes = request_bytes or _default_request_bytes
    content = request_bytes(normalized, {"User-Agent": DEFAULT_USER_AGENT})
    return content, {"url": normalized, "status": "fetched", "bytes": len(content)}


def _default_request_bytes(url: str, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec: URL was normalized as public
        return response.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Local public/synthetic fixture file to extract.")
    parser.add_argument("--url", help="Public URL to fetch and extract. Requires --allow-network.")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--max-chars", type=int, default=16000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.file:
        result = extract_local_file(args.file, source_url=args.url or "", max_chars=args.max_chars)
    elif args.url and args.allow_network:
        content, _status = fetch_public_url(args.url)
        result = extract_content(content, source_url=args.url, max_chars=args.max_chars)
    else:
        raise SystemExit("Provide --file, or provide --url with --allow-network.")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
