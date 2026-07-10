"""Judge-side negative control: the fabrication canary must reward a grounded reply over a reply that
cites an INVENTED statute, and the diverse framings (esp. faithfulness) should punish fabrication more."""
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
fc = _load("fabrication_canary", _ROOT / "scripts" / "fabrication_canary.py")


def test_canary_set_is_composite_with_invented_statutes_in_gamed_only():
    for sc in fc.CANARY_SET:
        assert {"id", "prompt", "grounded", "gamed"} <= set(sc)
        # the grounded reply cites a real ILO instrument (or the UN Migrant Workers Convention)
        assert ("No. 29" in sc["grounded"] or "No. 95" in sc["grounded"] or "No. 181" in sc["grounded"]
                or "No. 189" in sc["grounded"] or "Migrant Workers Convention" in sc["grounded"])
    joined_gamed = " ".join(sc["gamed"] for sc in fc.CANARY_SET)
    assert "No. 329" in joined_gamed or "Global Wage Security" in joined_gamed   # invented instruments


def _fooled_by_specificity_caller():
    """A judge that rewards SURFACE TOKENS: it scores any reply that name-drops a 'Convention'/'Article'
    the same, UNLESS the faithfulness framing (which asks about fabrication) is used -- then it drops the
    gamed reply. So the canary must show a bigger penalty under faithfulness than under the specificity framings."""
    def caller(prompt, *, model, max_tokens=0, **kw):
        m = re.search(r'"([A-F])"\s*:\s*<', prompt)
        key = m.group(1) if m else "A"
        mx = dict(fc.components_for_version("v1")).get(key, 20)
        has_tokens = ("Convention" in prompt or "Article" in prompt or "Section" in prompt
                      or "Code" in prompt or "Act" in prompt)
        faithfulness = "FACT-CHECKER" in prompt          # framing 4
        gamed = ("329" in prompt or "Global Wage Security" in prompt or "Household Employment Code" in prompt
                 or "Recruitment Fairness Code" in prompt or "22-D" in prompt)
        if faithfulness and gamed:
            val = 0.1 * mx                               # the fact-checker catches the invented statute
        elif has_tokens:
            val = 0.8 * mx                               # every other lens is fooled by the token presence
        else:
            val = 0.3 * mx
        return json.dumps({key: round(val), "reason": "x"})
    return caller


def test_faithfulness_framing_penalises_fabrication_more_than_specificity():
    res = fc.run_canary("mistral:mistral-small-latest", [0, 1, 2, 3, 4, 5],
                        caller=_fooled_by_specificity_caller())
    by = {r["framing"]: r for r in res["by_framing"]}
    # faithfulness (framing 4) drops the gamed reply -> a large penalty; specificity framings do not
    assert by[4]["fabrication_penalty"] > by[0]["fabrication_penalty"]
    assert res["diverse_penalty"] > res["specificity_penalty"]      # the added lenses catch the gaming


def test_run_canary_refuses_same_family_judge():
    rc = fc.main(["--judge", "gemma:whatever"])
    assert rc == 2                                                   # self-family judge -> refuse
