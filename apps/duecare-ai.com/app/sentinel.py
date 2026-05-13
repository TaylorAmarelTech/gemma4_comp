"""Hub-side Sentinel: scheduled web searches that harvest novel
information into KnowledgeObject drafts for curator review.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_PATH = DATA_DIR / "sentinel_state.json"
DRAFTS_PATH = DATA_DIR / "sentinel_drafts.jsonl"
SEEN_PATH = DATA_DIR / "sentinel_seen_urls.json"


DEFAULT_WATCH_QUERIES: list[dict[str, Any]] = [
    {"slug": "new_ilo_conventions",
     "query": "ILO new convention migrant worker recruitment 2026",
     "frequency_days": 7, "intent": "new_laws", "target_ko_type": "rag_doc"},
    {"slug": "poea_circulars",
     "query": "POEA Memorandum Circular 2026 fee cap migrant worker",
     "frequency_days": 7, "intent": "new_laws", "target_ko_type": "rag_doc"},
    {"slug": "bp2mi_regulations",
     "query": "BP2MI regulation 2026 Indonesian migrant worker protection",
     "frequency_days": 7, "intent": "new_laws", "target_ko_type": "rag_doc"},
    {"slug": "trafficking_court_cases",
     "query": "human trafficking court conviction migrant worker 2026",
     "frequency_days": 7, "intent": "case_law", "target_ko_type": "citation_edge"},
    {"slug": "recruiter_scams",
     "query": "migrant worker recruitment scam fraud 2026",
     "frequency_days": 7, "intent": "new_trends", "target_ko_type": "fact_template"},
    {"slug": "passport_retention_news",
     "query": "passport retention domestic worker abuse Saudi Arabia 2026",
     "frequency_days": 7, "intent": "negative_news", "target_ko_type": "fact_template"},
    {"slug": "fee_bondage_news",
     "query": "fee bondage placement fee migrant worker 2026",
     "frequency_days": 7, "intent": "negative_news", "target_ko_type": "fact_template"},
    {"slug": "ngo_advisories",
     "query": "Polaris IJM ECPAT Mission for Migrant Workers advisory 2026",
     "frequency_days": 14, "intent": "ngo_updates", "target_ko_type": "ngo_directory"},
    {"slug": "kafala_reforms",
     "query": "kafala system reform Gulf migrant worker 2026",
     "frequency_days": 14, "intent": "new_laws", "target_ko_type": "rag_doc"},
    {"slug": "fishing_industry_abuses",
     "query": "fishing vessel migrant worker forced labour 2026",
     "frequency_days": 14, "intent": "negative_news", "target_ko_type": "fact_template"},
]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_queries() -> list[dict[str, Any]]:
    persisted = _load_json(DATA_DIR / "sentinel_queries.json", default=[])
    seen = {q["slug"] for q in persisted}
    out = list(persisted)
    for q in DEFAULT_WATCH_QUERIES:
        if q["slug"] not in seen:
            out.append(q)
    return out


def get_query(slug: str) -> Optional[dict[str, Any]]:
    for q in list_queries():
        if q["slug"] == slug:
            return q
    return None


def get_state() -> dict[str, Any]:
    return _load_json(STATE_PATH, default={})


def _update_state(slug: str, **fields: Any) -> None:
    state = get_state()
    entry = state.get(slug, {"n_runs": 0, "n_drafts_queued": 0, "n_drafts_accepted": 0})
    entry.update(fields)
    state[slug] = entry
    _save_json(STATE_PATH, state)


def _seen_urls(slug: str) -> set[str]:
    seen = _load_json(SEEN_PATH, default={})
    return set(seen.get(slug, []))


def _mark_seen(slug: str, urls: list[str], cap: int = 5000) -> None:
    seen = _load_json(SEEN_PATH, default={})
    existing = list(dict.fromkeys((seen.get(slug, []) or []) + urls))
    if len(existing) > cap:
        existing = existing[-cap:]
    seen[slug] = existing
    _save_json(SEEN_PATH, seen)


def _searxng_url() -> str:
    return (os.environ.get("DUECARE_SEARXNG_URL", "") or "").rstrip("/")


def _searxng_search(query: str, top_n: int = 10) -> dict[str, Any]:
    url = _searxng_url()
    if not url:
        return {"results": [], "error": "DUECARE_SEARXNG_URL not configured"}
    import urllib.parse as _parse
    endpoint = f"{url}/search?format=json&q={_parse.quote_plus(query)}"
    t0 = time.time()
    try:
        try:
            import httpx
            with httpx.Client(timeout=8.0, follow_redirects=True) as cli:
                r = cli.get(endpoint, headers={"Accept": "application/json"})
                r.raise_for_status()
                body = r.json()
        except ImportError:
            import urllib.request as _req
            with _req.urlopen(endpoint, timeout=8.0) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return {"results": [], "error": f"{type(exc).__name__}: {exc}"}
    results = []
    for r in (body.get("results") or [])[:top_n]:
        results.append({
            "title": (r.get("title") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "snippet": ((r.get("content") or r.get("snippet") or "")[:600]).strip(),
        })
    return {"results": results, "source": "searxng",
            "elapsed_ms": int((time.time() - t0) * 1000)}


def _deterministic_envelope(result: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    ts = _utc_iso()
    slug_base = query["slug"]
    src = result.get("url") or result.get("title") or "unknown"
    src_hash = hashlib.sha256(src.encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": "1.0",
        "knowledge_object_type": query["target_ko_type"],
        "id": f"sentinel-{slug_base}-{src_hash}",
        "version": "v1-sentinel-draft",
        "provenance": {
            "created_at": ts,
            "created_by": "sentinel:server-automated",
            "watch_query_slug": query["slug"],
            "watch_query": query["query"],
            "intent": query["intent"],
            "source_url": result.get("url"),
            "source_title": result.get("title"),
        },
        "content": {
            "title": result.get("title"),
            "url": result.get("url"),
            "snippet": result.get("snippet"),
        },
        "tags": [f"sentinel:{query['intent']}", "branch:grounding_knowledge"],
        "extensions": {"draft": True, "needs_review": True,
                        "sentinel_run": True, "ollama_synthesized": False},
    }


def _ollama_synthesize(result: dict[str, Any], query: dict[str, Any]) -> Optional[dict[str, Any]]:
    base = os.environ.get("OLLAMA_BASE_URL", "").strip()
    model = os.environ.get("OLLAMA_MODEL", "gemma2:9b").strip()
    if not base:
        return None
    prompt = (
        f"You are DueCare's sentinel analyst. The following search result was "
        f"surfaced for the watch query: '{query['query']}'. Synthesize a brief "
        f"factual summary (2-3 sentences) appropriate for a "
        f"'{query['target_ko_type']}' KnowledgeObject. Only output the summary "
        f"itself; no preamble.\n\n"
        f"Title: {result.get('title', '')}\n"
        f"URL: {result.get('url', '')}\n"
        f"Snippet: {result.get('snippet', '')}"
    )
    try:
        import urllib.request as _req
        endpoint = base.rstrip("/") + "/api/generate"
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = _req.Request(endpoint, data=payload,
                            headers={"Content-Type": "application/json"}, method="POST")
        with _req.urlopen(req, timeout=20.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        synthesized = (data.get("response") or "").strip()
    except Exception:
        return None
    env = _deterministic_envelope(result, query)
    env["content"]["sentinel_summary"] = synthesized[:1500]
    env["extensions"]["ollama_synthesized"] = True
    env["extensions"]["ollama_model"] = model
    return env


def run_query(slug: str, *, top_n: int = 10) -> dict[str, Any]:
    q = get_query(slug)
    if not q:
        return {"ok": False, "error": f"unknown watch query: {slug}"}

    search_out = _searxng_search(q["query"], top_n=top_n)
    if "error" in search_out and not search_out.get("results"):
        _update_state(slug, last_run=_utc_iso(), last_error=search_out["error"])
        return {"ok": False, "slug": slug, "error": search_out["error"]}

    seen = _seen_urls(slug)
    novel: list[dict[str, Any]] = []
    new_urls: list[str] = []
    for r in search_out.get("results", []):
        url = r.get("url", "")
        if not url or url in seen:
            continue
        novel.append(r)
        new_urls.append(url)

    drafts: list[dict[str, Any]] = []
    for r in novel:
        env = _ollama_synthesize(r, q) or _deterministic_envelope(r, q)
        row = {
            "ts": _utc_iso(),
            "slug": slug,
            "watch_query": q["query"],
            "intent": q["intent"],
            "source_url": r.get("url"),
            "source_title": r.get("title"),
            "source_sha256": hashlib.sha256(
                (r.get("url", "") + "\n" + r.get("title", "")).encode("utf-8")
            ).hexdigest()[:16],
            "novel": True,
            "suggested_ko_type": q["target_ko_type"],
            "draft_envelope": env,
        }
        drafts.append(row)
        try:
            with open(DRAFTS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    if new_urls:
        _mark_seen(slug, new_urls)

    curator_submission_id = _emit_to_curator_queue(slug, drafts) if drafts else None

    state = get_state().get(slug, {})
    n_runs = int(state.get("n_runs", 0)) + 1
    n_drafts_queued = int(state.get("n_drafts_queued", 0)) + len(drafts)
    _update_state(slug, last_run=_utc_iso(), n_runs=n_runs,
                   n_drafts_queued=n_drafts_queued,
                   last_n_results=len(search_out.get("results", [])),
                   last_n_novel=len(novel), last_error=None)

    return {
        "ok": True, "slug": slug, "watch_query": q["query"],
        "source": search_out.get("source"),
        "n_results": len(search_out.get("results", [])),
        "n_novel": len(novel), "n_drafts_queued": len(drafts),
        "elapsed_ms": search_out.get("elapsed_ms"),
        "ollama_used": any(
            d["draft_envelope"]["extensions"].get("ollama_synthesized") for d in drafts
        ),
        "curator_submission_id": curator_submission_id,
    }


def run_due(now_iso: Optional[str] = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc) if now_iso is None else datetime.strptime(
        now_iso, "%Y-%m-%dT%H-%M-%SZ"
    ).replace(tzinfo=timezone.utc)
    state = get_state()
    reports = []
    skipped = []
    for q in list_queries():
        slug = q["slug"]
        last = state.get(slug, {}).get("last_run")
        due = True
        if last:
            try:
                last_dt = datetime.strptime(last, "%Y-%m-%dT%H-%M-%SZ").replace(tzinfo=timezone.utc)
                age_days = (now - last_dt).total_seconds() / 86400.0
                due = age_days >= float(q.get("frequency_days", 7))
            except Exception:
                due = True
        if due:
            reports.append(run_query(slug))
        else:
            skipped.append({"slug": slug, "last_run": last})
    return {"ok": True, "n_run": len(reports), "n_skipped": len(skipped),
             "reports": reports, "skipped": skipped}


def recent_drafts(limit: int = 50) -> list[dict[str, Any]]:
    if not DRAFTS_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with open(DRAFTS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []
    return list(reversed(rows))[:limit]


SUBMISSIONS_PATH = DATA_DIR / "knowledge_submissions.jsonl"


def _emit_to_curator_queue(slug: str, drafts: list[dict[str, Any]]) -> Optional[str]:
    """Append one curator-queue-compatible submission per Sentinel run.

    Bridges Sentinel into the existing /api/curator/queue surface so
    harvested drafts show up alongside human submissions. Returns the
    submission_id on success, None on failure (never raises).
    """
    if not drafts:
        return None
    try:
        ts = _utc_iso()
        submission_id = f"sentinel_{slug}_{ts}"
        accepted = []
        for d in drafts:
            env = d.get("draft_envelope") or {}
            content_blob = json.dumps(env.get("content", {}), sort_keys=True,
                                       ensure_ascii=False).encode("utf-8")
            accepted.append({
                "type": env.get("knowledge_object_type"),
                "id": env.get("id"),
                "content_sha256": hashlib.sha256(content_blob).hexdigest()[:16],
                "source_url": d.get("source_url"),
                "source_title": d.get("source_title"),
                "watch_query": d.get("watch_query"),
                "intent": d.get("intent"),
                "ko_envelope": env,
            })
        row = {
            "submission_id": submission_id,
            "ts": ts,
            "source": "sentinel:server-automated",
            "watch_slug": slug,
            "n_items": len(accepted),
            "accepted": accepted,
        }
        with open(SUBMISSIONS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return submission_id
    except Exception:
        return None


def status_summary() -> dict[str, Any]:
    queries = list_queries()
    state = get_state()
    out_q = []
    for q in queries:
        s = state.get(q["slug"], {})
        out_q.append({**q,
                       "last_run": s.get("last_run"),
                       "n_runs": s.get("n_runs", 0),
                       "n_drafts_queued": s.get("n_drafts_queued", 0),
                       "n_drafts_accepted": s.get("n_drafts_accepted", 0),
                       "last_error": s.get("last_error")})
    return {
        "n_queries": len(queries),
        "searxng_configured": bool(_searxng_url()),
        "ollama_configured": bool(os.environ.get("OLLAMA_BASE_URL", "").strip()),
        "queries": out_q,
        "n_drafts_total": sum(q.get("n_drafts_queued", 0) for q in out_q),
    }
