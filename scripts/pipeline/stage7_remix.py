#!/usr/bin/env python3
"""Stage 7: Remix prompts and their tests using all 14 generators.

Takes the rated prompt set from Stage 6 and runs it through all 14
DueCare generators to create adversarial variations. Each variation
is a new test that probes a different attack vector against the same
underlying exploitation scenario.

From N base prompts, this produces up to N × 14 variations.

Usage:
    python scripts/pipeline/stage7_remix.py --max-base 100 --variations-per-gen 2
    python scripts/pipeline/stage7_remix.py --generators evasion,coercion,persona
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=REPO_ROOT / "data" / "rated_prompts" / "rated.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "remixed_prompts" / "remixed.jsonl")
    parser.add_argument("--max-base", type=int, default=100, help="Max base prompts to remix")
    parser.add_argument("--variations-per-gen", type=int, default=1)
    parser.add_argument("--generators", default="all", help="Comma-separated generator names or 'all'")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--heuristic", action="store_true", help="(ignored, pipeline compat)")
    args = parser.parse_args(argv)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Load base prompts
    if not args.input.exists():
        # Fall back to seed prompts
        alt = REPO_ROOT / "configs" / "duecare" / "domains" / "trafficking" / "seed_prompts.jsonl"
        if alt.exists():
            base_prompts = []
            for line in alt.open("r", encoding="utf-8"):
                p = json.loads(line)
                if p.get("graded_responses"):
                    base_prompts.append(p)
                if len(base_prompts) >= args.max_base:
                    break
            print(f"Using {len(base_prompts)} graded seed prompts (rated.jsonl not found)")
        else:
            print("ERROR: No prompts found. Run earlier pipeline stages first.")
            return 1
    else:
        base_prompts = [json.loads(line) for line in args.input.open("r", encoding="utf-8")]
        base_prompts = base_prompts[:args.max_base]
        print(f"Loaded {len(base_prompts)} base prompts")

    # Load generators
    from duecare.tasks.generators import ALL_GENERATORS

    if args.generators != "all":
        names = [n.strip().lower() for n in args.generators.split(",")]
        generators = [g for g in ALL_GENERATORS if g.__class__.__name__.lower().replace("generator", "") in names]
    else:
        generators = ALL_GENERATORS

    print(f"# Stage 7: Remix with {len(generators)} generators")
    print(f"  Base prompts: {len(base_prompts)}")
    print(f"  Variations per generator: {args.variations_per_gen}")

    # Generate variations
    all_variations = list(base_prompts)  # Include originals
    for gen in generators:
        name = gen.__class__.__name__
        variations = gen.generate(base_prompts, n_variations=args.variations_per_gen, seed=args.seed)
        all_variations.extend(variations)
        print(f"  {name}: {len(variations)} variations")

    # Save
    with args.output.open("w", encoding="utf-8") as f:
        for p in all_variations:
            f.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")

    print(f"\n  Original: {len(base_prompts)}")
    print(f"  Generated: {len(all_variations) - len(base_prompts)}")
    print(f"  Total: {len(all_variations)}")
    print(f"  Saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
