"""Tests for app/experts.py -- gap -> support-org matching (expert discovery for outreach).

Unit tests use a small synthetic org list (deterministic); the endpoint test exercises the
real 532-org directory shipped in the repo. An autouse fixture resets the module cache so the
DUECARE_SUPPORT_ORGS override in one test cannot leak into another.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import experts, outreach
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_org_cache():
    experts._CACHE = None
    yield
    experts._CACHE = None


@pytest.fixture()
def client():
    return TestClient(create_app(data_dir=pathlib.Path(tempfile.mkdtemp(prefix="experts-test-"))))


_SYNTH_ORGS = [
    {"name": "PH Migrant Aid", "org_type": "anti_trafficking_ngo", "country": "PH",
     "services": "recruitment fee complaints, migrant worker hotline", "scope": "national",
     "contact_phone": "1343"},
    {"name": "Generic Global Desk", "org_type": "ngo", "country": "US",
     "services": "general support", "scope": "global"},
    {"name": "Seafarer Welfare HK", "org_type": "union", "country": "HK",
     "services": "fishing and seafarer labour rights", "scope": "national"},
]


def _gap(**kw):
    base = dict(id="g", topic="t", corridor="PH-HK", audience="NGO caseworkers",
                ask="?", kind="fee_cap", base_priority=0.7)
    base.update(kw)
    return outreach.ContextGap(**base)


def test_match_ranks_corridor_country_first():
    out = experts.match_experts(_gap(), _SYNTH_ORGS, limit=5)
    assert out and out[0]["country"] == "PH"          # on-corridor + services match -> top
    assert out[0]["score"] >= 3.0
    assert any("PH" in w for w in out[0]["why"])


def test_sector_gap_surfaces_the_relevant_org():
    gap = _gap(id="sector_fishing", topic="fishing", kind="sector_pattern", corridor="multi")
    names = [e["name"] for e in experts.match_experts(gap, _SYNTH_ORGS, limit=5)]
    assert "Seafarer Welfare HK" in names              # fishing services matched


def test_empty_directory_is_graceful(monkeypatch, tmp_path):
    monkeypatch.setenv("DUECARE_SUPPORT_ORGS", str(tmp_path / "nope.yaml"))
    assert experts.load_orgs(force=True) == []
    assert experts.match_experts(_gap()) == []        # no orgs -> no suggestions, no crash


def test_endpoint_scans_real_directory_for_a_seed_gap(client):
    r = client.get("/api/outreach/experts/fee_cap_ph_hk")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["n_directory"] >= 100                 # the real ~532-org directory is loaded
    assert body["n_matches"] >= 1
    top = body["experts"][0]
    assert top["name"] and "score" in top and isinstance(top["why"], list)

    # unknown gap -> 404
    assert client.get("/api/outreach/experts/does-not-exist").status_code == 404
