"""Structural text chunking for Duecare's RAG / Import / Deep-fetch layers.

The chunker prefers semantic-boundary splits over fixed-window splits because
this codebase routinely indexes legal/statutory text where structure carries
meaning (Article 3 §2 must travel with its parent heading, otherwise BM25
loses the very thing it keys on).

Strategy in priority order:

    1. Markdown headers (`#`, `##`, `###`) become section boundaries.
       Each section is its own chunk; long sections get further paragraph-
       split with a small overlap.
    2. Statute markers (`Article 1`, `Section 3`, `§ 4`, `Cap. 57 §32`)
       are detected as fallback section boundaries when no markdown
       headers are present.
    3. Paragraph splits (double-newline) accumulate into chunks up to
       `max_chunk_chars`, with a small character overlap on the boundaries
       so a sentence that straddles two chunks doesn't lose context for
       lexical retrieval.

The output schema is stable so downstream BM25 / reranker / citation
lookup all agree on field names:

    {
        "id":              <stable-ish chunk id>,
        "parent_doc_id":   <upstream doc id>,
        "parent_doc_title":<upstream doc title>,
        "source":          <upstream source/URL>,
        "heading_path":    "Article 1 > Section 3"  (str, "" if none),
        "text":            <chunk text, never truncated mid-sentence
                            on a known boundary>,
        "char_start":      <int offset into the parent doc>,
        "char_end":        <int offset>,
        "is_overlap":      <bool — True if this chunk starts in the
                            previous chunk's tail (set by accumulator)>,
    }

No external dependencies. ~250 lines of stdlib regex. Designed for the
35-doc / hand-curated corpus + a long tail of user-imported documents
(potentially MB-scale court filings) and deep-fetched HTML pages.
"""
from __future__ import annotations

import re
from typing import Iterable


# Markdown header at column 0 — supports up to ###### (h1..h6).
# We capture the level + the heading text so the heading_path can be
# rebuilt as a breadcrumb (h1 > h2 > h3) when nested.
_MD_HEADING_RE = re.compile(
    r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*\s*$",
    re.MULTILINE,
)

# Statute markers — fallback when there are no markdown headers. Matches
# common forms: "Article 1", "Article 1.", "Section 3", "§ 4",
# "Section 32 (Wages)", "Cap. 57 §32", "RA 8042 §5". Case-insensitive.
# We intentionally don't match "Article 1.2" as a single block — sub-
# numbering is handled by the paragraph splitter inside each section.
_STATUTE_MARKER_RE = re.compile(
    r"^\s*(?:"
    r"Article\s+\d+[A-Za-z]?(?:\.\d+)?"      # Article 1, Article 12.3
    r"|Section\s+\d+[A-Za-z]?(?:\.\d+)?"     # Section 31
    r"|§\s*\d+[A-Za-z]?(?:\.\d+)?"          # § 4, §31
    r"|Sec\.?\s+\d+[A-Za-z]?(?:\.\d+)?"      # Sec. 4
    r"|Art\.?\s+\d+[A-Za-z]?(?:\.\d+)?"      # Art. 7
    r")\b.*$",
    re.MULTILINE | re.IGNORECASE,
)

# Paragraph splitter — two-or-more newlines.
_PARA_SPLIT_RE = re.compile(r"\n{2,}")

# Sentence splitter (very rough — keeps decimal numbers + abbreviations
# from breaking). Used only as a last resort when a single paragraph is
# longer than max_chunk_chars (rare for legal text, common for HTML
# pages with one giant <p>).
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _strip_md_heading_marks(line: str) -> str:
    """Remove the leading `#` markers from a heading line."""
    m = _MD_HEADING_RE.match(line)
    if not m:
        return line
    return m.group("title").strip()


def _has_markdown_headers(text: str) -> bool:
    """True iff the text contains at least one `#` / `##` heading."""
    return bool(_MD_HEADING_RE.search(text or ""))


def _has_statute_markers(text: str) -> bool:
    """True iff the text contains at least one statute-style marker."""
    return bool(_STATUTE_MARKER_RE.search(text or ""))


def _split_at_markdown_headers(text: str) -> list[tuple[str, str, int]]:
    """Split text by `#`-headers. Returns [(heading_path, body, start_offset)].

    Heading path uses ` > ` as the breadcrumb separator and rebuilds the
    enclosing hierarchy:
      # Title
      Body 1
      ## Subtitle
      Body 2
    yields [("Title", "Body 1", 0), ("Title > Subtitle", "Body 2", N)].

    Text before the first heading becomes a section with heading_path="".
    """
    matches = list(_MD_HEADING_RE.finditer(text or ""))
    if not matches:
        return [("", text or "", 0)]
    sections: list[tuple[str, str, int]] = []
    # Preamble (before first heading)
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble, 0))
    # Heading hierarchy stack — index by level (1..6)
    stack: list[str] = []
    for i, m in enumerate(matches):
        level = len(m.group("hashes"))
        title = m.group("title").strip()
        # Pop stack to current depth
        while len(stack) >= level:
            stack.pop()
        stack.append(title)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            heading_path = " > ".join(stack)
            sections.append((heading_path, body, m.start()))
    return sections


def _split_at_statute_markers(text: str) -> list[tuple[str, str, int]]:
    """Split text by statute-style markers (Article N, Section N, § N)."""
    matches = list(_STATUTE_MARKER_RE.finditer(text or ""))
    if not matches:
        return [("", text or "", 0)]
    sections: list[tuple[str, str, int]] = []
    # Preamble
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble, 0))
    for i, m in enumerate(matches):
        marker = m.group(0).strip()
        # Body = from end-of-marker-line to start of next marker
        # (or end of text). Marker stays as the heading_path label.
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((marker, body, m.start()))
    return sections


def _split_long_section(text: str, *,
                          max_chunk_chars: int = 900,
                          overlap_chars: int = 120) -> list[tuple[str, int]]:
    """Split a single section's body into <=max_chunk_chars chunks.
    Returns [(chunk_text, char_offset_into_section)].

    Strategy:
      - First try paragraph (\\n\\n) boundaries; accumulate paragraphs
        into chunks up to max_chunk_chars.
      - If a single paragraph is > max_chunk_chars, sentence-split it.
      - If a single sentence is > max_chunk_chars, hard-split at the
        max_chunk_chars boundary.
      - Add overlap: each new chunk starts with the last `overlap_chars`
        of the previous one (so a sentence that straddles two chunks
        still appears in both for BM25 purposes).
    """
    if len(text) <= max_chunk_chars:
        return [(text, 0)]
    # First level: paragraphs
    paragraphs: list[tuple[str, int]] = []
    cursor = 0
    for piece in _PARA_SPLIT_RE.split(text):
        # Find piece's offset back in text. We use cursor+1 search to
        # tolerate variable-width separators.
        loc = text.find(piece, cursor)
        if loc < 0:
            loc = cursor
        paragraphs.append((piece, loc))
        cursor = loc + len(piece)
    # Accumulate
    chunks: list[tuple[str, int]] = []
    cur_text = ""
    cur_start = paragraphs[0][1] if paragraphs else 0
    for para, off in paragraphs:
        if not para.strip():
            continue
        # Single paragraph bigger than the budget — sentence-split it.
        if len(para) > max_chunk_chars:
            # Flush current accumulator first.
            if cur_text:
                chunks.append((cur_text.strip(), cur_start))
                cur_text = ""
            sentences = _SENTENCE_END_RE.split(para)
            sub_text = ""
            sub_start = off
            for sent in sentences:
                if len(sub_text) + len(sent) + 1 <= max_chunk_chars:
                    sub_text = (sub_text + " " + sent).strip() if sub_text else sent
                else:
                    if sub_text:
                        chunks.append((sub_text.strip(), sub_start))
                    # Sentence itself larger than budget? Hard-cut.
                    if len(sent) > max_chunk_chars:
                        for hc in range(0, len(sent), max_chunk_chars):
                            chunks.append((sent[hc:hc + max_chunk_chars], off + hc))
                        sub_text = ""
                        sub_start = off + len(sent)
                    else:
                        sub_text = sent
                        sub_start = off
            if sub_text:
                chunks.append((sub_text.strip(), sub_start))
            cur_start = off + len(para)
            continue
        # Normal paragraph — try to fit into the current chunk.
        if len(cur_text) + len(para) + 2 <= max_chunk_chars:
            cur_text = (cur_text + "\n\n" + para).strip() if cur_text else para
        else:
            if cur_text:
                chunks.append((cur_text.strip(), cur_start))
            cur_text = para
            cur_start = off
    if cur_text:
        chunks.append((cur_text.strip(), cur_start))
    # Apply overlap (last N chars of prev → start of next) for
    # chunks 2..N. Returns (text, char_offset, is_overlap_prepended)
    # so the caller knows which chunks ACTUALLY received an overlap
    # prefix vs. which merely happen to be position-2-or-later. That
    # distinction matters for downstream dedup/scoring decisions.
    if overlap_chars > 0 and len(chunks) > 1:
        with_overlap: list[tuple[str, int, bool]] = [(chunks[0][0], chunks[0][1], False)]
        for i in range(1, len(chunks)):
            prev_text, _ = chunks[i - 1]
            this_text, this_off = chunks[i]
            tail = prev_text[-overlap_chars:] if len(prev_text) > overlap_chars else prev_text
            # Don't overlap if the previous chunk's tail already overlaps
            # the current chunk's head verbatim.
            if not this_text.startswith(tail[:32]):
                this_text = "…" + tail.strip() + "\n\n" + this_text
                with_overlap.append((this_text, this_off, True))
            else:
                with_overlap.append((this_text, this_off, False))
        return with_overlap
    return [(t, off, False) for t, off in chunks]


def chunk_text(text: str,
                  *,
                  parent_doc_id: str = "",
                  parent_doc_title: str = "",
                  source: str = "",
                  max_chunk_chars: int = 900,
                  overlap_chars: int = 120,
                  base_heading: str = "") -> list[dict]:
    """Top-level entry point. Returns a list of chunk dicts.

    Args:
        text: the full document text. Markdown is preferred; plain text
              and HTML-with-headings also work.
        parent_doc_id / parent_doc_title / source: passed through into
              every chunk so downstream code can build attribution
              without re-joining.
        max_chunk_chars: target chunk size. Smaller = better BM25
              precision; larger = more context per chunk. 900 is a
              sweet spot for a Gemma 8K-context budget where we feed
              top-5 chunks (5 × 900 = 4500 chars).
        overlap_chars: how much of the previous chunk's tail to prepend
              to the next chunk. 120 chars covers ~20 words, enough to
              keep a sentence-spanning idea retrievable in the chunk
              that lacks the start of the sentence.
        base_heading: optional prefix for every chunk's heading_path.
              Useful when the doc is itself a section of a larger
              corpus (e.g. "ILO C189 > " for a chunk of Article 9).

    Returns:
        list of {id, parent_doc_id, parent_doc_title, source,
                 heading_path, text, char_start, char_end, is_overlap}.
        Empty list if the input is empty/whitespace.
    """
    text = (text or "").strip()
    if not text:
        return []

    # Pick the section splitter based on what structure the text has.
    # Markdown wins; statute markers second; otherwise treat the whole
    # doc as one section.
    if _has_markdown_headers(text):
        sections = _split_at_markdown_headers(text)
    elif _has_statute_markers(text):
        sections = _split_at_statute_markers(text)
    else:
        sections = [("", text, 0)]

    out: list[dict] = []
    for section_idx, (heading, body, sec_offset) in enumerate(sections):
        full_heading = (
            (base_heading + " > " if base_heading else "") + heading
        ).strip(" >")
        # Split overly-long sections into paragraph-bounded chunks.
        sub_chunks = _split_long_section(
            body, max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        for i, sub in enumerate(sub_chunks):
            # _split_long_section returns 3-tuples post v0.7.1; treat
            # 2-tuples as legacy (is_overlap=False) for safety.
            if len(sub) == 3:
                chunk_text_str, chunk_off, is_overlap = sub
            else:
                chunk_text_str, chunk_off = sub
                is_overlap = False
            chunk_text_str = chunk_text_str.strip()
            if not chunk_text_str:
                continue
            char_start = sec_offset + chunk_off
            char_end = char_start + len(chunk_text_str)
            chunk_id = (
                f"{parent_doc_id}#s{section_idx:02d}c{i:02d}"
                if parent_doc_id else
                f"chunk_{section_idx:02d}_{i:02d}"
            )
            out.append({
                "id":               chunk_id,
                "parent_doc_id":    parent_doc_id,
                "parent_doc_title": parent_doc_title,
                "source":           source,
                "heading_path":     full_heading,
                "text":             chunk_text_str,
                "char_start":       char_start,
                "char_end":         char_end,
                "is_overlap":       is_overlap,
            })
    return out


def chunks_to_corpus_entries(chunks: Iterable[dict]) -> list[tuple[str, str, str, str]]:
    """Convert chunk dicts to the (id, title, source, snippet) tuple
    shape used by the existing BM25 corpus indexer. The chunk's
    heading_path is prepended to the title for breadcrumb display:

        "ILO C189 > Article 9 (Domestic Workers)"

    so retrieval results read naturally without an extra UI hop."""
    out: list[tuple[str, str, str, str]] = []
    for c in chunks:
        title_parts: list[str] = []
        if c.get("parent_doc_title"):
            title_parts.append(c["parent_doc_title"])
        if c.get("heading_path"):
            title_parts.append(c["heading_path"])
        title = " > ".join(title_parts) or c.get("id", "(chunk)")
        out.append((
            c["id"],
            title,
            c.get("source", ""),
            c["text"],
        ))
    return out


def first_n_words(text: str, n: int = 8) -> str:
    """Tiny helper for breadcrumb display when the heading_path is empty —
    fall back to the chunk's first few words. Intentionally not lemma-
    aware; this is a UI hint, not retrieval signal."""
    words = re.findall(r"\S+", text or "")
    if not words:
        return ""
    return " ".join(words[:n]) + ("…" if len(words) > n else "")
