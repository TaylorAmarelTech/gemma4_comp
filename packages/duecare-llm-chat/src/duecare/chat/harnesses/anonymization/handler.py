"""Anonymization & Sharing harness handler.

Owns:
  - POST /api/anonymize -- batch redact PII in text array
  - POST /api/submit/knowledge -- audit + HTTPS POST to the public hub
  - POST /api/submit/local -- deprecated alias for submit/knowledge
"""
from __future__ import annotations

import hashlib
import json as _json
import threading as _threading
from datetime import UTC as _UTC, datetime as _dt
from pathlib import Path as _Path
from typing import Any
from uuid import uuid4 as _uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..._model_output import sanitize_model_output
from .._replay import demo_replay, sha256_json
from .._safe_text import fact_excerpt as _fact_excerpt
from .detector import PII_PATTERNS
from .redactor import DEFAULT_SALT, placeholder, raw_sha256


_DEFAULT_HUB_SUBMIT_URL = "https://duecare-ai.com/api/submit/knowledge"


def _audit_dir() -> _Path:
    audit_dir = _Path("/kaggle/working/audit")
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        return audit_dir
    except Exception:
        pass
    fallback = _Path(".") / ".duecare-audit"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# Hub allowlist: prevents the submit endpoint from being used as an
# SSRF vector. The Kaggle tunnel is unauthenticated, so any visitor
# could otherwise POST {"target_url": "http://169.254.169.254/..."}
# and have the kernel make an outbound request to internal metadata
# endpoints or any host reachable from the runtime.
# _HUB_ALLOWLIST_HOSTS is the built-in baseline; the LIVE check goes
# through duecare.chat.federation (same registry as /api/knowledge/sync
# and /api/network/peers), which adds DUECARE_PEERS entries on top.
_HUB_ALLOWLIST_HOSTS = frozenset({
    "gemma4-comp.onrender.com",
    "duecare-ai.com",
    "www.duecare-ai.com",
})


def _is_hub_url_allowed(target_url: str) -> tuple[bool, str]:
    """Validate that ``target_url`` is one of the approved DueCare
    submit endpoints. Returns (ok, reason). Blocks:
      * non-https schemes (including file://, ftp://, javascript:, etc.)
      * any host outside the federation peer registry (which always
        includes _HUB_ALLOWLIST_HOSTS, plus DUECARE_PEERS additions)
      * userinfo (e.g., https://attacker.example.com@allowed.com)
    """
    try:
        from ...federation import is_peer_url_allowed
        return is_peer_url_allowed(target_url)
    except Exception:
        pass
    # Fallback to the built-in baseline if the federation module is
    # unavailable (older partial installs); never fail open.
    if not target_url:
        return False, "empty target_url"
    try:
        from urllib.parse import urlparse as _urlparse
        parsed = _urlparse(target_url)
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"
    if parsed.scheme != "https":
        return False, f"scheme {parsed.scheme!r} not allowed (must be https)"
    if parsed.username or parsed.password:
        return False, "userinfo not allowed in target_url"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "missing host"
    if host not in _HUB_ALLOWLIST_HOSTS:
        return False, (
            f"host {host!r} not on allowlist "
            f"{sorted(_HUB_ALLOWLIST_HOSTS)}"
        )
    return True, ""


def _post_payload(target_url: str, payload: dict, sha: str) -> tuple[int | None, str | None, str | None, bool]:
    from ...knowledge_taxonomy import node_id as _node_id
    headers = {
        "Content-Type": "application/json",
        "X-DueCare-Source": _node_id(),
        "X-DueCare-SHA256": sha,
    }
    # SSRF gate -- refuse out-of-allowlist URLs before opening a socket.
    # The Kaggle tunnel has no auth so this prevents a curious visitor
    # from turning /api/submit/knowledge into an arbitrary HTTP egress.
    ok, reason = _is_hub_url_allowed(target_url)
    if not ok:
        return None, None, f"target_url rejected: {reason}", False
    try:
        try:
            import httpx as _httpx
            # follow_redirects disabled so an allowed host cannot
            # bounce the request to an unlisted host via 30x.
            with _httpx.Client(timeout=10.0, follow_redirects=False) as cli:
                r = cli.post(target_url, json=payload, headers=headers)
            status = int(r.status_code)
            response = (r.text[:2000] if r.text else None)
            return status, response, None, 200 <= status < 300
        except ImportError:
            import urllib.request as _req
            import urllib.error as _err
            req = _req.Request(
                target_url,
                data=_json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with _req.urlopen(req, timeout=10.0) as resp:
                    status = int(resp.getcode())
                    response = resp.read(2000).decode("utf-8", errors="replace")
                    return status, response, None, 200 <= status < 300
            except _err.HTTPError as he:
                status = int(he.code)
                try:
                    response = he.read(2000).decode("utf-8", errors="replace")
                except Exception:
                    response = None
                return status, response, None, False
            except _err.URLError as ue:
                return None, None, f"URLError: {ue.reason}", False
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}", False


def _gemma_anonymization_review(app: Any, redacted_texts: list[str]) -> dict:
    """Ask the loaded model to review already-redacted text for residual PII.

    Regex remains the mandatory safety gate. This model pass is a redundant
    review over the redacted output and is instructed not to quote any
    remaining personal data it suspects.
    """
    gc = getattr(app.state, "gemma_call", None)
    if gc is None:
        return {
            "available": False,
            "status": "no_model",
            "findings": [],
            "detail": "No Gemma 4 model is loaded; deterministic redaction still ran.",
        }
    snippets = [
        {"index": idx, "text": str(text)[:1200]}
        for idx, text in enumerate(redacted_texts[:20])
    ]
    prompt = (
        "You are DueCare's privacy reviewer. You are reviewing text AFTER "
        "deterministic regex redaction. Do not repeat, quote, or copy any "
        "remaining personal data. Return compact JSON only with keys: "
        "overall_status ('pass' or 'review_required'), findings (array of "
        "{index, category, severity, explanation_without_quote}), and "
        "recommended_action. Flag possible remaining names, phone numbers, "
        "emails, IDs, exact addresses, case narratives that identify a worker, "
        "or unredacted third-party contact details. If none are visible, return "
        "overall_status='pass'.\n\n"
        + _json.dumps({"redacted_texts": snippets}, ensure_ascii=False)
    )
    try:
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        try:
            model_out = gc(messages, max_new_tokens=240, temperature=0.0)
        except TypeError:
            model_out = gc(messages)
        text = model_out if isinstance(model_out, str) else (
            (model_out or {}).get("text") or (model_out or {}).get("response") or ""
        )
        text = sanitize_model_output(text)
        parsed = None
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                parsed = _json.loads(text[start:end + 1])
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            findings = parsed.get("findings") or []
            if not isinstance(findings, list):
                findings = []
            return {
                "available": True,
                "status": "ok",
                "overall_status": parsed.get("overall_status") or ("review_required" if findings else "pass"),
                "findings": findings[:20],
                "recommended_action": parsed.get("recommended_action") or "",
                "prompt_chars": len(prompt),
            }
        return {
            "available": True,
            "status": "unparsed_text",
            "overall_status": "review_required",
            "findings": [{
                "index": None,
                "category": "model_review_unparsed",
                "severity": "medium",
                "explanation_without_quote": "Gemma returned non-JSON output; review anonymized text manually before submit.",
            }],
            # Scrub kernel run IDs / staging paths / synthetic case
            # folder names so the worker-facing fallback text reads as
            # the (possibly malformed) Gemma narrative, not as a
            # build-log fragment. fact_excerpt also picks a sentence
            # boundary so the preview doesn't trail off mid-word.
            "text_preview": _fact_excerpt(text, 500),
            "prompt_chars": len(prompt),
        }
    except Exception as exc:
        return {
            "available": True,
            "status": "model_error",
            "overall_status": "review_required",
            "findings": [{
                "index": None,
                "category": "model_review_error",
                "severity": "medium",
                "explanation_without_quote": f"{type(exc).__name__}: {exc}"[:220],
            }],
            "recommended_action": "Review anonymized text manually before submitting.",
        }


def _build_anonymize_response(app: Any, body: dict[str, Any], *, replay_endpoint: str = "/api/anonymize") -> dict[str, Any]:
    texts = body.get("texts") or []
    if not isinstance(texts, list):
        raise HTTPException(400, "`texts` must be a list of strings")
    salt = body.get("salt") or DEFAULT_SALT
    gemma_review_requested = bool(body.get("gemma_review"))

    out_texts: list[str] = []
    out_diffs: list[dict] = []
    for t in texts:
        t = str(t)
        redactions: list[dict] = []
        redacted = t
        for label, pat in PII_PATTERNS:
            for m in pat.finditer(t):
                raw = m.group(0)
                ph = placeholder(label, raw, salt=salt)
                redactions.append({
                    "label": label,
                    "raw_sha256": raw_sha256(raw),
                    "placeholder": ph,
                    "start": m.start(),
                    "end": m.end(),
                })
                redacted = redacted.replace(raw, ph)
        out_texts.append(redacted)
        out_diffs.append({"n_redactions": len(redactions), "redactions": redactions})
    gemma_review = (
        _gemma_anonymization_review(app, out_texts)
        if gemma_review_requested
        else {
            "available": bool(getattr(app.state, "gemma_call", None)),
            "status": "not_requested",
            "findings": [],
        }
    )
    try:
        from .._training_log import log_interaction as _log
        _log(
            "anonymization",
            input_payload={"n_texts": len(texts)},
            output_payload={
                "n_redacted_texts": len(out_texts),
                "total_redactions": sum(d["n_redactions"] for d in out_diffs),
                "labels_seen": sorted({r["label"]
                                      for d in out_diffs
                                      for r in d["redactions"]}),
                "gemma_review_status": gemma_review.get("status"),
                "gemma_review_overall": gemma_review.get("overall_status"),
            },
            applied_layers={},
            trace={},
            anonymize=False,
        )
    except Exception:
        pass
    return {
        "redacted": out_texts,
        "diffs": out_diffs,
        "gemma_review": gemma_review,
        # Hard, top-level signal that the second-layer Gemma residual-PII review
        # crashed (vs. ran and flagged nothing). The regex redaction above still
        # ran, but callers must be able to hard-block submission on a review
        # *failure* instead of mistaking the soft "review_required" advisory for
        # a clean pass. UIs gate the Submit button on this.
        "gemma_review_model_error": gemma_review.get("status") == "model_error",
        "demo_replay": demo_replay(
            lane="anonymization_sharing",
            endpoint=replay_endpoint,
            request={
                "n_texts": len(texts),
                "text_sha256": [
                    hashlib.sha256(str(t).encode("utf-8", errors="replace")).hexdigest()
                    for t in texts
                ],
                "gemma_review": gemma_review_requested,
                "salt_scope": "caller supplied" if body.get("salt") else "default demo salt",
            },
            response_summary={
                "n_redacted_texts": len(out_texts),
                "total_redactions": sum(d["n_redactions"] for d in out_diffs),
                "gemma_review_status": gemma_review.get("status"),
                "gemma_review_overall": gemma_review.get("overall_status"),
            },
            artifacts=[{
                "name": "redacted_texts",
                "kind": "inline_response_json",
                "count": len(out_texts),
            }],
            note=(
                "Raw texts are represented by sha256 here. Use the "
                "browser replay download only for synthetic demo material "
                "if you need exact local request bodies."
            ),
        ),
    }


def register_routes(app: Any) -> None:

    def _anon_jobs() -> tuple[dict[str, dict[str, Any]], _threading.Lock]:
        if not hasattr(app.state, "anonymization_jobs"):
            app.state.anonymization_jobs = {}
        if not hasattr(app.state, "anonymization_jobs_lock"):
            app.state.anonymization_jobs_lock = _threading.Lock()
        return app.state.anonymization_jobs, app.state.anonymization_jobs_lock

    def _anon_job_update(job_id: str, **fields: Any) -> None:
        jobs, lock = _anon_jobs()
        with lock:
            job = jobs.setdefault(job_id, {"job_id": job_id, "events": []})
            now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if job.get("status") in {"abandoned", "cancelled"} and fields.get("status") not in {"abandoned", "cancelled"}:
                incoming_status = str(fields.get("status") or "running")
                if incoming_status == "complete":
                    job["late_status"] = "complete"
                    job["late_completed_at"] = now
                    if fields.get("result") is not None:
                        job["late_result"] = fields.get("result")
                    job.setdefault("events", []).append({
                        "ts": now,
                        "status": "abandoned",
                        "phase": "late_complete",
                        "pct": job.get("pct", 0),
                        "detail": "Gemma privacy review completed after browser polling was abandoned; result is retained as late_result.",
                    })
                elif incoming_status == "error":
                    job["late_status"] = "error"
                    job["late_error"] = fields.get("error") or fields.get("detail") or "worker failed"
                    job.setdefault("events", []).append({
                        "ts": now,
                        "status": "abandoned",
                        "phase": "late_error",
                        "pct": job.get("pct", 0),
                        "detail": str(job["late_error"])[:300],
                    })
                job["updated_at"] = now
                return
            event = {
                "ts": now,
                "status": fields.get("status", job.get("status", "running")),
                "phase": fields.get("phase", job.get("phase", "running")),
                "pct": fields.get("pct", job.get("pct", 0)),
                "detail": fields.get("detail", ""),
            }
            for key in ("error",):
                if key in fields and fields[key] is not None:
                    event[key] = fields[key]
            job.update(fields)
            job.setdefault("events", []).append(event)
            job["updated_at"] = now

    @app.post("/api/anonymize")
    async def api_anonymize(request: Request) -> Any:
        """{texts:[...], salt:str?} -> {redacted:[...], diffs:[...]}."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        return JSONResponse(_build_anonymize_response(app, body))

    @app.post("/api/anonymize/start")
    async def api_anonymize_start(request: Request) -> Any:
        """Start deterministic redaction plus optional Gemma privacy review."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        texts = body.get("texts") or []
        if not isinstance(texts, list):
            raise HTTPException(400, "`texts` must be a list of strings")
        job_id = f"anonymize_{_uuid4().hex[:12]}"
        now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        jobs, lock = _anon_jobs()
        with lock:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "queued",
                "pct": 4,
                "created_at": now,
                "updated_at": now,
                "events": [{
                    "ts": now,
                    "status": "queued",
                    "phase": "queued",
                    "pct": 4,
                    "detail": "Anonymization queued. Regex redaction runs first; Gemma residual-PII review is optional.",
                }],
            }

        def worker() -> None:
            try:
                _anon_job_update(
                    job_id,
                    status="running",
                    phase="regex_redaction",
                    pct=28,
                    detail="Running deterministic regex redaction and salted placeholders.",
                )
                if body.get("gemma_review"):
                    _anon_job_update(
                        job_id,
                        status="running",
                        phase="gemma_privacy_review",
                        pct=58,
                        detail="Calling local Gemma 4 to review already-redacted text for residual PII.",
                    )
                result = _build_anonymize_response(
                    app,
                    body,
                    replay_endpoint="/api/anonymize/start",
                )
                _anon_job_update(
                    job_id,
                    status="complete",
                    phase="complete",
                    pct=100,
                    detail="Anonymization complete. Review redacted output before submit.",
                    result=result,
                )
            except Exception as e:
                _anon_job_update(
                    job_id,
                    status="error",
                    phase="failed",
                    pct=100,
                    detail=str(e),
                    error=f"{type(e).__name__}: {e}"[:300],
                )

        thread = _threading.Thread(target=worker, name=f"duecare-{job_id}", daemon=True)
        thread.start()
        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "phase": "queued",
            "pct": 4,
            "poll_url": f"/api/anonymize/status/{job_id}",
            "cancel_url": f"/api/anonymize/cancel/{job_id}",
            "demo_replay": demo_replay(
                lane="anonymization_sharing",
                endpoint="/api/anonymize/start",
                request={
                    "n_texts": len(texts),
                    "text_sha256": [
                        hashlib.sha256(str(t).encode("utf-8", errors="replace")).hexdigest()
                        for t in texts
                    ],
                    "gemma_review": bool(body.get("gemma_review")),
                    "salt_scope": "caller supplied" if body.get("salt") else "default demo salt",
                },
                response_summary={
                    "job_id": job_id,
                    "poll_url": f"/api/anonymize/status/{job_id}",
                    "cancel_url": f"/api/anonymize/cancel/{job_id}",
                },
                artifacts=[{
                    "name": "anonymization_job_status",
                    "kind": "poll_endpoint",
                    "path": f"/api/anonymize/status/{job_id}",
                }],
            ),
        })

    @app.post("/api/anonymize/cancel/{job_id}")
    def api_anonymize_cancel(job_id: str) -> Any:
        jobs, lock = _anon_jobs()
        with lock:
            job = jobs.get(job_id)
            if not job:
                raise HTTPException(404, f"unknown anonymization job: {job_id}")
            if job.get("status") in {"complete", "error"}:
                job["cancelled"] = False
                job["cancel_detail"] = "Job already reached a terminal state before cancel."
                return JSONResponse(dict(job))
            now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            job["status"] = "abandoned"
            job["phase"] = "abandoned"
            job["detail"] = (
                "Browser-side polling was abandoned. Rerun with Gemma privacy "
                "review off for deterministic redaction, or check this status "
                "endpoint later for late_result."
            )
            job["cancelled"] = True
            job["abandoned_at"] = now
            job["updated_at"] = now
            job.setdefault("events", []).append({
                "ts": now,
                "status": "abandoned",
                "phase": "abandoned",
                "pct": job.get("pct", 0),
                "detail": job["detail"],
            })
            return JSONResponse(dict(job))

    @app.get("/api/anonymize/status/{job_id}")
    def api_anonymize_status(job_id: str) -> Any:
        jobs, lock = _anon_jobs()
        with lock:
            job = dict(jobs.get(job_id) or {})
        if not job:
            raise HTTPException(404, f"unknown anonymization job: {job_id}")
        return JSONResponse(job)

    @app.post("/api/submit/knowledge")
    async def api_submit_knowledge(request: Request) -> Any:
        """Submit anonymized knowledge items with local audit + remote POST."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        items = body.get("knowledge") or body.get("facts") or []
        target_url = body.get("target_url") or _DEFAULT_HUB_SUBMIT_URL
        if not isinstance(items, list):
            raise HTTPException(400, "`knowledge` must be a list")

        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"01_submit_{ts}"
        payload = {"submission_id": run_id, "ts": ts, "items": items}
        blob = _json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        sha = hashlib.sha256(blob).hexdigest()

        audit_path = _audit_dir() / "submit_log.jsonl"
        remote_status, remote_response, remote_error, transmitted = _post_payload(
            target_url, payload, sha
        )

        entry = {
            "ts": ts,
            "run_id": run_id,
            "action": "submit/knowledge",
            "target_url": target_url,
            "n_items": len(items),
            "sha256_blob": sha,
            "queued": True,
            "transmitted": transmitted,
            "remote_status": remote_status,
            "remote_error": remote_error,
        }
        try:
            with open(audit_path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception as e:
            fallback_path = _Path(".") / ".duecare-audit" / "submit_log.jsonl"
            try:
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                entry["audit_fallback_reason"] = f"{type(e).__name__}: {e}"
                with open(fallback_path, "a", encoding="utf-8") as f:
                    f.write(_json.dumps(entry) + "\n")
                audit_path = fallback_path
            except Exception as fallback_error:
                raise HTTPException(
                    500,
                    "audit write failed: "
                    f"{e}; fallback failed: {fallback_error}",
                )
        return JSONResponse({
            "ok": True,
            "run_id": run_id,
            "audit_path": str(audit_path),
            "n_items": len(items),
            "sha256_blob": sha,
            "audit_entry": entry,
            "transmitted": transmitted,
            "remote_status": remote_status,
            "remote_response": remote_response,
            "remote_error": remote_error,
            "demo_replay": demo_replay(
                lane="anonymization_sharing",
                endpoint="/api/submit/knowledge",
                request={
                    "target_url": target_url,
                    "n_items": len(items),
                    "knowledge_sha256": sha256_json(items),
                },
                response_summary={
                    "run_id": run_id,
                    "audit_path": str(audit_path),
                    "sha256_blob": sha,
                    "transmitted": transmitted,
                    "remote_status": remote_status,
                    "remote_error": remote_error,
                },
                artifacts=[{
                    "name": "submit_audit_log",
                    "kind": "jsonl",
                    "path": str(audit_path),
                }],
            ),
            "note": (
                "Knowledge transmitted." if transmitted else
                ("Local audit written. Remote returned "
                 + (f"HTTP {remote_status}" if remote_status else f"network error: {remote_error}")
                 + " -- rerun when the public hub is reachable.")
            ),
        })

    @app.post("/api/submit/local")
    async def api_submit_local(request: Request) -> Any:
        """Deprecated alias. Delegates to /api/submit/knowledge."""
        return await api_submit_knowledge(request)
