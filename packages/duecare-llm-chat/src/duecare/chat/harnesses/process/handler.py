"""Process Files harness handler.

Owns:
  - POST /api/process/batch -- multipart upload -> v1.0 bundle envelope
  - POST /api/process/graph-chat -- Gemma 4 query over the last bundle
"""
from __future__ import annotations

import csv as _csv
import io as _io
import json as _json
import re as _re
import zipfile
from datetime import datetime as _dt
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .extractor import ENTITY_PATTERNS
from .prompts import GRAPH_CHAT_SYSTEM_PROMPT, build_context_block


_ROW_CAP = 200
_DATE_RE = _re.compile(r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})\b", _re.IGNORECASE)
_CASE_RE = _re.compile(r"\b(?:DC-)?PH[-_ ]?HK[-_ ]?\d{3}\b|\bperson[-_ ]?\d{3}\b|\bCASE[-_ ]?\d{3}\b", _re.IGNORECASE)
_NAME_RE = _re.compile(r"\b(?:name|worker_name|complainant|subject)\s*[:=]\s*([A-Z][A-Za-z.' -]{2,60})")
_EMPLOYER_RE = _re.compile(r"\b(?:employer|household|company)\s*[:=]\s*([A-Z][A-Za-z0-9 &'.,-]{2,80})")
_AGENCY_RE = _re.compile(r"\b(?:agency|recruiter|broker)\s*[:=]\s*([A-Z][A-Za-z0-9 &'.,-]{2,80})")
_LOCATION_RE = _re.compile(r"\b(?:Manila|Quezon City|Cebu|Davao|Iloilo|Clark|Makati|Hong Kong|Central|Causeway Bay|Mong Kok|Sha Tin|Kowloon|Wan Chai|Tsuen Wan|Yuen Long|Tuen Mun)\b", _re.IGNORECASE)


def _norm_case_id(text: str) -> str | None:
    match = _CASE_RE.search(text or "")
    if not match:
        return None
    raw = match.group(0).upper().replace("_", "-").replace(" ", "-")
    raw = raw.replace("PERSON-", "PH-HK-").replace("CASE-", "PH-HK-")
    if raw.startswith("DC-"):
        return raw
    if raw.startswith("PH-HK-"):
        return "DC-" + raw
    digits = _re.search(r"(\d{3})", raw)
    return f"DC-PH-HK-{digits.group(1)}" if digits else raw


def _first_match(pattern: _re.Pattern, text: str) -> str | None:
    match = pattern.search(text or "")
    if not match:
        return None
    value = match.group(1) if match.lastindex else match.group(0)
    return " ".join(str(value).strip().split())


def _file_kind(row_id: str, text: str) -> str:
    hay = f"{row_id}\n{text}".lower()
    checks = (
        ("id_card", ("id_card", "identity card", "philippine id", "passport no")),
        ("complaint", ("complaint", "affidavit", "sworn statement")),
        ("police_report", ("police report", "incident report", "case officer")),
        ("travel_history", ("travel history", "flight", "arrival", "departure")),
        ("location_history", ("location history", "gps", "cell tower", "location ping")),
        ("payment_history", ("payment history", "remittance", "receipt", "salary deduction")),
        ("chat_messages", ("chat", "whatsapp", "telegram", "message")),
        ("contract", ("contract", "employment agreement", "live-in")),
    )
    for kind, needles in checks:
        if any(n in hay for n in needles):
            return kind
    return "other"


def _amount_value(raw: str) -> float:
    match = _re.search(r"([\d,]+(?:\.\d+)?)", raw or "")
    if not match:
        return 0.0
    try:
        return float(match.group(1).replace(",", ""))
    except Exception:
        return 0.0


def _build_intelligence(rows: list[dict], results: list[dict]) -> dict:
    """Create the process-harness intelligence view shown in the UI.

    This is intentionally deterministic and fast. When Gemma is loaded,
    _gemma_case_brief adds a model-authored case brief on top of these
    structured facts.
    """
    people: dict[str, dict] = {}
    doc_type_counts: dict[str, int] = {}
    timeline: list[dict] = []
    payments: list[dict] = []
    locations: dict[str, int] = {}
    evidence_edges: list[dict] = []

    by_row = {r.get("row_id"): r for r in results}
    for row in rows:
        row_id = row.get("row_id") or "row"
        text = row.get("text") or ""
        scored = by_row.get(row_id) or {}
        kind = _file_kind(row_id, text)
        doc_type_counts[kind] = doc_type_counts.get(kind, 0) + 1
        case_id = _norm_case_id(row_id) or _norm_case_id(text) or "UNKNOWN"
        person = people.setdefault(case_id, {
            "case_id": case_id,
            "name": None,
            "corridor": "PH-HK" if _re.search(r"\bPH[-\s]?HK\b|Philippines|Hong Kong", text, _re.I) else None,
            "employer": None,
            "agency": None,
            "document_types": {},
            "row_ids": [],
            "risk_score": 0,
            "risk_signals": [],
            "amounts": [],
            "locations": [],
            "timeline": [],
        })
        person["row_ids"].append(row_id)
        person["document_types"][kind] = person["document_types"].get(kind, 0) + 1
        person["name"] = person["name"] or _first_match(_NAME_RE, text)
        person["employer"] = person["employer"] or _first_match(_EMPLOYER_RE, text)
        person["agency"] = person["agency"] or _first_match(_AGENCY_RE, text)

        for loc in _LOCATION_RE.findall(text):
            loc_norm = str(loc).title()
            locations[loc_norm] = locations.get(loc_norm, 0) + 1
            if loc_norm not in person["locations"]:
                person["locations"].append(loc_norm)

        for date in _DATE_RE.findall(text)[:6]:
            item = {"case_id": case_id, "row_id": row_id, "date": date, "document_type": kind}
            timeline.append(item)
            person["timeline"].append(item)

        for amt in (scored.get("entities") or {}).get("AMOUNT", []):
            value = _amount_value(amt)
            pay = {"case_id": case_id, "row_id": row_id, "amount": amt, "value": value, "document_type": kind}
            payments.append(pay)
            person["amounts"].append(pay)

        for hit in scored.get("grep_hits") or []:
            severity = (hit.get("severity") or "medium").lower()
            inc = {"critical": 30, "high": 20, "medium": 12, "low": 6}.get(severity, 8)
            person["risk_score"] += inc
            rid = hit.get("rule_id") or "unknown_rule"
            if rid not in person["risk_signals"]:
                person["risk_signals"].append(rid)
            evidence_edges.append({
                "case_id": case_id,
                "row_id": row_id,
                "rule_id": rid,
                "severity": severity,
                "document_type": kind,
            })

        keyword_risk = (
            ("passport", "passport retention"),
            ("deduction", "salary deduction"),
            ("loan", "loan or debt"),
            ("placement fee", "placement fee"),
            ("live-in", "live-in control"),
            ("threat", "threat or coercion"),
        )
        lower = text.lower()
        for needle, label in keyword_risk:
            if needle in lower and label not in person["risk_signals"]:
                person["risk_score"] += 6
                person["risk_signals"].append(label)

    person_rows = []
    for p in people.values():
        person_rows.append({
            **p,
            "risk_score": min(100, int(p.get("risk_score") or 0)),
            "n_documents": len(p.get("row_ids") or []),
            "n_payments": len(p.get("amounts") or []),
            "total_payment_value": round(sum(float(x.get("value") or 0) for x in p.get("amounts") or []), 2),
            "risk_signals": (p.get("risk_signals") or [])[:12],
            "locations": (p.get("locations") or [])[:12],
            "timeline": (p.get("timeline") or [])[:10],
        })
    person_rows.sort(key=lambda p: (-p.get("risk_score", 0), p.get("case_id", "")))
    timeline.sort(key=lambda x: str(x.get("date", "")))
    payments.sort(key=lambda x: -float(x.get("value") or 0))
    hierarchy = {
        "root": "uploaded_bundle",
        "document_types": [
            {"type": k, "count": v} for k, v in sorted(doc_type_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "people": [
            {
                "case_id": p["case_id"],
                "name": p.get("name"),
                "documents": p.get("document_types", {}),
                "risk_score": p.get("risk_score", 0),
            }
            for p in person_rows[:50]
        ],
    }
    return {
        "version": "process-intelligence-v1",
        "n_people": len([p for p in person_rows if p.get("case_id") != "UNKNOWN"]),
        "n_documents": len(rows),
        "n_evidence_edges": len(evidence_edges),
        "document_type_counts": doc_type_counts,
        "people": person_rows,
        "hierarchy": hierarchy,
        "top_payments": payments[:20],
        "timeline": timeline[:40],
        "locations": [{"name": k, "count": v} for k, v in sorted(locations.items(), key=lambda kv: (-kv[1], kv[0]))[:20]],
        "evidence_edges": evidence_edges[:80],
    }


def _gemma_case_brief(app: Any, bundle: dict, intelligence: dict) -> dict:
    gc = getattr(app.state, "gemma_call", None)
    if gc is None:
        return {"available": False, "status": "no_model_loaded"}
    compact = {
        "summary": bundle.get("summary", {}),
        "people": (intelligence.get("people") or [])[:12],
        "document_types": intelligence.get("document_type_counts", {}),
        "top_payments": (intelligence.get("top_payments") or [])[:10],
        "timeline": (intelligence.get("timeline") or [])[:12],
    }
    prompt = (
        "You are DueCare's Gemma 4 process harness analyst. "
        "Given a locally extracted PH to HK case-bundle intelligence object, "
        "produce compact JSON with keys: case_theory, priority_people, "
        "risk_clusters, missing_evidence, recommended_questions. "
        "Use only the supplied facts and row_ids. Do not invent facts.\n\n"
        + _json.dumps(compact, ensure_ascii=False)[:12000]
    )
    try:
        model_out = gc(prompt, max_new_tokens=700, temperature=0.2)
        text = model_out if isinstance(model_out, str) else (
            (model_out or {}).get("text") or (model_out or {}).get("response") or ""
        )
        match = _re.search(r"\{[\s\S]*\}", text or "")
        parsed = None
        if match:
            try:
                parsed = _json.loads(match.group(0))
            except Exception:
                parsed = None
        return {
            "available": True,
            "status": "ok" if parsed else "unparsed_text",
            "text": text[:3000],
            "json": parsed,
            "prompt_chars": len(prompt),
        }
    except Exception as exc:
        return {
            "available": True,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }


def _parse_upload(filename: str, contents: bytes) -> list[dict]:
    fname_l = filename.lower()
    rows: list[dict] = []
    if fname_l.endswith(".zip"):
        with zipfile.ZipFile(_io.BytesIO(contents)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                try:
                    txt = zf.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue
                rows.append({"row_id": name, "text": txt, "source": filename})
    elif fname_l.endswith(".jsonl"):
        for i, line in enumerate(contents.decode("utf-8", errors="replace").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                txt = obj.get("prompt") or obj.get("text") or _json.dumps(obj)
            except Exception:
                txt = line
            rows.append({"row_id": f"line_{i}", "text": txt, "source": filename})
    elif fname_l.endswith(".csv"):
        buf = _io.StringIO(contents.decode("utf-8", errors="replace"))
        reader = _csv.reader(buf)
        all_rows = list(reader)
        start = 1 if all_rows and all_rows[0] else 0
        for i, row in enumerate(all_rows[start:]):
            if not row:
                continue
            rows.append({"row_id": f"row_{i}", "text": row[0], "source": filename})
    else:
        blob = contents.decode("utf-8", errors="replace")
        for i, chunk in enumerate([c for c in blob.split("\n\n") if c.strip()]):
            rows.append({"row_id": f"chunk_{i}", "text": chunk, "source": filename})
    return rows


def _score_rows(rows: list[dict], grep_call: Any) -> tuple[list[dict], dict, dict, dict]:
    results: list[dict] = []
    agg_grep: dict[str, int] = {}
    agg_entity: dict[str, int] = {}
    agg_statute: dict[str, int] = {}

    for row in rows:
        text = row["text"] or ""
        grep_hits: list[dict] = []
        if grep_call is not None:
            try:
                try:
                    gr = grep_call(text) or {}
                except TypeError:
                    gr = grep_call(text, extra_rules=None) or {}
                for h in (gr.get("hits") or [])[:10]:
                    rid = h.get("rule_id") or h.get("id") or "?"
                    grep_hits.append({
                        "rule_id": rid,
                        "category": h.get("category"),
                        "severity": h.get("severity"),
                        "match": (h.get("match_text") or h.get("match") or "")[:120],
                    })
                    agg_grep[rid] = agg_grep.get(rid, 0) + 1
            except Exception:
                pass

        entities: dict[str, list[str]] = {}
        for ent_label, pat in ENTITY_PATTERNS.items():
            hits = pat.findall(text)
            if hits:
                seen = list(dict.fromkeys(hits))[:8]
                entities[ent_label] = seen
                agg_entity[ent_label] = agg_entity.get(ent_label, 0) + len(seen)
                if ent_label == "STATUTE":
                    for s in seen:
                        agg_statute[s] = agg_statute.get(s, 0) + 1

        results.append({
            "row_id": row["row_id"],
            "source": row["source"],
            "char_count": len(text),
            "grep_hits": grep_hits,
            "entities": entities,
        })

    return results, agg_grep, agg_entity, agg_statute


def register_routes(app: Any) -> None:
    """Attach the process routes to a FastAPI app."""

    @app.post("/api/process/batch")
    async def api_process_batch(request: Request) -> Any:
        """Multipart upload -> rows -> GREP hits + entity regex -> v1.0 bundle."""
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no `file` field in multipart upload")
        contents = await upload.read()
        filename = getattr(upload, "filename", "uploaded") or "uploaded"

        try:
            rows = _parse_upload(filename, contents)
        except Exception as e:
            raise HTTPException(400, f"parse failed: {e}")

        capped = rows[:_ROW_CAP]
        results, agg_grep, agg_entity, agg_statute = _score_rows(
            capped, getattr(app.state, "grep_call", None)
        )

        ts = _dt.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"01_process_{ts}"
        top_grep = sorted(agg_grep.items(), key=lambda x: -x[1])[:10]
        top_statute = sorted(agg_statute.items(), key=lambda x: -x[1])[:10]
        bundle = {
            "schema_version": "1.0",
            "kernel_id": "01-duecare-exploration-workbench",
            "run_id": run_id,
            "config": {"row_cap": _ROW_CAP, "source": filename},
            "metadata": {"started_at": ts, "completed_at": ts, "host": "kernel-01"},
            "summary": {
                "n_rows_total": len(rows),
                "n_rows_processed": len(capped),
                "n_grep_rules_fired": len(agg_grep),
                "n_entities_extracted": sum(agg_entity.values()),
                "top_grep": [{"rule_id": r, "count": c} for r, c in top_grep],
                "top_statutes": [{"statute": s, "count": c} for s, c in top_statute],
                "entity_totals": agg_entity,
                "truncated": len(rows) > _ROW_CAP,
            },
            "results": results,
        }
        intelligence = _build_intelligence(capped, results)
        gemma_brief = _gemma_case_brief(app, bundle, intelligence)
        intelligence["gemma_case_brief"] = gemma_brief
        intelligence["harness_trace"] = [
            {
                "id": "upload",
                "label": "Upload accepted",
                "status": "complete",
                "detail": f"{filename} with {len(rows)} parsed rows",
            },
            {
                "id": "unpack",
                "label": "Bundle unpacked",
                "status": "complete",
                "detail": f"{len(capped)} rows kept under cap {_ROW_CAP}",
            },
            {
                "id": "grep",
                "label": "GREP safety scan",
                "status": "complete",
                "detail": f"{len(agg_grep)} unique rules fired",
            },
            {
                "id": "attributes",
                "label": "Entity and document attributes",
                "status": "complete",
                "detail": f"{intelligence.get('n_people', 0)} people, {len(intelligence.get('document_type_counts') or {})} document types",
            },
            {
                "id": "gemma",
                "label": "Gemma 4 case brief",
                "status": "complete" if gemma_brief.get("status") in {"ok", "unparsed_text"} else "skipped",
                "detail": gemma_brief.get("status", "not_run"),
            },
            {
                "id": "graph",
                "label": "Local graph cached",
                "status": "complete",
                "detail": f"{intelligence.get('n_evidence_edges', 0)} evidence edges",
            },
        ]
        bundle["intelligence"] = intelligence
        bundle["summary"]["n_people_detected"] = intelligence.get("n_people", 0)
        bundle["summary"]["n_evidence_edges"] = intelligence.get("n_evidence_edges", 0)
        bundle["summary"]["gemma_case_brief_status"] = gemma_brief.get("status")
        app.state.last_process_bundle = bundle
        try:
            from .._training_log import log_interaction as _log
            _summary = bundle.get("summary") or {}
            _log(
                "process",
                input_payload={"filename": filename, "n_rows": len(rows)},
                output_payload={
                    "run_id": bundle.get("run_id"),
                    "n_processed": _summary.get("n_rows_processed", 0),
                    "top_grep": _summary.get("top_grep", []),
                    "entity_totals": _summary.get("entity_totals", {}),
                    "n_people_detected": _summary.get("n_people_detected", 0),
                    "gemma_case_brief_status": _summary.get("gemma_case_brief_status"),
                },
                applied_layers={"grep": {"fired": _summary.get("n_grep_rules_fired", 0) > 0}},
                trace={
                    "top_statutes": _summary.get("top_statutes", []),
                    "harness_trace": intelligence.get("harness_trace", []),
                },
                extra={"kind": "batch"},
            )
        except Exception:
            pass
        return JSONResponse(bundle)

    @app.post("/api/process/graph-chat")
    async def api_process_graph_chat(request: Request) -> Any:
        """Query Gemma 4 against the most recent bundle uploaded via /api/process/batch."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        question = (body.get("question") or "").strip()
        if not question:
            raise HTTPException(400, "question is required")

        bundle = getattr(app.state, "last_process_bundle", None)
        gc = getattr(app.state, "gemma_call", None)

        if bundle is None:
            return JSONResponse({
                "answer": "No bundle has been uploaded yet on this kernel. "
                "Upload a ZIP/CSV/JSONL on the Process Files tab first, then "
                "ask the question again.",
                "bundle_present": False,
                "cited_rows": [],
                "grep_hits": 0,
            })

        if gc is None:
            summary = bundle.get("summary") or {}
            top = (summary.get("top_grep") or [])[:3]
            return JSONResponse({
                "answer": (
                    "No model is loaded; cannot synthesize a narrative. "
                    f"Bundle has {summary.get('n_rows_processed', 0)} rows "
                    f"with {summary.get('n_grep_rules_fired', 0)} unique GREP "
                    f"rules fired. Top: "
                    + ", ".join(f"{t['rule_id']} ({t['count']})" for t in top)
                ),
                "bundle_present": True,
                "cited_rows": [r["row_id"] for r in (bundle.get("results") or [])[:5]],
                "grep_hits": sum(c["count"] for c in (summary.get("top_grep") or [])),
                "fallback": "no_model_loaded",
            })

        # Layer composition: GREP + RAG + Tools against the user question so
        # the answer cites legal context, not just bundle row_ids. Wired
        # layers run; missing ones skipped silently.
        from .._layers import compose_layers
        layer_out = compose_layers(app, question, layers=("grep", "rag", "tools"))
        context_block = build_context_block(bundle)
        system_text = GRAPH_CHAT_SYSTEM_PROMPT + "\n\n" + context_block
        if layer_out["grounding"]:
            system_text += "\n\nAdditional grounding:\n" + layer_out["grounding"]
        msgs = [
            {"role": "system", "content": [{"type": "text", "text": system_text}]},
            {"role": "user", "content": [{"type": "text", "text": question}]},
        ]
        try:
            model_out = gc(msgs, max_new_tokens=600, temperature=0.3)
            response_text = model_out if isinstance(model_out, str) else (
                (model_out or {}).get("text") or (model_out or {}).get("response") or ""
            )
        except Exception as e:
            return JSONResponse(
                {"answer": f"Model call failed: {str(e)[:200]}", "bundle_present": True},
                status_code=500,
            )

        results = bundle.get("results") or []
        cited_rows: list[str] = []
        for r in results:
            rid = r.get("row_id") or ""
            if rid and rid in response_text:
                cited_rows.append(rid)
        cited_rows = cited_rows[:20]

        summary = bundle.get("summary") or {}
        try:
            from .._training_log import log_interaction as _log
            _log(
                "process",
                input_payload={"question": question, "bundle_run_id": bundle.get("run_id")},
                output_payload=response_text,
                applied_layers=layer_out["trace"],
                trace={"cited_rows": cited_rows, "grep_hits": summary.get("n_grep_rules_fired", 0)},
                extra={"kind": "graph_chat"},
            )
        except Exception:
            pass
        return JSONResponse({
            "answer": response_text,
            "bundle_present": True,
            "cited_rows": cited_rows,
            "grep_hits": summary.get("n_grep_rules_fired", 0),
            "applied_layers": layer_out["trace"],
        })
