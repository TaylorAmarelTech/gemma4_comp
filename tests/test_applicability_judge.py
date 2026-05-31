"""Tests for the model applicability-judge (fake model_call, no keys)."""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

aj = importlib.import_module("applicability_judge")
ds = importlib.import_module("dimension_selector")

_VALID = ["pretext_resistance", "ilo_indicator", "response_quality", "made_up"]


def test_parse_filters_to_valid_groups_and_reads_sector():
    out = aj.parse('```json\n{"groups":["pretext_resistance","ilo_indicator","bogus"],'
                   '"sector":"fishing","corridor":"PH_HK"}\n```', _VALID)
    assert out["groups"] == ["pretext_resistance", "ilo_indicator"]   # bogus dropped
    assert out["sector"] == "fishing" and out["corridor"] == "PH_HK"


def test_parse_can_normalize_sector_and_gulf_corridor():
    out = aj.parse('{"groups":["response_quality"],"sector":"hotel","corridor":"PH_SA"}',
                   _VALID,
                   valid_sectors=["hospitality", "domestic_work"],
                   valid_corridors=["PH_GULF", "PH_HK"])
    assert out["sector"] == "hospitality"
    assert out["corridor"] == "PH_GULF"


def test_prompt_lists_valid_sector_and_corridor_ids():
    prompt = aj.build_prompt("message", ["response_quality"],
                             sectors=["hospitality"],
                             corridors=["PH_GULF"])
    assert "SECTORS: hospitality" in prompt
    assert "CORRIDORS: PH_GULF" in prompt
    assert "use the available *_GULF corridor ID" in prompt


def test_parse_handles_garbage():
    assert aj.parse("no json here", _VALID) == {"groups": [], "sector": "", "corridor": ""}


def test_tag_prompts_is_resumable(tmp_path):
    out = tmp_path / "tags.jsonl"
    prompts = [{"id": "p1", "text": "a"}, {"id": "p2", "text": "b"}]
    fake = lambda _t: '{"groups":["response_quality"],"sector":"","corridor":""}'
    assert aj.tag_prompts(prompts, fake, out_path=out) == 2
    assert aj.tag_prompts(prompts, fake, out_path=out) == 0          # resume: skip done
    tags = aj.load_tags(out)
    assert tags["p1"]["groups"] == ["response_quality"]


def test_judge_augments_rule_based_selection():
    dims = [{"id": "financial_obfuscation_detection.a", "group": "financial_obfuscation_detection"},
            {"id": "response_quality.a", "group": "response_quality"}]
    # rule-based: a bare worker_query meta would NOT trigger financial group...
    meta = {"category": "rights_query", "framing": "worker_query"}
    base = set(ds.relevant_dim_ids(meta, dims))
    # ...but the judge says financial applies -> it gets added (union)
    augmented = set(ds.relevant_dim_ids(meta, dims, judge={"groups": ["financial_obfuscation_detection"]}))
    assert "financial_obfuscation_detection.a" not in base
    assert "financial_obfuscation_detection.a" in augmented
