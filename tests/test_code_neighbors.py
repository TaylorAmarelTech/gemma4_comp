"""Tests for scripts/code_neighbors.py -- the lexical-semantic 'similar files' tool."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cn = _load("code_neighbors", _ROOT / "scripts" / "code_neighbors.py")


def test_tokenize_drops_stopwords_and_tiny_tokens():
    toks = cn.tokenize("def fetch_orders(self): return order_total + tax_rate")
    assert "fetch_orders" in toks and "order_total" in toks and "tax_rate" in toks
    assert "def" not in toks and "self" not in toks and "return" not in toks  # stopwords gone


def test_cosine_identical_and_disjoint():
    a = {"fee": 0.5, "passport": 0.5}
    assert abs(cn.cosine(a, a) - 1.0) < 1e-9
    assert cn.cosine(a, {"vessel": 1.0}) == 0.0
    assert cn.cosine({}, a) == 0.0


def test_similar_files_ranks_nearest_first():
    p1, p2, p3 = Path("a.py"), Path("b.py"), Path("c.py")
    vecs = {
        p1: {"recruitment": 0.6, "fee": 0.4, "agency": 0.5},
        p2: {"recruitment": 0.6, "fee": 0.4, "agency": 0.4},   # near-duplicate of p1
        p3: {"vessel": 0.7, "fishing": 0.6},                   # unrelated
    }
    ranked = cn.similar_files(p1, vecs, top=8)
    assert ranked[0][0] == p2                                   # nearest first
    assert ranked[0][1] > (ranked[1][1] if len(ranked) > 1 else 0)
    assert p1 not in [p for p, _ in ranked]                     # target excluded


def test_imports_of_keeps_only_duecare_and_scripts(tmp_path):
    f = tmp_path / "m.py"
    f.write_text(
        "import os\nimport json\nfrom duecare.chat.harness import GREP_RULES\n"
        "from duecare.core import contracts\nimport scripts.entity_edges\n"
        "from ..model_interface import call_model_backend\nfrom . import base\n",
        encoding="utf-8")
    mods = cn.imports_of(f)
    assert "duecare.chat.harness" in mods and "duecare.core" in mods
    assert "scripts.entity_edges" in mods
    assert "..model_interface" in mods and "." in mods         # relative imports kept
    assert "os" not in mods and "json" not in mods             # stdlib filtered out


def test_module_of_strips_src_prefix():
    p = Path("packages/duecare-llm-chat/src/duecare/chat/harnesses/triage/handler.py")
    assert cn._module_of(p) == "duecare.chat.harnesses.triage.handler"
