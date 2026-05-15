"""Anonymization & Sharing harness handler.

Owns:
  - POST /api/anonymize -- batch redact PII in text array
  - POST /api/submit/knowledge -- audit + HTTPS POST to the public hub
  - POST /api/submit/local -- deprecated alias for submit/knowledge
"""
from __future__ import annotations

import hashlib
import json as _json
from datetime import datetime as _dt
from pathlib import Path as _Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..._model_output import sanitize_model_output
from .detector import PII_PATTERNS
from .redactor import DEFAULT_SALT, placeholder, raw_sha256


_DEFAULT_HUB_SUBMIT_URL = "https://gemma4-comp.onrender.com/api/submit/knowledge"


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


def _post_payload(target_url: str, payload: dict, sha: str) -> tuple[int | None, str | None, str | None, bool]:
    headers = {
        "Content-Type": "application/json",
        "X-DueCare-Source": "kernel-01",
        "X-DueCare-SHA256": sha,
    }
    try:
        try:
            import httpx as _httpx
            with _httpx.Client(timeout=10.0, follow_redirects=True) as cli:
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
            "text_preview": text[:500],
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


def register_routes(app: Any) -> None:

    @app.post("/api/anonymize")
    async def api_anonymize(request: Request) -> Any:
        """{texts:[...], salt:str?} -> {redacted:[...], diffs:[...]}."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
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
        return JSONResponse({
            "redacted": out_texts,
            "diffs": out_diffs,
            "gemma_review": gemma_review,
        })

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

        ts = _dt.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
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
