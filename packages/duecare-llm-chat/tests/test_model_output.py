"""Regression tests for `duecare.chat._model_output.sanitize_model_output`.

These cases are taken from real Gemma 4 thinking-mode outputs that
leaked to the user during live Kaggle testing. Adding a new case
here = adding a known-bad shape we've seen and want to defend
against. Every test asserts on observable behavior — what the user
actually sees in the chat UI — not on internal regex implementation
details.

Run:
    py -3.10 -m pytest packages/duecare-llm-chat/tests/test_model_output.py -v
"""

from __future__ import annotations

import pytest

from duecare.chat._model_output import sanitize_model_output


class TestEmptyAndPassThrough:
    def test_empty_string_returns_empty(self) -> None:
        assert sanitize_model_output("") == ""

    def test_none_returns_empty(self) -> None:
        # Defensive: callers occasionally pass None on error paths.
        assert sanitize_model_output(None) == ""  # type: ignore[arg-type]

    def test_clean_text_passes_through(self) -> None:
        clean = "Hello! How can I help you today?"
        assert sanitize_model_output(clean) == clean

    def test_clean_markdown_passes_through(self) -> None:
        text = (
            "Per **ILO C181 Art. 7**, the worker is not liable for any "
            "fee. See `POEA MC 14-2017` for the PH→HK corridor."
        )
        assert sanitize_model_output(text) == text

    def test_html_emitted_intentionally_passes_through(self) -> None:
        # We must not strip <br> / <hr> / <a> — the model legitimately
        # emits those when asked for HTML output.
        text = "Line 1<br>Line 2<hr><a href='https://x'>link</a>"
        assert sanitize_model_output(text) == text


class TestThinkingChannel:
    """Gemma 4 thinking-mode emits `<thinking>...</thinking><channel|>FINAL`.

    We saw this leak verbatim in the user's first live E2B test.
    """

    def test_simple_channel_split(self) -> None:
        # Verbatim from user's test on 2026-05-08
        leaked = (
            'The user simply said "HELLO". This is a very basic greeting. '
            'I should respond in a friendly and open manner, perhaps '
            'asking how I can help.<channel|>Hello! How can I help '
            'you today?'
        )
        assert sanitize_model_output(leaked) == "Hello! How can I help you today?"

    def test_multi_channel_takes_last_segment(self) -> None:
        # Some thinking-mode outputs interleave: thinking → channel →
        # more planning → channel → final. We must take the last
        # segment, not split-and-keep-middle.
        text = (
            "First I think about X.<channel|>Initial draft.<channel|>"
            "Final polished answer."
        )
        assert sanitize_model_output(text) == "Final polished answer."

    def test_thinking_block_no_channel(self) -> None:
        text = "<thinking>Internal reasoning</thinking>The actual answer."
        assert sanitize_model_output(text) == "The actual answer."

    def test_think_block_no_channel(self) -> None:
        # Some templates use <think> instead of <thinking>.
        text = "<think>Internal reasoning</think>The actual answer."
        assert sanitize_model_output(text) == "The actual answer."

    def test_thinking_block_multiline(self) -> None:
        text = (
            "<thinking>\n"
            "Step 1: analyze the prompt\n"
            "Step 2: identify legal red flags\n"
            "Step 3: compose response\n"
            "</thinking>\n"
            "The actual response begins here."
        )
        assert sanitize_model_output(text) == "The actual response begins here."

    def test_thinking_then_channel_then_thinking_block(self) -> None:
        # Belt-and-suspenders: model emits a channel marker AND a
        # thinking block in the final segment. Both should disappear.
        text = (
            "Pre-thinking<channel|>"
            "<thinking>more reasoning</thinking>"
            "Final answer."
        )
        assert sanitize_model_output(text) == "Final answer."


class TestTurnDelimiters:
    def test_turn_close_truncation(self) -> None:
        text = "The actual answer.<turn|>more text we don't want"
        assert sanitize_model_output(text) == "The actual answer."

    def test_end_of_turn_truncation(self) -> None:
        text = "The actual answer.<end_of_turn>more text"
        assert sanitize_model_output(text) == "The actual answer."

    def test_input_template_marker_strip(self) -> None:
        # batch_decode often returns the entire input + output blob.
        # Anything before <|turn>model is the echoed input.
        text = (
            "<bos><start_of_turn>user\nHello<end_of_turn>\n"
            "<|turn>modelHi there!"
        )
        assert sanitize_model_output(text) == "Hi there!"


class TestSpecialTokens:
    def test_strip_bos_eos(self) -> None:
        assert sanitize_model_output("<bos>Answer<eos>") == "Answer"

    def test_strip_start_end_of_turn(self) -> None:
        assert sanitize_model_output(
            "<start_of_turn>Answer<end_of_turn>"
        ) == "Answer"


class TestRealWorldHarnessOutput:
    """The full case the user pasted on 2026-05-08."""

    def test_full_harness_response(self) -> None:
        # Heavily abbreviated but structurally identical to the real
        # 4,681-char response that leaked.
        leaked = (
            "Based on the safety harness firing, I must adhere strictly "
            "to the required protocol: identify each fired indicator, "
            "cite the relevant statutes, and redirect the user to "
            "appropriate NGO/regulator hotlines.\n\n"
            "**Fired Indicators Identified:**\n"
            "1. **ilo_indicator_passport_retention**\n\n"
            "**Drafting the Response:** (Ensure strict adherence...)"
            "<channel|>"
            "The scenario you described contains multiple severe "
            "indicators of forced labour and exploitation."
        )
        out = sanitize_model_output(leaked)
        assert out.startswith("The scenario you described")
        assert "Drafting the Response" not in out
        assert "Fired Indicators" not in out
        assert "<channel|>" not in out
        assert "<thinking>" not in out


class TestIdempotence:
    """Calling sanitize twice should be the same as calling once."""

    @pytest.mark.parametrize("text", [
        "",
        "Already clean text.",
        "<thinking>x</thinking>Answer.",
        "Pre<channel|>Final.",
        "<bos>Answer<eos>",
        "<thinking>a</thinking>Pre<channel|>Final.<end_of_turn>",
    ])
    def test_idempotent(self, text: str) -> None:
        once = sanitize_model_output(text)
        twice = sanitize_model_output(once)
        assert once == twice
