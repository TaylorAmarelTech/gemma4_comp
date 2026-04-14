"""Tests for Gemma 4 native function-call output parsing."""

from __future__ import annotations

import json

from duecare.models.transformers_adapter.adapter import _parse_tool_calls


def test_parse_tool_call_tags() -> None:
    """Gemma 4 emits tool calls wrapped in <tool_call>...</tool_call>."""
    raw = (
        'I need to check legal references. '
        '<tool_call>{"name": "fact_db_query", "arguments": {"query": "RA 10022"}}</tool_call>'
        ' Now consulting the database.'
    )
    calls, cleaned = _parse_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "fact_db_query"
    assert calls[0].arguments == {"query": "RA 10022"}
    assert "<tool_call>" not in cleaned
    assert "fact_db_query" not in cleaned  # markup fully stripped


def test_parse_fenced_tool_call_block() -> None:
    """Some templates use ```tool_call fenced blocks."""
    raw = (
        "Checking fees...\n"
        "```tool_call\n"
        '{"name": "anonymize", "arguments": {"text": "Maria Santos"}}\n'
        "```\n"
        "Done."
    )
    calls, _ = _parse_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "anonymize"
    assert calls[0].arguments["text"] == "Maria Santos"


def test_parse_multiple_tool_calls() -> None:
    """A single response can emit multiple tool calls."""
    raw = (
        '<tool_call>{"name": "classify", "arguments": {"text": "A"}}</tool_call>'
        '<tool_call>{"name": "extract_facts", "arguments": {"text": "B"}}</tool_call>'
    )
    calls, _ = _parse_tool_calls(raw)
    assert len(calls) == 2
    assert {c.name for c in calls} == {"classify", "extract_facts"}


def test_no_tool_calls_returns_empty() -> None:
    """Plain prose with no tool markup returns empty list + original text."""
    raw = "This is just a normal safety response. Call POEA at 1343."
    calls, cleaned = _parse_tool_calls(raw)
    assert calls == []
    assert cleaned == raw


def test_malformed_tool_call_is_ignored() -> None:
    """Broken JSON inside a tool_call tag is silently skipped."""
    raw = '<tool_call>{not valid json}</tool_call> fallback text'
    calls, _ = _parse_tool_calls(raw)
    assert calls == []


def test_tool_call_with_parameters_alias() -> None:
    """Gemma sometimes uses `parameters` instead of `arguments`."""
    raw = '<tool_call>{"name": "foo", "parameters": {"x": 1}}</tool_call>'
    calls, _ = _parse_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].arguments == {"x": 1}
