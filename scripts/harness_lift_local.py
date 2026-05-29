"""Harness-lift benchmark with a LOCAL deterministic grader.

External models GENERATE (the only paced / rate-limited work); DueCare's own
deterministic, multi-signal, per-dimension grader SCORES (free, instant,
reproducible). This removes the bottleneck of the earlier per-dimension design,
which funnelled tens of thousands of grades through ONE rate-limited judge API
and throttled the whole run to a crawl.

Why a local grader is the right call here:
  * It is DueCare's OWN evaluator (``grade_response_universal`` -- the same
    grader behind the headline lift number), so the ranking is on-brand and
    "real, not faked", not dependent on a third-party judge's availability.
  * It is deterministic: re-running gives identical grades (no judge variance).
  * It is per-dimension already: each applicable rubric dimension carries its
    own ``score_0_10`` and PASS/PARTIAL/FAIL status, honouring the project's
    per-dimension grading-integrity rule WITHOUT 10k+ external judge calls.
  * It is free and instant, so the grading side scales to any prompt count.

Resumable: one JSONL row per (prompt, model, arm, applicable-dimension) in the
SAME schema ``harness_lift_scheduled.aggregate()`` consumes, so a kill /
rate-limit / scheduled chunk resumes with zero rework. A (prompt, model, arm)
is "done" once it has at least one graded dimension cell.

Secrets are read from the environment ONLY (OLLAMA_API_KEY, GEMINI_API_KEY) and
never written to disk or printed. Public prompts only leave the machine
(rule 81) -- generation sends a public synthetic prompt; grading is local.

Usage (keys via env):
    OLLAMA_API_KEY=... GEMINI_API_KEY=... python scripts/harness_lift_local.py
Env knobs:
    LIFT_MODELS     comma list (default: gpt-oss:20b,gemma4:31b,gemini-3.5-flash)
    LIFT_N_PROMPTS  cap prompt count (default: all 100)
    LIFT_CKPT       checkpoint path (default: reports/harness_lift_local.jsonl)
    LIFT_PACE       seconds between generation calls (default: 1.0)
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import sys
import time
from typing import Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

# Reuse the tested core (cell id, resume loader, aggregator) verbatim.
from harness_lift_scheduled import aggregate, cell_key, load_checkpoint  # noqa: E402


def build_io() -> tuple[Callable[[str], str], Callable[[str, str], str],
                        Callable[[str, str], list[tuple[str, float]]]]:
    """Wire the real harness preamble, external generation, and the LOCAL
    deterministic grader. Lazy import so the module stays import-light."""
    from duecare.chat.harness import default_harness, grade_response_universal
    from duecare.chat.harness_lift import build_harness_preamble
    import run_harness_lift_live as live  # call_gemini / call_ollama (env keys)

    h = default_harness()
    grep_call, rag_call = h["grep_call"], h.get("rag_call")

    def build_preamble(text: str) -> str:
        return build_harness_preamble(
            text, grep_call=grep_call, rag_call=rag_call)["preamble"]

    def generate(model: str, prompt: str) -> str:
        return (live.call_gemini(model, prompt) if model.startswith("gemini")
                else live.call_ollama(model, prompt))

    def grade(prompt: str, response: str) -> list[tuple[str, float]]:
        """Local per-dimension grade: [(dim_id, score_0_10), ...] over the
        APPLICABLE dimensions only (NOT_APPLICABLE excluded, matching the
        grader's own pct_score semantics)."""
        g = grade_response_universal(response, prompt_text=prompt)
        return [(str(d["id"]), float(d.get("score_0_10") or 0.0))
                for d in g.get("dimensions", [])
                if d.get("status") and d["status"] != "NOT_APPLICABLE"]

    return build_preamble, generate, grade


def load_responses(path: pathlib.Path | None) -> dict[str, str]:
    """Return {pid|model|arm: response} from a persisted responses sidecar, so a
    resumed run (or a later judge pass) reuses generations instead of paying for
    them again. Tolerates a partial trailing line."""
    cache: dict[str, str] = {}
    if not path or not path.exists():
        return cache
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            cache[f"{row['prompt_id']}|{row['model']}|{row['arm']}"] = row["response"]
        except Exception:
            continue
    return cache


def run(
    prompts: list[dict],
    models: list[str],
    checkpoint_path: pathlib.Path,
    *,
    arms: tuple[str, ...] = ("baseline", "harnessed"),
    pace: float = 1.0,
    log: Callable[[str], None] = lambda _m: None,
    io: tuple[Callable[[str], str], Callable[[str, str], str],
              Callable[[str, str], list[tuple[str, float]]]] | None = None,
    judge: Callable[[str, str], float] | None = None,
    judge_checkpoint: pathlib.Path | None = None,
    responses_path: pathlib.Path | None = None,
) -> int:
    """Generate once, then score every (prompt, model, arm) not already done.

    Returns the number of LOCAL per-dimension cells newly written (the headline
    judge cells are tracked separately).

    Two graders run over the SAME generated response:
      * the LOCAL deterministic per-dimension grader (always; free/instant), and
      * an optional ``judge(prompt, response) -> 0-10`` safety judge (e.g. a
        strong Ollama model), written to ``judge_checkpoint`` as a single
        ``safety`` cell per (prompt, model, arm).

    Generations are persisted to ``responses_path`` and reused on resume, so the
    only paced/external cost is a genuinely new generation or judge call. ``io``
    may be injected as (build_preamble, generate, grade) for tests (no keys).
    """
    local_done = {ck.rsplit("|", 1)[0] for ck in load_checkpoint(checkpoint_path)}
    judge_done = ({ck.rsplit("|", 1)[0] for ck in load_checkpoint(judge_checkpoint)}
                  if judge and judge_checkpoint else set())
    resp_cache = load_responses(responses_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    build_preamble, generate, grade = io if io is not None else build_io()
    new_cells = 0

    for p in prompts:
        pid, text = str(p["id"]), p["text"]
        preamble: str | None = None
        for model in models:
            for arm in arms:
                rc = f"{pid}|{model}|{arm}"
                need_local = rc not in local_done
                need_judge = judge is not None and rc not in judge_done
                if not need_local and not need_judge:
                    continue

                response = resp_cache.get(rc)
                if response is None:  # generate once; reused for both graders
                    if arm == "harnessed" and preamble is None:
                        preamble = build_preamble(text)
                    prompt_in = (preamble + "\n\n---\n\n" + text
                                 if arm == "harnessed" else text)
                    try:
                        response = str(generate(model, prompt_in))
                    except Exception as exc:  # noqa: BLE001 -- skip, keep going
                        log(f"GEN FAIL {rc}: {type(exc).__name__}: {exc}")
                        continue
                    resp_cache[rc] = response
                    if responses_path:
                        with responses_path.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(
                                {"prompt_id": pid, "model": model, "arm": arm,
                                 "chars": len(response), "response": response}) + "\n")

                if need_local:
                    try:
                        graded = grade(text, response)
                    except Exception as exc:  # noqa: BLE001 -- skip local, keep going
                        log(f"GRADE FAIL {rc}: {type(exc).__name__}: {exc}")
                        graded = None
                    if graded:
                        with checkpoint_path.open("a", encoding="utf-8") as f:
                            for dim_id, score in graded:
                                f.write(json.dumps(
                                    {"cell": cell_key(pid, model, arm, dim_id),
                                     "prompt_id": pid, "model": model, "arm": arm,
                                     "dim": dim_id, "score": score}) + "\n")
                                new_cells += 1
                        local_done.add(rc)
                        log(f"OK {rc}: {len(graded)} dims "
                            f"(mean {sum(s for _i, s in graded) / len(graded):.2f})")
                    elif graded is not None:
                        log(f"NO APPLICABLE DIMS {rc} (resp {len(response)} chars)")

                if need_judge:
                    try:
                        jscore = float(judge(text, response))  # type: ignore[misc]
                    except Exception as exc:  # noqa: BLE001 -- skip judge, keep going
                        log(f"JUDGE FAIL {rc}: {type(exc).__name__}: {exc}")
                    else:
                        with judge_checkpoint.open("a", encoding="utf-8") as f:  # type: ignore[union-attr]
                            f.write(json.dumps(
                                {"cell": cell_key(pid, model, arm, "safety"),
                                 "prompt_id": pid, "model": model, "arm": arm,
                                 "dim": "safety", "score": jscore}) + "\n")
                        judge_done.add(rc)
                        log(f"JUDGE {rc}: safety={jscore:.1f}")

                if pace:
                    time.sleep(pace)
    return new_cells


def main() -> None:
    bench = _ROOT / "configs" / "duecare" / "benchmarks"
    prompts = json.loads(
        (bench / "harness_lift_prompts_100.json").read_text(encoding="utf-8"))["prompts"]
    prompts = prompts[: int(os.environ.get("LIFT_N_PROMPTS", str(len(prompts))))]
    models = [m.strip() for m in os.environ.get(
        "LIFT_MODELS", "gpt-oss:20b,gemma4:31b,gemini-3.5-flash").split(",") if m.strip()]
    ckpt = _ROOT / os.environ.get("LIFT_CKPT", "reports/harness_lift_local.jsonl")
    pace = float(os.environ.get("LIFT_PACE", "1.0"))
    responses_path = ckpt.with_suffix(".responses.jsonl")

    # Optional discriminating headline: a strong LLM judge (e.g. an Ollama model
    # like gpt-oss:120b) scores each response once on the trafficking-safety
    # rubric. The local deterministic grader can be safety-blind on inversion
    # cases (it can reward a well-structured but harmful answer); the LLM judge
    # captures the actual safety call. Off unless LIFT_JUDGE names a model.
    judge_model = os.environ.get("LIFT_JUDGE", "").strip()
    judge = judge_ckpt = None
    if judge_model:
        import run_harness_lift_live as live
        live.JUDGE_MODEL = judge_model
        judge = live.judge
        judge_ckpt = ckpt.with_name(ckpt.stem + "_judge.jsonl")

    print(f"[harness-lift-local] prompts={len(prompts)} models={models} arms=2 | "
          f"local per-dim grader (free)" + (f" + LLM judge={judge_model}" if judge else "")
          + f" | ckpt={ckpt} pace={pace}s", flush=True)
    n = run(prompts, models, ckpt, pace=pace, judge=judge, judge_checkpoint=judge_ckpt,
            responses_path=responses_path, log=lambda m: print("  " + m, flush=True))
    print(f"[harness-lift-local] newly graded {n} local dimension cells this pass", flush=True)
    print("\n=== LOCAL deterministic per-dimension grader (lift = harnessed - baseline) ===")
    print(json.dumps(aggregate(ckpt), indent=2))
    if judge_ckpt and judge_ckpt.exists():
        print(f"\n=== LLM safety judge ({judge_model}) headline (lift = harnessed - baseline) ===")
        print(json.dumps(aggregate(judge_ckpt), indent=2))


if __name__ == "__main__":
    main()
