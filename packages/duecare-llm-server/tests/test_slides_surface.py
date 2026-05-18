"""Contract tests for the slide-deck demo surface.

Pins:
- /start serves the two-tile landing with both tiles wired to the
  /slides and /slides/setup routes.
- /slides serves the full-screen pitch deck with keyboard navigation
  hooks and reads the cached row from
  localStorage['duecare.slides.demo.chat'].
- /slides/setup serves the cached-I/O generator with audience +
  use_case selectors that match the documented keys.
- POST /api/slides/cached-io returns a deterministic prompt + response
  per (audience, use_case), validates inputs, respects prompt override.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _make_app(tmp_dir: str):
    pytest.importorskip("fastapi")
    from duecare.server import create_app
    from duecare.server.state import ServerState
    state = ServerState(db_path=str(Path(tmp_dir) / "t.duckdb"),
                        pipeline_output_dir=str(Path(tmp_dir) / "out"))
    Path(tmp_dir, "out").mkdir(parents=True, exist_ok=True)
    return create_app(state), state


def _client():
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    tmp = tempfile.mkdtemp(prefix="duecare_slides_test_")
    try:
        app, _ = _make_app(tmp)
    except Exception as e:
        pytest.skip(f"server cannot construct: {e}")
    return TestClient(app)


# --------------------------------------------------------------------------
# Page routes
# --------------------------------------------------------------------------

def test_start_landing_serves_two_tiles() -> None:
    c = _client()
    r = c.get("/start")
    assert r.status_code == 200
    html = r.text
    assert 'href="/slides"' in html, "Project slides tile must link to /slides"
    assert 'href="/slides/setup"' in html, \
        "Slide setup tile must link to /slides/setup"
    assert "Project slides" in html
    assert "Project slide setup" in html


def test_start_landing_is_recording_oriented() -> None:
    c = _client()
    r = c.get("/start")
    assert r.status_code == 200
    html = r.text.lower()
    assert "recording" in html, "Landing should call out the recording use case"
    assert "cached" in html or "cache" in html, \
        "Landing should mention the cached I/O path"


def test_slides_deck_serves_full_screen_pitch() -> None:
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    for marker in [
        "data-slide",  # individual slide nodes
        "ArrowRight",   # keyboard nav: next slide
        "ArrowLeft",    # keyboard nav: prev slide
        "duecare.slides.demo.chat",  # localStorage key for cached row
    ]:
        assert marker in html, f"slides.html missing marker: {marker!r}"


def test_slides_deck_has_demo_chat_slide_anchor() -> None:
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    assert "demo-chat" in html, (
        "Slides deck must expose a demo-chat anchor for /slides#demo-chat")


def test_slides_setup_serves_audience_and_use_case_selectors() -> None:
    c = _client()
    r = c.get("/slides/setup")
    assert r.status_code == 200
    html = r.text
    for key in ["worker", "ngo", "regulator",
                "researcher", "developer", "platform"]:
        assert f'value="{key}"' in html, \
            f"slides-setup.html missing audience option: {key}"
    for key in ["ph_hk_placement_fee", "passport_retention",
                "contract_substitution", "debt_bondage",
                "retaliation_risk", "fee_camouflage",
                "provider_choice"]:
        assert f'value="{key}"' in html, \
            f"slides-setup.html missing use_case option: {key}"
    assert "/api/slides/cached-io" in html
    assert "duecare.slides.demo.chat" in html


# --------------------------------------------------------------------------
# API: POST /api/slides/cached-io
# --------------------------------------------------------------------------

def test_cached_io_returns_default_prompt_for_known_pair() -> None:
    c = _client()
    r = c.post("/api/slides/cached-io", json={
        "audience": "worker",
        "use_case": "ph_hk_placement_fee",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "prompt" in data and "response" in data
    assert data["audience"] == "worker"
    assert data["use_case"] == "ph_hk_placement_fee"
    assert "PHP 50,000" in data["prompt"]
    assert "Hong Kong" in data["prompt"]
    assert "RA 11227" in data["response"]
    assert ("ILO C029" in data["response"]
            or "Convention 29" in data["response"])


def test_cached_io_is_deterministic_per_audience_use_case() -> None:
    """Same (audience, use_case) returns the same prompt + response."""
    c = _client()
    payload = {"audience": "regulator", "use_case": "passport_retention"}
    r1 = c.post("/api/slides/cached-io", json=payload)
    r2 = c.post("/api/slides/cached-io", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["prompt"] == r2.json()["prompt"]
    assert r1.json()["response"] == r2.json()["response"]


def test_cached_io_changes_with_audience() -> None:
    """The same use_case should produce different framings per audience."""
    c = _client()
    a = c.post("/api/slides/cached-io", json={
        "audience": "worker",
        "use_case": "debt_bondage",
    }).json()
    b = c.post("/api/slides/cached-io", json={
        "audience": "ngo",
        "use_case": "debt_bondage",
    }).json()
    assert a["response"] != b["response"], (
        "Worker and NGO responses must differ in framing")
    assert "debt bondage" in a["response"].lower()
    assert "debt bondage" in b["response"].lower()


def test_cached_io_respects_prompt_override() -> None:
    c = _client()
    custom = "Custom recruiter message about a placement loan in PH."
    r = c.post("/api/slides/cached-io", json={
        "audience": "developer",
        "use_case": "debt_bondage",
        "prompt": custom,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["prompt"] == custom
    assert "override" in data["response"].lower()


def test_cached_io_rejects_unknown_use_case() -> None:
    c = _client()
    r = c.post("/api/slides/cached-io", json={
        "audience": "worker",
        "use_case": "definitely_not_a_use_case",
    })
    assert r.status_code == 400


def test_cached_io_rejects_missing_audience() -> None:
    c = _client()
    r = c.post("/api/slides/cached-io", json={
        "audience": "",
        "use_case": "ph_hk_placement_fee",
    })
    assert r.status_code == 400


def test_cached_io_rejects_missing_use_case() -> None:
    c = _client()
    r = c.post("/api/slides/cached-io", json={
        "audience": "worker",
        "use_case": "",
    })
    assert r.status_code == 400


def test_cached_io_exposes_audience_and_use_case_keys() -> None:
    """The endpoint returns the canonical key lists so a UI that
    forgets to hard-code them stays in sync."""
    c = _client()
    r = c.post("/api/slides/cached-io", json={
        "audience": "worker",
        "use_case": "ph_hk_placement_fee",
    })
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("audience_keys"), list)
    assert isinstance(data.get("use_case_keys"), list)
    assert "worker" in data["audience_keys"]
    assert "ph_hk_placement_fee" in data["use_case_keys"]
