"""Regression coverage for the Harness Comparison page (compare.html).

The page has grown into one of the kernel's most heavily-modified
surfaces: chat-style pipeline progress per variant, examples
lightbox, AbortController-backed Interrupt, cumulative timing
breakdown, send-to-chat handoff, ARIA, and the SSE-streamed run
flow. These tests pin the contract pieces that are easy to
regress when iterating on the page.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from duecare.chat.app import create_app
    app = create_app()
    return TestClient(app)


def test_page_serves(client):
    r = client.get("/static/compare.html")
    assert r.status_code == 200
    assert len(r.text) > 5000


def test_required_markup_present(client):
    """Pin every IDs/markers the JS depends on. If one is renamed
    the page silently breaks; this test catches the rename."""
    r = client.get("/static/compare.html")
    text = r.text
    must_have = [
        # core controls
        'id="cmp-prompt"',
        'id="cmp-run"',
        'id="cmp-interrupt"',
        'id="cmp-max-tokens"',
        'id="cmp-temperature"',
        'id="cmp-show-truncation"',
        'id="grade-mode"',
        'id="A-import_corpus"',
        'id="B-import_corpus"',
        # variant cards
        'id="A-msgs"',
        'id="B-msgs"',
        'id="A-pipeline"',
        'id="B-pipeline"',
        'id="A-pipeline-rows"',
        'id="B-pipeline-rows"',
        'id="A-pipeline-elapsed"',
        'id="B-pipeline-elapsed"',
        'id="A-toggles"',
        'id="B-toggles"',
        'id="A-label"',
        'id="B-label"',
        # post-run cards
        'id="grade-card"',
        'id="timing-card"',
        'id="postrun-card"',
        # shared examples lightbox
        'src="/static/_examples_picker.js"',
        # log
        'id="cmp-log"',
    ]
    missing = [m for m in must_have if m not in text]
    assert not missing, f"required markup missing: {missing}"


def test_aria_attributes_present(client):
    """Tier 1 audit fix: ARIA on modal, variant cards, log host."""
    r = client.get("/static/compare.html")
    text = r.text
    picker = client.get("/static/_examples_picker.js").text
    compare_aria_required = [
        'role="region"',
        'aria-label="Variant A pipeline progress"',
        'aria-label="Variant B pipeline progress"',
        'role="log"',
        'aria-live="polite"',
        'role="alert"',
    ]
    picker_aria_required = [
        "modal.setAttribute('role', 'dialog')",
        "modal.setAttribute('aria-modal', 'true')",
        "modal.setAttribute('aria-labelledby', 'cmp-ex-modal-title')",
    ]
    missing = [a for a in compare_aria_required if a not in text]
    missing += [a for a in picker_aria_required if a not in picker]
    assert not missing, f"ARIA attributes missing: {missing}"


def test_max_tokens_default_is_16384(client):
    r = client.get("/static/compare.html")
    assert 'value="16384"' in r.text
    assert 'min="128" max="32768"' in r.text


def test_pipeline_step_labels_match_chat(client):
    """The pipeline steps on Compare must match the Chat page's
    labels exactly; mismatched labels confuse reviewers."""
    r = client.get("/static/compare.html")
    text = r.text
    for label in [
        "Preparing message", "Applied persona", "Running GREP regex rules",
        "Retrieving from RAG corpus", "Loading imported documents",
        "Calling lookup tools", "Searching the web", "Generating response",
    ]:
        assert label in text, f"pipeline step label missing: {label!r}"


def test_import_layer_visible_in_variant_controls(client):
    """Compare must expose the same Import layer Chat exposes."""
    r = client.get("/static/compare.html")
    text = r.text
    assert "import_corpus" in text
    assert "Loading imported documents" in text
    assert "Import" in text


def test_helper_functions_defined(client):
    r = client.get("/static/compare.html")
    text = r.text
    for fn in [
        "cmpInterrupt", "refreshVariantLabels", "renderTimingSummary",
        "renderGradeBars", "cmpSendToChat", "cmpCopyShareLink",
        "cmpPreset", "cmpOpenExamples", "cmpCloseExamples",
        "cmpRefreshModelStatus", "cmpLoadSelectedModel",
        "cmpEnsureModelReady",
        "pipelineInit", "pipelineSetStep", "pipelineRender",
    ]:
        assert fn in text, f"function {fn} not in compare.html"


def test_model_selector_lives_in_shared_nav(client):
    """The model picker is shared top chrome, not a Compare-only card."""
    compare = client.get("/static/compare.html").text
    nav = client.get("/static/_nav.html").text
    nav_js = client.get("/static/_nav.js").text
    assert 'id="cmp-model-card"' not in compare
    assert 'id="cmp-model-select"' not in compare
    assert 'id="dc-wb-model-open"' in nav
    assert 'id="dc-wb-model-select"' in nav
    assert 'id="dc-wb-model-overlay"' in nav
    assert 'data-nav-group="overview"' in nav
    assert 'data-nav-group="system"' in nav
    assert 'id="dc-wb-nav-toggle"' in nav
    assert "dcWbEnsureModelReady" in nav_js
    assert "openModelPopover({required: true})" in nav_js
    assert "dc-wb-model-required" in client.get("/static/_chrome.css").text
    assert "wireNavToggle" in nav_js


def test_abort_controller_wired(client):
    """Interrupt button uses AbortController per variant."""
    r = client.get("/static/compare.html")
    text = r.text
    assert "AbortController" in text
    assert "_abortCtls" in text
    assert "signal: ctl.signal" in text
    assert "AbortError" in text


def test_stream_error_handling(client):
    """When SSE ends without a `complete` event (Cloudflared idle
    timeout), the page must surface that explicitly instead of
    showing '(empty response)'."""
    r = client.get("/static/compare.html")
    text = r.text
    assert "stream ended without complete event" in text
    assert "stream ended without final response" in text


def test_mobile_breakpoint(client):
    r = client.get("/static/compare.html")
    assert "@media (max-width: 620px)" in r.text
    assert "@media (max-width: 980px)" in r.text


def test_examples_modal_close_on_esc(client):
    """ESC key handler is wired so the modal is keyboard-dismissible."""
    r = client.get("/static/_examples_picker.js")
    text = r.text
    assert "keydown" in text
    assert "Escape" in text


def test_examples_endpoint_consumed(client):
    """Compare must fetch examples from the same shared endpoint
    as Chat; reviewers see the same list everywhere."""
    r = client.get("/static/compare.html")
    assert "/api/examples" in r.text


def test_audit_log_host_at_end_of_main(client):
    """rule_70: activity log must be the very last <div class='wb-card'>
    inside <main>. Catches regressions where someone adds a card
    after it."""
    r = client.get("/static/compare.html")
    text = r.text
    main_end = text.rfind("</main>")
    log_idx = text.rfind('id="cmp-log"')
    assert main_end > 0 and log_idx > 0
    after_log = text[log_idx:main_end]
    n_cards = after_log.count('<div class="wb-card"')
    assert n_cards <= 0, (
        "extra wb-card found after the activity log -- log must be last"
    )


def test_back_compat_index_html_still_serves_chat(client):
    """The route swap for / -> Getting Started must not break the
    legacy /static/index.html alias."""
    r = client.get("/static/index.html")
    assert r.status_code == 200
    assert 'data-nav="chat"' in r.text


def test_chat_page_alias(client):
    """The new /static/chat.html alias serves the chat surface."""
    r = client.get("/static/chat.html")
    assert r.status_code == 200
    assert 'data-nav="chat"' in r.text
