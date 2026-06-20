"""End-to-end: an LLM knowledge-proposal DRAFT lands in the hub curator review queue.

Proves the scripts/curator_submit.py bridge produces envelopes the hub's
POST /api/submit/knowledge actually accepts + stages status="proposed" (Stage 04 curator
queue), without reaching the vetted layer. The conftest here puts APP_ROOT on sys.path.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cs = _load("curator_submit", _ROOT / "scripts" / "curator_submit.py")

_PROPOSALS = [
    {"observation": "Some corridors charge an illegal placement fee disguised as a training cost.",
     "claim_to_verify": "the lawful fee ceiling for that corridor",
     "source_type_to_check": "labour-ministry circular"},
    {"observation": "Employers sometimes retain a worker's passport for so-called safekeeping.",
     "claim_to_verify": "whether local law forbids document retention",
     "source_type_to_check": "national labour code / ILO C181"},
]
AT = "2026-06-20T00:00:00+00:00"


@pytest.fixture()
def client():
    return TestClient(create_app(data_dir=pathlib.Path(tempfile.mkdtemp(prefix="curator-test-"))))


def test_generated_proposals_land_in_the_curator_queue_as_proposed(client):
    sub = cs.build_submission(_PROPOSALS, model="glm-5.2", created_at=AT, submission_id="e2e-1")
    assert cs.validate_local(sub) == []                 # wrapper-valid before we send

    r = client.post(cs.SUBMIT_PATH, json=sub)
    assert r.status_code == 200, r.text
    receipt = r.json()

    assert receipt["status"] == "proposed"              # NOT vetted -- pending human review
    assert receipt["n_accepted"] == 2                   # both passed the schema + PII gates
    assert receipt.get("n_rejected_schema", 0) == 0
    assert receipt.get("n_rejected_pii", 0) == 0
