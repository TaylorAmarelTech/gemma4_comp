"""Framing-sensitivity / overfitting probe: grade each dimension under EACH question framing separately
and expose whether the specificity framings inflate the lift versus the diverse lenses."""
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
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))
mj = _load("multi_judge", _ROOT / "scripts" / "multi_judge.py")
fs = _load("grading_framing_sensitivity", _ROOT / "scripts" / "grading_framing_sensitivity.py")


def test_framing_bank_is_nine_semantically_distinct_wrappers():
    fr = mj._COMPONENT_QUESTION_FRAMINGS
    assert len(fr) == 9                                   # 3 specificity (0-2) + 6 diverse lenses (3-8)
    assert len(set(fr)) == 9                              # all distinct
    assert all("{f_note}" in f for f in fr)              # every framing keeps the F-channel note slot
    # framings 0-2 key on specificity; 3-8 introduce genuinely different lenses
    assert "WORKER'S point of view" in fr[3]
    assert "FACT-CHECKER" in fr[4]
    assert "DEDUCTION" in fr[5]
    assert "SKEPTICAL" in fr[6]                           # new: hold-up-under-scrutiny lens
    assert "COUNTERFACTUAL" in fr[7]                      # new: harm-if-this-were-absent lens
    assert "ACCESSIBILITY" in fr[8]                       # new: plain-language / can-the-worker-use-it lens
    assert fs.DIVERSE_FRAMINGS == (3, 4, 5, 6, 7, 8)     # the probe averages all six diverse lenses


def _biased_caller():
    """Scores the harnessed reply far above baseline under the SPECIFICITY framings (0-2) but only
    slightly above under the DIVERSE framings (3-5) -- i.e. a reply that games surface tokens. So the
    probe must surface a positive specificity-minus-diverse overfit gap."""
    def caller(prompt, *, model, max_tokens=0, **kw):
        m = re.search(r'"([A-F])"\s*:\s*<', prompt)      # the single-key schema names the component
        key = m.group(1) if m else "A"
        harnessed = "HARNESSED" in prompt
        diverse = any(s in prompt for s in ["WORKER'S point of view", "FACT-CHECKER", "DEDUCTION",
                                            "SKEPTICAL", "COUNTERFACTUAL", "ACCESSIBILITY"])
        val = 5 + (3 if diverse else 15) if harnessed else 5
        return json.dumps({key: val, "reason": "x"})
    return caller


def test_new_diverse_framings_are_bucketed_as_diverse_not_specificity():
    # the three added lenses (6 skeptic, 7 harm-if-absent, 8 plain-language) must score in the DIVERSE bucket
    prompts = {"P1": "worker q"}
    responses = {"P1": {"baseline": "plain", "harness_core": "HARNESSED reply"}}
    res = fs.sensitivity(list(prompts), prompts, responses, judge="mistral:mistral-small-latest",
                         framings=[0, 6, 7, 8], caller=_biased_caller())
    a = {r["dim"]: r for r in res["by_dim"]}["A"]
    pf = dict(a["per_framing"])
    assert pf[0][0] == 15.0                               # framing 0 = specificity -> inflated lift
    assert pf[6][0] == 3.0 and pf[7][0] == 3.0 and pf[8][0] == 3.0   # the new lenses see the honest 3


def test_grade_one_returns_none_when_key_missing():
    def caller(prompt, *, model, max_tokens=0, **kw):
        return json.dumps({"reason": "no score key here"})
    assert fs.grade_one("q", "r", "A", 25, framing=0, model="m",
                        caller=caller, rubric_version="v1") is None       # non-grade -> None, not 0


def test_sensitivity_surfaces_specificity_overfit_gap():
    prompts = {"P1": "worker q", "P2": "worker q2"}
    responses = {p: {"baseline": "plain", "harness_core": "HARNESSED reply"} for p in prompts}
    res = fs.sensitivity(list(prompts), prompts, responses, judge="mistral:mistral-small-latest",
                         framings=[0, 1, 2, 3, 4, 5], caller=_biased_caller())
    by = {r["dim"]: r for r in res["by_dim"]}
    assert set(by) >= {"A", "B", "C", "D", "E"}                          # every v1 dimension reported
    a = by["A"]
    assert a["per_framing"][0][0] == 15.0 and a["per_framing"][3][0] == 3.0   # spec lift 15, diverse 3
    assert a["specificity_mean"] == 15.0 and a["diverse_mean"] == 3.0
    assert a["overfit_gap"] == 12.0                                      # 15 - 3: specificity inflates the lift
    assert a["spread"] == 12.0                                           # max(15) - min(3) across framings


def test_sensitivity_no_gap_when_lens_agnostic():
    """A reply whose lift is identical across every framing yields ~0 overfit gap (the robust case)."""
    def flat(prompt, *, model, max_tokens=0, **kw):
        m = re.search(r'"([A-F])"\s*:\s*<', prompt)
        key = m.group(1) if m else "A"
        return json.dumps({key: (18 if "HARNESSED" in prompt else 6), "reason": "x"})
    prompts = {"P1": "q"}
    responses = {"P1": {"baseline": "plain", "harness_core": "HARNESSED"}}
    res = fs.sensitivity(["P1"], prompts, responses, judge="mistral:mistral-small-latest",
                         framings=[0, 1, 2, 3, 4, 5], caller=flat)
    by = {r["dim"]: r for r in res["by_dim"]}
    assert by["A"]["overfit_gap"] == 0.0 and by["A"]["spread"] == 0.0    # lens-agnostic -> no gap, no spread
