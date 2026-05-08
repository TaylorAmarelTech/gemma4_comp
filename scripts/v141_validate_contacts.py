"""Contact-directory freshness validator.

Pings the `web_url` and `web_form_url` fields of every entry in
`harness/_contacts.json` and reports broken links. Phone numbers
and email addresses are NOT checked — those require human
verification (calling / sending) and we do not want to spam real
NGO inboxes for a CI check.

This script is intentionally a post-hackathon tool. It does not run
in the chat package. It does not modify the contacts file. It just
reports which URLs return non-2xx responses so a curator can update
the JSON before the next wheel bump.

Run:
    py -3.10 scripts/v141_validate_contacts.py
    py -3.10 scripts/v141_validate_contacts.py --timeout 30 --json out.json

Exit codes:
    0   all reachable URLs returned 2xx
    1   at least one URL returned non-2xx or timed out (warning)
    2   contacts file missing or malformed (error)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
CONTACTS = (REPO / "packages" / "duecare-llm-chat" / "src" / "duecare"
              / "chat" / "harness" / "_contacts.json")


def _check_url(url: str, timeout: int = 15) -> tuple[bool, int | None, str]:
    """Returns (ok, status_code, reason). HEAD where possible, GET on
    405. Treats 200-399 as success (some sites 30x to a canonical URL)."""
    try:
        req = Request(url, headers={
            "User-Agent": "DuecareContactValidator/0.14.5 "
                          "(+https://github.com/TaylorAmarelTech/gemma4_comp)",
        }, method="HEAD")
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            return (200 <= code < 400, code, "")
    except HTTPError as e:
        # 405 = method not allowed; retry as GET
        if e.code == 405:
            try:
                req = Request(url, headers={
                    "User-Agent": "DuecareContactValidator/0.14.5",
                })
                with urlopen(req, timeout=timeout) as resp:
                    code = getattr(resp, "status", 200)
                    return (200 <= code < 400, code, "")
            except Exception as e2:  # noqa: BLE001
                return (False, None, f"GET retry failed: {e2}")
        return (False, e.code, e.reason or "")
    except URLError as e:
        return (False, None, str(e.reason))
    except Exception as e:  # noqa: BLE001
        return (False, None, f"{type(e).__name__}: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=15,
                          help="Per-URL timeout seconds (default 15)")
    parser.add_argument("--json", type=str, default="",
                          help="Optional path to write a JSON report")
    args = parser.parse_args()

    if not CONTACTS.exists():
        print(f"ERROR: contacts file not found at {CONTACTS}")
        return 2

    try:
        block = json.loads(CONTACTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: contacts file is malformed JSON: {e}")
        return 2

    entries = block.get("entries", []) or []
    print(f"Validating {len(entries)} contact entries from {CONTACTS.name}")
    print(f"Schema: {block.get('schema')}@{block.get('version')} "
            f"(last_updated {block.get('last_updated')})\n")

    results: list[dict] = []
    n_checked = n_ok = n_fail = 0
    t0 = time.time()
    for entry in entries:
        ent_id = entry.get("id", "?")
        for field in ("web_url", "web_form_url"):
            url = entry.get(field)
            if not url:
                continue
            n_checked += 1
            ok, code, reason = _check_url(url, args.timeout)
            mark = "OK" if ok else "FAIL"
            print(f"  {mark:4s}  [{code or '---'}]  {ent_id} {field}={url}")
            if not ok:
                print(f"        reason: {reason}")
            results.append({
                "id":     ent_id,
                "field":  field,
                "url":    url,
                "ok":     ok,
                "status": code,
                "reason": reason,
            })
            if ok:
                n_ok += 1
            else:
                n_fail += 1

    dt = time.time() - t0
    print(f"\n{n_checked} URLs checked in {dt:.1f}s — "
            f"{n_ok} OK, {n_fail} FAIL")

    if args.json:
        Path(args.json).write_text(
            json.dumps({
                "schema":       block.get("schema"),
                "version":      block.get("version"),
                "last_updated": block.get("last_updated"),
                "n_checked":    n_checked,
                "n_ok":         n_ok,
                "n_fail":       n_fail,
                "elapsed_s":    round(dt, 1),
                "results":      results,
            }, indent=2),
            encoding="utf-8")
        print(f"Report written to {args.json}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
