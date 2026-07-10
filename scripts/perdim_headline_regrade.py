"""Granular per-DIMENSION LLM re-grade of the harness headline (the rigor standard).

Taylor's directive: "keep this level of massive rigor, very discrete granular dimension grading." This
re-grades ALREADY-GENERATED responses (no generation, so it never competes with the engine's Ollama)
with ``judge_components_perdim`` -- ONE judge call PER dimension, so no dimension is anchored to a round
grand total -- and reports EACH dimension's lift separately (A-E, not just the total), per judge and
pooled. Judges default to off-Ollama provider-prefixed models (fan-out) so the grade is independent of
the subject model's host. Propose-only output.

Complements (does not duplicate): ``build_frontier_perdim_report.py`` renders the DETERMINISTIC ~77-dim
grader; ``rich_harness_lift.py --grader perdim`` generates+grades to the board. This one is the light,
non-competing LLM re-grade of existing responses.

Run:
    python scripts/perdim_headline_regrade.py --n 40 --judges nvidia:openai/gpt-oss-120b,sambanova:DeepSeek-V3.1
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))

from multi_judge import components_for_version, judge_components_perdim, model_family  # noqa: E402

DEFAULT_RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
DEFAULT_PROMPTSET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
OUT = _ROOT / "reports" / "perdim_headline_regrade.json"
ARMS_PAIR = ("baseline", "harness_core")


def load_responses(results_path: Path, model: str) -> dict[str, dict[str, str]]:
    """``{prompt_id: {arm: response}}`` for one subject model from a results JSONL."""
    by: dict[str, dict[str, str]] = defaultdict(dict)
    for ln in results_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("model") == model and r.get("arm") and r.get("prompt_id"):
            by[str(r["prompt_id"])][r["arm"]] = r.get("response") or ""
    return by


def load_prompts(promptset_path: Path) -> dict[str, str]:
    d = json.loads(promptset_path.read_text(encoding="utf-8"))
    items = d.get("prompts") if isinstance(d, dict) else d
    return {str(p.get("id")): p.get("text", "") for p in items if isinstance(p, dict)}


def regrade(cells: list[str], prompts: dict[str, str], responses: dict[str, dict[str, str]], *,
            model: str, judges: list[str], caller: Callable[..., str] | None = None,
            rubric_version: str = "v1", concurrency: int = 6,
            log: Callable[[str], None] | None = None) -> dict:
    """Per-dimension re-grade. For each (cell, judge) run judge_components_perdim on both arms; return the
    per-dimension lift (harness_core - baseline) pooled per judge and overall, plus the total. The
    (cell, judge) units run on a thread pool so a publishable-scale N x judges is not sequential."""
    comp_keys = [k for k, _mx in components_for_version(rubric_version)]
    # judge never grades its own family (subject is ``model``)
    judges = [j for j in judges if model_family(j) != model_family(model)]
    per_judge: dict[str, dict[str, list[float]]] = {
        j: {k: [] for k in comp_keys + ["score"]} for j in judges}
    units = [(pid, j) for pid in cells
             if all(a in responses.get(pid, {}) for a in ARMS_PAIR) for j in judges]

    def _grade_unit(pid: str, j: str):
        arms = responses[pid]
        b = judge_components_perdim(prompts.get(pid, ""), arms["baseline"], model=j,
                                    caller=caller, rubric_version=rubric_version)
        h = judge_components_perdim(prompts.get(pid, ""), arms["harness_core"], model=j,
                                    caller=caller, rubric_version=rubric_version)
        return j, {k: float(h[k]) - float(b[k]) for k in comp_keys + ["score"] if k in b and k in h}

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = {ex.submit(_grade_unit, pid, j): (pid, j) for (pid, j) in units}
        for fut in as_completed(futs):
            done += 1
            try:
                j, deltas = fut.result()
            except Exception:  # noqa: BLE001 -- a judge failure drops that (cell, judge), never the run
                continue
            for k, v in deltas.items():
                per_judge[j][k].append(v)
            if log and done % 10 == 0:
                log(f"  {done}/{len(units)} (cell, judge) units graded")

    def summarize(lifts: dict[str, list[float]]) -> dict:
        out = {}
        for k, vals in lifts.items():
            if vals:
                out[k] = {"lift": round(statistics.mean(vals), 2), "n": len(vals)}
        return out

    pooled: dict[str, list[float]] = {k: [] for k in comp_keys + ["score"]}
    for j in judges:
        for k in comp_keys + ["score"]:
            pooled[k].extend(per_judge[j][k])
    return {"model": model, "judges": judges, "rubric_version": rubric_version,
            "per_judge": {j: summarize(per_judge[j]) for j in judges},
            "pooled": summarize(pooled),
            "component_keys": comp_keys}


def format_report(result: dict) -> str:
    labels = {"A": "identifies indicator", "B": "cites specific law", "C": "refuses to enable",
              "D": "concrete resources", "E": "privacy/safety", "F": "appropriate engagement"}
    lines = [f"Per-DIMENSION harness lift (one judge call per dimension) -- {result['model']}",
             f"judges: {', '.join(result['judges'])}", ""]
    pooled = result["pooled"]
    for k in result["component_keys"]:
        if k in pooled:
            lines.append(f"  {k} {labels.get(k, k):22s} lift={pooled[k]['lift']:+6.2f}  (n={pooled[k]['n']})")
    if "score" in pooled:
        lines.append(f"  {'TOTAL (0-100)':26s} lift={pooled['score']['lift']:+6.2f}  (n={pooled['score']['n']})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Granular per-dimension LLM re-grade of existing responses.")
    ap.add_argument("--n", type=int, default=40, help="number of prompts to re-grade")
    ap.add_argument("--model", default="gemma4:31b", help="subject model to re-grade")
    ap.add_argument("--judges", default="nvidia:openai/gpt-oss-120b",
                    help="comma-separated provider-prefixed judges (off Ollama)")
    ap.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--promptset", type=Path, default=DEFAULT_PROMPTSET)
    ap.add_argument("--concurrency", type=int, default=6, help="concurrent (cell, judge) grade units")
    args = ap.parse_args(argv)

    responses = load_responses(args.results, args.model)
    prompts = load_prompts(args.promptset)
    cells = sorted(pid for pid, a in responses.items()
                   if all(x in a for x in ARMS_PAIR) and pid in prompts)[:args.n]
    print(f"re-grading {len(cells)} {args.model} cells per-dimension via {args.judges} ...", flush=True)
    result = regrade(cells, prompts, responses, model=args.model, judges=args.judges.split(","),
                     concurrency=args.concurrency, log=lambda m: print(m, flush=True))
    result["_synthetic"] = True
    result["_propose_only"] = True
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(format_report(result))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
