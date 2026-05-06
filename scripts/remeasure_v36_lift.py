"""scripts/remeasure_v36_lift.py — re-measure the +56pp harness lift
against the v3.6 rubric (21 dims, harm-axis dims, use-case-aware
weighting).

Designed to run on Kaggle T4 with a loaded Gemma 4 (E4B-it default,
configurable). Reads the bundled 207-prompt eval set, runs each
prompt twice (HARNESS OFF and HARNESS ON), grades both with
`grade_response_universal` (deterministic v3.6 grader), aggregates,
and writes the refreshed reference numbers to
`_baseline_gauge.json`.

Usage:

  # On Kaggle T4 (after loading the model + creating the chat app):
  python scripts/remeasure_v36_lift.py \\
      --eval-set bundled \\
      --max-prompts 50 \\
      --variant e4b-it \\
      --git-sha "$(git rev-parse --short HEAD)"

  # Local dev mode (mock LLM, no model required):
  python scripts/remeasure_v36_lift.py --mock

Outputs:
  data/v3_6_lift_runs/<run_id>/per_prompt.jsonl    — full grades
  data/v3_6_lift_runs/<run_id>/summary.json        — aggregates
  data/v3_6_lift_runs/<run_id>/baseline_gauge.json — drop-in for the
                                                       curator JSON

Then PR the `baseline_gauge.json` content into
`packages/duecare-llm-chat/src/duecare/chat/harness/_baseline_gauge.json`
to ship the refreshed numbers in the next wheel.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

# Ensure the chat package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,
                str(REPO_ROOT / "packages/duecare-llm-chat/src"))


def _load_harness():
    """Lazy import; avoids fastapi pull when running --mock."""
    import types
    if "duecare" not in sys.modules:
        duecare = types.ModuleType("duecare")
        duecare.__path__ = [str(REPO_ROOT / "packages/duecare-llm-chat/src/duecare")]
        sys.modules["duecare"] = duecare
    if "duecare.chat" not in sys.modules:
        duecare_chat = types.ModuleType("duecare.chat")
        duecare_chat.__path__ = [str(REPO_ROOT / "packages/duecare-llm-chat/src/duecare/chat")]
        sys.modules["duecare.chat"] = duecare_chat
    import importlib
    return importlib.import_module("duecare.chat.harness")


def _build_off_response(model_call: Callable[[str], str], prompt: str) -> str:
    """Generate response with NO harness layers — raw model only."""
    return model_call(prompt) or ""


def _build_on_response(model_call: Callable[[str], str], prompt: str,
                          harness, persona: str) -> tuple[str, dict]:
    """Generate response with persona + GREP + RAG + Tools layers.
    Returns (response_text, harness_trace) so the grader can flag
    which layers fired."""
    grep = harness._grep_call(prompt)
    rag = harness._rag_call(prompt, top_k=5)
    # Build the prepended context (mirrors app.py wiring)
    parts: list[str] = [persona]
    if grep.get("hits"):
        parts.append("GREP findings:\n"
                     + "\n".join(f"- [{h.get('citation','?')}] {h.get('rule','?')}: "
                                    f"{h.get('match_excerpt','')[:200]}"
                                    for h in grep["hits"][:6]))
    if rag.get("docs"):
        parts.append("RAG sources:\n"
                     + "\n\n".join(f"### {d['title']}\n{d['snippet'][:600]}"
                                       for d in rag["docs"][:3]))
    pre = "\n\n---\n\n".join(parts)
    full_prompt = f"{pre}\n\n---\n\nUSER QUESTION:\n\n{prompt}"
    response = model_call(full_prompt) or ""
    trace = {
        "persona": {"enabled": True, "wired": True, "fired": True},
        "grep":    {"enabled": True, "wired": True, "fired": bool(grep.get("hits")),
                     "hits": grep.get("hits", [])},
        "rag":     {"enabled": True, "wired": True, "fired": bool(rag.get("docs")),
                     "docs": rag.get("docs", [])},
    }
    return response, trace


def _mock_model_call(prompt: str) -> str:
    """Mock generator for --mock mode — returns a templated response
    that exercises the grader without a real LLM."""
    if "GREP findings" in prompt or "RAG sources" in prompt:
        # Harness ON → return a "good" response
        return (
            "Per ILO C181 Art. 7, recruitment fees from workers are "
            "prohibited. POEA MC 14-2017 caps PH-HK at zero placement "
            "fee. RA 10022 §15 imposes joint-and-several liability on "
            "the licensed agency. The worker can: (1) file at the "
            "POEA Anti-Illegal Recruitment Branch, (2) recover wages "
            "via NLRC, (3) contact MfMW HK at +852-2522-8264. This "
            "constitutes debt bondage (ILO Indicator 4) regardless of "
            "how the arrangement is labeled."
        )
    # Harness OFF → return a "weak" response
    return (
        "Recruitment fees can vary by jurisdiction. You may want to "
        "consult a lawyer about your specific situation. Consider "
        "structuring the payment via a tripartite agreement to "
        "optimize cash flow."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-set", default="bundled",
                            help="'bundled' uses the 207 examples in EXAMPLE_PROMPTS; "
                                  "'/path/to/jsonl' uses a custom file with {prompt} per line")
    parser.add_argument("--max-prompts", type=int, default=0,
                            help="Cap (0 = run all)")
    parser.add_argument("--variant", default=os.getenv("GEMMA_MODEL_VARIANT", "e4b-it"),
                            help="Gemma variant for run metadata (does not load the model)")
    parser.add_argument("--git-sha", default=os.getenv("DUECARE_GIT_SHA", "unknown"))
    parser.add_argument("--persona", default="",
                            help="Override persona text; empty = use bundled DEFAULT_PERSONA")
    parser.add_argument("--mock", action="store_true",
                            help="Use a built-in mock LLM (no model load); "
                                  "runs in seconds, lets you smoke-test the script")
    parser.add_argument("--out", default="data/v3_6_lift_runs",
                            help="Output directory")
    args = parser.parse_args()

    h = _load_harness()
    print(f"  rubric version: {h.RUBRIC_UNIVERSAL.get('version', '?')}")
    print(f"  n dimensions:   {len(h.RUBRIC_UNIVERSAL.get('dimensions', []))}")
    print(f"  evaluator qs:   {len(h.EVALUATION_QUESTIONS)}")
    print()

    # Resolve prompts
    if args.eval_set == "bundled":
        prompts = [(e["id"], e["text"]) for e in h.EXAMPLE_PROMPTS
                       if isinstance(e, dict) and e.get("text")]
    else:
        prompts = []
        for line in Path(args.eval_set).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                obj = json.loads(line)
                pid = obj.get("id") or f"p{len(prompts)+1:04d}"
                txt = obj.get("text") or obj.get("prompt") or ""
            else:
                pid = f"p{len(prompts)+1:04d}"
                txt = line
            if txt:
                prompts.append((pid, txt))
    if args.max_prompts:
        prompts = prompts[:args.max_prompts]
    print(f"  prompts to run: {len(prompts)}")

    # Resolve model
    if args.mock:
        model_call = _mock_model_call
        print("  model: MOCK (no GPU required)")
    else:
        # Caller is expected to have a Gemma loaded into their env.
        # We import from a kernel-level _gemma_call if it exists, else
        # raise. This script is designed to run inside the Kaggle
        # kernel after the model is loaded — in production you'd
        # call this from a notebook cell after the model is ready.
        try:
            from kernel import _gemma_call as _kc  # type: ignore[import-not-found]
            def model_call(p: str) -> str:
                msgs = [{"role": "user", "content": [{"type": "text", "text": p}]}]
                return _kc(msgs, max_new_tokens=2048, temperature=0.7) or ""
            print("  model: kernel._gemma_call (loaded by host kernel)")
        except ImportError:
            print("ERROR: no model loaded and --mock not passed. "
                  "Run inside a Kaggle kernel that has _gemma_call defined, "
                  "or use --mock for a smoke test.")
            return 1

    persona = args.persona or h.DEFAULT_PERSONA if hasattr(h, "DEFAULT_PERSONA") else \
              args.persona or ""

    # Output dir
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + f"-{args.variant}"
    out_dir = REPO_ROOT / args.out / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    per_prompt_path = out_dir / "per_prompt.jsonl"
    print(f"  output: {out_dir}")
    print()

    # Run
    t_start = time.time()
    rows: list[dict] = []
    with per_prompt_path.open("w", encoding="utf-8") as f:
        for i, (pid, prompt) in enumerate(prompts, 1):
            t_p = time.time()
            try:
                resp_off = _build_off_response(model_call, prompt)
                resp_on, trace = _build_on_response(model_call, prompt, h, persona)
                grade_off = h.grade_response_universal(
                    resp_off, prompt_text=prompt, harness_trace=None,
                )
                grade_on = h.grade_response_universal(
                    resp_on, prompt_text=prompt, harness_trace=trace,
                )
                row = {
                    "prompt_id":     pid,
                    "prompt":        prompt[:500],
                    "off_pct":       grade_off["pct_score"],
                    "on_pct":        grade_on["pct_score"],
                    "off_score_10":  grade_off.get("score_0_10"),
                    "on_score_10":   grade_on.get("score_0_10"),
                    "lift_pp":       grade_on["pct_score"] - grade_off["pct_score"],
                    "off_n_pass":    grade_off["n_pass"],
                    "on_n_pass":     grade_on["n_pass"],
                    "off_n_fail":    grade_off["n_fail"],
                    "on_n_fail":     grade_on["n_fail"],
                    "use_case":      grade_on.get("classification", {}).get("primary"),
                    "elapsed_sec":   round(time.time() - t_p, 1),
                }
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"  [{i:3}/{len(prompts)}] {pid:24s}  off={row['off_pct']:5.1f}  "
                      f"on={row['on_pct']:5.1f}  lift={row['lift_pp']:+5.1f}pp  "
                      f"({row['elapsed_sec']:.0f}s)")
            except Exception as e:  # noqa: BLE001
                print(f"  [{i:3}/{len(prompts)}] {pid:24s}  ERROR: {type(e).__name__}: {e}")

    # Aggregate
    if not rows:
        print("ERROR: no rows produced")
        return 1
    n = len(rows)
    avg_off = sum(r["off_pct"] for r in rows) / n
    avg_on  = sum(r["on_pct"]  for r in rows) / n
    avg_lift = avg_on - avg_off

    summary = {
        "run_id":         run_id,
        "rubric_version": h.RUBRIC_UNIVERSAL.get("version", ""),
        "git_sha":        args.git_sha,
        "variant":        args.variant,
        "n_prompts":      n,
        "avg_off_pct":    round(avg_off, 2),
        "avg_on_pct":     round(avg_on, 2),
        "avg_lift_pp":    round(avg_lift, 2),
        "elapsed_sec":    round(time.time() - t_start, 1),
        "completed_at":   datetime.utcnow().isoformat() + "Z",
        "mock_run":       args.mock,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    # Drop-in baseline_gauge.json (PR-able into the curator-block file)
    gauge = {
        "schema":         "duecare-baseline-gauge/v1",
        "version":        "1.1.0",
        "last_updated":   datetime.utcnow().strftime("%Y-%m-%d"),
        "curator":        "Duecare team — re-measured against v3.6",
        "notes":          (
            f"Re-measured against v3.6 rubric ({summary['rubric_version']}, "
            f"{len(h.RUBRIC_UNIVERSAL.get('dimensions', []))} dims) on {n} prompts "
            f"with Gemma 4 {args.variant}. "
            f"git_sha={args.git_sha}. {'MOCK RUN — replace with real numbers.' if args.mock else ''}"
        ),
        "stock": {
            "label":  f"stock {round(avg_off)}%",
            "value":  round(avg_off, 1),
            "color":  "#ef4444",
            "title":  f"Stock Gemma 4 {args.variant} baseline (no harness, {n}-prompt eval)",
            "notes":  ("Average pct_score across the eval set with all "
                          "harness layers OFF."),
        },
        "harnessed": {
            "label":  f"harnessed {round(avg_on)}%",
            "value":  round(avg_on, 1),
            "color":  "#10b981",
            "title":  f"Harnessed Gemma 4 {args.variant} (persona + GREP + RAG)",
            "notes":  ("Average pct_score across the eval set with "
                          "persona + GREP + RAG layers all ON."),
        },
        "eval_set_size":           n,
        "eval_run_date":           summary["completed_at"][:10],
        "rubric_version":          summary["rubric_version"],
        "rubric_version_current":  summary["rubric_version"],
        "git_sha":                 args.git_sha,
        "variant":                 args.variant,
        "lift_pp":                 round(avg_lift, 1),
        "footnote":                (
            "Re-measured against the current rubric version. PR the "
            "values in `stock.value`, `harnessed.value`, "
            "`eval_set_size`, `eval_run_date`, `rubric_version`, "
            "`git_sha` to the bundled `_baseline_gauge.json` to ship "
            "the refreshed numbers in the next wheel."
        ),
    }
    (out_dir / "baseline_gauge.json").write_text(
        json.dumps(gauge, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print(f"=== Summary ===")
    print(f"  prompts:   {n}")
    print(f"  avg OFF:   {avg_off:.1f}%")
    print(f"  avg ON:    {avg_on:.1f}%")
    print(f"  avg LIFT:  {avg_lift:+.1f}pp")
    print(f"  rubric:    {summary['rubric_version']}")
    print(f"  git_sha:   {args.git_sha}")
    print(f"  variant:   {args.variant}")
    print(f"  elapsed:   {summary['elapsed_sec']}s")
    print()
    print(f"Drop-in JSON:")
    print(f"  {out_dir / 'baseline_gauge.json'}")
    print(f"  → cp it to packages/duecare-llm-chat/src/duecare/chat/harness/_baseline_gauge.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
