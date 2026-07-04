#!/usr/bin/env python3
"""Offline coverage check for the money-laundering GREP pack (propose-only second domain).

Before the ML layer is worth a grading run, it must FIRE on the adversarial ML prompts (so the harness
has indicators to ground with) and stay QUIET on benign finance questions (no over-flagging). This runs
the pack's compiled rules over the FULL adversarial + benign prompt sets -- no model calls -- and reports:

  * per-rule fire counts (adversarial and benign) -- a rule that fires on zero adversarial prompts is
    DEAD (its pattern is too narrow); a rule that fires on benign prompts is a FALSE POSITIVE risk;
  * adversarial prompt coverage -- the share of ML prompts with >=1 rule firing (the harness can only
    ground a prompt whose indicators it detects);
  * benign over-fire rate -- the share of benign finance questions that trip >=1 rule (should be ~0).

The point is to fix dead rules / false positives BEFORE any grading credits are spent on the second
domain. Deterministic; reads only committed config; no PII (synthetic prompts).

    python scripts/analyze_ml_grep_coverage.py
    python scripts/analyze_ml_grep_coverage.py --out docs/research/money_laundering_grep_coverage.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import money_laundering_grep_pack as ml  # noqa: E402

ADVERSARIAL = _ROOT / "configs" / "duecare" / "benchmarks" / "money_laundering_prompts.jsonl"
BENIGN = _ROOT / "configs" / "duecare" / "benchmarks" / "money_laundering_benign_controls.json"
OUT_DEFAULT = _ROOT / "docs" / "research" / "money_laundering_grep_coverage.md"


def _load_prompts(path: pathlib.Path) -> list[str]:
    """Prompt texts from a .jsonl (one obj per line) or a .json (list, or {"prompts": [...]})."""
    if not path.exists():
        return []
    if path.suffix == ".jsonl":
        rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc.get("prompts", doc) if isinstance(doc, dict) else doc
    return [str(r.get("text", "")) for r in rows if isinstance(r, dict) and r.get("text")]


def _fired_rules(text: str, compiled: list[dict]) -> set[str]:
    return {r["rule"] for r in compiled if any(rx.search(text) for rx in r["compiled"])}


def analyse(adversarial: list[str] | None = None, benign: list[str] | None = None,
            compiled: list[dict] | None = None) -> dict:
    compiled = ml.compiled_rules() if compiled is None else compiled
    adversarial = _load_prompts(ADVERSARIAL) if adversarial is None else adversarial
    benign = _load_prompts(BENIGN) if benign is None else benign

    per_rule = {r["rule"]: {"adv": 0, "benign": 0,
                            "severity": r.get("severity"), "citation": r.get("citation")}
                for r in compiled}
    adv_hit = 0
    for text in adversarial:
        fired = _fired_rules(text, compiled)
        adv_hit += 1 if fired else 0
        for rid in fired:
            per_rule[rid]["adv"] += 1
    benign_hit = 0
    for text in benign:
        fired = _fired_rules(text, compiled)
        benign_hit += 1 if fired else 0
        for rid in fired:
            per_rule[rid]["benign"] += 1

    dead = sorted(rid for rid, s in per_rule.items() if s["adv"] == 0)
    false_pos = sorted((rid for rid, s in per_rule.items() if s["benign"] > 0),
                       key=lambda rid: -per_rule[rid]["benign"])
    return {
        "n_rules": len(compiled), "n_adversarial": len(adversarial), "n_benign": len(benign),
        "adv_coverage_pct": round(100 * adv_hit / len(adversarial), 1) if adversarial else 0.0,
        "benign_overfire_pct": round(100 * benign_hit / len(benign), 1) if benign else 0.0,
        "adv_hit": adv_hit, "benign_hit": benign_hit,
        "per_rule": per_rule, "dead_rules": dead, "false_positive_rules": false_pos,
    }


def build_report(a: dict) -> str:
    o: list[str] = []
    o.append("# Money-laundering GREP pack -- offline coverage check (no model calls)\n")
    o.append("> Runs the propose-only ML GREP rules over the full adversarial + benign prompt sets "
             "(`money_laundering_prompts.jsonl`, `money_laundering_benign_controls.json`). Regenerate "
             "with `python scripts/analyze_ml_grep_coverage.py`. Deterministic; synthetic prompts only.\n")
    o.append(f"**{a['n_rules']} rules** over **{a['n_adversarial']} adversarial** + **{a['n_benign']} "
             f"benign** prompts. Adversarial coverage (>=1 rule fires): **{a['adv_coverage_pct']}%** "
             f"({a['adv_hit']}/{a['n_adversarial']}) -- higher is better, the harness can only ground a "
             f"detected prompt. Benign over-fire: **{a['benign_overfire_pct']}%** ({a['benign_hit']}/"
             f"{a['n_benign']}) -- lower is better, a rule tripping a legitimate finance question is a "
             "false positive.\n")

    if a["dead_rules"]:
        o.append(f"**Dead rules (fire on 0 adversarial prompts -- pattern too narrow, fix these): "
                 f"{len(a['dead_rules'])}** -- " + ", ".join(f"`{r}`" for r in a["dead_rules"]) + ".\n")
    else:
        o.append("**No dead rules** -- every rule fires on at least one adversarial prompt.\n")
    if a["false_positive_rules"]:
        o.append(f"**False-positive rules (fire on a benign prompt): {len(a['false_positive_rules'])}** -- "
                 + ", ".join(f"`{r}` ({a['per_rule'][r]['benign']})" for r in a["false_positive_rules"])
                 + ".\n")
    else:
        o.append("**No false positives** -- no rule fires on any benign finance question.\n")

    o.append("## Per-rule fire counts\n")
    o.append("| Rule | severity | adversarial fires | benign fires | citation |")
    o.append("|---|---|---:|---:|---|")
    for rid in sorted(a["per_rule"], key=lambda r: (-a["per_rule"][r]["adv"], r)):
        s = a["per_rule"][rid]
        flag = " (dead)" if s["adv"] == 0 else (" (FP)" if s["benign"] else "")
        o.append(f"| `{rid}`{flag} | {s['severity']} | {s['adv']} | {s['benign']} | {s['citation']} |")
    o.append("")
    o.append("## Reading\n")
    o.append("- High adversarial coverage + ~0% benign over-fire means the ML layer is ready for a scored "
             "run (it fires where it should and stays quiet where it should).\n"
             "- **Adversarial coverage is partly circular by construction.** The adversarial prompts were "
             "generated from these rules and embed the indicator LABEL text, so a label-matching pattern "
             "fires on them almost by definition. 100% here means the pack is internally consistent with "
             "its own prompt set -- NOT that it would catch the same schemes phrased freely in the wild "
             "(real adversarial language is more varied). The **benign over-fire rate is the more "
             "informative number**: the benign set was written independently as legitimate finance "
             "questions, so a low over-fire is a genuine specificity signal, not circular.\n"
             "- Dead rules are not wrong, just inert on this prompt set -- widen the pattern or add prompts "
             "that exercise the indicator before relying on it.\n"
             "- Every mapping here stays **propose-only** until an AML expert validates it; this check is a "
             "readiness gate, not a correctness claim.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args(argv)
    a = analyse()
    if not a["n_adversarial"]:
        print(f"no adversarial prompts at {ADVERSARIAL} -- nothing to analyse", file=sys.stderr)
        return 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(a), encoding="utf-8")
    print(f"wrote {out} | {a['n_rules']} rules, adv coverage {a['adv_coverage_pct']}%, "
          f"benign over-fire {a['benign_overfire_pct']}%, dead {len(a['dead_rules'])}, "
          f"FP {len(a['false_positive_rules'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
