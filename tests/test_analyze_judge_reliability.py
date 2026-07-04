"""Tests for scripts/analyze_judge_reliability.py -- inter-judge reliability of the panel (offline)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):   # multi_judge.krippendorff_alpha
    sys.path.insert(0, str(_src))

import analyze_judge_reliability as jr  # noqa: E402


def _panel(n: int = 8) -> list[dict]:
    """One model, n prompts x 3 arms x 3 judges. j_hi always +4 above consensus, j_lo -4 (systematic
    leniency); the per-cell base value varies across prompts so there is between-item variance."""
    rows = []
    for i in range(n):
        base = 40.0 + 6.0 * i            # spread across prompts -> non-zero De for alpha
        for arm in ("baseline", "harness_core", "harness_full"):
            v = base + (0 if arm == "baseline" else 20)   # harnessed arms score higher
            for judge, off in (("j_lo", -4.0), ("j_mid", 0.0), ("j_hi", 4.0)):
                s = max(0.0, min(100.0, v + off))
                rows.append({"model": "m1", "prompt_id": f"p{i}", "arm": arm, "judge": judge,
                             "score_0_100": s,
                             "components": {"A": s/5, "B": s/6, "C": s/5, "D": s/8, "E": s/8}})
    return rows


def test_overall_alpha_high_for_consistent_judges():
    a = jr.analyse(panel=_panel())
    assert a["overall_alpha"] is not None
    assert 0.5 < a["overall_alpha"] <= 1.0      # small constant offsets -> high interval agreement
    assert a["judges"] == ["j_hi", "j_lo", "j_mid"]


def test_per_arm_and_per_component_keys():
    a = jr.analyse(panel=_panel())
    assert set(a["per_arm"]) == {"baseline", "harness_core", "harness_full"}
    for arm in a["per_arm"].values():
        assert arm["alpha"] is not None and arm["n"] > 0
    assert set(a["per_component"]) == {"A", "B", "C", "D", "E"}


def test_leniency_recovers_the_systematic_offset():
    a = jr.analyse(panel=_panel())
    pj = a["per_judge"]
    assert pj["j_hi"]["leniency"] > 0     # the consistently-high judge reads as lenient
    assert pj["j_lo"]["leniency"] < 0     # the consistently-low judge reads as harsh
    assert abs(pj["j_mid"]["leniency"]) < 0.5


def test_report_renders():
    md = jr.build_report(jr.analyse(panel=_panel()))
    assert "Krippendorff's alpha" in md
    assert "Per-judge leniency" in md
