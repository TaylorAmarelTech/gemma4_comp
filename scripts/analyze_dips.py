# ruff: noqa: E501
"""Find the DIPS and VALLEYS in the harness lift -- and turn them into a training-data worklist.

The converged headline (+40.7) hides the tail that actually improves the flywheel: the prompts where
the harness makes the answer WORSE (regressions), the typologies/corridors where it barely helps
(valleys), and the rubric dimension it lifts least. Those are the cases to fix -- exclude the
regressions from training (anti-signal), target the valleys with better grounding + more training
examples, and reinforce the weak dimension. This is why the exhaustive sweep must run to 100%: the
dips live in the tail, and a small sample misses them.

Reads the shared panel (reports/rich_lift/panel.jsonl -- the batched grades) joined to prompt metadata
(reports/benchmark/full_promptset.json), and writes a markdown worklist. Deterministic, no network.

    python scripts/analyze_dips.py                                  # report to docs/research/harness_dips.md
    python scripts/analyze_dips.py --panel reports/rich_lift/panel_perdim.jsonl --model gemma4:31b
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
PROMPTSET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
OUT = _ROOT / "docs" / "research" / "harness_dips.md"
DIMS = ("A", "B", "C", "D", "E")
DIM_NAMES = {"A": "indicator", "B": "legal", "C": "refusal", "D": "resources", "E": "privacy"}
VALLEY_MIN_N = 20  # a category/corridor needs at least this many prompts to be ranked (small-n is noise)


def _num(x: object) -> float | None:
    return float(x) if isinstance(x, (int, float)) and x == x else None


def load_meta(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    prompts = doc.get("prompts", doc) if isinstance(doc, dict) else doc
    return {str(p["id"]): p for p in prompts if isinstance(p, dict) and "id" in p}


def find_dips(panel_rows: list[dict], meta: dict[str, dict], model: str,
              *, teacher_arm: str = "harness_core") -> dict:
    """Return the dips: regressions (harness < baseline), lowest-lift categories & corridors, and the
    per-dimension gains. Pure over the given rows; no I/O."""
    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    comp: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in panel_rows:
        if r.get("model") != model:
            continue
        pid, arm = r.get("prompt_id"), r.get("arm")
        s = _num(r.get("score_0_100"))
        if pid is None or arm is None:
            continue
        if s is not None:
            acc[pid][arm].append(s)
        for k, v in (r.get("components") or {}).items():
            n = _num(v)
            if n is not None:
                comp[pid][arm][k].append(n)

    lift: dict[str, float] = {}
    for pid, arms in acc.items():
        if "baseline" in arms and teacher_arm in arms:
            lift[pid] = statistics.mean(arms[teacher_arm]) - statistics.mean(arms["baseline"])

    def _field(pid: str, field: str) -> str:
        return str((meta.get(pid) or {}).get(field, "?"))

    regressions = sorted(
        ({"prompt_id": p, "lift": round(d, 1), "category": _field(p, "category"), "corridor": _field(p, "corridor")}
         for p, d in lift.items() if d < 0),
        key=lambda r: r["lift"])

    def _valleys(field: str) -> list[dict]:
        by: dict[str, list[float]] = defaultdict(list)
        for p, d in lift.items():
            by[_field(p, field)].append(d)
        rows = [{"value": k, "mean_lift": round(statistics.mean(v), 1), "n": len(v)}
                for k, v in by.items() if len(v) >= VALLEY_MIN_N and k != "?"]
        return sorted(rows, key=lambda r: r["mean_lift"])

    dim_gain: dict[str, float] = {}
    for k in DIMS:
        deltas = []
        for pid in lift:
            b = comp[pid]["baseline"].get(k)
            c = comp[pid][teacher_arm].get(k)
            if b and c:
                deltas.append(statistics.mean(c) - statistics.mean(b))
        if deltas:
            dim_gain[k] = round(statistics.mean(deltas), 1)
    weakest = min(dim_gain, key=dim_gain.get) if dim_gain else None

    return {"model": model, "n_paired": len(lift),
            "regressions": regressions,
            "valley_categories": _valleys("category")[:8],
            "valley_corridors": [v for v in _valleys("corridor") if v["value"] != "various"][:8],
            "dimension_gain": dim_gain, "weakest_dimension": weakest}


def render(dips: dict) -> str:
    m, n = dips["model"], dips["n_paired"]
    reg = dips["regressions"]
    lines = [f"# Harness dips & valleys -- training-data worklist ({m})", "",
             f"Over **{n:,} paired prompts**. These are the tail the converged headline hides -- the cases "
             "that improve the training flywheel. Rubric-scored benchmark evidence, not field detection.", "",
             f"## 1. Regressions -- the harness makes it WORSE ({len(reg)} prompts, {100 * len(reg) / max(n, 1):.1f}%)",
             "*Training action: exclude from SFT/DPO (anti-signal); investigate the harness for the worst categories.*", ""]
    if reg:
        lines += ["| lift | category | corridor |", "|---|---|---|"]
        lines += [f"| {r['lift']:+.1f} | {r['category']} | {r['corridor']} |" for r in reg[:12]]
    else:
        lines.append("_No regressions in this panel._")
    lines += ["", "## 2. Valleys -- typologies where the harness barely helps",
              "*Training action: target these with better grounding + more training examples.*", "",
              "| mean lift | n | category |", "|---|---|---|"]
    lines += [f"| {v['mean_lift']:+.1f} | {v['n']} | {v['value']} |" for v in dips["valley_categories"]]
    if dips["valley_corridors"]:
        lines += ["", "Lowest-lift **corridors**:", "", "| mean lift | n | corridor |", "|---|---|---|"]
        lines += [f"| {v['mean_lift']:+.1f} | {v['n']} | {v['value']} |" for v in dips["valley_corridors"]]
    lines += ["", "## 3. Weakest dimension -- where the harness adds least",
              "*Training action: reinforce this habit in the SFT/DPO targets.*", ""]
    for k in DIMS:
        if k in dips["dimension_gain"]:
            mark = "  <- weakest" if k == dips["weakest_dimension"] else ""
            lines.append(f"- **{k} ({DIM_NAMES[k]})**: {dips['dimension_gain'][k]:+.1f}{mark}")
    lines += ["", "## Why the full sweep must finish",
              "The regressions are 0.x% of prompts and the valleys are specific typologies -- both live in "
              "the TAIL. A converged average estimate is stable early, but the *complete* dip set only "
              "emerges as the exhaustive per-dimension sweep runs to 100%. That complete set is what makes "
              "the next round of training data better."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", type=Path, default=PANEL)
    ap.add_argument("--promptset", type=Path, default=PROMPTSET)
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--teacher-arm", default="harness_core")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    rows = [json.loads(x) for x in args.panel.read_text(encoding="utf-8").splitlines() if x.strip()]
    dips = find_dips(rows, load_meta(args.promptset), args.model, teacher_arm=args.teacher_arm)
    report = render(dips)
    args.out.write_text(report, encoding="utf-8")
    print(f"{dips['n_paired']:,} paired | {len(dips['regressions'])} regressions | "
          f"weakest dim {dips['weakest_dimension']} | worklist -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
