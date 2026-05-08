"""Create or update the Render service for duecare-ai.com.

The script reads the Render token from RENDER_API_KEY. It never prints the
secret. It is intentionally dependency-free so it can run from a clean checkout.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.render.com/v1"
SERVICE_NAME = "duecare-ai-hub"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"
BRANCH = "master"
ROOT_DIR = "apps/duecare-ai.com"
DOMAINS = ("duecare-ai.com", "www.duecare-ai.com")

ENV_VARS = [
    {"key": "DUECARE_ENV", "value": "production"},
    {"key": "DUECARE_PRIVACY_MODE", "value": "anonymized_signals_only_no_raw_pii"},
    {"key": "DUECARE_STORAGE", "value": "file"},
    {"key": "DUECARE_DATA_DIR", "value": "/app/.duecare"},
    {"key": "PORT", "value": "10000"},
]


class RenderError(RuntimeError):
    """Raised when the Render API returns an unexpected response."""


def _api_key() -> str:
    key = os.environ.get("RENDER_API_KEY", "").strip()
    if not key:
        raise RenderError("RENDER_API_KEY is not set in this terminal environment.")
    return key


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {_api_key()}",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = payload
        return {"_render_http_error": True, "status": exc.code, "body": parsed}


def _raise_if_error(value: Any, *, action: str, allow_conflict: bool = False) -> Any:
    if isinstance(value, dict) and value.get("_render_http_error"):
        status = value.get("status")
        if allow_conflict and status == 409:
            return value
        raise RenderError(f"Render API failed during {action} with HTTP {status}: {value.get('body')}")
    return value


def _select_owner_id() -> str:
    explicit = os.environ.get("RENDER_OWNER_ID", "").strip()
    if explicit:
        return explicit

    response = _raise_if_error(_request("GET", "/owners?limit=100"), action="list owners")
    if not isinstance(response, list) or not response:
        raise RenderError("No Render workspaces were returned for this API key.")

    owners = [item.get("owner", {}) for item in response if isinstance(item, dict)]
    owners = [owner for owner in owners if isinstance(owner, dict) and owner.get("id")]
    if not owners:
        raise RenderError("No usable Render workspace IDs were returned for this API key.")

    if len(owners) > 1:
        print("Multiple Render workspaces found; using the first. Set RENDER_OWNER_ID to choose explicitly.")
    owner = owners[0]
    print(f"Using Render workspace: {owner.get('name', 'unnamed')} ({owner.get('type', 'unknown')})")
    return str(owner["id"])


def _service_payload(owner_id: str) -> dict[str, Any]:
    return {
        "type": "web_service",
        "name": SERVICE_NAME,
        "ownerId": owner_id,
        "repo": REPO_URL,
        "branch": BRANCH,
        "rootDir": ROOT_DIR,
        "autoDeploy": "yes",
        "envVars": ENV_VARS,
        "serviceDetails": {
            "runtime": "docker",
            "envSpecificDetails": {
                "dockerfilePath": "./Dockerfile",
                "dockerContext": ".",
            },
            "healthCheckPath": "/api/health",
            "plan": os.environ.get("RENDER_PLAN", "starter"),
            "region": os.environ.get("RENDER_REGION", "oregon"),
            "numInstances": 1,
            "disk": {
                "name": "duecare-ai-data",
                "mountPath": "/app/.duecare",
                "sizeGB": 1,
            },
        },
    }


def _find_existing_service(owner_id: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "ownerId": owner_id,
            "name": SERVICE_NAME,
            "type": "web_service",
            "limit": "20",
        }
    )
    response = _raise_if_error(_request("GET", f"/services?{query}"), action="find existing service")
    if not isinstance(response, list):
        return None
    for item in response:
        if not isinstance(item, dict):
            continue
        service = item.get("service")
        if isinstance(service, dict) and service.get("name") == SERVICE_NAME:
            return service
    return None


def _create_or_get_service(owner_id: str) -> dict[str, Any]:
    existing = _find_existing_service(owner_id)
    if existing:
        print(f"Found existing Render service: {existing.get('id')}")
        return existing

    response = _raise_if_error(_request("POST", "/services", _service_payload(owner_id)), action="create service")
    service = response.get("service") if isinstance(response, dict) else None
    if not isinstance(service, dict) or not service.get("id"):
        raise RenderError(f"Unexpected create-service response: {response}")
    print(f"Created Render service: {service['id']}")
    print(f"Dashboard: {service.get('dashboardUrl', '(dashboard URL not returned)')}")
    return service


def _add_domains(service_id: str) -> None:
    for domain in DOMAINS:
        response = _raise_if_error(
            _request("POST", f"/services/{service_id}/custom-domains", {"name": domain}),
            action=f"add domain {domain}",
            allow_conflict=True,
        )
        if isinstance(response, dict) and response.get("_render_http_error") and response.get("status") == 409:
            print(f"Domain already exists or conflicts: {domain}")
            continue
        print(f"Added custom domain: {domain}")


def _trigger_deploy(service_id: str) -> None:
    response = _raise_if_error(
        _request("POST", f"/services/{service_id}/deploys", {"clearCache": "do_not_clear"}),
        action="trigger deploy",
    )
    deploy = response.get("deploy") if isinstance(response, dict) else None
    deploy_id = deploy.get("id") if isinstance(deploy, dict) else None
    print(f"Triggered deploy: {deploy_id or 'created'}")


def main() -> int:
    try:
        owner_id = _select_owner_id()
        service = _create_or_get_service(owner_id)
        service_id = str(service["id"])
        _add_domains(service_id)
        _trigger_deploy(service_id)
        print("Render setup request complete.")
        print("Next: configure DNS records in Cloudflare, then verify custom domains in Render.")
        return 0
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
