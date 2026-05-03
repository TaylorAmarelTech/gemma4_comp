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


# Known slug drift overrides — actual live slug differs from
# kernel-metadata.json id because the kernel was first pushed under a
# different title and Kaggle locks the slug at creation. Add new
# entries here as drift is found.
SLUG_OVERRIDES = {
    "taylorsamarel/duecare-chat-playground":
        "taylorsamarel/duecare-gemma-chat-playground",
    "taylorsamarel/duecare-chat-playground-with-grep-rag-tools":
        "taylorsamarel/duecare-gemma-chat-playground-grep-rag-tools",
}

# The 11 submission notebooks live at kaggle/<purpose>/ (NOT under
# kaggle/kernels/). Probed alongside the research arc.
SUBMISSION_FOLDERS = (
    "chat-playground",
    "chat-playground-with-grep-rag-tools",
    "content-classification-playground",
    "content-knowledge-builder-playground",
    "gemma-content-classification-evaluation",
    "live-demo",
    "prompt-generation",
    "bench-and-tune",
    "research-graphs",
    "chat-playground-with-agentic-research",
    "chat-playground-jailbroken-models",
)


def _collect_metadata_paths() -> list[tuple[str, Path]]:
    """Return (label, metadata_path) for every notebook to verify.

    Includes the 11 submission notebooks at kaggle/<purpose>/ and the
    research-arc notebooks at kaggle/kernels/<n>/.
    """
    out: list[tuple[str, Path]] = []
    for folder in SUBMISSION_FOLDERS:
        p = Path("kaggle") / folder / "kernel-metadata.json"
        if p.exists():
            out.append((f"submission/{folder}", p))
    for p in sorted(Path("kaggle/kernels").glob("*/kernel-metadata.json")):
        out.append((f"research/{p.parent.name}", p))
    return out


def main() -> int:
    errors: list[tuple[str, str, int]] = []
    drifted: list[tuple[str, str, str]] = []
    for label, meta_path in _collect_metadata_paths():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        wanted_id = meta["id"]
        live_id = SLUG_OVERRIDES.get(wanted_id, wanted_id)
        if wanted_id != live_id:
            drifted.append((label, wanted_id, live_id))
        live_url = f"https://www.kaggle.com/code/{live_id}"
        status_code = _probe(live_url, timeout=10)
        status = "OK" if status_code == 200 else f"FAIL {status_code}"
        drift_marker = "  [SLUG DRIFT]" if wanted_id != live_id else ""
        print(f"{label}: {status} {live_url}{drift_marker}")
        if status_code != 200:
            errors.append((label, live_url, status_code))

    print()
    if drifted:
        print(f"{len(drifted)} notebook(s) with slug drift "
              f"(live slug != metadata id, handled via SLUG_OVERRIDES):")
        for label, wanted, live in drifted:
            print(f"  {label}: metadata={wanted}  live={live}")
        print()

    if errors:
        print(f"{len(errors)} notebook(s) return non-200:")
        for name, url, code in errors:
            print(f"  {name} {code} {url}")
        return 1

    total = len(_collect_metadata_paths())
    print(f"All {total} notebooks resolve "
          f"(including {len(drifted)} via slug overrides).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())