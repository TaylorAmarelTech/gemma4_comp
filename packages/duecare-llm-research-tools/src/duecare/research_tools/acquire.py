"""Acquisition pipeline orchestrator -- turns a source-candidate frontier into
retrieval-ready, deduped, PII-scrubbed, graphed passages, STAGED for review.

It NEVER auto-inserts into the live corpus (the no-silent-mutation invariant the
Research Monitor also follows): it returns staged candidate chunks + a doc graph
+ a manifest, which a separate explicit promote step reviews and inserts.

Stage chain per source:
    fetch (curl_cffi/urllib, injected)  -- the only network step
    -> extract main text (trafilatura when installed, else stdlib tag-strip)
    -> chunk (provenance-tagged passages)
    -> dedup (exact sha256 + near-dup SimHash, vs existing corpus + in-batch)
    -> PII-scrub (emails / phones / passport- / account-shaped tokens redacted)
    -> graph (doc<->doc + doc->entity edges, built once over the kept docs)

Every stage except ``fetch`` is pure, and ``fetch`` is injected, so the whole
pipeline is deterministic and testable offline with a fake fetch.
"""
from __future__ import annotations

import html as _html
import re
from typing import Callable

from pydantic import BaseModel

from .chunker import chunk_document
from .dedup import SimHashIndex, content_key, simhash64
from .docfetch import fetch_document
from .graph import build_graph
from .monitor import FetchResult
from .monitor import scrub as _scrub_contacts
from .store import AcquisitionStore

# Public pages can legitimately name public officials / orgs / public-record
# cases (rule 10 permits those); what we defensively strip even from public docs
# is *contact* PII and id-shaped tokens -- the volatile data rule 80 says must
# come from tools, never baked into knowledge. monitor.scrub handles phone/email;
# this adds passport- and financial-account-shaped tokens.
_EXTRA_PII = re.compile(
    r"\b[A-Z]{1,2}\d{6,9}\b|(?:account|acct|a/c|iban)[:#\s]*[A-Z0-9\-]{6,}", re.I)


def scrub_text(text: str) -> str:
    """Redact contact + id-shaped PII from extracted public text."""
    return _EXTRA_PII.sub("[redacted]", _scrub_contacts(text or ""))


_SCRIPT = re.compile(r"(?is)<(script|style|noscript)\b.*?</\1>")
_TAGS = re.compile(r"(?s)<[^>]+>")
_SPACES = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n\s*\n\s*\n+")


def _strip_html(raw: str) -> str:
    """Stdlib boilerplate-light fallback: drop script/style, tags->newlines,
    unescape entities, collapse whitespace. Deterministic."""
    s = _SCRIPT.sub(" ", raw or "")
    s = _TAGS.sub("\n", s)
    s = _html.unescape(s)
    s = _SPACES.sub(" ", s)
    s = _BLANKS.sub("\n\n", s)
    return "\n".join(line.strip() for line in s.splitlines()).strip()


try:  # boilerplate-stripped extraction; optional, like curl_cffi
    import trafilatura as _traf  # type: ignore
    _HAVE_TRAF = True
except Exception:  # noqa: BLE001
    _HAVE_TRAF = False


def extract_main_text(raw_html: str, url: str | None = None) -> str:
    """Main content of a fetched page. trafilatura when installed (strips nav /
    boilerplate); stdlib tag-strip fallback otherwise. Deterministic per input."""
    if _HAVE_TRAF and raw_html:
        try:
            out = _traf.extract(
                raw_html, url=url, include_comments=False,
                include_tables=True, favor_recall=True)
            if out and out.strip():
                return out.strip()
        except Exception:  # noqa: BLE001 -- fall back, never crash a run
            pass
    return _strip_html(raw_html or "")


class AcquiredChunk(BaseModel):
    id: str
    doc_id: str
    ordinal: int
    text: str
    url: str | None = None
    title: str | None = None
    source_tier: str | None = None
    jurisdictions: list[str] = []
    signals: list[str] = []
    content_key: str
    simhash: int
    n_chars: int


class AcquisitionResult(BaseModel):
    n_sources: int
    n_fetched: int
    n_unreachable: int
    n_chunks_kept: int
    n_chunks_dropped: int
    kept: list[AcquiredChunk]
    dropped: list[dict]
    unreachable: list[dict]
    graph: dict


def acquire(
    candidates: list[dict],
    *,
    fetch: Callable[[str], FetchResult] = fetch_document,
    existing_keys: set[str] | None = None,
    existing_sigs: list[int] | None = None,
    store: AcquisitionStore | None = None,
    target_chars: int = 900,
    overlap_chars: int = 150,
    max_dist: int = 3,
    min_doc_chars: int = 200,
) -> AcquisitionResult:
    """Run the full acquisition chain over ``candidates`` (dicts with at least a
    ``url``; optional ``id``/``title``/``source_tier``/``jurisdictions``/
    ``signals``). Dedups against ``existing_keys``/``existing_sigs`` (the live
    corpus) and within the batch. Returns staged chunks + doc graph + manifest;
    writes nothing (the runner persists the staging artifact)."""
    seen_keys: set[str] = set(existing_keys or set())
    sig_index = SimHashIndex(existing_sigs or [], bands=max(4, max_dist + 1))
    kept: list[AcquiredChunk] = []
    dropped: list[dict] = []
    unreachable: list[dict] = []
    doc_texts: dict[str, str] = {}   # doc_id -> text, for newly-kept docs only
    n_fetched = 0

    for c in candidates:
        url = c.get("url")
        provided = c.get("text")
        if provided is None and not url:
            continue
        if provided is not None:
            raw = provided          # API/connector source: text already supplied, skip fetch
        else:
            res = fetch(url)
            if not res.ok:
                unreachable.append({"url": url, "status": res.status, "error": res.error})
                continue
            raw = res.text
        n_fetched += 1
        text = scrub_text(extract_main_text(raw, url))
        if len(text) < min_doc_chars:
            dropped.append({"url": url, "_dup_reason": "too_short", "n_chars": len(text)})
            continue
        doc_id = c.get("id") or content_key(url)[:16]
        chunks = chunk_document(
            text, doc_id=doc_id, target_chars=target_chars, overlap_chars=overlap_chars,
            source=url, kind=c.get("source_tier"),
            jurisdiction=(c.get("jurisdictions") or [None])[0])
        kept_any = False
        for ch in chunks:
            key = content_key(ch.text)
            sig = simhash64(ch.text)
            ac = AcquiredChunk(
                id=ch.id, doc_id=ch.doc_id, ordinal=ch.ordinal, text=ch.text,
                url=url, title=c.get("title"), source_tier=c.get("source_tier"),
                jurisdictions=c.get("jurisdictions") or [], signals=c.get("signals") or [],
                content_key=key, simhash=sig, n_chars=ch.n_chars)
            if store is not None:
                # persistent, scalable dedup against the whole corpus (O(bucket))
                verdict = store.add_chunk(ac.model_dump(), max_dist=max_dist)
                if verdict != "kept":
                    dropped.append({"id": ch.id, "url": url, "_dup_reason": verdict})
                    continue
            else:
                if key in seen_keys:
                    dropped.append({"id": ch.id, "url": url, "_dup_reason": "exact"})
                    continue
                if sig_index.query_near(sig, max_dist=max_dist):  # empty index -> False
                    dropped.append({"id": ch.id, "url": url, "_dup_reason": "near"})
                    continue
                seen_keys.add(key)
                sig_index.add(sig)
            kept.append(ac)
            kept_any = True
        if kept_any:
            doc_texts[doc_id] = text

    docs_for_graph = [{"id": d, "t": t} for d, t in sorted(doc_texts.items())]
    graph = build_graph(docs_for_graph, text_of=lambda x: x["t"], id_of=lambda x: x["id"])
    return AcquisitionResult(
        n_sources=len(candidates), n_fetched=n_fetched, n_unreachable=len(unreachable),
        n_chunks_kept=len(kept), n_chunks_dropped=len(dropped),
        kept=kept, dropped=dropped, unreachable=unreachable, graph=graph)
