"""integrate_grep_rules.py -- validate + insert workflow-authored GREP rules.

Takes a candidates JSON (the `grep-rules-colloquial-expansion` workflow's return value,
shape {"rules": [ {rule, patterns, all_required, severity, citation, indicator,
trigger_examples, register}, ... ]}) and safely merges the GOOD ones into
``GREP_RULES`` in packages/duecare-llm-chat/.../harness/__init__.py.

Quality gates (a candidate is DROPPED unless it passes all):
  * name does not collide with an existing GREP rule (or an already-accepted candidate);
  * every pattern compiles as a regex;
  * the rule actually FIRES on >= 1 of its own trigger_examples (all_required -> every
    pattern present; else any pattern) -- this auto-filters broken/mismatched regex.

Surviving rules are formatted as Python dict literals (repr-escaped) and inserted
immediately before the ``]`` that closes the ``GREP_RULES`` list (located via the
``def _grep_call(`` anchor), under a category banner. The file is then py_compiled.

    <venv-python> scripts/integrate_grep_rules.py --candidates reports/grep_candidates.json \
        --category "CATEGORY MMM: COLLOQUIAL / SHORTHAND / COMMON-PHRASE DETECTION (2026-06-08)"
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARNESS = REPO / "packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py"
ANCHOR = "\ndef _grep_call("
SEV = {"high", "medium", "low"}


def _existing_names() -> set[str]:
    from duecare.chat.harness import GREP_RULES
    return {r.get("rule") for r in GREP_RULES if r.get("rule")}


def _fires(rule: dict) -> bool:
    """True if the rule triggers on >= 1 of its trigger_examples."""
    try:
        compiled = [re.compile(p, re.I) for p in rule["patterns"]]
    except re.error:
        return False
    if not compiled:
        return False
    examples = rule.get("trigger_examples") or []
    all_required = bool(rule.get("all_required"))
    for ex in examples:
        low = (ex or "").lower()
        present = [bool(c.search(low)) for c in compiled]
        if (all(present) if all_required else any(present)):
            return True
    return False


def _valid(rule: dict, taken: set[str]) -> tuple[bool, str]:
    name = (rule.get("rule") or "").strip()
    if not name or not re.fullmatch(r"[a-z0-9_]+", name):
        return False, "bad-name"
    if name in taken:
        return False, "dup-name"
    if not isinstance(rule.get("patterns"), list) or not rule["patterns"]:
        return False, "no-patterns"
    for p in rule["patterns"]:
        if not isinstance(p, str) or not p:
            return False, "empty-pattern"
        try:
            re.compile(p)
        except re.error:
            return False, "bad-regex"
    if rule.get("severity") not in SEV:
        return False, "bad-severity"
    if not (rule.get("citation") and rule.get("indicator")):
        return False, "missing-citation-or-indicator"
    if not _fires(rule):
        return False, "does-not-fire-on-examples"
    return True, "ok"


def _fmt(rule: dict) -> str:
    pats = ", ".join(repr(p) for p in rule["patterns"])
    return (
        "    {\n"
        f"        'rule': {rule['rule']!r},\n"
        f"        'patterns': [{pats}],\n"
        f"        'all_required': {bool(rule.get('all_required'))},\n"
        f"        'severity': {rule['severity']!r},\n"
        f"        'citation': {rule['citation']!r},\n"
        f"        'indicator': {rule['indicator']!r},\n"
        "    },"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--category", default="CATEGORY MMM: WORKFLOW-AUTHORED RULES")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = data.get("rules", data) if isinstance(data, dict) else data
    print(f"candidates: {len(cands)}")

    taken = _existing_names()
    print(f"existing GREP rules: {len(taken)}")

    kept, drops = [], {}
    for r in cands:
        ok, why = _valid(r, taken)
        if ok:
            taken.add(r["rule"])
            kept.append(r)
        else:
            drops[why] = drops.get(why, 0) + 1
    print(f"kept: {len(kept)}  dropped: {sum(drops.values())}  reasons: {drops}")
    if not kept:
        print("nothing to integrate")
        return 1

    block = (f"\n    # {args.category}\n"
             "    # Workflow-authored (grep-rules-colloquial-expansion); each fire-tested\n"
             "    # against its own trigger_examples before integration.\n"
             + "\n".join(_fmt(r) for r in kept) + "\n")

    if args.dry_run:
        print("--- DRY RUN: first 3 formatted rules ---")
        print("\n".join(_fmt(r) for r in kept[:3]))
        print(f"... would insert {len(kept)} rules")
        return 0

    content = HARNESS.read_text(encoding="utf-8")
    a = content.index(ANCHOR)
    close = content.rindex("\n]\n", 0, a)   # the "]" line closing GREP_RULES
    new = content[:close] + "\n" + block + content[close:]
    HARNESS.write_text(new, encoding="utf-8")
    print(f"inserted {len(kept)} rules into {HARNESS}")

    import py_compile
    py_compile.compile(str(HARNESS), doraise=True)
    print("py_compile OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
