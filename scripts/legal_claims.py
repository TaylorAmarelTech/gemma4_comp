"""Load, validate, and FLAG-FOR-RECHECK the vetted legal-claim library (configs/duecare/legal_claims.json).

The claim library is the EvidenceClaim-style verification/freshness overlay on the flat statute DB
(configs/duecare/legal_provisions.yaml). This module enforces its schema and, crucially, answers the
question Taylor asked: which claims are POTENTIALLY OUTDATED and must be re-verified (recheck_after has
passed, or the claim is high-volatility, or it is a time-bounded reform that has since become effective)?
Legal claims MUST pass applicability + temporal-validity + source-authority + exception checks before a
grounded answer uses them; this tool is the freshness half of that. Deterministic, no network, propose-only.

Run:
    python scripts/legal_claims.py --today 2026-07-10            # report claims due for recheck
    python scripts/legal_claims.py --render docs/research/legal_claims_register.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _ROOT / "configs" / "duecare" / "legal_claims.json"
REQUIRED = ("id", "claim_type", "text", "authority", "source_url", "jurisdiction",
            "binding_status", "as_of", "volatility", "recheck_after", "recheck_reason")
_VOLATILITY = ("low", "medium", "high")


def load_claims(path: Path = DEFAULT_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")).get("claims", [])


def validate_schema(claims: list[dict]) -> list[str]:
    """Return a list of schema problems (empty = valid). Checks required fields, unique ids, known
    volatility levels, and parseable ISO dates for as_of/recheck_after/effective_from."""
    errors: list[str] = []
    seen: set[str] = set()
    for i, c in enumerate(claims):
        cid = c.get("id", f"#{i}")
        for f in REQUIRED:
            if not c.get(f) and c.get(f) != []:
                errors.append(f"{cid}: missing required field '{f}'")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        if c.get("volatility") not in _VOLATILITY:
            errors.append(f"{cid}: volatility '{c.get('volatility')}' not in {_VOLATILITY}")
        for f in ("as_of", "recheck_after", "effective_from"):
            v = c.get(f)
            if v is None:
                continue
            try:
                date.fromisoformat(v)
            except (ValueError, TypeError):
                errors.append(f"{cid}: field '{f}' = {v!r} is not an ISO date (YYYY-MM-DD)")
    # referential integrity (audit A5): a supersede pointer must name a claim that actually exists, so the
    # build-upon/supersede chain can never dangle as the corpus grows.
    ids = {c.get("id") for c in claims}
    for c in claims:
        cid = c.get("id", "?")
        for f in ("superseded_by", "supersedes"):
            tgt = c.get(f)
            if tgt and tgt not in ids:
                errors.append(f"{cid}: {f} points to unknown claim id {tgt!r}")
    return errors


def due_for_recheck(claims: list[dict], today: date) -> list[dict]:
    """Claims that should be re-verified NOW: recheck_after has passed, OR volatility is high, OR a
    'reform' whose effective_from date is now in the past (its 'becomes applicable' moment arrived, so the
    'forthcoming' framing is stale). Each returned claim gets a '_reasons' list."""
    out = []
    for c in claims:
        reasons = []
        ra = c.get("recheck_after")
        try:
            if ra and date.fromisoformat(ra) <= today:
                reasons.append(f"recheck_after {ra} has passed")
        except (ValueError, TypeError):
            reasons.append(f"unparseable recheck_after {ra!r}")
        if c.get("volatility") == "high":
            reasons.append("high volatility")
        ef = c.get("effective_from")
        try:
            if ef:
                efd = date.fromisoformat(ef)
                if efd > today:
                    # not-yet-in-force for ANY claim_type -- a future effective_from means binding_status may
                    # overstate current applicability (e.g. a directive whose transposition deadline is future)
                    reasons.append(f"effective_from {ef} is in the FUTURE -- not yet in force; "
                                   "binding_status may overstate current applicability")
                elif c.get("claim_type") == "reform":
                    reasons.append(f"reform effective_from {ef} now in the past (update 'forthcoming' framing)")
        except (ValueError, TypeError):
            pass
        if reasons:
            out.append({**c, "_reasons": reasons})
    return out


def render_markdown(claims: list[dict], today: date) -> str:
    due = {c["id"] for c in due_for_recheck(claims, today)}
    lines = ["# Legal-claim register (with freshness / recheck flags)", "",
             f"Generated from `configs/duecare/legal_claims.json`; freshness evaluated as of {today}. "
             "Claims flagged RECHECK are potentially outdated and must be re-verified against a primary "
             "source before a grounded answer relies on them. This is not legal advice.", "",
             f"**{len(claims)} claims -- {len(due)} flagged for recheck.**", "",
             "| id | jurisdiction | binding | volatility | as_of | recheck_after | flag |",
             "|---|---|---|---|---|---|---|"]
    for c in sorted(claims, key=lambda x: (x.get("volatility") != "high", x.get("jurisdiction", ""))):
        flag = "**RECHECK**" if c["id"] in due else "ok"
        lines.append(f"| `{c['id']}` | {c.get('jurisdiction','')} | {c.get('binding_status','')} | "
                     f"{c.get('volatility','')} | {c.get('as_of','')} | {c.get('recheck_after','')} | {flag} |")
    lines += ["", "## Claims"]
    for c in claims:
        lines += [f"### {c['id']}  ({c.get('jurisdiction','')}, {c.get('claim_type','')})",
                  f"> {c.get('text','')}", "",
                  f"- **Authority:** {c.get('authority','')} ({c.get('authority_class','')}) -- <{c.get('source_url','')}>",
                  f"- **Applies to:** {c.get('applies_to','')}",
                  f"- **Exceptions:** {'; '.join(c.get('exceptions') or []) or 'none recorded'}",
                  f"- **Binding:** {c.get('binding_status','')} | **effective_from:** {c.get('effective_from')}"
                  f" | **as_of:** {c.get('as_of')} | **volatility:** {c.get('volatility')}",
                  f"- **Recheck after {c.get('recheck_after')}:** {c.get('recheck_reason','')}",
                  f"- **Caveats:** {'; '.join(c.get('caveats') or []) or 'none'}", ""]
    return "\n".join(lines)


def _format_due(due: list[dict]) -> str:
    if not due:
        return "no claims are due for recheck."
    lines = [f"{len(due)} claim(s) flagged for recheck:"]
    for c in due:
        lines.append(f"  [{c.get('volatility'):>6}] {c['id']:26s} {c.get('jurisdiction',''):>4} -- "
                     + "; ".join(c["_reasons"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate + flag-for-recheck the legal-claim library.")
    ap.add_argument("--path", type=Path, default=DEFAULT_PATH)
    ap.add_argument("--today", default=None, help="ISO date to evaluate freshness against (default: today)")
    ap.add_argument("--render", type=Path, default=None, help="write a markdown register to this path")
    args = ap.parse_args(argv)
    claims = load_claims(args.path)
    errors = validate_schema(claims)
    if errors:
        print("SCHEMA ERRORS:")
        for e in errors:
            print("  -", e)
        return 1
    today = date.fromisoformat(args.today) if args.today else date.today()
    print(f"legal-claim library OK: {len(claims)} claims validated. Freshness as of {today}.\n")
    print(_format_due(due_for_recheck(claims, today)))
    if args.render:
        args.render.write_text(render_markdown(claims, today), encoding="utf-8")
        print(f"\n-> rendered register to {args.render}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
