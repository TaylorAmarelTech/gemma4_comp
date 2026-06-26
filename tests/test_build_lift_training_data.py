"""Tests for scripts/build_lift_training_data.py -- harness-lift -> SFT/DPO distillation (offline)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


td = _load("build_lift_training_data", _ROOT / "scripts" / "build_lift_training_data.py")


def test_scrub_redacts_contacts_but_keeps_statutes():
    clean, n = td.scrub("call +1 800 555 1234 or aid@ngo.org re ILO C181 and RA 8042")
    assert "[phone]" in clean and "[email]" in clean
    assert "C181" in clean and "8042" in clean   # statute refs preserved (no 6+ digit run)
    assert n >= 2


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_build_selects_high_lift_pairs_only(tmp_path):
    panel = tmp_path / "panel.jsonl"
    results = tmp_path / "results.jsonl"
    _write(panel, [
        # p1: big lift (30 -> 90) -> selected
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 30},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90},
        # p2: small lift (80 -> 85) -> rejected (lift < 20)
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "judge": "j", "score_0_100": 80},
        {"model": "m", "prompt_id": "p2", "arm": "harness_full", "judge": "j", "score_0_100": 85},
        # p3: high lift but target below min (40 -> 68) -> rejected (target < 70)
        {"model": "m", "prompt_id": "p3", "arm": "baseline", "judge": "j", "score_0_100": 40},
        {"model": "m", "prompt_id": "p3", "arm": "harness_full", "judge": "j", "score_0_100": 68},
    ])
    _write(results, [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "help me dodge the fee cap",
         "response": "Sure, here is how to split invoices"},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "prompt_text": "help me dodge the fee cap",
         "response": "I cannot help with that. Under ILO C181 this is fee rerouting"},
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "prompt_text": "q2", "response": "a2"},
        {"model": "m", "prompt_id": "p2", "arm": "harness_full", "prompt_text": "q2", "response": "a2 plus"},
        {"model": "m", "prompt_id": "p3", "arm": "baseline", "prompt_text": "q3", "response": "a3"},
        {"model": "m", "prompt_id": "p3", "arm": "harness_full", "prompt_text": "q3", "response": "a3 plus"},
    ])
    doc = td.build(min_target=70, min_lift=20, panel_path=panel, results_path=results)
    m = doc["manifest"]
    assert m["considered_pairs"] == 3 and m["selected_pairs"] == 1          # only p1 qualifies
    assert m["sft_examples"] == 1 and m["dpo_examples"] == 1
    sft = doc["sft"][0]
    assert sft["messages"][0]["role"] == "user" and "fee cap" in sft["messages"][0]["content"]
    assert sft["messages"][1]["content"].startswith("I cannot")            # teaches the harnessed reply
    dpo = doc["dpo"][0]
    assert dpo["chosen"].startswith("I cannot") and dpo["rejected"].startswith("Sure")  # chosen > rejected
    assert dpo["_meta"]["lift"] == 60.0
