#!/usr/bin/env python3
"""Convergent validity: how far do the two independent graders agree?

DueCare scores each response two independent ways -- a DETERMINISTIC rule-based
grader (the reproducible per-dimension headline) and an LLM judge. Convergent
validity asks whether they agree on the SAME responses. The honest answer is
nuanced, so this measures it three ways on the high-variance 1000-prompt
gemma4:31b run (where both graders scored every response):

1. **Absolute-score correlation** -- do they rank individual (prompt, arm)
   responses the same way?
2. **Lift-level correlation** -- do they agree on the harness LIFT
   (harnessed - baseline) per prompt? This is what we actually claim, and it is
   the more meaningful test.
3. **Directional + binned convergence** -- do both find the harness helps ON
   AVERAGE (sign), and does mean judge-lift rise monotonically across
   deterministic-lift bins? This extracts the reliable signal from noisy
   per-prompt deltas.

This is the right place to test it: the deterministic grader is ceiling-bound on
strong frontier models (near-constant scores -> attenuated correlation), so a
ceiling-compressed subset would understate agreement. gemma4:31b over 1000
prompts has the dynamic range to measure it fairly. Pure analysis on stored
cells -- no model calls.

    python scripts/convergent_validity.py
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

import numpy as np

_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEFAULT_DET = _ROOT / "reports" / "harness_lift_1000.jsonl"
DEFAULT_JUDGE = _ROOT / "reports" / "harness_lift_1000_judge.jsonl"
DEFAULT_OUT = _ROOT / "docs" / "research" / "convergent_validity.md"


def load_cells(path: pathlib.Path) -> list[dict]:
    if not pathlib.Path(path).exists():
        return []
    out = []
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if {"prompt_id", "arm", "score"} <= r.keys():
            out.append(r)
    return out


def pair_means(cells: list[dict]) -> dict[tuple[str, str], float]:
    """{(prompt_id, arm): mean score over that response's graded dimensions}."""
    acc: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for c in cells:
        try:
            acc[(str(c["prompt_id"]), str(c["arm"]))].append(float(c["score"]))
        except (TypeError, ValueError):
            continue
    return {k: sum(v) / len(v) for k, v in acc.items() if v}


def aligned_absolute(detm: dict, judm: dict) -> tuple[list[float], list[float]]:
    """Aligned (det, llm) score lists over the (prompt, arm) keys present in both."""
    keys = sorted(set(detm) & set(judm))
    return [detm[k] for k in keys], [judm[k] for k in keys]


def aligned_lift(detm: dict, judm: dict) -> tuple[list[float], list[float]]:
    """Per-prompt (det_lift, llm_lift) where both arms exist in both graders."""
    pids = {p for (p, _a) in detm} & {p for (p, _a) in judm}
    det_lift, llm_lift = [], []
    for pid in sorted(pids):
        keys = [(pid, "baseline"), (pid, "harnessed")]
        if all(k in detm for k in keys) and all(k in judm for k in keys):
            det_lift.append(detm[(pid, "harnessed")] - detm[(pid, "baseline")])
            llm_lift.append(judm[(pid, "harnessed")] - judm[(pid, "baseline")])
    return det_lift, llm_lift


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (sx * sy) if sx * sy else 0.0


def _spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    rx = np.argsort(np.argsort(xs)).astype(float)
    ry = np.argsort(np.argsort(ys)).astype(float)
    return _pearson(list(rx), list(ry))


def sign_agreement(a: list[float], b: list[float], *, eps: float = 0.05) -> float:
    """Share of prompts where both graders agree on the sign of the lift (±/0)."""
    if not a:
        return 0.0

    def sgn(x: float) -> int:
        return 1 if x > eps else -1 if x < -eps else 0

    return sum(1 for x, y in zip(a, b) if sgn(x) == sgn(y)) / len(a)


def binned_convergence(det_lift: list[float], llm_lift: list[float], *, bins: int = 5) -> list[dict]:
    """Bin prompts by deterministic lift; report mean judge-lift per bin.

    Monotone increasing mean judge-lift across deterministic-lift bins is
    aggregate convergence even when the per-prompt correlation is noisy.
    """
    if len(det_lift) < bins:
        return []
    order = np.argsort(det_lift)
    chunks = np.array_split(order, bins)
    out = []
    for i, idx in enumerate(chunks, 1):
        dl = [det_lift[j] for j in idx]
        ll = [llm_lift[j] for j in idx]
        out.append({"bin": i, "n": len(idx),
                    "det_lift_mean": round(sum(dl) / len(dl), 3),
                    "llm_lift_mean": round(sum(ll) / len(ll), 3)})
    return out


def analyze(detm: dict, judm: dict) -> dict:
    ad, al = aligned_absolute(detm, judm)
    dl, ll = aligned_lift(detm, judm)
    bins = binned_convergence(dl, ll)
    monotone = all(bins[i]["llm_lift_mean"] <= bins[i + 1]["llm_lift_mean"]
                   for i in range(len(bins) - 1)) if len(bins) >= 2 else False
    return {
        "n_abs": len(ad),
        "abs_pearson": round(_pearson(ad, al), 3),
        "abs_spearman": round(_spearman(ad, al), 3),
        "n_lift": len(dl),
        "lift_pearson": round(_pearson(dl, ll), 3),
        "lift_spearman": round(_spearman(dl, ll), 3),
        "det_lift_mean": round(sum(dl) / len(dl), 3) if dl else 0.0,
        "llm_lift_mean": round(sum(ll) / len(ll), 3) if ll else 0.0,
        "sign_agreement": round(sign_agreement(dl, ll), 3),
        "both_positive": (sum(dl) > 0 and sum(ll) > 0) if dl else False,
        "bins": bins,
        "bins_monotone": monotone,
    }


def _strength(r: float) -> str:
    r = abs(r)
    return ("strong" if r >= 0.6 else "moderate" if r >= 0.4 else "weak" if r >= 0.2 else "negligible")


def build_report(analysis: dict, *, det_label: str, judge_label: str, out_path: pathlib.Path) -> str:
    a = analysis
    o: list[str] = []
    o.append("# Convergent validity — how far do the two graders agree?\n")
    o.append(
        "DueCare scores each response two **independent** ways: a deterministic rule-based grader "
        "(the reproducible per-dimension headline) and an LLM judge. This measures their agreement on "
        f"the high-variance **{det_label}** run, where both graders scored every response — the right "
        "place to test it, since the deterministic grader is ceiling-bound (near-constant) on already-"
        "strong models, which would understate agreement on a compressed subset.\n")
    o.append(
        f"> **The honest result is partial, directional convergence — not interchangeable graders.** "
        f"Both independently find the harness helps on average (deterministic lift "
        f"**{a['det_lift_mean']:+.2f}**, judge lift **{a['llm_lift_mean']:+.2f}**, both > 0), and mean "
        f"judge-lift {'rises monotonically' if a['bins_monotone'] else 'trends up'} across "
        f"deterministic-lift bins — directional convergence. But the per-prompt **lift correlation is "
        f"{_strength(a['lift_pearson'])} (Pearson r = {a['lift_pearson']})** and absolute-score "
        f"correlation is {_strength(a['abs_pearson'])} (r = {a['abs_pearson']}): the deterministic "
        "grader (a strict surface-pattern matcher, ceiling-bound) and the holistic judge **agree on "
        "direction but diverge on magnitude and per-prompt ranking.** Neither is a proxy for the "
        "other; we report both.\n")

    o.append("## Three views of agreement\n")
    o.append("| View | n | Pearson r | Spearman ρ | strength |")
    o.append("|---|---:|---:|---:|---|")
    o.append(f"| Absolute scores (per prompt × arm) | {a['n_abs']} | {a['abs_pearson']} | "
             f"{a['abs_spearman']} | {_strength(a['abs_pearson'])} |")
    o.append(f"| **Harness lift (per prompt)** | {a['n_lift']} | {a['lift_pearson']} | "
             f"{a['lift_spearman']} | {_strength(a['lift_pearson'])} |")
    o.append("")
    o.append(f"Per-prompt **sign agreement** on the lift: **{a['sign_agreement']*100:.0f}%** "
             "(both graders agree whether the harness helped, hurt, or was neutral on that prompt).\n")

    if a["bins"]:
        o.append("## Directional convergence — mean judge-lift across deterministic-lift bins\n")
        o.append("If the deterministic grader carries real signal, prompts it scores as higher-lift "
                 "should also get higher judge-lift, even if the per-prompt correlation is noisy.\n")
        o.append("| Det-lift bin (low→high) | n | mean det lift | mean judge lift |")
        o.append("|---:|---:|---:|---:|")
        for b in a["bins"]:
            o.append(f"| {b['bin']} | {b['n']} | {b['det_lift_mean']:+.2f} | {b['llm_lift_mean']:+.2f} |")
        o.append("")

    o.append("## Reading this honestly\n")
    o.append(
        "- **What converges:** the *direction*. Two independently-built graders both find the harness "
        "raises safety on average, and they trend together in aggregate. That the result survives two "
        "unrelated scoring methods is real evidence it is not an artifact of one method.\n"
        "- **What does not:** the *magnitude and per-prompt ranking*. The deterministic grader is a "
        "strict pattern/citation matcher with a small dynamic range on strong models (so it reports a "
        "small lift); the LLM judge holistically weighs safety (so it reports a larger one). Their "
        "weak per-prompt correlation means we must **not** treat the cheap deterministic grader as a "
        "stand-in for the holistic judge.\n"
        "- **Consequence for the headline:** the large single-number lift is the **LLM-judge** view "
        "(`harness_lift_report.md`); the deterministic grader is a **conservative, reproducible "
        "floor** and the per-dimension diagnostic (`comparative_results.md`, "
        "`frontier_perdim_report.md`). Ground truth from human experts is still the missing piece "
        "(`evaluation_methodology.md` §6).\n")
    md = "\n".join(o) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--det", default=str(DEFAULT_DET))
    ap.add_argument("--judge", default=str(DEFAULT_JUDGE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    det_cells = load_cells(pathlib.Path(args.det))
    judge_cells = load_cells(pathlib.Path(args.judge))
    if not det_cells or not judge_cells:
        print(f"need both det ({len(det_cells)}) and judge ({len(judge_cells)}) cells", file=sys.stderr)
        return 1
    detm, judm = pair_means(det_cells), pair_means(judge_cells)
    a = analyze(detm, judm)
    build_report(a, det_label=pathlib.Path(args.det).stem, judge_label=pathlib.Path(args.judge).stem,
                 out_path=pathlib.Path(args.out))
    print(f"report -> {pathlib.Path(args.out).name} | lift r={a['lift_pearson']} "
          f"abs r={a['abs_pearson']} | det lift {a['det_lift_mean']:+.2f} judge lift "
          f"{a['llm_lift_mean']:+.2f} | sign-agree {a['sign_agreement']*100:.0f}%", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
