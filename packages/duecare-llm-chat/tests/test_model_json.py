"""Tests for ``duecare.chat._model_json``.

Covers the failure shapes the v4 process harness hit when Gemma's
edge-extraction pass returned a 7-minute response that was *almost*
JSON but wrapped in markdown fences, with trailing commas, or with
prose before/after the JSON block. The historical regex extractor
silently failed on each of these; the new extractor recovers them
and exposes a diagnostic ``attempts`` log when it cannot.
"""
from __future__ import annotations

from duecare.chat._model_json import (
    extract_json,
    extract_json_object,
)


class TestHappyPath:
    def test_strict_json_object(self) -> None:
        result = extract_json('{"a": 1, "b": "two"}')
        assert result.ok
        assert result.payload == {"a": 1, "b": "two"}
        assert "parsed via strict json.loads" in result.attempts

    def test_strict_json_array(self) -> None:
        result = extract_json("[1, 2, 3]")
        assert result.ok
        assert result.payload == [1, 2, 3]

    def test_nested_object(self) -> None:
        text = '{"edges": [{"src": "a", "tgt": "b"}], "n": 1}'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {
            "edges": [{"src": "a", "tgt": "b"}],
            "n": 1,
        }


class TestMarkdownFences:
    def test_strip_json_fenced_block(self) -> None:
        text = '```json\n{"a": 1}\n```'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": 1}
        assert "stripped markdown code fence" in result.attempts

    def test_strip_bare_fenced_block(self) -> None:
        text = "```\n{\"edges\": []}\n```"
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"edges": []}

    def test_prose_then_fenced_json(self) -> None:
        text = (
            "Here is the requested JSON edge contract:\n\n"
            "```json\n"
            '{"edges": [{"src": "case:123", "tgt": "rule:fee"}]}\n'
            "```\n\n"
            "Let me know if you want different fields."
        )
        result = extract_json(text)
        assert result.ok
        assert result.payload["edges"][0]["src"] == "case:123"


class TestProseAroundJson:
    def test_leading_prose(self) -> None:
        text = "Sure thing -- here's the JSON:\n{\"a\": 1}"
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": 1}
        assert any("trimmed" in a for a in result.attempts)

    def test_trailing_prose(self) -> None:
        text = '{"a": 1}\n\nThat covers the main edges.'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": 1}

    def test_prose_around_array(self) -> None:
        text = "Here you go: [1, 2, 3] -- three numbers."
        result = extract_json(text)
        assert result.ok
        assert result.payload == [1, 2, 3]


class TestLightRepair:
    def test_trailing_comma_object(self) -> None:
        text = '{"a": 1, "b": 2,}'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": 1, "b": 2}
        assert "parsed after light repair" in result.attempts

    def test_trailing_comma_array(self) -> None:
        text = "[1, 2, 3,]"
        result = extract_json(text)
        assert result.ok
        assert result.payload == [1, 2, 3]

    def test_python_none(self) -> None:
        text = '{"a": None, "b": 1}'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": None, "b": 1}

    def test_python_true_false(self) -> None:
        text = '{"on": True, "off": False}'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"on": True, "off": False}

    def test_does_not_touch_string_named_None(self) -> None:
        text = '{"label": "None of the above"}'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"label": "None of the above"}


class TestSingleQuoteRepair:
    def test_python_repr_style(self) -> None:
        text = "{'edges': [{'src': 'a', 'tgt': 'b'}]}"
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"edges": [{"src": "a", "tgt": "b"}]}


class TestFailureModes:
    def test_empty_input(self) -> None:
        result = extract_json("")
        assert not result.ok
        assert "empty input" in result.attempts

    def test_no_json_at_all(self) -> None:
        result = extract_json("This response is just prose.")
        assert not result.ok
        assert "no balanced { ... } or [ ... ] span found" in result.attempts

    def test_unparseable_garbage(self) -> None:
        result = extract_json('{"a": @@@}')
        assert not result.ok
        # raw_preview should preserve the first chars for diagnostics.
        assert "@@@" in result.raw_preview


class TestPicksFirstValue:
    def test_picks_object_when_object_comes_first(self) -> None:
        text = '{"a": 1}\n[1, 2]'
        result = extract_json(text)
        assert result.ok
        assert result.payload == {"a": 1}

    def test_picks_array_when_array_comes_first(self) -> None:
        text = "[1, 2]\n{\"a\": 1}"
        result = extract_json(text)
        assert result.ok
        assert result.payload == [1, 2]


class TestBackCompatShim:
    def test_extract_json_object_returns_dict(self) -> None:
        assert extract_json_object('{"a": 1}') == {"a": 1}

    def test_extract_json_object_returns_none_for_array(self) -> None:
        # The legacy shim only returns dicts, mirroring the old
        # _extract_json_object semantics in handler.py.
        assert extract_json_object("[1, 2, 3]") is None

    def test_extract_json_object_returns_none_for_garbage(self) -> None:
        assert extract_json_object("not json") is None


class TestExtractedJsonDataclass:
    def test_raw_preview_truncated(self) -> None:
        big = "x" * 5000
        result = extract_json(big)
        assert len(result.raw_preview) <= 600
        assert not result.ok

    def test_attempts_list_is_always_populated(self) -> None:
        result = extract_json("{}")
        assert result.attempts
        result2 = extract_json("")
        assert result2.attempts
        result3 = extract_json("nothing here")
        assert result3.attempts


class TestRealisticGemmaOutput:
    """End-to-end fixtures that mirror the failure shapes observed in
    the live activity log. Each one corresponds to a real Gemma 4
    edge-pass response that the old greedy-regex extractor rejected."""

    def test_thinking_then_channel_then_fenced_json(self) -> None:
        # Real <thinking> tags are stripped earlier by
        # sanitize_model_output. By the time the extractor runs, the
        # input usually still has prose + a fenced JSON block.
        text = (
            "Based on the bundle I'll propose typed edges.\n"
            "```json\n"
            "{\n"
            '  "edges": [\n'
            '    {"edge_type": "fee_amount_observed", '
            '"source_node": "case:dc_ph_hk_501", '
            '"target_node": "amount:php_45_500", '
            '"confidence": 0.82},\n'
            '  ],\n'
            '  "rag_candidates": []\n'
            "}\n"
            "```"
        )
        result = extract_json(text)
        assert result.ok
        assert len(result.payload["edges"]) == 1
        assert result.payload["edges"][0]["confidence"] == 0.82
        attempts = " | ".join(result.attempts)
        assert "stripped markdown code fence" in attempts
        assert "light repair" in attempts

    def test_no_fence_just_prose_then_object(self) -> None:
        text = (
            "Here is my analysis of the bundle.\n\n"
            "After reviewing the timeline and chat evidence, the typed "
            "edges I propose are:\n\n"
            '{"edges": [{"edge_type": "rule_hit", '
            '"source_node": "case:dc_ph_hk_501", '
            '"target_node": "rule:fee_camouflage_medical_exam", '
            '"confidence": 0.79}]}\n\n'
            "I am moderately confident in this edge."
        )
        result = extract_json(text)
        assert result.ok
        assert result.payload["edges"][0]["edge_type"] == "rule_hit"
