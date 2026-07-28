#!/usr/bin/env python3
"""Validate a built read-only DueCare continuity bundle without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ATTR_RE = re.compile(r"(?<![-\w])(?:href|src|action)\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)
FORBIDDEN_SNAPSHOT_KEYS = {
    "api_key",
    "contact_email",
    "data_dir",
    "raw_log",
    "raw_logs",
    "secret",
    "sender_email",
    "submitter_email",
    "token",
}


def _normalize_base_path(value: str) -> str:
    text = str(value or "").strip()
    if not text or text == "/":
        return ""
    return ("/" + text.lstrip("/")).rstrip("/")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def _local_target(site: Path, href: str, base_path: str) -> Path | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return None
    path = unquote(parsed.path)
    if base_path:
        if path == base_path:
            path = "/"
        elif path.startswith(base_path + "/"):
            path = path[len(base_path) :]
        else:
            raise ValueError(f"root-relative URL escapes base path: {href}")
    relative = path.lstrip("/")
    if not relative:
        return site / "index.html"
    exact = site / relative
    if exact.is_file():
        return exact
    return exact / "index.html"


def validate(site: Path, *, base_path: str, site_url: str, expect_cname: str | None) -> list[str]:
    findings: list[str] = []
    base_path = _normalize_base_path(base_path)
    required = [
        site / "index.html",
        site / "404.html",
        site / ".nojekyll",
        site / "robots.txt",
        site / "sitemap.xml",
        site / "static" / "styles.css",
        site / "static" / "duecare-static-fallback.js",
        site / "static" / "snapshots" / "manifest.json",
    ]
    for path in required:
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(site)}")

    cname_path = site / "CNAME"
    if expect_cname is None and cname_path.exists():
        findings.append("CNAME must be omitted for the project-path preview")
    elif expect_cname is not None:
        actual = cname_path.read_text(encoding="utf-8").strip() if cname_path.is_file() else ""
        if actual != expect_cname:
            findings.append(f"CNAME mismatch: expected {expect_cname!r}, got {actual!r}")

    html_files = sorted(site.rglob("*.html"))
    page_files = [path for path in html_files if path.name == "index.html"]
    if len(page_files) != 51:
        findings.append(f"expected 51 pretty-URL pages, found {len(page_files)}")

    for page in html_files:
        text = page.read_text(encoding="utf-8", errors="replace")
        rel = page.relative_to(site)
        if 'name="duecare-static-mode" content="read-only-fallback"' not in text:
            findings.append(f"{rel}: missing static-mode marker")
        expected_script = f"{base_path}/static/duecare-static-fallback.js"
        if expected_script not in text:
            findings.append(f"{rel}: missing fallback boundary script")
        if re.search(r"fetch\([^)]*gemma4-comp\.onrender\.com", text, re.IGNORECASE):
            findings.append(f"{rel}: executable Render fetch remains")
        for _, href in ATTR_RE.findall(text):
            if href.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
                continue
            try:
                target = _local_target(site, href, base_path)
            except ValueError as exc:
                findings.append(f"{rel}: {exc}")
                continue
            if target is not None and not target.is_file():
                findings.append(f"{rel}: unresolved local target {href}")

    fallback_script = site / "static" / "duecare-static-fallback.js"
    if fallback_script.is_file():
        text = fallback_script.read_text(encoding="utf-8", errors="replace")
        for contract in (
            "window.fetch",
            "blockedResponse",
            "disableServerControls",
            "disableApiLinks",
            "/api/hub/packs",
        ):
            if contract not in text:
                findings.append(f"fallback script missing contract: {contract}")

    manifest_path = site / "static" / "snapshots" / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings.append("snapshot manifest is not valid JSON")
        else:
            if manifest.get("schema") != "duecare.static-fallback-snapshots.v1":
                findings.append("snapshot manifest schema mismatch")
            if manifest.get("contains_private_submissions") is not False:
                findings.append("snapshot manifest does not deny private submissions")
            source_revision = manifest.get("source_revision")
            if not isinstance(source_revision, str) or not re.fullmatch(
                r"(?:[0-9a-f]{40}|working-tree)", source_revision
            ):
                findings.append("snapshot manifest source_revision is not auditable")
            entries = manifest.get("entries")
            if not isinstance(entries, list) or len(entries) != 5:
                findings.append("snapshot manifest must contain exactly five allowlisted routes")
            else:
                for entry in entries:
                    path = site / str(entry.get("file", ""))
                    if not path.is_file():
                        findings.append(f"snapshot file missing: {entry.get('file')}")
                        continue
                    if _sha256(path) != entry.get("sha256"):
                        findings.append(f"snapshot checksum mismatch: {entry.get('file')}")
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        findings.append(f"snapshot is not valid JSON: {entry.get('file')}")
                        continue
                    forbidden = sorted(_walk_keys(payload) & FORBIDDEN_SNAPSHOT_KEYS)
                    if forbidden:
                        findings.append(
                            f"snapshot contains forbidden key(s) {', '.join(forbidden)}: "
                            f"{entry.get('file')}"
                        )

    robots = site / "robots.txt"
    sitemap = site / "sitemap.xml"
    canonical = site_url.rstrip("/")
    if robots.is_file() and f"Sitemap: {canonical}/sitemap.xml" not in robots.read_text(
        encoding="utf-8"
    ):
        findings.append("robots.txt sitemap URL does not match --site-url")
    if sitemap.is_file() and f"<loc>{canonical}/</loc>" not in sitemap.read_text(encoding="utf-8"):
        findings.append("sitemap root URL does not match --site-url")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--base-path", default="")
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--expect-cname", default=None)
    args = parser.parse_args(argv)
    findings = validate(
        args.site.resolve(),
        base_path=args.base_path,
        site_url=args.site_url,
        expect_cname=args.expect_cname,
    )
    if findings:
        for finding in findings:
            print(f"[static-fallback] FAIL: {finding}")
        return 1
    print(
        "[static-fallback] PASS: 51 pages, five safe snapshots, links, checksums, "
        "read-only controls, sitemap, and 404 are valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
