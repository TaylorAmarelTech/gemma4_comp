"""Adversarial money-laundering scheme prompts (cross-domain MVP, propose-only).

gen_money_laundering_prompts reuses the 20 GREP-pack indicators as the scheme basis and wraps each in
an operator voice + pretext framings across regulatory contexts. Deterministic, composite (no PII),
and the committed jsonl is regeneratable.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
gm = _load("gen_money_laundering_prompts", _ROOT / "scripts" / "gen_money_laundering_prompts.py")

_PRIVATE = re.compile(r"@|\+?\d[\d ().\-]{8,}\d|\d{8,}")


def test_full_product_all_unique():
    rows = gm.generate()
    assert len(rows) == len(gm.GREP_RULES) * len(gm.CONTEXTS) * len(gm.FRAMINGS) == 600
    assert len({r["id"] for r in rows}) == len(rows)
    assert len({r["text"] for r in rows}) == len(rows)


def test_fields_and_no_pii():
    for r in gm.generate():
        assert r["id"].startswith("MLSCHEME-")
        assert r["category"].startswith("ml_")
        assert r["framing"] in {f[0] for f in gm.FRAMINGS}
        assert r["difficulty"] in ("hard", "very_hard")
        assert r["source"] == "ml_scheme"
        assert len(r["text"]) > 120
        assert not _PRIVATE.search(r["text"])


def test_deterministic_and_committed_matches():
    assert gm.generate() == gm.generate()
    committed = [json.loads(l) for l in gm.OUT_DEFAULT.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert committed == gm.generate()


def test_prompts_reference_real_aml_regimes():
    text = " ".join(r["text"] for r in gm.generate())
    for token in ("Bank Secrecy Act", "AMLD", "Proceeds of Crime Act", "FATF"):
        assert token in text
