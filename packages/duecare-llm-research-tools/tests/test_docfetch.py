"""Tests for the document fetch + PDF/HTML extraction layer (offline)."""
from __future__ import annotations

import io

import pytest

from duecare.research_tools.docfetch import (
    fetch_document, looks_like_pdf, pdf_to_text,
)

HTML = b"<html><body><main><p>Recruitment fees may not be charged.</p></main></body></html>"


def _valid_pdf_bytes() -> bytes:
    pypdf = pytest.importorskip("pypdf")
    w = pypdf.PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_looks_like_pdf_detection():
    assert looks_like_pdf("x", "", b"%PDF-1.7")              # magic bytes
    assert looks_like_pdf("x", "application/pdf", b"")        # content-type
    assert looks_like_pdf("https://e.org/report.pdf", "", b"")  # url suffix
    assert not looks_like_pdf("https://e.org/page", "text/html", b"<htm")


def test_pdf_to_text_graceful_on_garbage():
    assert pdf_to_text(b"not a pdf at all") == ""
    assert pdf_to_text(b"") == ""


def test_pdf_to_text_reads_valid_pdf_without_crashing():
    data = _valid_pdf_bytes()
    assert looks_like_pdf("x", "", data[:5])     # it's a real PDF
    assert isinstance(pdf_to_text(data), str)    # blank page -> "" but no crash


def test_fetch_document_routes_html():
    def raw(url, timeout):
        return (True, 200, HTML, "text/html; charset=utf-8", None)
    r = fetch_document("https://e.org/p", raw_fetch=raw)
    assert r.ok and "Recruitment fees" in r.text and "<p>" in r.text  # decoded HTML, not extracted yet


def test_fetch_document_routes_pdf():
    def raw(url, timeout):
        return (True, 200, b"%PDF-1.4 broken pdf bytes", "application/pdf", None)
    r = fetch_document("https://e.org/doc.pdf", raw_fetch=raw)
    # routed to the PDF branch -> pdf_to_text (unparseable here -> "") not raw bytes as text
    assert r.ok and r.text == "" and "%PDF" not in r.text


def test_fetch_document_unreachable():
    def raw(url, timeout):
        return (False, 403, b"", "", "HTTP 403")
    r = fetch_document("https://e.org/x", raw_fetch=raw)
    assert not r.ok and r.status == 403
