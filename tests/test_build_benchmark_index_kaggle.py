"""build_benchmark_index_kaggle: the polished Start Here front-door notebook for the collection."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_benchmark_index_kaggle", _ROOT / "scripts" / "build_benchmark_index_kaggle.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_benchmark_index_kaggle"] = mod
    spec.loader.exec_module(mod)
    return mod


b = _load()


def _nb(tmp_path):
    out = tmp_path / "out"
    b.build(out, force=True)
    nb_dir = out / "notebooks" / "duecare-harness-lift-benchmark-start-here"
    nb = json.loads((nb_dir / "notebook.ipynb").read_text(encoding="utf-8"))
    meta = json.loads((nb_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
    return nb, meta


def test_builds_valid_notebook_with_toc_and_boundary(tmp_path):
    nb, _ = _nb(tmp_path)
    assert nb["nbformat"] == 4 and nb["cells"]
    text = "\n".join("".join(c["source"]) for c in nb["cells"])
    # TOC anchors + matching section anchors
    for anchor in ("#headline", "#board", "#tour", "#reproduce", "#boundary"):
        assert anchor in text
    for aid in ('id="headline"', 'id="board"', 'id="tour"', 'id="boundary"'):
        assert aid in text
    # the honest boundary is present and prominent
    assert "does NOT" in text and "not anti-trafficking professionals" in text


def test_guided_tour_links_the_whole_collection(tmp_path):
    nb, _ = _nb(tmp_path)
    text = "\n".join("".join(c["source"]) for c in nb["cells"])
    for url in (b.DS, b.NB_REPRO, b.NB_BREAK, b.NB_ROBUST, b.NB_JUDGE, b.NB_CLAIM, b.NB_CALIB,
                b.NB_CONTROLS, b.NB_CONVERGE, b.DS_BOARD, b.DS_CONTROLS, b.REPO, b.SITE):
        assert url in text


def test_kernel_metadata_public_and_dataset_linked(tmp_path):
    _, meta = _nb(tmp_path)
    assert meta["is_private"] is False
    assert meta["enable_gpu"] is False and meta["enable_internet"] is False
    assert b.DATASET_ID in meta["dataset_sources"]
    # Kaggle derives the slug from the title; it must slugify to the id
    slug = meta["id"].split("/", 1)[1]
    assert meta["title"].lower().replace(" ", "-") == slug
