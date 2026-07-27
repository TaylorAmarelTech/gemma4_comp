#!/usr/bin/env python3
# ruff: noqa: E501  (report-rendering script; long prose f-strings)
"""Cross-protocol agreement -- is the harness lift an artifact of how we ask the judges?

DueCare grades responses with the SAME judge panel and the SAME v1 rubric under two different
elicitation protocols:

  * ``batched`` (``reports/rich_lift/panel.jsonl``)        -- one judge call returns all five A-E dimensions
  * ``perdim``  (``reports/rich_lift/panel_perdim.jsonl``) -- five independent judge calls, one per dimension

A reviewer's fair objection to the headline is that a single batched grading prompt could induce the
lift (the judge sees all five dimensions at once and rewards a response that visibly ticks them off).
The per-dimension protocol removes that: each dimension is scored in isolation, with no sight of the
others. If the lift survives both, it is not an artifact of the grading prompt.

This compares the two protocols on the prompts BOTH graded -- a paired, like-for-like test -- and
reports where they agree and where they do not. It is deterministic and fully offline: it reads only
the recorded panels and calls no model.

Run:
    python scripts/cross_protocol_agreement.py
    python scripts/cross_protocol_agreement.py --json
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
BATCHED = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
PERDIM = _ROOT / "reports" / "rich_lift" / "panel_perdim.jsonl"
OUT = _ROOT / "docs" / "research" / "cross_protocol_agreement.md"
BASE, CORE = "baseline", "harness_core"


def _has_windows_drive_marker(parts: tuple[str, ...]) -> bool:
    """Return whether POSIX resolution embedded a Windows drive as a path component."""
    return any(len(part) == 2 and part[0].isalpha() and part[1] == ":" for part in parts)


def _label(path: Path) -> str:
    """Repo-relative label; anything outside the repo collapses to its bare filename."""
    try:
        relative = path.resolve().relative_to(_ROOT)
        if _has_windows_drive_marker(relative.parts):
            return path.name
        return relative.as_posix()
    except (ValueError, OSError):
        return path.name


def load_arm_means(path: Path, model: str) -> dict[str, dict[str, float]]:
    """prompt_id -> {arm: mean score across judges} for one model.

    The per-(prompt, arm) score is the mean over that arm's judge verdicts -- the same reduction
    ``scripts/analyze_full_results.py`` uses, so these numbers stay comparable with the headline.
    """
    acc: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("model") != model:
                continue
            pid, arm, score = row.get("prompt_id"), row.get("arm"), row.get("score_0_100")
            if not pid or arm not in (BASE, CORE) or not isinstance(score, (int, float)):
                continue
            acc[(str(pid), arm)].append(float(score))
    out: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for (pid, arm), scores in acc.items():
        out[pid][arm] = statistics.fmean(scores)
    return dict(out)


def paired_lifts(arms: dict[str, dict[str, float]]) -> dict[str, float]:
    """prompt_id -> (core - baseline), for prompts having BOTH arms."""
    return {pid: a[CORE] - a[BASE] for pid, a in arms.items() if BASE in a and CORE in a}


def _bootstrap_ci(values: list[float], *, n: int = 2000, seed: int = 20260716) -> tuple[float, float] | None:
    """Percentile bootstrap 95% CI of the mean, resampling prompts (the unit of independence)."""
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    k = len(values)
    means = []
    for _ in range(n):
        means.append(statistics.fmean([values[rng.randrange(k)] for _ in range(k)]))
    means.sort()
    return (round(means[int(0.025 * n)], 2), round(means[int(0.975 * n) - 1], 2))


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    try:
        return round(statistics.correlation(xs, ys), 3)
    except (statistics.StatisticsError, ValueError):
        return None


def compare(batched: dict[str, float], perdim: dict[str, float]) -> dict:
    """Paired agreement between the two protocols on their shared prompts."""
    shared = sorted(set(batched) & set(perdim))
    b = [batched[p] for p in shared]
    d = [perdim[p] for p in shared]
    diffs = [x - y for x, y in zip(b, d)]
    # A prompt "helps" when that protocol's lift is > 0; agreement is the share of shared prompts
    # where both protocols land on the same side of zero.
    agree = sum(1 for x, y in zip(b, d) if (x > 0) == (y > 0))
    b_hurt = {p for p in shared if batched[p] < 0}
    d_hurt = {p for p in shared if perdim[p] < 0}
    return {
        "n_batched_paired": len(batched),
        "n_perdim_paired": len(perdim),
        "n_shared": len(shared),
        "batched_lift": round(statistics.fmean(b), 2) if b else None,
        "perdim_lift": round(statistics.fmean(d), 2) if d else None,
        "protocol_delta": round(statistics.fmean(diffs), 2) if diffs else None,
        "protocol_delta_ci95": _bootstrap_ci(diffs),
        "lift_correlation_r": _pearson(b, d),
        "sign_agreement": round(100.0 * agree / len(shared), 1) if shared else None,
        "batched_hurts": len(b_hurt),
        "perdim_hurts": len(d_hurt),
        "hurts_in_both": len(b_hurt & d_hurt),
        "hurts_in_either": len(b_hurt | d_hurt),
    }


def render(c: dict, *, model: str, today: str, batched_path: Path, perdim_path: Path) -> str:
    if not c["n_shared"]:
        return (f"# Cross-protocol agreement -- {today}\n\n"
                f"No prompts are graded under both protocols for `{model}` yet, so there is nothing to "
                f"compare. Re-run once `{_label(perdim_path)}` overlaps `{_label(batched_path)}`.\n")
    ci = c["protocol_delta_ci95"]
    ci_disp = f", bootstrap 95% [{ci[0]:+}, {ci[1]:+}]" if ci else ""
    includes_zero = bool(ci and ci[0] <= 0 <= ci[1])
    # Statistical detectability and practical size are different questions. At this n a sub-point
    # difference is easily detectable, so report the delta RELATIVE to the effect it is qualifying --
    # that is the number a reader needs to decide whether the protocol matters.
    ref = abs(c["perdim_lift"] or 0.0)
    rel = (abs(c["protocol_delta"]) / ref * 100.0) if ref else None
    rel_disp = f" ({rel:.1f}% of the {c['perdim_lift']:+} per-dimension lift)" if rel is not None else ""
    if includes_zero:
        verdict = ("the interval includes 0, so the two protocols do **not** measurably disagree -- the "
                   "lift is not an artifact of the batched grading prompt")
    elif rel is not None and rel < 5.0:
        verdict = (f"the interval excludes 0, so the batched protocol is measurably the more generous of "
                   f"the two -- but only by {rel:.1f}% of the effect{'' if not ref else ''}. Scoring each "
                   "dimension in isolation removes essentially none of the lift, so the effect is **not** "
                   "an artifact of the batched grading prompt")
    else:
        verdict = ("the interval excludes 0 and the gap is a material share of the effect, so the headline "
                   "should be read as protocol-dependent; prefer the per-dimension number")
    r = c["lift_correlation_r"]
    r_disp = "not computable (degenerate variance)" if r is None else f"Pearson r = {r}"
    return f"""# Cross-protocol agreement -- does the grading protocol create the lift? ({today})

Generated by `scripts/cross_protocol_agreement.py`. Deterministic and fully offline -- it reads only
the recorded judge panels and **calls no model**.

## The question

The headline harness lift is scored by an LLM judge panel. A fair objection is that the *batched*
grading prompt could manufacture it: one call asks the judge to score all five A-E dimensions at
once, so a response that visibly names an indicator, cites a law, refuses, offers resources, and
protects privacy may be rewarded for legibly matching the rubric rather than for domain value.

The **per-dimension** protocol is the control. It scores each dimension in a separate judge call,
with no sight of the other dimensions, using the same judge panel and the same v1 rubric. If the
lift is an elicitation artifact, it should shrink or vanish here.

## Result (`{model}`, baseline -> harness_core)

| protocol | source panel | paired prompts | mean lift |
|---|---|---:|---:|
| batched | `{_label(batched_path)}` | {c['n_batched_paired']:,} | {c['batched_lift']:+} |
| per-dimension | `{_label(perdim_path)}` | {c['n_perdim_paired']:,} | {c['perdim_lift']:+} |

Those two rows cover different prompt sets, so the honest comparison is the **paired** one below,
restricted to the **{c['n_shared']:,} prompts graded under both protocols**.

- **Protocol delta (batched - per-dimension): {c['protocol_delta']:+}**{ci_disp}{rel_disp} -- {verdict}.
- **Per-prompt lift correlation: {r_disp}.**
- **Sign agreement: {c['sign_agreement']}%** of shared prompts land on the same side of zero
  (both protocols call it a help, or both call it a hurt).

## The hurt tail

The negative-lift tail is the north star -- the cases where the harness makes a response worse.

| | batched | per-dimension | both | either |
|---|---:|---:|---:|---:|
| prompts hurt (of {c['n_shared']:,} shared) | {c['batched_hurts']} | {c['perdim_hurts']} | {c['hurts_in_both']} | {c['hurts_in_either']} |

A prompt flagged by only one protocol is a grading-sensitivity case, not a settled regression. The
`both` column is the set worth repairing first; `either` bounds the work.

## Limits, kept explicit

1. The two protocols share the same judge panel and rubric, so this tests **elicitation robustness**,
   not judge-independence. Judge-independence is measured separately by the leave-one-judge-out
   envelope in `docs/research/full_results.md`.
2. Agreement on *direction and magnitude of the mean* is a weaker claim than per-prompt
   interchangeability; read the correlation above before treating the protocols as substitutable.
3. These are statements about the recorded panel under this rubric -- not real-world detection claims.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paired agreement between the batched and per-dimension grading protocols.")
    ap.add_argument("--batched", type=Path, default=BATCHED)
    ap.add_argument("--perdim", type=Path, default=PERDIM)
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--today", default=datetime.now(UTC).date().isoformat())
    ap.add_argument("--json", action="store_true", help="print the summary as JSON and write no report")
    args = ap.parse_args(argv)

    b = paired_lifts(load_arm_means(args.batched, args.model))
    d = paired_lifts(load_arm_means(args.perdim, args.model))
    c = compare(b, d)

    if args.json:
        print(json.dumps({"model": args.model, "generated": args.today,
                          "batched_panel": _label(args.batched), "perdim_panel": _label(args.perdim),
                          **c}, indent=2, sort_keys=True))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render(c, model=args.model, today=args.today, batched_path=args.batched, perdim_path=args.perdim),
        encoding="utf-8",
    )
    if not c["n_shared"]:
        print(f"no shared prompts for {args.model}; wrote placeholder -> {args.out}")
        return 0
    print(f"shared {c['n_shared']:,} prompts | batched {c['batched_lift']:+} vs perdim {c['perdim_lift']:+} "
          f"| delta {c['protocol_delta']:+} ci {c['protocol_delta_ci95']} | r {c['lift_correlation_r']} "
          f"| sign agree {c['sign_agreement']}% | hurts both {c['hurts_in_both']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
