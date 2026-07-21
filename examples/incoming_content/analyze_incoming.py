#!/usr/bin/env python3
"""Run example incoming content through the DueCare indicator engine.

This is the "what does the harness actually receive, and what does it produce"
example. It reads ``incoming_samples.jsonl`` -- synthetic, composite messages of
the kind a DueCare integration would see on a job board, a worker helpline, a
contract-review queue, or a public forum -- and for each one prints the ILO
forced-labour indicators surfaced (with the controlling convention/reference),
a weighted risk level, and a self-check verdict against the sample's declared
``expect`` value.

Each sample declares ``expect``:

  * ``fires``    -- the compact engine should surface >=1 indicator.
  * ``clean``    -- a benign control that must NOT fire (an over-flag is a bug).
  * ``boundary`` -- concerning content the *compact representative* engine does
    NOT catch but the full production GREP layer (451 rules / 11+ languages)
    does. A compact "LOW" here is a known representative-subset boundary, NOT a
    safety clearance. See ``README.md``.

It uses the published :mod:`duecare.kit` package when installed
(``pip install duecare-llm-kit``) and otherwise falls back to the in-repo copy,
so it runs identically before and after the PyPI release.

Run it::

    python examples/incoming_content/analyze_incoming.py
    python examples/incoming_content/analyze_incoming.py --json
    python examples/incoming_content/analyze_incoming.py --only chat-002

Exit code is non-zero only on a real regression: a benign control that fires
(over-flag) or a ``fires`` sample that goes silent (miss). Declared boundaries
do not fail the run. Deterministic stdlib + regex only -- no model, no network,
no API key. All content is synthetic/composite; see ``.claude/rules/10_safety_gate.md``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "incoming_samples.jsonl"


def _load_engine():
    """Prefer the published package; fall back to the in-repo engine."""
    try:
        from duecare.kit import engine  # type: ignore

        return engine, "duecare.kit.engine (installed package)"
    except Exception:  # pragma: no cover - repo fallback path
        pass
    repo_root = HERE.parents[1]
    scripts = repo_root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import types

    from _usecase_engine import ENGINE  # type: ignore

    module = types.ModuleType("_incoming_engine")
    exec(compile(ENGINE, "<duecare-engine>", "exec"), module.__dict__)
    return module, "scripts/_usecase_engine.ENGINE (in-repo fallback)"


def _verdict(expect, fired):
    """Return (label, is_regression) comparing the declared expectation to reality."""
    if expect == "clean":
        return ("OK -- correctly clean (benign control)", False) if not fired \
            else ("OVER-FLAG -- benign control fired (precision bug)", True)
    if expect == "fires":
        return ("OK -- fired as expected", False) if fired \
            else ("MISS -- expected an indicator, engine was silent", True)
    if expect == "boundary":
        return ("caught (compact engine also fired this boundary case)", False) if fired \
            else ("BOUNDARY -- compact engine silent; production GREP layer fires (see note)", False)
    return ("(no expectation declared)", False)


def analyze_one(engine, sample):
    """Scan one incoming message and return the full engine analysis + self-check."""
    text = sample["text"]
    hits = engine.scan(text)
    level, why = engine.risk_level(hits)
    chain = engine.generate_chain(text)
    present = [step for _, step in chain if "PRESENT" in step]
    expect = sample.get("expect", "")
    verdict, is_regression = _verdict(expect, bool(hits))
    return {
        "id": sample["id"],
        "channel": sample["channel"],
        "language": sample["language"],
        "country_context": sample.get("country_context", ""),
        "text": text,
        "note": sample.get("note", ""),
        "expect": expect,
        "verdict": verdict,
        "is_regression": is_regression,
        "risk_level": level,
        "risk_reason": why,
        "indicators": [
            {"indicator": h["indicator"], "label": h["label"],
             "snippet": h["snippet"], "ilo_ref": h["ilo_ref"]}
            for h in hits
        ],
        "chain_present_steps": present,
    }


def _print_human(rows, source):
    bar = "=" * 78
    print(bar)
    print("DueCare incoming-content analysis")
    print(f"engine: {source}")
    print(f"samples: {len(rows)}  ({SAMPLES.name})")
    print(bar)
    for r in rows:
        print()
        print(f"[{r['id']}]  {r['channel']}  ({r['language']}, {r['country_context']})")
        print(f"  expect={r['expect']:8s} -> {r['verdict']}")
        print(f"  RISK: {r['risk_level']} -- {r['risk_reason']}")
        print(f"  incoming: {r['text']}")
        if r["indicators"]:
            print(f"  indicators ({len(r['indicators'])}):")
            for ind in r["indicators"]:
                print(f"    - {ind['label']}  <- \"{ind['snippet']}\"")
                print(f"        ref: {ind['ilo_ref']}")
        else:
            print("  indicators: none surfaced by the compact engine")
        print(f"  note: {r['note']}")
    print()
    print(bar)
    fired = sum(1 for r in rows if r["expect"] == "fires")
    clean = sum(1 for r in rows if r["expect"] == "clean")
    bound = sum(1 for r in rows if r["expect"] == "boundary")
    regr = sum(1 for r in rows if r["is_regression"])
    print(f"summary: {fired} expected-to-fire, {clean} benign control(s), {bound} known compact-engine boundary case(s).")
    ok = "PASS -- no over-flags, no unexpected misses"
    bad = f"FAIL -- {regr} regression(s)"
    print(f"self-check: {ok if regr == 0 else bad}")
    print("note: a 'boundary' LOW is a representative-subset limit, not a safety clearance -- the full")
    print("      production GREP layer (451 rules / 11+ languages) catches those.")
    print(bar)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyze example incoming content with the DueCare engine.")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a report")
    ap.add_argument("--only", metavar="ID", help="analyze a single sample by id")
    args = ap.parse_args(argv)

    if not SAMPLES.exists():
        print(f"error: {SAMPLES} not found", file=sys.stderr)
        return 2

    engine, source = _load_engine()
    samples = [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        samples = [s for s in samples if s["id"] == args.only]
        if not samples:
            print(f"error: no sample with id {args.only!r}", file=sys.stderr)
            return 2

    rows = [analyze_one(engine, s) for s in samples]
    if args.json:
        print(json.dumps({"engine": source, "rows": rows}, indent=2))
    else:
        _print_human(rows, source)
    return 1 if any(r["is_regression"] for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
