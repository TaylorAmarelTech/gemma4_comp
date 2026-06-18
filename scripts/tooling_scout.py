#!/usr/bin/env python3
"""Tooling scout -- exhaustively search GitHub (and PyPI) for integrable tools.

Turns the ad-hoc "go research GitHub repos" passes into a repeatable, deterministic
tool. Given one or more search queries, it runs ``gh search repos`` (and optionally
``gh search code``), dedups the hits, enriches each with stars / language /
license / archival / recency, and SCORES them against this project's adoption
constraints -- Python-first, permissively licensed, actively maintained, no Node,
no AGPL/GPL -- emitting a ranked ADOPT / CONSIDER / AVOID report.

It is the deterministic engine behind the ``tooling-scout`` agent: the agent picks
queries, runs this, then web-verifies the top ADOPT picks and writes the prose
recommendation. The scoring/ranking is pure and tested; the GitHub calls go
through an injectable ``run`` so the logic is exercised offline.

Usage:
    python scripts/tooling_scout.py -q "cloudflare bypass python" -q "stealth playwright"
    python scripts/tooling_scout.py --queries-file needs.txt --top 15 --json
    python scripts/tooling_scout.py -q "ckan client python" --code   # also search code
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone

#: licenses we can vendor/port freely
PERMISSIVE = {"mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "isc", "mpl-2.0",
              "cc0-1.0", "unlicense", "0bsd", "bsl-1.0", "cc-by-4.0", "postgresql"}
#: copyleft licenses that conflict with distributable tooling here
COPYLEFT = {"gpl-3.0", "gpl-2.0", "agpl-3.0", "lgpl-3.0", "lgpl-2.1", "agpl-3.0-only",
            "gpl-3.0-only", "gpl-2.0-only"}
_NODE_LANGS = {"javascript", "typescript", "vue", "svelte", "coffeescript"}

_REPO_FIELDS = "fullName,stargazersCount,language,license,pushedAt,description,isArchived,url"


# ---------------------------------------------------------------------------
# Scoring (pure -- tested offline)
# ---------------------------------------------------------------------------

def _license_key(repo: dict) -> str:
    lic = repo.get("license") or {}
    return str(lic.get("key") or "").lower() if isinstance(lic, dict) else str(lic).lower()


def _months_since(iso: str, *, now: datetime | None = None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - dt).days / 30.4


def score_repo(repo: dict, *, want_langs=("python",), stale_months: int = 18,
               now: datetime | None = None) -> tuple[float, list[str]]:
    """Score a repo (0-ish..16) against the adoption constraints + return flags.

    Higher is better. Flags name the blockers (``node``, ``copyleft:*``,
    ``no-license``, ``archived``, ``stale``) so ``classify`` can veto.
    """
    flags: list[str] = []
    stars = int(repo.get("stargazersCount") or 0)
    score = min(math.log10(stars + 1), 5.0) * 2.0          # up to 10 for popularity

    lang = (repo.get("language") or "").lower()
    if want_langs and lang in want_langs:
        score += 3
    elif lang in _NODE_LANGS:
        score -= 2
        flags.append("node")

    lic = _license_key(repo)
    if lic in PERMISSIVE:
        score += 3
    elif lic in COPYLEFT:
        score -= 4
        flags.append(f"copyleft:{lic}")
    elif not lic:
        score -= 1
        flags.append("no-license")

    if repo.get("isArchived"):
        score -= 4
        flags.append("archived")

    months = _months_since(repo.get("pushedAt", ""), now=now)
    if months is not None and months > stale_months:
        score -= 2
        flags.append(f"stale:{months:.0f}mo")

    return round(score, 2), flags


_BLOCKERS = ("archived", "copyleft:", "node", "no-license")


def classify(score: float, flags: list[str]) -> str:
    """ADOPT / CONSIDER / AVOID from a score + flags (blockers veto ADOPT)."""
    if any(f.startswith(("archived", "copyleft:")) for f in flags):
        return "AVOID"
    if any(f.startswith(("node", "no-license")) for f in flags):
        # usable-but-caveated (can't vendor a no-license / Node repo) -- never an
        # outright ADOPT, and only worth CONSIDER if it's otherwise strong.
        return "CONSIDER" if score >= 5 else "AVOID"
    if score >= 9:
        return "ADOPT"
    if score >= 5:
        return "CONSIDER"
    return "AVOID"


def evaluate(repo: dict, **kw) -> dict:
    """Augment a repo dict with score / flags / verdict."""
    score, flags = score_repo(repo, **kw)
    return {**repo, "score": score, "flags": flags, "verdict": classify(score, flags)}


# ---------------------------------------------------------------------------
# GitHub search (injectable runner)
# ---------------------------------------------------------------------------

def _gh(args: list[str], *, run) -> str:
    return run(["gh", *args])


def _default_run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                          encoding="utf-8").stdout


def gh_search_repos(query: str, *, limit: int = 20, run=_default_run) -> list[dict]:
    """`gh search repos <query>` -> list of repo dicts (empty on any failure)."""
    try:
        out = _gh(["search", "repos", query, "--limit", str(limit), "--json", _REPO_FIELDS],
                  run=run)
        data = json.loads(out or "[]")
        return [d for d in data if isinstance(d, dict)]
    except Exception:  # noqa: BLE001 -- a failed search is empty, never fatal
        return []


def gh_search_code(query: str, *, limit: int = 10, run=_default_run) -> list[str]:
    """`gh search code <query>` -> distinct owner/repo slugs that contain the code."""
    try:
        out = _gh(["search", "code", query, "--limit", str(limit), "--json", "repository"],
                  run=run)
        data = json.loads(out or "[]")
        slugs = []
        for d in data:
            repo = (d or {}).get("repository") or {}
            nm = repo.get("nameWithOwner") or repo.get("fullName")
            if nm and nm not in slugs:
                slugs.append(nm)
        return slugs
    except Exception:  # noqa: BLE001
        return []


def scout(queries: list[str], *, limit: int = 20, want_langs=("python",),
          run=_default_run, now: datetime | None = None) -> list[dict]:
    """Search every query, dedup by repo, evaluate, and rank by score (desc)."""
    seen: dict[str, dict] = {}
    for q in queries:
        for repo in gh_search_repos(q, limit=limit, run=run):
            name = repo.get("fullName")
            if name and name not in seen:
                seen[name] = repo
    evaluated = [evaluate(r, want_langs=want_langs, now=now) for r in seen.values()]
    evaluated.sort(key=lambda r: -r["score"])
    return evaluated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _render(rows: list[dict]) -> str:
    lines = [f"{'VERDICT':9} {'SCORE':>5} {'STARS':>6}  {'LICENSE':12} REPO",
             "-" * 78]
    for r in rows:
        lic = _license_key(r) or "-"
        flags = (" [" + ",".join(r["flags"]) + "]") if r["flags"] else ""
        lines.append(f"{r['verdict']:9} {r['score']:5.1f} {int(r.get('stargazersCount') or 0):6d}  "
                     f"{lic[:12]:12} {r['fullName']}{flags}")
        desc = (r.get("description") or "").strip()
        if desc:
            lines.append(f"            {desc[:88]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--query", action="append", default=[], help="search query (repeatable)")
    ap.add_argument("--queries-file", help="file with one query per line")
    ap.add_argument("--limit", type=int, default=20, help="results per query")
    ap.add_argument("--top", type=int, default=25, help="rows to show")
    ap.add_argument("--lang", default="python", help="preferred language (scored up)")
    ap.add_argument("--code", action="store_true", help="also list repos containing matching code")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    queries = list(args.query)
    if args.queries_file:
        queries += [ln.strip() for ln in open(args.queries_file, encoding="utf-8") if ln.strip()]
    if not queries:
        ap.error("provide at least one -q/--query or --queries-file")

    rows = scout(queries, limit=args.limit, want_langs=(args.lang.lower(),))[:args.top]
    if args.code:
        code_slugs = sorted({s for q in queries for s in gh_search_code(q)})
        print("# repos containing matching code:", ", ".join(code_slugs[:20]), file=sys.stderr)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(_render(rows))
        n = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("ADOPT", "CONSIDER", "AVOID")}
        print(f"\n{len(rows)} repos | ADOPT {n['ADOPT']} · CONSIDER {n['CONSIDER']} · AVOID {n['AVOID']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
