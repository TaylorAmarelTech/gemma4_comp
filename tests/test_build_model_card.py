"""Tests for scripts/build_model_card.py -- render a provenance model card from a registry record."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))   # so the sibling finetune_registry import resolves


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bmc = _load("build_model_card", _ROOT / "scripts" / "build_model_card.py")


def _rec(**kw):
    base = {"model_id": "duecare-x-v0.1.0", "base_model": "google/gemma-4-e4b-it", "status": "trained",
            "git_sha": "abc1234", "created_utc": "2026-06-27T00:00:00+00:00",
            "data": {"manifest_sha256": "deadbeef12345678", "sft_examples": 2613, "dpo_examples": 2613},
            "eval": {}}
    base.update(kw)
    return base


def test_render_card_frontmatter_and_provenance():
    card = bmc.render_card(_rec())
    assert card.startswith("---")                                  # YAML frontmatter for HF
    assert "base_model: google/gemma-4-e4b-it" in card
    assert "duecare-x-v0.1.0" in card and "abc1234" in card and "deadbeef12345678" in card  # reproducibility
    assert "2613" in card                                          # training counts surfaced
    assert "Not legal advice" in card and "Privacy boundary" in card


def test_render_card_eval_pending_then_present():
    pending = bmc.render_card(_rec(eval={}))
    assert "Pending the GPU four-arm evaluation" in pending
    scored = bmc.render_card(_rec(eval={"internalisation": 12.3, "generalisation_gap": 4.1}))
    assert "internalisation" in scored and "12.3" in scored and "Pending the GPU" not in scored


def test_render_card_minimal_record_no_crash():
    card = bmc.render_card({"model_id": "m"})                      # missing base/data/eval -> .get fallbacks
    assert "# m" in card and "n/a" in card                        # counts fall back to n/a, no KeyError
