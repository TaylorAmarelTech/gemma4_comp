"""Deterministic document chunker -- splits a source document into provenance-
tagged retrieval passages for the acquisition pipeline (the 10k-doc program's
"properly chunked" step).

Pure + offline + stdlib + DETERMINISTIC (same text -> same chunks): no RNG, no
model, no network. Paragraph-aware packing up to a target size; over-long
paragraphs fall back to sentence-aware splitting; consecutive chunks carry a
char-level overlap so a passage that straddles a boundary is still retrievable.

Every chunk records its parent ``doc_id``, ordinal, and the char offsets of its
CORE span in the source text -- so a retrieved chunk is always traceable back to
the exact span of the cited source ("real, not faked"). The overlap context is
prepended to ``text`` for retrieval but the offsets describe the core span only.
"""
from __future__ import annotations

import re

from pydantic import BaseModel


class Chunk(BaseModel):
    id: str            # f"{doc_id}#c{ordinal:03d}"
    doc_id: str
    ordinal: int
    text: str          # core span (+ prepended overlap context for ordinal > 0)
    char_start: int    # offset of the core span in the source text
    char_end: int
    n_chars: int       # len of the core span (excludes prepended overlap)
    source: str | None = None
    kind: str | None = None
    jurisdiction: str | None = None


# A paragraph = one or more non-blank lines not separated by a blank line.
_PARA = re.compile(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*")
_SENT = re.compile(r"(?<=[.!?])\s+")


def _paragraphs(text: str) -> list[tuple[str, int, int]]:
    """(paragraph_text, char_start, char_end) for each paragraph, real offsets."""
    return [(m.group().strip(), m.start(), m.end()) for m in _PARA.finditer(text) if m.group().strip()]


def _sentence_spans(para: str) -> list[tuple[str, int]]:
    """(sentence_incl_trailing_ws, offset_in_para) with EXACT offsets -- so packed
    chunk offsets stay traceable to the source (no split-and-recount drift)."""
    spans: list[tuple[str, int]] = []
    prev = 0
    for m in re.finditer(r"[.!?]+(?:\s+|$)", para):
        spans.append((para[prev:m.end()], prev))
        prev = m.end()
    if prev < len(para):
        spans.append((para[prev:], prev))
    return spans


def _split_long_paragraph(para: str, start: int, target: int) -> list[tuple[str, int, int]]:
    """Sentence-pack an over-long paragraph into <= target spans with REAL source
    offsets (``start`` is the paragraph's offset in the source text)."""
    spans: list[tuple[str, int, int]] = []
    cur, cur_off = "", None
    for sent, off in _sentence_spans(para):
        if cur and len(cur) + len(sent) > target:
            spans.append((cur.strip(), start + cur_off, start + cur_off + len(cur)))
            cur, cur_off = sent, off
        else:
            if not cur:
                cur_off = off
            cur += sent
    if cur.strip():
        spans.append((cur.strip(), start + cur_off, start + cur_off + len(cur)))
    return spans or [(para.strip(), start, start + len(para))]


def chunk_document(
    text: str,
    *,
    doc_id: str,
    target_chars: int = 900,
    overlap_chars: int = 150,
    source: str | None = None,
    kind: str | None = None,
    jurisdiction: str | None = None,
) -> list[Chunk]:
    """Split ``text`` into ~``target_chars`` provenance-tagged chunks with
    char-level overlap. Deterministic and offline. Returns [] for empty input."""
    text = text or ""
    if not text.strip():
        return []

    # 1) paragraph spans (real offsets); explode over-long paragraphs by sentence
    pieces: list[tuple[str, int, int]] = []
    for ptext, pstart, _pend in _paragraphs(text):
        if len(ptext) > target_chars:
            pieces.extend(_split_long_paragraph(ptext, pstart, target_chars))
        else:
            pieces.append((ptext, pstart, pstart + len(ptext)))

    # 2) pack consecutive pieces into chunks up to target_chars
    packed: list[tuple[str, int, int]] = []
    cur_text, cur_start, cur_end = "", -1, -1
    for ptext, pstart, pend in pieces:
        if cur_text and len(cur_text) + 2 + len(ptext) > target_chars:
            packed.append((cur_text, cur_start, cur_end))
            cur_text, cur_start, cur_end = ptext, pstart, pend
        else:
            if not cur_text:
                cur_start = pstart
            cur_text = (cur_text + "\n\n" + ptext) if cur_text else ptext
            cur_end = pend
    if cur_text:
        packed.append((cur_text, cur_start, cur_end))

    # 3) build Chunk models; prepend overlap context from the previous chunk
    chunks: list[Chunk] = []
    for i, (body, c_start, c_end) in enumerate(packed):
        out_text = body
        if i > 0 and overlap_chars > 0:
            tail = packed[i - 1][0][-overlap_chars:].strip()
            if tail:
                out_text = tail + " … " + body  # ellipsis marks the overlap join
        chunks.append(Chunk(
            id=f"{doc_id}#c{i:03d}", doc_id=doc_id, ordinal=i, text=out_text,
            char_start=c_start, char_end=c_end, n_chars=len(body),
            source=source, kind=kind, jurisdiction=jurisdiction))
    return chunks
