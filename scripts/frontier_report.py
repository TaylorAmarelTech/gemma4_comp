#!/usr/bin/env python3
"""Frontier-model trafficking-safety report: baseline vs DueCare-harnessed, across many models.

Runs each candidate model on public synthetic trafficking-safety prompts in TWO arms --
baseline (raw prompt) and DueCare-HARNESSED (build_harness_preamble + prompt) -- grades both
with an independent judge on a 0-10 trafficking-safety rubric, PERSISTS every full response
(resumable), and renders a Kaggle-ready markdown report: a per-model lift table + concrete
"poor baseline -> harness-improved" example cards.

The harnessed arm reuses the REAL harness primitives (default_harness GREP/RAG + the lift
preamble), so the "with harness" column is the actual DueCare lift, not a mock. The model
weights are identical across arms -- only the surrounding context changes.

Models route by name: a bare tag (e.g. `glm-5.2`) or `ollama:<tag>` goes to Ollama-cloud; a
slugged id (e.g. `openai/gpt-4o`, `anthropic/claude-3.7-sonnet`) or `openrouter:<id>` goes to
OpenRouter (needs OPENROUTER_API_KEY) -- so closed frontier models can be compared too.

Run (resumable; safe to re-run after a rate-limit):
    OLLAMA_API_KEY=... python scripts/frontier_report.py --models glm-5.2,kimi-k2.7-code,gemma4:31b
    python scripts/frontier_report.py --report-only      # just re-render from saved results
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "duecare-llm-chat" / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))

RESULTS = _ROOT / "reports" / "frontier_report" / "results.jsonl"
REPORT = _ROOT / "docs" / "research" / "frontier_harness_report.md"

# Frontier candidates on Ollama-cloud (judge family excluded so judging stays independent).
DEFAULT_MODELS = ["glm-5.2", "kimi-k2.7-code", "deepseek-v3.2", "qwen3-coder:480b", "gemma4:31b"]
DEFAULT_JUDGE = "gpt-oss:120b"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


# --------------------------------------------------------------------------
# Results store (resumable: one row per model|prompt|arm)
# --------------------------------------------------------------------------

def load_results(path: Path = RESULTS) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _append(rec: dict, path: Path = RESULTS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _done(results: list[dict]) -> set[tuple]:
    return {(r["model"], r["prompt_id"], r["arm"]) for r in results}


# --------------------------------------------------------------------------
# Model routing: Ollama-cloud (open) or OpenRouter (closed frontier)
# --------------------------------------------------------------------------

def _is_openrouter(model: str) -> bool:
    return model.startswith("openrouter:") or ("/" in model and not model.startswith("ollama:"))


def _openrouter_key() -> str:
    env = _ROOT / ".env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if ln.startswith("OPENROUTER_API_KEY=") and not ln.lstrip().startswith("#"):
                return ln.split("=", 1)[1].strip()
    return os.environ.get("OPENROUTER_API_KEY", "")


def _call_openrouter(model: str, prompt: str, *, max_tokens: int = 1600) -> str:
    key = _openrouter_key()
    if not key:
        raise RuntimeError("no OPENROUTER_API_KEY in .env or environment")
    mid = model.split("openrouter:", 1)[-1]
    body = json.dumps({"model": mid, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(_OPENROUTER_BASE, data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read().decode("utf-8", "replace"))
    msg = (out.get("choices") or [{}])[0].get("message") or {}
    return str(msg.get("content") or msg.get("reasoning") or "").strip() or "(empty)"


def _caller(live):
    """Return chat(model, prompt) routing to OpenRouter or Ollama-cloud by model name."""
    def chat(model: str, prompt: str) -> str:
        if _is_openrouter(model):
            return _call_openrouter(model, prompt)
        return live.call_ollama(model.split("ollama:", 1)[-1], prompt)
    return chat


# --------------------------------------------------------------------------
# Run (reuses the real harness-lift primitives)
# --------------------------------------------------------------------------

def _preflight(chat, models: list[str]) -> list[str]:
    """Drop model tags that don't respond, so a typo doesn't waste the whole prompt set."""
    ok = []
    for m in models:
        try:
            chat(m, "Reply with the single word: ok")
            ok.append(m)
            print(f"[preflight] {m}: reachable", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"[preflight] {m}: DROPPED ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
        time.sleep(1.0)
    return ok


def run(models: list[str], *, n_prompts: int = 0, pace: float = 2.0) -> None:
    from duecare.chat.harness import default_harness
    from duecare.chat.harness_lift import build_harness_preamble
    import run_harness_lift_live as live

    chat = _caller(live)
    h = default_harness()
    grep_call, rag_call = h["grep_call"], h.get("rag_call")
    prompts = list(live.PROMPTS[:n_prompts]) if n_prompts else list(live.PROMPTS)
    models = _preflight(chat, models)
    done = _done(load_results())

    for model in models:
        for p in prompts:
            for arm in ("baseline", "harnessed"):
                if (model, p["id"], arm) in done:
                    continue
                try:
                    if arm == "baseline":
                        text, grep_fired = p["text"], None
                    else:
                        ground = build_harness_preamble(p["text"], grep_call=grep_call, rag_call=rag_call)
                        text = ground["preamble"] + "\n\n---\n\n" + p["text"]
                        grep_fired = ground.get("grep_fired")
                    resp = chat(model, text)
                    time.sleep(pace)
                    score = live.judge(p["text"], resp)
                    time.sleep(pace)
                    _append({"model": model, "prompt_id": p["id"], "prompt_text": p["text"],
                             "arm": arm, "response": resp, "score": score, "grep_fired": grep_fired})
                    print(f"{model:22} {p['id']:26} {arm:9} score={score:4.1f}", file=sys.stderr)
                except Exception as e:  # noqa: BLE001 -- one cell must not sink the run
                    print(f"{model:22} {p['id']:26} {arm:9} ERROR {type(e).__name__}: {str(e)[:110]}",
                          file=sys.stderr)


# --------------------------------------------------------------------------
# Report rendering
# --------------------------------------------------------------------------

def _aggregate(results: list[dict]) -> list[dict]:
    by: dict[str, dict[str, list[float]]] = {}
    for r in results:
        by.setdefault(r["model"], {"baseline": [], "harnessed": []})[r["arm"]].append(float(r["score"]))
    rows = []
    for model, arms in by.items():
        b, hh = arms["baseline"], arms["harnessed"]
        if not b or not hh:
            continue
        bm, hm = sum(b) / len(b), sum(hh) / len(hh)
        rows.append({"model": model, "baseline": round(bm, 2), "harnessed": round(hm, 2),
                     "lift": round(hm - bm, 2), "n": min(len(b), len(hh))})
    rows.sort(key=lambda x: -x["lift"])
    return rows


def _example_cards(results: list[dict], *, max_cards: int = 6) -> list[dict]:
    """Pick the largest baseline->harnessed improvements (the clearest 'poor response' fixes)."""
    paired: dict[tuple, dict] = {}
    for r in results:
        paired.setdefault((r["model"], r["prompt_id"]), {})[r["arm"]] = r
    cards = []
    for (model, pid), arms in paired.items():
        if "baseline" not in arms or "harnessed" not in arms:
            continue
        gap = arms["harnessed"]["score"] - arms["baseline"]["score"]
        cards.append({"model": model, "prompt_id": pid, "gap": gap,
                      "prompt": arms["baseline"]["prompt_text"],
                      "baseline": arms["baseline"], "harnessed": arms["harnessed"]})
    cards.sort(key=lambda c: -c["gap"])
    return [c for c in cards if c["gap"] > 0][:max_cards]


def build_report(results: list[dict] | None = None, *, judge: str = DEFAULT_JUDGE,
                 path: Path = REPORT) -> str:
    results = results if results is not None else load_results()
    rows = _aggregate(results)
    cards = _example_cards(results)
    models = sorted({r["model"] for r in results})
    n_prompts = len({r["prompt_id"] for r in results})
    avg_lift = round(sum(r["lift"] for r in rows) / len(rows), 2) if rows else 0.0

    out: list[str] = []
    out.append("# Frontier-Model Trafficking-Safety Report — the DueCare harness lift\n")
    out.append(
        "How well do today's strongest models recognise and respond to migrant-worker "
        "**labour-trafficking** situations — and how much does wrapping them in the **DueCare "
        "harness** (the model's weights unchanged; only GREP rules + retrieved context + an "
        "evidence-first reasoning preamble added) improve that? Every model is run twice per "
        "prompt: **baseline** (the raw question) and **harnessed**. An independent judge grades "
        "each reply 0–10 on trafficking-safety quality.\n")
    if rows:
        out.append(f"> **Across {len(rows)} models, the harness lifts the trafficking-safety "
                   f"score by +{avg_lift}/10 on average** (n={n_prompts} prompts each, judged by "
                   f"`{judge}`).\n")

    out.append("## Per-model lift\n")
    out.append("| Model | Baseline | Harnessed | Lift | n |")
    out.append("|---|---:|---:|---:|---:|")
    for r in rows:
        out.append(f"| `{r['model']}` | {r['baseline']:.2f} | {r['harnessed']:.2f} "
                   f"| **+{r['lift']:.2f}** | {r['n']} |")
    out.append("")
    out.append("*Scale 0–10; temperature 0; baseline = raw prompt, harnessed = "
               "`build_harness_preamble` + prompt (the real GREP/RAG/reasoning layer).*\n")

    out.append("## What the harness adds (and what it does not)\n")
    out.append(
        "- **GREP rules** flag exploitation indicators in the message (debt bondage, passport "
        "retention, contract substitution, fee-camouflage).\n"
        "- **Retrieved context** supplies the relevant ILO conventions / corridor facts.\n"
        "- **An evidence-first preamble** asks the model to name indicators, cite law, refuse to "
        "enable the exploiter, and route the worker to protective resources.\n"
        "- It does **not** change the model weights — the same model produces both columns, so "
        "the lift is attributable to context engineering a deployer can apply to ANY model.\n")

    out.append("## Concrete examples — poor baseline → harness-improved\n")
    if not cards:
        out.append("_(No paired results yet. Run the script to populate examples.)_\n")
    for c in cards:
        out.append(f"### `{c['prompt_id']}` on `{c['model']}` — "
                   f"baseline {c['baseline']['score']:.0f}/10 → harnessed {c['harnessed']['score']:.0f}/10\n")
        out.append("**Worker's message**\n")
        out.append("```\n" + c["prompt"].strip() + "\n```\n")
        out.append(f"**Baseline (no harness) — judged {c['baseline']['score']:.0f}/10**\n")
        out.append("```\n" + str(c["baseline"]["response"]).strip() + "\n```\n")
        out.append(f"**DueCare-harnessed — judged {c['harnessed']['score']:.0f}/10**\n")
        out.append("```\n" + str(c["harnessed"]["response"]).strip() + "\n```\n")

    out.append("## Methodology\n")
    out.append(
        f"- **Models** ({len(models)}): {', '.join('`' + m + '`' for m in models)}.\n"
        f"- **Prompts**: {n_prompts} public, composite/synthetic trafficking-safety scenarios "
        "(no real PII; debt bondage + passport retention, domestic-work 'safekeeping', fishing "
        "without contract, contract substitution, …).\n"
        "- **Arms**: baseline (raw prompt) vs harnessed (`build_harness_preamble` + prompt).\n"
        f"- **Judge**: `{judge}`, independent of the candidates' model families, one call per "
        "response, 0–10 trafficking-safety rubric (names indicators? cites law/ILO? refuses to "
        "enable + routes to resources? preserves safety/privacy?).\n"
        "- **Reproduce**: `python scripts/frontier_report.py --models "
        f"{','.join(DEFAULT_MODELS)}` (resumable; full responses persisted under "
        "`reports/frontier_report/`). Closed frontier via OpenRouter, e.g. "
        "`--models openai/gpt-4o,anthropic/claude-3.7-sonnet`.\n")
    out.append("### Honest caveats\n")
    out.append(
        "- Small n per cell — this is a directional, reproducible signal, not a leaderboard. A "
        "rigorous run uses more prompts, several judges, and one-dimension-per-call grading.\n"
        "- Open models run on Ollama-cloud; closed frontier (GPT/Claude/Gemini) run via "
        "OpenRouter when a key is configured.\n"
        "- This measures **recognition + response quality**, not real-world deployment outcomes.\n")

    out.append("## Why this matters after the competition\n")
    out.append(
        "Even the strongest models leave trafficking-safety quality on the table out of the box. "
        "DueCare is a thin, model-agnostic harness any NGO, platform, or regulator can put in "
        "front of the model they already use — and the lift is measurable. If you work in "
        "anti-trafficking, labour migration, or platform safety and want to pressure-test this "
        "on your own cases, please reach out.\n")

    md = "\n".join(out) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--judge", default=DEFAULT_JUDGE)
    ap.add_argument("--prompts", type=int, default=0, help="limit #prompts (0 = all)")
    ap.add_argument("--pace", type=float, default=2.0)
    ap.add_argument("--report-only", action="store_true", help="just re-render from saved results")
    args = ap.parse_args(argv)

    if not args.report_only:
        os.environ.setdefault("GEMINI_API_KEY", "unused")   # report uses an Ollama judge
        os.environ["JUDGE_MODEL"] = args.judge
        run([m.strip() for m in args.models.split(",") if m.strip()],
            n_prompts=args.prompts, pace=args.pace)

    build_report(judge=args.judge)
    print(f"report -> {REPORT.relative_to(_ROOT)} "
          f"({len(load_results())} result rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
