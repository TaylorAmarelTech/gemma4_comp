#!/usr/bin/env python3
"""Multi-model, multi-persona developer review loop (propose-only).

A standing "advisory board" for DueCare: assemble a project digest, then have a panel of
PERSONAS — each a different lens (competition judge, YC partner, CEO/COO/CTO/CFO, peer
engineer) running on a different MODEL (GLM, Kimi, DeepSeek, Qwen, Gemma via Ollama-cloud;
Claude Code adds its own pass + the synthesis) — critique the project, score product-market
fit, and propose prioritized improvements. A second CROSS-REVIEW pass has each model react to
another's critique. Everything is staged PROPOSE-ONLY to gitignored reports/dev_review/; a
human (or Claude Code) triages the suggestions into actual work.

Boundary (real-not-faked): the panel only PROPOSES. No file is changed, no doc archived, nothing
merged. Suggestions are drafts for human/Claude triage. Models reviewing each other reduces
single-model blind spots; the lenses force breadth (tech AND market AND fundability AND rubric).

    OLLAMA_API_KEY=... python scripts/dev_review_loop.py            # full panel
    python scripts/dev_review_loop.py --personas yc_partner,cto    # subset
    python scripts/dev_review_loop.py --no-cross-review            # skip the cross pass
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from llm_generate import extract_json, ollama_chat, stage_proposal  # noqa: E402  (engine reuse)

REVIEW_DIR = _ROOT / "reports" / "dev_review"

# Persona = a lens + the model that argues it. Models are spread so GLM, Kimi, DeepSeek, Qwen,
# and the project's own Gemma all sit on the board; Claude Code (this caller) adds the synthesis.
PERSONAS: dict[str, dict] = {
    "competition_judge": {
        "model": "gemma4:31b",
        "lens": "a Gemma 4 'AI for Good' hackathon JUDGE. Score Impact & Vision (40), Video & "
                "Storytelling (30), Technical Depth & real-not-faked execution (30). Is the Gemma "
                "usage load-bearing? Is anything faked for demo?"},
    "yc_partner": {
        "model": "glm-5.2",
        "lens": "a YC partner. Assess product-market fit, who pays, market size, 'why now', "
                "distribution, defensibility/moat, and founder-market fit. Be blunt about what "
                "would kill it."},
    "ceo": {
        "model": "glm-5.2",
        "lens": "a CEO. Assess the vision, the narrative, strategic focus, and what to cut. Is "
                "the one-sentence pitch crisp? What is the single most important next bet?"},
    "cto": {
        "model": "deepseek-v3.2",
        "lens": "a CTO. Assess architecture, correctness, tech debt, test coverage, scalability, "
                "and the biggest engineering risk. What would not survive real load or audit?"},
    "cfo": {
        "model": "kimi-k2.7-code",   # the only reachable Kimi 2.7 tag; needs the high token budget
        "lens": "a CFO. Assess cost structure, unit economics (per-NGO, per-inference), runway, "
                "and sustainability. What is the cheapest path to durable value?"},
    "coo": {
        "model": "qwen3-coder:480b",
        "lens": "a COO. Assess operations, deployment, NGO/regulator go-to-market, partnerships, "
                "and what blocks a real pilot. What is the operational bottleneck?"},
    "peer_engineer": {
        "model": "deepseek-v3.2",
        "lens": "a senior peer engineer doing code review. Assess code quality, naming, module "
                "boundaries, testing, and maintainability. What is the worst smell?"},
}

_SCHEMA_HINT = (
    'Reply with ONLY compact JSON: {"strengths": ["..."], "weaknesses": ["..."], '
    '"top_improvements": [{"title": "...", "why": "...", "effort": "S|M|L"}], '
    '"pmf_or_rubric_score_0_10": <number>, "verdict": "<one sentence>"}'
)


def gather_digest(*, max_chars: int = 12000) -> str:
    """A bounded project digest from the highest-signal files for a reviewer to react to."""
    parts: list[str] = []
    picks = [
        ("README.md", 2500),
        ("docs/FOR_JUDGES.md", 2500),
        ("docs/writeup_draft.md", 2500),
        ("docs/research/frontier_perdim_report.md", 1800),
        ("CLAUDE.md", 1500),
    ]
    for rel, cap in picks:
        p = _ROOT / rel
        if p.exists():
            parts.append(f"===== {rel} =====\n{p.read_text(encoding='utf-8', errors='replace')[:cap]}")
    digest = "\n\n".join(parts)
    return digest[:max_chars]


def review(persona_key: str, digest: str, *, model: str | None = None,
           caller: Callable[..., str] | None = None) -> dict:
    """One persona's structured critique of the project digest."""
    spec = PERSONAS[persona_key]
    model = model or spec["model"]
    prompt = (
        f"You are {spec['lens']}\n\n"
        "Review this project (DueCare — an on-device Gemma-4 anti-trafficking LLM-safety harness "
        "for NGOs and regulators) from your lens. Be specific and critical; cite the digest.\n\n"
        f"PROJECT DIGEST:\n{digest}\n\n{_SCHEMA_HINT}")
    call = caller or (lambda p, **kw: ollama_chat(p, **kw))
    # high budget so reasoning models (Kimi/GLM) finish the answer after their thinking pass
    text = call(prompt, model=model, max_tokens=3500)
    data = extract_json(text) or {}
    if not isinstance(data, dict):
        data = {}
    return {
        "persona": persona_key, "model": model,
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "top_improvements": [i for i in (data.get("top_improvements") or []) if isinstance(i, dict)],
        "score": data.get("pmf_or_rubric_score_0_10"),
        "verdict": data.get("verdict", ""),
    }


def cross_review(reviewer_key: str, target: dict, *, caller: Callable[..., str] | None = None) -> dict:
    """A persona reacts to ANOTHER persona's review — agree/dispute + add what they missed."""
    spec = PERSONAS[reviewer_key]
    prompt = (
        f"You are {spec['lens']}\n\n"
        f"Another reviewer (the {target['persona']}) said:\n"
        f"weaknesses={json.dumps(target.get('weaknesses', []))[:1200]}\n"
        f"top_improvements={json.dumps(target.get('top_improvements', []))[:1500]}\n\n"
        "From YOUR lens: which of their points do you agree with, which do you dispute, and what "
        "did they MISS? "
        'Reply ONLY compact JSON: {"agree": ["..."], "dispute": ["..."], "missed": ["..."]}')
    call = caller or (lambda p, **kw: ollama_chat(p, **kw))
    data = extract_json(call(prompt, model=spec["model"], max_tokens=3000)) or {}
    if not isinstance(data, dict):
        data = {}
    return {"reviewer": reviewer_key, "target": target["persona"],
            "agree": data.get("agree", []), "dispute": data.get("dispute", []),
            "missed": data.get("missed", [])}


def synthesize(reviews: list[dict]) -> list[dict]:
    """Rank proposed improvements by how many personas surface a similar title (cross-lens demand)."""
    buckets: dict[str, dict] = {}
    for r in reviews:
        for imp in r.get("top_improvements", []):
            title = str(imp.get("title", "")).strip()
            if not title:
                continue
            key = title.lower()[:60]
            b = buckets.setdefault(key, {"title": title, "personas": set(), "why": [], "effort": []})
            b["personas"].add(r["persona"])
            if imp.get("why"):
                b["why"].append(str(imp["why"]))
            if imp.get("effort"):
                b["effort"].append(str(imp["effort"]))
    out = [{"title": b["title"], "raised_by": sorted(b["personas"]), "n": len(b["personas"]),
            "why": b["why"][:3], "effort": (b["effort"] or ["?"])[0]} for b in buckets.values()]
    out.sort(key=lambda x: -x["n"])
    return out


def run(personas: list[str], *, do_cross: bool = True,
        caller: Callable[..., str] | None = None) -> dict:
    digest = gather_digest()
    reviews = []
    for k in personas:
        try:
            r = review(k, digest, caller=caller)
            reviews.append(r)
            print(f"  {k:18} ({PERSONAS[k]['model']:16}) score={r['score']} "
                  f"improvements={len(r['top_improvements'])}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 -- one reviewer must not sink the board
            print(f"  {k:18} ERROR {type(e).__name__}: {str(e)[:90]}", file=sys.stderr)
    crosses = []
    if do_cross and len(reviews) >= 2:
        for i, tgt in enumerate(reviews):
            reviewer = reviews[(i + 1) % len(reviews)]["persona"]   # next persona reacts
            try:
                crosses.append(cross_review(reviewer, tgt, caller=caller))
            except Exception as e:  # noqa: BLE001
                print(f"  cross {reviewer}->{tgt['persona']} ERROR {str(e)[:70]}", file=sys.stderr)
    return {"reviews": reviews, "cross_review": crosses, "prioritized": synthesize(reviews)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--personas", default=",".join(PERSONAS),
                    help="comma list (default: the full board)")
    ap.add_argument("--no-cross-review", action="store_true")
    args = ap.parse_args(argv)
    keys = [k.strip() for k in args.personas.split(",") if k.strip() in PERSONAS]

    print(f"convening {len(keys)} reviewers...", file=sys.stderr)
    result = run(keys, do_cross=not args.no_cross_review)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = stage_proposal([result], task="dev-review", model="multi", name="dev_review.json", at=at)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (REVIEW_DIR / "latest.json").write_text(
        json.dumps({"generated_at": at, **result}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nstaged PROPOSE-ONLY -> {path.relative_to(_ROOT)} + "
          f"{(REVIEW_DIR / 'latest.json').relative_to(_ROOT)}", file=sys.stderr)
    print("\n=== cross-lens prioritized improvements (most-raised first) ===", file=sys.stderr)
    for p in result["prioritized"][:10]:
        print(f"  [{p['n']}x {','.join(p['raised_by'])}] ({p['effort']}) {p['title']}", file=sys.stderr)
    return 0 if result["reviews"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
