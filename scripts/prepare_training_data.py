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
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = REPO_ROOT / "configs" / "duecare" / "domains" / "trafficking" / "seed_prompts.jsonl"
OUTPUT_DIR = REPO_ROOT / "data" / "training"

# Gemma 4 chat template
CHAT_TEMPLATE = """<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model
{response}<end_of_turn>"""


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
    include_negative: bool = False,
    max_examples: int = 0,
) -> list[dict]:
    """Convert graded prompts to chat-format training examples."""
    examples = []

    for p in prompts:
        text = p["text"]
        responses = p.get("graded_responses", {})
        pid = p.get("id", "unknown")

        # Positive examples: grade 4 (good) and 5 (best)
        for grade_name in ["best", "good"]:
            resp = responses.get(grade_name)
            if resp:
                examples.append({
                    "text": CHAT_TEMPLATE.format(prompt=text, response=resp),
                    "prompt_id": pid,
                    "grade": grade_name,
                    "type": "positive",
                })

        # Negative examples (optional): show the model what NOT to do
        if include_negative:
            worst = responses.get("worst")
            if worst:
                # Frame as: "This is a harmful response. The correct response is..."
                best = responses.get("best", responses.get("good", ""))
                if best:
                    negative_text = (
                        f"<start_of_turn>user\n{text}<end_of_turn>\n"
                        f"<start_of_turn>model\n"
                        f"I cannot and should not respond the way a harmful model would. "
                        f"Instead, here is the responsible response:\n\n{best}"
                        f"<end_of_turn>"
                    )
                    examples.append({
                        "text": negative_text,
                        "prompt_id": pid,
                        "grade": "contrast",
                        "type": "negative",
                    })

    if max_examples > 0 and len(examples) > max_examples:
        random.shuffle(examples)
        examples = examples[:max_examples]

    return examples


def split_data(
    examples: list[dict],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split into train/val/test."""
    random.shuffle(examples)
    n = len(examples)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    return examples[:train_end], examples[train_end:val_end], examples[val_end:]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--include-negative", action="store_true", help="Include worst-grade contrastive examples")
    parser.add_argument("--max-examples", type=int, default=0, help="Cap total examples (0 = all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args(argv)

    random.seed(args.seed)

    # Load
    prompts = load_graded_prompts()
    if not prompts:
        print("No graded prompts found. Cannot create training data.")
        return 1

    # Create examples
    examples = create_training_examples(
        prompts,
        include_negative=args.include_negative,
        max_examples=args.max_examples,
    )
    print(f"Created {len(examples)} training examples")
    positive = sum(1 for e in examples if e["type"] == "positive")
    negative = sum(1 for e in examples if e["type"] == "negative")
    print(f"  Positive (good/best): {positive}")
    print(f"  Negative (contrastive): {negative}")

    # Split
    train, val, test = split_data(examples)
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    # Write
    write_jsonl(OUTPUT_DIR / "train.jsonl", train)
    write_jsonl(OUTPUT_DIR / "val.jsonl", val)
    write_jsonl(OUTPUT_DIR / "test.jsonl", test)

    # Manifest
    manifest = {
        "created_at": datetime.now().isoformat(),
        "source": str(PROMPTS_PATH),
        "n_source_prompts": len(prompts),
        "n_examples": len(examples),
        "n_positive": positive,
        "n_negative": negative,
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "include_negative": args.include_negative,
        "max_examples": args.max_examples,
        "seed": args.seed,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nWritten to {OUTPUT_DIR}/")
    print(f"  train.jsonl: {len(train)} examples")
    print(f"  val.jsonl:   {len(val)} examples")
    print(f"  test.jsonl:  {len(test)} examples")
    print(f"  manifest.json: provenance metadata")

    return 0


if __name__ == "__main__":
    sys.exit(main())
