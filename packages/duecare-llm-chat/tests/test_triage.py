"""Regression coverage for the triage harness (batch screening on one loaded Gemma).

Pins:
  - the harness contract (name / applied_layers / spec / PRIMARY membership)
  - routing: GREP high-severity flags without model time, loaded-Gemma
    flag/clear/low-confidence verdicts, soft-signal review routing
  - honest degradation: grep-only mode can NEVER produce status='cleared',
    malformed model replies can never clear an item
  - one model: the screening model is the loaded in-process Gemma (no endpoint,
    no second model, no model switch); the deeper pass runs only on escalated items
  - privacy: raw item text never appears in the response payload
  - the /api/triage/* endpoints (validation, status, model resolution)
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from duecare.chat.harnesses.triage.handler import (
    _parse_verdict,
    resolve_screen_model,
    screen_items,
)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

def _grep_fee_high(text: str) -> dict:
    """Fake GREP layer: high-severity hit on placement-fee language."""
    if "placement fee" in text.lower():
        return {"hits": [{"rule_id": "fee_0001", "severity": "high",
                          "match_text": "placement fee"}]}
    return {"hits": []}


def _grep_visa_soft(text: str) -> dict:
    """Fake GREP layer: medium-severity (soft) hit on 'free visa'."""
    if "free visa" in text.lower():
        return {"hits": [{"rule_id": "visa_0002", "severity": "medium"}]}
    return {"hits": []}


def _model_fixed(verdict_json: str):
    def call(prompt: str) -> str:
        return verdict_json
    return call


FEE_AD = "Great job in Dubai! Just pay the placement fee of 120,000 pesos."
VISA_AD = "Totally free visa, no costs, leave tomorrow!"
BENIGN_AD = "Hiring a barista for our Quezon City cafe, PHP 610/day, SSS + PhilHealth."
SUBTLE_AD = "No salary until your contract ends, accommodation provided on site."


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------

def test_harness_contract():
    from duecare.chat.harnesses import triage
    assert triage.name == "triage"
    assert triage.applied_layers == ("grep",)
    assert "grep_rule" in triage.consumes
    assert "audit_template" in triage.emits
    assert callable(triage.register_routes)
    assert triage.spec.tier == "primary"
    # the default model target is the loaded in-process Gemma -- one model, no endpoint
    default = [t for t in triage.spec.model_targets if t.default]
    assert default and default[0].transport == "gemma4_runtime"
    # no openai_compatible / external endpoint target remains
    assert not [t for t in triage.spec.model_targets if t.transport == "openai_compatible"]


def test_harness_registered_as_primary():
    from duecare.chat.harnesses import PRIMARY_HARNESSES, triage
    assert triage in PRIMARY_HARNESSES


# ---------------------------------------------------------------------------
# routing (pure function, fake backends)
# ---------------------------------------------------------------------------

def test_grep_high_severity_flags_without_model_time():
    out = screen_items(
        [{"id": "a", "text": FEE_AD}, {"id": "b", "text": BENIGN_AD}],
        grep_call=_grep_fee_high,
        model_call=None,
    )
    flagged, benign = out["items"]
    assert flagged["status"] == "flagged"
    assert flagged["flagged_by"] == "grep"
    assert flagged["grep"]["max_severity"] == "high"
    assert "skipped" in flagged["screen"]
    assert flagged["escalate"] is True
    assert benign["status"] == "passed_grep_only"
    assert out["summary"]["n_flagged"] == 1
    assert out["summary"]["n_passed_grep_only"] == 1


def test_grep_rule_id_accepts_rule_key():
    """The real default_harness grep_call returns hits keyed by 'rule' (not
    'rule_id'/'id'). screen_items must surface those rule ids, or the live
    triage page shows fired rules with blank ids."""
    def grep_rule_keyed(text: str) -> dict:
        return {"hits": [{"rule": "fee_camouflage_training", "severity": "high",
                          "match_excerpt": "training fee"}]}

    out = screen_items([{"text": FEE_AD}], grep_call=grep_rule_keyed, model_call=None)
    assert out["items"][0]["grep"]["rule_ids"] == ["fee_camouflage_training"]


def test_grep_only_mode_never_says_cleared():
    out = screen_items(
        [{"text": BENIGN_AD}, {"text": VISA_AD}],
        grep_call=_grep_visa_soft,
        model_call=None,
    )
    statuses = {row["status"] for row in out["items"]}
    assert "cleared" not in statuses
    # soft grep signal without a model goes to review, not silently passed
    assert out["items"][1]["status"] == "review"
    assert out["items"][1]["flagged_by"] == "grep_soft_signal"


def test_model_flags_item_grep_missed():
    out = screen_items(
        [{"text": SUBTLE_AD}],
        grep_call=_grep_fee_high,  # no hit on this text
        model_call=_model_fixed('{"verdict": "flag", "confidence": 0.9, '
                                '"category": "wage_withholding", "reason": "pay withheld"}'),
        model_label="loaded Gemma",
    )
    row = out["items"][0]
    assert row["status"] == "flagged"
    assert row["flagged_by"] == "model"
    assert row["screen"]["category"] == "wage_withholding"
    assert row["screen"]["latency_ms"] >= 0
    assert out["summary"]["model"]["n_calls"] == 1


def test_model_clear_high_confidence_clears():
    out = screen_items(
        [{"text": BENIGN_AD}],
        grep_call=_grep_fee_high,
        model_call=_model_fixed('{"verdict": "clear", "confidence": 0.95}'),
    )
    assert out["items"][0]["status"] == "cleared"
    assert out["items"][0]["escalate"] is False


def test_model_clear_low_confidence_goes_review():
    out = screen_items(
        [{"text": BENIGN_AD}],
        grep_call=_grep_fee_high,
        model_call=_model_fixed('{"verdict": "clear", "confidence": 0.3}'),
    )
    row = out["items"][0]
    assert row["status"] == "review"
    assert row["flagged_by"] == "low_confidence"
    assert row["escalate"] is True


def test_grep_soft_signal_overrides_model_clear():
    """A medium-severity GREP hit keeps the item in review even when the
    model confidently clears it — deterministic evidence wins."""
    out = screen_items(
        [{"text": VISA_AD}],
        grep_call=_grep_visa_soft,
        model_call=_model_fixed('{"verdict": "clear", "confidence": 0.99}'),
    )
    row = out["items"][0]
    assert row["status"] == "review"
    assert row["flagged_by"] == "grep_soft_signal"


def test_malformed_model_reply_can_never_clear():
    out = screen_items(
        [{"text": BENIGN_AD}],
        model_call=_model_fixed("Sure! This looks fine to me."),
    )
    row = out["items"][0]
    assert row["status"] == "review"
    assert "parse_error" in row["screen"]


def test_model_backend_exception_goes_review():
    def boom(prompt: str) -> str:
        raise ConnectionError("model crashed")
    out = screen_items([{"text": BENIGN_AD}], model_call=boom)
    row = out["items"][0]
    assert row["status"] == "review"
    assert "ConnectionError" in row["screen"]["error"]


def test_deep_runs_only_on_escalated_items():
    deep_calls: list[str] = []

    def deep(text: str) -> str:
        deep_calls.append(text)
        return "Indicators: debt bondage. Action: block."

    out = screen_items(
        [{"text": FEE_AD}, {"text": BENIGN_AD}],
        grep_call=_grep_fee_high,
        model_call=_model_fixed('{"verdict": "clear", "confidence": 0.9}'),
        deep_call=deep,
        run_deep=True,
    )
    assert len(deep_calls) == 1 and deep_calls[0] == FEE_AD
    assert out["items"][0]["deep"]["analysis"].startswith("Indicators")
    assert out["items"][1]["deep"] is None


def test_no_raw_item_text_in_response():
    out = screen_items(
        [{"text": FEE_AD}],
        grep_call=_grep_fee_high,
    )
    payload = json.dumps(out)
    assert "120,000" not in payload
    assert out["items"][0]["text_sha256"]


# ---------------------------------------------------------------------------
# verdict parsing
# ---------------------------------------------------------------------------

def test_parse_verdict_strips_fences_and_clamps():
    parsed = _parse_verdict(
        '```json\n{"verdict": "FLAG", "confidence": 7, "category": "fees"}\n```')
    assert parsed["verdict"] == "flag"
    assert parsed["confidence"] == 1.0  # clamped into [0, 1]


def test_parse_verdict_unknown_verdict_routes_review():
    parsed = _parse_verdict('{"verdict": "maybe", "confidence": 0.8}')
    assert parsed["verdict"] == "review"
    assert "unknown verdict" in parsed["parse_error"]


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from duecare.chat.app import create_app
    app = create_app()
    return TestClient(app)


def test_screen_endpoint_uses_loaded_gemma(client):
    """Default: the one loaded Gemma screens every item -- no flag, no model switch."""
    app = client.app
    saved = getattr(app.state, "gemma_call", None)

    def fake_gemma(payload, **kwargs):
        return '{"verdict": "flag", "confidence": 0.88, "category": "debt_bondage", "reason": "fee + debt"}'

    app.state.grep_call = None
    app.state.gemma_call = fake_gemma
    try:
        r = client.post("/api/triage/screen", json={"items": [SUBTLE_AD]})
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["model"]["source"] == "gemma4_runtime"  # the loaded model, in-process
        assert body["summary"]["model"]["n_calls"] == 1
        assert body["items"][0]["status"] == "flagged"
        assert body["items"][0]["flagged_by"] == "model"
    finally:
        app.state.gemma_call = saved


def test_screen_endpoint_grep_only_when_no_model(client):
    app = client.app
    saved = getattr(app.state, "gemma_call", None)
    app.state.grep_call = _grep_fee_high
    app.state.gemma_call = None
    try:
        # no model loaded -> honest 'not_configured', GREP still routes
        r = client.post("/api/triage/screen", json={"items": [
            {"id": "x1", "text": FEE_AD}, {"id": "x2", "text": BENIGN_AD}]})
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["model"]["source"] == "not_configured"
        assert body["summary"]["model"]["n_calls"] == 0
        assert body["items"][0]["status"] == "flagged"          # GREP high-severity
        assert body["items"][1]["status"] == "passed_grep_only"
        assert FEE_AD not in r.text  # raw text never echoed
    finally:
        app.state.gemma_call = saved


def test_screen_endpoint_use_model_false_forces_grep_only(client):
    """use_model:false skips the model even when one is loaded (GREP-only mode)."""
    app = client.app
    saved = getattr(app.state, "gemma_call", None)
    app.state.grep_call = _grep_fee_high
    app.state.gemma_call = lambda payload, **kw: '{"verdict": "clear", "confidence": 0.9}'
    try:
        r = client.post("/api/triage/screen", json={
            "items": [{"text": BENIGN_AD}], "use_model": False})
        body = r.json()
        assert body["summary"]["model"]["source"] == "off"
        assert body["summary"]["model"]["n_calls"] == 0
        assert body["items"][0]["status"] == "passed_grep_only"
    finally:
        app.state.gemma_call = saved


def test_screen_endpoint_validation(client):
    assert client.post("/api/triage/screen", json={"items": []}).status_code == 400
    assert client.post("/api/triage/screen", json={}).status_code == 400
    assert client.post("/api/triage/screen",
                       json={"items": [{"text": ""}]}).status_code == 400
    assert client.post("/api/triage/screen",
                       json={"items": [{"text": "x" * 20_001}]}).status_code == 400
    too_many = ["ad"] * 201
    assert client.post("/api/triage/screen",
                       json={"items": too_many}).status_code == 400


def test_status_endpoint(client):
    r = client.get("/api/triage/status")
    assert r.status_code == 200
    body = r.json()
    assert body["harness"] == "triage"
    assert "model" in body and "available" in body["model"] and "source" in body["model"]
    assert body["statuses"] == ["flagged", "review", "cleared", "passed_grep_only"]
    assert "never produces user-facing answers" in body["policy"]


def test_resolve_screen_model_is_the_loaded_gemma():
    class _App:
        class state:  # noqa: N801 - mimic app.state
            gemma_call = staticmethod(lambda payload, **kw: '{"verdict": "clear", "confidence": 0.9}')

    call, label, source = resolve_screen_model(_App())
    assert source == "gemma4_runtime" and callable(call)
    assert "loaded" in label.lower()

    class _Empty:
        class state:  # noqa: N801
            gemma_call = None

    assert resolve_screen_model(_Empty()) == (None, "", "not_configured")
