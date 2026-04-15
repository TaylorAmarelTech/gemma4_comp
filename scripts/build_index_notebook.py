"""Build the DueCare Kaggle index/table-of-contents notebook.

A single notebook judges can open first that lists every other DueCare
kernel with links, category, and a 1-line description of what it proves.

Regenerate: python scripts/build_index_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

KERNEL_DIR = Path(__file__).resolve().parent.parent / "kaggle" / "kernels" / "duecare_index"
SLUG = "taylorsamarel/duecare-index"
TITLE = "[INDEX] DueCare — Start Here: All Notebooks & Writeup"


def _md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


# Manually curated groups — authoritative ordering
KERNELS = [
    ("🚀 START HERE", [
        ("duecare-quickstart", "S1", "5-minute setup + first safety evaluation"),
        ("duecare-submission-walkthrough", "S2", "Hackathon submission flow, install → report"),
        ("duecare-cross-domain-proof", "S3", "Same harness on trafficking + tax_evasion + financial_crime"),
        ("duecare-12-agent-gemma-4-safety-pipeline", "S4", "12-agent swarm orchestrated by Gemma 4"),
    ]),
    ("📊 BASELINE — real Gemma 4 numbers", [
        ("duecare-real-gemma-4-on-50-trafficking-prompts", "B1",
         "Gemma 4 E4B on 50 trafficking prompts — **primary result**: 0.610 mean / 28% HARD_VIOLATION"),
        ("duecare-rag-comparison", "B2",
         "Plain vs retrieval-augmented vs system-guided (context lift measurement)"),
        ("duecare-phase-2-model-comparison", "B3",
         "Gemma 4 E2B vs E4B size vs safety"),
        ("duecare-22-gemma-generations", "B4",
         "Gemma 2 vs 3 vs 4 — does a new model release close the safety gap?"),
    ]),
    ("🔍 TASK — capability-specific evaluations", [
        ("duecare-adversarial-resistance", "T1", "Gemma 4 against 15 adversarial attack vectors"),
        ("duecare-function-calling-multimodal", "T2", "Native tool calls + document-photo analysis"),
        ("duecare-llm-judge-grading", "T3", "6-dimension 0-100 safety grading by Gemma 4"),
        ("duecare-conversation-testing", "T4", "Multi-turn escalation detection"),
        ("duecare-rubric-anchored-evaluation", "T5", "54-criterion pass/fail rubric"),
        ("duecare-uncensored-redteam", "T6", "Uncensored red-team: how bad is the worst output?"),
        ("duecare-context-judge", "T7", "Contextual judge — worst-response classifier"),
    ]),
    ("⚔️ COMPARE — Gemma 4 vs everything else", [
        ("gemma-4-vs-llama-vs-mistral-on-trafficking-safety", "C1",
         "Gemma 4 9B vs Llama 3.1 8B, Mistral 7B, Gemma 2 2B"),
        ("duecare-gemma-4-vs-6-oss-models-via-ollama-cloud", "C2",
         "Gemma 4 vs 6 open models via Ollama Cloud"),
        ("duecare-gemma-4-vs-mistral-family", "C3",
         "Gemma 4 vs Mistral Large 2, Small 3, Nemo, Ministral 8B, Mistral 7B"),
        ("duecare-vs-large-cloud-models", "C4",
         "DueCare vs large cloud models (via OpenRouter)"),
        ("duecare-comparative-grading", "C5",
         "Anchored grading: responses scored vs hand-written best and worst refs"),
    ]),
    ("⚙️ PIPELINE — data + curriculum production", [
        ("duecare-curating-2k-trafficking-prompts-from-74k", "P1",
         "Select 2K high-value prompts from the 74,567-prompt corpus"),
        ("duecare-15-adversarial-attack-generators-for-gemma-4", "P2",
         "Generate 15 adversarial variations per base prompt"),
        ("duecare-adversarial-prompt-factory", "P3",
         "Prompt factory: generate, validate, rank by victim impact"),
        ("duecare-rubric-pipeline", "P4",
         "Per-prompt rubric generator"),
    ]),
    ("🏗️ FINE-TUNE — Phase 3 curriculum + training", [
        ("duecare-curriculum-builder", "F1", "Locally-validated curriculum builder"),
        ("duecare-phase3-finetune", "F2", "Unsloth LoRA fine-tune + GGUF export"),
    ]),
    ("📈 REPORT", [
        ("duecare-results-dashboard", "R1", "Interactive dashboard across all evaluations"),
    ]),
]


def build() -> None:
    cells = []

    cells.append(_md(
        """# DueCare — Index

> Start here. This notebook is a table of contents for the whole DueCare
> submission: 25+ Kaggle notebooks, 8 PyPI packages, one writeup, one
> 3-minute video, one live demo on HuggingFace Spaces.

**Writeup:** [DueCare — Exercising Due Care in LLM Safety Design](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups)
**Live demo:** [huggingface.co/spaces/TaylorScottAmarel/duecare-demo](https://huggingface.co/spaces/TaylorScottAmarel/duecare-demo)
**Code:** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) (MIT)
**Model weights (pending Phase 3):** [huggingface.co/TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge](https://huggingface.co/TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge)
**Install:** `pip install duecare-llm`

Every notebook runs on free Kaggle T4 GPU or CPU. Every result traces
back to a `(git_sha, config_hash, dataset_version)` tuple.

**Privacy is non-negotiable. The lab runs on your machine.**
"""
    ))

    cells.append(_md(
        """## What DueCare is — in 30 seconds

Stock Gemma 4 E4B helps migrant-worker trafficking actors structure
exploitation in **28% of prompts** and fails to detect the framing in
another **46%**. Judges and hackathon viewers can verify this on real
Kaggle GPU in notebook B1 below (takes 15 min).

DueCare is the **agentic safety harness** that turns the same Gemma 4
E4B into a per-domain safety judge via:

1. **Domain packs** — taxonomy + rubric + evidence per safety area
   (3 shipped: `trafficking`, `tax_evasion`, `financial_crime`)
2. **12-agent swarm** orchestrated by Gemma 4 native function calling
3. **Curriculum pipeline** — generate, rank, remix, anonymize
4. **Unsloth LoRA fine-tune** — supervised training on graded responses
5. **On-device inference** — GGUF export for llama.cpp or LiteRT

Below is every notebook, grouped by purpose.
"""
    ))

    for group_name, kernels in KERNELS:
        lines = [f"## {group_name}\n", ""]
        lines.append("| Code | Title | URL |")
        lines.append("|---|---|---|")
        for slug, code, desc in kernels:
            lines.append(f"| **{code}** | {desc} | [`{slug}`](https://www.kaggle.com/code/taylorsamarel/{slug}) |")
        lines.append("")
        cells.append(_md("\n".join(lines)))

    cells.append(_md(
        """## Fast verification path — 5 minutes

If you have 5 minutes:

1. Open [B1 — Real Gemma 4 on 50 prompts](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts), click **Copy & Edit**, click **Run All**. Output `gemma_baseline_findings.json` matches the numbers in the writeup.
2. Open [S3 — Cross-domain proof](https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof) — the same harness works on `tax_evasion` and `financial_crime` with zero code changes. This is the *"we built a lab, not a model"* claim.
3. Visit the [live demo](https://huggingface.co/spaces/TaylorScottAmarel/duecare-demo), paste any suspicious recruiter message, see the grade + hotline.

If anything fails to reproduce, that's a bug — open an issue at
[github.com/TaylorAmarelTech/gemma4_comp/issues](https://github.com/TaylorAmarelTech/gemma4_comp/issues).

---

*"Privacy is non-negotiable. So the lab runs on your machine."*
"""
    ))

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "kaggle": {"accelerator": "none", "isInternetEnabled": True},
        },
        "cells": cells,
    }

    KERNEL_DIR.mkdir(parents=True, exist_ok=True)
    (KERNEL_DIR / "index.ipynb").write_text(
        json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8"
    )

    meta = {
        "id": SLUG,
        "title": TITLE,
        "code_file": "index.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
    }
    (KERNEL_DIR / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    print(f"Wrote {KERNEL_DIR / 'index.ipynb'}")
    print(f"Wrote {KERNEL_DIR / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
