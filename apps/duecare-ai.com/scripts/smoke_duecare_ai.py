from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    expected_status: int = 200,
    timeout_seconds: float = 10.0,
) -> tuple[int, dict[str, Any] | list[Any] | None]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=data,
        method=method,
        headers=request_headers,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8")
    except URLError as exc:
        raise RuntimeError(f"network error while calling {path}: {exc.reason}") from exc

    if status != expected_status:
        raise RuntimeError(f"{path} returned {status}, expected {expected_status}: {body[:400]}")
    if not body:
        return status, None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return status, None
    return status, parsed


def _check(name: str, action: Any) -> CheckResult:
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports concise failures.
        return CheckResult(name=name, ok=False, detail=str(exc))
    return CheckResult(name=name, ok=True, detail="ok")


def run_smoke(base_url: str) -> list[CheckResult]:
    checks: list[tuple[str, Any]] = [
        ("health", lambda: _request_json(base_url, "/api/health")),
        ("status", lambda: _request_json(base_url, "/api/hub/status")),
        ("knowledge packs", lambda: _request_json(base_url, "/api/hub/knowledge-packs")),
        ("trends", lambda: _request_json(base_url, "/api/hub/trends")),
        ("local kb stats", lambda: _request_json(base_url, "/api/local-kb/stats")),
        (
            "cors preflight",
            lambda: _request_json(
                base_url,
                "/api/hub/status",
                method="OPTIONS",
                headers={
                    "Origin": "https://duecare-ai.com",
                    "Access-Control-Request-Method": "GET",
                },
                expected_status=200,
            ),
        ),
        (
            "reject raw pii in client payload",
            lambda: _request_json(
                base_url,
                "/api/hub/client/submission",
                method="POST",
                payload={
                    "kind": "context",
                    "deployment_id": "smoke-test",
                    "summary": "Composite update with no names.",
                    "payload": {"passport_ref": "A1234567"},
                    "consent_public_proposal": True,
                },
                expected_status=422,
            ),
        ),
    ]
    return [_check(name, action) for name, action in checks]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the DueCare public hub.")
    parser.add_argument("--base-url", required=True, help="Base URL, for example http://127.0.0.1:8000")
    args = parser.parse_args()

    results = run_smoke(args.base_url)
    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"[{marker}] {result.name}: {result.detail}")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
