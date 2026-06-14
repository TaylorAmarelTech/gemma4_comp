"""Tests for scripts/archive_source.py -- Wayback provenance archival.

Offline: `fetch` is injectable, so save/latest URL building + response parsing
and the propose-only archive log are tested with no network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ar = _load("archive_source", _ROOT / "scripts" / "archive_source.py")


def test_save_reads_snapshot_from_content_location_header():
    def fetch(url):  # mimic web.archive.org/save returning a Content-Location
        return ("ok", {"Content-Location": "/web/20260613010101/https://dmw.gov.ph/x"},
                "https://web.archive.org/save/https://dmw.gov.ph/x")
    r = ar.save("https://dmw.gov.ph/x", fetch=fetch)
    assert r["snapshot_url"] == "https://web.archive.org/web/20260613010101/https://dmw.gov.ph/x"
    assert r["status"] == "saved"


def test_save_falls_back_to_final_url_then_submitted():
    r = ar.save("https://x.test", fetch=lambda u: ("body", {}, ""))
    assert r["status"] == "submitted" and r["snapshot_url"] == ""


def test_save_handles_error():
    def boom(url):
        raise ConnectionError("down")
    r = ar.save("https://x.test", fetch=boom)
    assert r["snapshot_url"] == "" and r["status"].startswith("error_")


def test_latest_parses_availability_api():
    def fetch(url):
        return json.dumps({"archived_snapshots": {"closest": {
            "available": True, "url": "http://web.archive.org/web/2023/https://x", "timestamp": "20230119"}}})
    r = ar.latest("https://x", fetch=fetch)
    assert r["available"] is True and r["timestamp"] == "20230119"
    assert "web.archive.org" in r["snapshot_url"]


def test_latest_handles_no_snapshot():
    r = ar.latest("https://x", fetch=lambda u: json.dumps({"archived_snapshots": {}}))
    assert r["available"] is False and r["snapshot_url"] == ""


def test_archive_sources_writes_propose_only_log(tmp_path):
    log = tmp_path / "archive_log.jsonl"
    def fetch(url):
        return ("ok", {"Content-Location": f"/web/2026/{url}"}, "")
    res = ar.archive_sources(["https://a.test", "https://b.test"], fetch=fetch,
                             log_path=log, archived_at="2026-06-13T12:00")
    assert len(res) == 2 and all(r["snapshot_url"] for r in res)
    lines = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines()]
    assert {r["url"] for r in lines} == {"https://a.test", "https://b.test"}
    assert lines[0]["archived_at"] == "2026-06-13T12:00"
