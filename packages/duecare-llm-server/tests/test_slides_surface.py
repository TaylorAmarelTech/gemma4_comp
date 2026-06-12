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
- GET /api/slides/recording-pack returns selected examples, cached
  responses, and redacted evidence image paths for no-wait recording.
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
    assert 'href="/static/style.css"' in html
    assert 'href="/static/styles.css"' not in html
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


def test_live_demo_home_serves_six_lanes() -> None:
    c = _client()
    r = c.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Six use cases" in html
    assert "Five use cases" not in html
    lane_cursor = -1
    for marker in [
        "Platform safety",
        "NGO &amp; regulator",
        "Individual worker / mobile",
        "Researcher",
        "Anonymized knowledge sharing",
        "Developer / integration partner",
    ]:
        marker_index = html.find(marker)
        assert marker_index > lane_cursor, f"missing or out-of-order lane: {marker}"
        lane_cursor = marker_index
    assert '<a href="/knowledge"><span>05</span>' in html
    assert '<a href="/architecture"><span>06</span>' in html


def test_legacy_demo_copy_avoids_fragile_claims() -> None:
    c = _client()
    r = c.get("/demo")
    assert r.status_code == 200
    html = r.text
    lower = html.lower()
    assert "Why Gemma 4 is the right model engine." in html
    assert "substrate" not in lower
    assert "materially less harmful" not in lower
    assert "verdicts/min" not in lower
    assert "roughly zero per-call cost" not in lower


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
        "duecare.slides.demo.pack",  # localStorage key for selected examples
        "/static/evidence/",         # image-backed recording examples
    ]:
        assert marker in html, f"slides.html missing marker: {marker!r}"


def test_slides_deck_has_demo_chat_slide_anchor() -> None:
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    assert "demo-chat" in html, (
        "Slides deck must expose a demo-chat anchor for /slides#demo-chat")


def test_slides_deck_uses_recording_safe_ecosystem_story() -> None:
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    for marker in [
        "data-slide-id=\"case-analysis-overview\"",
        "data-slide-id=\"knowledge-sharing-demo\"",
        "data-slide-id=\"module-ecosystem\"",
        "Exploitation continues because the protective workflow is fragmented",
        "Six public setup lanes, one shared local safety stack",
    ]:
        assert marker in html
    assert "substrate" not in html.lower()
    lane_cursor = -1
    for marker in [
        "Platform safety",
        "NGO &amp; regulator",
        "Individual worker / mobile",
        "Researcher",
        "Anonymized knowledge sharing",
        "Developer / integration partner",
    ]:
        marker_index = html.find(marker)
        assert marker_index > lane_cursor, f"missing or out-of-order lane: {marker}"
        lane_cursor = marker_index
    assert "Full screen" not in html
    assert "arrows / space" not in html
    assert "Hiring 30 Filipina maids for Saudi Arabia" in html
    assert "+63 917 123 4567" in html
    assert "false_urgency_only_n_spots" in html
    assert "gemma-4-e4b-it" in html
    assert "287515 ms" in html
    assert "Local Gemma 4</span>" not in html
    assert "Evidence harness</span>" not in html
    assert 'class="slide dark"' not in html
    assert 'class="slide accent"' not in html
    assert "--camera-safe-right" not in html
    assert "what not to optimize" not in html
    assert "not to optimize" not in html
    for marker in [
        'data-demo-run="moderation"',
        'data-demo-run="case"',
        'data-demo-run="phone"',
        'data-demo-run="chat"',
        'data-demo-run="research"',
        'data-demo-run="sharing"',
        "Six public setup lanes, one shared local safety stack",
        "Gemma 4 is not another lane",
    ]:
        assert marker in html


def test_slides_deck_exposes_new_unique_and_knowledge_pack_slides() -> None:
    """The 2026-05-18 deck adds two new slides: a 4-tile 'what makes
    this unique' emphasis slide and a 'download the knowledge packs'
    take-it-home slide. Pin their anchors + the evidence-stack counts that
    appear on the unique tile."""
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    # Anchors
    assert "data-slide-id=\"unique\"" in html, (
        "deck must expose /slides#unique anchor for the 4-tile uniqueness slide")
    assert "data-slide-id=\"knowledge-packs\"" in html, (
        "deck must expose /slides#knowledge-packs anchor for the download slide")
    # Substrate counts on the unique slide
    assert "451" in html and "859" in html, (
        "unique slide must display the live GREP/RAG counts (451+ rules, "
        "859+ RAG entries)")
    # On-device APK tile
    assert "On-device APK" in html or "on-device APK" in html, (
        "unique slide must include the on-device APK tile")
    # Knowledge-pack download links resolve to /wb-static/samples/
    for sample in [
        "/wb-static/samples/knowledge_pack_rich_sample.zip",
        "/wb-static/samples/knowledge_files_sample.zip",
        "/wb-static/samples/knowledge_bundle_sample.zip",
        "/wb-static/samples/prompt_eval_training_seed_sample.zip",
        "/wb-static/samples/case_files_streamlined_demo.zip",
    ]:
        assert sample in html, (
            f"knowledge-packs slide must link {sample}")


def test_slides_deck_drops_placeholder_benchmark_numbers() -> None:
    """The deck should show the measured A-00 smoke matrix and should
    not regress to old placeholders or future-tense benchmark claims."""
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    for percentage in ["62.0%", "81.5%", "74.8%", "88.2%"]:
        assert percentage not in html, (
            f"placeholder benchmark percentage {percentage!r} reappeared "
            "in the deck; soften to qualitative capability framing.")
    for forbidden in [
        "We'll publish specific lift numbers",
        "will publish specific lift numbers",
        "Lift numbers published with the final A-00 run",
    ]:
        assert forbidden not in html
    for measured in ["29.5%", "35.6%", "41.2%", "2026-05-18"]:
        assert measured in html


def test_slides_deck_keeps_cached_replay_labels() -> None:
    """Every client-side demo runner should carry a 'cached, replays
    in ~Ns' label so reviewers see we are honest about pre-baking."""
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    assert "cached &middot; replays in" in html, (
        "deck must show the 'cached - replays in ~Ns' subtext on demo "
        "runners")


def test_slides_deck_uses_canonical_kernel_slugs() -> None:
    """After the 2026-05-18 rename, every Kaggle URL on the deck
    should use the new slugs (duecare-app / duecare-live-demo /
    duecare-fine-tuning-and-evaluation), not the old ones."""
    c = _client()
    r = c.get("/slides")
    assert r.status_code == 200
    html = r.text
    assert "duecare-app" in html
    assert "duecare-fine-tuning-and-evaluation" in html
    # Old slugs must NOT appear
    assert "duecare-exploration-workbench" not in html, (
        "old kernel slug should be gone from the live deck")
    assert "duecare-a-00-omni-experiment-workbench" not in html, (
        "old A-00 slug should be gone from the live deck")


def test_slides_cached_io_returns_correct_statute() -> None:
    """The 2026-05-18 statute fix replaced RA 11227 (officer-training
    law) with RA 8042 (Migrant Workers Act) for the PH placement-fee
    response. Pin the correction across every (audience, use_case)
    pair that touches PH placement law."""
    c = _client()
    for use_case in ("ph_hk_placement_fee", "debt_bondage", "fee_camouflage"):
        for audience in ("worker", "ngo", "regulator"):
            r = c.post("/api/slides/cached-io", json={
                "audience": audience,
                "use_case": use_case,
            })
            assert r.status_code == 200, r.text
            body = r.json()["response"]
            assert "RA 11227" not in body, (
                f"({audience}, {use_case}) response still cites RA 11227 "
                "(officer-training law). Migrant-workers statute is RA 8042.")


def test_slides_setup_serves_audience_and_use_case_selectors() -> None:
    c = _client()
    r = c.get("/slides/setup")
    assert r.status_code == 200
    html = r.text
    assert 'href="/static/style.css"' in html
    assert 'href="/static/styles.css"' not in html
    for key in ["worker", "ngo", "regulator",
                "researcher", "developer", "platform"]:
        assert f'value="{key}"' in html, \
            f"slides-setup.html missing audience option: {key}"
    for key in ["ph_sa_platform_moderation", "ph_hk_placement_fee", "passport_retention",
                "contract_substitution", "debt_bondage",
                "retaliation_risk", "fee_camouflage",
                "provider_choice"]:
        assert f'value="{key}"' in html, \
            f"slides-setup.html missing use_case option: {key}"
    assert "/api/slides/cached-io" in html
    assert "/api/slides/recording-pack" in html
    assert "duecare.slides.demo.chat" in html
    assert "duecare.slides.demo.pack" in html
    assert "Preload recording pack" in html
    assert 'option value="platform" selected' in html
    assert "Platform safety &mdash; moderation" in html
    assert "Developer / integration partner &mdash; API + harness integration" in html
    assert "captured Gemma E4B call took 287.5s" in html
    assert "replays without GPU latency" in html


def test_slide_surface_stylesheet_is_served() -> None:
    c = _client()
    r = c.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers.get("content-type", "")
    assert b"Source of truth" in r.content
    stale = c.get("/static/styles.css")
    assert stale.status_code == 404


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
    assert "RA 8042" in data["response"], (
        "PH placement-fee statute is RA 8042 (Migrant Workers Act), as "
        "amended by RA 10022 - not RA 11227 (officer training law). The "
        "cached PH-HK response must cite the correct migrant-workers act.")
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
    assert "ph_sa_platform_moderation" in data["use_case_keys"]


def test_recording_pack_preloads_selected_examples_and_images() -> None:
    c = _client()
    r = c.get("/api/slides/recording-pack")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["schema_version"] == "duecare.slides.recording_pack.v1"
    assert data["storage_keys"]["pack"] == "duecare.slides.demo.pack"
    assert data["storage_keys"]["chat"] == "duecare.slides.demo.chat"
    examples = data["examples"]
    assert len(examples) >= 8
    assert {e["lane"] for e in examples} >= {
        "Content moderation",
        "Case analysis",
        "Worker support",
        "Research",
        "Anonymized knowledge sharing",
        "Custom API implementations",
    }
    assert any(
        e.get("image") and e["image"]["src"].startswith("/static/evidence/")
        for e in examples
    )
    trace_examples = [
        e for e in examples if e["id"] == "platform_ph_sa_job_post_trace"
    ]
    assert trace_examples, "captured PH-Saudi moderation trace missing"
    trace_example = trace_examples[0]
    assert "+63 917 123 4567" in trace_example["prompt"]
    assert "false_urgency_only_n_spots" in " ".join(trace_example["artifacts"])
    assert trace_example["trace"]["model"] == "gemma-4-e4b-it"
    assert trace_example["trace"]["model_latency_ms"] == 287515
    assert data["moderation_trace"]["grade"]["score"] == "6.96/10"
    assert any(e["id"] == "custom_api_moderation_endpoint" for e in examples)
    assert data["slides_chat"]["prompt"]
    assert data["slides_chat"]["response"]
    assert "PHP 50,000" in data["slides_chat"]["prompt"]
