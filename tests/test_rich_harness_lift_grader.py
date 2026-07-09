"""The opt-in --grader flag: judge_panel routes to the batched or the per-dimension grader.

Taylor's rigor rule is "a single prompt for EACH dimension". judge_components (batched) sends ONE
judge call scoring all components; judge_components_perdim sends ONE call PER component. This test
proves judge_panel honours the selected grader by counting judge_caller invocations per cell -- with
1 result row x 1 judge (= 1 cell): batched makes 1 call, per-dim makes 5 (v1: A-E). Offline; the judge
caller is a fake, no network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_src))
rh = _load("rich_harness_lift", _ROOT / "scripts" / "rich_harness_lift.py")

_RESULTS = [{"model": "candidate", "prompt_id": "D1", "arm": "baseline",
             "prompt_text": "q", "response": "a"}]
# a fake judge that returns every component key each call, so per-dim can extract whichever it asked for
_ALL_COMPS = '{"A":20,"B":15,"C":18,"D":8,"E":9,"score":70}'


def _counting_caller():
    calls: list[str] = []

    def caller(prompt, *, model, max_tokens=0, **kw):
        calls.append(prompt)
        return _ALL_COMPS

    return calls, caller


def test_batched_grader_is_one_call_for_all_dimensions(tmp_path):
    calls, caller = _counting_caller()
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=caller,
                       pace=0.0, log=lambda _m: None)                 # default grader = batched
    assert n == 1
    assert len(calls) == 1                                            # one judge call scores all A-E


def test_perdim_grader_is_one_call_per_dimension(tmp_path):
    calls, caller = _counting_caller()
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=caller,
                       pace=0.0, log=lambda _m: None, grader=rh.judge_components_perdim)
    assert n == 1
    assert len(calls) == 5                                            # one judge call PER dimension (A-E)


def test_grader_none_defaults_to_batched_and_honours_monkeypatch(tmp_path, monkeypatch):
    """grader=None resolves to the module-global judge_components at CALL time, so a monkeypatch of it
    (the existing test suite's mechanism) still takes effect."""
    used = {}

    def fake_components(prompt, response, *, model, caller, domain_spec, rubric_version):
        used["hit"] = True
        return {"score": 88.0, **{k: 1.0 for k, _l, _m in rh.COMPONENTS}}

    monkeypatch.setattr(rh, "judge_components", fake_components)
    n = rh.judge_panel(_RESULTS, ["judge"], panel_path=tmp_path / "panel.jsonl", judge_caller=None,
                       pace=0.0, log=lambda _m: None)                 # grader=None -> monkeypatched batched
    assert n == 1 and used.get("hit") is True
