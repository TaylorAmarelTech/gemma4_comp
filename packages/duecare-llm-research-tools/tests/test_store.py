"""Tests for the persistent SQLite acquisition store."""
from __future__ import annotations

from duecare.research_tools.store import AcquisitionStore


def _chunk(cid, key, sig, *, doc="d1", text="a public-law passage about recruitment fees", **kw):
    base = {"id": cid, "doc_id": doc, "ordinal": 0, "url": "https://e.org/x",
            "title": "T", "text": text, "content_key": key, "simhash": sig, "n_chars": len(text)}
    base.update(kw)
    return base


def test_exact_dedup():
    with AcquisitionStore(":memory:") as s:
        assert s.add_chunk(_chunk("c1", "K1", 100)) == "kept"
        assert s.add_chunk(_chunk("c2", "K1", 999)) == "exact"   # same content_key
        assert s.count() == 1


def test_near_dedup_via_band_index():
    with AcquisitionStore(":memory:", bands=4) as s:
        base = 0x0123456789ABCDEF
        assert s.add_chunk(_chunk("c1", "K1", base)) == "kept"
        assert s.add_chunk(_chunk("c2", "K2", base ^ 0b11)) == "near"   # 2 bits -> near
        far = base ^ 0xF0F0F0F0F                                        # far
        assert s.add_chunk(_chunk("c3", "K3", far)) == "kept"
        assert s.count() == 2


def test_url_ledger():
    with AcquisitionStore(":memory:") as s:
        assert not s.url_done("https://e.org/a")
        s.mark_url("https://e.org/a", status="fetched", status_code=200)
        assert s.url_done("https://e.org/a")


def test_persistence_across_reopen(tmp_path):
    db = tmp_path / "acq.db"
    with AcquisitionStore(db) as s:
        s.add_chunk(_chunk("c1", "K1", 0xABCDEF123456))
        s.commit()
    # reopen: chunk + band index persist, so dedup still fires without a rescan
    with AcquisitionStore(db) as s2:
        assert s2.count() == 1
        assert s2.has_content_key("K1")
        assert s2.is_near_dup(0xABCDEF123456 ^ 0b1, max_dist=3) is True
        assert s2.add_chunk(_chunk("c2", "K1", 0xABCDEF123456)) == "exact"


def test_fts_search():
    with AcquisitionStore(":memory:") as s:
        if not s.has_fts:
            return  # FTS5 not compiled -> search degrades to []
        s.add_chunk(_chunk("c1", "K1", 100, text="C189 domestic worker passport retention on PH-HK"))
        s.add_chunk(_chunk("c2", "K2", 200, text="carbon border adjustment certificate scheme"))
        hits = s.search("passport")
        assert any(h["chunk_id"] == "c1" for h in hits)
        assert not any(h["chunk_id"] == "c2" for h in hits)


def test_seed_baseline_dedups_against_corpus():
    with AcquisitionStore(":memory:", bands=4) as s:
        # seed as if from the live corpus (keys + simhashes), no chunk rows added
        s.seed_baseline(["CORP1"], [0xDEADBEEF12345])
        assert s.count() == 0 and s.baseline_seeded()
        assert s.add_chunk(_chunk("c1", "CORP1", 111)) == "exact"          # exact vs corpus key
        assert s.add_chunk(_chunk("c2", "K2", 0xDEADBEEF12345 ^ 0b1)) == "near"  # near vs corpus sig
        assert s.add_chunk(_chunk("c3", "K3", 0x1)) == "kept"              # distinct


def test_edges_and_stats():
    with AcquisitionStore(":memory:") as s:
        s.add_chunk(_chunk("c1", "K1", 100))
        s.add_edges([{"source": "d1", "target": "ilo_c189", "relation": "mentions", "weight": 1}])
        st = s.stats()
        assert st["chunks"] == 1 and st["edges"] == 1 and st["docs"] == 1


def test_frontier_queue():
    with AcquisitionStore(":memory:") as s:
        added = s.add_frontier_bulk([
            {"url": "https://e.org/a", "host": "e.org", "source_tier": "gov"},
            {"url": "https://e.org/b", "host": "e.org"},
            {"url": "https://e.org/a"},  # dup -> ignored
        ])
        assert added == 2 and s.frontier_count() == 2
        assert s.frontier_count(status="pending") == 2
        pend = list(s.iter_frontier(status="pending"))
        assert {p["url"] for p in pend} == {"https://e.org/a", "https://e.org/b"}
        s.mark_frontier("https://e.org/a", "acquired")
        assert s.frontier_count(status="pending") == 1
        assert s.add_frontier("https://e.org/b") is False  # already present


def test_sitemap_ledger():
    with AcquisitionStore(":memory:") as s:
        assert not s.sitemap_seen("https://e.org/sitemap.xml")
        s.mark_sitemap("https://e.org/sitemap.xml")
        assert s.sitemap_seen("https://e.org/sitemap.xml")


def test_frontier_diverse_ordering():
    with AcquisitionStore(":memory:") as s:
        s.add_frontier_bulk([
            {"url": "https://a.org/1", "host": "a.org"},
            {"url": "https://a.org/2", "host": "a.org"},
            {"url": "https://a.org/3", "host": "a.org"},
            {"url": "https://b.org/1", "host": "b.org"}])
        diverse = [r["url"] for r in s.iter_frontier(diverse=True)]
        # round-robin: b.org's single URL surfaces early, not after all of a.org
        assert diverse.index("https://b.org/1") < diverse.index("https://a.org/2")
        rowid = [r["url"] for r in s.iter_frontier()]
        assert rowid[-1] == "https://b.org/1"        # insertion order buries it last
