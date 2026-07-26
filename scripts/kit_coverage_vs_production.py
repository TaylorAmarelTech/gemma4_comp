#!/usr/bin/env python3
# ruff: noqa: E501  (report-rendering script; long prose f-strings)
"""How much of the production GREP layer does the compact kit engine actually reproduce?

The published `duecare-llm-kit` ships a COMPACT indicator engine so a Kaggle notebook stays
self-contained and stdlib-only. Every doc calls it "a representative subset of the real GREP layer
(451 rules across 11+ languages)" -- but *representative* was prose, never a number. A reader
deciding whether to rely on the kit deserves the measurement.

This measures it on the recorded corpus, deterministically and offline:

  * production -- ``duecare.chat.harness._grep_call`` (456 rules / 1,037 patterns incl. multilingual)
  * compact    -- ``scripts/_usecase_engine.py`` ``scan()`` (the kit's embedded engine)

Both layers run over the SAME texts. Their output vocabularies differ (production emits 456 rule
IDs, the compact engine emits 12 ILO indicator keys), so indicator-level equality is not meaningful.
The honest comparison is at the TEXT level -- does each layer flag this text at all -- plus a ranked
list of which production rules fire on texts the compact engine misses. That ranking is the
evidence-based backlog for what to port next.

Run:
    python scripts/kit_coverage_vs_production.py --limit 3000
    python scripts/kit_coverage_vs_production.py --limit 500 --json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
SHOWCASE = _ROOT / "packages" / "duecare-llm-kit" / "tests" / "fixtures" / "showcase_sample.jsonl"
OUT = _ROOT / "docs" / "research" / "kit_coverage_vs_production.md"
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def _label(path: Path) -> str:
    """Repo-relative label; anything outside the repo collapses to its bare filename."""
    try:
        return path.resolve().relative_to(_ROOT).as_posix()
    except (ValueError, OSError):
        return path.name


def load_production_grep():
    """The real harness GREP entry point (456 rules incl. the multilingual pack)."""
    sys.path.insert(0, str(_ROOT / "packages" / "duecare-llm-chat" / "src"))
    from duecare.chat.harness import _grep_call  # noqa: PLC0415
    return _grep_call


def load_compact_scan():
    """The kit's embedded compact engine, loaded from the ENGINE source of truth."""
    src = (_ROOT / "scripts" / "_usecase_engine.py").read_text(encoding="utf-8")
    holder: dict = {}
    exec(compile(src, "<usecase_engine>", "exec"), holder)  # noqa: S102
    ns: dict = {}
    exec(holder["ENGINE"], ns)  # noqa: S102
    return ns["scan"]


def collect_texts(limit: int, *, results: Path = RESULTS, showcase: Path = SHOWCASE) -> list[str]:
    """Recorded model responses, plus the committed showcase fields, as the evaluation corpus."""
    texts: list[str] = []
    if showcase.exists():
        for line in showcase.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            texts += [v for v in (r.get("prompt_text"), r.get("baseline_response"),
                                  r.get("harness_core_response")) if isinstance(v, str) and v.strip()]
    if results.exists():
        with results.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= limit:
                    break
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(r.get("response"), str) and r["response"].strip():
                    texts.append(r["response"])
    return texts


def measure(texts, grep_call, scan) -> dict:
    """Text-level agreement plus the ranked list of production rules the compact engine misses."""
    both = prod_only = compact_only = neither = 0
    missed_rules: collections.Counter = collections.Counter()
    missed_sev: collections.Counter = collections.Counter()
    rule_sev: dict[str, str] = {}
    prod_rule_total: collections.Counter = collections.Counter()

    for t in texts:
        p_hits = grep_call(t).get("hits", [])
        c_hits = scan(t)
        for h in p_hits:
            prod_rule_total[h["rule"]] += 1
            rule_sev.setdefault(h["rule"], str(h.get("severity", "")).lower())
        p, c = bool(p_hits), bool(c_hits)
        if p and c:
            both += 1
        elif p and not c:
            prod_only += 1
            for h in p_hits:
                missed_rules[h["rule"]] += 1
                missed_sev[str(h.get("severity", "")).lower()] += 1
        elif c and not p:
            compact_only += 1
        else:
            neither += 1

    prod_fired = both + prod_only
    return {
        "n_texts": len(texts),
        "production_fired": prod_fired,
        "compact_fired": both + compact_only,
        "both": both,
        "production_only": prod_only,
        "compact_only": compact_only,
        "neither": neither,
        # The headline: when production flags a text, how often does the compact engine agree?
        "compact_recall_vs_production_pct": round(100.0 * both / prod_fired, 1) if prod_fired else None,
        # Every observed severity is reported, not a fixed high/medium/low subset: the rule set also
        # uses "info", and silently dropping a bucket would understate what the compact engine misses.
        "missed_severity": {s: missed_sev[s] for s in
                            sorted(missed_sev, key=lambda s: (SEVERITY_ORDER.index(s)
                                                              if s in SEVERITY_ORDER else len(SEVERITY_ORDER), s))},
        "top_missed_rules": [
            {"rule": r, "missed_texts": n, "severity": rule_sev.get(r, ""),
             "total_fires": prod_rule_total[r]}
            for r, n in missed_rules.most_common(25)
        ],
    }


def render(m: dict, *, today: str, limit: int) -> str:
    if not m["n_texts"]:
        return (f"# Kit coverage vs the production GREP layer -- {today}\n\n"
                f"No texts available to scan. Ensure `{_label(RESULTS)}` exists.\n")
    recall = m["compact_recall_vs_production_pct"]
    sev = m["missed_severity"]
    rows = "\n".join(
        f"| `{r['rule']}` | {r['severity'] or 'n/a'} | {r['missed_texts']:,} | {r['total_fires']:,} |"
        for r in m["top_missed_rules"]) or "| _(none -- compact caught every flagged text)_ | | | |"
    return f"""# Kit coverage vs the production GREP layer ({today})

Generated by `scripts/kit_coverage_vs_production.py`. Deterministic and fully offline -- it runs two
rule engines over recorded text and **calls no model**.

## Why this exists

The published `duecare-llm-kit` embeds a COMPACT indicator engine so a Kaggle notebook stays
self-contained and stdlib-only. Every doc describes it as "a representative subset of the real GREP
layer (451 rules across 11+ languages)". *Representative* was prose. This is the number.

## What was compared

| layer | implementation | scope |
|---|---|---|
| production | `duecare.chat.harness._grep_call` | 456 rules / 1,037 patterns (incl. the multilingual pack) |
| compact | `scan()` from `scripts/_usecase_engine.py` (the kit's embedded `ENGINE`) | 12 ILO indicator keys |

Corpus: **{m['n_texts']:,} recorded texts** -- the committed showcase fields plus up to {limit:,}
model responses streamed from `{_label(RESULTS)}`.

The two layers speak different vocabularies (456 rule IDs vs 12 ILO indicator keys), so
indicator-level equality is not a meaningful test. The comparison is at the **text level** -- does
each layer flag this text at all.

## Result

| | production flags | production silent |
|---|---:|---:|
| **compact flags** | {m['both']:,} | {m['compact_only']:,} |
| **compact silent** | {m['production_only']:,} | {m['neither']:,} |

- **Compact recall vs production: {recall}%** -- of the {m['production_fired']:,} texts the
  production layer flags, the compact engine independently flags {m['both']:,}.
- **{m['compact_only']:,} texts** are flagged by the compact engine but not production. These are not
  necessarily false positives: the compact engine's ILO-indicator patterns and the production rule
  set were authored separately, so this is genuine complementary coverage worth triaging.
- Severity of the production hits on missed texts: {', '.join(f"**{k} {v:,}**" if k in ('critical', 'high') else f"{k} {v:,}" for k, v in sev.items()) or 'none'}.
  The `critical` and `high` buckets are the ones that matter: those are texts the production layer
  treats as acute and the kit reports as clean.

## The ranked port backlog

Production rules that fire most often on texts the compact engine misses. This is the
evidence-ordered list of what to port into the kit next -- highest-frequency, highest-severity first.

| production rule | severity | fires on missed texts | total fires in corpus |
|---|---|---:|---:|
{rows}

## How to read this honestly

1. A high recall number does **not** make the kit equivalent to production. Production returns the
   specific rule, its severity, and a legal citation; the compact engine returns one of 12 ILO
   indicator keys. Same alarm, far less detail.
2. Text-level agreement is the *loosest* comparison. Two layers can both flag a text for entirely
   different reasons. Treat this as an upper bound on kit fidelity, not a guarantee.
3. `compact silent / production silent` is the large cell in most corpora; the interesting numbers
   are the off-diagonals, not the raw agreement rate.
4. Deployments that need the full rule set, citations, and 11+ language coverage should run the
   production harness, not the kit. The kit is for reproducible notebooks and offline demos.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure compact kit engine coverage against the production GREP layer.")
    ap.add_argument("--limit", type=int, default=3000, help="max recorded responses to stream (default 3000)")
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--showcase", type=Path, default=SHOWCASE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--today", default=datetime.now(UTC).date().isoformat())
    ap.add_argument("--json", action="store_true", help="print the summary as JSON and write no report")
    args = ap.parse_args(argv)

    texts = collect_texts(args.limit, results=args.results, showcase=args.showcase)
    m = measure(texts, load_production_grep(), load_compact_scan())

    if args.json:
        print(json.dumps({"generated": args.today, **m}, indent=2, sort_keys=True))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(m, today=args.today, limit=args.limit), encoding="utf-8")
    print(f"{m['n_texts']:,} texts | production fired {m['production_fired']:,} | "
          f"compact recall {m['compact_recall_vs_production_pct']}% | "
          f"compact-only {m['compact_only']:,} | missed-high {m['missed_severity'].get('high', 0):,} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
