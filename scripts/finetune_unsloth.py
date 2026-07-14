#!/usr/bin/env python3
"""Deprecated compatibility entrypoint for the former direct SFT runner.

This file intentionally does not import Unsloth or start training. The former
implementation accepted unaudited JSONL files, skipped the canonical quality
and provenance gates, and trained only the SFT stage. Use the strict training
engine or the active A-00 Kaggle workbench instead.

Usage:
    python scripts/training_engine.py --dry-run
    python scripts/training_engine.py --with-gpu

Kaggle:
    kaggle/A-00-omni-experiment-workbench
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CANONICAL_ENGINE = "python scripts/training_engine.py --with-gpu"
ACTIVE_KAGGLE_WORKBENCH = "kaggle/A-00-omni-experiment-workbench"


def main(argv: list[str] | None = None) -> int:
    """Refuse the unsafe legacy path and identify the validated replacements."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Deprecated compatibility option; the legacy config is not executed.",
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Deprecated compatibility option; no training is started.",
    )
    parser.parse_args(argv)

    print(
        "ERROR: scripts/finetune_unsloth.py is disabled because it bypassed "
        "required training gates."
    )
    print(f"Use the strict engine: {CANONICAL_ENGINE}")
    print(f"Or run the active Kaggle workbench: {ACTIVE_KAGGLE_WORKBENCH}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
