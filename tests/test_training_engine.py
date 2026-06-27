"""Tests for scripts/training_engine.py -- the Phase-3 data->train->eval->register orchestrator."""
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


te = _load("training_engine", _ROOT / "scripts" / "training_engine.py")


def test_plan_order_is_the_pipeline_dag():
    names = [s["name"] for s in te.plan(model_id="m", base="b", with_gpu=False)]
    assert names == ["distill", "organize", "reason", "train", "evaluate", "register"]


def test_plan_gpu_gating_offline():
    steps = {s["name"]: s for s in te.plan(model_id="m", base="b", with_gpu=False)}
    # offline host: data-prep + register run; GPU train/evaluate are skipped (will_run False, with a reason)
    assert steps["distill"]["will_run"] and steps["organize"]["will_run"] and steps["reason"]["will_run"]
    assert steps["register"]["will_run"]
    assert not steps["train"]["will_run"] and not steps["evaluate"]["will_run"]
    assert steps["train"]["skip_reason"] and "GPU" in steps["train"]["skip_reason"]


def test_plan_gpu_gating_with_gpu():
    steps = {s["name"]: s for s in te.plan(model_id="m", base="b", with_gpu=True)}
    assert all(steps[n]["will_run"] for n in ("distill", "train", "evaluate", "register"))


def test_register_status_tracks_gpu():
    def status(with_gpu):
        reg = next(s for s in te.plan(model_id="m", base="b", with_gpu=with_gpu) if s["name"] == "register")
        return reg["cmd"][reg["cmd"].index("--status") + 1]
    assert status(False) == "planned"     # offline data-prep -> a planned run
    assert status(True) == "trained"      # GPU train ran -> a trained run


def test_run_steps_dry_run_executes_nothing():
    steps = te.plan(model_id="m", base="b", with_gpu=False)
    results = te.run_steps(steps, dry_run=True)
    by = {r["name"]: r for r in results}
    assert by["distill"]["status"] == "dry-run" and "cmd" in by["distill"]
    assert by["train"]["status"] == "skipped"          # GPU step skipped even in dry-run
    assert {r["status"] for r in results} <= {"dry-run", "skipped"}   # nothing actually executed


def test_gpu_available_returns_bool_without_raising():
    assert isinstance(te.gpu_available(), bool)        # no torch / no driver in CI -> False, never raises
