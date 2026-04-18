#!/usr/bin/env python3
"""Prepare training data for Unsloth fine-tuning.

Converts the 74K+ seed prompts (with graded response examples) into
Unsloth chat-format JSONL suitable for supervised fine-tuning.

Strategy:
  1. Use only prompts that have graded_responses (204 prompts, 5 grades each)
  2. Training data = grade 4 (good) + grade 5 (best) responses
  3. Negative examples = grade 1 (worst) responses with "DO NOT" prefix
  4. Split: 80% train, 10% val, 10% test
  5. Augment with the DueCare test generators for diversity

Output:
  data/training/train.jsonl
  data/training/val.jsonl
  data/training/test.jsonl
  data/training/manifest.json  (provenance tracking)

Usage:
  python scripts/prepare_training_data.py
  python scripts/prepare_training_data.py --include-negative  # add worst responses as negative examples
  python scripts/prepare_training_data.py --max-examples 5000
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = REPO_ROOT / "configs" / "duecare" / "domains" / "trafficking" / "seed_prompts.jsonl"
OUTPUT_DIR = REPO_ROOT / "data" / "training"


def _bootstrap_workspace_packages() -> None:
    """Add all workspace package src roots so namespace-package imports work."""
    packages_dir = REPO_ROOT / "packages"
    for src_dir in sorted(packages_dir.glob("*/src")):
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_bootstrap_workspace_packages()

from duecare.core import (  # noqa: E402
    Provenance,
    TrainingDatasetManifest,
    TrainingExample,
    TrainingMessage,
    compute_checksum,
    generate_run_id,
    get_git_sha,
)

# Gemma 4 chat template
CHAT_TEMPLATE = """<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model
{response}<end_of_turn>"""


def render_chat(messages: list[TrainingMessage]) -> str:
    """Render structured chat messages into the Gemma/Unsloth text template."""
    rendered_parts = []
    for message in messages:
        role = "model" if message.role == "assistant" else message.role
        rendered_parts.append(
            f"<start_of_turn>{role}\n{message.content}<end_of_turn>"
        )
    return "\n".join(rendered_parts)


def _prompt_record_checksum(prompt: dict) -> str:
    """Stable checksum for the source prompt record."""
    return compute_checksum(json.dumps(prompt, sort_keys=True, default=str))


def load_graded_prompts() -> list[dict]:
    """Load only prompts that have graded response examples."""
    if not PROMPTS_PATH.exists():
        print(f"ERROR: {PROMPTS_PATH} not found")
        print("Run scripts/extract_benchmark_prompts.py first")
        sys.exit(1)

    graded = []
    total = 0
    with PROMPTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            total += 1
            p = json.loads(line)
            if p.get("graded_responses"):
                graded.append(p)

    print(f"Loaded {total:,} total prompts, {len(graded)} have graded responses")
    return graded


def create_training_examples(
    prompts: list[dict],
    *,
    run_id: str,
    git_sha: str,
    created_at: datetime,
    include_negative: bool = False,
    max_examples: int = 0,
) -> list[TrainingExample]:
    """Convert graded prompts to chat-format training examples."""
    examples: list[TrainingExample] = []

    for p in prompts:
        text = p["text"]
        responses = p.get("graded_responses", {})
        pid = p.get("id", "unknown")
        category = p.get("category", "")
        source = p.get("source", "")
        record_checksum = _prompt_record_checksum(p)
        metadata = dict(p.get("metadata", {}))
        metadata.setdefault("difficulty", p.get("difficulty", ""))
        metadata.setdefault("expected_grade", p.get("expected_grade", ""))

        # Positive examples: grade 4 (good) and 5 (best)
        for grade_name in ["best", "good"]:
            resp = responses.get(grade_name)
            if resp:
                messages = [
                    TrainingMessage(role="user", content=text),
                    TrainingMessage(role="assistant", content=resp),
                ]
                rendered = render_chat(messages)
                examples.append(
                    TrainingExample(
                        prompt_id=pid,
                        grade=grade_name,
                        type="positive",
                        text=rendered,
                        messages=messages,
                        category=category,
                        source=source,
                        source_record_ids=[pid],
                        source_record_checksums=[record_checksum],
                        metadata=metadata,
                        provenance=Provenance(
                            source_id=source,
                            source_row_id=pid,
                            run_id=run_id,
                            git_sha=git_sha,
                            workflow_id="training_prepare",
                            domain_id="trafficking",
                            ingested_at=created_at,
                            created_at=created_at,
                            ingestion_script_version="scripts/prepare_training_data.py",
                            parent_record_id=pid,
                            checksum=compute_checksum(rendered),
                        ),
                    )
                )

        # Negative examples (optional): show the model what NOT to do
        if include_negative:
            worst = responses.get("worst")
            if worst:
                # Frame as: "This is a harmful response. The correct response is..."
                best = responses.get("best", responses.get("good", ""))
                if best:
                    negative_response = (
                        "I cannot and should not respond the way a harmful model would. "
                        "Instead, here is the responsible response:\n\n"
                        f"{best}"
                    )
                    messages = [
                        TrainingMessage(role="user", content=text),
                        TrainingMessage(role="assistant", content=negative_response),
                    ]
                    rendered = render_chat(messages)
                    negative_metadata = dict(metadata)
                    negative_metadata["contrast_source_grade"] = "worst"
                    negative_metadata["harmful_reference_checksum"] = compute_checksum(worst)
                    examples.append(
                        TrainingExample(
                            prompt_id=pid,
                            grade="contrast",
                            type="negative",
                            text=rendered,
                            messages=messages,
                            category=category,
                            source=source,
                            source_record_ids=[pid],
                            source_record_checksums=[record_checksum],
                            metadata=negative_metadata,
                            provenance=Provenance(
                                source_id=source,
                                source_row_id=pid,
                                run_id=run_id,
                                git_sha=git_sha,
                                workflow_id="training_prepare",
                                domain_id="trafficking",
                                ingested_at=created_at,
                                created_at=created_at,
                                ingestion_script_version="scripts/prepare_training_data.py",
                                parent_record_id=pid,
                                checksum=compute_checksum(rendered),
                            ),
                        )
                    )

    if max_examples > 0 and len(examples) > max_examples:
        random.shuffle(examples)
        examples = examples[:max_examples]

    return examples


def split_data(
    examples: list[TrainingExample],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> tuple[list[TrainingExample], list[TrainingExample], list[TrainingExample]]:
    """Split into train/val/test."""
    random.shuffle(examples)
    n = len(examples)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    return examples[:train_end], examples[train_end:val_end], examples[val_end:]


def assign_split(examples: list[TrainingExample], split_name: str) -> None:
    """Persist split membership into each example's provenance."""
    for example in examples:
        example.provenance.split = split_name


def write_jsonl(path: Path, examples: list[TrainingExample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(
                json.dumps(
                    ex.model_dump(mode="json", by_alias=True),
                    ensure_ascii=False,
                )
                + "\n"
            )


def split_checksum(examples: list[TrainingExample]) -> str:
    """Stable checksum for one emitted JSONL split."""
    payload = "\n".join(
        json.dumps(example.model_dump(mode="json", by_alias=True), sort_keys=True)
        for example in examples
    )
    return compute_checksum(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--include-negative", action="store_true", help="Include worst-grade contrastive examples")
    parser.add_argument("--max-examples", type=int, default=0, help="Cap total examples (0 = all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args(argv)

    random.seed(args.seed)
    run_id = generate_run_id("training_prepare")
    git_sha = get_git_sha()
    created_at = datetime.now()

    # Load
    prompts = load_graded_prompts()
    if not prompts:
        print("No graded prompts found. Cannot create training data.")
        return 1

    # Create examples
    examples = create_training_examples(
        prompts,
        run_id=run_id,
        git_sha=git_sha,
        created_at=created_at,
        include_negative=args.include_negative,
        max_examples=args.max_examples,
    )
    print(f"Created {len(examples)} training examples")
    positive = sum(1 for e in examples if e.example_type == "positive")
    negative = sum(1 for e in examples if e.example_type == "negative")
    print(f"  Positive (good/best): {positive}")
    print(f"  Negative (contrastive): {negative}")

    # Split
    train, val, test = split_data(examples)
    assign_split(train, "train")
    assign_split(val, "val")
    assign_split(test, "test")
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    # Write
    write_jsonl(OUTPUT_DIR / "train.jsonl", train)
    write_jsonl(OUTPUT_DIR / "val.jsonl", val)
    write_jsonl(OUTPUT_DIR / "test.jsonl", test)

    # Manifest
    grade_distribution = Counter(example.grade for example in examples)
    type_distribution = Counter(example.example_type for example in examples)
    manifest = TrainingDatasetManifest(
        run_id=run_id,
        git_sha=git_sha,
        created_at=created_at,
        source_path=str(PROMPTS_PATH),
        source_checksum=compute_checksum(PROMPTS_PATH.read_bytes()),
        output_dir=str(OUTPUT_DIR),
        n_source_prompts=len(prompts),
        n_examples=len(examples),
        n_positive=positive,
        n_negative=negative,
        split_counts={"train": len(train), "val": len(val), "test": len(test)},
        split_checksums={
            "train": split_checksum(train),
            "val": split_checksum(val),
            "test": split_checksum(test),
        },
        grade_distribution=dict(grade_distribution),
        type_distribution=dict(type_distribution),
        include_negative=args.include_negative,
        max_examples=args.max_examples,
        seed=args.seed,
    )
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    print(f"\nWritten to {OUTPUT_DIR}/")
    print(f"  train.jsonl: {len(train)} examples")
    print(f"  val.jsonl:   {len(val)} examples")
    print(f"  test.jsonl:  {len(test)} examples")
    print(f"  manifest.json: provenance metadata")

    return 0


if __name__ == "__main__":
    sys.exit(main())
