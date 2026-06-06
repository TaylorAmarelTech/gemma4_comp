"""Tests for the acquisition orchestrator (offline, injected fake fetch)."""
from __future__ import annotations

from duecare.research_tools.acquire import acquire, extract_main_text, scrub_text
from duecare.research_tools.monitor import FetchResult

# Synthetic public-law-style pages (no real PII). Long enough to chunk.
_BODY1 = (
    "<html><body><nav>menu</nav><main>"
    "<p>Under C189 the domestic worker on the PH-HK corridor keeps custody of her "
    "passport at all times. Recruitment fees may not be charged to the worker.</p>"
    "<p>The employer bears all costs of recruitment, deployment, and travel. Any fee "
    "collected from the worker is unlawful and must be refunded in full.</p>"
    "<p>Contact the office at test.person@example.org or +63 917 555 0000 for help.</p>"
    "</main></body></html>")
_BODY2 = (
    "<html><body><main>"
    "<p>FATF guidance addresses financial flows linked to trafficking and the "
    "financial action task force typology of layered placement fees.</p>"
    "<p>Supervised entities should file suspicious transaction reports when wage "
    "deductions resemble debt bondage repayment schedules over many months.</p>"
    "</main></body></html>")


def _fetch(mapping):
    def f(url):
        if url in mapping:
            return FetchResult(ok=True, status=200, text=mapping[url])
        return FetchResult(ok=False, status=404, error="HTTP 404")
    return f


def test_extract_strips_tags():
    out = extract_main_text(_BODY1, "https://example.org/a")
    assert "C189" in out and "<p>" not in out


def test_scrub_redacts_contact_pii():
    out = scrub_text("reach me at test.person@example.org or 917-555-0000 today")
    assert "@example.org" not in out and "[redacted]" in out


def test_acquire_keeps_chunks_and_builds_graph():
    cands = [
        {"id": "d1", "url": "u1", "title": "DW rights", "source_tier": "ilo",
         "jurisdictions": ["PH"], "signals": ["debt_bondage"]},
        {"id": "d2", "url": "u2", "title": "FATF", "source_tier": "fatf"},
    ]
    r = acquire(cands, fetch=_fetch({"u1": _BODY1, "u2": _BODY2}), min_doc_chars=100)
    assert r.n_fetched == 2 and r.n_chunks_kept >= 2
    assert r.graph["nodes"]                       # entities + docs present
    # scrubbed: no raw email survives into staged chunks
    assert all("@example.org" not in c.text for c in r.kept)


def test_acquire_records_unreachable():
    r = acquire([{"id": "x", "url": "missing"}], fetch=_fetch({}))
    assert r.n_fetched == 0 and r.n_unreachable == 1
    assert r.unreachable[0]["status"] == 404


def test_acquire_dedups_identical_sources():
    cands = [{"id": "a", "url": "u1"}, {"id": "b", "url": "u1b"}]
    r = acquire(cands, fetch=_fetch({"u1": _BODY1, "u1b": _BODY1}), min_doc_chars=100)
    # second identical doc -> all its chunks dropped as exact dups
    assert any(d.get("_dup_reason") == "exact" for d in r.dropped)
    kept_docs = {c.doc_id for c in r.kept}
    assert "b" not in kept_docs


def test_acquire_drops_too_short():
    r = acquire([{"id": "t", "url": "u"}], fetch=_fetch({"u": "<p>tiny</p>"}), min_doc_chars=200)
    assert r.n_chunks_kept == 0
    assert any(d.get("_dup_reason") == "too_short" for d in r.dropped)
