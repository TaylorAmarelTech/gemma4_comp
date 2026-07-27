#!/usr/bin/env python3
"""Sync the packaged kit engine from the single source of truth.

`scripts/_usecase_engine.py` defines ``ENGINE`` (an r-string embedded verbatim into the
self-contained Kaggle notebooks). `packages/duecare-llm-kit/src/duecare/kit/engine.py` is the
importable copy of that same code, wrapped with a module docstring + ``from __future__`` +
``import re``. This script regenerates the packaged copy from ``ENGINE`` so the two never drift.

Usage:
    python scripts/sync_kit_engine.py            # rewrite the kit engine from ENGINE
    python scripts/sync_kit_engine.py --check    # exit 1 if the kit engine is stale (CI-friendly)
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "_usecase_engine.py"
KIT = ROOT / "packages" / "duecare-llm-kit" / "src" / "duecare" / "kit" / "engine.py"

HEADER = (
    '"""DueCare indicator engine.\n'
    "\n"
    "Single source of truth: this file is kept in sync with scripts/_usecase_engine.py ENGINE\n"
    "(the string embedded into the self-contained Kaggle notebooks). Representative subset of the\n"
    "real GREP layer + ILO knowledge packs. Deterministic, stdlib-only. ASCII.\n"
    '"""\n'
    "from __future__ import annotations\n"
    "\n"
    "import re\n"
    "\n"
)


def _render() -> str:
    engine = runpy.run_path(str(SRC))["ENGINE"]
    body = engine
    lead = "import re\n\n"
    if body.startswith(lead):
        body = body[len(lead):]
    return HEADER + body


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sync duecare.kit.engine from scripts/_usecase_engine.ENGINE")
    ap.add_argument("--check", action="store_true", help="exit 1 if the kit engine is stale")
    args = ap.parse_args(argv)

    rendered = _render()
    current = KIT.read_text(encoding="utf-8") if KIT.exists() else ""
    if args.check:
        if rendered != current:
            print("STALE: duecare.kit.engine differs from scripts/_usecase_engine.ENGINE; run scripts/sync_kit_engine.py")
            return 1
        print("OK: duecare.kit.engine is in sync with ENGINE")
        return 0
    if rendered == current:
        print("already in sync")
        return 0
    KIT.write_text(rendered, encoding="utf-8")
    print(f"synced {KIT.relative_to(ROOT)} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
