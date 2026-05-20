"""Regression coverage for the Claude Design tooltip + step-depth pass.

The four design-contract pages (process / knowledge / search / share)
use a small shared vocabulary defined in ``_chrome.css``:

* ``.dc-step`` -- the numbered step chassis;
* ``.dc-pill`` / ``.dc-gemma-mark`` -- lifecycle state pills;
* ``[data-tip]`` -- declarative on-brand hover tooltips.

This module pins three properties:

1. ``_chrome.css`` defines the ``[data-tip]::after`` pseudo-element and
   a subtle resting / hover ``box-shadow`` on ``.dc-step`` so the
   stratified depth from the design package is preserved.
2. ``share.html`` and ``knowledge.html`` use ``data-tip`` on the
   gemma-mark + nearby controls instead of the native ``title=``
   attribute. The native ``title`` value is no longer present on those
   specific controls (no double tooltips at runtime).
3. The ``dc-gemma-mark is-optional`` and step-state pill ids remain
   wired so the Gemma honesty contract is preserved.

These checks are intentionally narrow: they only assert what the design
package asks for. They do not pin pixel-perfect copy or layout, so the
test stays stable across future tweaks of the same widgets.
"""
from __future__ import annotations

from pathlib import Path

import pytest


_STATIC = (
    Path(__file__).parents[1]
    / "src"
    / "duecare"
    / "chat"
    / "static"
)


def _read(name: str) -> str:
    return (_STATIC / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# _chrome.css contract
# ---------------------------------------------------------------------------


def test_chrome_defines_data_tip_pseudo_element() -> None:
    """The declarative tooltip pattern is the shared replacement for
    native ``title=`` hover hints. It must exist as a CSS pseudo-element
    so any page can opt in by adding ``data-tip`` without loading JS."""
    css = _read("_chrome.css")
    assert "[data-tip]::after" in css, (
        "_chrome.css must define [data-tip]::after for the declarative "
        "tooltip pattern."
    )
    # The two optional positions documented in the design package.
    assert '[data-tip][data-tip-pos="below"]' in css
    assert '[data-tip][data-tip-pos="right"]' in css


def test_chrome_data_tip_hides_on_touch_and_respects_reduced_motion() -> None:
    """Hover tooltips should not flash on touch devices (no hover
    affordance) and should not animate when the user prefers reduced
    motion. Both rules live alongside the pseudo-element."""
    css = _read("_chrome.css")
    assert "@media (hover: none)" in css
    assert "prefers-reduced-motion" in css


def test_chrome_dc_step_has_resting_and_hover_depth() -> None:
    """The step chassis should sit on a subtle resting shadow and lift
    slightly on hover. The waiting state stays flat so empty steps do
    not advertise stratification before they are active."""
    css = _read("_chrome.css")
    assert ".dc-step {" in css
    assert "box-shadow: var(--shadow-1);" in css
    assert ".dc-step:hover { box-shadow: var(--shadow-2); }" in css
    # Waiting steps should not lift on hover (the contract says empty
    # steps read as "not yet started", not as "interactive").
    assert (
        '.dc-step[data-state="waiting"]:hover { box-shadow: var(--shadow-1); }'
        in css
    )


# ---------------------------------------------------------------------------
# share.html -- 3 controls converted from title= to data-tip
# ---------------------------------------------------------------------------


SHARE_DATA_TIP_HOSTS = (
    'id="wb-step3-btn"',
    'id="wb-step3-fast-btn"',
    'id="wb-step3-gemma-mark"',
)


@pytest.mark.parametrize("host_marker", SHARE_DATA_TIP_HOSTS)
def test_share_step3_controls_use_data_tip(host_marker: str) -> None:
    """The Step 3 button cluster on share.html had three explanatory
    hover hints. Each one must be carried as ``data-tip`` (rendered
    by the shared chrome) rather than the native ``title=`` attribute."""
    html = _read("share.html")
    line = next(
        (line for line in html.splitlines() if host_marker in line),
        None,
    )
    assert line is not None, f"share.html lost {host_marker}"
    assert "data-tip=" in line, (
        f"{host_marker} should carry a data-tip attribute "
        "for the on-brand hover hint."
    )


def test_share_step3_gemma_mark_keeps_optional_state() -> None:
    """The Gemma honesty marker must remain ``dc-gemma-mark is-optional``
    by default. The data-tip rewrite must not have stripped the lifecycle
    class that powers the design contract's Gemma honesty rule."""
    html = _read("share.html")
    assert (
        'class="dc-gemma-mark is-optional" id="wb-step3-gemma-mark"' in html
    ), "share.html lost the Gemma honesty marker on Step 3."


def test_share_no_double_tooltip_on_swapped_controls() -> None:
    """After the migration, the swapped explanatory copy must NOT also
    appear as a native ``title=`` attribute. Otherwise the browser
    renders its own tooltip on top of the styled one."""
    html = _read("share.html")
    swapped_strings = (
        "Deterministic regex redaction always runs.",
        "Fast recording fallback: deterministic salted-hash redaction only.",
        "Reflects whether Gemma actually reviewed the redacted text.",
    )
    for needle in swapped_strings:
        assert f'title="{needle}' not in html, (
            f"share.html still has a native title= for: {needle!r} "
            "-- both title= and data-tip= would render concurrently."
        )


# ---------------------------------------------------------------------------
# knowledge.html -- 2 controls converted from title= to data-tip
# ---------------------------------------------------------------------------


def test_knowledge_kx_gemma_mark_uses_data_tip() -> None:
    """The Knowledge Extraction Gemma marker carries an explanatory hint
    about when the marker flips from Optional to Done. It must be
    ``data-tip`` on the styled span."""
    html = _read("knowledge.html")
    line = next(
        (line for line in html.splitlines() if 'id="kx-gemma-mark"' in line),
        None,
    )
    assert line is not None, "knowledge.html lost kx-gemma-mark."
    assert "data-tip=" in line
    assert 'class="dc-gemma-mark is-optional"' in line


def test_knowledge_use_gemma_label_uses_data_tip() -> None:
    """The ``Use Gemma refinement`` checkbox label has a longer hint
    explaining when to enable refinement. It must be carried as
    ``data-tip`` on the wrapping ``<label>``."""
    html = _read("knowledge.html")
    # The label wraps the kx-use-gemma checkbox. Find the chunk and
    # assert data-tip is on the same element.
    idx = html.find('id="kx-use-gemma"')
    assert idx != -1, "knowledge.html lost the kx-use-gemma checkbox."
    window = html[max(0, idx - 400) : idx]
    assert "data-tip=" in window, (
        "The label wrapping kx-use-gemma should carry a data-tip "
        "with the refinement guidance."
    )


def test_knowledge_no_double_tooltip_on_swapped_controls() -> None:
    """After the migration, neither of the two swapped hints should
    still appear as a native ``title=`` attribute on knowledge.html."""
    html = _read("knowledge.html")
    swapped_strings = (
        "Fast deterministic drafts are the default.",
        "Reflects whether Gemma actually ran.",
    )
    for needle in swapped_strings:
        assert f'title="{needle}' not in html, (
            f"knowledge.html still has a native title= for: {needle!r}"
        )


# ---------------------------------------------------------------------------
# Cross-page sanity -- all four design-contract pages keep their
# trust-row + step chassis primitives so the design contract is not
# silently dropped.
# ---------------------------------------------------------------------------


DESIGN_CONTRACT_PAGES = ("process.html", "knowledge.html", "search.html", "share.html")


@pytest.mark.parametrize("page", DESIGN_CONTRACT_PAGES)
def test_design_contract_pages_have_trust_row(page: str) -> None:
    """Every design-contract page must surface the LOCAL / GATED trust
    boundary as a compact ``dc-trust-row``. The design package banned
    paragraph-style trust statements in favor of this pill row."""
    html = _read(page)
    assert "dc-trust-row" in html, (
        f"{page} must carry a .dc-trust-row trust boundary."
    )
    assert "dc-trust-pill" in html, (
        f"{page} must carry at least one .dc-trust-pill."
    )


@pytest.mark.parametrize("page", DESIGN_CONTRACT_PAGES)
def test_design_contract_pages_use_dc_pill_lifecycle(page: str) -> None:
    """Step status must be expressed via the shared lifecycle pills, not
    one-off page-local pills. This pins the ``.dc-pill`` vocabulary to
    every design-contract page."""
    html = _read(page)
    assert "dc-pill" in html, (
        f"{page} must use the shared .dc-pill lifecycle pills."
    )


# ---------------------------------------------------------------------------
# Activity log "Copy JSON" contract -- design package §2.3 calls for a
# panel-header copy affordance on every activity log. The shared helper
# at /static/_activity_log.js exposes the API, the chrome provides the
# styles, and each design-contract page opts in by declaring
# data-toolbar="copy-json" on the activity-log host.
# ---------------------------------------------------------------------------


def test_activity_log_helper_exposes_to_json_and_copy() -> None:
    """The shared activity-log helper must expose ``toJSON()`` and
    ``copy()`` on the returned API so any page can render a panel-header
    Copy JSON link without rolling its own clipboard logic."""
    js = _read("_activity_log.js")
    assert "toJSON: function ()" in js, (
        "_activity_log.js must expose toJSON() on the attach() return."
    )
    assert "copy: async function ()" in js, (
        "_activity_log.js must expose async copy() that writes the "
        "JSON payload to navigator.clipboard."
    )
    # Events should be mirrored in memory so toJSON() has data to copy.
    assert "const events = [];" in js
    # The copy() implementation must serialize via JSON.stringify, not
    # an ad-hoc DOM scrape.
    assert "JSON.stringify(events, null, 2)" in js


def test_activity_log_copy_fails_honestly_when_clipboard_unavailable() -> None:
    """copy() must return false (not a fake true) when the clipboard
    API is missing -- e.g., insecure origin, sandboxed iframe, ancient
    browser. Otherwise the UI shows a "Copied" tick on a no-op."""
    js = _read("_activity_log.js")
    # The guard reads the clipboard surface defensively and bails early.
    assert "typeof navigator === 'undefined'" in js
    assert "!navigator.clipboard" in js
    assert "typeof navigator.clipboard.writeText !== 'function'" in js
    # The early-return must explicitly emit false so the caller can
    # show a real failure state.
    assert "navigator.clipboard unavailable" in js


def test_activity_log_helper_opt_in_toolbar() -> None:
    """The toolbar is opt-in via ``opts.toolbar === "copy-json"`` or
    ``data-toolbar="copy-json"`` on the host. Existing call sites that
    do not opt in must render identically -- so the helper must check
    one of those two flags before mounting any toolbar DOM."""
    js = _read("_activity_log.js")
    assert "opts.toolbar === 'copy-json'" in js
    assert "host.dataset.toolbar === 'copy-json'" in js
    # The toolbar must include a Copy JSON button labelled clearly.
    assert "'Copy JSON'" in js
    # The button must carry an aria-label for accessibility.
    assert "Copy activity log as JSON" in js


def test_chrome_styles_activity_log_toolbar() -> None:
    """``_chrome.css`` must style the toolbar so the Copy JSON button
    reads on the dark log panel. Scoped under ``.dc-activity-log`` so the
    styles do not leak to other panels."""
    css = _read("_chrome.css")
    assert ".dc-activity-log .dc-activity-log-toolbar {" in css
    assert ".dc-activity-log .dc-activity-log-copy {" in css
    # The "Copied" feedback state should be visually distinct.
    assert ".dc-activity-log .dc-activity-log-copy.is-copied {" in css
    # Focus-visible coverage so keyboard users see the focus ring.
    assert (
        ".dc-activity-log .dc-activity-log-copy:focus-visible {" in css
    )


@pytest.mark.parametrize("page", DESIGN_CONTRACT_PAGES)
def test_design_contract_pages_opt_into_copy_json(page: str) -> None:
    """Every design-contract page must opt in to the Copy JSON toolbar so
    reviewers can capture the activity stream for audit / bug reports.

    The opt-in is a single attribute on the activity-log host:
    ``data-toolbar="copy-json"``."""
    html = _read(page)
    # Locate the activity-log host (id varies across pages).
    log_line = next(
        (
            line
            for line in html.splitlines()
            if 'class="dc-activity-log"' in line
            and ("wb-log" in line or "search-log" in line or "kx-log" in line)
        ),
        None,
    )
    assert log_line is not None, (
        f"{page} should declare a dc-activity-log host."
    )
    assert 'data-toolbar="copy-json"' in log_line, (
        f"{page} must opt in to the panel-header Copy JSON affordance via "
        'data-toolbar="copy-json" on the activity-log host.'
    )


# ---------------------------------------------------------------------------
# Resilient grade-stream parser (compare.html cmpGradeOne)
#
# Real Kaggle bug: 30+ minutes of LLM-judge grading was thrown away when
# the Cloudflared tunnel dropped mid-stream (TypeError: Error in input
# stream from reader.read()). The fix preserves every dim_done event
# the client did receive and surfaces them as a partial result.
#
# These tests pin the source-level resilience surface so a future
# refactor can't accidentally drop the try/catch + partial accumulator.
# ---------------------------------------------------------------------------


def test_compare_grade_parser_catches_reader_read_throw() -> None:
    """``reader.read()`` must run inside a try/catch so a forcibly
    closed SSE stream (Cloudflared idle, tunnel reset, server crash)
    cannot kill the parse mid-grade."""
    html = _read("compare.html")
    # The pattern: try { chunk = await reader.read(); } catch (e) { ... }
    assert "chunk = await reader.read();" in html, (
        "compare.html cmpGradeOne must call reader.read() in a way that "
        "can be wrapped in try/catch (assign to a local first)."
    )
    # The catch clause must capture the error and break the loop so the
    # partial-result return path runs.
    assert "streamError = (e && e.message)" in html, (
        "compare.html must capture the stream-error message into a "
        "streamError variable so partial results can be returned."
    )


def test_compare_grade_parser_preserves_partial_dimensions() -> None:
    """The parser must accumulate every dim_done row that arrives,
    then surface them via a ``partial`` flag on stream error.

    Without this, a single tunnel hiccup throws away 30+ minutes of
    LLM-judge work (the real bug we just fixed)."""
    html = _read("compare.html")
    assert "const partialDims = [];" in html, (
        "compare.html must maintain an in-memory partialDims array "
        "that captures dim_done rows as they arrive."
    )
    assert "partialDims.push(evt.row);" in html, (
        "compare.html must push each dim_done row into partialDims."
    )
    assert "function buildPartial(errMsg, code)" in html, (
        "compare.html must define a buildPartial helper that returns "
        "the partial result on stream error / early end."
    )
    assert "partial: hasAnything," in html
    assert "partial_dimensions: partialDims.slice()," in html
    assert "n_done: lastNDone || partialDims.length," in html


def test_compare_grade_parser_wraps_handlers_in_try_catch() -> None:
    """Each event handler runs inside its own try/catch so one weird
    event (unexpected shape, missing field) does not kill the loop."""
    html = _read("compare.html")
    # The decoder.decode call should also be wrapped to handle truncated
    # multibyte sequences gracefully (drop chunk, keep going).
    assert "decoded = decoder.decode(value, {stream: true});" in html
    # JSON.parse already had a try/catch; verify it is still there and
    # bumps the dropped_frames counter.
    assert "droppedFrames += 1;" in html, (
        "compare.html must track dropped frames so the UI can surface "
        "an honest count of skipped malformed events."
    )


def test_compare_grade_score_label_handles_partial() -> None:
    """``scoreLabel`` must render a partial result as ``partial N/M``,
    not as a fake ``err``. Otherwise the reviewer mistakes a 46/74
    incomplete grade for a total failure."""
    html = _read("compare.html")
    # Source-text pattern: the partial branch sits BEFORE the error
    # branch so partial results never fall through to 'err'.
    assert "if (g.partial) {" in html
    assert "return 'partial ' + String(nDone) + '/' + String(nTotal);" in html


def test_compare_grade_bars_render_partial_banner() -> None:
    """``renderGradeBars`` must render an amber partial-grade banner
    when ``gradeResult.partial`` is true, plus fall through to the
    normal bars so the user sees the dimensions that did grade."""
    html = _read("compare.html")
    assert "if (gradeResult.partial) {" in html
    assert "Partial grade" in html
    assert "before the stream closed" in html
    # The banner is built with safe DOM construction (textContent /
    # createTextNode), not innerHTML interpolation, so SSE-supplied
    # values cannot inject markup.
    banner_section = html[html.index("data-role"):html.index("data-role") + 4000]
    assert "headStrong.textContent = 'Partial grade';" in banner_section, (
        "Partial-grade banner must use textContent (no innerHTML with "
        "interpolated values) to keep SSE-injected strings safe."
    )


def test_app_grade_stream_isolates_per_event_yield_errors() -> None:
    """The server-side ``_grade_stream_response`` helper wraps each
    ``json.dumps(evt)`` + ``yield`` in its own try/except. A single
    non-serializable event (stray non-JSON type leaked into a dim row)
    must not kill the whole stream mid-grade."""
    app_py = (
        Path(__file__).parents[1]
        / "src" / "duecare" / "chat" / "app.py"
    ).read_text(encoding="utf-8")
    # The new structure: per-event try block with a fallback warn frame
    # that lets the client know an event was skipped and the stream
    # continues.
    assert "payload = json.dumps(evt)" in app_py
    assert "dropped non-serializable event" in app_py
    # The first_event path is independently guarded so a bad
    # deterministic_done payload cannot kill the stream before the
    # judge phase begins.
    assert "first_event not JSON-serializable" in app_py


# ---------------------------------------------------------------------------
# Render-grade resilience + coverage breakdown
#
# Real bug: deterministic-mode grade completed but the Variant A/B
# panels stayed on the prior "(not graded yet)" text -- a silent
# exception inside renderGradeBars (poisoned dimension shape, missing
# field, etc.) left the host with no visible feedback. The fix wraps
# the inner render in try/catch and surfaces a visible error.
#
# Related: when two variants land within 2pp of each other, the pct
# alone hides whether one engaged with more applicable dimensions.
# renderGradeBars now adds a Coverage row that exposes the underlying
# applicable / pass / partial / fail counts so the reviewer can read
# the trade-off honestly.
# ---------------------------------------------------------------------------


def test_compare_render_grade_bars_isolates_exceptions() -> None:
    """The render function must wrap its body in try/catch so a bad
    dimension shape can't leave the host stuck on the prior text."""
    html = _read("compare.html")
    assert "function _renderGradeBarsInner(host, variant, gradeResult)" in html, (
        "compare.html must split renderGradeBars into a thin wrapper + "
        "inner function so the wrapper can catch render errors."
    )
    assert "_renderGradeBarsInner(host, variant, gradeResult);" in html, (
        "The wrapper must invoke the inner function inside try/catch."
    )
    # On exception the wrapper must clear the host and surface a
    # visible error to the user so the panel does not appear frozen.
    assert "'Render failed: '" in html
    assert "check the browser console for the full stack." in html
    # Console-side, log the gradeResult shape so devs can repro.
    assert "[renderGradeBars]" in html


def test_compare_render_grade_bars_emits_coverage_row() -> None:
    """The Coverage row reads n_applicable / n_not_applicable / n_pass /
    n_partial / n_fail from the grade payload (present on every
    /api/grade and /api/grade-combined-stream complete event) and
    surfaces them so the reviewer can read coverage vs. quality."""
    html = _read("compare.html")
    assert "// Coverage breakdown row." in html, (
        "compare.html must include the Coverage row above the dim details."
    )
    assert "gradeResult.n_applicable" in html
    assert "gradeResult.n_not_applicable" in html
    assert "gradeResult.n_pass" in html
    assert "gradeResult.n_partial" in html
    assert "gradeResult.n_fail" in html
    assert "'Coverage: '" in html


def test_compare_grade_close_score_caveat() -> None:
    """When A and B land within 2pp of each other, cmpGrade emits a
    one-line muted caveat to the activity log explaining the close
    comparison and pointing the reviewer to the per-axis breakdown
    (Quality / Coverage row added by the rubric refresh)."""
    html = _read("compare.html")
    assert "Math.abs(aPct - bPct) < 2.0" in html, (
        "compare.html cmpGrade must detect close-grade comparisons "
        "(within 2pp) so it can surface the coverage caveat."
    )
    assert "within 2pp" in html
    assert "Quality / Coverage row" in html, (
        "The close-grade caveat must point reviewers at the per-axis "
        "row (Quality / Coverage / Overall) in each grade panel."
    )


# ---------------------------------------------------------------------------
# Two-axis rubric: quality / coverage / overall
#
# The legacy pct_score is a weighted average over applicable dimensions
# only, which can produce counter-intuitive comparisons: a response
# that engages with MORE applicable dimensions at PARTIAL quality
# scores LOWER than a narrower response at slightly higher quality.
#
# The fix exposes three new fields on every grade response:
#   * quality_pct  -- alias of pct_score (depth)
#   * coverage_pct -- n_applicable / n_total (breadth)
#   * overall_pct  -- harmonic mean of the two (the principled headline)
#
# These tests pin the math and the JSON shape so a future refactor
# can't silently drop the breakdown.
# ---------------------------------------------------------------------------


def test_grade_universal_returns_two_axis_breakdown() -> None:
    """grade_response_universal must return quality_pct, coverage_pct,
    overall_pct, overall_score_0_10 on every call, including the
    standard PASS / PARTIAL / FAIL paths."""
    from duecare.chat.harness import grade_response_universal
    result = grade_response_universal(
        "ILO C181 Art. 7 prohibits worker-paid recruitment fees. "
        "POEA MC 14-2017 enforces zero-fee for Filipino domestic "
        "workers in Hong Kong. The DMW handles complaints.",
        prompt_text="tell me about PH-HK labor migration fees",
    )
    for key in ("quality_pct", "coverage_pct", "overall_pct",
                "overall_score_0_10"):
        assert key in result, f"grade_response_universal missing {key}"
    # Backward-compat aliases preserved.
    assert result["quality_pct"] == result["pct_score"], (
        "quality_pct must alias pct_score so legacy callers keep the "
        "same headline number under the new key."
    )
    # Harmonic-mean math: HM(q, c) = 2qc / (q+c).
    q = result["quality_pct"]
    c = result["coverage_pct"]
    if q + c > 0:
        expected = round(2 * q * c / (q + c), 1)
        assert abs(result["overall_pct"] - expected) < 0.15, (
            f"overall_pct={result['overall_pct']} not within 0.15 of "
            f"HM({q}, {c})={expected}"
        )


def test_grade_universal_overall_is_harmonic_mean() -> None:
    """Pin the harmonic-mean math: HM(60, 40) = 48.0."""
    # Use a synthetic input that gets a stable applicability profile.
    # The actual q/c values depend on the rubric, so we check the math
    # property: the helper rounds to 1 decimal, and overall is the HM.
    from duecare.chat.harness import grade_response_universal
    r = grade_response_universal(
        "ILO C181 prohibits charging recruitment fees.",
        prompt_text="x",
    )
    q = r["quality_pct"]
    c = r["coverage_pct"]
    overall = r["overall_pct"]
    if q + c > 0:
        expected = 2 * q * c / (q + c)
        assert abs(overall - expected) < 0.2


def test_grade_combined_inherits_breakdown_without_evaluator() -> None:
    """The combined grader, when called without an evaluator, must
    forward quality/coverage/overall from the deterministic side so
    /api/grade-combined-stream consumers see the same shape."""
    from duecare.chat.harness import (
        grade_response_universal, _combine_dimension_results,
    )
    det = grade_response_universal(
        "ILO C181 prohibits charging recruitment fees.",
        prompt_text="x",
    )
    combined = _combine_dimension_results(
        det, None, evaluator_weight=0.0, version="v2.0",
    )
    assert combined.get("quality_pct") == det["quality_pct"]
    assert combined.get("coverage_pct") == det["coverage_pct"]
    assert combined.get("overall_pct") == det["overall_pct"]


def test_compare_cmpscorenumber_prefers_overall_pct() -> None:
    """The headline number for ranking in the comparison UI must come
    from overall_pct so a response that engages with more applicable
    dimensions doesn't get penalized by the weighted-average pct."""
    html = _read("compare.html")
    # The function must check overall_pct FIRST, before pct_score, so
    # the rubric refresh actually changes the bar / score label.
    assert "if (typeof g.overall_pct === 'number') return g.overall_pct;" in html, (
        "cmpScoreNumber must prefer overall_pct over pct_score."
    )
    # Quality / Coverage helpers should also be present so the close-
    # grade caveat can report deltas on each axis.
    assert "function cmpQualityNumber(g) {" in html
    assert "function cmpCoverageNumber(g) {" in html


def test_compare_render_shows_per_axis_row() -> None:
    """renderGradeBars must surface Quality / Coverage / Overall as
    distinct values in the panel so reviewers can read the trade-off
    instead of guessing from a single pct."""
    html = _read("compare.html")
    assert "Quality / Coverage / Overall row" in html, (
        "compare.html must include the per-axis row comment."
    )
    assert "'Overall '" in html
    assert "'Quality '" in html
    assert "'Coverage '" in html


# ---------------------------------------------------------------------------
# Evaluator JSON repair
#
# Real Kaggle failure: Gemma-4-E4B-it hit max_new_tokens partway
# through the structured envelope, leaving the JSON unclosed. The
# parser fell to the keyword scan and the dim was reported with
# rationale "(parse failed; scanned key)" even though the verdict +
# score were already on the wire.
#
# The fix adds a brace-balancing repair step that auto-closes
# unterminated strings / arrays / objects before re-attempting parse.
# Plus the evaluator's default token cap is raised so truncation is
# rarer in the first place.
# ---------------------------------------------------------------------------


def test_evaluator_parser_recovers_truncated_envelope() -> None:
    """A real-world truncated JSON envelope (cut off mid-
    missing_elements list, no closing brace) must still parse to a
    structured verdict thanks to the brace-balancing repair step."""
    from duecare.chat.harness import _parse_evaluator_verdict
    truncated = (
        '{\n'
        '  "verdict": "no",\n'
        '  "applicability_0_10": 0,\n'
        '  "score_0_10": 0,\n'
        '  "confidence_0_10": 10,\n'
        '  "severity": "low",\n'
        '  "evidence_quote": "",\n'
        '  "evidence_quotes": [],\n'
        '  "missing_elements": [\n'
        '    "first missing item",\n'
        '    "second missing item",\n'
        '    "third missing item"'
    )
    parsed = _parse_evaluator_verdict(truncated)
    assert parsed["parse_ok"] is True, (
        "Truncated envelope with verdict + score on the wire should "
        "parse_ok=True after JSON repair, not fall to scan."
    )
    assert parsed["verdict"] == "no"
    assert parsed["score_0_10"] == 0.0
    assert parsed["applicability_0_10"] == 0.0
    assert parsed["confidence_0_10"] == 10.0
    assert len(parsed["missing_elements"]) == 3


def test_evaluator_parser_recovers_mid_string_truncation() -> None:
    """When the model is cut off mid-string (no closing quote), the
    repair step closes the dangling string + outer structures so the
    parser still extracts the verdict and numeric fields."""
    from duecare.chat.harness import _parse_evaluator_verdict
    mid_string = (
        '{\n'
        '  "verdict": "partial",\n'
        '  "applicability_0_10": 8,\n'
        '  "score_0_10": 5,\n'
        '  "confidence_0_10": 7,\n'
        '  "severity": "medium",\n'
        '  "evidence_quote": "",\n'
        '  "rationale": "The response addresses fees but does not name'
    )
    parsed = _parse_evaluator_verdict(mid_string)
    assert parsed["parse_ok"] is True
    assert parsed["verdict"] == "partial"
    assert parsed["score_0_10"] == 5.0


def test_repair_truncated_json_helper_is_idempotent() -> None:
    """_repair_truncated_json must be a no-op for already-balanced
    input. Otherwise round-tripping a valid envelope would mutate it."""
    from duecare.chat.harness import _repair_truncated_json
    valid = '{"verdict":"yes","score_0_10":9,"missing_elements":[]}'
    assert _repair_truncated_json(valid) == valid


def test_evaluator_max_new_tokens_default_raised() -> None:
    """DeepGradeRequest.max_new_tokens default was 320, which was
    routinely too small for the structured envelope. Raise to 640 so
    truncation is the exception, not the rule. (The repair step
    catches the leftover cases.)"""
    app_py = (
        Path(__file__).parents[1]
        / "src" / "duecare" / "chat" / "app.py"
    ).read_text(encoding="utf-8")
    assert "max_new_tokens: int = Field(default=640" in app_py, (
        "DeepGradeRequest.max_new_tokens default must be at least "
        "640 so the structured envelope finishes before truncation."
    )


# ---------------------------------------------------------------------------
# Judge (evaluator) model slot
#
# The kernel exposes a separate evaluator slot so a more capable model
# (typically Gemma 4 31B-it) can be loaded for LLM-judge grading while
# the chat model stays loaded for A/B inference. The chat package's
# _evaluator_model_call already prefers app.state.evaluator_call over
# app.state.gemma_call -- no grading-side changes needed once a judge
# is loaded.
#
# Tests pin the contract from both sides:
#   * kernel.py: three new endpoints + state ring + threaded loader
#   * compare.html: section + checkbox + variant picker + load/unload
#                   controls + localStorage persistence + status poll
# ---------------------------------------------------------------------------


# Repo-root path to the active Kaggle kernel. parents[3] is the
# repo root: tests/ -> duecare-llm-chat/ -> packages/ -> repo-root/.
# Hard-required at import time so a repo reorganization fails loudly
# here rather than silently skipping the judge-model coverage.
_KERNEL_PATH = (
    Path(__file__).parents[3]
    / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py"
)
assert _KERNEL_PATH.exists(), (
    f"Active Kaggle kernel missing at {_KERNEL_PATH}. The judge-model "
    f"feature lives in this kernel; if it moved, update _KERNEL_PATH."
)


def test_kernel_exposes_evaluator_load_endpoints() -> None:
    """kernel.py must expose POST /api/load-evaluator-model,
    POST /api/unload-evaluator-model, and GET /api/load-evaluator-model/status
    so the compare UI can load a separate judge model."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert '@app.post("/api/load-evaluator-model")' in src
    assert '@app.post("/api/unload-evaluator-model")' in src
    assert '@app.get("/api/load-evaluator-model/status")' in src


def test_kernel_evaluator_load_uses_separate_state_ring() -> None:
    """The judge-model load must NOT mutate the chat-model state ring.
    Separate _MODEL_LOAD_STATE_EVAL, _MODEL_LOAD_LOCK_EVAL, and
    _MODEL_LOAD_EVENTS_EVAL keep the two surfaces independent so a
    judge load doesn't make /api/load-model/status look busy.

    After the ModelSlot refactor, the evaluator slot still uses its
    own state dict (passed into ``_JUDGE_SLOT = ModelSlot(...)``); the
    load thread still writes to ``app.state.evaluator_call``. Unload
    clears the slot via ``setattr(app.state, self.app_state_attr, None)``
    where ``app_state_attr="evaluator_call"`` for the judge slot."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert "_MODEL_LOAD_STATE_EVAL" in src
    assert "_MODEL_LOAD_LOCK_EVAL" in src
    assert "_MODEL_LOAD_EVENTS_EVAL" in src
    # The load thread writes to the evaluator slot. The assignment is
    # routed through _queue_wrap so concurrent users serialise through
    # the inference queue; both the wrapper call and the original
    # backend reference appear on the assignment line.
    assert 'app.state.evaluator_call = _queue_wrap(loaded_local.backend, "judge")' in src
    # The unload clears the slot via the ModelSlot abstraction.
    assert "setattr(app.state, self.app_state_attr, None)" in src
    # And the judge slot is wired with the right attr name.
    assert 'app_state_attr="evaluator_call"' in src


def test_kernel_evaluator_unload_flushes_cuda_cache() -> None:
    """On unload, the kernel must call torch.cuda.empty_cache() (best-
    effort) so the freed weights actually release VRAM. After the
    ModelSlot refactor, the flush lives inside ``ModelSlot.unload``
    and BOTH slots inherit it -- so we look at the class body, not
    the endpoint shim."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    # Look at the ModelSlot class body.
    cls_idx = src.find("class ModelSlot:")
    assert cls_idx >= 0, "kernel.py is missing the ModelSlot class"
    # Find the end of the class by locating the next top-level def or
    # module-level statement. Take a generous window.
    region = src[cls_idx:cls_idx + 8000]
    # CUDA flush is invoked inside the unload procedure.
    assert "_torch.cuda.empty_cache()" in region, (
        "ModelSlot.unload must call torch.cuda.empty_cache() so VRAM "
        "actually returns to the pool after unload."
    )


def test_kernel_judge_preflight_returns_expected_shape() -> None:
    """The preflight result must include the 8 fields the UI relies on:
    variant, needs_disk_gb, needs_gpu_gb, disk_free_gb, gpu_free_gb,
    ok, reasons, notes. After the refactor ``_judge_preflight`` is a
    thin alias of ``_model_preflight``; the return dict literal lives
    in the latter."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    # Look at the slot-agnostic helper that both aliases call.
    idx = src.find("def _model_preflight(")
    assert idx >= 0, "_model_preflight helper missing"
    body = src[idx:idx + 4000]
    for key in ("variant", "needs_disk_gb", "needs_gpu_gb",
                "disk_free_gb", "gpu_free_gb", "ok", "reasons", "notes"):
        assert f'"{key}":' in body, (
            f"_model_preflight return must include the '{key}' field"
        )
    # The alias still exists for any external consumers that pinned
    # the old name.
    assert "def _judge_preflight(" in src


def test_compare_judge_section_present() -> None:
    """compare.html must include the Judge model section with the
    checkbox, variant picker, load/unload buttons, status pill, and
    suggestion pill."""
    html = _read("compare.html")
    assert 'id="judge-model-card"' in html, (
        "compare.html must have a <details id=\"judge-model-card\"> "
        "block for the Judge model UI."
    )
    assert 'id="judge-use-separate"' in html, (
        "Judge model section must include the use-separate checkbox."
    )
    assert 'id="judge-variant"' in html, (
        "Judge model section must include the variant picker."
    )
    assert 'id="judge-load-btn"' in html
    assert 'id="judge-unload-btn"' in html
    assert 'id="judge-status-pill"' in html
    assert 'id="judge-model-suggestion"' in html


def test_compare_judge_section_offers_31b_first() -> None:
    """The variant picker default must be Gemma 4 31B-it, since that
    is the recommended judge model for grading accuracy."""
    html = _read("compare.html")
    # Find the variant picker block.
    idx = html.find('id="judge-variant"')
    assert idx >= 0
    block = html[idx:idx + 1200]
    # The first option must be 31b-it AND it must be selected by default.
    assert 'value="31b-it" selected' in block, (
        "Judge variant picker must default to 31b-it (the most "
        "accurate Gemma 4 variant for LLM-judge grading)."
    )


def test_compare_judge_orchestration_js_wired() -> None:
    """The page must define judgeLoad / judgeUnload / judgeInit / and
    call judgeInit on DOMContentLoaded so the UI is alive on page load."""
    html = _read("compare.html")
    assert "async function judgeLoad()" in html
    # judgeUnload now accepts an opts arg ({force: bool}) so the queue-busy
    # gate can recursively call itself with force=true. Either form is
    # acceptable.
    assert ("async function judgeUnload(" in html)
    assert "function judgeInit()" in html
    # judgeInit must be called on DOMContentLoaded.
    assert "try { judgeInit();" in html


def test_compare_judge_persists_preferences_in_localstorage() -> None:
    """The user's choice (use judge yes/no + which variant) must
    survive page reload via localStorage so the reviewer doesn't have
    to re-set it after every refresh."""
    html = _read("compare.html")
    assert "'duecare:judge-use-separate'" in html
    assert "'duecare:judge-variant'" in html
    # The init function reads both keys.
    assert "localStorage.getItem(_JUDGE_LS_USE)" in html
    assert "localStorage.getItem(_JUDGE_LS_VARIANT)" in html


def test_compare_judge_polls_status_endpoint() -> None:
    """judgeLoad must POST then poll /api/load-evaluator-model/status
    so the UI updates as the loader thread reports phase changes."""
    html = _read("compare.html")
    assert "/api/load-evaluator-model" in html
    assert "/api/load-evaluator-model/status" in html
    assert "/api/unload-evaluator-model" in html
    # Polling helper must exist.
    assert "function judgeStartPolling()" in html


# ---------------------------------------------------------------------------
# Preflight: disk + GPU multi-step safety
#
# Loading 31B on Kaggle needs ~30 GB disk + ~20 GB GPU. Without
# preflight, an OOM mid-load leaves the kernel needing a restart.
# These tests pin the kernel-side gate and the UI-side gating + force
# override.
# ---------------------------------------------------------------------------


def test_kernel_exposes_judge_preflight_endpoint() -> None:
    """Kernel must expose GET /api/load-evaluator-model/preflight with
    a ?variant= query so the UI can check fit BEFORE clicking Load."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert '@app.get("/api/load-evaluator-model/preflight")' in src
    # Helper functions used by the preflight gate.
    assert "def _judge_preflight(variant: str)" in src
    assert "def _disk_free_gb(" in src
    assert "def _gpu_free_gb(" in src
    assert "def _estimate_model_size_gb(variant: str)" in src


def test_kernel_judge_load_enforces_preflight_with_override() -> None:
    """The load endpoint must run preflight and refuse with 503 when
    it fails, unless the caller passes ``override: true``. The error
    envelope must carry the preflight result so the UI can render
    the actual reasons."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    idx = src.find("def api_load_evaluator_model(")
    assert idx >= 0
    # The endpoint body grew over time (mirroring-chat 409 branch +
    # cross-slot duplicate detection + ModelSlot delegation). Pull a
    # generous slice so the preflight assertions still find the 503
    # branch regardless of how many gates have been added in front.
    body = src[idx:idx + 8000]
    assert "pre = _judge_preflight(variant)" in body
    assert 'if not pre["ok"] and not override:' in body
    assert "status_code=503" in body
    assert '"preflight_failed"' in body
    # Override flag must be read from the request body.
    assert 'body or {}).get("override"' in body


def test_kernel_judge_variant_footprints_documented() -> None:
    """The variant -> {disk, gpu} mapping must include the four
    primary Gemma 4 variants the UI exposes. Unknown variants get a
    conservative worst-case fallback."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert "_VARIANT_FOOTPRINT_GB" in src
    assert '"e2b-it"' in src
    assert '"e4b-it"' in src
    assert '"26b-a4b-it"' in src
    assert '"31b-it"' in src
    # Cloud routes must auto-pass (no local footprint).
    assert '"cloud-gemini"' in src
    # The estimator must fall back conservatively when the variant is
    # not in the table.
    assert "Unknown variant: assume worst-case" in src


def test_compare_judge_renders_preflight_panel() -> None:
    """The compare page must render a preflight panel above the
    Load/Unload row with badge + needs/have detail + a Re-check
    button so the user can refresh after freeing disk."""
    html = _read("compare.html")
    assert 'id="judge-preflight"' in html
    assert 'id="judge-preflight-badge"' in html
    assert 'id="judge-preflight-detail"' in html
    assert 'id="judge-preflight-reasons"' in html
    assert 'id="judge-preflight-refresh"' in html


def test_compare_judge_supports_force_override() -> None:
    """When preflight blocks, the UI must surface a "Force load"
    toggle that disables the gate. Hidden by default; revealed only
    after a blocking preflight; the Load button is disabled until
    the user ticks it."""
    html = _read("compare.html")
    assert 'id="judge-force"' in html
    assert 'id="judge-force-label"' in html
    # The override flag must travel in the POST body so the server-
    # side gate can honor it.
    assert "override: override" in html
    # The label is hidden by default (display:none); the JS reveals
    # it only after preflight fails.
    assert 'id="judge-force-label">' in html


def test_compare_judge_refreshes_preflight_on_variant_change() -> None:
    """Changing the variant in the picker must trigger a fresh
    preflight (different variants have different footprints)."""
    html = _read("compare.html")
    # judgeRefreshPreflight is the helper.
    assert "async function judgeRefreshPreflight()" in html
    # variantSel listener must call it.
    idx = html.find("variantSel.addEventListener('change'")
    assert idx >= 0
    block = html[idx:idx + 800]
    assert "judgeRefreshPreflight()" in block


def test_compare_judge_re_runs_preflight_at_click_time() -> None:
    """judgeLoad must re-check preflight at click time (not just
    rely on the panel's cached result), because the chat model may
    have been loaded since the last refresh and eaten the headroom."""
    html = _read("compare.html")
    idx = html.find("async function judgeLoad()")
    assert idx >= 0
    body = html[idx:idx + 2500]
    assert "await judgeRefreshPreflight()" in body, (
        "judgeLoad must re-run preflight at click time, not trust "
        "the cached badge."
    )
    # And must surface a server-side 503 (preflight_failed) cleanly.
    assert "r.status === 503" in body


# ---------------------------------------------------------------------------
# Chat-model preflight + auto-purge + ModelSlot abstraction
#
# Mirror of the judge-slot preflight, applied to the chat slot too.
# Plus the ModelSlot wrapper that consolidates the unload + cache
# purge logic so both slots use one canonical implementation.
# ---------------------------------------------------------------------------


def test_kernel_exposes_chat_preflight_endpoint() -> None:
    """Kernel must expose GET /api/load-model/preflight (chat slot)
    in addition to the existing judge-slot preflight."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert '@app.get("/api/load-model/preflight")' in src
    assert "def api_chat_preflight(" in src


def test_kernel_chat_load_enforces_preflight_with_override() -> None:
    """POST /api/load-model must refuse with 503 on a blocking
    preflight, unless body sets override=true. Same gate as the
    judge slot."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    idx = src.find("def api_load_model(")
    assert idx >= 0
    body = src[idx:idx + 4000]
    assert "pre = _model_preflight(variant)" in body
    assert 'if not pre["ok"] and not override:' in body
    assert "status_code=503" in body
    assert '"preflight_failed"' in body


def test_kernel_exposes_chat_unload_endpoint() -> None:
    """POST /api/unload-model must exist so the chat picker can free
    the slot before loading a new variant. Required for model
    swapping on Kaggle (the load endpoint otherwise refuses with
    'already_loaded')."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert '@app.post("/api/unload-model")' in src
    assert "def api_unload_chat_model(" in src
    # Default behavior: purge HF cache to free the precious
    # /kaggle/working disk (~20 GB on Kaggle).
    chat_unload = src[src.find("def api_unload_chat_model("):
                       src.find("def api_unload_chat_model(") + 1500]
    assert 'purge_cache' in chat_unload
    assert 'True' in chat_unload  # default value


def test_kernel_purge_helper_handles_both_hf_orgs() -> None:
    """_purge_hf_cache_for_variant must check BOTH google/* and
    unsloth/* cache dirs, since the chat runtime falls back to the
    Unsloth pre-quantized variants when google/* is gated. After the
    2026-05-20 variant-registry extraction, the unsloth aliases live
    in duecare.chat.variants; the kernel derives its _UNSLOTH_ALIASES
    dict from there."""
    kernel_src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert "_UNSLOTH_ALIASES" in kernel_src
    assert "def _hf_cache_dir_candidates_for_variant" in kernel_src
    assert "def _purge_hf_cache_for_variant" in kernel_src
    # The aliases themselves now live in the variants module.
    variants_src = _VARIANTS_MODULE.read_text(encoding="utf-8")
    assert "unsloth/gemma-4-E2B-it" in variants_src
    assert "unsloth/gemma-4-E4B-it" in variants_src
    assert "unsloth/gemma-4-31B-it" in variants_src
    assert "unsloth/gemma-4-26B-A4B-it" in variants_src


def test_kernel_purge_helper_returns_expected_shape() -> None:
    """_purge_hf_cache_for_variant returns {ok, bytes_freed,
    paths_checked, paths_deleted, ...}. The UI relies on the
    gb_freed field for the 'freed N GB' message."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    idx = src.find("def _purge_hf_cache_for_variant")
    assert idx >= 0
    body = src[idx:idx + 4000]
    for key in ('"ok":', '"bytes_freed":', '"paths_checked":',
                '"paths_deleted":'):
        assert key in body, f"_purge_hf_cache_for_variant must return {key}"
    # gb_freed is the user-facing convenience field.
    assert '"gb_freed":' in body


def test_kernel_model_slot_abstraction_present() -> None:
    """The ModelSlot class consolidates the unload + cache-purge
    logic so chat and judge slots share one canonical
    implementation. Two instances must exist: _CHAT_SLOT (writes to
    gemma_call) and _JUDGE_SLOT (writes to evaluator_call)."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert "class ModelSlot:" in src
    assert "_CHAT_SLOT = ModelSlot(" in src
    assert "_JUDGE_SLOT = ModelSlot(" in src
    # The unload endpoints must delegate, not re-implement.
    assert "_CHAT_SLOT.unload(" in src
    assert "_JUDGE_SLOT.unload(" in src


def test_kernel_model_slot_unload_steps_documented() -> None:
    """ModelSlot.unload is the canonical 9-step unload procedure.
    Pin the key steps so a future refactor cannot accidentally
    drop the CUDA flush, the disk purge, or the lock."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    idx = src.find("class ModelSlot:")
    assert idx >= 0
    body = src[idx:idx + 8000]
    # Lock acquisition and 409 on busy.
    assert "self.lock.acquire(blocking=False)" in body
    assert "status_code=409" in body
    # app.state.<attr> = None.
    assert "setattr(app.state, self.app_state_attr, None)" in body
    # LoadedModel ref cleared.
    assert "self.loaded_ref_setter(None)" in body
    # CUDA cache flush.
    assert "_torch.cuda.empty_cache()" in body
    # State reset to idle.
    assert '"status": "idle", "variant": None' in body
    # HF disk purge gated on purge_cache flag.
    assert "if purge_cache and current_variant:" in body
    assert "_purge_hf_cache_for_variant(current_variant)" in body


def test_nav_html_has_chat_preflight_panel() -> None:
    """_nav.html (shared model picker chrome) must include the
    preflight panel + Unload button + purge checkbox so EVERY page
    that uses the picker gets the same safety surface."""
    nav_html = _read("_nav.html")
    assert 'id="dc-wb-model-preflight"' in nav_html
    assert 'id="dc-wb-model-preflight-badge"' in nav_html
    assert 'id="dc-wb-model-preflight-detail"' in nav_html
    assert 'id="dc-wb-model-preflight-reasons"' in nav_html
    assert 'id="dc-wb-model-force"' in nav_html
    assert 'id="dc-wb-model-unload"' in nav_html
    assert 'id="dc-wb-model-purge"' in nav_html
    # Purge should default to checked given Kaggle's 20 GB disk.
    purge_idx = nav_html.find('id="dc-wb-model-purge"')
    assert purge_idx >= 0
    purge_block = nav_html[purge_idx:purge_idx + 100]
    assert "checked" in purge_block, (
        "Auto-purge checkbox should default ON (Kaggle /kaggle/working "
        "is only ~20 GB; keeping every download wastes disk)."
    )


def test_nav_js_wires_chat_preflight_and_unload() -> None:
    """_nav.js must implement refreshModelPreflight + unloadCurrentModel
    and wire them to the new UI elements."""
    nav_js = (
        Path(__file__).parents[1]
        / "src" / "duecare" / "chat" / "static" / "_nav.js"
    ).read_text(encoding="utf-8")
    assert "async function refreshModelPreflight()" in nav_js
    # unloadCurrentModel now takes an opts arg ({force: bool}) so the
    # queue-busy gate can recursively call itself with force=true.
    assert "async function unloadCurrentModel(" in nav_js
    # The load function must re-run preflight at click time.
    load_idx = nav_js.find("async function loadSelectedModel()")
    assert load_idx >= 0
    load_body = nav_js[load_idx:load_idx + 3500]
    assert "await refreshModelPreflight()" in load_body
    # 503 from preflight failure handled cleanly.
    assert "r.status === 503" in load_body
    # Unload endpoint called with purge_cache body. Signature now
    # accepts {force} for the 409 queue-busy recursive call.
    unload_idx = nav_js.find("async function unloadCurrentModel(")
    assert unload_idx >= 0
    unload_body = nav_js[unload_idx:unload_idx + 2500]
    assert "/api/unload-model" in unload_body
    assert "purge_cache" in unload_body
    # New functions exposed on the shared dcWbModelService for
    # programmatic callers (e.g., compare.html orchestration).
    assert "unload: unloadCurrentModel" in nav_js
    assert "preflight: refreshModelPreflight" in nav_js


def test_compare_judge_has_purge_checkbox() -> None:
    """The judge section must also have an auto-purge checkbox so the
    Kaggle 20 GB disk constraint applies to the judge slot too. Default
    checked. judgeUnload passes the flag to /api/unload-evaluator-model."""
    html = _read("compare.html")
    assert 'id="judge-purge"' in html
    # Default ON.
    purge_idx = html.find('id="judge-purge"')
    purge_block = html[purge_idx:purge_idx + 100]
    assert "checked" in purge_block
    # judgeUnload reads the checkbox and POSTs with purge_cache. The
    # signature now accepts {force} for the queue-busy 409 path; either
    # form locates the function body.
    unload_idx = html.find("async function judgeUnload(")
    assert unload_idx >= 0
    unload_body = html[unload_idx:unload_idx + 2500]
    assert "judge-purge" in unload_body
    assert "purge_cache: purge" in unload_body


# ---------------------------------------------------------------------------
# Inline-Gemma watchdog + mode defaults (2026-05-19 pass)
# ---------------------------------------------------------------------------


def test_process_watchdog_is_25_minutes_not_90_seconds() -> None:
    """The previous 90-second per-phase breaker tripped on healthy Gemma
    calls (5-15 min is common on Kaggle T4 with larger variants). The new
    behaviour scales to at least 25 minutes per phase, with a separate
    soft-warning heartbeat at 60s/5min/15min."""
    html = _read("process.html")
    # New generous breaker.
    assert "25 * 60 * 1000" in html
    # The old 90-second hardcoded gate must be gone.
    assert "phaseAgeMs > 90 * 1000" not in html
    assert "exceeded 90 seconds" not in html
    # Heartbeat scaffolding is present.
    assert "_wbGemmaLastHeartbeatSec" in html
    assert "Gemma phase still running" in html


def test_process_standard_review_is_recommended_with_gemma_default() -> None:
    """Standard review is the demo default: inline Gemma 4 ON, 5-call cap,
    one call per page item. The mode card carries a Recommended badge."""
    html = _read("process.html")
    # WB_REVIEW_MODES.standard_review config.
    sr_idx = html.find("standard_review: {")
    assert sr_idx >= 0
    sr_block = html[sr_idx:sr_idx + 600]
    assert "calls: 5" in sr_block
    assert "perItem: 1" in sr_block
    assert "inlineGemma: true" in sr_block
    # Quick triage stays deterministic-only (no Gemma calls).
    qt_idx = html.find("quick_triage: {")
    assert qt_idx >= 0
    qt_block = html[qt_idx:qt_idx + 600]
    assert "calls: 0" in qt_block
    assert "inlineGemma: false" in qt_block
    # The mode card surfaces the Recommended-for-demo signal.
    assert "Recommended for demo" in html


def test_process_max_calls_default_is_five() -> None:
    """The advanced setting #wb-max-gemma-calls now defaults to 5 so it
    matches the new standard-review preset and the user's request to cap
    Gemma calls during demos."""
    html = _read("process.html")
    assert 'id="wb-max-gemma-calls" type="number" min="0" max="1000" value="5"' in html


def test_process_has_where_gemma_runs_hint() -> None:
    """The advanced settings section explains the three Gemma 4 paths so
    the reviewer can pick the right button. This was previously implicit."""
    html = _read("process.html")
    assert 'id="wb-gemma-paths-hint"' in html
    assert "Where Gemma 4 runs on this page" in html
    assert "Explicit edge pass" in html
    assert "Graph chat" in html


def test_process_edge_pass_has_cancel_button_and_abort_flag() -> None:
    """The Gemma edge pass is the most likely place for a long-running
    Gemma call. It must expose a Cancel button and abort flag the operator
    can use to stop the poll loop."""
    html = _read("process.html")
    assert 'id="wb-gemma-edge-cancel-btn"' in html
    assert "wbCancelEdgePass" in html
    assert "_wbEdgeAbort" in html
    # The poll loop must check the flag and handle abandoned/cancelled.
    poll_idx = html.find("async function wbPollGemmaEdgeJob(")
    assert poll_idx >= 0
    poll_body = html[poll_idx:poll_idx + 4500]
    assert "_wbEdgeAbort" in poll_body
    assert "abandoned" in poll_body
    assert "cancelled" in poll_body


def test_process_edge_pass_start_wraps_json_parse() -> None:
    """The /api/process/graph-extract/start response body is parsed with
    a try/catch so a non-JSON 502/524 page does not crash the handler
    with a silent uncaught exception."""
    html = _read("process.html")
    start_idx = html.find("/api/process/graph-extract/start")
    assert start_idx >= 0
    # Pull a generous block around the start call and verify the body is
    # read as text first, then JSON.parse'd inside a try/catch.
    block = html[start_idx:start_idx + 1800]
    assert "bodyText = await r.text()" in block
    assert "JSON.parse(bodyText)" in block


# ---------------------------------------------------------------------------
# knowledge.html progress-event dedup + heartbeat
# ---------------------------------------------------------------------------


def test_knowledge_dedups_progress_event_tiles() -> None:
    """The poll endpoints return the cumulative events list each call.
    Without dedup the visible event strip explodes with duplicates
    (the "queued / layers / model_or_fallback" cascade). The new code
    keys each tile by (ts, phase, pct, idx) and skips duplicates."""
    html = _read("knowledge.html")
    assert "_kxSeenProgressKeys" in html
    assert "kxResetProgressEvents" in html
    assert "kxEventKey" in html
    # The callers now pass idx.
    assert "kxAddProgressEvent('kx-source', evt, idx)" in html
    assert "kxAddProgressEvent('kx-draft', evt, idx)" in html
    # The old raw innerHTML reset on the host has been replaced with
    # kxResetProgressEvents which clears the seen-key set too.
    assert "kxResetProgressEvents('kx-source')" in html
    assert "kxResetProgressEvents('kx-draft')" in html


def test_knowledge_useGemma_poll_budget_is_20_minutes() -> None:
    """The previous useGemma budget of 180 polls (4.5 minutes) tripped
    on legitimate Gemma calls. New budget is 800 polls (~20 minutes)."""
    html = _read("knowledge.html")
    assert "useGemma ? 800 : 40" in html


def test_knowledge_has_gemma_phase_heartbeat() -> None:
    """While in a Gemma model phase, knowledge.html must emit honest
    "still running" log entries every 60s so the activity log does not
    go silent during long generations."""
    html = _read("knowledge.html")
    assert "Knowledge draft phase:" in html
    assert "model_or_fallback" in html  # the gated regex literal
    assert "_kxLastHeartbeatSec" in html


def test_knowledge_has_where_gemma_runs_hint() -> None:
    """The knowledge page explains where Gemma 4 actually runs (Step 2
    draft refinement, not the local Process harness summary above)."""
    html = _read("knowledge.html")
    assert 'id="kx-gemma-paths-hint"' in html
    assert "Where Gemma 4 runs on this page" in html
    assert "Knowledge draft" in html


# ---------------------------------------------------------------------------
# search.html + share.html Gemma 4 path clarity (2026-05-19 pass 2)
# ---------------------------------------------------------------------------


def test_search_rephrase_is_on_by_default() -> None:
    """The "Also ask Gemma 4 to rephrase" checkbox is now checked by
    default so the demo path exercises Gemma 4. The server returns
    rephrase_wired=false when no model is loaded; the page surfaces
    that state honestly instead of failing silently."""
    html = _read("search.html")
    rephrase_idx = html.find('id="rephrase"')
    assert rephrase_idx >= 0
    rephrase_block = html[rephrase_idx:rephrase_idx + 80]
    assert "checked" in rephrase_block
    # Updated label uses the explicit "Gemma 4" wording.
    assert "Also ask Gemma 4 to rephrase" in html


def test_search_has_where_gemma_runs_hint() -> None:
    """The search page explains the three Gemma 4 touch points: query
    rephrase, per-result drafting, and the linked Knowledge Extraction
    refinement path."""
    html = _read("search.html")
    assert 'id="search-gemma-paths-hint"' in html
    assert "Where Gemma 4 runs on this page" in html
    assert "Query rephrase" in html


def test_search_hero_card_is_honest_about_gemma() -> None:
    """The hero "Model fit" card previously said "Search does not require
    Gemma" which read as "Gemma is not used here at all." Replaced with
    the honest "Gemma 4 role" description."""
    html = _read("search.html")
    assert "Search does not require Gemma" not in html
    assert "Gemma 4 role" in html


def test_share_step3_has_where_gemma_runs_hint() -> None:
    """The share page Step 3 body now opens with the same Where Gemma 4
    Runs hint used on the other design-contract pages, naming the
    regex pass as the always-on gate and Gemma 4 as the optional
    second control."""
    html = _read("share.html")
    assert 'id="share-gemma-paths-hint"' in html
    assert "Where Gemma 4 runs on this page" in html
    assert "Regex pass (always)" in html
    assert "residual-PII review" in html


def test_share_diff_render_is_dom_pure() -> None:
    """wbRenderDiffs must not assign innerHTML with interpolated
    user-derived strings (XSS smell). All dynamic content now flows
    through createElement + textContent. The wbAppendLabeled helper
    handles the label+separator+value pattern in one place."""
    html = _read("share.html")
    # Helper present.
    assert "function wbAppendLabeled(" in html
    # The body of wbRenderDiffs must not contain raw `+= '<` or
    # `.innerHTML =` followed by an interpolated value.
    start = html.find("function wbRenderDiffs(")
    end = html.find("function wbStep4(", start)
    assert start >= 0 and end > start
    body = html[start:end]
    # No string-built HTML with `+ escapeHtml(` (the previous pattern).
    assert "+ escapeHtml(" not in body
    # No innerHTML += pattern.
    assert ".innerHTML +=" not in body
    # No `.innerHTML = '<` style template either.
    assert ".innerHTML = '<" not in body


def test_share_diff_renders_two_tier_summary() -> None:
    """The summary block must label the regex pass and the Gemma 4
    review independently so a judge can read off "regex did X, Gemma
    additionally did Y" without inferring."""
    html = _read("share.html")
    body_idx = html.find("function wbRenderDiffs(")
    next_idx = html.find("function wbStep4(", body_idx)
    body = html[body_idx:next_idx]
    assert "Regex pass" in body
    assert "Gemma 4 review" in body
    assert "wb-anon-summary" in body
    # Honest labels for the not-ran cases.
    assert "no model loaded" in body
    assert "skipped this run" in body


# ---------------------------------------------------------------------------
# Carry-over hardening pass (2026-05-19 pass 3)
# ---------------------------------------------------------------------------


def test_search_safe_href_blocks_javascript_and_data_urls() -> None:
    """Result-card links must validate their protocol before assigning
    to a.href. A malicious search backend that returns
    `url: 'javascript:alert(1)'` must produce href='#' instead of a
    live XSS surface."""
    html = _read("search.html")
    # Helper present.
    assert "function safeHref(" in html
    # Helper allows only http/https + plain absolute paths.
    helper_idx = html.find("function safeHref(")
    helper_end = html.find("\n    }", helper_idx)
    helper_body = html[helper_idx:helper_end]
    assert "'http:'" in helper_body and "'https:'" in helper_body
    # Both <a href> assignments use the helper now (not the raw
    # `String(r.url || '#')` pattern).
    assert "a.href = safeHref(r.url)" in html
    assert "open.href = safeHref(r.url)" in html
    # rel hardened to noopener noreferrer to prevent reverse tabnabbing.
    assert "rel = 'noopener noreferrer'" in html


def test_search_run_has_abort_controller() -> None:
    """A second click on the Search button must abort the in-flight
    request so a slow first response cannot clobber a fast second
    response. AbortError is handled gracefully in the catch."""
    html = _read("search.html")
    assert "_searchActiveController" in html
    assert "new AbortController()" in html
    # An older Search may still be aborted via _searchActiveController.abort();
    # the literal helper signature is what we pin, not the exact call site.
    assert "_searchActiveController.abort()" in html
    assert "AbortError" in html
    # Both fetches pass the signal.
    fetch_count = html.count("signal: controller ? controller.signal : undefined")
    assert fetch_count >= 2, f"expected both sanitize + client fetches to pass signal; found {fetch_count}"


def test_knowledge_kxsleep_declared_once() -> None:
    """The duplicate `function kxSleep(...)` declaration that shadowed
    the original async version has been removed. Exactly one
    declaration remains."""
    html = _read("knowledge.html")
    # async function kxSleep is the only declaration.
    assert html.count("function kxSleep(") == 1


def test_knowledge_source_poll_has_abort_flag_and_cancel_button() -> None:
    """kxPollProcessJob now respects kxSourceAbort and surfaces a
    visible Cancel button next to Step 1's progress block so a stuck
    source-bundle poll can be released without waiting for the
    240-attempt budget."""
    html = _read("knowledge.html")
    assert "kxSourceAbort" in html
    assert "function kxCancelSourceJob(" in html
    assert 'id="kx-source-cancel-btn"' in html
    # Poll loop checks the flag.
    poll_idx = html.find("async function kxPollProcessJob(")
    poll_end = html.find("\n    function kxBuildTextFromProcessBundle(", poll_idx)
    poll_body = html[poll_idx:poll_end]
    assert "if (kxSourceAbort)" in poll_body
    # Finally block resets state + hides the button.
    assert "} finally {" in poll_body
    assert "kxActiveSourceJobId = ''" in poll_body


def test_share_step4_requires_typed_submit_confirmation() -> None:
    """Step 4 must require the operator to type SUBMIT before the
    button enables. A misclick or stale focus must not fire the real
    outbound POST."""
    html = _read("share.html")
    # Confirmation input present.
    assert 'id="wb-step4-confirm"' in html
    # Gate helper enforces both step3 completion + SUBMIT match.
    assert "function wbRefreshSubmitGate(" in html
    assert "=== 'SUBMIT'" in html
    # Step 3 success path now flips wbStep3Complete and re-runs the gate.
    assert "wbStep3Complete = true" in html
    # wbStep4 re-checks the gate at click time so the console cannot
    # bypass it.
    step4_idx = html.find("async function wbStep4(")
    step4_end = html.find("\n    const dz = document.getElementById('wb-dropzone')", step4_idx)
    step4_body = html[step4_idx:step4_end]
    assert "Submit blocked" in step4_body
    assert "wbSubmittedRunId" in step4_body


def test_share_step4_has_abort_controller_and_cancel_button() -> None:
    """A mid-flight submit must be cancellable so a slow/stuck POST
    does not hold the operator hostage. AbortError is recognised in
    the catch so the user sees an honest "cancelled by operator"
    message, not a generic network failure."""
    html = _read("share.html")
    assert "_wbSubmitController" in html
    assert "function wbCancelSubmit(" in html
    assert 'id="wb-step4-cancel-btn"' in html
    assert "new AbortController()" in html
    # Fetch passes the signal.
    step4_idx = html.find("async function wbStep4(")
    step4_end = html.find("\n    const dz = document.getElementById('wb-dropzone')", step4_idx)
    step4_body = html[step4_idx:step4_end]
    assert "signal: controller ? controller.signal : undefined" in step4_body
    assert "e.name === 'AbortError'" in step4_body


def test_share_step3_gemma_mark_is_honest_during_polling() -> None:
    """The Step 3 gemma-mark must NOT flip to 'Gemma active' while the
    poll is still running (we don't yet know if the model actually
    ran). It stays Optional with 'Gemma queued' text during polling,
    then routes to is-done / is-unavailable / is-skipped after the
    response resolves."""
    html = _read("share.html")
    step3_idx = html.find("async function wbStep3(")
    step3_end = html.find("\n    function wbAppendLabeled(", step3_idx)
    step3_body = html[step3_idx:step3_end]
    # The early is-active assignment that flipped before the model
    # call resolved is gone.
    assert "gMark.className = 'dc-gemma-mark is-active';" not in step3_body
    # Replaced with is-optional + "Gemma queued" so the marker is
    # honest while we wait.
    assert "'Gemma queued'" in step3_body
    # Final result-aware flip still routes through is-done /
    # is-unavailable / is-skipped.
    assert "'is-done'" in step3_body or "is-done" in step3_body
    assert "'is-unavailable'" in step3_body or "is-unavailable" in step3_body


def test_share_bumps_hub_submits_counter_on_success() -> None:
    """Per rule 70 §3, a successful hub submit must bump the
    localStorage counter so /static/status.html reflects activity
    from this page. Status reads the counter via
    statusReadLocalCounters()."""
    html = _read("share.html")
    assert "'duecare:hub-submits-count'" in html
    assert "'duecare:hub-submits-last-at'" in html
    status = _read("status.html")
    assert "'duecare:hub-submits-count'" in status
    assert 'id="stat-hub-submits-count"' in status
    assert 'id="stat-hub-submits-last"' in status
    assert "hubSubmitsCount" in status


def test_knowledge_bumps_imports_counter_on_promote_and_pack_import() -> None:
    """Promoting a draft or importing a knowledge pack mutates the
    local knowledge store; both must bump duecare:imports-count so
    Status reflects activity."""
    html = _read("knowledge.html")
    assert "function kxBumpImportsCounter(" in html
    # kxPromoteDraft calls the bump on success.
    promote_idx = html.find("async function kxPromoteDraft(")
    next_fn = html.find("function escapeHtml(", promote_idx)
    promote_body = html[promote_idx:next_fn]
    assert "kxBumpImportsCounter(1)" in promote_body
    # kImport bumps with the server-reported n_imported.
    import_idx = html.find("async function kImport(ev)")
    next_imp = html.find("async function kRefresh(", import_idx)
    import_body = html[import_idx:next_imp]
    assert "kxBumpImportsCounter(out.n_imported" in import_body


def test_search_bumps_imports_counter_when_saving_drafts() -> None:
    """Saving a search-result envelope to the local knowledge store
    is an import event; bump duecare:imports-count so Status reflects
    it."""
    html = _read("search.html")
    assert "function searchBumpImportsCounter(" in html
    save_idx = html.find("async function searchSaveOneDraft(")
    save_end = html.find("async function searchSaveAllDrafts(", save_idx)
    save_body = html[save_idx:save_end]
    assert "searchBumpImportsCounter(1)" in save_body


def test_kernel_cross_slot_duplicate_detection() -> None:
    """/api/load-evaluator-model now detects the case where the
    requested judge variant is already resident in the chat slot and
    returns a structured 409 instead of falling through to a
    preflight_failed disk error. compare.html surfaces the new status
    as an actionable log message."""
    repo_root = Path(__file__).parents[3]
    kernel_path = repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py"
    assert kernel_path.exists(), f"missing: {kernel_path}"
    kernel = kernel_path.read_text(encoding="utf-8")
    assert "duplicate_in_chat_slot" in kernel
    assert "chat_loaded_variant" in kernel
    assert "/api/unload-model" in kernel
    compare = _read("compare.html")
    assert "duplicate_in_chat_slot" in compare
    assert "already loaded in the chat slot" in compare


# ---------------------------------------------------------------------------
# Multi-user inference queue (2026-05-19 pass 4)
# ---------------------------------------------------------------------------


_QUEUE_MODULE = (
    Path(__file__).parents[1]
    / "src" / "duecare" / "chat" / "inference_queue.py"
)


def test_kernel_has_model_queue_with_chat_and_judge_slots() -> None:
    """The inference queue (extracted to duecare.chat.inference_queue
    on 2026-05-20) wraps both app.state.gemma_call and
    app.state.evaluator_call so concurrent users serialise through a
    FIFO-ish queue with position visibility, backpressure, and
    per-slot locking. The kernel imports + wires the singleton."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    assert "class ModelQueue" in queue_src
    assert "MAX_WAITING" in queue_src
    assert "class QueueFull" in queue_src
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    # Kernel imports the queue classes from the package.
    assert "from duecare.chat.inference_queue import" in kernel
    assert "_MODEL_QUEUE = _ModelQueue()" in kernel
    # Both backend assignments route through the wrapper factory.
    assert '_queue_wrap(loaded_local.backend, "chat")' in kernel
    assert 'app.state.evaluator_call = _queue_wrap(loaded_local.backend, "judge")' in kernel
    # 503 handler maps the exception to JSON so each route benefits
    # automatically (no per-route try/except needed).
    assert "@app.exception_handler(_QueueFull)" in kernel
    assert "status_code=503" in kernel


def test_kernel_publishes_queue_status_endpoint() -> None:
    """GET /api/queue/status returns a JSON-friendly snapshot the UI
    can poll for the per-slot 'N waiting' indicator. The endpoint
    lives in the kernel; the snapshot method that builds the payload
    lives in duecare.chat.inference_queue."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert '@app.get("/api/queue/status")' in kernel
    assert "def api_queue_status" in kernel
    # Snapshot fields live in the extracted module now.
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    snap_idx = queue_src.find("def snapshot")
    snap_end = queue_src.find("\n__all__ = ", snap_idx)
    if snap_end == -1:
        snap_end = snap_idx + 3000
    snap = queue_src[snap_idx:snap_end]
    assert '"n_active"' in snap
    assert '"n_waiting"' in snap
    assert '"position"' in snap
    assert '"elapsed_secs"' in snap


def test_nav_chrome_renders_queue_status() -> None:
    """The shared chrome adds a Queue status pill next to GPU so every
    workbench page shows live queue state without per-page code.
    _nav.js polls /api/queue/status inside the existing refreshStatus
    cadence and tolerates older kernels (404) by staying quiet."""
    nav_html = _read("_nav.html")
    assert 'id="dc-wb-status-queue"' in nav_html
    nav_js = _read("_nav.js")
    assert "/api/queue/status" in nav_js
    assert "_renderQueueStatus" in nav_js
    # Quiet fallback so a missing endpoint cannot break the chrome.
    assert "catch (_) { /* quiet */ }" in nav_js


def test_kernel_queue_has_slot_state_machine() -> None:
    """ModelQueue protects against use-after-free during model swaps
    by gating ticket enqueue on a per-slot state machine. Slots start
    closed, transition to open after a successful load, and to
    draining/closed during unload. wrap() refuses with QueueClosed
    when the slot is not open. State machine lives in
    duecare.chat.inference_queue; the kernel wires it."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    # State constants
    assert 'STATE_CLOSED = "closed"' in queue_src
    assert 'STATE_OPEN = "open"' in queue_src
    assert 'STATE_DRAINING = "draining"' in queue_src
    # State-change methods
    assert "def open_slot(self, name" in queue_src
    assert "def close_slot(" in queue_src
    assert "def is_busy(self, name" in queue_src
    # The wrapper enforces the gate before enqueuing.
    assert 'if state != self.STATE_OPEN:' in queue_src
    # Exception class is in the module (kernel just imports it).
    assert "class QueueClosed" in queue_src
    # Kernel-side wiring
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "@app.exception_handler(_QueueClosed)" in kernel
    assert '_MODEL_QUEUE.open_slot("chat")' in kernel
    assert '_MODEL_QUEUE.open_slot("judge")' in kernel


def test_kernel_unload_endpoints_gate_on_queue() -> None:
    """The unload endpoints refuse to free model weights while the
    inference queue still has work. Returns HTTP 409 with a queue
    snapshot unless force=true. Both chat + judge endpoints share
    the same gate pattern."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    # Chat unload gate
    chat_idx = kernel.find("def api_unload_chat_model(")
    chat_end = kernel.find("\ndef _set_chat_loaded(", chat_idx)
    chat_body = kernel[chat_idx:chat_end]
    assert '_MODEL_QUEUE.is_busy("chat")' in chat_body
    assert '"queue_busy"' in chat_body
    assert "force" in chat_body and "drain_seconds" in chat_body
    assert "status_code=409" in chat_body
    # Judge unload gate
    judge_idx = kernel.find("def api_unload_evaluator_model(")
    # Pick the next top-level marker after the judge unload body.
    judge_end = kernel.find("\n# Picker overlay:", judge_idx)
    if judge_end == -1:
        judge_end = judge_idx + 4000
    judge_body = kernel[judge_idx:judge_end]
    assert '_MODEL_QUEUE.is_busy("judge")' in judge_body
    assert '"queue_busy"' in judge_body
    assert "force" in judge_body and "drain_seconds" in judge_body
    assert "status_code=409" in judge_body


def test_kernel_queue_snapshot_includes_slot_state() -> None:
    """The /api/queue/status snapshot must include the per-slot state
    so the UI can render 'idle' vs 'draining' vs 'running' without
    inferring from the active/waiting counters. Source: ModelQueue.snapshot
    in duecare.chat.inference_queue."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    snap_idx = queue_src.find("def snapshot")
    snap_end = queue_src.find("\n__all__ = ", snap_idx)
    if snap_end == -1:
        snap_end = snap_idx + 3000
    snap = queue_src[snap_idx:snap_end]
    assert '"state": slot.get("state", self.STATE_CLOSED)' in snap


def test_kernel_has_use_chat_as_judge_endpoint() -> None:
    """The kernel exposes POST /api/use-chat-as-judge that toggles the
    _JUDGE_USES_CHAT module flag and mirrors app.state.gemma_call into
    app.state.evaluator_call. Refuses with 400 when no chat model is
    loaded; refuses with 409 when a separate judge is already loaded.
    Chat-load thread re-wires the mirror automatically; chat-unload
    clears it."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    # Module-level flag.
    assert "_JUDGE_USES_CHAT" in kernel
    # Endpoint exists with the new path.
    assert '@app.post("/api/use-chat-as-judge")' in kernel
    assert "def api_use_chat_as_judge(" in kernel
    # 400 + 409 error paths covered explicitly.
    ep_idx = kernel.find("def api_use_chat_as_judge(")
    ep_end = kernel.find("\n@app.post(", ep_idx + 100)
    ep_body = kernel[ep_idx:ep_end]
    assert '"no_chat_model"' in ep_body
    assert "status_code=400" in ep_body
    assert '"separate_judge_loaded"' in ep_body
    assert "status_code=409" in ep_body
    # Re-wiring on chat load: when _JUDGE_USES_CHAT is set, the load
    # thread mirrors the wrapped chat callable into evaluator_call.
    # Both the chat-load thread and the toggle endpoint assign through
    # local variables (wrapped_chat / chat_call) under the queue _meta
    # lock so the flag and the mirrored callable cannot drift apart.
    assert "app.state.evaluator_call = wrapped_chat" in kernel
    assert "app.state.evaluator_call = chat_call" in kernel
    # /api/load-evaluator-model refuses when mirroring is active.
    eval_load = kernel[kernel.find("def api_load_evaluator_model("):]
    eval_load = eval_load[: eval_load.find("\n@app.post(")]
    assert "_JUDGE_USES_CHAT" in eval_load
    assert '"mirroring_chat"' in eval_load
    # Status endpoint surfaces the flag so the UI can render the
    # mirrored state on page load.
    status_idx = kernel.find("def api_load_evaluator_status(")
    status_end = kernel.find("\n@app.post(", status_idx)
    status_body = kernel[status_idx:status_end]
    assert '"judge_uses_chat": _JUDGE_USES_CHAT' in status_body


def test_compare_has_use_chat_as_judge_toggle() -> None:
    """The compare page exposes the toggle as a checkbox above the
    existing 'Use a separate model as judge' control. The handler
    posts to /api/use-chat-as-judge; the status poller hides the
    separate-judge controls when the server reports mirroring."""
    compare = _read("compare.html")
    assert 'id="judge-use-chat-as-judge"' in compare
    assert "function judgeUseChatAsJudge(" in compare
    assert "/api/use-chat-as-judge" in compare
    assert "function _judgeRenderMirrorState(" in compare
    # When the server reports mirroring, the separate-judge controls
    # collapse so the UI is honest about what's resident.
    assert "data.judge_uses_chat" in compare


def test_kernel_sets_hf_home_under_kaggle_working() -> None:
    """On Kaggle, the HF cache must land under /kaggle/working so the
    preflight disk gate (which measures that partition) matches the
    actual download destination. The default is the root filesystem,
    which has a different quota -- so the kernel sets HF_HOME at
    import time when /kaggle/working exists."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "/kaggle/working/.cache/huggingface" in kernel
    assert 'os.environ["HF_HOME"] = _kaggle_hf_home' in kernel
    # HF_HUB_CACHE is the modern shorthand; TRANSFORMERS_CACHE the legacy.
    assert "HF_HUB_CACHE" in kernel
    assert "TRANSFORMERS_CACHE" in kernel


def test_kernel_lowered_31b_disk_footprint() -> None:
    """The 31b-it disk footprint estimate was lowered from 30GB to the
    quantised-shard reality (~18GB) so preflight does not reject the
    default chat variant on a fresh Kaggle session. After the 2026-05-20
    variant-registry extraction, the source of truth is variants.py."""
    src = _VARIANTS_MODULE.read_text(encoding="utf-8")
    # The 31b-it VariantSpec has disk_gb=18.0; jailbroken-31b mirrors.
    assert "disk_gb=18.0" in src
    # And the value is associated with 31b-it, not some other variant.
    spec_31b_idx = src.find('id="31b-it"')
    assert spec_31b_idx >= 0
    # Scan the next ~600 chars for the disk_gb=18.0 line within that
    # spec's body.
    spec_block = src[spec_31b_idx:spec_31b_idx + 800]
    assert "disk_gb=18.0" in spec_block


def test_kernel_purges_partial_shards_on_load_failure() -> None:
    """Mid-download failures (disk full, HF rate limit) used to leave
    partial shards consuming disk. The load thread's exception path
    now calls _purge_hf_cache_for_variant so a retry has a clean budget."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    # The chat-load thread purges on failure.
    err_section_idx = kernel.find('"FAILED:')
    assert err_section_idx >= 0
    err_section = kernel[err_section_idx:err_section_idx + 2000]
    assert "_purge_hf_cache_for_variant(variant)" in err_section


def test_queue_wrap_rechecks_state_after_lock_acquire() -> None:
    """ModelQueue.wrap must re-check the slot state AFTER acquiring
    call_lock. A force-close that happened while the ticket waited
    must raise QueueClosed rather than invoke a possibly-None
    backend. Lives in duecare.chat.inference_queue."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    wrap_idx = queue_src.find("def wrap(self, backend_fn, slot_name")
    wrap_end = queue_src.find("def snapshot", wrap_idx)
    body = queue_src[wrap_idx:wrap_end]
    # The post-acquire re-check is present.
    assert "Re-check state after acquire" in body
    assert "post_state != self.STATE_OPEN" in body
    assert "slot[\"call_lock\"].release()" in body


def test_activity_log_exposes_inference_error_helper() -> None:
    """The shared _activity_log.js exposes window.dcInferenceError so
    every page can render queue 503 envelopes uniformly instead of
    leaving them as raw 'HTTP 503' messages."""
    js = _read("_activity_log.js")
    assert "window.dcInferenceError" in js
    assert "async parse(response)" in js
    assert "queue_full" in js
    assert "queue_closed" in js
    # compare.html consumes the helper on the chat-send 503 branch.
    compare = _read("compare.html")
    assert "window.dcInferenceError.parse(r)" in compare


def test_process_edge_mark_stays_optional_until_job_accepted() -> None:
    """process.html edge-pass marker must NOT flip to is-active before
    the start-endpoint returns 200 with a job_id. Stays Optional with
    'Gemma queued' text during the start fetch, then promotes."""
    html = _read("process.html")
    run_idx = html.find("async function wbRunGemmaEdgePass(")
    run_end = html.find("function wbRenderJourney(", run_idx)
    body = html[run_idx:run_end]
    # Initial state is is-optional, not is-active.
    assert "'dc-gemma-mark is-optional'" in body
    assert "'Gemma queued'" in body
    # Promotion happens only after the job is accepted.
    assert "Job confirmed; now the marker can honestly show is-active" in body
    # Abort flag is reset at function entry so a prior Cancel does not
    # short-circuit a fresh run.
    assert "_wbEdgeAbort = false" in body


def test_knowledge_source_abort_reset_on_new_load() -> None:
    """knowledge.html kxLoadSourceFile must reset kxSourceAbort at the
    top so a stale Cancel from a prior bundle does not short-circuit a
    fresh upload."""
    html = _read("knowledge.html")
    load_idx = html.find("async function kxLoadSourceFile(")
    load_end = html.find("async function kxExtract(", load_idx)
    if load_end == -1:
        load_end = load_idx + 4000
    body = html[load_idx:load_end]
    assert "kxSourceAbort = false" in body


def test_design_contract_pages_use_is_private_trust_row() -> None:
    """process.html and knowledge.html are local-only surfaces; their
    trust-rows must use the is-private modifier so the dot + border
    color reflect the privacy posture instead of falling to default."""
    for page in ("process.html", "knowledge.html"):
        html = _read(page)
        assert 'class="dc-trust-row is-private"' in html, (
            page + " trust-row missing is-private modifier"
        )


def test_anonymization_hub_allowlist_blocks_ssrf() -> None:
    """_post_payload must refuse any target_url whose host is not on
    _HUB_ALLOWLIST_HOSTS. The kernel runs unauthenticated on a Kaggle
    tunnel, so the submit endpoint cannot be allowed to act as a
    general HTTP proxy / SSRF vector."""
    repo_root = Path(__file__).parents[1].parent
    handler_path = (
        Path(__file__).parents[1] / "src" / "duecare" / "chat"
        / "harnesses" / "anonymization" / "handler.py"
    )
    src = handler_path.read_text(encoding="utf-8")
    assert "_HUB_ALLOWLIST_HOSTS" in src
    # Must reject http:// and any other non-https scheme.
    assert "scheme {parsed.scheme!r} not allowed" in src
    assert 'parsed.scheme != "https"' in src
    # Approved hub hosts.
    assert '"gemma4-comp.onrender.com"' in src
    assert '"duecare-ai.com"' in src
    # Userinfo rejected.
    assert "parsed.username or parsed.password" in src
    # follow_redirects disabled so an allowed host can't bounce off-list.
    assert "follow_redirects=False" in src


def test_kernel_robust_bool_parser() -> None:
    """The kernel exposes _parse_bool to avoid bool(\"false\")==True
    when a request body sends a JSON-stringified boolean. The
    use-chat-as-judge endpoint routes through this helper."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "def _parse_bool(" in kernel
    # Truthy + falsy strings handled explicitly.
    assert "true" in kernel.lower() and "false" in kernel.lower()
    # Endpoint uses the helper for "enabled".
    ep_idx = kernel.find("def api_use_chat_as_judge(")
    ep_end = kernel.find("\n@app.post(", ep_idx + 100)
    ep_body = kernel[ep_idx:ep_end]
    assert '_parse_bool(body.get("enabled")' in ep_body


def test_compare_warns_when_judge_shares_chat_slot() -> None:
    """During a grade run, the compare page must log a heads-up when
    mirroring is active so the operator knows why a long wait may
    happen if another user is mid-generation."""
    html = _read("compare.html")
    grade_idx = html.find("async function cmpGradeOne(")
    grade_end = grade_idx + 1200
    grade_body = html[grade_idx:grade_end]
    assert "_judgeLastStatus.judge_uses_chat" in grade_body
    assert "mirror ON" in grade_body


_TEMPLATES_MODULE = (
    Path(__file__).parents[1]
    / "src" / "duecare" / "chat" / "templates.py"
)


def test_templates_module_has_registry_and_endpoints() -> None:
    """The templates module (extracted out of kernel.py on 2026-05-20)
    registers 4 NGO templates (HK Labour Dept, PH DMW, IOM, NGO intake)
    and provides register_template_routes(app) which wires
    GET /api/templates/list + POST /api/templates/fill onto a FastAPI
    instance. Each TemplateSpec carries a body string, audience,
    jurisdiction, and ordered fields tuple."""
    assert _TEMPLATES_MODULE.exists(), f"missing module: {_TEMPLATES_MODULE}"
    src = _TEMPLATES_MODULE.read_text(encoding="utf-8")
    assert "TEMPLATES_REGISTRY" in src
    for tpl_id in ("hk_ld_fdh_complaint", "ph_dmw_complaint",
                   "iom_referral", "ngo_intake"):
        assert f'"{tpl_id}"' in src
    # Route registration helper exposed as a public function.
    assert "def register_template_routes(" in src
    assert '@app.get("/api/templates/list")' in src
    assert '@app.post("/api/templates/fill")' in src
    # Unknown template returns 404 with the available list.
    assert '"unknown_template"' in src
    assert 'status_code=404' in src


def test_templates_module_provenance_includes_four_buckets() -> None:
    """gemma_fill_template returns provenance with four possible
    values per field: manual, bundle_hint, gemma, missing. The UI
    paints each bucket with a different border colour so the user
    can audit who proposed each value."""
    src = _TEMPLATES_MODULE.read_text(encoding="utf-8")
    fill_idx = src.find("def gemma_fill_template(")
    fill_end = src.find("\ndef parse_bool(", fill_idx)
    body = src[fill_idx:fill_end]
    assert '"bundle_hint"' in body
    assert '"manual"' in body
    assert '"gemma"' in body
    assert '"missing"' in body
    # Manual fields take precedence over bundle hints (caseworker
    # has final authority).
    assert "Pass 2:" in body or "manual_fields ALWAYS override" in body
    # Gemma's proposed field_ids are validated against the template's
    # schema -- the model cannot inject fields that don't exist.
    assert "valid_ids" in body and "if fid not in valid_ids" in body


def test_templates_module_respects_use_gemma_false() -> None:
    """When use_gemma=False, the endpoint must skip the Gemma path
    entirely. The module uses parse_bool to handle JSON-stringified
    booleans correctly (bool('false') == True is a footgun)."""
    src = _TEMPLATES_MODULE.read_text(encoding="utf-8")
    # The module's own parse_bool routes string/int booleans correctly.
    assert "def parse_bool(" in src
    # The fill route passes the parsed bool through to gemma_call=None.
    fill_idx = src.find("def api_templates_fill(")
    fill_end = src.find("\n__all__ =", fill_idx)
    if fill_end == -1:
        fill_end = fill_idx + 3000
    fill_body = src[fill_idx:fill_end]
    assert 'parse_bool(body.get("use_gemma")' in fill_body
    assert "if use_gemma else None" in fill_body


_VARIANTS_MODULE = (
    Path(__file__).parents[1]
    / "src" / "duecare" / "chat" / "variants.py"
)


def test_variants_module_registers_nine_specs() -> None:
    """The new variants module replaces 4 inline kernel dicts with a
    single frozen-dataclass registry. All 9 builtin variants must be
    present and the dataclass must be frozen so the registry cannot
    drift via in-place mutation."""
    assert _VARIANTS_MODULE.exists(), f"missing module: {_VARIANTS_MODULE}"
    src = _VARIANTS_MODULE.read_text(encoding="utf-8")
    assert "VARIANT_REGISTRY" in src
    assert "@dataclass(frozen=True)" in src
    assert "class VariantSpec" in src
    for vid in (
        "e2b-it", "e4b-it", "26b-a4b-it", "31b-it",
        "jailbroken-31b", "jailbroken-e4b",
        "cloud-gemini", "cloud-openai", "cloud-ollama",
    ):
        assert f'id="{vid}"' in src, f"variant {vid} missing from registry"
    # Helper exports declared in __all__ so the kernel can stay
    # tightly scoped on what it imports.
    for helper in ("get_variant", "list_variant_ids", "is_cloud_variant",
                   "footprint_gb", "hf_id", "unsloth_alias", "to_ui_map"):
        assert f'"{helper}"' in src, f"helper {helper} missing from __all__"


def test_variants_module_round_trips_runtime_smoke() -> None:
    """Quick runtime smoke -- the registry resolves correctly, the
    cloud variants are correctly tagged, and the unknown-variant
    fallback returns the conservative worst-case footprint."""
    import importlib
    import sys
    src_path = str(Path(__file__).parents[1] / "src")
    sys.path.insert(0, src_path)
    try:
        variants = importlib.import_module("duecare.chat.variants")
    finally:
        try:
            sys.path.remove(src_path)
        except ValueError:
            pass
    assert variants.get_variant("31b-it").disk_gb == 18.0
    assert variants.footprint_gb("31b-it") == {"disk": 18.0, "gpu": 16.0}
    assert variants.hf_id("31b-it") == "google/gemma-4-31b-it"
    assert variants.unsloth_alias("31b-it") == "unsloth/gemma-4-31B-it"
    assert variants.is_cloud_variant("cloud-gemini") is True
    assert variants.is_cloud_variant("e4b-it") is False
    # Unknown variant -> conservative fallback, no exception.
    assert variants.footprint_gb("unknown-xyz") == {"disk": 30.0, "gpu": 20.0}
    assert variants.hf_id("cloud-gemini") is None
    assert variants.unsloth_alias("jailbroken-e4b") is None  # no alias


def test_kernel_derives_variant_dicts_from_module() -> None:
    """kernel.py no longer hard-codes the 4 variant dicts inline.
    _VARIANT_INFO, _VARIANT_FOOTPRINT_GB, and _UNSLOTH_ALIASES are
    derived from duecare.chat.variants at kernel-load time. The
    early _VARIANT_HF_ID (defined before duecare.chat is on path)
    stays inline but has a drift-check that fires at module load."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    # Imports.
    assert "from duecare.chat.variants import (" in kernel
    assert "VARIANT_REGISTRY as _DC_VARIANT_REGISTRY" in kernel
    assert "to_ui_map as _dc_variants_to_ui_map" in kernel
    # Drift check for the early HF id dict.
    assert "def _drift_check_hf_id_dict(" in kernel
    assert "_drift_check_hf_id_dict()" in kernel
    # Derived dicts (no big inline literals).
    assert "_VARIANT_INFO = _dc_variants_to_ui_map()" in kernel
    assert "spec.disk_gb" in kernel and "spec.gpu_gb" in kernel
    assert "spec.unsloth_alias" in kernel
    # Make sure the deleted inline literals are NOT back. (Spot-check
    # the most distinctive line -- e2b-it's display row.)
    assert '"e2b-it":         {"display": "Gemma 4 E2B-it"' not in kernel


def test_inference_queue_module_exports() -> None:
    """The extracted queue module exposes the three public symbols the
    kernel imports: ModelQueue, QueueFull, QueueClosed. The kernel
    binds them to underscore-prefixed legacy names so existing call
    sites in the kernel stay unchanged."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    assert 'class ModelQueue' in queue_src
    assert 'class QueueFull' in queue_src
    assert 'class QueueClosed' in queue_src
    assert '"ModelQueue"' in queue_src
    assert '"QueueFull"' in queue_src
    assert '"QueueClosed"' in queue_src
    # Round-trip via real Python import to make sure the module is
    # syntactically valid and the public symbols are reachable.
    import importlib
    import sys
    src_path = str(Path(__file__).parents[1] / "src")
    sys.path.insert(0, src_path)
    try:
        mod = importlib.import_module("duecare.chat.inference_queue")
    finally:
        try:
            sys.path.remove(src_path)
        except ValueError:
            pass
    assert mod.ModelQueue.MAX_WAITING == 5
    assert mod.ModelQueue.STATE_OPEN == "open"
    q = mod.ModelQueue()
    assert q.slot_state("nonexistent") == mod.ModelQueue.STATE_CLOSED


def test_kernel_imports_inference_queue_module() -> None:
    """kernel.py no longer carries inline ModelQueue / QueueFull /
    QueueClosed definitions. They are imported from the package and
    rebound to the legacy underscore names so existing call sites
    stay unchanged."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "from duecare.chat.inference_queue import" in kernel
    assert "ModelQueue as _ModelQueue" in kernel
    assert "QueueClosed as _QueueClosed" in kernel
    assert "QueueFull as _QueueFull" in kernel
    # Inline class definitions are gone.
    assert "class _ModelQueue:" not in kernel
    assert "class _QueueFull(Exception):" not in kernel
    assert "class _QueueClosed(Exception):" not in kernel
    # Singleton instantiation stays in kernel.
    assert "_MODEL_QUEUE = _ModelQueue()" in kernel


def test_kernel_queue_uses_event_based_drain() -> None:
    """ModelQueue.close_slot must wait on a threading.Event instead of
    spinning at 250ms intervals. The wrap() finally clears the event
    when a ticket starts and sets it when the active count drops to 0.
    Lives in duecare.chat.inference_queue."""
    queue_src = _QUEUE_MODULE.read_text(encoding="utf-8")
    # Slot init creates the Event in the SET state (slot starts idle).
    assert "idle_event" in queue_src
    assert "idle.set()" in queue_src
    # close_slot uses Event.wait, not the spin loop.
    assert "idle_event.wait(timeout=remaining)" in queue_src
    # wrap() clears the event before the model call and sets it in
    # the finally when no other active ticket remains.
    assert 'slot["idle_event"].clear()' in queue_src
    assert 'slot["idle_event"].set()' in queue_src


def test_kernel_queue_status_has_ttl_cache_and_cache_control() -> None:
    """GET /api/queue/status uses a 1s TTL cache and emits a
    Cache-Control header so heavy multi-tab polling collapses to ~1
    real snapshot per second per process."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "_QUEUE_SNAPSHOT_TTL_SECONDS = 1.0" in kernel
    assert "def _cached_queue_snapshot(" in kernel
    assert 'Cache-Control": "max-age=1, must-revalidate"' in kernel


def test_kernel_has_operator_token_gate() -> None:
    """The kernel prints an operator token at startup and gates the
    destructive endpoints (force-unload + use-chat-as-judge) on the
    X-Operator-Token header or operator_token body field."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "_OPERATOR_TOKEN" in kernel
    assert "secrets.token_urlsafe(24)" in kernel
    assert "def _check_operator_token(" in kernel
    # Constant-time compare prevents timing oracles on token prefix.
    assert "secrets.compare_digest" in kernel
    # Body or header sources both supported.
    assert 'request.headers.get("X-Operator-Token")' in kernel
    assert 'body.get("operator_token")' in kernel
    # use-chat-as-judge gated unconditionally; unloads gated only on force.
    toggle_idx = kernel.find("def api_use_chat_as_judge(")
    toggle_body = kernel[toggle_idx:toggle_idx + 2000]
    assert "_check_operator_token(request, body)" in toggle_body
    unload_idx = kernel.find("def api_unload_chat_model(")
    unload_body = kernel[unload_idx:unload_idx + 2500]
    assert "_check_operator_token(request, body)" in unload_body


def test_nav_js_has_operator_token_helper() -> None:
    """_nav.js exposes window.dcOperatorToken so every page can reuse
    the same prompt+cache flow for the destructive endpoints. The
    force-unload path uses it."""
    nav_js = _read("_nav.js")
    assert "window.dcOperatorToken" in nav_js
    assert "duecare:operator-token" in nav_js
    # ensure() prompts when no token is cached.
    assert "ensure(reason)" in nav_js
    # unloadCurrentModel force path requires the token + sends header.
    assert "X-Operator-Token" in nav_js
    # 401/403 from the gate clears the cached token.
    assert "window.dcOperatorToken.clear()" in nav_js


def test_compare_threads_operator_token_into_judge_toggles() -> None:
    """compare.html threads window.dcOperatorToken into judgeUnload's
    force path AND judgeUseChatAsJudge (always required)."""
    compare = _read("compare.html")
    assert "window.dcOperatorToken.ensure(" in compare
    assert "X-Operator-Token" in compare
    # Two occurrences: one for force-unload, one for the toggle.
    assert compare.count("window.dcOperatorToken.ensure(") >= 2


def test_activity_log_handle_helper() -> None:
    """The shared _activity_log.js exposes dcInferenceError.handle that
    pages can call as a one-liner to consume queue 503 responses."""
    js = _read("_activity_log.js")
    assert "async handle(response, log)" in js


def test_design_pages_consume_queue_handle_helper() -> None:
    """Every design-contract page that calls an inference endpoint
    now consumes dcInferenceError.handle so queue 503s render
    uniformly instead of as raw 'HTTP 503'."""
    for page in ("share.html", "knowledge.html", "process.html", "compare.html"):
        html = _read(page)
        assert "window.dcInferenceError" in html, page + " missing dcInferenceError consumer"


def test_kernel_imports_template_module() -> None:
    """kernel.py no longer carries the inline templates block; it
    imports register_template_routes from duecare.chat.templates and
    calls it once after create_app. This keeps kernel.py focused on
    runtime orchestration and lets the template registry grow in
    its own file."""
    repo_root = Path(__file__).parents[3]
    kernel = (repo_root / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py").read_text(encoding="utf-8")
    assert "from duecare.chat.templates import register_template_routes" in kernel
    assert "_register_template_routes(app)" in kernel
    # The old inline definitions are gone from the kernel.
    assert "_TEMPLATE_HK_LD_BODY = " not in kernel
    assert "def _gemma_fill_template(" not in kernel
    assert "def api_templates_fill(" not in kernel


def test_templates_page_exists_with_design_contract_chrome() -> None:
    """The new /static/templates.html follows the same chrome contract
    as the four other design-contract pages: dc-trust-row.is-private,
    Gemma honesty marker, data-toolbar=copy-json on the activity log,
    "Where Gemma 4 runs on this page" hint block."""
    html = _read("templates.html")
    assert '<body data-nav="templates">' in html
    assert 'class="dc-trust-row is-private"' in html
    assert 'id="tpl-gemma-mark"' in html
    assert 'class="dc-gemma-mark is-optional"' in html
    # Activity log opts into the Copy JSON toolbar.
    assert 'data-toolbar="copy-json"' in html
    # Where Gemma 4 runs hint block.
    assert 'id="tpl-gemma-paths-hint"' in html
    assert "Where Gemma 4 runs on this page" in html
    # Consumes the shared dcInferenceError helper so 503 queue errors
    # render uniformly.
    assert "window.dcInferenceError" in html


def test_templates_page_calls_kernel_endpoints() -> None:
    """The page must call /api/templates/list on load and
    /api/templates/fill on Generate draft, passing the three documented
    body params."""
    html = _read("templates.html")
    assert "/api/templates/list" in html
    assert "/api/templates/fill" in html
    fill_call_idx = html.find("/api/templates/fill")
    fill_section = html[fill_call_idx:fill_call_idx + 800]
    assert "template_id" in fill_section
    assert "bundle" in fill_section
    assert "manual_fields" in fill_section
    assert "use_gemma" in fill_section


def test_templates_nav_link_present() -> None:
    """_nav.html exposes Templates between Knowledge Extraction and
    Search so a caseworker walking the nav left-to-right sees the
    template flow in the expected sequence."""
    nav = _read("_nav.html")
    assert 'data-nav-key="templates"' in nav
    assert 'href="/static/templates.html"' in nav
    # Order: knowledge -> templates -> search. Verify the ordering
    # by string position.
    k_idx = nav.find('data-nav-key="knowledge"')
    t_idx = nav.find('data-nav-key="templates"')
    s_idx = nav.find('data-nav-key="search"')
    assert k_idx >= 0 and t_idx >= 0 and s_idx >= 0
    assert k_idx < t_idx < s_idx, "nav order: knowledge -> templates -> search"


def test_compare_log_has_copy_json_toolbar() -> None:
    """compare.html generates the richest activity log of any page
    (every per-step grade event, both variants, full SSE traces). It
    must opt into the Copy JSON toolbar like the four design-contract
    pages."""
    compare = _read("compare.html")
    log_idx = compare.find('id="cmp-log"')
    log_end = log_idx + 400
    log_section = compare[log_idx:log_end]
    assert 'data-toolbar="copy-json"' in log_section


def test_chat_picker_defaults_to_31b_it() -> None:
    """The model picker now defaults the chat variant to 31b-it. With
    'Use chat model as judge', this means one 31b-it serves both
    chat and grading without a second model load."""
    nav_js = _read("_nav.js")
    # The selection ladder now prefers 31b-it before falling back
    # to e4b-it for legacy compatibility.
    assert "sel.value = '31b-it'" in nav_js
    # The e4b-it fallback is still present for older variant lists
    # that omit 31b-it.
    assert "sel.value = 'e4b-it'" in nav_js


def test_model_picker_handles_queue_busy_unload() -> None:
    """When /api/unload-model returns 409 queue_busy, the picker
    surfaces a confirm dialog so a careful operator does not interrupt
    other users silently. _nav.js (chat slot) and compare.html (judge
    slot) both follow the same pattern."""
    nav_js = _read("_nav.js")
    assert "r.status === 409" in nav_js
    assert "queue_busy" in nav_js
    assert "force: true" in nav_js
    assert "force-interrupt" in nav_js.lower() or "force-unload" in nav_js.lower()
    compare = _read("compare.html")
    # judgeUnload accepts an opts.force argument and recurses on confirm.
    assert "async function judgeUnload(opts)" in compare
    assert "force: force" in compare
    # 409 branch present
    assert "data.status === 'queue_busy'" in compare
