#!/usr/bin/env python3
"""Phase 3 four-arm evaluator -- does training internalise the harness lift, and do they stack?

The benchmark already grades the STOCK model in two arms: A = baseline (harness off) and B =
harness_full (harness on). This evaluator adds the TRAINED model (the LoRA from train_lift_distill.py)
in the same two arms -- C = trained baseline, D = trained harness_full -- on the SAME prompts, then
reports:

  internalisation     = C - A           (how much training alone raised the unharnessed model)
  internalised_frac   = (C-A)/(B-A)      (fraction of the harness's lift that training captured)
  harness_lift_stock  = B - A
  harness_lift_trained= D - C            (does the harness still help after training?)
  total               = D - A            (trained + harness vs stock baseline)
  stacks_vs_stock_harness = D >= B       (trained + harness beats stock + harness?)

Two paths:
  --analyze  CPU-safe: read panel.jsonl (the board's stock A/B + this tool's trained C/D) and print
             + write the four-arm table. Runs anywhere; this is the testable core.
  --run      GPU (Kaggle): load the trained adapter, generate C/D on the stock model's already-graded
             prompts (reusing rich_harness_lift's generation + the component-judge panel), then analyze.

    python scripts/four_arm_eval.py --analyze --stock-model gemma4:31b --trained-label duecare-trained
    python scripts/four_arm_eval.py --run --adapter reports/training/adapter --stock-model gemma4:31b

Design: docs/phase3_training_framework.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARD_PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
BOARD_RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DIR = _ROOT / "reports" / "four_arm"
FOUR_ARM_PANEL = OUT_DIR / "panel.jsonl"
FOUR_ARM_RESULTS = OUT_DIR / "results.jsonl"
REPORT = _ROOT / "docs" / "research" / "four_arm_eval.md"
ARM_OFF = "baseline"
ARM_ON = "harness_full"
DEFAULT_BASE = "unsloth/gemma-4-E2B-it"


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


def mean_by_arm(panel: list[dict], model: str) -> dict[tuple[str, str], float]:
    """{(prompt_id, arm): mean 0-100 score over judges} for one model."""
    by: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in panel:
        if str(r.get("model")) != model:
            continue
        try:
            by[(str(r["prompt_id"]), str(r["arm"]))].append(float(r["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {k: round(statistics.mean(v), 1) for k, v in by.items() if v}


def four_arm_table(panel: list[dict], stock_model: str, trained_model: str) -> dict[str, Any]:
    """A/B/C/D on prompts graded for BOTH models in both off/on arms, plus internalisation + stacking."""
    stock = mean_by_arm(panel, stock_model)
    trained = mean_by_arm(panel, trained_model)
    common = {p for (p, _a) in stock} & {p for (p, _a) in trained}
    rows = []
    for pid in sorted(common):
        a, b = stock.get((pid, ARM_OFF)), stock.get((pid, ARM_ON))
        c, d = trained.get((pid, ARM_OFF)), trained.get((pid, ARM_ON))
        if None in (a, b, c, d):
            continue
        rows.append({"prompt_id": pid, "A": a, "B": b, "C": c, "D": d})
    if not rows:
        return {"n": 0, "stock_model": stock_model, "trained_model": trained_model, "rows": [],
                "issues": ["no prompts graded for BOTH models in both off/on arms "
                           "(run --run after training, or check the model labels)"]}

    def m(k: str) -> float:
        return round(statistics.mean(r[k] for r in rows), 1)

    a, b, c, d = m("A"), m("B"), m("C"), m("D")
    harness_lift_stock = round(b - a, 1)
    return {
        "n": len(rows), "stock_model": stock_model, "trained_model": trained_model,
        "arms": {"A_stock_off": a, "B_stock_on": b, "C_trained_off": c, "D_trained_on": d},
        "internalisation": round(c - a, 1),
        "internalised_frac": (round((c - a) / harness_lift_stock, 2) if harness_lift_stock > 0 else None),
        "harness_lift_stock": harness_lift_stock,
        "harness_lift_trained": round(d - c, 1),
        "total": round(d - a, 1),
        "stacks_vs_stock_harness": d >= b,
        "harness_still_helps_trained": d > c,
        "rows": rows,
        "issues": [],
    }


def render_report(table: dict[str, Any], *, generated: str, sha: str) -> str:
    """Markdown four-arm report."""
    if table.get("n", 0) == 0:
        return ("# Four-arm evaluation (stock vs trained x harness off/on)\n\n"
                f"_generated {generated} - git {sha}_\n\n"
                "No paired data yet: " + "; ".join(table.get("issues") or ["pending the first trained run"])
                + ".\n\nRun `python scripts/four_arm_eval.py --run --adapter reports/training/adapter` "
                "on a GPU after training to populate arms C/D.\n")
    arms = table["arms"]
    frac = table["internalised_frac"]
    frac_s = f"{int(round(frac * 100))}%" if frac is not None else "n/a"
    return (
        "# Four-arm evaluation (stock vs trained x harness off/on)\n\n"
        f"_generated {generated} - git {sha} - n={table['n']} paired prompts - "
        f"stock `{table['stock_model']}` vs trained `{table['trained_model']}`_\n\n"
        "Does training internalise the harness lift, and do training + harness stack? Each prompt is "
        "scored by the same 0-100 component-judge panel in four arms on the same prompts.\n\n"
        "| arm | model | harness | mean 0-100 |\n|---|---|---|---:|\n"
        f"| A | stock | off | {arms['A_stock_off']} |\n"
        f"| B | stock | on | {arms['B_stock_on']} |\n"
        f"| C | trained | off | {arms['C_trained_off']} |\n"
        f"| D | trained | on | {arms['D_trained_on']} |\n\n"
        "| metric | value | reading |\n|---|---:|---|\n"
        f"| internalisation (C-A) | {table['internalisation']:+.1f} | training alone, harness off |\n"
        f"| internalised fraction | {frac_s} | share of the harness lift (B-A) captured by training |\n"
        f"| harness lift, stock (B-A) | {table['harness_lift_stock']:+.1f} | the original inference-time lift |\n"
        f"| harness lift, trained (D-C) | {table['harness_lift_trained']:+.1f} | does the harness still help after training |\n"
        f"| total (D-A) | {table['total']:+.1f} | trained + harness vs stock baseline |\n"
        f"| stacks vs stock+harness (D>=B) | {table['stacks_vs_stock_harness']} | training + harness beats harness alone |\n\n"
        "**Honest reading.** A high internalised fraction means training carried the harness's stable "
        "behaviours into the weights; a positive harness-lift-trained (D-C) means the harness still adds "
        "value on top (the volatile facts it supplies that weights can't memorise). We do not claim the "
        "gap closes -- we report it. Numbers regenerate from `panel.jsonl`; the judge panel is "
        "self-family-excluded.\n"
    )


def _stock_prompts(board_panel: list[dict], board_results: list[dict], stock_model: str, n: int) -> list[dict]:
    """Prompts the board already graded for the stock model in BOTH arms, with their text (for re-gen)."""
    arms_by_pid: dict[str, set] = defaultdict(set)
    for r in board_panel:
        if str(r.get("model")) == stock_model:
            arms_by_pid[str(r.get("prompt_id"))].add(str(r.get("arm")))
    text_by_pid = {}
    for r in board_results:
        if str(r.get("model")) == stock_model and r.get("prompt_text"):
            text_by_pid[str(r.get("prompt_id"))] = str(r["prompt_text"])
    out = []
    for pid in sorted(p for p, arms in arms_by_pid.items() if {ARM_OFF, ARM_ON} <= arms):
        if pid in text_by_pid:
            out.append({"id": pid, "text": text_by_pid[pid]})
    return out[:n] if n else out


def run(*, adapter: str, base: str, stock_model: str, trained_label: str, n: int,
        judges: list[str], max_seq: int, max_new_tokens: int) -> dict[str, Any]:
    """GPU path: generate the trained model's A/B (=C/D) on the stock prompts, judge, then analyze."""
    import sys as _sys
    _sys.path.insert(0, str(_ROOT / "scripts"))
    import rich_harness_lift as rl  # noqa: E402  (heavy: pulls llm_generate; lazy on purpose)

    board_panel = load_jsonl(BOARD_PANEL)
    prompts = _stock_prompts(board_panel, load_jsonl(BOARD_RESULTS), stock_model, n)
    if not prompts:
        raise SystemExit(f"no board-graded prompts for stock model {stock_model!r}; grade it first.")
    print(f"[four-arm] {len(prompts)} stock-graded prompts -> generating trained arms with adapter {adapter}")

    try:
        from unsloth import FastModel
        from unsloth.chat_templates import get_chat_template
        import torch  # noqa: F401
    except ImportError as exc:
        raise SystemExit(f"Unsloth/torch unavailable ({exc}); the --run step needs a CUDA GPU. "
                         "Use --analyze on CPU once a trained run has populated reports/four_arm/.")

    model, tokenizer = FastModel.from_pretrained(model_name=adapter, max_seq_length=max_seq,
                                                 dtype=None, load_in_4bit=True)
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
    if hasattr(FastModel, "for_inference"):
        FastModel.for_inference(model)

    def gen(_model_id: str, prompt_in: str) -> str:
        msgs = [{"role": "user", "content": [{"type": "text", "text": prompt_in}]}]
        ids = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                            return_tensors="pt").to(model.device)
        out = model.generate(input_ids=ids, max_new_tokens=max_new_tokens, temperature=1.0,
                             top_p=0.95, top_k=64, do_sample=True)
        return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rl.generate_responses(prompts, [trained_label], reuse={}, results_path=FOUR_ARM_RESULTS,
                          generate=gen, pace=0.0, max_tokens=max_new_tokens,
                          log=lambda m: print("  " + m, flush=True))
    four_results = load_jsonl(FOUR_ARM_RESULTS)
    rl.judge_panel(four_results, judges, panel_path=FOUR_ARM_PANEL, judge_caller=None, pace=0.6,
                   log=lambda m: print("  " + m, flush=True))
    combined = board_panel + load_jsonl(FOUR_ARM_PANEL)
    return four_arm_table(combined, stock_model, trained_label)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analyze", action="store_true", help="CPU-safe: read panels + print/write the table")
    ap.add_argument("--run", action="store_true", help="GPU: generate trained C/D then analyze")
    ap.add_argument("--adapter", default=str(_ROOT / "reports" / "training" / "adapter"))
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--stock-model", default="gemma4:31b")
    ap.add_argument("--trained-label", default="duecare-trained")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--judges", default="gpt-oss:120b,glm-5.2,deepseek-v4-pro")
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--generated", default="", help="ISO timestamp for the report header (optional)")
    ap.add_argument("--sha", default="", help="git sha for the report header (optional)")
    args = ap.parse_args(argv)

    if args.run:
        table = run(adapter=args.adapter, base=args.base, stock_model=args.stock_model,
                    trained_label=args.trained_label, n=args.n,
                    judges=[j.strip() for j in args.judges.split(",") if j.strip()],
                    max_seq=args.max_seq, max_new_tokens=args.max_new_tokens)
    else:
        combined = load_jsonl(BOARD_PANEL) + load_jsonl(FOUR_ARM_PANEL)
        table = four_arm_table(combined, args.stock_model, args.trained_label)

    print("[four-arm]", json.dumps({k: v for k, v in table.items() if k != "rows"}, indent=2))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(table, generated=args.generated or "(unstamped)",
                                    sha=args.sha or "(unstamped)"), encoding="utf-8")
    print(f"[four-arm] report -> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
