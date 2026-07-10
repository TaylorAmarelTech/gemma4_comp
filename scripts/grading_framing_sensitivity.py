"""Is the measured harness lift an artifact of HOW the grading question is phrased? (overfitting probe)

Taylor's directive: "remixing the grading questions so we aren't overfitting to certain semantic points."
The per-dimension rubric can be asked with several question FRAMINGS (``_COMPONENT_QUESTION_FRAMINGS``).
Framings 0-2 all reward SPECIFICITY (exact statute / fee / hotline); framings 3-5 use genuinely different
lenses (worker-actionability, faithfulness/anti-fabrication, top-down deduction). If the harness lift is a
real quality gain it should survive the lens change; if it is the judge rewarding surface tokens the
harness happens to inject, the specificity framings will show a much larger lift than the diverse ones.

This tool grades each dimension of already-generated responses with EACH framing SEPARATELY (never
averaged) and reports, per dimension: the lift under each framing, the SPREAD across framings (max-min =
how much the measured lift depends on wording), and the SPECIFICITY-minus-DIVERSE gap (framings 0-2 mean
lift minus framings 3-5 mean lift = the overfitting-to-surface-tokens signal). It re-grades existing
responses, so it never regenerates model output or competes with the engine's Ollama. Propose-only.

Run (live off-Ollama judge):
    python scripts/grading_framing_sensitivity.py --n 6 --judge mistral:mistral-small-latest
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))

from multi_judge import (  # noqa: E402
    _COMPONENT_QUESTION_FRAMINGS, build_component_rubric_single, components_for_version,
    extract_json, model_family,
)
from perdim_headline_regrade import ARMS_PAIR, load_prompts, load_responses  # noqa: E402
import llm_generate as lg  # noqa: E402

OUT = _ROOT / "reports" / "grading_framing_sensitivity.json"
SPECIFICITY_FRAMINGS = (0, 1, 2)          # all reward exact statute/fee/hotline -> surface-token risk
DIVERSE_FRAMINGS = (3, 4, 5, 6, 7, 8)     # genuinely different lenses; a real lift survives ALL of them
_LABELS = {"A": "identifies indicator", "B": "cites specific law", "C": "refuses to enable",
           "D": "concrete resources", "E": "privacy/safety", "F": "appropriate engagement"}
_FRAMING_NAME = {0: "specific", 1: "strict", 2: "absent-to-concrete",
                 3: "worker-utility", 4: "faithfulness", 5: "deduction",
                 6: "skeptic", 7: "harm-if-absent", 8: "plain-language"}


def grade_one(prompt: str, response: str, key: str, mx: int, *, framing: int, model: str,
              caller: Callable[..., str], rubric_version: str) -> float | None:
    """One component's score under ONE framing, or None if the judge failed to return that key (a
    non-grade is skipped, never counted as a phantom 0)."""
    rubric = build_component_rubric_single(key, version=rubric_version, phrasing=framing)
    body = f"{rubric}\n\nWORKER:\n{prompt}\n\nASSISTANT REPLY:\n{response}"
    for _attempt in range(2):
        try:
            data = extract_json(caller(body, model=model, max_tokens=0)) or {}
        except Exception:  # noqa: BLE001 -- transient sub-call failure; retry once then skip
            continue
        if key in data:
            try:
                return max(0.0, min(float(mx), float(data[key])))
            except (TypeError, ValueError):
                return None
    return None


def sensitivity(cells: list[str], prompts: dict[str, str], responses: dict[str, dict[str, str]], *,
                judge: str, framings: list[int], rubric_version: str = "v1", concurrency: int = 6,
                caller: Callable[..., str] | None = None,
                log: Callable[[str], None] | None = None) -> dict:
    """Per (dimension, framing) harness lift over ``cells``, run on a thread pool. A unit is one
    (cell, framing): it grades every component on BOTH arms under that framing and returns the per-dim
    lift, so the same framing scores both arms (the lift cancels the framing's absolute offset)."""
    call = caller or (lambda p, **kw: lg.provider_chat(p, **kw))
    comps = components_for_version(rubric_version)
    lifts: dict[tuple[str, int], list[float]] = defaultdict(list)   # (dim, framing) -> [per-cell lift]
    units = [(pid, ph) for pid in cells
             if all(a in responses.get(pid, {}) for a in ARMS_PAIR) for ph in framings]

    def _grade_unit(pid: str, ph: int) -> list[tuple[str, float]]:
        arms = responses[pid]
        out: list[tuple[str, float]] = []
        for k, mx in comps:
            b = grade_one(prompts.get(pid, ""), arms["baseline"], k, mx,
                          framing=ph, model=judge, caller=call, rubric_version=rubric_version)
            h = grade_one(prompts.get(pid, ""), arms["harness_core"], k, mx,
                          framing=ph, model=judge, caller=call, rubric_version=rubric_version)
            if b is not None and h is not None:
                out.append((k, h - b))
        return out

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = {ex.submit(_grade_unit, pid, ph): (pid, ph) for (pid, ph) in units}
        for fut in as_completed(futs):
            done += 1
            try:
                for k, dv in fut.result():
                    lifts[(k, futs[fut][1])].append(dv)
            except Exception:  # noqa: BLE001
                continue
            if log and done % 5 == 0:
                log(f"  {done}/{len(units)} (cell, framing) units graded")

    dims = [k for k, _mx in comps]
    rows = []
    for k in dims:
        per_fr = {ph: (round(statistics.mean(lifts[(k, ph)]), 2), len(lifts[(k, ph)]))
                  for ph in framings if lifts[(k, ph)]}
        means = [m for m, _n in per_fr.values()]
        spec = [statistics.mean(lifts[(k, ph)]) for ph in framings
                if ph in SPECIFICITY_FRAMINGS and lifts[(k, ph)]]
        div = [statistics.mean(lifts[(k, ph)]) for ph in framings
               if ph in DIVERSE_FRAMINGS and lifts[(k, ph)]]
        rows.append({
            "dim": k, "label": _LABELS.get(k, k), "per_framing": per_fr,
            "spread": round(max(means) - min(means), 2) if means else None,
            "specificity_mean": round(statistics.mean(spec), 2) if spec else None,
            "diverse_mean": round(statistics.mean(div), 2) if div else None,
            "overfit_gap": round(statistics.mean(spec) - statistics.mean(div), 2) if (spec and div) else None,
        })
    return {"judge": judge, "rubric_version": rubric_version, "framings": framings,
            "framing_names": {ph: _FRAMING_NAME.get(ph, str(ph)) for ph in framings},
            "n_cells": len(cells), "by_dim": rows}


def format_report(res: dict) -> str:
    fr = res["framings"]
    head = "dim  " + " ".join(f"{_FRAMING_NAME.get(ph, ph)[:9]:>9s}" for ph in fr) + "  spread  spec  div   gap"
    lines = [f"Grading-question framing sensitivity -- judge {res['judge']}, {res['n_cells']} cells",
             "(each cell = per-dimension harness_core-vs-baseline lift under EACH framing, scored separately)",
             "", head]
    for r in res["by_dim"]:
        cells = " ".join((f"{r['per_framing'][ph][0]:+9.2f}" if ph in r["per_framing"] else f"{'--':>9s}")
                         for ph in fr)
        gap = r["overfit_gap"]
        lines.append(f"{r['dim']:>3s}  {cells}  {(r['spread'] if r['spread'] is not None else 0):+6.2f}  "
                     f"{(r['specificity_mean'] or 0):+5.2f} {(r['diverse_mean'] or 0):+5.2f} "
                     f"{(gap if gap is not None else 0):+5.2f}  {r['label']}")
    gaps = [r["overfit_gap"] for r in res["by_dim"] if r["overfit_gap"] is not None]
    if gaps:
        lines += ["", f"mean overfit gap (specificity minus diverse lift) across dims: {statistics.mean(gaps):+.2f}",
                  "  gap ~0 => the lift survives the lens change (robust); large + => specificity framings",
                  "  inflate the lift (the judge is rewarding surface tokens the harness injects)."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Framing-sensitivity / overfitting probe for the grading questions.")
    ap.add_argument("--n", type=int, default=6, help="cells to grade (each = 2 arms x dims x framings calls)")
    ap.add_argument("--model", default="gemma4:31b", help="subject model whose responses are re-graded")
    ap.add_argument("--judge", default="mistral:mistral-small-latest", help="one off-Ollama judge")
    ap.add_argument("--framings", default=",".join(str(i) for i in range(len(_COMPONENT_QUESTION_FRAMINGS))),
                    help="comma-separated framing indices to compare")
    ap.add_argument("--results", type=Path, default=_ROOT / "reports" / "rich_lift" / "results.jsonl")
    ap.add_argument("--promptset", type=Path, default=_ROOT / "reports" / "benchmark" / "full_promptset.json")
    ap.add_argument("--concurrency", type=int, default=6)
    args = ap.parse_args(argv)

    if model_family(args.judge) == model_family(args.model):
        print(f"refusing: judge {args.judge} shares the subject's family (self-grading)"); return 2
    framings = [int(x) for x in args.framings.split(",") if x.strip() != ""]
    responses = load_responses(args.results, args.model)
    prompts = load_prompts(args.promptset)
    cells = sorted(pid for pid, a in responses.items()
                   if all(x in a for x in ARMS_PAIR) and pid in prompts)[:args.n]
    print(f"framing-sensitivity: {len(cells)} {args.model} cells x {len(framings)} framings via {args.judge} ...",
          flush=True)
    res = sensitivity(cells, prompts, responses, judge=args.judge, framings=framings,
                      concurrency=args.concurrency, log=lambda m: print(m, flush=True))
    res["_synthetic"] = True
    res["_propose_only"] = True
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(format_report(res))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
