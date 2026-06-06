"""Tests for the deterministic document chunker (acquisition pipeline)."""
from __future__ import annotations

from duecare.research_tools.chunker import Chunk, chunk_document

# Synthetic public-law-style text (no real PII), multiple paragraphs.
DOC = (
    "Article 1. Recruitment fees may not be charged to the worker. The employer "
    "or principal bears all costs of recruitment and deployment.\n\n"
    "Article 2. Passport retention is prohibited. The worker keeps custody of all "
    "identity and travel documents at all times during employment.\n\n"
    "Article 3. Wages must be paid monthly in full, without unauthorized "
    "deduction. Any deduction requires written consent and a lawful basis.\n\n"
    "Article 4. A worker may terminate employment and return home; the employer "
    "may not withhold wages or documents to prevent departure."
)


def test_empty_returns_nothing():
    assert chunk_document("", doc_id="d1") == []
    assert chunk_document("   \n\n  ", doc_id="d1") == []


def test_basic_chunking_ids_and_models():
    chunks = chunk_document(DOC, doc_id="law_demo", target_chars=200, overlap_chars=40)
    assert len(chunks) >= 2
    assert all(isinstance(c, Chunk) for c in chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert [c.id for c in chunks] == [f"law_demo#c{i:03d}" for i in range(len(chunks))]


def test_deterministic():
    a = chunk_document(DOC, doc_id="d", target_chars=200, overlap_chars=40)
    b = chunk_document(DOC, doc_id="d", target_chars=200, overlap_chars=40)
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


def test_offsets_traceable_to_source():
    chunks = chunk_document(DOC, doc_id="d", target_chars=200, overlap_chars=0)
    for c in chunks:
        assert 0 <= c.char_start < c.char_end <= len(DOC)
        span = DOC[c.char_start:c.char_end]
        first_word = c.text.split()[0]
        assert first_word in span  # core span in source contains the chunk's lead word


def test_overlap_prepended_for_later_chunks():
    chunks = chunk_document(DOC, doc_id="d", target_chars=160, overlap_chars=50)
    assert len(chunks) >= 2
    assert "…" not in chunks[0].text                      # first chunk: no overlap join
    assert any("…" in c.text for c in chunks[1:])          # later chunks carry overlap


def test_respects_target_size_roughly():
    chunks = chunk_document(DOC, doc_id="d", target_chars=180, overlap_chars=0)
    assert all(c.n_chars <= 180 * 1.6 for c in chunks)     # slack for boundaries


def test_long_paragraph_is_sentence_split():
    long_para = " ".join(f"Sentence number {i} states a distinct rule." for i in range(40))
    chunks = chunk_document(long_para, doc_id="d", target_chars=200, overlap_chars=0)
    assert len(chunks) >= 3                                 # one giant paragraph -> several chunks


def test_metadata_propagates():
    chunks = chunk_document(DOC, doc_id="d", target_chars=200,
                            source="https://example.org/law", kind="law", jurisdiction="PH")
    assert chunks[0].source == "https://example.org/law"
    assert chunks[0].kind == "law" and chunks[0].jurisdiction == "PH"
