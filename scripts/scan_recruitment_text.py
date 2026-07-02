#!/usr/bin/env python3
"""Scan recruitment text for trafficking-indicative ("suspicious") language.

A defensive screening tool for NGOs, regulators, and platform-safety teams:
paste a job ad / recruiter message, point it at a folder of saved pages, or
(opt-in) fetch a small list of URLs you are investigating, and it routes each
item through DueCare's deterministic GREP suspicious-language rules — the same
first tier the Platform Triage harness uses — then writes a propose-only
report. No model call, no network unless you pass --url, no live knowledge is
mutated.

Scope + ethics (read before running --url):
  * This screens content YOU provide or a SMALL list of pages YOU are
    investigating. It is not a mass crawler and deliberately caps the URL
    count, rate-limits, sends an identifying User-Agent, and respects
    robots.txt. Use it to triage recruitment material for exploitation
    indicators, the way a caseworker reviews an ad — not to scrape sites at
    scale.
  * Output is advisory. A GREP hit is a signal to review, never a verdict;
    "no hits" means "nothing matched the rule set", not "safe".

Usage:
    python scripts/scan_recruitment_text.py --text "Pay PHP 120,000 placement fee..."
    python scripts/scan_recruitment_text.py --file ad.txt
    python scripts/scan_recruitment_text.py --dir saved_pages/        # *.txt/*.md/*.html/*.htm
    python scripts/scan_recruitment_text.py --url https://example.org/jobs  # opt-in, robots-respecting
    python scripts/scan_recruitment_text.py --dir pages/ --out reports/recruitment_scan/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html as _html
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

from duecare.chat.harness import GREP_RULES, default_harness  # noqa: E402
from duecare.chat.harnesses.triage.handler import screen_items  # noqa: E402

USER_AGENT = "duecare-recruitment-screen/1.0 (+defensive anti-trafficking review; respects robots.txt)"
MAX_URLS = 25
MAX_FETCH_BYTES = 2_000_000
FETCH_TIMEOUT = 12.0
FETCH_PACE_SECONDS = 1.0
MAX_ITEM_CHARS = 20_000


def _strip_html(raw: str) -> str:
    """Reduce an HTML page to readable text (stdlib only)."""
    no_script = re.sub(r"(?is)<(script|style|head|noscript)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?is)<[^>]+>", " ", no_script)
    text = _html.unescape(text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _read_text_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        return _strip_html(raw)
    return raw


def _fetch_url(url: str) -> tuple[str, str | None]:
    """Fetch one URL as text. Returns (text, error). Robots-respecting, capped.

    Returns ("", reason) when the fetch is skipped or fails so the caller can
    record the reason instead of silently dropping the item.
    """
    import urllib.error
    import urllib.parse
    import urllib.request

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "", "url must be http(s)"
    # robots.txt gate
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        rp.read()
        if not rp.can_fetch(USER_AGENT, url):
            return "", "disallowed by robots.txt"
    except Exception:
        pass  # no robots.txt / unreachable -> proceed politely
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(MAX_FETCH_BYTES)
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return "", f"http {exc.code}"
    except Exception as exc:  # noqa: BLE001 -- one bad URL must not sink the run
        return "", f"{type(exc).__name__}: {exc}"[:160]
    body = raw.decode("utf-8", errors="replace")
    return (_strip_html(body) if "html" in ctype.lower() or "<html" in body[:500].lower()
            else body), None


def gather_items(args: argparse.Namespace) -> list[dict]:
    """Build the item list from --text / --file / --dir / --url inputs."""
    items: list[dict] = []
    if args.text:
        items.append({"id": "inline", "text": args.text})
    for fpath in args.file or []:
        p = Path(fpath)
        if not p.exists():
            print(f"  ! file not found: {fpath}", file=sys.stderr)
            continue
        items.append({"id": p.name, "text": _read_text_file(p)})
    if args.dir:
        d = Path(args.dir)
        paths = sorted(
            p for ext in ("*.txt", "*.md", "*.html", "*.htm", "*.json")
            for p in d.glob(ext)
        )
        for p in paths:
            items.append({"id": str(p.relative_to(d)), "text": _read_text_file(p)})
    if args.url:
        urls = list(args.url)[:MAX_URLS]
        if len(args.url) > MAX_URLS:
            print(f"  ! {len(args.url)} URLs given; capped at {MAX_URLS}", file=sys.stderr)
        for i, u in enumerate(urls):
            if i:
                time.sleep(FETCH_PACE_SECONDS)
            print(f"  fetching {u} ...", file=sys.stderr)
            text, err = _fetch_url(u)
            if err:
                print(f"    skipped: {err}", file=sys.stderr)
                continue
            items.append({"id": u, "text": text})
    # cap per-item length and drop empties
    cleaned: list[dict] = []
    for it in items:
        text = (it["text"] or "").strip()
        if not text:
            continue
        cleaned.append({"id": it["id"], "text": text[:MAX_ITEM_CHARS]})
    return cleaned


def _agency_check(items: list[dict], result: dict, registry_path: str) -> None:
    """Cross-check any agency name an item names against the licensed registry.

    A recruiter not on the official licensed list — or one that is
    EXPIRED/CANCELLED/DELISTED — is a strong legitimacy red flag that
    complements the GREP `licensed_agency_chop_passthrough` rule. Best-effort:
    a registry that won't load just skips the check.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dc_agency_registry", str(_ROOT / "scripts" / "agency_registry.py"))
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: agency_registry defines a frozen dataclass whose
    # KW_ONLY check reads sys.modules.get(cls.__module__).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    try:
        registry = mod.load_registry(registry_path)
    except Exception as exc:  # noqa: BLE001 -- missing registry just skips
        for row in result["items"]:
            row["agency_check"] = {"skipped": f"registry not loaded: {exc}"[:160]}
        return
    # Two-pronged name harvest:
    #  (1) DIRECT registry match -- if a known agency's distinctive name
    #      appears in the text, verify it (catches a CANCELLED/DELISTED agency
    #      still advertising, the highest-value case).
    #  (2) REGEX harvest -- capitalized multi-word names ending in a recruiter
    #      suffix, to catch UNKNOWN agencies (not_found) that aren't in the
    #      registry, especially when a licence number is claimed.
    name_re = re.compile(
        r"\b([A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+){0,4}\s+"
        r"(?:Agency|Agencies|Manpower|Recruitment|Placement|Services|Solutions|"
        r"Workforce|Crewing|Enterprises|Corporation|Consultancy|Inc\.?|Corp\.?|Co\.?))\b")
    lic_re = re.compile(r"\b((?:POEA|DMW|DOH)[-\s]?[A-Z0-9\-]{3,})\b", re.I)

    def _norm(s: str) -> str:
        return mod.normalize_name(s)

    for row, item in zip(result["items"], items):
        text = item["text"]
        norm_text = " " + re.sub(r"\s+", " ", _norm(text)) + " "
        lic_m = lic_re.search(text)
        lic = lic_m.group(1) if lic_m else ""
        candidates: list[str] = []
        # (1) direct registry-name presence (use the agency's full name so the
        # verifier matches exactly; require its leading 2 tokens to be present)
        for p in registry:
            toks = p.norm_name.split()
            lead = " ".join(toks[:2]) if len(toks) >= 2 else (toks[0] if toks else "")
            if lead and len(lead) >= 6 and f" {lead} " in norm_text:
                candidates.append(p.name)
        # (2) regex harvest
        candidates.extend(name_re.findall(text))
        checks = []
        seen_raw: set[str] = set()
        seen_resolved: set[str] = set()
        for nm in candidates:
            key = _norm(nm)
            if not key or key in seen_raw:
                continue
            seen_raw.add(key)
            v = mod.verify_agency(nm, registry, claimed_license=lic)
            # dedupe distinct raw strings that resolve to the same registry
            # agency (e.g. "Join Easternwind..." vs "Easternwind...")
            resolved = v.matched_name or key
            if resolved in seen_resolved:
                continue
            seen_resolved.add(resolved)
            checks.append({"name": nm, "status": v.status,
                           "license_status": v.license_status,
                           "advisory": v.advisory})
            # escalate a clean GREP pass when a named agency is bogus/red
            if v.status in {"not_found", "licensed_red"} and row["status"] in {
                    "passed_grep_only", "cleared"}:
                row["status"] = "review"
                row["flagged_by"] = "agency_not_verified"
        row["agency_check"] = checks or {"note": "no agency name detected"}


def scan(items: list[dict], registry_path: str = "") -> dict:
    """Run items through the GREP suspicious-language tier (no model).

    When ``registry_path`` is set, also cross-check named agencies against the
    licensed-agency registry (legitimacy anti-signal).
    """
    harness = default_harness()
    grep_call = harness.get("grep_call")
    result = screen_items(items, grep_call=grep_call, model_call=None)
    # enrich each row with the human-readable rule indicators it hit, pulled
    # from the live rule set so the report explains WHY each item was flagged.
    rules_by_id = {r.get("rule"): r for r in GREP_RULES}
    for row, item in zip(result["items"], items):
        ids = (row.get("grep") or {}).get("rule_ids") or []
        row["why"] = [
            {
                "rule": rid,
                "severity": rules_by_id.get(rid, {}).get("severity", ""),
                "citation": rules_by_id.get(rid, {}).get("citation", ""),
                "indicator": rules_by_id.get(rid, {}).get("indicator", ""),
            }
            for rid in ids
        ]
        # preview only (the report is for a human reviewer, not a store)
        row["text_preview"] = item["text"][:280]
    if registry_path:
        _agency_check(items, result, registry_path)
    return result


def write_report(result: dict, out_dir: Path, stamp: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"scan_{stamp}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = result["items"]
    s = result["summary"]
    lines = [
        "# Recruitment-text suspicious-language scan",
        "",
        f"- items: {s['n_items']}  ·  flagged: {s['n_flagged']}  ·  "
        f"review: {s['n_review']}  ·  no-hit pass: {s['n_passed_grep_only']}",
        "- tier: deterministic GREP rules only (no model). Advisory, not a verdict.",
        "",
    ]
    order = {"flagged": 0, "review": 1, "passed_grep_only": 2, "cleared": 3}
    for row in sorted(rows, key=lambda r: order.get(r["status"], 9)):
        lines.append(f"## {row['id']} — **{row['status']}**")
        grep = row.get("grep") or {}
        lines.append(
            f"- grep: {grep.get('n_hits', 0)} hit(s), max severity "
            f"{grep.get('max_severity') or '—'}"
        )
        for w in row.get("why", []):
            lines.append(f"  - `{w['rule']}` ({w['severity']}) — {w['indicator'][:240]}")
            if w["citation"]:
                lines.append(f"    - cite: {w['citation'][:240]}")
        lines.append(f"- preview: {row.get('text_preview', '')[:240]}")
        lines.append("")
    md_path = out_dir / f"scan_{stamp}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="screen a single inline string")
    ap.add_argument("--file", action="append", help="screen a text/HTML file (repeatable)")
    ap.add_argument("--dir", help="screen every *.txt/*.md/*.html/*.json in a directory")
    ap.add_argument("--url", action="append",
                    help="opt-in: fetch + screen a URL (repeatable, robots-respecting, "
                         f"capped at {MAX_URLS})")
    ap.add_argument("--registry", default="",
                    help="optional: licensed-agency registry JSON/CSV to cross-check named "
                         "agencies against (e.g. data/agency_registry/sample_licensed_agencies.json)")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "recruitment_scan"),
                    help="report output directory (propose-only; default reports/recruitment_scan/)")
    ap.add_argument("--stamp", default="", help="report filename stamp (default: content hash)")
    args = ap.parse_args(argv)

    if not any([args.text, args.file, args.dir, args.url]):
        ap.error("provide at least one of --text / --file / --dir / --url")

    print("DueCare recruitment-text screen (defensive; GREP-only; propose-only)", file=sys.stderr)
    items = gather_items(args)
    if not items:
        print("no screenable items gathered.", file=sys.stderr)
        return 1

    result = scan(items, registry_path=args.registry)
    # deterministic stamp from content so repeat runs are stable + idempotent
    stamp = args.stamp or hashlib.sha256(
        "".join(sorted(i["id"] for i in items)).encode("utf-8")
    ).hexdigest()[:12]
    json_path, md_path = write_report(result, Path(args.out), stamp)

    s = result["summary"]
    print(
        f"\nscanned {s['n_items']} item(s): "
        f"{s['n_flagged']} flagged, {s['n_review']} review, "
        f"{s['n_passed_grep_only']} no-hit pass",
        file=sys.stderr,
    )
    print(f"report: {md_path}", file=sys.stderr)
    print(f"        {json_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
