"""Tests for scripts/train_lift_distill.py -- Phase 3 Unsloth runner (CPU-safe paths only).

The GPU train() path needs unsloth/trl/torch + CUDA and is not exercised here; these cover the
data loading, validation, message normalisation, chat-template rendering, and plan construction.
"""
from __future__ import annotations

import argparse
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


tr = _load("train_lift_distill", _ROOT / "scripts" / "train_lift_distill.py")


def test_normalize_messages_maps_assistant_and_wraps_content():
    out = tr.normalize_messages([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "I cannot help with that"},
    ])
    assert out[0]["role"] == "user" and out[1]["role"] == "model"   # assistant -> model
    assert out[0]["content"] == [{"type": "text", "text": "hi"}]    # str -> [{type,text}]
    assert out[1]["content"][0]["text"].startswith("I cannot")


def test_validate_counts_valid_and_flags_empty():
    sft = [
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},  # ok
        {"messages": [{"role": "user", "content": "q only"}]},                                     # no assistant
    ]
    dpo = [
        {"prompt": "p", "chosen": "good", "rejected": "bad"},   # ok
        {"prompt": "p", "chosen": "", "rejected": "bad"},        # empty chosen
    ]
    v = tr.validate(sft, dpo)
    assert v["sft_valid"] == 1 and v["dpo_valid"] == 1
    assert v["ok"] is True   # at least some valid rows, no blocking issue


def test_validate_fails_when_no_data():
    v = tr.validate([], [])
    assert v["ok"] is False and v["issues"]


def test_render_sft_applies_template_and_strips_bos():
    rows = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    seen = {}

    def fake_apply(msgs):
        seen["roles"] = [m["role"] for m in msgs]
        return "<bos>RENDERED"

    out = tr.render_sft(rows, fake_apply)
    assert out == [{"text": "RENDERED"}]               # <bos> stripped
    assert seen["roles"] == ["user", "model"]          # normalized before templating


def test_build_plan_test_run_overrides_steps():
    ns = argparse.Namespace(
        base_model="unsloth/gemma-4-E2B-it", sft=Path("s"), dpo=Path("d"), out=Path("o"),
        max_seq=2048, epochs=2, max_steps=-1, batch=2, grad_accum=4, lr=2e-4,
        lora_r=16, lora_alpha=16, skip_dpo=False, dpo_beta=0.1, dpo_max_steps=200,
        dpo_lr=5e-6, rpo_alpha=1.0, gguf=False, test_run=True,
    )
    plan = tr.build_plan(ns)
    assert plan["sft"]["max_steps"] == 20 and plan["sft"]["epochs"] == 1   # test-run overrides
    assert plan["dpo"]["enabled"] is True and plan["dpo"]["max_steps"] == 10
    assert plan["base_model"] == "unsloth/gemma-4-E2B-it"
    # DPO truncation lengths are set (the silent length-bias fix) + the tunable knobs
    assert plan["dpo"]["lr"] == 5e-6 and plan["dpo"]["rpo_alpha"] == 1.0
    assert plan["dpo"]["max_length"] == 2048 and plan["dpo"]["max_prompt_length"] == 1024
