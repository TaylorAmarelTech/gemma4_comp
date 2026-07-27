#!/usr/bin/env python3
"""DueCare Pipeline Runner — chains all 8 stages end-to-end.

Stages:
  1. Acquire    — download authoritative documents (ILO, POEA, NGOs)
  2. Classify   — classify documents by type/relevance using Gemma 4
  3. Extract    — extract facts, laws, indicators using Gemma 4
  4. KB Build   — organize into structured knowledge base
  5. Generate   — create prompts from KB using Gemma 4
  6. Rate       — rate prompt quality and importance
  7. Remix      — generate adversarial variations (14 generators)
  8. Baseline   — test Gemma 4 plain vs RAG vs context injection

Usage:
    # Full pipeline (requires Ollama + Gemma 4)
    python scripts/pipeline/run_pipeline.py --all

    # Heuristic mode (no model needed, uses existing data)
    python scripts/pipeline/run_pipeline.py --all --heuristic

    # Individual stages
    python scripts/pipeline/run_pipeline.py --stages 4,5,6,7

    # Quick test (5 prompts each stage)
    python scripts/pipeline/run_pipeline.py --all --quick

    # Non-mutating local rehearsal (keeps tracked data/ artifacts unchanged)
    python scripts/pipeline/run_pipeline.py --stages 4,5,6,7 --heuristic --quick \
        --data-dir reports/pipeline-rehearsal
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

STAGES = {
    1: ("Acquire", "scripts/pipeline/stage1_acquire.py"),
    2: ("Classify", "scripts/pipeline/stage2_classify.py"),
    3: ("Extract", "scripts/pipeline/stage3_extract.py"),
    4: ("Knowledge Base", "scripts/pipeline/stage4_knowledge_base.py"),
    5: ("Generate Prompts", "scripts/pipeline/stage5_generate_prompts.py"),
    6: ("Rate & Evaluate", "scripts/pipeline/stage6_rate_evaluate.py"),
    7: ("Remix", "scripts/pipeline/stage7_remix.py"),
    8: ("Baseline Test", "scripts/pipeline/stage8_baseline_test.py"),
}


def run_stage(stage_num: int, extra_args: list[str] | None = None) -> int:
    name, script = STAGES[stage_num]
    script_path = REPO_ROOT / script

    if not script_path.exists():
        print(f"  SKIP: {script} not found")
        return 1

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"  STAGE {stage_num}: {name}")
    print(f"  Script: {script}")
    print(f"{'='*60}\n")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    elapsed = time.time() - t0

    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"\n  Stage {stage_num} {status} ({elapsed:.0f}s)")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Run all 8 stages")
    parser.add_argument("--stages", help="Comma-separated stage numbers (e.g. 4,5,6)")
    parser.add_argument("--heuristic", action="store_true", help="Use heuristic mode (no model)")
    parser.add_argument("--quick", action="store_true", help="Quick mode (5 items per stage)")
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument(
        "--data-dir",
        type=Path,
        help=(
            "Write and read every stage artifact below this directory instead of "
            "the repository data/ tree (recommended for tests and dry rehearsals)"
        ),
    )
    args = parser.parse_args(argv)

    if args.all:
        stages = list(range(1, 9))
    elif args.stages:
        stages = [int(s) for s in args.stages.split(",")]
    else:
        parser.error("Specify --all or --stages")

    # Per-stage args — each stage only gets what it supports
    stage_args_by_number: dict[int, list[str]] = {s: [] for s in range(1, 9)}
    data_dir = args.data_dir.resolve() if args.data_dir else None
    if data_dir is not None:
        acquired = data_dir / "acquired_documents" / "documents.jsonl"
        classified = data_dir / "classified_documents" / "classified.jsonl"
        facts = data_dir / "extracted_facts" / "facts.jsonl"
        knowledge_base = data_dir / "knowledge_base" / "kb.json"
        generated = data_dir / "generated_prompts" / "kb_prompts.jsonl"
        rated = data_dir / "rated_prompts" / "rated.jsonl"
        remixed = data_dir / "remixed_prompts" / "remixed.jsonl"
        baseline = data_dir / "baseline_results" / "comparison.json"
        stage_args_by_number[1].extend(["--output-dir", str(acquired.parent)])
        stage_args_by_number[2].extend(
            ["--input", str(acquired), "--output", str(classified)]
        )
        stage_args_by_number[3].extend(["--input", str(classified), "--output", str(facts)])
        stage_args_by_number[4].extend(
            ["--facts-input", str(facts), "--output", str(knowledge_base)]
        )
        stage_args_by_number[5].extend(
            ["--kb-input", str(knowledge_base), "--output", str(generated)]
        )
        stage_args_by_number[6].extend(["--input", str(generated), "--output", str(rated)])
        stage_args_by_number[7].extend(["--input", str(rated), "--output", str(remixed)])
        stage_args_by_number[8].extend(
            [
                "--prompts",
                str(remixed),
                "--kb",
                str(knowledge_base),
                "--output",
                str(baseline),
            ]
        )
    if args.heuristic:
        for s in range(1, 9):
            stage_args_by_number[s].append("--heuristic")
    if args.quick:
        stage_args_by_number[1].extend(["--max-documents", "5"])
        stage_args_by_number[2].extend(["--max-documents", "5"])
        stage_args_by_number[3].extend(["--max-documents", "5"])
        stage_args_by_number[4].extend(["--max-entries", "5"])
        stage_args_by_number[5].extend(["--max-entries", "5"])
        stage_args_by_number[6].extend(["--max-prompts", "5"])
        stage_args_by_number[7].extend(["--max-base", "5"])
        stage_args_by_number[8].extend(["--max-prompts", "5"])

    print("# DueCare Pipeline Runner")
    print(f"  Stages: {stages}")
    print(f"  Mode: {'heuristic' if args.heuristic else f'Gemma 4 ({args.model})'}")
    print(f"  Quick: {args.quick}")
    print(f"  Data: {data_dir if data_dir is not None else 'repository defaults'}")

    t0 = time.time()
    failed = []

    for stage in stages:
        if stage not in STAGES:
            print(f"  Unknown stage: {stage}")
            continue

        stage_args = list(stage_args_by_number.get(stage, []))
        if stage == 8 and not args.heuristic:
            stage_args.extend(["--model", args.model])

        rc = run_stage(stage, stage_args)
        if rc != 0:
            failed.append(stage)
            if stage < 4:
                print(
                    f"  WARNING: Stage {stage} failed but continuing "
                    "(later stages may use existing data)"
                )

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print("  PIPELINE COMPLETE")
    print(f"  Elapsed: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Stages run: {len(stages)}")
    print(f"  Failed: {len(failed)} ({failed if failed else 'none'})")
    print(f"{'='*60}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
