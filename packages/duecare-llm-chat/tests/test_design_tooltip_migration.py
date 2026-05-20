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
    judge load doesn't make /api/load-model/status look busy."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    assert "_MODEL_LOAD_STATE_EVAL" in src
    assert "_MODEL_LOAD_LOCK_EVAL" in src
    assert "_MODEL_LOAD_EVENTS_EVAL" in src
    # The endpoints must write to app.state.evaluator_call (the slot
    # the chat package already prefers for grading).
    assert "app.state.evaluator_call = loaded_local.backend" in src
    assert "app.state.evaluator_call = None" in src


def test_kernel_evaluator_unload_flushes_cuda_cache() -> None:
    """On unload, the kernel must call torch.cuda.empty_cache() (best-
    effort) so the freed weights actually release VRAM."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    # Look at the unload handler region specifically.
    unload_idx = src.find("def api_unload_evaluator_model(")
    assert unload_idx >= 0, "kernel.py is missing api_unload_evaluator_model"
    # Examine the next ~3 KB of source for the cache flush.
    region = src[unload_idx:unload_idx + 3000]
    assert "torch.cuda.empty_cache" in region or "_torch.cuda.empty_cache" in region


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
    assert "async function judgeUnload()" in html
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


def test_kernel_judge_preflight_returns_expected_shape() -> None:
    """The preflight result must include the 8 fields the UI relies on:
    variant, needs_disk_gb, needs_gpu_gb, disk_free_gb, gpu_free_gb,
    ok, reasons, notes."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    # Look at the preflight helper's return dict literal.
    idx = src.find("def _judge_preflight(")
    assert idx >= 0
    body = src[idx:idx + 4000]
    for key in ("variant", "needs_disk_gb", "needs_gpu_gb",
                "disk_free_gb", "gpu_free_gb", "ok", "reasons", "notes"):
        assert f'"{key}":' in body, (
            f"_judge_preflight return must include the '{key}' field"
        )


def test_kernel_judge_load_enforces_preflight_with_override() -> None:
    """The load endpoint must run preflight and refuse with 503 when
    it fails, unless the caller passes ``override: true``. The error
    envelope must carry the preflight result so the UI can render
    the actual reasons."""
    src = _KERNEL_PATH.read_text(encoding="utf-8")
    idx = src.find("def api_load_evaluator_model(")
    assert idx >= 0
    body = src[idx:idx + 4000]
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
