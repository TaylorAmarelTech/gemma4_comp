"""Tests for scripts/curator_submit.py -- the proposal -> curator-queue bridge.

Offline: the HTTP POST is injected as a fake, so no hub / no network is needed. Covers the
proposal->envelope conversion (a VALID, unverified-marked KnowledgeObject), submission shape,
local validation, and that submit targets the right endpoint with the right body.
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


cs = _load("curator_submit", _ROOT / "scripts" / "curator_submit.py")

_PROPOSAL = {
    "observation": "Recruiters in some corridors charge an illegal placement fee disguised as training.",
    "claim_to_verify": "the specific corridor and the lawful fee ceiling",
    "source_type_to_check": "labour-ministry circular / ILO fair-recruitment guidance",
    "confidence": "unverified",
    "_needs_source_verification": True,
}
AT = "2026-06-20T00:00:00+00:00"


def test_proposal_becomes_a_valid_unverified_envelope():
    env = cs.proposal_to_envelope(_PROPOSAL, model="glm-5.2", created_at=AT)
    # valid against the envelope wrapper contract
    ok, why = cs.validate_envelope(env, known_types={cs.PROPOSAL_TYPE})
    assert ok, why
    assert env["knowledge_object_type"] == "context_snippet"
    assert env["content"]["text"] == _PROPOSAL["observation"]
    # the real-not-faked markers ride along so a curator never mistakes it for a vetted fact
    assert env["content"]["confidence"] == "unverified"
    assert env["content"]["needs_source_verification"] is True
    assert "needs-source-verification" in env["tags"]
    assert env["extensions"]["review_status"] == "proposed"
    # provenance integrity hash is stamped (64 hex chars)
    sha = env["provenance"]["content_sha256"]
    assert isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)


def test_envelope_id_is_kebab_and_deterministic():
    a = cs.proposal_to_envelope(_PROPOSAL, model="m", created_at=AT)["id"]
    b = cs.proposal_to_envelope(_PROPOSAL, model="m", created_at=AT)["id"]
    assert a == b                                   # same observation -> same id (idempotent)
    assert a.startswith("llm-proposal-")
    import re
    assert re.match(r"^[a-z0-9][a-z0-9\-_]*$", a)   # the taxonomy id pattern


def test_build_submission_filters_textless_items():
    items = [_PROPOSAL, {"claim_to_verify": "no observation here"}, {"observation": "   "}]
    sub = cs.build_submission(items, model="glm-5.2", created_at=AT, submission_id="sub-1")
    assert sub["submission_id"] == "sub-1" and sub["ts"] == AT
    assert len(sub["items"]) == 1                   # only the one with a real observation
    assert cs.validate_local(sub) == []             # and it is wrapper-valid


def test_validate_local_flags_a_broken_envelope():
    bad = {"submission_id": "x", "ts": AT, "items": [{"schema_version": "1.0",
           "knowledge_object_type": "context_snippet", "id": "BadID", "content": {}}]}
    errs = cs.validate_local(bad)
    assert errs and "item[0]" in errs[0]            # uppercase id is not kebab -> rejected


def test_submit_to_curator_posts_to_the_right_endpoint():
    seen = {}

    def fake_poster(url, payload):
        seen["url"] = url
        seen["payload"] = payload
        return {"ok": True, "status": "proposed", "n_accepted": len(payload["items"])}

    sub = cs.build_submission([_PROPOSAL], model="glm-5.2", created_at=AT, submission_id="sub-9")
    receipt = cs.submit_to_curator(sub, hub_url="https://hub.example/", poster=fake_poster)
    assert seen["url"] == "https://hub.example/api/submit/knowledge"   # trailing slash handled
    assert seen["payload"]["items"][0]["knowledge_object_type"] == "context_snippet"
    assert receipt["status"] == "proposed" and receipt["n_accepted"] == 1
