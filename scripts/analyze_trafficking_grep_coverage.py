#!/usr/bin/env python3
"""Offline coverage / dead-rule check for the PRIMARY trafficking GREP pack (no model calls).

The trafficking harness ships 451 GREP indicator rules -- the layer the whole harness lift leans on.
A rule whose pattern is too narrow to ever match a real prompt is dead weight: it adds maintenance
surface and citation clutter without ever grounding a reply. This runs the harness's OWN matcher
(``duecare.chat.harness._grep_call`` logic, faithfully re-implemented with precompiled patterns so it is
fast over the whole corpus, and so it honours ``min_capture_value`` + ``all_required`` exactly) over the
benchmark prompt set and reports:

  * per-rule fire counts -- rules that fire on ZERO prompts are DEAD (fix or prune the pattern);
  * prompt coverage -- the share of prompts with >=1 rule firing (the harness can only ground what it
    detects), and the mean number of rules per prompt;
  * a per-severity dead breakdown, and the benign-control fire rate (context-dependent for this domain:
    a worker describing passport retention SHOULD trip an indicator, so this is reported, not judged).

Deterministic; reads only committed data; synthetic prompts, no PII (rule / severity labels only).

    python scripts/analyze_trafficking_grep_coverage.py             # 15k-prompt sample (default, ~2.5 min)
    python scripts/analyze_trafficking_grep_coverage.py --sample 0  # full corpus (~13 min)
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _src in (_ROOT / "packages").glob("*/src"):
    sys.path.insert(0, str(_src))
sys.path.insert(0, str(_ROOT / "scripts"))

from duecare.chat.harness import GREP_RULES  # noqa: E402

PROMPTSET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
BENIGN = _ROOT / "configs" / "duecare" / "benchmarks" / "benign_control_prompts.json"
OUT_DEFAULT = _ROOT / "docs" / "research" / "trafficking_grep_coverage.md"


def compile_rules(rules: list[dict]) -> list[dict]:
    """Precompile each rule's patterns once (re cache is 512; ~900 patterns would thrash otherwise)."""
    out = []
    for r in rules:
        try:
            compiled = [re.compile(p, re.IGNORECASE) for p in (r.get("patterns") or [])]
        except re.error:
            compiled = []          # a rule with a bad regex cannot fire; surfaces as dead
        out.append({"rule": r["rule"], "severity": r.get("severity"),
                    "compiled": compiled, "min_capture": r.get("min_capture_value"),
                    "all_required": bool(r.get("all_required", False))})
    return out


def fired_rules(text: str, compiled: list[dict]) -> set[str]:
    """Mirror of harness._grep_call's match logic (ANY-match by default, all_required + min_capture)."""
    if not text or not text.strip():
        return set()
    hits: set[str] = set()
    for r in compiled:
        matched = False
        all_matched = True
        for rx in r["compiled"]:
            m = rx.search(text)
            if m is None:
                all_matched = False
                continue
            if r["min_capture"] is not None and m.groups():
                try:
                    if int(m.group(1)) < r["min_capture"]:
                        all_matched = False
                        continue
                except (ValueError, IndexError):
                    pass
            matched = True
        if r["all_required"] and not all_matched:
            continue
        if not matched:
            continue
        hits.add(r["rule"])
    return hits


def _load_prompts(path: pathlib.Path, sample: int) -> list[str]:
    if not path.exists():
        return []
    if path.suffix == ".jsonl":
        rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc.get("prompts", doc) if isinstance(doc, dict) else doc
    texts = [str(r.get("text", "")) for r in rows if isinstance(r, dict) and r.get("text")]
    if sample and len(texts) > sample:
        # deterministic evenly-spaced subsample (no RNG -- reproducible)
        step = len(texts) / sample
        texts = [texts[int(i * step)] for i in range(sample)]
    return texts


def analyse(prompts: list[str] | None = None, benign: list[str] | None = None,
            rules: list[dict] | None = None, sample: int = 0) -> dict:
    compiled = compile_rules(GREP_RULES if rules is None else rules)
    prompts = _load_prompts(PROMPTSET, sample) if prompts is None else prompts
    benign = _load_prompts(BENIGN, 0) if benign is None else benign

    per_rule: collections.Counter = collections.Counter()
    per_rule_benign: collections.Counter = collections.Counter()
    rules_per_prompt = []
    covered = 0
    for text in prompts:
        fired = fired_rules(text, compiled)
        rules_per_prompt.append(len(fired))
        covered += 1 if fired else 0
        for rid in fired:
            per_rule[rid] += 1
    for text in benign:
        for rid in fired_rules(text, compiled):
            per_rule_benign[rid] += 1

    sev = {r["rule"]: r["severity"] for r in compiled}
    empty_pattern = {r["rule"] for r in compiled if not r["compiled"]}
    dead = sorted(r["rule"] for r in compiled if per_rule[r["rule"]] == 0)
    dead_by_sev = collections.Counter(sev.get(rid) for rid in dead)
    n = len(prompts) or 1
    return {
        "n_rules": len(compiled), "n_prompts": len(prompts), "n_benign": len(benign),
        "coverage_pct": round(100 * covered / n, 1),
        "mean_rules_per_prompt": round(sum(rules_per_prompt) / n, 2),
        "dead_rules": dead, "dead_by_severity": dict(dead_by_sev),
        "empty_pattern_rules": sorted(empty_pattern),
        "top_rules": per_rule.most_common(15),
        "benign_fire": per_rule_benign.most_common(10),
        "severity": sev,
    }


def build_report(a: dict) -> str:
    o: list[str] = []
    o.append("# Primary trafficking GREP pack -- coverage / dead-rule check (offline, no model calls)\n")
    o.append(f"> Runs the harness's {a['n_rules']}-rule matcher over **{a['n_prompts']:,}** benchmark "
             "prompts (`reports/benchmark/full_promptset.json`). Regenerate with "
             "`python scripts/analyze_trafficking_grep_coverage.py`. Synthetic prompts; rule labels only.\n")
    o.append(f"**{a['n_rules']} rules.** Prompt coverage (>=1 rule fires): **{a['coverage_pct']}%**; mean "
             f"**{a['mean_rules_per_prompt']}** rules fire per prompt. **Rules that never fire on this "
             f"promptset: {len(a['dead_rules'])}**"
             + (f" -- by severity {a['dead_by_severity']}." if a["dead_rules"] else " -- none.") + "\n")
    o.append("> Two non-exclusive reads of a never-firing rule, and they need different fixes: (a) a "
             "**benchmark coverage gap** -- the promptset has no prompt that exercises that indicator, so "
             "the benchmark under-tests the harness's own rule library (fix: add prompts); or (b) an "
             "**over-narrow / stale rule** that would not fire on realistic worker text either (fix: "
             "widen or prune). The GREP rules are built to fire on real worker chat / documents, and the "
             "benchmark's adversarial *scheme* prompts are a different distribution, so some non-firing "
             "is expected -- but this many (incl. high/critical severities) is worth a review pass.\n")
    if a["empty_pattern_rules"]:
        o.append(f"**Rules with an uncompilable/empty pattern (cannot ever fire): "
                 f"{len(a['empty_pattern_rules'])}** -- "
                 + ", ".join(f"`{r}`" for r in a["empty_pattern_rules"][:20]) + ".\n")

    if a["dead_rules"]:
        o.append("## Rules that never fire on this promptset (coverage gap OR over-narrow)\n")
        o.append("| Rule | severity |")
        o.append("|---|---|")
        for rid in a["dead_rules"][:60]:
            o.append(f"| `{rid}` | {a['severity'].get(rid)} |")
        if len(a["dead_rules"]) > 60:
            o.append(f"| … +{len(a['dead_rules']) - 60} more | |")
        o.append("")

    o.append("## Most-fired rules (the workhorses)\n")
    o.append("| Rule | fires | severity |")
    o.append("|---|---:|---|")
    for rid, c in a["top_rules"]:
        o.append(f"| `{rid}` | {c:,} | {a['severity'].get(rid)} |")
    o.append("")

    if a["benign_fire"]:
        o.append("## Fires on the benign worker-question controls (context-dependent, NOT auto-a-bug)\n")
        o.append(f"Over {a['n_benign']} benign controls. For trafficking, a benign worker question can "
                 "*legitimately* trip an indicator (a worker describing passport retention SHOULD), so "
                 "this is reported for review, not scored as a false positive the way the ML domain is.\n")
        o.append("| Rule | benign fires | severity |")
        o.append("|---|---:|---|")
        for rid, c in a["benign_fire"]:
            o.append(f"| `{rid}` | {c} | {a['severity'].get(rid)} |")
        o.append("")

    o.append("## Reading\n")
    o.append("- The never-firing list is a **prioritized worklist**: triage the high/critical rules first "
             "-- either add benchmark prompts that exercise the indicator (closing a coverage gap) or "
             "widen/prune the rule (if it would not fire on realistic worker text either).\n"
             "- A rule with an uncompilable/empty pattern is a latent bug: it can never fire, full stop.\n"
             "- The benign-control fires are context-dependent for trafficking (a worker describing "
             "passport retention SHOULD trip an indicator) -- reviewed, not auto-scored as false "
             "positives the way the money-laundering domain's compliance-question controls are.\n"
             "- High coverage + several rules per prompt is the healthy signal the lift leans on.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=15000,
                    help="subsample N prompts for speed (0 = full corpus, ~13 min; deterministic)")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args(argv)
    a = analyse(sample=args.sample)
    if not a["n_prompts"]:
        print(f"no prompts at {PROMPTSET} -- nothing to analyse", file=sys.stderr)
        return 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(a), encoding="utf-8")
    print(f"wrote {out} | {a['n_rules']} rules over {a['n_prompts']:,} prompts, coverage "
          f"{a['coverage_pct']}%, dead {len(a['dead_rules'])}, empty-pattern "
          f"{len(a['empty_pattern_rules'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
