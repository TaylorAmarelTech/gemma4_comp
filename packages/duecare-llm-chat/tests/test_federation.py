"""Tests for the federation peer registry and its enforcement points."""
from __future__ import annotations

from fastapi.testclient import TestClient

from duecare.chat import federation
from duecare.chat.app import create_app


def test_builtin_peers_cover_legacy_allowlist() -> None:
    hosts = federation.allowed_hosts()
    assert {"duecare-ai.com", "www.duecare-ai.com", "gemma4-comp.onrender.com"} <= hosts


def test_peers_env_extends_registry(monkeypatch) -> None:
    monkeypatch.setenv(
        "DUECARE_PEERS",
        "ngo-manila=https://manila.example.org, https://nairobi.example.org/,"
        "bad=http://insecure.example.org,",
    )
    registry = federation.peers()
    by_name = {p["name"]: p for p in registry}
    assert by_name["ngo-manila"]["base_url"] == "https://manila.example.org"
    assert by_name["ngo-manila"]["role"] == "peer"
    assert by_name["nairobi.example.org"]["base_url"] == "https://nairobi.example.org"
    # http:// entries are dropped, never weakened to allowed.
    assert "bad" not in by_name
    assert "manila.example.org" in federation.allowed_hosts()


def test_is_peer_url_allowed_blocks_ssrf_shapes(monkeypatch) -> None:
    monkeypatch.delenv("DUECARE_PEERS", raising=False)
    bad = [
        "",
        "http://duecare-ai.com/api",                       # not https
        "file:///etc/passwd",
        "https://evil.example.com/api",                    # unregistered host
        "https://duecare-ai.com@evil.example.com/api",     # userinfo trick
        "https://169.254.169.254/latest/meta-data",        # metadata service
    ]
    for url in bad:
        ok, why = federation.is_peer_url_allowed(url)
        assert not ok, url
        assert why
    ok, _ = federation.is_peer_url_allowed("https://duecare-ai.com/api/hub/knowledge/download")
    assert ok


def test_network_peers_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("DUECARE_NODE_ID", "node-alpha")
    client = TestClient(create_app())
    r = client.get("/api/network/peers")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "duecare.network.v1"
    assert body["node_id"] == "node-alpha"
    assert any(p["base_url"] == "https://duecare-ai.com" for p in body["peers"])
    assert "sync_contract" in body


def test_sync_rejects_unregistered_target_url() -> None:
    client = TestClient(create_app())
    r = client.post(
        "/api/knowledge/sync",
        json={"target_url": "https://attacker.example.com/zip"},
    )
    assert r.status_code == 400
    assert "not a registered peer" in r.text


def test_sync_rejects_plain_http_target_url() -> None:
    client = TestClient(create_app())
    r = client.post(
        "/api/knowledge/sync",
        json={"target_url": "http://169.254.169.254/latest"},
    )
    assert r.status_code == 400
    assert "must be https" in r.text
