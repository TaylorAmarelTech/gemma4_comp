"""Offline tests for the recruitment-text suspicious-language scanner.

The scanner (scripts/scan_recruitment_text.py) reuses the triage GREP tier to
flag trafficking-indicative recruitment language. These tests run fully
offline (no --url / network): they exercise HTML stripping, item gathering
from a temp directory, the GREP-only scan, the rule-level "why" enrichment,
and the propose-only report writer.
"""
from __future__ import annotations

import glob
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)


def _load_scanner():
    path = _ROOT / "scripts" / "scan_recruitment_text.py"
    spec = importlib.util.spec_from_file_location("dc_scan_recruitment", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCAN = _load_scanner()

EXPLOITATIVE = (
    "Great job in Dubai! Pay PHP 120,000 placement fee before deployment. "
    "We hold your passport for safekeeping until the loan is repaid via "
    "salary deduction every month."
)
BENIGN = (
    "Hiring a barista for our Quezon City cafe. PHP 610/day plus SSS, "
    "PhilHealth, and Pag-IBIG. Walk-in interviews Monday to Friday."
)


def test_strip_html_removes_tags_and_scripts():
    raw = "<html><head><style>x{}</style></head><body><p>Pay a fee</p>" \
          "<script>evil()</script></body></html>"
    out = SCAN._strip_html(raw)
    assert "Pay a fee" in out
    assert "<p>" not in out
    assert "evil()" not in out
    assert "x{}" not in out


def test_scan_flags_exploitative_and_passes_benign():
    result = SCAN.scan([
        {"id": "ad-bad", "text": EXPLOITATIVE},
        {"id": "ad-ok", "text": BENIGN},
    ])
    by_id = {r["id"]: r for r in result["items"]}
    assert by_id["ad-bad"]["status"] == "flagged"
    assert by_id["ad-bad"]["grep"]["n_hits"] >= 1
    assert by_id["ad-bad"]["grep"]["max_severity"] in {"critical", "high"}
    # the benign ad must not be flagged (grep-only -> passed_grep_only)
    assert by_id["ad-ok"]["status"] in {"passed_grep_only", "review"}
    assert result["summary"]["n_flagged"] >= 1


def test_why_enrichment_resolves_rule_ids_to_citations():
    """The fix for the rule/rule_id key mismatch must populate per-rule 'why'
    with real citations from the live GREP_RULES (this was empty before)."""
    result = SCAN.scan([{"id": "ad-bad", "text": EXPLOITATIVE}])
    row = result["items"][0]
    assert row["why"], "flagged item must carry rule-level 'why' detail"
    first = row["why"][0]
    assert first["rule"]
    assert first["severity"]
    assert first["citation"], "each fired rule should resolve to its citation"
    # the debt-bondage cluster should be among the hits for this ad
    rules = {w["rule"] for w in row["why"]}
    assert any("debt" in r or "fee" in r or "passport" in r.lower() or "loan" in r
               for r in rules)


def test_gather_items_from_directory(tmp_path):
    (tmp_path / "ad1.txt").write_text(EXPLOITATIVE, encoding="utf-8")
    (tmp_path / "ad2.html").write_text(
        f"<html><body><div>{BENIGN}</div></body></html>", encoding="utf-8")
    (tmp_path / "empty.txt").write_text("   ", encoding="utf-8")  # dropped

    class _Args:
        text = None
        file = None
        dir = str(tmp_path)
        url = None

    items = SCAN.gather_items(_Args())
    ids = {it["id"] for it in items}
    assert "ad1.txt" in ids and "ad2.html" in ids
    assert "empty.txt" not in ids  # blank items are dropped
    # the html item is tag-stripped
    html_item = next(it for it in items if it["id"] == "ad2.html")
    assert "<div>" not in html_item["text"]


def test_write_report_is_propose_only(tmp_path):
    result = SCAN.scan([{"id": "ad-bad", "text": EXPLOITATIVE}])
    json_path, md_path = SCAN.write_report(result, tmp_path, "testhash")
    assert json_path.exists() and md_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "suspicious-language scan" in md
    assert "flagged" in md
    assert "Advisory, not a verdict" in md


def test_main_runs_end_to_end_with_text(tmp_path):
    rc = SCAN.main(["--text", EXPLOITATIVE, "--out", str(tmp_path), "--stamp", "e2e"])
    assert rc == 0
    assert (tmp_path / "scan_e2e.json").exists()
    assert (tmp_path / "scan_e2e.md").exists()
