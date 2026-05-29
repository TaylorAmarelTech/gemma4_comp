"""Harness-lift benchmark -- the multi-model meta-orchestrator.

Runs ANY model BOTH baseline (raw prompt) and DueCare-HARNESSED (GREP+RAG
grounding preamble prepended) over a set of trafficking-safety prompts, grades
both arms with the same rubric, and reports the per-model *lift*
(harnessed_mean - baseline_mean). This is the model-agnostic generalisation of
A-00's local-Gemma baseline-vs-harnessed proof: it lets you ask "how much safer
does the DueCare harness make Gemini 3.5 / Claude Opus 4.8 / GPT-OSS / local
Gemma 4 on migrant-worker safety?".

Design: every external dependency is INJECTED, so the orchestrator is testable
and runs without API keys.
  - ``grep_call`` / ``rag_call``: the harness layers (default_harness wires these).
  - ``resolve_model_call(target) -> (prompt -> str)``: returns a caller for a
    target. Real mode resolves a duecare-llm-models adapter or an endpoint via
    duecare.chat.harnesses.model_interface; test/offline mode injects a fake.
  - ``grade_fn(prompt, response) -> float`` in [0, 1]: real mode uses
    duecare.chat.harness.grade_response_universal; tests inject a fake.

Privacy (rule 81): external/frontier targets receive ONLY the public benchmark
prompts + public harness grounding -- never raw worker PII.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from duecare.chat.harness_lift import lift_arms

ModelCall = Callable[..., Any]
GradeFn = Callable[[str, str], float]
ResolveModelCall = Callable[[dict], Optional[ModelCall]]


def run_target(
    target: dict,
    prompts: list[dict],
    *,
    grep_call: Callable[..., Any],
    rag_call: Optional[Callable[..., Any]],
    resolve_model_call: ResolveModelCall,
    grade_fn: GradeFn,
) -> dict[str, Any]:
    """Run both arms for one target over all prompts; return its lift summary.

    A target that cannot be resolved (e.g. missing API key) is reported as
    ``skipped`` rather than failing the whole run.
    """
    name = str(target.get("name") or target.get("model") or "target")
    model_call = resolve_model_call(target)
    if model_call is None:
        return {"name": name, "status": "skipped",
                "reason": "model_call unavailable (missing key/adapter?)",
                "n": 0, "baseline_mean": 0.0, "harnessed_mean": 0.0, "lift": 0.0}

    rows: list[dict] = []
    for p in prompts:
        text = p["text"] if isinstance(p, dict) else str(p)
        try:
            arms = lift_arms(text, model_call=model_call,
                             grep_call=grep_call, rag_call=rag_call)
            b = float(grade_fn(text, arms["baseline"]))
            h = float(grade_fn(text, arms["harnessed"]))
            rows.append({"prompt_id": (p.get("id") if isinstance(p, dict) else None),
                         "baseline_score": b, "harnessed_score": h,
                         "grep_fired": arms["grep_fired"]})
        except Exception as exc:  # noqa: BLE001 -- one prompt failing must not sink the target
            rows.append({"prompt_id": (p.get("id") if isinstance(p, dict) else None),
                         "error": f"{type(exc).__name__}: {exc}"})

    scored = [r for r in rows if "baseline_score" in r]
    n = len(scored)
    base_mean = sum(r["baseline_score"] for r in scored) / n if n else 0.0
    harn_mean = sum(r["harnessed_score"] for r in scored) / n if n else 0.0
    return {
        "name": name,
        "provider": target.get("provider"),
        "model": target.get("model"),
        "status": "ok",
        "n": n,
        "n_errors": len(rows) - n,
        "baseline_mean": round(base_mean, 4),
        "harnessed_mean": round(harn_mean, 4),
        "lift": round(harn_mean - base_mean, 4),
        "rows": rows,
    }


def run_benchmark(
    config: dict,
    *,
    grep_call: Callable[..., Any],
    rag_call: Optional[Callable[..., Any]],
    resolve_model_call: ResolveModelCall,
    grade_fn: GradeFn,
) -> dict[str, Any]:
    """Run the harness-lift benchmark across every target in ``config``.

    ``config`` = ``{"targets": [...], "prompts": [{"id","text"}, ...]}``.
    Returns ``{"targets": [<per-target summary>], "ranked_by_lift": [...]}``.
    """
    prompts = config.get("prompts") or []
    targets = config.get("targets") or []
    summaries = [
        run_target(t, prompts, grep_call=grep_call, rag_call=rag_call,
                   resolve_model_call=resolve_model_call, grade_fn=grade_fn)
        for t in targets
    ]
    ranked = sorted(
        (s for s in summaries if s.get("status") == "ok"),
        key=lambda s: s["lift"], reverse=True,
    )
    return {
        "targets": summaries,
        "ranked_by_lift": [
            {"name": s["name"], "baseline_mean": s["baseline_mean"],
             "harnessed_mean": s["harnessed_mean"], "lift": s["lift"]}
            for s in ranked
        ],
        "n_targets": len(targets),
        "n_prompts": len(prompts),
    }


def default_harness_calls() -> tuple[Callable[..., Any], Optional[Callable[..., Any]]]:
    """Resolve the real GREP + RAG callables from the default harness.

    Imported lazily so this module stays import-light for tests/offline use.
    """
    from duecare.chat.harness import default_harness

    h = default_harness()
    return h["grep_call"], h.get("rag_call")
