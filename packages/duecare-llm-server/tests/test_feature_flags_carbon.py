"""Smoke tests for the feature_flags + carbon helper modules.

Both modules are pure-Python add-ons that don't touch the demo path
— they're available for operators who want them and silently no-op
otherwise.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from duecare.server import carbon, feature_flags


# ─── feature_flags ─────────────────────────────────────────────────

def test_unknown_flag_is_disabled() -> None:
    assert feature_flags.is_enabled("does-not-exist", tenant="t1") is False


def test_default_true_flag_returns_true_for_any_tenant(tmp_path: Path) -> None:
    cfg = tmp_path / "flags.json"
    cfg.write_text(json.dumps({"flags": {"big-banner": {"default": True}}}))
    os.environ["DUECARE_FEATURE_FLAGS_FILE"] = str(cfg)
    feature_flags.reload()
    try:
        assert feature_flags.is_enabled("big-banner", tenant="anyone") is True
    finally:
        os.environ.pop("DUECARE_FEATURE_FLAGS_FILE", None)
        feature_flags.reload()


def test_explicit_tenant_allowlist(tmp_path: Path) -> None:
    cfg = tmp_path / "flags.json"
    cfg.write_text(json.dumps({"flags": {
        "early-access": {
            "default": False,
            "rollout": {"tenants": ["ngo-pilot"]},
        }
    }}))
    os.environ["DUECARE_FEATURE_FLAGS_FILE"] = str(cfg)
    feature_flags.reload()
    try:
        assert feature_flags.is_enabled("early-access", tenant="ngo-pilot") is True
        assert feature_flags.is_enabled("early-access", tenant="other") is False
    finally:
        os.environ.pop("DUECARE_FEATURE_FLAGS_FILE", None)
        feature_flags.reload()


def test_percent_rollout_is_stable_per_tenant(tmp_path: Path) -> None:
    cfg = tmp_path / "flags.json"
    cfg.write_text(json.dumps({"flags": {
        "ramp": {"default": False, "rollout": {"percent": 50}},
    }}))
    os.environ["DUECARE_FEATURE_FLAGS_FILE"] = str(cfg)
    feature_flags.reload()
    try:
        # Same tenant must always resolve the same way
        first = feature_flags.is_enabled("ramp", tenant="alice")
        for _ in range(20):
            assert feature_flags.is_enabled("ramp", tenant="alice") == first
        # Across many tenants, ~50% should be enabled
        enabled = sum(
            feature_flags.is_enabled("ramp", tenant=f"t{i}")
            for i in range(200)
        )
        assert 70 < enabled < 130   # ~100 ± noise
    finally:
        os.environ.pop("DUECARE_FEATURE_FLAGS_FILE", None)
        feature_flags.reload()


def test_missing_flags_file_is_safe() -> None:
    os.environ["DUECARE_FEATURE_FLAGS_FILE"] = "/no/such/path.json"
    feature_flags.reload()
    try:
        assert feature_flags.is_enabled("any", tenant="any") is False
    finally:
        os.environ.pop("DUECARE_FEATURE_FLAGS_FILE", None)
        feature_flags.reload()


# ─── carbon ────────────────────────────────────────────────────────

def test_known_model_known_region_returns_positive_estimate() -> None:
    kg = carbon.estimate_co2_kg(
        model="gemma4:e2b",
        tokens_in=10_000,
        tokens_out=10_000,
        region="us-east1",
    )
    assert kg > 0.0
    # 20k tokens * 0.10 Wh/1k = 2 Wh = 0.002 kWh
    # * 390 g/kWh = 0.78 g = 0.00078 kg
    assert kg == pytest.approx(0.00078, abs=1e-5)


def test_clean_grid_lowers_estimate() -> None:
    dirty = carbon.estimate_co2_kg("gemma4:e2b", 10_000, 10_000, "ZA")  # 850 g/kWh
    clean = carbon.estimate_co2_kg("gemma4:e2b", 10_000, 10_000, "NO")  #  25 g/kWh
    assert clean < dirty / 10


def test_unknown_region_falls_back_to_default() -> None:
    kg = carbon.estimate_co2_kg("gemma4:e2b", 1000, 1000, "asgard-1")
    # Falls back to _default = 450 g/kWh; non-zero, finite
    assert kg > 0.0
    assert kg < 1.0   # sanity: < 1 kg for 2k tokens of E2B


def test_unknown_model_uses_default_energy() -> None:
    kg = carbon.estimate_co2_kg("future-model-9000", 10_000, 10_000, "us-east1")
    assert kg > 0.0


def test_record_returns_estimate() -> None:
    kg = carbon.record(
        tenant="t1", model="gemma4:e2b",
        tokens_in=1000, tokens_out=1000,
        region="europe-west1",
    )
    assert kg >= 0.0


def test_reference_table_exposes_lookups() -> None:
    table = carbon.reference_table()
    assert "energy_wh_per_1k_tokens" in table
    assert "carbon_intensity_g_per_kwh_by_region" in table
    assert "gemma4:e2b" in table["energy_wh_per_1k_tokens"]
    assert "us-east1" in table["carbon_intensity_g_per_kwh_by_region"]
