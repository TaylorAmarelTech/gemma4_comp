#!/usr/bin/env python3
"""Deterministic, model-free verification over the FULL response registry.

The cloud judge panel is rate-limited, so it has only graded a subset of the
registry. The deterministic `duecare.kit.verify` checker needs no model and no
network, so it can score EVERY generated response pair. This produces a
full-coverage, un-gameable corroboration table (baseline vs harness_core) plus a
compact CSV suitable for external review.

    python scripts/deterministic_full_registry.py                       # gemma4:31b
    python scripts/deterministic_full_registry.py --model gpt-oss:120b

Outputs (under reports/external_review/):
  * deterministic_verify_<model>.csv     -- one row per prompt (scores + A-E flags, both arms)
  * deterministic_verify_<model>.summary.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "duecare-llm-kit" / "src"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="reports/rich_lift/results.jsonl")
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--arm", default="harness_core")
    ap.add_argument("--outdir", default="reports/external_review")
    args = ap.parse_args(argv)

    from duecare.kit.verify import verify

    arms = {"baseline", args.arm}
    recs: dict = defaultdict(dict)
    with open(args.results, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("model") != args.model or r.get("arm") not in arms:
                continue
            recs[r["prompt_id"]][r["arm"]] = {"p": r["prompt_text"], "r": r["response"]}

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    slug = args.model.replace(":", "_").replace("/", "_")
    csv_path = outdir / f"deterministic_verify_{slug}.csv"

    crit = "ABCDE"
    header = (["prompt_id", "model", "base_score_0_5", "core_score_0_5", "lift_0_5"]
              + [f"base_{k}" for k in crit] + [f"core_{k}" for k in crit])
    n = 0
    sb = sc = 0.0
    reg = defaultdict(int)
    score_reg = 0
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for pid, v in recs.items():
            if len(v) != 2:
                continue
            vb = verify(v["baseline"]["p"], v["baseline"]["r"])
            vc = verify(v[args.arm]["p"], v[args.arm]["r"])
            n += 1
            sb += vb["score_0_5"]
            sc += vc["score_0_5"]
            if vc["score_0_5"] < vb["score_0_5"]:
                score_reg += 1
            for k in crit:
                if vb[k] and not vc[k]:
                    reg[k] += 1
            w.writerow([pid, args.model, vb["score_0_5"], vc["score_0_5"], vc["score_0_5"] - vb["score_0_5"]]
                       + [int(vb[k]) for k in crit] + [int(vc[k]) for k in crit])

    summary = outdir / f"deterministic_verify_{slug}.summary.md"
    lines = [
        f"# Deterministic full-registry verification -- {args.model}",
        "",
        "Model-free `duecare.kit.verify` scored on every generated (baseline, "
        f"{args.arm}) response pair. No judge model, no network -- fully reproducible.",
        "",
        f"- paired prompts scored: **{n:,}**",
        f"- deterministic mean score: baseline **{sb/n:.3f}/5** -> {args.arm} **{sc/n:.3f}/5** "
        f"(**{sc/n - sb/n:+.3f}** lift)",
        f"- score regressions ({args.arm} < baseline): **{score_reg:,}** ({100*score_reg/n:.2f}%)",
        "",
        "## Per-criterion regressions (baseline passed, harness failed)",
        "",
        "| criterion | meaning | regressions |",
        "|---|---|---|",
        f"| A | indicator surfaced | {reg['A']:,} |",
        f"| B | legal citation | {reg['B']:,} |",
        f"| C | refusal + redirect | {reg['C']:,} |",
        f"| D | resource routing | {reg['D']:,} |",
        f"| E | privacy clean | {reg['E']:,} |",
        "",
        f"CSV: `{csv_path.as_posix()}` ({n:,} rows). Regenerate: "
        f"`python scripts/deterministic_full_registry.py --model {args.model}`.",
    ]
    summary.write_text("\n".join(lines), encoding="utf-8")
    print(f"DONE n={n} base={sb/n:.3f} core={sc/n:.3f} lift={sc/n - sb/n:+.3f} "
          f"score_reg={score_reg} crit={{k:reg[k] for k in crit}}")
    print(f"csv -> {csv_path}  ({csv_path.stat().st_size//1024} KB)")
    print(f"summary -> {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
