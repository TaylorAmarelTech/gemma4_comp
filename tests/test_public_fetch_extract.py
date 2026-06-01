from __future__ import annotations

import importlib
import pathlib
import sys

import pytest


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

extractor = importlib.import_module("public_fetch_extract")


def test_html_extraction_redacts_contact_details():
    email = "worker.help" + "@example.org"
    phone = "+1 202" + " 555 0100"
    content = f"""
    <html><head><style>.x{{}}</style><script>bad()</script></head>
    <body><h1>Debt bondage indicators</h1><p>Contact {email} or {phone}.</p></body></html>
    """.encode()

    result = extractor.extract_content(
        content,
        source_url="https://example.org/report.html?utm_source=x",
        content_type="text/html",
    )

    assert result["extractor"] in {"stdlib_html", "trafilatura"}
    assert "Debt bondage indicators" in result["text"]
    assert email not in result["text"]
    assert phone not in result["text"]
    assert result["pii_redactions"]["email"] == 1
    assert result["pii_redactions"]["phone"] == 1
    assert result["privacy"]["raw_private_cases_ingested"] is False


def test_pdf_without_optional_dependency_stays_metadata_only_for_minimal_pdf():
    result = extractor.extract_content(
        b"%PDF-1.4\n% synthetic fixture\n",
        source_url="https://example.org/report.pdf",
        content_type="application/pdf",
    )

    assert result["extractor"] in {"pdf_metadata_only_no_optional_extractor", "pdfplumber", "pypdf"}
    assert result["source_url"] == "https://example.org/report.pdf"
    assert result["privacy"]["public_or_synthetic_fixture_only"] is True


def test_rejects_private_case_roots_without_literal_fixture_leak(tmp_path):
    private_root = pathlib.Path("C:" + "\\" + "projects" + "\\" + "major_cases")
    with pytest.raises(extractor.PublicExtractionError):
        extractor.extract_local_file(private_root / "case.txt")


def test_fetch_public_url_uses_injected_request_and_normalizes():
    def fake_request(url: str, headers: dict[str, str]) -> bytes:
        assert url == "https://example.org/public/page.html?b=2"
        assert "User-Agent" in headers
        return b"<main>forced labour public guidance</main>"

    content, status = extractor.fetch_public_url(
        "https://Example.org/public/page.html?b=2#fragment",
        request_bytes=fake_request,
    )
    result = extractor.extract_content(content, source_url=status["url"], content_type="text/html")

    assert status["bytes"] > 0
    assert result["source_url"] == "https://example.org/public/page.html?b=2"
    assert "forced labour public guidance" in result["text"]


def test_local_text_fixture_extracts_without_network(tmp_path):
    fixture = tmp_path / "public_fixture.txt"
    passport = "AB" + "1234567"
    fixture.write_text(f"Passport {passport} and debt bondage are in this synthetic fixture.", encoding="utf-8")

    result = extractor.extract_local_file(fixture, source_url="https://example.org/public.txt")

    assert passport not in result["text"]
    assert result["pii_redactions"]["passport"] == 1
    assert "debt bondage" in result["text"]
