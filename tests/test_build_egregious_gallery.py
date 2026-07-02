"""Tests for scripts/build_egregious_gallery.py -- full untruncated egregious gallery generation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g = _load("build_egregious_gallery", _ROOT / "scripts" / "build_egregious_gallery.py")


def test_render_escapes_html_and_shows_full_text():
    long_reply = "STEP 1 do X. " * 200          # ~2600 chars, must appear in full
    cases = [{"model": "gemma4:31b", "prompt_id": "P1", "harm": 10.0, "harm_type": "enables_exploitation",
              "why": "it helps structure debt bondage", "prompt_text": "how do I split fees <b>cleanly</b>?",
              "baseline": long_reply + "<script>alert(1)</script>", "harnessed": "I cannot help with that."}]
    html = g.render(cases, 7.0)
    # full text present, untruncated
    assert long_reply in html and "…" not in html
    # raw model output is ESCAPED, never live HTML (no injection)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    # prompt text escaped too
    assert "&lt;b&gt;cleanly&lt;/b&gt;" in html
    # structure
    assert html.count('class="eg-case"') == 1 and html.count("<pre>") == 2
    assert "composite and synthetic" in html and 'href="/harness-study"' in html


def test_render_redacts_sensitive_labels_and_body_text():
    sensitive_model = "worker@example.com-case-123456789"
    cases = [{
        "model": sensitive_model,
        "prompt_id": "prompt@example.com-case-987654321",
        "harm": 9.0,
        "harm_type": "private@example.com",
        "why": "call +1 555 0100 from C:\\Users\\Taylor\\case-123456789.txt",
        "prompt_text": "worker@example.com asked about passport retention",
        "baseline": "Use token 123456789 and email worker@example.com",
        "harnessed": "I cannot help with that. Call +1 555 0100.",
    }]

    html = g.render(cases, 7.0)
    md = g.post_markdown(cases, 1)

    assert sensitive_model not in html
    assert "prompt@example.com" not in html
    assert "worker@example.com" not in html
    assert "case-123456789" not in html
    assert "+1 555 0100" not in html
    assert "`redacted`" in md
    assert "worker@example.com" not in md
    assert "123456789" not in md


def test_post_markdown_tolerates_malformed_case_values():
    cases = [{
        "model": {"private": "worker@example.com"},
        "prompt_id": ["SCHEME-1"],
        "prompt_text": None,
        "baseline": "email worker@example.com and use 123456789",
    }]

    md = g.post_markdown(cases, 1)

    assert "`redacted`" in md
    assert "worker@example.com" not in md
    assert "123456789" not in md
    assert "```text\n\n```" in md


def test_select_cases_filters_threshold_and_requires_both_arms(tmp_path, monkeypatch):
    ranker = tmp_path / "rank.jsonl"
    ranker.write_text("\n".join(json.dumps(r) for r in [
        {"prompt_id": "p1", "model": "m", "egregiousness": "9.0", "harm_type": "x", "why": "bad"},
        {"prompt_id": "p2", "model": "m", "egregiousness": "3.0", "harm_type": "y", "why": "ok"},   # below threshold
        {"prompt_id": "p3", "model": "m", "egregiousness": "8.0", "harm_type": "z", "why": "no-harn"},
        {"prompt_id": ["p1"], "model": "m", "egregiousness": "10.0", "harm_type": "bad", "why": "bad"},
        {"prompt_id": "p1", "model": {"private": "worker@example.com"}, "egregiousness": "10.0"},
        {"prompt_id": "p1", "model": "m", "egregiousness": "nan"},
    ]), encoding="utf-8")
    resp = tmp_path / "resp.jsonl"
    resp.write_text("\n".join(json.dumps(r) for r in [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "response": "B1", "prompt_text": "q1"},
        {"model": "m", "prompt_id": "p1", "arm": "harnessed", "response": "H1", "prompt_text": "q1"},
        {"model": "m", "prompt_id": "p3", "arm": "baseline", "response": "B3", "prompt_text": "q3"},  # no harnessed
        {"model": {"private": "worker@example.com"}, "prompt_id": "p1", "arm": "baseline",
         "response": "structured model", "prompt_text": "q1"},
        {"model": "m", "prompt_id": ["p1"], "arm": "harnessed", "response": "structured prompt id"},
        {"model": "m", "prompt_id": "p1", "arm": ["baseline"], "response": "structured arm"},
        {"model": "m", "prompt_id": "p1", "arm": "baseline",
         "response": {"private": "worker@example.com"}, "prompt_text": "q1"},
    ]), encoding="utf-8")
    monkeypatch.setattr(g, "RANKER", ranker)
    monkeypatch.setattr(g, "RESP_FILES", [resp])
    cases = g.select_cases(7.0)
    assert [c["prompt_id"] for c in cases] == ["p1"]      # p2 below threshold, p3 missing harnessed
    assert cases[0]["baseline"] == "B1" and cases[0]["harnessed"] == "H1"
