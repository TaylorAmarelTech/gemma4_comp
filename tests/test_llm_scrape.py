"""Tests for scripts/llm_scrape.py -- the LLM + browser + vision scraper.

Offline: the renderer and the text/vision model callables are injectable, so
HTML cleaning, JSON parsing, text + vision extraction, and the orchestration are
tested with no browser, no GPU, no network.
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


ls = _load("llm_scrape", _ROOT / "scripts" / "llm_scrape.py")

_HTML = """<html><head><title>Sunrise Overseas</title>
<style>.x{color:red}</style><script>var a=1;evil()</script></head>
<body><nav>menu</nav><h1>Sunrise Overseas Manpower Inc.</h1>
<p>License: POEA-1001 | Status: Valid</p>
<a href="javascript:void(0)">ignore</a><a href="/contact">Contact</a>
<table><tr><td>Phone</td><td>(02) 5550-1001</td></tr></table>
</body></html>"""


def test_clean_html_strips_script_style_keeps_text_and_links():
    text = ls.clean_html(_HTML)
    assert "Sunrise Overseas Manpower Inc." in text
    assert "POEA-1001" in text and "(02) 5550-1001" in text
    assert "evil()" not in text and "color:red" not in text  # script/style dropped
    assert "[/contact]" in text                               # real link kept
    assert "javascript" not in text                           # js: link dropped


def test_parse_json_extracts_object_from_prose():
    assert ls._parse_json('Here you go: {"name":"X","status":"Valid"} done')["name"] == "X"
    assert ls._parse_json("no json") == {}


def test_llm_extract_uses_model_and_parses_json():
    captured = {}
    def model_fn(prompt):
        captured["prompt"] = prompt
        return '{"name":"Sunrise Overseas Manpower Inc.","license_no":"POEA-1001","status":"Valid"}'
    got = ls.llm_extract(ls.clean_html(_HTML), ["name", "license_no", "status"], model_fn)
    assert got["license_no"] == "POEA-1001" and got["status"] == "Valid"
    # the page content + the requested fields are both put to the model
    assert "POEA-1001" in captured["prompt"] and "license_no" in captured["prompt"]


def test_vision_extract_passes_image_to_multimodal_model():
    seen = {}
    def vmodel(prompt, image_b64):
        seen["img"] = image_b64
        return '{"name":"Sunrise","status":"Valid"}'
    got = ls.vision_extract("ZmFrZV9wbmc=", ["name", "status"], vmodel)
    assert got["name"] == "Sunrise" and seen["img"] == "ZmFrZV9wbmc="


def test_scrape_page_orchestrates_render_clean_extract():
    def fake_render(url):
        return {"url": url, "title": "Sunrise Overseas", "html": _HTML,
                "screenshot_b64": "ZmFrZQ=="}
    text_calls = []
    def model_fn(prompt):
        text_calls.append(prompt)
        return '{"name":"Sunrise Overseas Manpower Inc.","status":"Valid"}'
    def vmodel(prompt, image_b64):
        return '{"name":"Sunrise Overseas Manpower Inc.","status":"Valid (vision)"}'
    res = ls.scrape_page("https://x.test/agency", ["name", "status"],
                         renderer=fake_render, model_fn=model_fn, vision_model_fn=vmodel)
    assert res["title"] == "Sunrise Overseas"
    assert res["extracted"]["name"] == "Sunrise Overseas Manpower Inc."
    assert res["vision_extracted"]["status"] == "Valid (vision)"  # screenshot path used
    assert res["n_content_chars"] > 0 and text_calls  # html was cleaned + sent


def test_scrape_page_without_models_just_renders():
    res = ls.scrape_page("https://x.test", ["name"],
                         renderer=lambda u: {"url": u, "title": "T", "html": _HTML})
    assert "extracted" not in res and "vision_extracted" not in res
    assert res["n_content_chars"] > 0  # still cleaned the html
