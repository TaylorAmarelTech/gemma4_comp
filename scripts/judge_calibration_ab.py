#!/usr/bin/env python3
"""A/B test: does the calibrated 0-100 anchored judge actually de-cluster vs the default 0-10 judge?

Taylor's worry: 0-10 judges default to round numbers (9/10) and miss the 7-vs-8 nuance. multi_judge
now has a `calibrated` rubric (0-100 + anchor bands, rescaled to 0-10). This script scores the SAME
stored responses with BOTH judges (same judge model, so only the rubric differs) and compares their
score distributions on the metrics that matter: distinct values, ceiling pile-up (share >= 9),
round-integer share, spread, and entropy. If the calibrated judge spreads the scores out, the
distinct-value count and entropy rise and the ceiling pile-up falls.

Reuses stored responses (only the judge calls are new). Resumable; judge injectable for tests.

    OLLAMA_API_KEY=... python scripts/judge_calibration_ab.py --responses reports/scheme_run.responses.jsonl --sample 60
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

DEFAULT_RESP = _ROOT / "reports" / "scheme_run.responses.jsonl"
DEFAULT_CKPT = _ROOT / "reports" / "judge_calibration_ab.jsonl"
DEFAULT_OUT = _ROOT / "docs" / "research" / "judge_calibration.md"


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


def load_responses(path: pathlib.Path, sample: int = 0) -> list[dict]:
    """Rows of {prompt_text, response}. prompt_text via the row, else looked up by prompt_id."""
    idx = _prompt_index()
    out: list[dict] = []
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        resp = r.get("response")
        if not resp:
            continue
        ptext = r.get("prompt_text") or r.get("prompt") or idx.get(str(r.get("prompt_id", "")), "")
        if not ptext:
            continue
        key = f"{r.get('model','?')}|{r.get('prompt_id','?')}|{r.get('arm','?')}"
        out.append({"key": key, "prompt_text": ptext, "response": str(resp)})
    return out[:sample] if sample else out


def _default_judge(prompt: str, response: str, *, model: str, calibrated: bool) -> float:
    from multi_judge import judge_one
    return judge_one(prompt, response, model=model, calibrated=calibrated)


def run_ab(items: list[dict], *, judge_model: str, judge: Callable[..., float] | None = None,
           ckpt: pathlib.Path = DEFAULT_CKPT, pace: float = 0.2,
           log: Callable[[str], None] = lambda _m: None) -> list[dict]:
    """Score each response with the default and the calibrated judge. Resumable (keyed by arm+key)."""
    jf = judge or _default_judge
    done: dict[tuple[str, str], dict] = {}
    if ckpt.exists():
        for ln in ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                done[(r["key"], r["arm"])] = r
            except (json.JSONDecodeError, KeyError):
                continue
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    for it in items:
        for arm, calibrated in (("default", False), ("calibrated", True)):
            if (it["key"], arm) in done:
                continue
            try:
                score = float(jf(it["prompt_text"], it["response"], model=judge_model, calibrated=calibrated))
            except Exception as exc:  # noqa: BLE001
                log(f"FAIL {arm} {it['key']}: {type(exc).__name__}: {exc}")
                continue
            row = {"key": it["key"], "arm": arm, "score": score}
            with ckpt.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            done[(it["key"], arm)] = row
            log(f"{arm} {it['key']}: {score}")
            if pace:
                time.sleep(pace)
    return list(done.values())


def clustering_metrics(scores: list[float]) -> dict:
    """The distribution shape: distinct values, ceiling pile-up, round-integer share, spread, entropy."""
    if not scores:
        return {}
    n = len(scores)
    dist = collections.Counter(round(s, 1) for s in scores)
    n_int = sum(1 for s in scores if abs(s - round(s)) < 1e-9)
    n_ceiling = sum(1 for s in scores if s >= 9.0)
    mean = sum(scores) / n
    std = (sum((s - mean) ** 2 for s in scores) / n) ** 0.5
    entropy = -sum((c / n) * math.log2(c / n) for c in dist.values())
    return {"n": n, "distinct_values": len(dist), "pct_integer": round(100 * n_int / n, 1),
            "pct_ceiling_ge9": round(100 * n_ceiling / n, 1), "std": round(std, 2),
            "entropy_bits": round(entropy, 2), "mean": round(mean, 2)}


def aggregate(rows: list[dict]) -> dict:
    by = collections.defaultdict(list)
    for r in rows:
        by[r["arm"]].append(float(r["score"]))
    return {arm: clustering_metrics(s) for arm, s in by.items()}


def build_report(agg: dict, *, judge_model: str, out_path: pathlib.Path) -> str:
    d, c = agg.get("default", {}), agg.get("calibrated", {})
    o: list[str] = []
    o.append("# Judge calibration A/B — does a 0-100 anchored rubric de-cluster the scores?\n")
    o.append(
        "Same responses, same judge model (`" + judge_model + "`), two rubrics: the default 0-10 ask vs "
        "the **calibrated** 0-100 anchored rubric (rescaled to 0-10). 0-10 judges pile up at round "
        "numbers (9/10) and miss the 7-vs-8 nuance; if the calibrated rubric helps, it shows **more "
        "distinct values, lower ceiling pile-up, and higher entropy** on the same answers.\n")
    if d and c:
        better = (c["distinct_values"] > d["distinct_values"] and c["pct_ceiling_ge9"] <= d["pct_ceiling_ge9"])
        verdict = ("the calibrated rubric **spreads the scores out** — it is the better instrument here"
                   if better else
                   "the calibrated rubric did **not** clearly de-cluster — anchors alone are not enough, "
                   "so the next lever (few-shot example responses or pairwise judging) is warranted")
        o.append(
            f"> Over **{d['n']} responses**, distinct score values went **{d['distinct_values']} → "
            f"{c['distinct_values']}**, the 9-10 ceiling pile-up **{d['pct_ceiling_ge9']}% → "
            f"{c['pct_ceiling_ge9']}%**, integer-only scores **{d['pct_integer']}% → {c['pct_integer']}%**, "
            f"and entropy **{d['entropy_bits']} → {c['entropy_bits']} bits**. So {verdict}.\n")
    o.append("## Distribution shape, by rubric\n")
    o.append("| Rubric | n | distinct values | % at 9-10 (ceiling) | % integer | std | entropy (bits) | mean |")
    o.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for arm, label in (("default", "default 0-10"), ("calibrated", "calibrated 0-100 → 0-10")):
        m = agg.get(arm)
        if m:
            o.append(f"| {label} | {m['n']} | {m['distinct_values']} | {m['pct_ceiling_ge9']}% | "
                     f"{m['pct_integer']}% | {m['std']} | {m['entropy_bits']} | {m['mean']} |")
    o.append("")
    o.append("## Reading this\n")
    o.append(
        "- **distinct values** and **entropy** up + **ceiling pile-up** down = the judge is using the "
        "scale instead of defaulting to 9/10. **% integer** near 0 for the calibrated arm means it is "
        "actually returning fine-grained scores (8.3, not 8).\n"
        "- This is about *resolution*, not the headline lift: the paired delta is reported on whichever "
        "rubric is the better instrument. If calibration de-clusters, future panels should use it; if "
        "not, few-shot examples or pairwise comparative judging are the next levers.\n"
        "- Same judge model on both arms, so only the rubric differs. Reuses stored responses; "
        "deterministic aggregation. → `scripts/judge_calibration_ab.py`.\n")
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
    ap.add_argument("--sample", type=int, default=60)
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
        items = load_responses(rp, args.sample)
        print(f"[calibration-ab] {len(items)} responses | judge={args.judge}", flush=True)
        run_ab(items, judge_model=args.judge, ckpt=ckpt, pace=0.2,
               log=lambda m: print("  " + m, flush=True))
    rows = [json.loads(ln) for ln in ckpt.read_text(encoding="utf-8").splitlines() if ln.strip()] \
        if ckpt.exists() else []
    agg = aggregate(rows)
    if not agg:
        print("no scores yet", file=sys.stderr)
        return 1
    build_report(agg, judge_model=args.judge, out_path=pathlib.Path(args.out))
    d, c = agg.get("default", {}), agg.get("calibrated", {})
    print(f"report -> {pathlib.Path(args.out).name} | distinct {d.get('distinct_values')}→"
          f"{c.get('distinct_values')} | ceiling {d.get('pct_ceiling_ge9')}%→{c.get('pct_ceiling_ge9')}%",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
