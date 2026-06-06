"""Live acquisition runner -- fetch a source-candidate frontier through the
acquisition pipeline and STAGE retrieval-ready chunks + a doc graph + a manifest
for review.

Propose-only: writes only under ``reports/acquisition/`` (gitignored); it NEVER
touches the live RAG corpus (a separate, explicit promote step does that after a
human/curator review of the staged batch).

Resumable: a candidate whose URL is already a corpus source, already staged, or
already recorded in ``done_urls.json`` is skipped, so the run can be killed and
restarted (it is designed to run for a long time over a large frontier).

Env knobs:
  ACQ_CANDIDATES  candidates .jsonl (default: research_spider/source_candidates.jsonl)
  ACQ_OUT         staging dir       (default: reports/acquisition)
  ACQ_LIMIT       max NEW candidates this run (default 0 = all)
  ACQ_BATCH       candidates per pipeline call / progress tick (default 20)
  ACQ_TIMEOUT     per-fetch timeout seconds (default 25)
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.acquire import acquire  # noqa: E402
from duecare.research_tools.dedup import content_key, simhash64  # noqa: E402
from duecare.research_tools.docfetch import fetch_document  # noqa: E402
from duecare.research_tools.graph import build_graph  # noqa: E402
from duecare.research_tools.monitor import default_fetch  # noqa: E402
from duecare.research_tools.politeness import PoliteFetcher, RateLimiter, RobotsCache  # noqa: E402
from duecare.research_tools.store import AcquisitionStore  # noqa: E402

CAND = Path(os.environ.get(
    "ACQ_CANDIDATES",
    ROOT / "configs/duecare/benchmarks/research_spider/source_candidates.jsonl"))
OUT = Path(os.environ.get("ACQ_OUT", ROOT / "reports/acquisition"))
LIMIT = int(os.environ.get("ACQ_LIMIT", "0"))
BATCH = int(os.environ.get("ACQ_BATCH", "20"))
TIMEOUT = float(os.environ.get("ACQ_TIMEOUT", "25"))
MIN_INTERVAL = float(os.environ.get("ACQ_MIN_INTERVAL", "1.0"))  # per-host seconds
RESPECT_ROBOTS = os.environ.get("ACQ_RESPECT_ROBOTS", "1") not in ("0", "false", "")
FRONTIER_DB = os.environ.get("ACQ_FRONTIER_DB", "")          # drain harvested frontier if set
FRONTIER_LIMIT = int(os.environ.get("ACQ_FRONTIER_LIMIT", "0"))  # cap pending pulled per run


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def main() -> None:
    _utf8()
    OUT.mkdir(parents=True, exist_ok=True)
    # Candidates come from the harvested frontier db (drain pending) or a jsonl.
    fstore = AcquisitionStore(FRONTIER_DB) if FRONTIER_DB else None
    if fstore is not None:
        cands = [dict(c) for c in fstore.iter_frontier(status="pending", limit=FRONTIER_LIMIT or None)]
        print(f"[acquire] draining frontier {FRONTIER_DB}: {len(cands)} pending", flush=True)
    else:
        cands = load_jsonl(CAND)

    # Dedup baseline from the live corpus (URL + exact-text + near-dup signals).
    # Persistent store = dedup index + crawl ledger + corpus (system of record).
    store = AcquisitionStore(OUT / "corpus.db", bands=4)
    if not store.baseline_seeded():
        from duecare.chat.harness import RAG_CORPUS  # noqa: E402
        store.seed_baseline(
            (content_key(b) for (*_h, b) in RAG_CORPUS),
            (simhash64(b) for (*_h, b) in RAG_CORPUS))
        for (_id, _t, s, _b) in RAG_CORPUS:
            if s:
                store.mark_url(str(s), status="corpus")
        store.commit()
        print(f"[acquire] seeded dedup baseline from {len(RAG_CORPUS)} corpus docs", flush=True)

    staged_path = OUT / "staged_chunks.jsonl"
    if store.count() == 0 and staged_path.exists():
        # One-time reconcile: fold prior JSONL staging into a fresh store so
        # dedup + the crawl ledger cover earlier runs (no re-fetch, no rewrite).
        migrated = 0
        for row in load_jsonl(staged_path):
            if store.add_chunk(row) == "kept":
                migrated += 1
            if row.get("url"):
                store.mark_url(row["url"], status="fetched")
        store.commit()
        print(f"[acquire] reconciled {migrated} prior staged chunks into the store", flush=True)

    todo = [c for c in cands if c.get("url") and not store.url_done(c["url"])]
    if LIMIT:
        todo = todo[:LIMIT]
    st0 = store.stats()
    print(f"[acquire] candidates={len(cands)} todo={len(todo)} "
          f"store_chunks={st0['chunks']} processed_urls={st0['urls']}", flush=True)
    if not todo:
        print("[acquire] nothing to do (all candidates already processed).", flush=True)
        store.close()
        if fstore is not None:
            fstore.close()
        return

    # Polite fetch: per-host robots Disallow + rate limit, wrapping the
    # PDF-aware document fetch. Good citizenship + avoids being blocked at scale.
    robots = RobotsCache(
        lambda u: (default_fetch(u, timeout=10).text or "")) if RESPECT_ROBOTS else None
    limiter = RateLimiter(MIN_INTERVAL) if MIN_INTERVAL > 0 else None
    fetch = PoliteFetcher(
        lambda url: fetch_document(url, timeout=TIMEOUT), robots=robots, limiter=limiter)
    print(f"[acquire] politeness: robots={'on' if robots else 'off'} "
          f"min_interval={MIN_INTERVAL}s/host", flush=True)

    tot_kept = tot_drop = tot_unreach = 0
    t0 = time.time()
    n_batches = (len(todo) + BATCH - 1) // BATCH
    with open(staged_path, "a", encoding="utf-8") as sf, \
            open(OUT / "unreachable.jsonl", "a", encoding="utf-8") as uf, \
            open(OUT / "dropped.jsonl", "a", encoding="utf-8") as df:
        for bi in range(n_batches):
            batch = todo[bi * BATCH:(bi + 1) * BATCH]
            r = acquire(batch, fetch=fetch, store=store)  # store-backed scalable dedup
            for ch in r.kept:
                sf.write(json.dumps(ch.model_dump(), ensure_ascii=False) + "\n")
            for d in r.dropped:
                df.write(json.dumps(d, ensure_ascii=False) + "\n")
            for u in r.unreachable:
                uf.write(json.dumps(u, ensure_ascii=False) + "\n")
            if r.graph.get("edges"):
                store.add_edges(r.graph["edges"])
            sf.flush(); uf.flush(); df.flush()
            unreached = {u.get("url") for u in r.unreachable}
            for c in batch:
                store.mark_url(c["url"],
                               status=("unreachable" if c["url"] in unreached else "fetched"))
            store.commit()
            if fstore is not None:
                for c in batch:
                    fstore.mark_frontier(c["url"], "acquired")
                fstore.commit()
            tot_kept += r.n_chunks_kept
            tot_drop += r.n_chunks_dropped
            tot_unreach += r.n_unreachable
            print(f"[acquire] batch {bi + 1}/{n_batches} "
                  f"done={min((bi + 1) * BATCH, len(todo))}/{len(todo)} "
                  f"kept={tot_kept} dropped={tot_drop} unreach={tot_unreach} "
                  f"store_chunks={store.count()} elapsed={time.time() - t0:.0f}s", flush=True)

    # Combined doc graph over everything staged so far (chunks -> doc text).
    docs: dict[str, list[str]] = {}
    for row in load_jsonl(staged_path):
        docs.setdefault(row["doc_id"], []).append(row.get("text", ""))
    doc_list = [{"id": d, "t": "\n".join(parts)} for d, parts in sorted(docs.items())]
    g = build_graph(doc_list, text_of=lambda x: x["t"], id_of=lambda x: x["id"])
    (OUT / "graph.json").write_text(json.dumps(g), encoding="utf-8")

    manifest = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "candidates_file": str(CAND),
        "n_candidates": len(cands), "n_todo": len(todo),
        "chunks_kept_this_run": tot_kept, "chunks_dropped_this_run": tot_drop,
        "unreachable_this_run": tot_unreach,
        "store": store.stats(),
        "staged_total_docs": len(docs),
        "graph_nodes": len(g["nodes"]), "graph_edges": len(g["edges"]),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    store.close()
    if fstore is not None:
        fstore.close()
    print("[acquire] DONE " + json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
