#!/usr/bin/env python3
"""Cross-model deterministic verification board over the generated response set.

One streaming pass over results.jsonl. For every model, it pairs each prompt's
baseline and harness_core responses and scores both with the model-free
`duecare.kit.verify` checker, then reports the per-model deterministic lift. No
judge model, no network, no Ollama. Coverage is whatever responses exist per
model (only some models have the full registry), so the `n` column is the honest
guard on how far to trust each row.

    python scripts/cross_model_deterministic.py
    python scripts/cross_model_deterministic.py --results reports/rich_lift/results.jsonl

Writes docs/external_review/cross_model_deterministic_leaderboard.csv.
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
    ap.add_argument("--outdir", default="docs/external_review")
    args = ap.parse_args(argv)

    from duecare.kit.verify import verify

    arms = {"baseline", "harness_core"}
    pending: dict = {}
    agg = defaultdict(lambda: {"n": 0, "sb": 0.0, "sc": 0.0, "reg": 0})
    with open(args.results, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("arm") not in arms:
                continue
            k = (r["model"], r["prompt_id"])
            pending.setdefault(k, {})[r["arm"]] = {"p": r["prompt_text"], "r": r["response"]}
            d = pending[k]
            if "baseline" in d and "harness_core" in d:
                vb = verify(d["baseline"]["p"], d["baseline"]["r"])
                vc = verify(d["harness_core"]["p"], d["harness_core"]["r"])
                a = agg[r["model"]]
                a["n"] += 1; a["sb"] += vb["score_0_5"]; a["sc"] += vc["score_0_5"]
                if vc["score_0_5"] < vb["score_0_5"]:
                    a["reg"] += 1
                del pending[k]

    board = []
    for m, a in agg.items():
        if a["n"] == 0:
            continue
        board.append({
            "model": m, "n": a["n"],
            "det_base_0_5": round(a["sb"]/a["n"], 3),
            "det_core_0_5": round(a["sc"]/a["n"], 3),
            "det_lift_0_5": round((a["sc"]-a["sb"])/a["n"], 3),
            "score_regression_pct": round(100*a["reg"]/a["n"], 2),
        })
    board.sort(key=lambda x: -x["det_lift_0_5"])

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "cross_model_deterministic_leaderboard.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "n", "det_base_0_5", "det_core_0_5",
                                           "det_lift_0_5", "score_regression_pct"])
        w.writeheader()
        for row in board:
            w.writerow(row)
    for b in board:
        print(f"  {b['model']:22s} n={b['n']:6d}  {b['det_base_0_5']:.3f} -> "
              f"{b['det_core_0_5']:.3f}  (+{b['det_lift_0_5']:.3f})  reg={b['score_regression_pct']}%")
    print(f"wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
