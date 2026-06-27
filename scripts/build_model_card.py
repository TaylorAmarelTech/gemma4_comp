#!/usr/bin/env python3
"""Model-card generator -- render a publishable card from a finetune_registry provenance record.

Reads the latest finetune_registry.py record for a model_id and renders a Hugging-Face-style model
card (YAML frontmatter + markdown): base model, the reproducibility provenance (git_sha = code version,
data_manifest_sha256 = dataset version), training-data counts, eval scores, intended use, limitations,
and the privacy boundary. So the published adapter ships with a card that lets a reviewer trace it back
to the exact data + code -- the hackathon's "real, not faked: reproducible from (git_sha, dataset_version)"
invariant, made human-readable.

Propose-only + offline: reads the registry, writes reports/training/<model_id>_model_card.md (gitignored
until a real trained model is published). Reuses finetune_registry.load/latest_by_id (DRY).

    python scripts/build_model_card.py --model-id duecare-gemma-4-e4b-safetyjudge-v0.1.0
    python scripts/build_model_card.py --model-id ... --stdout      # print instead of writing
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from finetune_registry import load as _load_registry, latest_by_id as _latest_by_id  # noqa: E402

OUT_DIR = _ROOT / "reports" / "training"


def _frontmatter(record: dict) -> str:
    base = record.get("base_model", "unknown")
    return "\n".join([
        "---",
        f"base_model: {base}",
        "license: mit",
        "library_name: peft",
        "language:",
        "- en",
        "tags:",
        "- gemma",
        "- lora",
        "- safety",
        "- migrant-worker-protection",
        "- trafficking",
        "- on-device",
        "---",
    ])


def _eval_section(record: dict) -> str:
    ev = record.get("eval") or {}
    if not ev:
        return ("_Pending the GPU four-arm evaluation_ (internalisation `C-A`, internalised fraction "
                "`(C-A)/(B-A)`, and the held-out-typology generalisation gap). Run "
                "`python scripts/training_engine.py --with-gpu`, which records the scores back into the "
                "registry; regenerate this card to fill this section.")
    rows = "\n".join(f"| {k} | {v} |" for k, v in ev.items())
    return "| metric | value |\n| --- | --- |\n" + rows


def render_card(record: dict[str, Any]) -> str:
    """Render a full model card (str) from a finetune_registry record. Pure -- no I/O."""
    data = record.get("data") or {}
    mid = record.get("model_id", "unknown")
    base = record.get("base_model", "unknown")
    provenance = "\n".join([
        "| field | value |",
        "| --- | --- |",
        f"| model_id | `{mid}` |",
        f"| base_model | `{base}` |",
        f"| status | {record.get('status', 'unknown')} |",
        f"| git_sha (code version) | `{record.get('git_sha')}` |",
        f"| data_manifest_sha256 (dataset version) | `{data.get('manifest_sha256')}` |",
        f"| created_utc | {record.get('created_utc')} |",
    ])
    sft = data.get("sft_examples")
    dpo = data.get("dpo_examples")
    return "\n".join([
        _frontmatter(record),
        "",
        f"# {mid}",
        "",
        f"A LoRA fine-tune of `{base}` into an **on-device trafficking-safety judge** for migrant-worker "
        "protection. It is trained to answer like the DueCare harness: name the exploitation **indicator**, "
        "cite the controlling **law / ILO convention**, give a clear graded **action** (refuse to "
        "operationalize harm; tell the worker what to do), and point to protective **resources** -- never a "
        "bare refusal without details or citations.",
        "",
        "## Provenance (reproducible)",
        "",
        provenance,
        "",
        "Every number here is reproducible from `(git_sha, data_manifest_sha256)` -- the project's "
        '"real, not faked" invariant. The data manifest pins the exact distilled training set.',
        "",
        "## Training data",
        "",
        f"- SFT examples: **{sft if sft is not None else 'n/a'}**",
        f"- DPO examples: **{dpo if dpo is not None else 'n/a'}**",
        "- Distilled from the DueCare harness-lift benchmark (baseline vs harnessed grades), then gated so "
        "the lift teaches grounding, not refusal: a **grounding-delta** gate (the harnessed reply must add "
        "indicator+law+resources over baseline) and a **reasoning-chain** gate "
        "(indicator -> statute -> action -> resources). Exact + SimHash near-duplicate deduped; whole "
        "typologies held out for a generalisation diagnostic.",
        "",
        "## Evaluation",
        "",
        _eval_section(record),
        "",
        "## Intended use",
        "",
        "A private, local safety evaluator for NGOs and regulators who cannot send sensitive case data to "
        "frontier APIs. Runs on a laptop (llama.cpp / LiteRT). Use it to triage suspicious recruitment "
        "messages, flag ILO forced-labour indicators, and surface the controlling statute + protective "
        "resources.",
        "",
        "## Limitations & out-of-scope",
        "",
        "- **Not legal advice.** Outputs are decision support, not a determination.",
        "- **Volatile facts** (hotline numbers, current fee caps, fresh advisories) are intentionally NOT "
        "memorized -- they come from tools / retrieval, so the weights teach stable reasoning, not "
        "stale contacts.",
        "- Trained on synthetic + public benchmark data; coverage is strongest on the corridors and "
        "typologies in the training distribution.",
        "",
        "## Privacy boundary",
        "",
        "Raw worker chats, IDs, and documents stay on the local device. Only explicitly sanitized, "
        "anonymized envelopes are ever shared. The model itself adds no telemetry.",
        "",
        "## Citation",
        "",
        f"DueCare — Gemma 4 safety judge for migrant-worker protection. Model `{mid}`, base `{base}`.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-id", required=True, help="model_id to render (latest registry record wins)")
    ap.add_argument("--stdout", action="store_true", help="print the card instead of writing a file")
    ap.add_argument("--out-dir", type=pathlib.Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    latest = _latest_by_id(_load_registry())
    record = latest.get(args.model_id)
    if not record:
        have = ", ".join(sorted(latest)) or "(registry empty)"
        print(f"[model-card] no registry record for {args.model_id}; known: {have}")
        return 1
    card = render_card(record)
    if args.stdout:
        print(card)
        return 0
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.model_id}_model_card.md"
    out.write_text(card, encoding="utf-8")
    print(f"[model-card] wrote {len(card)} chars -> {out} (status={record.get('status')}, "
          f"data_sha={(record.get('data') or {}).get('manifest_sha256')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
