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
            verdict=_FakeVerdict("needs_curator_review", "new_information", extracted_facts=["f"]),
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
    assert body["smtp_configured"] is False
    assert body["delivery_mode"] == "draft_only"
    assert body["can_send"] is False
    assert body["stores_recipient_addresses"] is False

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


def test_public_page_discloses_non_contactable_hash_boundary(client):
    response = client.get("/outreach")

    assert response.status_code == 200
    assert "It does not create a contactable mailing-list entry" in response.text
    assert "the hub cannot recover your address or email you" in response.text
    assert "separate consented address book" in response.text


# ------------------- vocabulary + honesty regression guards ------------------

def test_intent_weights_align_with_automation_vocabulary():
    """outreach.py deliberately does not import automation, so this test is
    the coupling: every weight key must be a real automation.Intent token
    (the 'new_info' era silently zeroed 4 of 7 real intents), and every
    informative intent must outweigh the 'unclear' fallback."""
    import typing

    from app import automation

    intents = set(typing.get_args(automation.Intent))
    assert set(outreach._INTENT_WEIGHTS) <= intents, (
        "outreach._INTENT_WEIGHTS contains tokens automation never emits"
    )
    assert outreach._CONFIRMING_INTENTS <= intents
    for intent in intents - {"off_topic", "unclear"}:
        assert outreach._INTENT_WEIGHTS.get(intent, 0.0) > 0.3, (
            f"informative intent {intent!r} falls to the 'unclear' fallback"
        )


def test_real_inbound_verdict_confirms_and_weights():
    """A REAL automation.InboundVerdict (not the test fake) must confirm a
    gap and carry the designed weight, so the vocabulary cannot drift."""
    from app import automation

    d = pathlib.Path(tempfile.mkdtemp())
    v = automation.InboundVerdict(
        verdict="accept", intent="new_information", summary="s",
        extracted_facts=["fact one", "fact two"], pii_findings=[])
    sig = outreach.ingest_observation(
        d, "statute_new_regulations", verdict=v,
        sender_email="l" + AT + "aw.org", ts="2026-06-11T00-00-00Z")
    assert sig.weight > 1.0  # base 1.2 + fact bonus, not the 0.3 fallback
    gap = outreach.gap_by_id(d, "statute_new_regulations")
    assert gap.confirm_count == 1


def test_reject_with_facts_carries_zero_weight_and_never_surfaces():
    d = pathlib.Path(tempfile.mkdtemp())
    bad = _FakeVerdict("reject", "verification",
                       extracted_facts=["a", "b", "c", "d"])
    sig = outreach.ingest_observation(
        d, "fee_cap_ph_hk", verdict=bad,
        sender_email="x" + AT + "y.org", ts="2026-06-11T00-00-00Z")
    assert sig.weight == 0.0  # the fact bonus must not resurrect a reject
    ok = _FakeVerdict("needs_curator_review", "verification",
                      extracted_facts=["legit fact"])
    outreach.ingest_observation(
        d, "fee_cap_ph_hk", verdict=ok,
        sender_email="c" + AT + "d.org", ts="2026-06-11T00-01-00Z")
    pri = outreach.prioritized_context(d)
    row = next(p for p in pri if p["gap_id"] == "fee_cap_ph_hk")
    assert row["n_observations"] == 1  # the reject contributes nothing
    assert row["sample_facts"] == ["legit fact"]  # rejected facts never go public


def test_match_recipients_handles_the_forms_own_placeholder_examples():
    """The /outreach opt-in form suggests 'topics, e.g. PH-HK, fee_cap,
    fishing' — every suggested example must actually match its gap."""
    d = pathlib.Path(tempfile.mkdtemp())
    gaps = {g.id: g for g in outreach.detect_context_gaps(d)}

    def matches(topics, gap_id):
        subs = [{"topics": topics, "role": "", "consent_to_outreach": True}]
        return len(outreach._match_recipients(gaps[gap_id], subs)) == 1

    assert matches(["PH-HK"], "fee_cap_ph_hk")
    assert matches(["NP-QA"], "fee_cap_np_qa")
    assert matches(["fishing"], "sector_fishing")
    assert matches(["fee_cap"], "fee_cap_ph_hk")
    # discrimination: an unrelated topic must NOT match (the blank-profile
    # fallback would hide over-matching, so this guards the matcher itself)
    assert not matches(["parking"], "fee_cap_ph_hk")


def test_campaign_send_status_always_drafted_even_with_smtp_env(monkeypatch):
    """send_status='queued' was a real-not-faked violation: no send
    implementation exists and the hub stores no raw addresses. The status
    must stay 'drafted' regardless of SMTP env vars."""
    monkeypatch.setenv("DUECARE_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("DUECARE_SMTP_FROM", "hub" + AT + "example.org")
    d = pathlib.Path(tempfile.mkdtemp())
    gap = outreach.gap_by_id(d, "fee_cap_ph_hk")

    class _Draft:
        subject = "s"
        body = "b"
        model = "template-fallback"

    campaign = outreach.draft_campaign(d, gap, [], compose=lambda *a: _Draft())
    assert campaign.send_status == "drafted"


# ------------------ LLM outreach-drafts -> PROPOSED context gaps -------------

_DRAFTS = [
    {"topic": "Student-visa labour in JP",
     "question": "Are student-visa holders in Japan being pushed into excessive overtime by recruiters?",
     "target_role": "migrant-worker advocate"},
    {"topic": "Crypto fee rails in BD-MY",
     "question": "Are Bangladesh to Malaysia recruiters collecting fees via USDT or bKash?",
     "target_role": "hotline volunteer"},
]


def test_proposed_gap_spec_from_draft_marks_proposed():
    spec = outreach.proposed_gap_spec_from_draft(_DRAFTS[0], model="glm-5.2")
    assert spec["proposed"] is True and spec["kind"] == "proposed"
    assert spec["id"].startswith("proposed_")
    assert spec["ask"] == _DRAFTS[0]["question"]
    assert spec["audience"] == "migrant-worker advocate"
    assert spec["base_priority"] < 0.5             # never displaces the curated seeds


def test_ingest_proposed_gaps_persists_dedups_and_surfaces():
    d = pathlib.Path(tempfile.mkdtemp())
    added = outreach.ingest_proposed_gaps(d, _DRAFTS, model="glm-5.2", ts="2026-06-20T00-00-00Z")
    assert len(added) == 2
    # re-ingesting the same drafts adds nothing (dedup by id)
    assert outreach.ingest_proposed_gaps(d, _DRAFTS, model="glm-5.2", ts="2026-06-20T00-01-00Z") == []
    gaps = outreach.detect_context_gaps(d)
    by_id = {g.id: g for g in gaps}
    assert len(gaps) >= 10                          # 8 seeds + 2 proposed
    assert by_id[added[0]["id"]].proposed is True
    assert gaps[0].proposed is False                # a curated seed still ranks first
    # textless drafts are skipped
    assert outreach.ingest_proposed_gaps(d, [{"topic": "x"}, {"question": "  "}],
                                         model="m", ts="2026-06-20T00-02-00Z") == []


def test_endpoint_propose_gaps_then_draftable(client):
    r = client.post("/api/outreach/propose-gaps", json={"drafts": _DRAFTS, "model": "glm-5.2"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["n_proposed"] == 2
    pid = body["proposed_gaps"][0]["id"]

    # it now appears in the gaps list, flagged proposed
    g = client.get("/api/outreach/gaps").json()
    match = [x for x in g["gaps"] if x["id"] == pid]
    assert match and match[0]["proposed"] is True

    # and a curator can draft a (still draft-only) campaign for it
    camp = client.post("/api/outreach/campaign", json={"gap_id": pid})
    assert camp.status_code == 200
    assert camp.json()["campaign"]["send_status"] == "drafted"
