#!/usr/bin/env python3
"""Review the cases where the harness HURT (harnessed score < baseline).

Offline, model-free triage of the negative-lift tail: it pairs an arm against
baseline in the per-dimension panel, finds the prompts where the harness scored
LOWER, shows which A-E dimension dropped, then pulls the actual prompt + both
responses from results.jsonl and re-scores them with the DETERMINISTIC verifier
(duecare.kit.verify) so you can tell a real content regression from a judge
preference on ordering/verbosity.

    python scripts/review_harness_hurts.py                # gemma4:31b, harness_core vs baseline
    python scripts/review_harness_hurts.py --model gpt-oss:120b --arm harness_full
    python scripts/review_harness_hurts.py --out docs/research/harness_hurts_review.md

No model, no network. Needs the kit importable (repo src is added to sys.path).
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "duecare-llm-kit" / "src"))


def _load_panel(panel: Path, model: str, arm: str):
    scores: dict = defaultdict(list)
    comps: dict = defaultdict(lambda: defaultdict(list))
    with panel.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("model") != model or r.get("arm") not in ("baseline", arm):
                continue
            key = (r["prompt_id"], r["arm"])
            scores[key].append(float(r["score_0_100"]))
            for k, v in (r.get("components") or {}).items():
                comps[key][k].append(float(v))
    return scores, comps


def _pair(scores, comps, arm):
    pids = sorted({pid for (pid, a) in scores})
    rows = []
    for pid in pids:
        if (pid, "baseline") not in scores or (pid, arm) not in scores:
            continue
        b = st.mean(scores[(pid, "baseline")])
        c = st.mean(scores[(pid, arm)])
        dims = {}
        for k in "ABCDE":
            bv = comps[(pid, "baseline")].get(k)
            cv = comps[(pid, arm)].get(k)
            if bv and cv:
                dims[k] = round(st.mean(cv) - st.mean(bv), 1)
        rows.append({"pid": pid, "base": round(b, 1), "arm": round(c, 1),
                     "lift": round(c - b, 1), "dims": dims})
    rows.sort(key=lambda x: x["lift"])
    return rows


def _pull_text(results: Path, model: str, arm: str, pids: set):
    want = {(p, a) for p in pids for a in ("baseline", arm)}
    got: dict = {}
    with results.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            k = (r.get("prompt_id"), r.get("arm"))
            if r.get("model") == model and k in want:
                got[k] = {"prompt": r["prompt_text"], "response": r["response"]}
                if len(got) >= len(want):
                    break
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", default="reports/rich_lift/panel_perdim.jsonl")
    ap.add_argument("--results", default="reports/rich_lift/results.jsonl")
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--arm", default="harness_core")
    ap.add_argument("--out", default=None, help="write a markdown report here")
    args = ap.parse_args(argv)

    from duecare.kit.verify import verify

    scores, comps = _load_panel(Path(args.panel), args.model, args.arm)
    rows = _pair(scores, comps, args.arm)
    hurts = [r for r in rows if r["lift"] < 0]
    if not rows:
        print(f"no paired rows for model={args.model} arm={args.arm}")
        return 1

    got = _pull_text(Path(args.results), args.model, args.arm, {r["pid"] for r in hurts})

    det_base = det_arm = 0.0
    d_lost = d_gained = d_tied = 0
    for r in hurts:
        b = got.get((r["pid"], "baseline"))
        c = got.get((r["pid"], args.arm))
        if not (b and c):
            r["det"] = None
            continue
        vb = verify(b["prompt"], b["response"])
        vc = verify(c["prompt"], c["response"])
        r["det"] = {"base": vb["score_0_5"], "arm": vc["score_0_5"], "D_base": vb["D"], "D_arm": vc["D"]}
        det_base += vb["score_0_5"]
        det_arm += vc["score_0_5"]
        if vb["D"] and not vc["D"]:
            d_lost += 1
        elif vc["D"] and not vb["D"]:
            d_gained += 1
        else:
            d_tied += 1

    n = len(hurts)
    scored = [r for r in hurts if r.get("det")]
    dim_drops = defaultdict(int)
    for r in hurts:
        for k, v in r["dims"].items():
            if v < 0:
                dim_drops[k] += 1

    print(f"model={args.model}  arm={args.arm} vs baseline")
    print(f"paired={len(rows)}  hurts(<0)={n}  mean_lift=+{st.mean([r['lift'] for r in rows]):.1f}")
    print(f"dimension most often dropped on hurts: {dict(sorted(dim_drops.items(), key=lambda x: -x[1]))}")
    if scored:
        print(f"DETERMINISTIC verify on the {len(scored)} hurts: baseline={det_base/len(scored):.2f}/5  "
              f"{args.arm}={det_arm/len(scored):.2f}/5  (D: lost={d_lost} gained={d_gained} tied={d_tied})")
        verdict = ("mostly JUDGE-PREFERENCE (ordering/verbosity) -- harness content is equal-or-better"
                   if det_arm >= det_base else "possible real content regression -- inspect")
        print(f"verdict: {verdict}")

    if args.out:
        out = Path(args.out)
        lines = [f"# Harness-hurts review -- {args.model} ({args.arm} vs baseline)", ""]
        lines.append(f"- paired prompts: **{len(rows)}**, hurts (<0): **{n}**, "
                     f"mean lift **+{st.mean([r['lift'] for r in rows]):.1f}**")
        if scored:
            lines.append(f"- deterministic verify on the hurts: baseline **{det_base/len(scored):.2f}/5** -> "
                         f"{args.arm} **{det_arm/len(scored):.2f}/5** (D lost={d_lost}, gained={d_gained}, tied={d_tied})")
        lines += ["", "| pid | base | arm | lift | dropped dims | det base/arm |", "|---|---|---|---|---|---|"]
        for r in hurts:
            dd = ", ".join(f"{k}{v:+g}" for k, v in r["dims"].items() if v < 0) or "-"
            det = f"{r['det']['base']}->{r['det']['arm']}" if r.get("det") else "n/a"
            lines.append(f"| {r['pid']} | {r['base']} | {r['arm']} | {r['lift']:+g} | {dd} | {det} |")
        lines += ["", "## Golden hurts set (freeze; re-check after any harness change)", "",
                  "```json", json.dumps([r["pid"] for r in hurts]), "```", ""]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
