"""Tests for scripts/hk_eaa_collector.py -- the HK EAA collector + robust waits.

Offline: the browser PAGE is a fake, so the robust-waits retry/backoff, the
gated-flow pagination, the PDF parser, and the entity mapping are tested with no
browser and no network (injected `sleep` makes retries instant).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hk = _load("hk_eaa_collector", _ROOT / "scripts" / "hk_eaa_collector.py")
_NOSLEEP = lambda *_a, **_k: None


# ---- robust-waits engine --------------------------------------------------

class _FlakyPage:
    def __init__(self, fail_times):
        self.fail = fail_times
        self.calls = 0
    def goto(self, url, timeout=None, wait_until=None):
        self.calls += 1
        if self.calls <= self.fail:
            raise RuntimeError("transient net error")
    def wait_for_selector(self, *a, **k): return True
    def click(self, *a, **k): pass
    def content(self): return ""


def test_robustwaits_retries_then_succeeds():
    rw = hk.RobustWaits(_FlakyPage(fail_times=1), sleep=_NOSLEEP)
    assert rw.goto("https://x") is True
    assert rw.page.calls == 2                      # failed once, retried, succeeded
    assert any(s == "ok" for *_h, s in rw.log)


def test_robustwaits_gives_up_after_retries():
    rw = hk.RobustWaits(_FlakyPage(fail_times=99), retries=2, sleep=_NOSLEEP)
    assert rw.goto("https://x") is False
    assert rw.page.calls == 3                       # initial + 2 retries
    assert rw.log[-1][-1] == "failed"


class _ClickPage:
    def __init__(self, good):
        self.good = good
        self.clicked = None
    def wait_for_selector(self, sel, timeout=None):
        if sel != self.good:
            raise RuntimeError("not found")
    def click(self, sel, timeout=None): self.clicked = sel
    def goto(self, *a, **k): pass
    def content(self): return ""


def test_wait_click_tries_candidates_until_one_works():
    rw = hk.RobustWaits(_ClickPage(good="text=Agree"), sleep=_NOSLEEP)
    assert rw.wait_click(["text=Accept", "text=Agree", "text=Confirm"]) is True
    assert rw.page.clicked == "text=Agree"


# ---- gated-flow pagination ------------------------------------------------

class _FakeEAAPage:
    """Returns fixture result tables per page; page 3 is empty (end signal)."""
    def __init__(self, pages):
        self.pages = pages
        self.cur = None
        self.clicks = []
        self.gotos = []
    def goto(self, url, timeout=None, wait_until=None):
        import re
        self.gotos.append(url)
        m = re.search(r"page-no=(\d+)", url)
        self.cur = int(m.group(1)) if m else None
    def wait_for_selector(self, *a, **k): return True
    def click(self, sel, timeout=None): self.clicks.append(sel)
    def content(self): return self.pages.get(self.cur, "<html><body></body></html>")


def _table(*rows):
    body = "".join(f"<tr><td>{n}</td><td>{a}</td><td>{s}</td></tr>" for n, a, s in rows)
    return f"<table><tr><th>Agency Name</th><th>Address</th><th>Status</th></tr>{body}</table>"


def test_collect_hk_eaa_live_accepts_gates_and_paginates():
    pages = {1: _table(("ADECCO Personnel Limited", "Wan Chai, Hong Kong", "Valid"),
                       ("ACTON CONSULTING LIMITED", "Central, Hong Kong", "Valid")),
             2: _table(("Air Win Employment Co.", "Tsuen Wan, New Territories", "Valid"))}
    page = _FakeEAAPage(pages)
    res = hk.collect_hk_eaa_live(page, max_pages=10, sleep=_NOSLEEP)
    names = {r["name"] for r in res["records"]}
    assert names == {"ADECCO Personnel Limited", "ACTON CONSULTING LIMITED", "Air Win Employment Co."}
    assert res["pages"] == 2                        # stopped when page 3 returned no rows
    assert page.clicks                              # gate accept clicks happened


# ---- result.php deterministic path ----------------------------------------

def _result_block(name, district, address, aid):
    return (f'<div class="result"> <h3 class="en-name">{name}</h3> '
            f'<p><strong>District:</strong></p> <p>{district}</p> '
            f'<p><strong>Address:</strong></p> <p>{address}</p> '
            f'<p class="right"><a href="record.html?agency_id={aid}" role="button">View Details</a></p> </div>')


def test_parse_result_php_extracts_name_district_address_id():
    html = ("<div class='wrap'>" +
            _result_block("ADECCO Personnel Limited", "Wan Chai District",
                          "Flat 1101, K. Wah Centre, North Point, Hong Kong", "TTV6M1k9") +
            _result_block("South China Manpower Co", "Kwun Tong District",
                          "Room 02, How Ming Street, Kowloon", "TzVEM0k9") + "</div>")
    recs = hk.parse_result_php(html)
    assert len(recs) == 2
    a = recs[0]
    assert a["name"] == "ADECCO Personnel Limited" and a["district"] == "Wan Chai District"
    assert "K. Wah Centre" in a["address"] and a["license_no"] == "TTV6M1k9"
    assert a["jurisdiction"] == "HK" and a["status"] == "valid" and a["source_tier"] == "official"


def test_collect_resultphp_paginates_until_empty():
    page1 = _result_block("Agency A Ltd", "Central", "1 Queen's Road", "AA1") + \
            _result_block("Agency B Ltd", "Mong Kok", "2 Nathan Road", "BB2")
    page2 = _result_block("Agency C Ltd", "Sha Tin", "3 New Town Plaza", "CC3")
    posts = []
    def request_post(url, form):
        posts.append(form)
        return {"1": page1, "2": page2}.get(form["page-no"], "<html>no results</html>")
    res = hk.collect_hk_eaa_resultphp(request_post=request_post, get_token=lambda: "tok123",
                                      max_pages=10, sleep=_NOSLEEP)
    names = {r["name"] for r in res["records"]}
    assert names == {"Agency A Ltd", "Agency B Ltd", "Agency C Ltd"}
    assert res["pages"] == 2                         # stopped at empty page 3
    assert all(p["token"] == "tok123" for p in posts)  # CSRF token sent each page


# ---- PDF baseline parser --------------------------------------------------

def test_parse_pdf_list_real_format():
    text = ("3\n"
            "ACTON CONSULTING LIMITED  Central, Hong Kong\n"
            "ADECCO Personnel Limited  Wan Chai, Hong Kong\n"
            "adi Consult China - Hong Kong Limited  Tsuen Wan, New Territories\n"
            "Air Win Employment Co.  Tsuen Wan, New Territories\n"
            "\n")
    recs = hk.parse_pdf_list(text)
    by = {r["name"]: r for r in recs}
    assert "ACTON CONSULTING LIMITED" in by and "Air Win Employment Co." in by
    assert by["ACTON CONSULTING LIMITED"]["address"] == "Central, Hong Kong"
    assert by["ADECCO Personnel Limited"]["jurisdiction"] == "HK"
    assert by["ADECCO Personnel Limited"]["status"] == "valid"
    assert by["adi Consult China - Hong Kong Limited"]["address"].endswith("New Territories")


def test_parse_pdf_list_skips_page_numbers_and_headers():
    text = "1\n42\nList of licensed employment agencies, Hong Kong\nAJOB  Sheung Wan, Hong Kong\n"
    recs = hk.parse_pdf_list(text)
    names = {r["name"] for r in recs}
    assert names == {"AJOB"}  # page numbers + "List of..." header excluded


# ---- entity mapping -------------------------------------------------------

def test_records_to_entities_maps_to_hk_recruitment_agency():
    ents = hk.records_to_entities([{"name": "ADECCO Personnel Limited",
                                    "address": "Wan Chai, Hong Kong", "status": "valid"}])
    assert len(ents) == 1
    e = ents[0]
    assert e["entity_type"] == "recruitment_agency" and e["jurisdiction"] == "HK"
    assert e["source_tier"] == "official"
