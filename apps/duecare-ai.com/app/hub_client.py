"""Reference client for the public DueCare hub.

Lives on the server as a documented protocol reference. The chat-package
wheel (and any third-party deployer) can copy this module wholesale,
swap the default URL, and have a working client without taking the hub
as a Python dependency. Stdlib only.

Defaults
========
- ``DUECARE_HUB_URL`` env var, falling back to ``DEFAULT_PUBLIC_HUB``.
- ``DEFAULT_PUBLIC_HUB`` is the public coordination service. To run a
  private hub for your own network, point ``DUECARE_HUB_URL`` at your
  Render / VPC / on-prem deployment.

Network choice
==============
A worker-wheel deployer has three options:

1. **Use the public hub.** Default. Pulls vetted packs from the public
   curator network. Submissions (if you opt in) flow into the public
   review queue.
2. **Run your own private hub.** Set ``DUECARE_HUB_URL`` to your own
   deployment. You curate everything; nothing crosses to anyone else's
   network. The Docker image ships under
   ``apps/duecare-ai.com/Dockerfile`` and is MIT-licensed.
3. **Federate.** Pull packs from one hub, submit to another. Each call
   takes an explicit ``hub_url`` argument that overrides the env var.

Failure mode
============
Every call returns ``None`` on a transport error and logs a warning. The
hub is a coordination layer; the local runtime never blocks on it being
up. Pin a pack version locally and the wheel keeps working offline.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

LOGGER = logging.getLogger(__name__)

DEFAULT_PUBLIC_HUB = "https://duecare-ai.com"
"""Public coordination hub for DueCare, live at https://duecare-ai.com
(the Render service). The legacy https://gemma4-comp.onrender.com hostname
still resolves to the same service for back-compat. Override with the
``DUECARE_HUB_URL`` env var or the per-call ``hub_url`` argument."""


def default_hub_url() -> str:
    """Resolve the active hub URL: env var, else the public default."""
    return os.environ.get("DUECARE_HUB_URL", DEFAULT_PUBLIC_HUB).rstrip("/")


def _request(
    method: str,
    path: str,
    *,
    hub_url: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    """Issue one HTTP call; return parsed JSON or ``None`` on any failure."""
    base = (hub_url or default_hub_url()).rstrip("/")
    url = f"{base}{path}"
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        LOGGER.warning("hub_client %s %s failed: %s", method, url, exc)
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        LOGGER.warning("hub_client %s %s returned non-JSON payload", method, url)
        return None


# ---------------------------------------------------------------- packs

def list_packs(
    *,
    kind: str | None = None,
    jurisdiction: str | None = None,
    corridor: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    latest_only: bool = True,
    hub_url: str | None = None,
) -> dict[str, Any] | None:
    """Filtered list of packs. Returns the wrapped envelope from the hub."""
    params = {
        "kind": kind,
        "jurisdiction": jurisdiction,
        "corridor": corridor,
        "tag": tag,
        "status_": status,
        "latest_only": "true" if latest_only else "false",
    }
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value not in (None, "")})
    suffix = f"?{query}" if query else ""
    return _request("GET", f"/api/hub/packs{suffix}", hub_url=hub_url)


def pull_pack(pack_id: str, *, version: str | None = None, hub_url: str | None = None) -> dict[str, Any] | None:
    """Download one pack body. ``version=None`` resolves to the latest."""
    suffix = f"/{version}" if version else ""
    return _request("GET", f"/api/hub/packs/{pack_id}{suffix}", hub_url=hub_url)


def list_versions(pack_id: str, *, hub_url: str | None = None) -> dict[str, Any] | None:
    """List every known version of a pack."""
    return _request("GET", f"/api/hub/packs/{pack_id}/versions", hub_url=hub_url)


def sync(since: str | None = None, *, hub_url: str | None = None) -> dict[str, Any] | None:
    """Incremental sync since the given ISO-8601 cursor."""
    suffix = f"?since={urllib.parse.quote(since, safe='')}" if since else ""
    return _request("GET", f"/api/hub/sync{suffix}", hub_url=hub_url)


# ---------------------------------------------------------------- submission

def submit_signal(
    *,
    source: str,
    jurisdiction: str,
    summary: str,
    consent_basis: str = "explicit_opt_in",
    corridor: str | None = None,
    risk_tags: list[str] | None = None,
    evidence_hashes: list[str] | None = None,
    hub_url: str | None = None,
) -> dict[str, Any] | None:
    """Send an anonymized usage signal. Local anonymizer is the caller's job.

    The hub re-checks for PII at the boundary; this is defence in depth,
    not a substitute for local anonymization.
    """
    payload = {
        "source": source,
        "jurisdiction": jurisdiction,
        "summary": summary,
        "consent_basis": consent_basis,
        "corridor": corridor,
        "risk_tags": risk_tags or [],
        "evidence_hashes": evidence_hashes or [],
    }
    payload = {key: value for key, value in payload.items() if value not in (None, "")}
    return _request("POST", "/api/hub/signals", body=payload, hub_url=hub_url)


def submit_proposal(
    *,
    kind: str,
    summary: str,
    deployment_id: str | None = None,
    organization: str | None = None,
    contact_email: str | None = None,
    jurisdiction: str | None = None,
    corridor: str | None = None,
    public_source_url: str | None = None,
    payload: dict[str, Any] | None = None,
    consent_public_proposal: bool = True,
    contact_publication_consent: bool = False,
    hub_url: str | None = None,
) -> dict[str, Any] | None:
    """Send a generic public-source proposal from a deployment."""
    body = {
        "kind": kind,
        "summary": summary,
        "deployment_id": deployment_id,
        "organization": organization,
        "contact_email": contact_email,
        "jurisdiction": jurisdiction,
        "corridor": corridor,
        "public_source_url": public_source_url,
        "payload": payload or {},
        "consent_public_proposal": consent_public_proposal,
        "contact_publication_consent": contact_publication_consent,
    }
    body = {key: value for key, value in body.items() if value not in (None, "")}
    return _request("POST", "/api/hub/client/submission", body=body, hub_url=hub_url)


def retract_submission(
    submission_id: str,
    *,
    deployment_id: str | None = None,
    reason: str | None = None,
    hub_url: str | None = None,
) -> dict[str, Any] | None:
    """Retract a submission. Only succeeds while it is still proposed/needs_review."""
    body = {
        "submission_id": submission_id,
        "deployment_id": deployment_id,
        "reason": reason,
    }
    body = {key: value for key, value in body.items() if value not in (None, "")}
    return _request("POST", "/api/hub/client/submission/retract", body=body, hub_url=hub_url)


__all__ = [
    "DEFAULT_PUBLIC_HUB",
    "default_hub_url",
    "list_packs",
    "list_versions",
    "pull_pack",
    "retract_submission",
    "submit_proposal",
    "submit_signal",
    "sync",
]
