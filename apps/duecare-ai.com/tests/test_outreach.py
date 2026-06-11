"""Tests for the civil-society outreach loop (app/outreach.py + endpoints).

Covers: gap detection + prioritization, campaign drafting + recipient
targeting, observation intake -> context signal, and the deterministic
intent->weight/confirm logic (so the LLM-path boost is tested without an LLM).
"""
from __future__ import annotations

import pathlib
import tempfile
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app import outreach

AT = chr(64)  # guaranteed-ASCII '@' (avoid homoglyph traps in source)


@pytest.fixture()
def client():
    return TestClient(create_app(data_dir=pathlib.Path(tempfile.mkdtemp(prefix="outreach-test-"))))


@dataclass
class _FakeVerdict:
    verdict: str
    intent: str
    summary: str = ""
    extracted_facts: list[str] | None = None
    pii_findings: list[str] | None = None

    def __post_init__(self):
        self.extracted_facts = self.extracted_facts or []
        self.pii_findings = self.pii_findings or []


# ----------------------------- unit: gaps -----------------------------------

def test_detect_gaps_returns_seed_sorted_by_priority():
    d = pathlib.Path(tempfile.mkdtemp())
    gaps = outreach.detect_context_gaps(d)
    assert len(gaps) >= 8
    priorities = [g.priority for g in gaps]
    assert priorities == sorted(priorities, reverse=True)
    assert {g.id for g in gaps} >= {"fee_cap_ph_hk", "pattern_digital_fee_rails", "sector_fishing"}
    # every gap is a concrete, answerable ask
    assert all(g.ask and "?" in g.ask for g in gaps)


# ----------------------- unit: observation -> signal ------------------------

def test_ingest_observation_weights_and_confirm_boost():
    d = pathlib.Path(tempfile.mkdtemp())
    # a 'verification' reply with facts should confirm + carry weight
    v = _FakeVerdict("needs_curator_review", "verification",
                     extracted_facts=["PHP 45000 training fee", "deducted from salary"])
    sig = outreach.ingest_observation(d, "fee_cap_ph_hk", verdict=v,
                                      sender_email="a" + AT + "b.org", ts="2026-06-10T00-00-00Z")
    assert sig.gap_id == "fee_cap_ph_hk" and sig.intent == "verification"
    assert sig.weight > 1.0  # base 1.0 + fact bonus
    assert len(sig.sender_sha256) == 64 and AT not in sig.sender_sha256  # hashed, no raw email
    # a rejected reply carries zero weight but is still logged
    v2 = _FakeVerdict("reject", "off_topic")
    sig2 = outreach.ingest_observation(d, "fee_cap_ph_hk", verdict=v2,
                                       sender_email="x" + AT + "y.org", ts="2026-06-10T00-01-00Z")
    assert sig2.weight == 0.0
    # the gap's confirm_count reflects the one confirming reply
    gap = outreach.gap_by_id(d, "fee_cap_ph_hk")
    assert gap.confirm_count == 1
    assert gap.priority > gap.base_priority  # boosted


def test_prioritized_context_ranks_and_proposes_dimension():
    d = pathlib.Path(tempfile.mkdtemp())
    for _ in range(3):
        outreach.ingest_observation(
            d, "fee_cap_ph_hk",
            verdict=_FakeVerdict("needs_curator_review", "new_info", extracted_facts=["f"]),
            sender_email="a" + AT + "b.org", ts="2026-06-10T00-00-00Z")
    outreach.ingest_observation(
        d, "pattern_free_visa",
        verdict=_FakeVerdict("needs_curator_review", "verification"),
        sender_email="c" + AT + "d.org", ts="2026-06-10T00-00-00Z")
    pri = outreach.prioritized_context(d)
    assert pri[0]["gap_id"] == "fee_cap_ph_hk"  # 3 strong > 1
    assert pri[0]["n_observations"] == 3
    assert pri[0]["candidate_dimension"] == "fee_cap_ph_hk_currency"
    assert pri[0]["score"] > pri[1]["score"]


# ----------------------------- endpoint flow --------------------------------

def test_endpoint_loop(client):
    # collect a contact
    sub = client.post("/api/newsletter/subscribe", json={
        "email": "ngo" + AT + "example.org", "topics": ["PH-HK", "fee_cap"],
        "role": "caseworker", "consent_to_outreach": True})
    assert sub.status_code == 200, sub.text

    # gaps
    g = client.get("/api/outreach/gaps")
    assert g.status_code == 200
    body = g.json()
    assert body["count"] >= 8 and body["n_subscribers"] == 1
    assert body["smtp_configured"] is False  # no creds in test

    # campaign draft targets the matching subscriber, not sent (no SMTP)
    camp = client.post("/api/outreach/campaign", json={"gap_id": "fee_cap_ph_hk"})
    assert camp.status_code == 200
    c = camp.json()["campaign"]
    assert c["send_status"] == "drafted" and c["n_recipients"] >= 1
    assert c["subject"] and c["body"]

    # unknown gap -> 404
    assert client.post("/api/outreach/campaign", json={"gap_id": "nope"}).status_code == 404

    # observation intake -> signal recorded
    o = client.post("/api/outreach/observe", json={
        "gap_id": "fee_cap_ph_hk", "subject": "Re: fees",
        "body": "Still seeing relabelled placement fees on the PH-HK corridor.",
        "sender_email": "ngo" + AT + "example.org"})
    assert o.status_code == 200, o.text
    assert o.json()["signal"]["gap_id"] == "fee_cap_ph_hk"

    # priorities reflect the observation + a candidate dimension
    p = client.get("/api/outreach/priorities")
    assert p.status_code == 200
    pr = p.json()["priorities"]
    assert pr and pr[0]["gap_id"] == "fee_cap_ph_hk"
    assert pr[0]["candidate_dimension"] == "fee_cap_ph_hk_currency"
