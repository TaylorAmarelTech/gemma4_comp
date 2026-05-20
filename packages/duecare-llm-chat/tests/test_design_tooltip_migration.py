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
    one-line muted caveat to the activity log explaining that the pct
    average can hide a real difference in coverage (more applicable
    dims at PARTIAL quality drags the weighted average down even when
    the response is more thorough)."""
    html = _read("compare.html")
    assert "Math.abs(aPct - bPct) < 2.0" in html, (
        "compare.html cmpGrade must detect close-grade comparisons "
        "(within 2pp) so it can surface the coverage caveat."
    )
    assert "within 2pp" in html
    assert "see the coverage row" in html
