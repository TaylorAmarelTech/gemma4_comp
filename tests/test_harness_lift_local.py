"""Tests for the local-grader harness-lift runner (no keys, no cost).

Verifies the resume + per-dimension-cell + aggregate wiring with injected fake
I/O, so the orchestration is proven without any external model or judge call.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

local = importlib.import_module("harness_lift_local")
from harness_lift_scheduled import aggregate  # noqa: E402


def _fake_io():
    """Deterministic fakes: harnessed responses grade higher than baseline."""
    def build_preamble(text: str) -> str:
        return "GROUNDING: ILO indicators + statute citations."

    def generate(model: str, prompt: str) -> str:
        return "HARNESSED REPLY" if "GROUNDING" in prompt else "bare reply"

    def grade(prompt: str, response: str) -> list[tuple[str, float]]:
        base = 8.0 if "HARNESSED" in response else 3.0
        return [("ilo.deception", base), ("quality.resources", base + 1.0)]

    return build_preamble, generate, grade


def test_run_writes_per_dimension_cells_and_is_resumable(tmp_path):
    ckpt = tmp_path / "ck.jsonl"
    prompts = [{"id": "p1", "text": "worker message one"},
               {"id": "p2", "text": "worker message two"}]
    models = ["fake-a", "fake-b"]

    n1 = local.run(prompts, models, ckpt, pace=0.0, io=_fake_io())
    # 2 prompts x 2 models x 2 arms x 2 dims = 16 cells
    assert n1 == 16

    # Re-run: every (prompt, model, arm) already has cells -> zero rework.
    n2 = local.run(prompts, models, ckpt, pace=0.0, io=_fake_io())
    assert n2 == 0


def test_aggregate_reports_positive_lift(tmp_path):
    ckpt = tmp_path / "ck.jsonl"
    prompts = [{"id": "p1", "text": "worker message"}]
    local.run(prompts, ["fake-a"], ckpt, pace=0.0, io=_fake_io())

    agg = aggregate(ckpt)
    assert agg["total_cells"] == 4  # 1 prompt x 1 model x 2 arms x 2 dims
    row = next(r for r in agg["ranked_by_lift"] if r["model"] == "fake-a")
    # baseline mean = (3+4)/2 = 3.5 ; harnessed = (8+9)/2 = 8.5 ; lift = +5.0
    assert row["baseline_mean"] == 3.5
    assert row["harnessed_mean"] == 8.5
    assert row["lift"] == 5.0


def test_no_applicable_dims_is_not_marked_done(tmp_path):
    ckpt = tmp_path / "ck.jsonl"
    prompts = [{"id": "p1", "text": "worker message"}]

    def io_no_dims():
        bp, gen, _ = _fake_io()
        return bp, gen, (lambda _p, _r: [])  # grader finds nothing applicable

    n = local.run(prompts, ["fake-a"], ckpt, pace=0.0, io=io_no_dims())
    assert n == 0
    assert not ckpt.exists() or ckpt.read_text(encoding="utf-8").strip() == ""


def test_select_prompts_uses_exact_ids_and_rejects_drift():
    prompts = [
        {"id": "p1", "text": "one"},
        {"id": "p2", "text": "two"},
        {"id": "p3", "text": "three"},
    ]

    assert [row["id"] for row in local.select_prompts(
        prompts, prompt_ids="p3,p1", limit=2
    )] == ["p3", "p1"]

    try:
        local.select_prompts(prompts, prompt_ids="p3,missing")
    except ValueError as exc:
        assert "unknown LIFT_PROMPT_IDS: missing" in str(exc)
    else:  # pragma: no cover - failure branch is the assertion
        raise AssertionError("missing prompt ID did not fail closed")
