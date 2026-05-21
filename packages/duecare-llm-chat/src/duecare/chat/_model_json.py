"""Robust JSON extraction from model output.

Instruction-tuned chat models often wrap structured output in
markdown code fences, prose preambles, trailing explanations, or
emit minor syntactic noise (trailing commas, single quotes,
Python-style ``None``/``True``/``False``) that ``json.loads``
rejects.

The historical extractor in ``harnesses/process/handler.py`` used a
greedy regex (``\\{[\\s\\S]*\\}``), which:

  - Matches from the FIRST ``{`` to the LAST ``}`` in the text, so
    multiple JSON-looking blocks (or prose between them) end up in
    one un-parseable blob.
  - Has no fallback if ``json.loads`` rejects the result.
  - Returns ``None`` silently, leaving the operator with no signal
    about WHY the parse failed -- only that the deterministic
    fallback was used.

This module is the one canonical place for that extraction. It is
deliberately conservative: every repair step is documented and
opt-in, so a future content failure can be diagnosed by inspecting
``ExtractedJson.attempts``.

Public surface:

* ``extract_json(text)`` -> ``ExtractedJson`` -- the diagnostic form.
* ``extract_json_object(text)`` -> ``dict | None`` -- back-compat
  shim matching the old ``_extract_json_object`` signature.

Repair steps applied, in order, each independently undo-able:

  1. Strip markdown code fences.
  2. Balanced-brace / bracket scan to find the first complete
     top-level JSON object or array, ignoring strings.
  3. Strict ``json.loads`` on the extracted slice.
  4. Light repair: drop trailing commas before ``}`` / ``]``,
     replace bare ``None`` / ``True`` / ``False`` outside string
     literals with ``null`` / ``true`` / ``false``.
  5. Quote repair: convert single-quoted JSON-ish output to
     double-quoted (last resort -- has edge cases on apostrophes
     inside strings).

Anything still unparsed returns ``None`` payload with the full
attempt log so the caller can surface a diagnostic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


_FENCE_RE = re.compile(
    r"```(?:json|JSON|json5)?\s*\n?(.*?)\n?```",
    re.DOTALL,
)


@dataclass
class ExtractedJson:
    """Result of attempting to extract a JSON payload from text.

    ``payload`` is the parsed object/array (``dict`` or ``list``),
    or ``None`` if no recovery strategy succeeded. ``attempts`` is
    an ordered log of every strategy tried, useful for the activity
    log on a content failure. ``raw_preview`` is the first ~600
    characters of input so the operator can see what the model
    actually returned.
    """

    payload: Any | None = None
    attempts: list[str] = field(default_factory=list)
    raw_preview: str = ""

    @property
    def ok(self) -> bool:
        return self.payload is not None


def _strip_fences(text: str) -> str:
    """Return ``text`` with the FIRST markdown code fence stripped to
    its body. If no fence is present, return the input unchanged.
    Defensive against fences with language tags (\\`\\`\\`json) and
    fences with no tag."""
    match = _FENCE_RE.search(text)
    if not match:
        return text
    body = match.group(1)
    return body if body else text


def _find_balanced_span(
    text: str, open_ch: str, close_ch: str
) -> tuple[int, int] | None:
    """Return ``(start, end)`` indices for the first balanced
    ``open_ch``...``close_ch`` span at or after the first
    occurrence of ``open_ch``. Ignores braces/brackets inside JSON
    string literals (handles escaped quotes). Returns ``None`` if
    no balanced span is found."""
    start = text.find(open_ch)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return (start, i + 1)
    return None


def _slice_first_json_value(text: str) -> str | None:
    """Find the first top-level JSON object or array span in
    ``text`` and return its substring. Picks the earlier of an
    object span or an array span when both are present."""
    obj_span = _find_balanced_span(text, "{", "}")
    arr_span = _find_balanced_span(text, "[", "]")
    spans = [s for s in (obj_span, arr_span) if s is not None]
    if not spans:
        return None
    spans.sort(key=lambda s: s[0])
    s, e = spans[0]
    return text[s:e]


_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
# Match bare Python None/True/False that look like JSON values -- followed
# by a structural character, EOL, or end of string. Avoids touching
# identifiers like "NoneType" or "TrueColor".
_PY_NONE_RE = re.compile(r"\bNone\b(?=\s*(?:[,}\]]|$|\n))")
_PY_TRUE_RE = re.compile(r"\bTrue\b(?=\s*(?:[,}\]]|$|\n))")
_PY_FALSE_RE = re.compile(r"\bFalse\b(?=\s*(?:[,}\]]|$|\n))")


def _light_repair(text: str) -> str:
    """Apply repairs that are safe on already-valid JSON (so a
    re-parse is harmless on healthy input)."""
    repaired = _TRAILING_COMMA_RE.sub(r"\1", text)
    repaired = _PY_NONE_RE.sub("null", repaired)
    repaired = _PY_TRUE_RE.sub("true", repaired)
    repaired = _PY_FALSE_RE.sub("false", repaired)
    return repaired


def _single_to_double_quote(text: str) -> str:
    """Last-resort conversion of single-quoted JSON-ish to double
    quotes. Skips single quotes that look like apostrophes inside
    a word (don't / it's). Crude but useful when a model emits
    Python ``repr()`` instead of JSON."""
    out: list[str] = []
    in_dq = False
    in_sq = False
    escape = False
    for i, ch in enumerate(text):
        prev = text[i - 1] if i > 0 else ""
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\":
            out.append(ch)
            escape = True
            continue
        if ch == '"' and not in_sq:
            in_dq = not in_dq
            out.append(ch)
            continue
        if ch == "'" and not in_dq:
            if in_sq:
                in_sq = False
                out.append('"')
                continue
            # Only treat ' as an opening string quote if it follows a
            # JSON structural character. Apostrophes inside words
            # ("don't") follow letters and are left alone.
            if prev in ("", "{", "[", ",", ":", " ", "\n", "\t"):
                in_sq = True
                out.append('"')
                continue
        out.append(ch)
    return "".join(out)


def extract_json(text: str) -> ExtractedJson:
    """Extract the first top-level JSON value from ``text``.

    Returns an :class:`ExtractedJson` whose ``payload`` is a dict
    or list on success, or ``None`` if every repair strategy failed.
    The ``attempts`` log records each strategy tried so the caller
    can surface why parsing failed.
    """
    result = ExtractedJson(raw_preview=(text or "")[:600])
    if not text:
        result.attempts.append("empty input")
        return result

    cleaned = text.strip()

    after_fence = _strip_fences(cleaned)
    if after_fence != cleaned:
        result.attempts.append("stripped markdown code fence")
        cleaned = after_fence.strip()

    span = _slice_first_json_value(cleaned)
    if not span:
        result.attempts.append("no balanced { ... } or [ ... ] span found")
        return result
    if span != cleaned:
        result.attempts.append(
            f"balanced span trimmed {len(cleaned) - len(span)} surrounding chars"
        )

    try:
        result.payload = json.loads(span)
        result.attempts.append("parsed via strict json.loads")
        return result
    except json.JSONDecodeError as exc:
        result.attempts.append(f"strict json.loads failed: {exc.msg}")

    repaired = _light_repair(span)
    if repaired != span:
        try:
            result.payload = json.loads(repaired)
            result.attempts.append("parsed after light repair")
            return result
        except json.JSONDecodeError as exc:
            result.attempts.append(f"light-repair parse failed: {exc.msg}")

    quoted = _single_to_double_quote(repaired)
    if quoted != repaired:
        try:
            result.payload = json.loads(quoted)
            result.attempts.append("parsed after single->double quote repair")
            return result
        except json.JSONDecodeError as exc:
            result.attempts.append(f"quote-repair parse failed: {exc.msg}")

    result.attempts.append("all repair strategies exhausted")
    return result


def extract_json_object(text: str) -> dict | None:
    """Back-compat shim for callers that expect a ``dict`` or
    ``None``. Returns ``None`` if the extraction failed OR the
    payload was a list at the top level."""
    extracted = extract_json(text)
    if extracted.payload is None or not isinstance(extracted.payload, dict):
        return None
    return extracted.payload


__all__ = ["ExtractedJson", "extract_json", "extract_json_object"]
