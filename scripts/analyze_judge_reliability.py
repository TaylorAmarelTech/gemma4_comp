#!/usr/bin/env python3
"""Inter-judge reliability of the 0-100 panel -- offline, from the committed grades.

The harness-lift board is scored by a panel of independent frontier judges. A fair reviewer asks: how
much do the judges AGREE, is any judge systematically lenient, and is the harness's effect robust to
that? This reads ``reports/rich_lift/panel.jsonl`` (one row per model x prompt x arm x judge) and reports:

  1. Krippendorff's alpha (interval) -- inter-judge agreement -- OVERALL, PER ARM, and PER COMPONENT.
     Higher on the harnessed arms would mean the harness makes replies more consistently gradeable.
  2. Per-judge leniency -- each judge's mean deviation from the per-cell panel consensus (positive =
     scores above the panel; a paired measure that controls for which prompts each judge saw).
  3. Mean per-cell disagreement (stdev across judges), overall and per arm.

Distinct from ``convergent_validity`` (LLM-judge vs the DETERMINISTIC grader) -- this is judges vs each
other. Deterministic; no model calls. Model / judge labels only; no prompt or response text.

    python scripts/analyze_judge_reliability.py
    python scripts/analyze_judge_reliability.py --out docs/research/judge_reliability.md
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in (_ROOT / "packages").glob("*/src"):
    sys.path.insert(0, str(_src))

from multi_judge import krippendorff_alpha  # noqa: E402  (canonical interval-alpha; reused for DRY)

PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
OUT_DEFAULT = _ROOT / "docs" / "research" / "judge_reliability.md"
ARMS = ("baseline", "harness_core", "harness_full")
COMPONENTS = ("A", "B", "C", "D", "E")
COMPONENT_LABEL = {"A": "indicator", "B": "cites law", "C": "refuses", "D": "resources", "E": "safety"}


def _load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def analyse(panel: list[dict] | None = None) -> dict:
    panel = _load(PANEL) if panel is None else panel
    # cell -> {judge: score}; cell -> {judge: {comp: value}}
    cell_scores: dict[tuple, dict[str, float]] = collections.defaultdict(dict)
    cell_comps: dict[tuple, dict[str, dict[str, float]]] = collections.defaultdict(dict)
    judges: set[str] = set()
    for p in panel:
        try:
            cell = (str(p["model"]), str(p["prompt_id"]), str(p["arm"]))
            judge = str(p["judge"])
            cell_scores[cell][judge] = float(p["score_0_100"])
        except (KeyError, TypeError, ValueError):
            continue
        judges.add(judge)
        c = p.get("components")
        if isinstance(c, dict):
            cell_comps[cell][judge] = {k: float(c[k]) for k in COMPONENTS
                                       if isinstance(c.get(k), (int, float))}

    def _alpha_for(cells: list[tuple]) -> tuple[float | None, int]:
        items = {cell: list(cell_scores[cell].values()) for cell in cells
                 if len(cell_scores[cell]) >= 2}
        return (krippendorff_alpha(items) if items else None), len(items)

    all_cells = list(cell_scores)
    overall_alpha, overall_n = _alpha_for(all_cells)
    per_arm = {}
    for arm in ARMS:
        cells = [c for c in all_cells if c[2] == arm]
        alpha, n = _alpha_for(cells)
        # mean per-cell disagreement (population stdev across judges), for cells with >=2 judges
        stdevs = [statistics.pstdev(list(cell_scores[c].values())) for c in cells
                  if len(cell_scores[c]) >= 2]
        per_arm[arm] = {"alpha": alpha, "n": n,
                        "mean_disagreement": round(statistics.mean(stdevs), 1) if stdevs else None}

    # per-component alpha (overall, across arms)
    per_component = {}
    for comp in COMPONENTS:
        items = {}
        for cell, jc in cell_comps.items():
            vals = [jc[j][comp] for j in jc if comp in jc[j]]
            if len(vals) >= 2:
                items[cell] = vals
        per_component[comp] = {"alpha": krippendorff_alpha(items) if items else None, "n": len(items)}

    # per-model inter-judge alpha: is the panel reliable for EACH subject model? (low agreement on a
    # model means that model's lift number rests on shakier judge consensus)
    per_model = {}
    for m in sorted({c[0] for c in all_cells}):
        alpha, n = _alpha_for([c for c in all_cells if c[0] == m])
        if n:
            per_model[m] = {"alpha": alpha, "n": n}

    # per-judge leniency: deviation from the per-cell consensus (cells with >=2 judges)
    dev: dict[str, list[float]] = collections.defaultdict(list)
    raw: dict[str, list[float]] = collections.defaultdict(list)
    for cell, js in cell_scores.items():
        if len(js) >= 2:
            cmean = statistics.mean(js.values())
            for judge, sc in js.items():
                dev[judge].append(sc - cmean)
                raw[judge].append(sc)
    per_judge = {j: {"n": len(dev[j]),
                     "leniency": round(statistics.mean(dev[j]), 2) if dev[j] else None,
                     "mean_score": round(statistics.mean(raw[j]), 1) if raw[j] else None}
                 for j in sorted(judges)}

    return {"overall_alpha": overall_alpha, "overall_n": overall_n, "per_arm": per_arm,
            "per_component": per_component, "per_model": per_model, "per_judge": per_judge,
            "judges": sorted(judges), "n_panel": len(panel)}


def _fmt(v, nd=3):
    return "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def build_report(a: dict) -> str:
    o: list[str] = []
    o.append("# Inter-judge reliability of the 0-100 panel (offline, no model calls)\n")
    o.append(f"> From the committed grades (`reports/rich_lift/panel.jsonl`, {a['n_panel']:,} judge rows). "
             "Judges vs each other (not vs the deterministic grader -- that is `convergent_validity.md`). "
             "Regenerate with `python scripts/analyze_judge_reliability.py`. Judge labels only.\n")
    o.append(f"Panel judges: {', '.join('`'+j+'`' for j in a['judges'])}. "
             f"**Overall Krippendorff's alpha = {_fmt(a['overall_alpha'])}** "
             f"(interval, over {a['overall_n']:,} cells graded by >=2 judges). Alpha >= 0.80 is the "
             "conventional 'reliable' threshold; >= 0.67 'tentative'.\n")

    o.append("## Agreement per arm (is a harnessed reply more consistently gradeable?)\n")
    o.append("| Arm | alpha | cells (>=2 judges) | mean per-cell disagreement (stdev) |")
    o.append("|---|---:|---:|---:|")
    for arm in ARMS:
        s = a["per_arm"][arm]
        o.append(f"| `{arm}` | {_fmt(s['alpha'])} | {s['n']:,} | {_fmt(s['mean_disagreement'], 1)} |")
    o.append("")

    o.append("## Agreement per criterion (which criterion do judges agree on most?)\n")
    o.append("| Criterion | alpha | cells |")
    o.append("|---|---:|---:|")
    for comp in COMPONENTS:
        s = a["per_component"][comp]
        o.append(f"| {comp} ({COMPONENT_LABEL[comp]}) | {_fmt(s['alpha'])} | {s['n']:,} |")
    o.append("")

    o.append("## Agreement per subject model (is the lift trustworthy for each model?)\n")
    o.append("Inter-judge alpha over each subject model's cells. A low value flags a model whose lift "
             "number rests on weaker judge consensus; rows with very few cells (see `n`) are noisy small "
             "samples, not a reliability verdict.\n")
    o.append("| Subject model | alpha | cells |")
    o.append("|---|---:|---:|")
    for m, s in sorted(a.get("per_model", {}).items(), key=lambda kv: -(kv[1]["alpha"] or 0)):
        o.append(f"| `{m}` | {_fmt(s['alpha'])} | {s['n']:,} |")
    o.append("")

    o.append("## Per-judge leniency (deviation from the per-cell panel consensus)\n")
    o.append("`leniency` = mean(judge score - panel-cell mean); positive = this judge scores ABOVE the "
             "panel (lenient), negative = below (harsh). A paired measure, so it controls for which "
             "prompts each judge happened to grade.\n")
    o.append("| Judge | cells | leniency | mean score |")
    o.append("|---|---:|---:|---:|")
    for j, s in a["per_judge"].items():
        o.append(f"| `{j}` | {s['n']:,} | {_fmt(s['leniency'], 2)} | {_fmt(s['mean_score'], 1)} |")
    o.append("")

    o.append("## Reading\n")
    o.append("- A high overall alpha means the +37-40 harness lift is not an artifact of one idiosyncratic "
             "judge -- independent judges converge on the same 0-100 scores.\n"
             "- Per-arm alpha: if the harnessed arms agree MORE than baseline, grounding makes replies "
             "more consistently gradeable (a structured, cited answer is less ambiguous to score).\n"
             "- Per-criterion alpha typically peaks on the crisp criteria (does it refuse? does it cite a "
             "statute?) and is lower on the holistic ones -- pointing to where a human-calibration pass "
             "would most improve the rubric.\n"
             "- Per-judge leniency near 0 for all judges means no single model is inflating or deflating "
             "the board; a large positive/negative would flag a judge to down-weight or recalibrate.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args(argv)
    if not PANEL.exists():
        print(f"no panel at {PANEL} -- nothing to analyse", file=sys.stderr)
        return 1
    a = analyse()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(a), encoding="utf-8")
    print(f"wrote {out} | overall alpha={_fmt(a['overall_alpha'])} over {a['overall_n']:,} cells, "
          f"{len(a['judges'])} judges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
