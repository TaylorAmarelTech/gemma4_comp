# ruff: noqa: E501
"""Interim-goal dashboard for the exhaustive per-dimension grading run.

Reports how far the shuffled perdim grading has progressed toward a ladder of LARGE
interim milestones, the current lift estimate + bootstrap CI, and how representative the
actually-graded sample is vs the full registry. Because the grading order is seed-shuffled
(``rich_harness_lift.py --shuffle-seed``), each interim sample is an unbiased random draw of
the full set: interim goals reduce the prompt COUNT, never the grading resolution (every
graded prompt still gets all dimensions x all judges x all arms).

Read-only. Run anytime while the engine grades:
    python scripts/perdim_interim_goals.py
    python scripts/perdim_interim_goals.py --milestones 10000,25000,50000,78719
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "reports" / "rich_lift" / "panel_perdim.jsonl"
PROMPTSET = ROOT / "reports" / "benchmark" / "full_promptset.json"
# Large interim goals by default -- a 5k first checkpoint is ~6% of the registry and already
# matches the full category distribution within ~0.2pp; the ladder climbs to the full sweep.
DEFAULT_MILESTONES = (5_000, 10_000, 25_000, 50_000, 78_719)


def _load_analyzer():
    spec = importlib.util.spec_from_file_location("analyze_full_results", ROOT / "scripts" / "analyze_full_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_rows(panel: Path) -> list[dict]:
    rows: list[dict] = []
    if not panel.exists():
        return rows
    with panel.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def prompt_categories(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    prompts = doc.get("prompts", doc) if isinstance(doc, dict) else doc
    out: dict[str, str] = {}
    for p in prompts:
        if isinstance(p, dict) and p.get("id") is not None:
            out[str(p["id"])] = str(p.get("category", p.get("attack_category", "?")))
    return out


def representativeness(graded_pids: set, cats: dict[str, str]) -> tuple[int, int, float] | None:
    """(distinct categories in sample, distinct in full, max per-category share gap in pp)."""
    if not cats or not graded_pids:
        return None
    whole = Counter(cats.values())
    sample = Counter(cats.get(str(p), "?") for p in graded_pids)
    tot_s, tot_w = sum(sample.values()), sum(whole.values())
    if not tot_s or not tot_w:
        return None
    gap = max(abs(100 * sample.get(c, 0) / tot_s - 100 * whole[c] / tot_w) for c in whole)
    return len(sample), len(whole), gap


def render(rows: list[dict], cats: dict[str, str], milestones: tuple[int, ...], registry: int) -> str:
    analyzer = _load_analyzer()
    agg = analyzer.aggregate(rows)
    out = [f"=== perdim interim goals ===  rows={len(rows):,}  registry={registry:,}", ""]
    if not agg["per_model"]:
        out.append("no paired (baseline+harness_core) prompts graded yet.")
        return "\n".join(out)
    for m in agg["per_model"]:
        npair = m["n_pair"]
        graded = {r.get("prompt_id") for r in rows if r.get("model") == m["model"] and r.get("prompt_id")}
        stats = m.get("statistics") or {}
        ci = stats.get("lift_bootstrap_95")
        ci_txt = f"  95% CI [{ci[0]:+.1f}, {ci[1]:+.1f}]" if ci else ""
        out.append(f"model {m['model']}: paired {npair:,} prompts | lift {m['lift_core']:+.1f}{ci_txt} "
                   f"| helps {m['helps']} hurts {m['hurts']}")
        rep = representativeness(graded, cats)
        if rep:
            ncat, tcat, gap = rep
            out.append(f"   representativeness: {ncat}/{tcat} categories, max category-share gap {gap:.2f}pp vs full registry")
        out.append("   interim-goal ladder:")
        for ms in milestones:
            if npair >= ms:
                out.append(f"     [x] {ms:>7,} reached")
            else:
                bar = int(20 * npair / ms)
                out.append(f"     [ ] {ms:>7,}  {'#' * bar}{'.' * (20 - bar)}  {npair:,}/{ms:,} ({100 * npair / ms:.1f}%)")
        remaining = [ms for ms in milestones if npair < ms]
        if remaining:
            next_ms = remaining[0]
            eta_h = (next_ms - npair) / 6.8 / 60  # ~20.4 perdim cells/min => ~6.8 paired prompts/min
            out.append(f"   next goal {next_ms:,} in ~{eta_h:.1f} h at the current pace (~6.8 paired prompts/min)")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", type=Path, default=PANEL)
    ap.add_argument("--promptset", type=Path, default=PROMPTSET)
    ap.add_argument("--milestones", default=",".join(str(m) for m in DEFAULT_MILESTONES),
                    help="comma-separated interim prompt-count goals (default: large ladder to the full sweep)")
    ap.add_argument("--registry", type=int, default=78_719)
    args = ap.parse_args(argv)
    milestones = tuple(sorted(int(x) for x in args.milestones.split(",") if x.strip()))
    rows = read_rows(args.panel)
    cats = prompt_categories(args.promptset)
    print(render(rows, cats, milestones, args.registry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
