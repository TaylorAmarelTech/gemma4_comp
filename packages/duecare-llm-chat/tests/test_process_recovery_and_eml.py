"""Pins for three previously-untested Bulk File Review behaviors.

All three were implemented 2026-06-10 and flagged untested by the
improvement review:

  1. bundle.json restart recovery (_persist_bundle / _recover_last_bundle)
     — graph-chat survives a Kaggle OOM auto-restart.
  2. .eml MIME parsing (_decode_documentish_text) — mail headers, boundary
     markers, and base64 attachment bodies must NOT flow into GREP scoring
     as prose; bodies must.
  3. ZIP parse_error rows — a text member whose decode raises surfaces as
     an explicit parse_error work item instead of silently vanishing.
"""
from __future__ import annotations

import io
import os
import time
import zipfile
from email.message import EmailMessage
from pathlib import Path

from fastapi.testclient import TestClient

from duecare.chat.harnesses.process import handler as process_handler


# ---------------------------------------------------------------------------
# 1. bundle.json restart recovery
# ---------------------------------------------------------------------------

def test_persist_then_recover_returns_most_recent_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(process_handler, "_process_staging_root", lambda: tmp_path)
    first = process_handler._persist_bundle({"marker": "alpha", "rows": []}, "run_a")
    assert first["saved"] is True and Path(first["path"]).exists()
    time.sleep(0.05)  # distinct mtimes so "most recent" is deterministic
    second = process_handler._persist_bundle({"marker": "beta", "rows": []}, "run_b")
    assert second["saved"] is True
    # nudge run_b's mtime decisively newer (FAT/OneDrive mtime granularity)
    os.utime(Path(second["path"]), None)

    recovered = process_handler._recover_last_bundle()
    assert recovered is not None
    assert recovered["marker"] == "beta"


def test_recover_returns_none_without_staging_root(monkeypatch):
    monkeypatch.setattr(process_handler, "_process_staging_root", lambda: None)
    assert process_handler._recover_last_bundle() is None


def test_recover_skips_corrupt_bundle_json(monkeypatch, tmp_path):
    monkeypatch.setattr(process_handler, "_process_staging_root", lambda: tmp_path)
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    (run_dir / "bundle.json").write_text("{not valid json", encoding="utf-8")
    # the only candidate is corrupt -> recovery degrades to None, never raises
    assert process_handler._recover_last_bundle() is None


# ---------------------------------------------------------------------------
# 2. .eml MIME parsing
# ---------------------------------------------------------------------------

def _synthetic_eml() -> bytes:
    msg = EmailMessage()
    msg["From"] = "recruiter" + chr(64) + "agency.example"
    msg["To"] = "worker" + chr(64) + "mail.example"
    msg["Subject"] = "Deployment schedule"
    msg["DKIM-Signature"] = "v=1; a=rsa-sha256; d=agency.example; s=sel; bh=FAKE"
    msg.set_content(
        "The placement fee of PHP 50,000 must be paid before deployment."
    )
    msg.add_alternative(
        "<p>Your passport will be <b>held by the employer</b> on arrival.</p>",
        subtype="html",
    )
    msg.add_attachment(
        b"FAKEPDFBYTES-NOT-PROSE" * 20,
        maintype="application",
        subtype="pdf",
        filename="contract.pdf",
    )
    return bytes(msg)


def test_eml_keeps_text_bodies_and_drops_headers_and_attachments():
    out = process_handler._decode_documentish_text("mail.eml", _synthetic_eml())
    # both text bodies survive (html is tag-stripped)
    assert "placement fee of PHP 50,000" in out
    assert "held by the employer" in out
    assert "<p>" not in out
    # raw mail plumbing must NOT flow into GREP/entity extraction as prose
    assert "DKIM-Signature" not in out
    assert "boundary=" not in out
    # the base64-encoded attachment body must not appear
    # (b"FAKEPDFBYTES" base64-encodes through "RkFLRVBERkJZVEVT")
    assert "RkFLRVBERkJZVEVT" not in out
    assert "contract.pdf" not in out


def test_eml_without_mime_structure_falls_back_to_raw_text():
    raw = b"just a plain note with no mime structure at all"
    out = process_handler._decode_documentish_text("note.eml", raw)
    assert "no mime structure" in out


# ---------------------------------------------------------------------------
# 3. ZIP parse_error work items
# ---------------------------------------------------------------------------

def test_zip_text_member_decode_failure_surfaces_parse_error_row(monkeypatch):
    """A text-like ZIP member whose decode raises must become an explicit
    parse_error work item (visible in the bundle rows), not silently vanish."""
    from duecare.chat.app import create_app

    def _boom(name, data):
        raise RuntimeError("synthetic decode failure (e.g. mangled UTF-16)")

    monkeypatch.setattr(process_handler, "_decode_documentish_text", _boom)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("cases/intake_note.txt", "fee of PHP 50,000 charged")
    buf.seek(0)

    client = TestClient(create_app())
    resp = client.post(
        "/api/process/batch",
        files={"file": ("broken_text.zip", buf, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    bundle = resp.json()
    # the member is counted, not silently dropped
    assert bundle["summary"]["n_rows_total"] == 1
    results = bundle.get("results") or []
    assert results and "intake_note.txt" in str(results[0].get("row_id"))
    # and the failure is visibly flagged in the graph: a typed edge whose
    # evidence quote carries the parse_error marker + the member name
    edges = (bundle.get("intelligence") or {}).get("typed_edges") or []
    quotes = [str((e.get("evidence") or {}).get("quote") or "") for e in edges]
    flagged = [q for q in quotes if "parse_error_queued_for_manual_review" in q]
    assert flagged, "decode failure must surface as a visible parse_error flag"
    assert any("intake_note.txt" in q for q in flagged)
