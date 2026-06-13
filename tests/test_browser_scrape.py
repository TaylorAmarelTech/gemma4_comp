"""Tests for scripts/browser_scrape.py -- the JS-walled-registry connector.

Fully offline: the live Playwright render is injectable, so the capture
routing, endpoint discovery, JSON-envelope unwrapping, and propose-only output
are tested with a fake renderer -- no browser, no network. The only test that
touches Playwright is skipped when it is installed (it asserts the missing-dep
runbook message otherwise).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_MOD_PATH = _ROOT / "scripts" / "browser_scrape.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("browser_scrape", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen dataclass needs the module resolvable
    spec.loader.exec_module(mod)
    return mod


bs = _load_module()

# a realistic wrapped DMW-style API payload (camelCase keys exercise map_header)
AGENCY_JSON = json.dumps({"data": [
    {"agencyName": "Sunrise Overseas Manpower Inc.", "licenseNo": "POEA-1001",
     "status": "VALID", "officeAddress": "12 Mabini St, Manila", "telephone": "+63-2-5550-1001"},
    {"agencyName": "Pacific Bridge Recruitment Corp.", "licenseNo": "POEA-1002",
     "status": "CANCELLED", "officeAddress": "88 EDSA, Quezon City"},
]})
NOISE_JSON = json.dumps({"meta": {"buildId": "abc123"}, "session": "xyz"})


def _result_with(*payloads, endpoints=None, pages=1):
    return bs.CaptureResult(
        payloads=list(payloads),
        discovered_endpoints=endpoints or [p["url"] for p in payloads],
        pages_rendered=pages,
    )


def test_captures_to_profiles_picks_wrapped_agency_json_and_endpoint():
    res = _result_with(
        {"url": "https://dmw.gov.ph/api/config", "text": NOISE_JSON},
        {"url": "https://dmw.gov.ph/api/v1/lra?page=1", "text": AGENCY_JSON},
    )
    profiles, endpoint = bs.captures_to_profiles(res, source="browser:dmw_lra")
    names = {p["name"] for p in profiles}
    assert "Sunrise Overseas Manpower Inc." in names
    assert "Pacific Bridge Recruitment Corp." in names
    assert profiles  # statuses normalized by the registry schema
    assert {p["status"] for p in profiles} == {"valid", "cancelled"}
    # the agency-list endpoint is discovered, not the config noise
    assert endpoint == "https://dmw.gov.ph/api/v1/lra?page=1"


def _dmw_page(page, items):
    return json.dumps({"meta": {"total": 4, "perPage": 2, "currentPage": page, "lastPage": 2},
                       "data": items})


# real DMW public-API field shape (verified live 2026-06-13)
_DMW_A = {"name": "101 MOJO INT`L. CORPORATION", "classification": "Private Employment Agency",
          "license_status": "Valid License", "license_expiration_date": "2031-10-03T00:00:00.000Z",
          "is_valid": True, "representative": "James Tan", "address": "Unit 103",
          "municipality_province": "MALATE", "city_province": "MANILA",
          "contact_number": "(02) 86818959/09178870567", "eMail": "a@example.test", "data_as_of": "2026-06-01"}
_DMW_B = {"name": "Pacific Bridge Recruitment Corp.", "classification": "Manning Agency",
          "license_status": "Cancelled", "is_valid": False, "address": "88 EDSA",
          "municipality_province": "QC", "city_province": "MANILA", "contact_number": "(02) 555-2002"}


def test_dmw_schema_is_mapped_explicitly_and_aggregated_across_pages():
    # two pages of the DMW public API; records must aggregate, not pick-one
    res = _result_with(
        {"url": "https://master-api.dmw.gov.ph/api/v1/public/licensed-agencies?page=1", "text": _dmw_page(1, [_DMW_A])},
        {"url": "https://master-api.dmw.gov.ph/api/v1/public/licensed-agencies?page=2", "text": _dmw_page(2, [_DMW_B])},
        {"url": "https://dmw.gov.ph/api/config", "text": NOISE_JSON},
        pages=2,
    )
    profiles, endpoint = bs.captures_to_profiles(res, source="browser:dmw_lra")
    by_name = {p["name"]: p for p in profiles}
    assert set(by_name) == {"101 MOJO INT`L. CORPORATION", "Pacific Bridge Recruitment Corp."}
    # license_status mapped to status correctly (NOT into license_no), normalized
    assert by_name["101 MOJO INT`L. CORPORATION"]["status"] == "valid"
    assert by_name["Pacific Bridge Recruitment Corp."]["status"] == "cancelled"
    # address concatenates the locality fields; phones split on '/'
    a = by_name["101 MOJO INT`L. CORPORATION"]
    assert "MALATE" in a["address"] and "MANILA" in a["address"]
    assert "(02) 86818959" in a["phones"] and "09178870567" in a["phones"]
    assert a["email"] == "a@example.test"
    assert endpoint.startswith("https://master-api.dmw.gov.ph/api/v1/public/licensed-agencies")


def test_captures_to_profiles_handles_bare_array_and_html_table():
    bare = json.dumps([{"name": "Acme Manpower", "license_no": "POEA-9", "status": "valid"}])
    html = ("<table><tr><th>Agency Name</th><th>Status</th></tr>"
            "<tr><td>Beta Recruitment</td><td>Suspended</td></tr></table>")
    res = _result_with(
        {"url": "https://x/api/list.json", "text": bare},
        {"url": "https://x/legacy.html", "text": html},
    )
    profiles, endpoint = bs.captures_to_profiles(res, source="browser:test")
    # the bare JSON array scores higher (more agency-like keys) -> chosen
    assert any(p["name"] == "Acme Manpower" for p in profiles)
    assert endpoint == "https://x/api/list.json"


def test_captures_to_profiles_empty_when_no_agency_data():
    res = _result_with({"url": "https://x/c.json", "text": NOISE_JSON})
    profiles, endpoint = bs.captures_to_profiles(res, source="browser:test")
    assert profiles == [] and endpoint == ""


def test_render_and_capture_uses_injected_renderer():
    sentinel = bs.CaptureResult(payloads=[{"url": "u", "text": AGENCY_JSON}], pages_rendered=3)
    got = bs.render_and_capture(bs.PRESETS["dmw_lra"], renderer=lambda cfg: sentinel)
    assert got is sentinel


def test_main_writes_propose_only_manifest_with_endpoint(tmp_path, monkeypatch):
    out = tmp_path / "browser_scraped.json"
    fake = _result_with(
        {"url": "https://dmw.gov.ph/api/v1/lra?page=1", "text": AGENCY_JSON},
        {"url": "https://dmw.gov.ph/api/config", "text": NOISE_JSON},
    )
    monkeypatch.setattr(bs, "_playwright_render", lambda cfg: fake)
    rc = bs.main(["--preset", "dmw_lra", "--out", str(out)])
    assert rc == 0
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["_synthetic"] is False
    assert manifest["n_records"] == 2
    assert manifest["chosen_endpoint"] == "https://dmw.gov.ph/api/v1/lra?page=1"
    assert "https://dmw.gov.ph/api/config" in manifest["discovered_endpoints"]
    assert {r["name"] for r in manifest["records"]} == {
        "Sunrise Overseas Manpower Inc.", "Pacific Bridge Recruitment Corp."}


def test_main_url_mode_returns_1_when_nothing_parsed(tmp_path, monkeypatch):
    out = tmp_path / "empty.json"
    monkeypatch.setattr(bs, "_playwright_render",
                        lambda cfg: _result_with({"url": "https://x/c.json", "text": NOISE_JSON}))
    rc = bs.main(["--url", "https://x/registry", "--out", str(out)])
    assert rc == 1  # no records, but the manifest (with discovered endpoints) is still written
    assert out.exists()


def _playwright_installed() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(_playwright_installed(),
                    reason="playwright installed; the missing-dep runbook path cannot be exercised")
def test_playwright_missing_raises_helpful_runbook():
    with pytest.raises(ImportError) as exc:
        bs._playwright_render(bs.PRESETS["dmw_lra"])
    assert "playwright install" in str(exc.value)
