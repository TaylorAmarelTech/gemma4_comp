"""Peer registry for node-to-node anonymized knowledge sharing.

A DueCare deployment is one node in a hub-and-spoke network: kernels and
NGO instances pull vetted knowledge packs from one or more hubs and push
anonymized envelopes back for curation. This module is the single source
of truth for which remote peers a node may talk to -- the same registry
backs the sync target allowlist, the submit allowlist, and the
``/api/network/peers`` discovery endpoint, so adding a peer in one place
(``DUECARE_PEERS``) extends every flow at once.

Security note: kernels run behind an unauthenticated public tunnel, so
any outbound URL a visitor can influence MUST be checked against this
registry (https-only, no userinfo, host must be a registered peer) or the
kernel becomes an SSRF proxy.

Domain-agnostic by design: peers serve KnowledgeObject envelopes
(`knowledge_taxonomy`); nothing here assumes the anti-trafficking domain.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from .knowledge_taxonomy import node_id

# Built-in hub peers (the public DueCare hub and its aliases). These match
# the historical anonymization-handler allowlist so single-node
# deployments behave exactly as before.
_BUILTIN_PEERS: tuple[dict[str, str], ...] = (
    {"name": "duecare-ai.com hub", "base_url": "https://duecare-ai.com", "role": "hub"},
    {"name": "duecare-ai.com hub (www)", "base_url": "https://www.duecare-ai.com", "role": "hub"},
    {"name": "render service alias", "base_url": "https://gemma4-comp.onrender.com", "role": "hub"},
)


def peers() -> list[dict[str, str]]:
    """Built-in hub peers plus ``DUECARE_PEERS`` additions.

    ``DUECARE_PEERS`` is comma-separated ``name=https://host`` entries
    (bare https URLs are accepted too; the hostname becomes the name).
    Non-https entries are ignored rather than weakening the transport
    requirement.
    """
    out = [dict(p) for p in _BUILTIN_PEERS]
    raw = os.environ.get("DUECARE_PEERS", "").strip()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, _, url = chunk.rpartition("=")
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        out.append({
            "name": (name.strip() or parsed.hostname),
            "base_url": url.rstrip("/"),
            "role": "peer",
        })
    return out


def allowed_hosts() -> frozenset[str]:
    """Lowercased hostnames of every registered peer."""
    hosts: set[str] = set()
    for peer in peers():
        host = urlparse(peer["base_url"]).hostname
        if host:
            hosts.add(host.lower())
    return frozenset(hosts)


def is_peer_url_allowed(target_url: str) -> tuple[bool, str]:
    """Validate an outbound URL against the peer registry.

    Blocks non-https schemes (file://, http://, javascript:, ...),
    userinfo tricks (https://evil@allowed.com), and any host that is not
    a registered peer. Returns ``(ok, reason)``.
    """
    if not target_url:
        return False, "empty target_url"
    try:
        parsed = urlparse(target_url)
    except Exception as e:  # noqa: BLE001 -- urlparse failure means reject
        return False, f"parse error: {e}"
    if parsed.scheme != "https":
        return False, f"scheme {parsed.scheme!r} not allowed (must be https)"
    if parsed.username or parsed.password:
        return False, "userinfo not allowed in target_url"
    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts():
        return False, (
            f"host {host!r} is not a registered peer; set DUECARE_PEERS="
            '"name=https://host" before kernel start to add one'
        )
    return True, ""


def network_manifest() -> dict[str, Any]:
    """Discovery payload for ``GET /api/network/peers``."""
    return {
        "schema_version": "duecare.network.v1",
        "node_id": node_id(),
        "peers": peers(),
        "how_to_add_a_peer": (
            'Set DUECARE_PEERS="name=https://host,other=https://host2" in the '
            "environment before kernel start. Only https peers are accepted; "
            "the registry doubles as the outbound allowlist for sync and submit."
        ),
        "sync_contract": {
            "pull": "GET <peer>/api/hub/knowledge/download?vetted=true -> ZIP of <type>/<id>.json envelopes",
            "delta": "GET <peer>/api/hub/sync?since=<ISO-8601> -> changed vetted packs",
            "push": "POST <peer>/api/submit/knowledge -> schema + PII gate + dedup, then human curation",
            "integrity": "every envelope carries provenance.content_sha256 (sha256 over sorted-key compact content JSON)",
            "schema": "GET <peer>/static/envelope_schema.json (same artifact every node validates)",
        },
    }
