#!/usr/bin/env python3
# ruff: noqa: E501
"""Prep a Kaggle notebook dir for a best-packages push: enable internet, prepend a tolerant
pip-install bootstrap for top NLP/visualization packages, and leave the notebook ascii-clean-ready.

    python scripts/prep_kaggle_push.py <notebook_dir> [<notebook_dir> ...]

Idempotent. The bootstrap NEVER fails the run (check=False), and notebooks keep their in-code
try/except fallbacks, so a pip hiccup can't break publishing -- best packages when available,
guaranteed run otherwise.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

PIP_CELL = (
    "# Best-in-class NLP + visualization packages. Internet is enabled for this kernel so the\n"
    "# analysis uses the real libraries (VADER sentiment, textstat readability, wordcloud, squarify\n"
    "# treemaps) rather than lightweight fallbacks. Tolerant: a failed install never stops the run.\n"
    "import subprocess, sys as _sys\n"
    "_pkgs = ['vaderSentiment', 'textstat', 'wordcloud', 'squarify']\n"
    "subprocess.run([_sys.executable, '-m', 'pip', 'install', '-q', '--disable-pip-version-check', *_pkgs], check=False)\n"
    "print('nlp/viz package bootstrap complete')\n"
)
MARKER = "nlp/viz package bootstrap complete"


def prep(nbdir: Path) -> None:
    meta = nbdir / "kernel-metadata.json"
    m = json.loads(meta.read_text(encoding="utf-8"))
    m["enable_internet"] = True
    meta.write_text(json.dumps(m, indent=2), encoding="utf-8")
    nbp = nbdir / "notebook.ipynb"
    nb = json.loads(nbp.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    if not any(MARKER in "".join(c.get("source", [])) for c in cells):
        cells.insert(0, {"cell_type": "code", "metadata": {}, "execution_count": None,
                         "outputs": [], "source": PIP_CELL.splitlines(keepends=True)})
        nb["cells"] = cells
        nbp.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"prepped {nbdir.name}: internet=on, pip bootstrap present")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        prep(Path(arg))
