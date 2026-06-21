"""Tests for scripts/dev_review_loop.py -- the multi-persona review board.

Offline: the model call is injected, so no network / API key is needed. Covers a persona's
structured review, the cross-lens synthesis ranking, cross-review, and an end-to-end run.
"""
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


d = _load("dev_review_loop", _ROOT / "scripts" / "dev_review_loop.py")


def _fake(prompt, **kw):
    if '"agree"' in prompt or "did they MISS" in prompt:      # cross-review prompt
        return '{"agree": ["the video matters"], "dispute": [], "missed": ["cost model"]}'
    return ('{"strengths": ["real harness"], "weaknesses": ["thin PMF"], '
            '"top_improvements": [{"title": "Polish the video", "why": "70 pts live there", '
            '"effort": "M"}], "pmf_or_rubric_score_0_10": 7, "verdict": "solid but unproven"}')


def test_review_returns_structured_critique():
    r = d.review("cto", "DIGEST", caller=_fake)
    assert r["persona"] == "cto" and r["model"] == d.PERSONAS["cto"]["model"]
    assert r["score"] == 7 and r["verdict"].startswith("solid")
    assert r["top_improvements"][0]["title"] == "Polish the video"


def test_synthesize_ranks_by_cross_persona_demand():
    reviews = [
        {"persona": "ceo", "top_improvements": [{"title": "Polish the video", "effort": "M"}]},
        {"persona": "yc_partner", "top_improvements": [{"title": "polish the VIDEO", "why": "x"}]},
        {"persona": "cto", "top_improvements": [{"title": "Add tests", "effort": "S"}]},
    ]
    pri = d.synthesize(reviews)
    assert pri[0]["title"] in {"Polish the video", "polish the VIDEO"}   # 2 personas -> ranks first
    assert pri[0]["n"] == 2 and set(pri[0]["raised_by"]) == {"ceo", "yc_partner"}


def test_cross_review_reacts_to_another_persona():
    c = d.cross_review("cfo", {"persona": "cto", "weaknesses": ["w"], "top_improvements": []},
                       caller=_fake)
    assert c["reviewer"] == "cfo" and c["target"] == "cto"
    assert "cost model" in c["missed"]


def test_run_offline_end_to_end():
    res = d.run(["cto", "yc_partner"], caller=_fake)
    assert len(res["reviews"]) == 2
    assert res["prioritized"] and res["cross_review"]        # synthesis + cross pass populated


def test_digest_is_nonempty_and_bounded():
    dig = d.gather_digest(max_chars=4000)
    assert 100 < len(dig) <= 4000                            # reads real project docs, capped
