"""List or check external links on active public surfaces.

The existing public-surface validator checks repo-local links and app routes.
This script covers the complementary case: outbound http(s) links in active
Markdown/HTML files. By default it lists discovered links without network
access; pass `--check` to perform HEAD/GET probes.

Examples:

    python scripts/check_external_links.py --list
    python scripts/check_external_links.py --check --timeout 8 --max 100
    python scripts/check_external_links.py --json --check
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_GLOBS: tuple[str, ...] = (
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "docs/**/*.md",
    "examples/**/*.md",
    "kaggle/**/README.md",
    "kaggle/_INDEX.md",
    "apps/duecare-ai.com/app/templates/*.html",
    "packages/*/README.md",
)

EXCLUDE_PARTS: tuple[str, ...] = (
    "_archive/",
    "_reference/",
    "docs/adr/",
    "docs/duecare_adversarial_audit.md",
    "docs/notes/",
    ".venv/",
    "node_modules/",
    "site-packages/",
)

URL_RE = re.compile(r"https?://[^\s<>)\"']+")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_ATTR_RE = re.compile(r"\b(?:href|src)=[\"'](https?://[^\"']+)[\"']", re.IGNORECASE)
EXISTS_BUT_NOT_FETCHABLE = {401, 403, 405}


@dataclass(frozen=True)
class LinkRef:
    url: str
    file: str
    line: int


@dataclass
class LinkResult:
    url: str
    ok: bool
    status: int | None
    error: str
    file: str
    line: int
    elapsed_ms: int


def _excluded(path: Path) -> bool:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    return any(part in rel for part in EXCLUDE_PARTS)


def _walk_active() -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in ACTIVE_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file() or _excluded(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def _clean_url(url: str) -> str:
    url = html.unescape(url.strip())
    return url.rstrip(".,;]`")


def _should_skip_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    raw = url.lower()
    host = (parsed.hostname or "").lower()
    if not parsed.netloc:
        return True
    if any(token in url for token in ("${", "{{", "}}", "$", "...", "…", "*")):
        return True
    if "your-url" in raw or "example.com" in raw or "example.org" in raw:
        return True
    if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return True
    if "your-" in host or host.startswith("your"):
        return True
    if host.startswith(("192.168.", "10.")):
        return True
    if host.endswith(".local"):
        return True
    return False


def extract_links() -> list[LinkRef]:
    refs: list[LinkRef] = []
    for path in _walk_active():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        in_fence = False
        for line_no, line in enumerate(text.splitlines(), start=1):
            if path.suffix.lower() in {".md", ".markdown"} and line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if "external-link-check:ignore" in line or "audit-allow:drift" in line:
                continue
            candidates: list[str] = []
            candidates.extend(m.group(1) for m in MD_LINK_RE.finditer(line))
            candidates.extend(m.group(1) for m in HTML_ATTR_RE.finditer(line))
            candidates.extend(m.group(0) for m in URL_RE.finditer(line))
            for raw in candidates:
                url = _clean_url(raw)
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in {"http", "https"} or _should_skip_url(url):
                    continue
                refs.append(LinkRef(url=url, file=rel, line=line_no))
    deduped: dict[str, LinkRef] = {}
    for ref in refs:
        deduped.setdefault(ref.url, ref)
    return sorted(deduped.values(), key=lambda item: (urllib.parse.urlparse(item.url).netloc, item.url))


def check_url(ref: LinkRef, timeout: float) -> LinkResult:
    started = time.perf_counter()
    headers = {"User-Agent": "DueCareLinkCheck/1.0 (+https://duecare-ai.com)"}
    status: int | None = None
    error = ""
    ok = False
    try:
        req = urllib.request.Request(ref.url, method="HEAD", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(resp.status)
            ok = 200 <= status < 400
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        if status in {405, 403}:
            try:
                req = urllib.request.Request(ref.url, method="GET", headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = int(resp.status)
                    ok = 200 <= status < 400
            except urllib.error.HTTPError as get_exc:
                status = int(get_exc.code)
                ok = status in EXISTS_BUT_NOT_FETCHABLE
                if not ok:
                    error = f"HTTPError: {get_exc}"
            except Exception as get_exc:  # noqa: BLE001
                ok = status in EXISTS_BUT_NOT_FETCHABLE
                if not ok:
                    error = f"{type(get_exc).__name__}: {get_exc}"
        elif status in EXISTS_BUT_NOT_FETCHABLE:
            ok = True
        else:
            error = f"HTTPError: {exc}"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return LinkResult(ref.url, ok, status, error, ref.file, ref.line, elapsed_ms)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Probe links over the network.")
    parser.add_argument("--list", action="store_true", help="List discovered links without network checks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-link timeout in seconds.")
    parser.add_argument("--max", type=int, default=0, help="Maximum links to process; 0 means all.")
    args = parser.parse_args(argv)

    refs = extract_links()
    if args.max > 0:
        refs = refs[: args.max]

    if not args.check:
        payload = [asdict(ref) for ref in refs]
        if args.json:
            print(json.dumps({"count": len(refs), "links": payload}, indent=2, sort_keys=True))
        else:
            print(f"External links discovered: {len(refs)}")
            for ref in refs:
                print(f"{ref.file}:{ref.line} {ref.url}")
        return 0

    results = [check_url(ref, timeout=args.timeout) for ref in refs]
    failures = [res for res in results if not res.ok]
    if args.json:
        print(json.dumps({"count": len(results), "failures": len(failures), "results": [asdict(r) for r in results]}, indent=2, sort_keys=True))
    else:
        print(f"External links checked: {len(results)} · failures: {len(failures)}")
        for res in results:
            marker = "OK" if res.ok else "FAIL"
            status = res.status if res.status is not None else "-"
            detail = f" {res.error}" if res.error else ""
            print(f"[{marker}] {status} {res.file}:{res.line} {res.url}{detail}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
