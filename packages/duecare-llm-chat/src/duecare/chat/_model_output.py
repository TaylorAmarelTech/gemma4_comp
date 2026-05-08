"""Single-source sanitizer for model output text.

Gemma 4 (and other instruction-tuned chat models) emit template
control tokens, thinking-mode scratchpads, and turn delimiters that
we don't want surfacing in the user-visible response. Historically
this stripping was done inline in each kernel's _gemma_call (and
NOT done at all for cloud / Ollama paths, which would have shown
visible artifacts on a different deployment).

This module is the one canonical place for that cleanup. Local
Gemma calls, cloud-Gemini, cloud-OpenAI, and cloud-Ollama all use
`sanitize_model_output(text)` at the boundary where the model's
response becomes the user-visible response.

Tokens it strips (in order):
  1. Input-side template wrapper:
        <|turn>model ...
     anything before this is the harness pre-context the model was
     conditioned on, not its answer.
  2. Gemma 4 thinking-mode separator:
        <thinking>...</thinking><channel|>FINAL ANSWER
     We take the LAST <channel|> split — defends against models
     that emit multiple thinking-then-channel cycles (planning →
     channel → next planning step → channel → final).
  3. Generic <thinking>...</thinking> and <think>...</think>
     blocks anywhere in the remaining text.
  4. Closing turn delimiters: <turn|>, <end_of_turn>.
  5. Special tokens: <bos>, <eos>, <start_of_turn>, <end_of_turn>.

What it does NOT strip:
  - Markdown code fences (```python ... ```)
  - HTML the model intentionally emits (`<br>`, `<hr>`, `<a href>`)
  - <tool_call> blocks — those are caller-sanitized separately
  - Citation brackets like [ILO C181 Art. 7]

Conservative-by-default: a token-stripper that's too aggressive
would mangle legitimate user text. Each stripped marker is a
documented Gemma 4 / Llama-family template token. New tokens
should be added with a regression test capturing the actual
model-output shape that motivated the addition.
"""

from __future__ import annotations

import re
from typing import Final


# ---------------------------------------------------------------------------
# Markers known to leak from supported model templates
# ---------------------------------------------------------------------------

_INPUT_TEMPLATE_MARKER: Final = "<|turn>model"
_CHANNEL_DELIM:         Final = "<channel|>"
_TURN_END_TEXT:         Final = "<turn|>"
_END_OF_TURN_TOKEN:     Final = "<end_of_turn>"
_START_OF_TURN_TOKEN:   Final = "<start_of_turn>"
_BOS_TOKEN:             Final = "<bos>"
_EOS_TOKEN:             Final = "<eos>"

# `re.DOTALL` so `.` matches newlines inside multi-line thinking blocks.
_THINKING_BLOCK_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)
_THINK_BLOCK_RE    = re.compile(r"<think>.*?</think>",       re.DOTALL)


def sanitize_model_output(text: str) -> str:
    """Strip template artifacts from a model response. Idempotent —
    calling this twice on the same string is the same as calling it
    once. Safe to call on already-clean text (cloud-Gemini etc.).

    Returns the cleaned text with leading/trailing whitespace stripped.
    Empty input returns "".
    """
    if not text:
        return ""

    # 1. Strip the harness-side input template wrapper. tokenizer
    # batch_decode often returns the entire input + output as one
    # blob; everything before the model's continuation token is the
    # echoed input we want to discard.
    if _INPUT_TEMPLATE_MARKER in text:
        text = text.split(_INPUT_TEMPLATE_MARKER, 1)[1]

    # 2. Take the LAST segment after a thinking-mode <channel|>
    # delimiter. Defensive against models that interleave multiple
    # thinking + channel cycles. The user-visible answer is always
    # the last segment.
    if _CHANNEL_DELIM in text:
        text = text.rsplit(_CHANNEL_DELIM, 1)[1]

    # 3. Strip any remaining <thinking> / <think> blocks. Some
    # templates emit these without a trailing channel delimiter.
    text = _THINKING_BLOCK_RE.sub("", text)
    text = _THINK_BLOCK_RE.sub("", text)

    # 4. Truncate at end-of-turn delimiters.
    if _TURN_END_TEXT in text:
        text = text.split(_TURN_END_TEXT, 1)[0]
    if _END_OF_TURN_TOKEN in text:
        text = text.split(_END_OF_TURN_TOKEN, 1)[0]

    # 5. Drop literal special tokens.
    for tok in (_BOS_TOKEN, _EOS_TOKEN, _START_OF_TURN_TOKEN,
                _END_OF_TURN_TOKEN):
        text = text.replace(tok, "")

    return text.strip()


__all__ = ["sanitize_model_output"]
