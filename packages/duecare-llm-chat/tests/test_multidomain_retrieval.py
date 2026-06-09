"""Tests for the opt-in multidomain BM25 retrieval (separate index)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from duecare.chat import harness as h
from duecare.chat.app import create_app
from duecare.chat.harness._multidomain_corpus import MULTIDOMAIN_CORPUS


def test_multidomain_rag_call_returns_vertical_docs() -> None:
    out = h.multidomain_rag_call("elder care nursing home medication neglect", top_k=5)
    assert out["n_corpus"] == len(MULTIDOMAIN_CORPUS)
    assert out["docs"], "expected hits for an in-vertical query"
    for doc in out["docs"]:
        assert doc["corpus"] == "multidomain"
        assert doc["domain"] == str(doc["id"]).split("_", 1)[0]
        assert doc["score"] > 0


def test_multidomain_index_is_separate_from_trafficking_index() -> None:
    md_ids = {d[0] for d in MULTIDOMAIN_CORPUS}
    # The trafficking retrieval path must never surface multidomain ids.
    trafficking = h._rag_call("recruitment placement fee deduction Hong Kong", top_k=8)
    assert not (md_ids & {d["id"] for d in trafficking["docs"]})
    # And the parallel index sizes match their own corpora, not each other.
    stats = h._multidomain_stats()
    assert stats["n"] == len(MULTIDOMAIN_CORPUS)
    assert h._N == len(h.RAG_CORPUS)
    assert stats["n"] != h._N


def test_multidomain_rag_endpoint() -> None:
    client = TestClient(create_app())
    r = client.get("/api/multidomain/rag", params={"q": "procurement bid rigging public contract", "top_k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["n_corpus"] == len(MULTIDOMAIN_CORPUS)
    assert len(body["docs"]) <= 3
    for doc in body["docs"]:
        assert doc["corpus"] == "multidomain"


def test_multidomain_rag_endpoint_clamps_top_k_and_handles_empty_query() -> None:
    client = TestClient(create_app())
    r = client.get("/api/multidomain/rag", params={"q": "", "top_k": 999})
    assert r.status_code == 200
    assert r.json()["docs"] == []
