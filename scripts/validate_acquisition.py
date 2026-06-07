"""Validate that acquired docs are GENUINELY HELPFUL, not just keyword-relevant.

Two layers here (lift validation is a separate, heavier script):

  keyword/retrieval (always, deterministic, offline): runs the REAL kernel BM25
  (`_rag_call`) with the acquired docs as ``extra_docs`` over real trafficking
  queries, and measures how often an acquired doc makes top-k / OUTRANKS the
  existing corpus, plus what fraction of the added set is ever surfaced (a doc
  never retrieved for any real query is relevant-but-not-helpful).

  semantic (if an embedder is installed): cosine similarity of each query to its
  nearest acquired doc -- catches docs relevant in MEANING but using different
  vocabulary than the keyword lexicon. ``pip install fastembed`` enables it.

Writes reports/acquisition/validation_report.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.validate import (  # noqa: E402
    cosine, query_lift, query_utility, summarize_lift, summarize_retrieval,
    summarize_semantic,
)

OUT = Path(os.environ.get("ACQ_OUT", ROOT / "reports/acquisition"))
PROMPTS = Path(os.environ.get(
    "VALIDATE_PROMPTS", ROOT / "configs/duecare/benchmarks/harness_lift_prompts_100.json"))
K = int(os.environ.get("VALIDATE_K", "8"))
MAX_DOCS = int(os.environ.get("VALIDATE_MAX_DOCS", "0"))     # 0 = all promoted
MAX_QUERIES = int(os.environ.get("VALIDATE_MAX_QUERIES", "0"))


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_queries() -> list[str]:
    raw = json.loads(PROMPTS.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else None
    if items is None and isinstance(raw, dict):
        for v in raw.values():                # first list value = the prompts
            if isinstance(v, list) and v:
                items = v
                break
    qs: list[str] = []
    for it in (items or []):
        if isinstance(it, str):
            qs.append(it)
        elif isinstance(it, dict):
            q = it.get("prompt") or it.get("text") or it.get("question") or it.get("input")
            if q:
                qs.append(str(q))
    if MAX_QUERIES:
        qs = qs[:MAX_QUERIES]
    return qs


def load_acquired() -> list[dict]:
    docs: list[dict] = []
    p = OUT / "knowledge_envelopes.jsonl"
    if not p.exists():
        return docs
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        e = json.loads(ln)
        if e.get("knowledge_object_type") != "rag_doc":
            continue
        c = e.get("content", {})
        docs.append({"id": e["id"], "title": c.get("title", ""),
                     "source": c.get("source_url", ""), "snippet": c.get("text", "")})
        if MAX_DOCS and len(docs) >= MAX_DOCS:
            break
    return docs


def retrieval_and_lift(queries: list[str], acquired: list[dict]) -> tuple[dict, dict]:
    """One pass over the REAL kernel BM25: baseline (corpus only) vs enriched
    (corpus + acquired). Derives keyword utility (from enriched) AND grounding
    lift (baseline vs enriched)."""
    from duecare.chat.harness import _rag_call  # noqa: E402 -- real kernel retrieval
    util_per, lift_per = [], []
    for q in queries:
        base = _rag_call(q, top_k=K).get("docs", [])
        enr = _rag_call(q, top_k=K, extra_docs=acquired).get("docs", [])
        util_per.append(query_utility(enr, k=K))
        lift_per.append(query_lift(base, enr))
    return summarize_retrieval(util_per, n_acquired=len(acquired)), summarize_lift(lift_per)


def get_embedder():
    try:
        from fastembed import TextEmbedding  # type: ignore
        model = TextEmbedding()

        def embed(texts):
            return [list(map(float, v)) for v in model.embed(list(texts))]
        return embed, "fastembed"
    except Exception:
        return None, None


def semantic_validation(queries: list[str], acquired: list[dict], embed) -> dict:
    doc_vecs = embed([(d["snippet"] or d["title"]) for d in acquired])
    q_vecs = embed(queries)
    best = [max((cosine(qv, dv) for dv in doc_vecs), default=0.0) for qv in q_vecs]
    return summarize_semantic(best)


def main() -> None:
    _utf8()
    queries = load_queries()
    acquired = load_acquired()
    print(f"[validate] queries={len(queries)} acquired_docs={len(acquired)} k={K}", flush=True)
    if not queries or not acquired:
        print("[validate] missing queries or acquired docs -- run promote first.", flush=True)
        return

    report: dict = {"queries": len(queries), "acquired_docs": len(acquired), "k": K}
    t0 = time.time()
    report["keyword"], report["lift"] = retrieval_and_lift(queries, acquired)
    print("[validate] keyword: " + json.dumps(report["keyword"]), flush=True)
    print("[validate] lift:    " + json.dumps(report["lift"]), flush=True)

    embed, backend = get_embedder()
    if embed and os.environ.get("VALIDATE_SEMANTIC", "1") not in ("0", "false", ""):
        try:
            sem = semantic_validation(queries, acquired, embed)
            sem["backend"] = backend
            report["semantic"] = sem
            print("[validate] semantic: " + json.dumps(sem), flush=True)
        except Exception as e:  # noqa: BLE001
            report["semantic"] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    else:
        report["semantic"] = {"skipped": "no embedder (pip install fastembed to enable semantic)"}

    report["elapsed_s"] = round(time.time() - t0, 1)
    (OUT / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[validate] DONE " + json.dumps({k: v for k, v in report.items() if k != "keyword"}),
          flush=True)


if __name__ == "__main__":
    main()
