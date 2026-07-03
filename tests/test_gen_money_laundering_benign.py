"""Money-laundering benign control set (over-refusal split symmetry, propose-only).

Legitimate AML-compliance questions (SAR filing, CTR thresholds, KYC, record-keeping) a safe assistant
must HELP with; they measure whether an ML-detection harness over-refuses. Deterministic, composite,
and must pass rich_harness_lift's fail-closed benign loader.
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
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
gm = _load("gen_money_laundering_benign", _ROOT / "scripts" / "gen_money_laundering_benign.py")
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")

_PRIVATE = re.compile(r"@|\+?\d[\d ().\-]{8,}\d|\d{8,}")


def test_full_product_all_unique():
    rows = gm.generate()
    assert len(rows) == len(gm.CONTEXTS) * len(gm._topics("X")) == 72
    assert len({r["id"] for r in rows}) == len(rows)
    assert len({r["text"] for r in rows}) == len(rows)


def test_all_benign_and_clean():
    for r in gm.generate():
        assert r["id"].startswith("MLBENIGN-")
        assert r["intent"] == "benign"
        assert r["difficulty"] == "benign"
        assert len(r["text"]) > 60
        assert not _PRIVATE.search(r["text"])


def test_deterministic_and_committed_matches():
    assert gm.generate() == gm.generate()
    doc = json.loads(gm.OUT_DEFAULT.read_text(encoding="utf-8"))
    assert doc["intent"] == "benign_control"
    assert doc["prompts"] == gm.generate()


def test_passes_fail_closed_loader():
    loaded = rh.load_benign_control_prompts(gm.OUT_DEFAULT)   # raises on PII / dup / non-benign
    assert len(loaded) == len(gm.generate())
    assert all(p["intent"] == "benign" for p in loaded)
