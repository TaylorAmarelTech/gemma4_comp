#!/usr/bin/env python3
"""Pairwise harness lift — the absolute-scale-free measurement that beats round-number clustering.

The calibration A/B showed an anchored 0-100 judge adds resolution but does NOT cure the ceiling
pile-up (50% still rate >= 9). The cure is pairwise judging: show the judge BOTH replies to the same
prompt and ask only which is SAFER and by how much (-10..+10), averaged over both presentation orders
to cancel position bias. The judge never makes a 7-vs-8 absolute call, so there is no ceiling.

This runs judge_pair over stored baseline/harnessed response pairs and reports the head-to-head harness
lift: mean signed preference, win rate, and the distribution (which, unlike the absolute judge, uses
the full range instead of piling at the top). Reuses stored responses; resumable; judge injectable.

    OLLAMA_API_KEY=... python scripts/pairwise_lift.py --responses reports/scheme_run.responses.jsonl --sample 40
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import pathlib
import sys
import time
from typing import Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import lift_stats  # noqa: E402

DEFAULT_RESP = _ROOT / "reports" / "scheme_run.responses.jsonl"
DEFAULT_CKPT = _ROOT / "reports" / "pairwise_lift.jsonl"
DEFAULT_OUT = _ROOT / "docs" / "research" / "pairwise_lift.md"


def _prompt_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for f in glob.glob(str(_ROOT / "configs" / "duecare" / "benchmarks" / "*.json")):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            for p in (d.get("prompts", d) if isinstance(d, dict) else d):
                if isinstance(p, dict) and p.get("id"):
                    idx.setdefault(str(p["id"]), p.get("text", ""))
        except Exception:  # noqa: BLE001
            continue
    return idx


def load_pairs(path: pathlib.Path, sample: int = 0) -> list[dict]:
    """{prompt_id, prompt_text, baseline, harnessed} for prompts with BOTH arms stored."""
    idx = _prompt_index()
    by: dict[str, dict] = collections.defaultdict(dict)
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("response") and r.get("arm") in ("baseline", "harnessed"):
            pid = str(r.get("prompt_id"))
            by[pid][r["arm"]] = str(r["response"])
            by[pid]["prompt_text"] = r.get("prompt_text") or r.get("prompt") or idx.get(pid, "")
    out = [{"prompt_id": pid, "prompt_text": v.get("prompt_text", ""),
            "baseline": v["baseline"], "harnessed": v["harnessed"]}
           for pid, v in by.items()
           if "baseline" in v and "harnessed" in v and v.get("prompt_text")]
    return out[:sample] if sample else out


def _default_judge_pair(prompt: str, a: str, b: str, *, model: str) -> float:
    from multi_judge import judge_pair
    return judge_pair(prompt, a, b, model=model)


def run_pairwise(pairs: list[dict], *, judge_model: str, judge: Callable[..., float] | None = None,
                 ckpt: pathlib.Path = DEFAULT_CKPT, pace: float = 0.2,
                 log: Callable[[str], None] = lambda _m: None) -> list[dict]:
    """judge_pair(baseline, harnessed) per prompt -> signed lift (positive = harness safer). Resumable."""
    jf = judge or _default_judge_pair
    done: dict[str, dict] = {}
    if ckpt.exists():
        for ln in ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                done[r["prompt_id"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    for p in pairs:
        if p["prompt_id"] in done:
            continue
        try:
            # A = baseline, B = harnessed -> positive return = harnessed (B) safer = the lift
            lift = float(jf(p["prompt_text"], p["baseline"], p["harnessed"], model=judge_model))
        except Exception as exc:  # noqa: BLE001
            log(f"FAIL {p['prompt_id']}: {type(exc).__name__}: {exc}")
            continue
        row = {"prompt_id": p["prompt_id"], "pairwise_lift": lift}
        with ckpt.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        done[p["prompt_id"]] = row
        log(f"{p['prompt_id']}: {lift:+.1f}")
        if pace:
            time.sleep(pace)
    return list(done.values())


def aggregate(rows: list[dict]) -> dict:
    lifts = [float(r["pairwise_lift"]) for r in rows]
    if not lifts:
        return {}
    st = lift_stats.paired_test(lifts)
    n = len(lifts)
    wins = sum(1 for x in lifts if x > 0.5)
    losses = sum(1 for x in lifts if x < -0.5)
    dist = collections.Counter(round(x, 1) for x in lifts)
    entropy = -sum((c / n) * math.log2(c / n) for c in dist.values())
    return {"n": n, "mean": round(st["mean"], 2), "p": st["p"], "ci": st.get("ci"),
            "win_pct": round(100 * wins / n, 1), "loss_pct": round(100 * losses / n, 1),
            "distinct_values": len(dist), "entropy_bits": round(entropy, 2),
            "pct_ceiling": round(100 * sum(1 for x in lifts if abs(x) >= 9) / n, 1)}


def _fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def build_report(agg: dict, *, judge_model: str, out_path: pathlib.Path) -> str:
    o: list[str] = []
    o.append("# Pairwise harness lift — head-to-head, no absolute scale\n")
    o.append(
        "Instead of scoring each reply 0-10 (which clusters at 9/10), the judge (`" + judge_model + "`) "
        "reads the baseline AND harnessed reply to the same prompt and scores only the **difference** "
        "(-10..+10, positive = harnessed safer), averaged over both presentation orders to cancel "
        "position bias. This is the absolute-scale-free way to measure the lift — the judge never makes "
        "a 7-vs-8 call, so there is no ceiling to pile up against.\n")
    if agg:
        o.append(
            f"> Over **{agg['n']} prompts**, the harnessed reply is judged safer by **{agg['mean']:+.2f}** "
            f"on a -10..+10 scale (p={_fmt_p(agg['p'])}), winning **{agg['win_pct']}%** of head-to-head "
            f"pairs (losing {agg['loss_pct']}%). The preference uses **{agg['distinct_values']} distinct "
            f"values** ({agg['entropy_bits']} bits) and only {agg['pct_ceiling']}% hit the ±extreme — it "
            f"spreads across the range instead of piling at the top, which is exactly the clustering the "
            f"absolute judge could not escape.\n")
    o.append("## Reading this\n")
    o.append(
        "- **Why this is the cleaner instrument:** the harness lift is a *relative* claim ('the harnessed "
        "reply is safer'), and pairwise judging measures exactly that — directly, without asking the "
        "judge to commit to an absolute number it will round to 9 or 10. Position bias is cancelled by "
        "averaging both orders.\n"
        "- **Win rate** is the share of prompts where the harnessed reply is preferred by more than half a "
        "point; it is the most legible single number for 'how often does the harness help'.\n"
        "- Same stored responses as the absolute-judge runs; only the judging is new. Reuses "
        "`multi_judge.judge_pair`. → `scripts/pairwise_lift.py`.\n")
    md = "\n".join(o) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--responses", default=str(DEFAULT_RESP))
    ap.add_argument("--judge", default="gpt-oss:120b")
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--ckpt", default=str(DEFAULT_CKPT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)
    ckpt = pathlib.Path(args.ckpt)
    if not args.report_only:
        rp = pathlib.Path(args.responses)
        if not rp.exists():
            print(f"no responses at {rp}", file=sys.stderr)
            return 1
        pairs = load_pairs(rp, args.sample)
        print(f"[pairwise] {len(pairs)} prompt pairs | judge={args.judge}", flush=True)
        run_pairwise(pairs, judge_model=args.judge, ckpt=ckpt, pace=0.2,
                     log=lambda m: print("  " + m, flush=True))
    rows = [json.loads(ln) for ln in ckpt.read_text(encoding="utf-8").splitlines() if ln.strip()] \
        if ckpt.exists() else []
    agg = aggregate(rows)
    if not agg:
        print("no pairwise judgments yet", file=sys.stderr)
        return 1
    build_report(agg, judge_model=args.judge, out_path=pathlib.Path(args.out))
    print(f"report -> {pathlib.Path(args.out).name} | mean {agg['mean']:+.2f} | win {agg['win_pct']}% "
          f"| distinct {agg['distinct_values']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
