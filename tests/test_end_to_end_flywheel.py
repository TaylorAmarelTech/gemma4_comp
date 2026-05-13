"""End-to-end smoke: sentinel -> curator -> vetted -> kernel sync."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


HUB_APP = Path(__file__).resolve().parents[1] / "apps" / "duecare-ai.com"
if str(HUB_APP) not in sys.path:
    sys.path.insert(0, str(HUB_APP))


@pytest.fixture()
def isolated_hub(tmp_path, monkeypatch):
    monkeypatch.setenv("DUECARE_ADMIN_TOKEN", "test-token-flywheel")
    from app import sentinel as _sentinel
    monkeypatch.setattr(_sentinel, "DATA_DIR", tmp_path)
    monkeypatch.setattr(_sentinel, "STATE_PATH", tmp_path / "sentinel_state.json")
    monkeypatch.setattr(_sentinel, "DRAFTS_PATH", tmp_path / "sentinel_drafts.jsonl")
    monkeypatch.setattr(_sentinel, "SEEN_PATH", tmp_path / "sentinel_seen_urls.json")
    monkeypatch.setattr(_sentinel, "SUBMISSIONS_PATH",
                         tmp_path / "knowledge_submissions.jsonl")
    monkeypatch.setattr(_sentinel, "_searxng_search", lambda q, top_n=10: {
        "results": [{
            "title": "ILO C181 fee prohibition (2026 update)",
            "url": "https://ilo.org/c181-2026",
            "snippet": "Private employment agencies shall not charge "
                       "directly or indirectly any fees to workers.",
        }],
        "source": "searxng",
        "elapsed_ms": 12,
    })
    return tmp_path


def test_sentinel_to_curator_chain(isolated_hub):
    from app import sentinel as _sentinel

    report = _sentinel.run_query("new_ilo_conventions")
    assert report["ok"] is True
    assert report["n_drafts_queued"] == 1
    assert report["curator_submission_id"] is not None

    submissions_path = isolated_hub / "knowledge_submissions.jsonl"
    assert submissions_path.exists()
    submission_row = json.loads(submissions_path.read_text().splitlines()[0])
    assert submission_row["source"] == "sentinel:server-automated"
    assert submission_row["n_items"] == 1
    item = submission_row["accepted"][0]
    assert item["type"] == "rag_doc"
    assert item["source_url"] == "https://ilo.org/c181-2026"


def test_sentinel_emits_dedup(isolated_hub):
    from app import sentinel as _sentinel
    r1 = _sentinel.run_query("new_ilo_conventions")
    assert r1["n_novel"] == 1
    r2 = _sentinel.run_query("new_ilo_conventions")
    assert r2["n_novel"] == 0
    assert r2["n_drafts_queued"] == 0


def test_kernel_layer_composer_reads_synced_knowledge():
    """Final leg: kernel-side compose_layers reads runtime knowledge_extras_grep.
    Simulates the state AFTER curator accept + sync push.
    """
    from types import SimpleNamespace
    from duecare.chat.harnesses._layers import compose_layers

    def fake_grep_call(text, extra_rules=None):
        if "fee" in text.lower():
            return {"hits": [{
                "rule_id": "sentinel_new_ilo_conventions_fee_2026",
                "severity": "high",
                "match_text": "placement fee",
                "category": "fee_bondage",
            }]}
        return {"hits": []}

    app = SimpleNamespace(state=SimpleNamespace(
        grep_call=fake_grep_call,
        knowledge_extras_grep=[{
            "rule_id": "sentinel_new_ilo_conventions_fee_2026",
            "source": "knowledge:extra",
        }],
    ))
    out = compose_layers(app, "recruiter wants 30k PHP placement fee",
                          layers=("grep",))
    assert out["trace"]["grep"]["fired"] is True
    assert "sentinel_new_ilo_conventions_fee_2026" in out["trace"]["grep"]["rule_ids"]
