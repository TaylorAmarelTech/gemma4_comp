"""Verify that configured Kaggle notebook URLs resolve."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_NOT_FOUND_MARKERS = (
    "Page not found",
    "This page isn't available",
    "does not exist",
)


def _probe(url: str, *, timeout: int) -> int:
    """Probe a Kaggle URL and return 200 only if the page actually loads.

    Kaggle rejects HEAD requests and non-browser user-agents with 404
    even for pages that render fine in a real browser. We must use GET
    with a browser user-agent, then inspect the response body because
    Kaggle's soft-404 page also returns HTTP 200.
    """
    request = Request(
        url,
        method="GET",
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            if status != 200:
                return status
            body = response.read(4000).decode("utf-8", errors="replace")
            if any(marker in body for marker in _NOT_FOUND_MARKERS):
                return 404
            return 200
    except HTTPError as exc:
        return exc.code
    except URLError:
        return 0


def main() -> int:
    errors: list[tuple[str, str, int]] = []
    metadata_files = sorted(Path("kaggle/kernels").glob("*/kernel-metadata.json"))
    for meta_path in metadata_files:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        slug = meta["id"].split("/", 1)[1]
        url = f"https://www.kaggle.com/code/taylorsamarel/{slug}"
        status_code = _probe(url, timeout=10)
        status = "OK" if status_code == 200 else f"FAIL {status_code}"
        print(f"{meta_path.parent.name}: {status} {url}")
        if status_code != 200:
            errors.append((meta_path.parent.name, url, status_code))

    if errors:
        print(f"\n{len(errors)} notebooks return non-200:")
        for name, url, code in errors:
            print(f"  {name} {code} {url}")
        return 1

    print(f"\nAll {len(metadata_files)} notebooks resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())