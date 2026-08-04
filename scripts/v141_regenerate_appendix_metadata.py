"""Regenerate the 12 appendix kaggle/*/wheels/dataset-metadata.json files to
v0.14.0 numbers, preserving the per-kernel slug and per-kernel
purpose-subtitle while harmonizing the description block.

Why this script exists: each appendix kernel's wheel-folder
dataset-metadata.json carried stale 'v3.6 / chat-package 0.2.0' /
'108 GREP / 33 RAG / 21-dim / 51 examples' descriptions even though
the wheel they ship is the current v0.14.0 wheel. The Kaggle public
dataset page renders this description verbatim, so a judge browsing
the appendix datasets sees outdated counts.

Run:
    py -3.10 scripts/v141_regenerate_appendix_metadata.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KAGGLE_DIR = REPO / "kaggle"

# The shared header that opens every description (anchored on chat-package
# 0.14.0 numbers as of 2026-05-08).
SHARED_HEADER = (
    "v0.14.5 / chat-package 0.14.5 (2026-05-08) — 587 example prompts across "
    "8 audience buckets (model_capability / enterprise_moderation / ngo_intake / "
    "individual_query / research / image_prompts / data_intelligence / "
    "regulator_audit), 46-dim rubric v3.10, 161 GREP rules across 31 categories, "
    "46-doc curated RAG corpus, 46-edge citation graph, 65-test adversarial "
    "validation suite across 16 attack families, 6 harness layers (Persona / "
    "GREP / RAG / Imports / Tools / Online), interactive RAG corpus graph "
    "viewer, evaluator_call hook for judge-model separation (in-process "
    "self-grade in the Kaggle deployment due to T4 VRAM limits), 20 bundled "
    "CC0 synthetic-evidence images + 13 structured-post JSONs."
)

# Per-kernel: (relative_path, title, slug_id, subtitle, license, kernel_blurb)
APPENDIX_KERNELS: list[dict[str, str]] = [
    {
        "path": "02-live-demo/wheels",
        "title": "Duecare Live Demo Wheels",
        "id": "taylorsamarel/duecare-live-demo-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 polished live-demo: focused 4-card homepage + "
            "+56.5pp lift regenerator"
        ),
        "kernel_blurb": (
            "Wheels for the polished live-demo notebook. Bundled: "
            "duecare-llm-chat / -core / -models / -cli / -server / -agents / "
            "-tasks / -domains / -workflows / -publishing / -engine / -nl2sql / "
            "-research-tools / -evidence-db / -training / -benchmark / meta. "
            "The headline +56.5pp lift demonstration runs end-to-end via the "
            "focused 4-card homepage (/individual / /enterprise / /knowledge / "
            "/settings)."
        ),
    },
    {
        "path": "A-01-chat-playground/wheels",
        "title": "Duecare Chat Playground Wheels",
        "id": "taylorsamarel/duecare-chat-playground-wheels",
        "license": "MIT",
        "subtitle": "v0.14.5 baseline harness-OFF Gemma 4 chat (the failure mode)",
        "kernel_blurb": (
            "Wheels for the baseline chat-playground (harness OFF). "
            "Bundled: duecare-llm-chat / -core / -models. Demonstrates raw "
            "Gemma 4 behaviour on trafficking-shaped prompts (the '5 cash flow "
            "optimization strategies' failure mode). Pair with "
            "chat-playground-with-grep-rag-tools to see the harness-OFF vs "
            "harness-ON delta."
        ),
    },
    {
        "path": "A-02-chat-playground-with-grep-rag-tools/wheels",
        "title": "Duecare Chat Playground with GREP RAG Tools Wheels",
        "id": "taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 6-toggle chat (Persona / GREP 161 / RAG 46 / Imports / "
            "Tools 5 / Online)"
        ),
        "kernel_blurb": (
            "Wheels for the chat-playground-with-grep-rag-tools notebook. "
            "Bundled: duecare-llm-chat / -core / -models. Shows the 6 harness "
            "layers as toggleable tiles. GREP catalog spans 161 rules across "
            "31 categories. Each fired rule prepends to the Gemma context with "
            "rule name + ILO/national-statute citation + indicator description. "
            "Pipeline modal renders the full 7-card transformation trace plus "
            "the new RETRIEVAL PATH TRACE card (BM25 → optional rerank → graph "
            "expansion → parent expansion)."
        ),
    },
    {
        "path": "A-03-content-classification-playground/wheels",
        "title": "Duecare Content Classification Playground Wheels",
        "id": "taylorsamarel/duecare-content-classification-playground-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 NGO classifier: 587 example prompts (8 audience buckets) "
            "+ 20 bundled CC0 evidence images"
        ),
        "kernel_blurb": (
            "Wheels for the content-classification-playground notebook (the "
            "NGO-triage surface of the same harness). Bundled: duecare-llm-chat "
            "/ -core / -models. 587 pre-built example prompts across 8 "
            "audience buckets covering recruitment posts, intake forms, "
            "complaints, advisories, journalist queries, image attachments, "
            "data-intelligence dashboards, and regulator audits. Each classify "
            "call returns risk score + per-vector magnitudes + recommended "
            "action pill + NGO referrals."
        ),
    },
    {
        "path": "A-04-content-knowledge-builder-playground/wheels",
        "title": "Duecare Knowledge Builder Playground Wheels",
        "id": "taylorsamarel/duecare-content-knowledge-builder-playground-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 knowledge builder — extend the 46-doc RAG corpus from "
            "web/text"
        ),
        "kernel_blurb": (
            "Wheels for content-knowledge-builder-playground. Bundled: "
            "duecare-llm-chat / -core / -models. Lets a user paste a recent "
            "ILO press release, court filing, or NGO report; Gemma 4 extracts "
            "citations and writes a new RAG corpus entry that the chat / "
            "classifier surfaces can immediately retrieve over BM25 + optional "
            "dense embedding fusion. The 46-doc baseline RAG corpus extends "
            "in place; the 46-edge citation graph tracks new edges."
        ),
    },
    {
        "path": "A-05-gemma-content-classification-evaluation/wheels",
        "title": "Duecare Gemma Content Classification Evaluation Wheels",
        "id": "taylorsamarel/duecare-gemma-content-classification-evaluation-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 OFF/ON classifier eval over 587 bundled cases across 8 "
            "audience buckets"
        ),
        "kernel_blurb": (
            "Wheels for gemma-content-classification-evaluation. Bundled: "
            "duecare-llm-chat / -core / -models. Runs all 587 example prompts "
            "through the classifier twice (harness OFF vs harness ON) and "
            "emits per-case OFF/ON delta + aggregate lift number + per-case "
            "markdown table. Now grades against the 46-dim rubric v3.10 with "
            "citation grounding + multi-signal matching."
        ),
    },
    {
        "path": "A-06-prompt-generation/wheels",
        "title": "Duecare Prompt Generation Wheels",
        "id": "taylorsamarel/duecare-prompt-generation-wheels",
        "license": "MIT",
        "subtitle": "v0.14.5 prompt generation — Gemma 4 self-generates eval prompts",
        "kernel_blurb": (
            "Wheels for prompt-generation. Bundled: duecare-llm-chat / -core "
            "/ -models. Uses Gemma 4 to generate new evaluation prompts in "
            "the smoke_25 row shape, plus 5 graded response examples per "
            "prompt (worst / fail / partial / good / best). Output JSON feeds "
            "the bench-and-tune A-07 fine-tune. Lets the corpus grow beyond "
            "the original 21K-test benchmark + the 587-prompt curated set."
        ),
    },
    {
        "path": "A-07-bench-and-tune/wheels",
        "title": "Duecare Bench & Tune Wheels",
        "id": "taylorsamarel/duecare-bench-and-tune-wheels",
        "license": "MIT",
        "subtitle": "v0.14.5 Unsloth SFT + DPO + GGUF + HF Hub fine-tune pipeline",
        "kernel_blurb": (
            "Wheels for bench-and-tune. Bundled: duecare-llm-chat / -core / "
            "-models / -benchmark / -domains / -tasks / -training. End-to-end "
            "fine-tune pipeline: smoke benchmark on stock Gemma 4 → Unsloth "
            "SFT (LoRA on harness-distilled or A-06-generated pairs) → DPO → "
            "re-benchmark → GGUF Q8_0 export → HF Hub push. Special Tech "
            "Track angle (Unsloth bonus). Outputs "
            "Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0 on HF Hub + GGUF "
            "artifact."
        ),
    },
    {
        "path": "A-08-research-graphs/wheels",
        "title": "Duecare Research Graphs Wheels",
        "id": "taylorsamarel/duecare-research-graphs-wheels",
        "license": "MIT",
        "subtitle": "v0.14.5 7 Plotly visualizations of corpus + harness data (CPU)",
        "kernel_blurb": (
            "Wheels for research-graphs (CPU only, ~30 sec to render). "
            "Bundled: duecare-llm-chat / -core / -models / -benchmark. 7 "
            "interactive Plotly charts: entity graph / corridor Sankey / "
            "per-category benchmark bars / fee-camouflage heatmap / ILO "
            "indicator hits / 46-doc RAG corpus sunburst / 46-edge citation "
            "graph network. Lets researchers explore what the harness "
            "actually knows: 161 GREP rules, 46 RAG docs, 11 ILO indicators, "
            "16 fee-camouflage labels, named NGO intake hotlines."
        ),
    },
    {
        "path": "A-09-chat-playground-with-agentic-research/wheels",
        "title": "Duecare Chat Agentic Research Wheels",
        "id": "taylorsamarel/duecare-chat-playground-with-agentic-research-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 chat with Playwright real-browser agentic web search "
            "(BYOK Brave / DDG fallback)"
        ),
        "kernel_blurb": (
            "Wheels for chat-playground-with-agentic-research. Bundled: "
            "duecare-llm-chat / -core / -models. Adds a 6th toggle for live "
            "agentic web research via Playwright (real browser automation). "
            "Multi-step Gemma 4 loop using Brave Search API (BYOK) with "
            "DuckDuckGo HTML fallback + httpx deep-fetch + Wikipedia. "
            "Open-source, no API keys required for the fallback path. "
            "Supplements GREP / RAG / Imports / Tools with fresh web context "
            "for prompts where the local corpus is silent."
        ),
    },
    {
        "path": "A-10-runtime-vs-weights-safety-study/wheels",
        "title": "Duecare Jailbroken Models Wheels",
        "id": "taylorsamarel/duecare-a10-runtime-vs-weights-safety-study-wheels",
        "license": "MIT",
        "subtitle": (
            "v0.14.5 harness on abliterated Gemma 4 — real-not-faked proof"
        ),
        "kernel_blurb": (
            "Wheels for the chat-playground-jailbroken-models notebook. "
            "Bundled: duecare-llm-chat / -core / -models. Loads "
            "<operator-supplied-checkpoint> or "
            "<operator-supplied-checkpoint> by default. Demonstrates "
            "that the 6-layer harness (Persona / GREP 161 / RAG 46 / Imports "
            "/ Tools 5 / Online) still produces safe + cited outputs even "
            "when the base model has had its refusal layer ablated by the "
            "model author. Strongest evidence that the safety lift is "
            "harness-driven, not base-model-driven."
        ),
    },
    {
        "path": "A-11-grading-evaluation/wheels",
        "title": "Duecare Grading Evaluation Wheels",
        "id": "taylorsamarel/duecare-grading-evaluation-wheels",
        "license": "CC0-1.0",
        "subtitle": (
            "v0.14.5 lift regenerator with provenance tuple "
            "(model / git_sha / dataset_version)"
        ),
        "kernel_blurb": (
            "Wheels for grading-evaluation (the lift regenerator). Bundled: "
            "duecare-llm-chat / -core / -models. Runs N curated prompts "
            "through Gemma 4 twice (harness OFF vs ON full Persona+GREP+RAG"
            "+Imports+Tools+Online) and grades both with the universal "
            "rubric v3.10 (46 dimensions, intent-aware, citation-grounding "
            "cross-reference, multi-signal matching) plus optional LLM-as-"
            "judge with evidence quotes. Emits duecare_lift_eval.json + .md "
            "with provenance tuple (model, git_sha, dataset_version). The "
            "+56.5pp number, regenerated live from a git SHA. Re-run after "
            "pushing a new wheel version to get the post-expansion number."
        ),
    },
]


def write_metadata(entry: dict[str, str]) -> tuple[Path, dict[str, object]]:
    target_dir = KAGGLE_DIR / entry["path"]
    target_path = target_dir / "dataset-metadata.json"
    if not target_dir.exists():
        raise FileNotFoundError(f"Missing wheels dir: {target_dir}")

    description = f"{SHARED_HEADER} {entry['kernel_blurb']}"

    payload: dict[str, object] = {
        "title": entry["title"],
        "id": entry["id"],
        "licenses": [{"name": entry["license"]}],
        "subtitle": entry["subtitle"],
        "description": description,
        "keywords": [
            "duecare",
            "gemma-4",
            "trafficking",
            "safety-harness",
        ],
    }

    target_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target_path, payload


def main() -> None:
    written: list[Path] = []
    for entry in APPENDIX_KERNELS:
        path, _ = write_metadata(entry)
        written.append(path)
        print(f"  updated {path.relative_to(REPO)}")

    print(f"\nTotal regenerated: {len(written)} appendix metadata files.")


if __name__ == "__main__":
    main()
