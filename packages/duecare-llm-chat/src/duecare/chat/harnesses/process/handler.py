"""Bulk File Review harness handler.

Owns:
  - POST /api/process/batch: multipart upload to v1.0 bundle envelope
  - POST /api/process/graph-chat: Gemma 4 query over the last bundle
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

from ..._model_output import sanitize_model_output
from .extractor import ENTITY_PATTERNS
from .prompts import GRAPH_CHAT_SYSTEM_PROMPT, build_context_block


_ROW_CAP = 300
_TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".jsonl", ".log"}
_MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
_DOC_IMAGE_EXTS = _MEDIA_EXTS | {".pdf"}
_CHUNK_CHARS = 4500
_DATE_RE = _re.compile(r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})\b", _re.IGNORECASE)
_CASE_RE = _re.compile(r"\b(?:DC-)?PH[-_ ]?HK[-_ ]?\d{3}\b|\bperson[-_ ]?\d{3}\b|\bCASE[-_ ]?\d{3}\b", _re.IGNORECASE)
_NAME_RE = _re.compile(r"\b(?:name|worker_name|complainant|subject)\s*[:=]\s*([A-Z][A-Za-z.' -]{2,60})")
_EMPLOYER_RE = _re.compile(r"\b(?:employer|household|company)\s*[:=]\s*([A-Z][A-Za-z0-9 &'.,-]{2,80})")
_AGENCY_RE = _re.compile(r"\b(?:agency|recruiter|broker)\s*[:=]\s*([A-Z][A-Za-z0-9 &'.,-]{2,80})")
_LOCATION_RE = _re.compile(r"\b(?:Manila|Quezon City|Cebu|Davao|Iloilo|Clark|Makati|Hong Kong|Central|Causeway Bay|Mong Kok|Sha Tin|Kowloon|Wan Chai|Tsuen Wan|Yuen Long|Tuen Mun)\b", _re.IGNORECASE)
_JOURNEY_STAGE_ORDER = {
    "recruitment": 1,
    "payment_and_debt": 2,
    "contracting": 3,
    "documents_and_identity": 4,
    "travel": 5,
    "arrival_and_placement": 6,
    "employment_control": 7,
    "complaint_and_escalation": 8,
    "other_evidence": 99,
}


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
    if any(hay.endswith(ext) or ext + "\n" in hay for ext in _MEDIA_EXTS):
        return "media_image"
    if ".pdf" in hay and "requiring ocr" in hay:
        return "scanned_pdf"
    path = str(row_id or "").replace("\\", "/").lower()
    path_checks = (
        ("chat_messages", ("chats/", "messages/", "whatsapp", "telegram")),
        ("payment_history", ("payment_history/", "payments/", "receipts/")),
        ("location_history", ("location_history/", "locations/")),
        ("travel_history", ("travel_history/", "travel/")),
        ("id_card", ("id_cards/", "identity/", "ids/")),
        ("complaint", ("complaints/", "intake/")),
        ("police_report", ("police_reports/", "reports/")),
    )
    for kind, needles in path_checks:
        if any(n in path for n in needles):
            return kind
    checks = (
        ("id_card", ("id_card", "identity card", "philippine id", "passport no")),
        ("complaint", ("complaint", "affidavit", "sworn statement")),
        ("police_report", ("police report", "incident report", "case officer")),
        ("travel_history", ("travel history", "flight", "arrival", "departure")),
        ("location_history", ("location history", "gps", "cell tower", "location ping")),
        ("chat_messages", ("chat", "whatsapp", "telegram", "message")),
        ("payment_history", ("payment history", "remittance", "receipt", "salary deduction")),
        ("contract", ("contract", "employment agreement", "live-in")),
    )
    for kind, needles in checks:
        if any(n in hay for n in needles):
            return kind
    return "other"


def _ext(name: str) -> str:
    dot = "." + (name.rsplit(".", 1)[-1].lower() if "." in name else "")
    return dot if dot != "." else ""


def _path_metadata(name: str) -> dict[str, Any]:
    """Return folder/path fields that often carry investigative meaning."""
    clean = str(name or "").replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p]
    folders = parts[:-1]
    return {
        "source_path": clean,
        "folders": folders,
        "leaf_name": parts[-1] if parts else clean,
        "folder_context": folders[-1] if folders else None,
    }


def _is_probably_text(name: str, data: bytes) -> bool:
    ext = _ext(name)
    if ext in _TEXT_EXTS:
        return True
    if ext in _DOC_IMAGE_EXTS:
        return False
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    decoded = sample.decode("utf-8", errors="replace")
    if not decoded:
        return False
    return decoded.count("\ufffd") / max(1, len(decoded)) < 0.03


def _chunk_text_rows(
    name: str,
    text: str,
    source: str,
    *,
    parent_doc: str | None = None,
    page_index: int | None = None,
) -> list[dict]:
    clean = text or ""
    parent = parent_doc or name
    base_level = "page" if page_index is not None else "document"
    if len(clean) <= _CHUNK_CHARS * 1.2:
        meta = _path_metadata(name)
        return [{
            "row_id": name,
            "text": clean,
            "source": source,
            "parent_doc": parent,
            "page_index": page_index,
            "chunk_index": 0,
            "processing_level": base_level,
            **meta,
        }]
    rows: list[dict] = []
    for idx, start in enumerate(range(0, len(clean), _CHUNK_CHARS)):
        chunk = clean[start:start + _CHUNK_CHARS]
        suffix = f"page-{page_index:03d}-chunk-{idx + 1:03d}" if page_index is not None else f"chunk-{idx + 1:03d}"
        meta = _path_metadata(f"{parent}#{suffix}")
        rows.append({
            "row_id": f"{parent}#{suffix}",
            "text": chunk,
            "source": source,
            "parent_doc": parent,
            "page_index": page_index,
            "chunk_index": idx,
            "processing_level": f"{base_level}_chunk",
            **meta,
        })
    return rows


def _try_pdf_text_rows(name: str, data: bytes, source: str) -> list[dict]:
    """Extract page text from a PDF when a reader is already installed.

    Kaggle images vary. The process harness should benefit from pypdf or
    PyPDF2 when present, while still treating scanned or unsupported PDFs as
    explicit OCR/Gemma-vision work items.
    """
    reader_cls = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
        except Exception:
            return []

    try:
        reader = reader_cls(_io.BytesIO(data))
        rows: list[dict] = []
        for idx, page in enumerate(getattr(reader, "pages", []) or [], start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                rows.extend(_chunk_text_rows(
                    f"{name}#page-{idx:03d}",
                    text,
                    source,
                    parent_doc=name,
                    page_index=idx,
                ))
        return rows
    except Exception:
        return []


def _media_row(name: str, data: bytes, source: str) -> dict:
    ext = _ext(name)
    media_type = "pdf" if ext == ".pdf" else "image"
    meta = _path_metadata(name)
    return {
        "row_id": name,
        "text": (
            f"[{media_type} asset requiring OCR or multimodal Gemma pass]\n"
            f"file: {name}\n"
            f"bytes: {len(data)}\n"
            "status: queued_for_ocr_and_multimodal_extraction"
        ),
        "source": source,
        "parent_doc": name,
        "chunk_index": 0,
        "processing_level": "media_asset",
        "media_type": media_type,
        "binary_size": len(data),
        "needs_ocr": True,
        **meta,
    }


def _amount_value(raw: str) -> float:
    match = _re.search(r"([\d,]+(?:\.\d+)?)", raw or "")
    if not match:
        return 0.0
    try:
        return float(match.group(1).replace(",", ""))
    except Exception:
        return 0.0


def _journey_stage(row_id: str, text: str, kind: str) -> str:
    hay = f"{row_id}\n{text}".lower()
    if kind == "payment_history":
        return "payment_and_debt"
    if kind == "contract":
        return "contracting"
    if kind == "id_card":
        return "documents_and_identity"
    if kind == "travel_history":
        return "travel"
    if kind == "location_history":
        return "arrival_and_placement"
    if kind in {"complaint", "police_report"}:
        return "complaint_and_escalation"
    if kind == "chat_messages":
        return "recruitment"
    if any(n in hay for n in ("placement fee", "processing fee", "training fee", "salary deduction", "remittance", "receipt", "loan", "debt")):
        return "payment_and_debt"
    if any(n in hay for n in ("contract", "side letter", "second contract", "replacement agreement")):
        return "contracting"
    if any(n in hay for n in ("passport", "identity card", "visa", "document", "id card")):
        return "documents_and_identity"
    if any(n in hay for n in ("flight", "airport", "arrival", "departure", "travel history")):
        return "travel"
    if any(n in hay for n in ("gps", "location ping", "cell tower", "arrival address")):
        return "arrival_and_placement"
    if any(n in hay for n in ("live-in", "day off", "food", "phone", "locked", "threat", "curfew", "employer")):
        return "employment_control"
    if any(n in hay for n in ("complaint", "police report", "case officer", "affidavit", "sworn statement")):
        return "complaint_and_escalation"
    if any(n in hay for n in ("recruiter", "agency", "broker", "slot", "dm", "whatsapp", "telegram")):
        return "recruitment"
    return "other_evidence"


def _journey_summary(stage: str, kind: str, signals: list[str], payments: list[dict], locations: list[str]) -> str:
    parts: list[str] = [stage.replace("_", " ")]
    if kind and kind != "other":
        parts.append(kind.replace("_", " "))
    if payments:
        parts.append(f"{len(payments)} payment mention(s)")
    if signals:
        parts.append(f"{len(signals)} risk signal(s)")
    if locations:
        parts.append("locations: " + ", ".join(locations[:3]))
    return " | ".join(parts)


def _row_severity(severities: list[str]) -> str:
    rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if not severities:
        return "info"
    return max(severities, key=lambda s: rank.get(str(s).lower(), 0))


def _slug_id(value: str) -> str:
    slug = _re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return slug or "unknown"


def _clean_signal(value: Any, *, fallback: str = "unknown_signal") -> str:
    text = " ".join(str(value or "").strip().split())
    if not text or text in {"?", "??", "unknown", "unknown_rule"}:
        return fallback
    return text


def _build_graph_view(
    *,
    doc_type_counts: dict[str, int],
    person_rows: list[dict],
    journey_points: list[dict],
    risk_signal_counts: dict[str, int],
    folder_counts: dict[str, int],
    evidence_edges: list[dict],
) -> dict:
    """Compact graph contract for the Bulk File Review UI and exports.

    The full bundle remains row-oriented. This graph view is deliberately
    smaller and stable so the browser can render it without a graph library.
    """
    nodes: dict[str, dict] = {
        "bundle": {
            "id": "bundle",
            "label": "Uploaded bundle",
            "group": "root",
            "count": sum(doc_type_counts.values()),
        }
    }
    edges: list[dict] = []

    for dtype, count in sorted(
        doc_type_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )[:10]:
        nid = f"doc:{_slug_id(dtype)}"
        nodes[nid] = {
            "id": nid,
            "label": dtype.replace("_", " "),
            "group": "document_type",
            "count": count,
        }
        edges.append({
            "source": "bundle",
            "target": nid,
            "type": "contains",
            "weight": count,
        })

    for folder, count in sorted(
        folder_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )[:14]:
        nid = f"folder:{_slug_id(folder)}"
        nodes[nid] = {
            "id": nid,
            "label": folder,
            "group": "folder",
            "count": count,
        }
        edges.append({
            "source": "bundle",
            "target": nid,
            "type": "folder_context",
            "weight": count,
        })

    stage_counts: dict[str, int] = {}
    stage_critical: dict[str, int] = {}
    for point in journey_points:
        stage = point.get("stage") or "other_evidence"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        if point.get("is_critical"):
            stage_critical[stage] = stage_critical.get(stage, 0) + 1
    for stage, count in sorted(
        stage_counts.items(),
        key=lambda kv: (_JOURNEY_STAGE_ORDER.get(kv[0], 99), kv[0]),
    ):
        nid = f"stage:{_slug_id(stage)}"
        nodes[nid] = {
            "id": nid,
            "label": stage.replace("_", " "),
            "group": "stage",
            "count": count,
            "critical": stage_critical.get(stage, 0),
        }
        edges.append({
            "source": "bundle",
            "target": nid,
            "type": "journey_stage",
            "weight": count,
        })

    top_signal_names = [
        name for name, _count in sorted(
            risk_signal_counts.items(), key=lambda kv: (-kv[1], kv[0])
        )[:12]
    ]
    for signal in top_signal_names:
        signal = _clean_signal(signal)
        nid = f"signal:{_slug_id(signal)}"
        nodes[nid] = {
            "id": nid,
            "label": signal.replace("_", " "),
            "group": "signal",
            "count": risk_signal_counts.get(signal, 0),
        }
        edges.append({
            "source": "bundle",
            "target": nid,
            "type": "risk_signal",
            "weight": risk_signal_counts.get(signal, 1),
        })

    top_people = person_rows[:18]
    for person in top_people:
        pid = person.get("case_id") or "UNKNOWN"
        nid = f"person:{_slug_id(pid)}"
        nodes[nid] = {
            "id": nid,
            "label": person.get("name") or pid,
            "group": "person",
            "case_id": pid,
            "risk_score": person.get("risk_score", 0),
            "documents": person.get("n_documents", 0),
            "payments": person.get("n_payments", 0),
        }
        edges.append({
            "source": "bundle",
            "target": nid,
            "type": "person",
            "weight": max(1, int(person.get("n_documents") or 1)),
        })
        for signal in (person.get("risk_signals") or [])[:5]:
            signal = _clean_signal(signal)
            if signal not in top_signal_names:
                continue
            edges.append({
                "source": nid,
                "target": f"signal:{_slug_id(signal)}",
                "type": "has_signal",
                "weight": 1,
            })
        for folder in (person.get("folders") or [])[:4]:
            fid = f"folder:{_slug_id(folder)}"
            if fid in nodes:
                edges.append({
                    "source": nid,
                    "target": fid,
                    "type": "filed_under",
                    "weight": 1,
                })

    top_people_ids = {p.get("case_id") for p in top_people}
    for point in journey_points[:80]:
        case_id = point.get("case_id")
        stage = point.get("stage") or "other_evidence"
        if case_id not in top_people_ids:
            continue
        edges.append({
            "source": f"person:{_slug_id(case_id)}",
            "target": f"stage:{_slug_id(stage)}",
            "type": "appears_in_stage",
            "weight": 1,
            "row_id": point.get("row_id"),
        })

    return {
        "schema_version": "duecare.process.graph.v1",
        "nodes": list(nodes.values()),
        "edges": edges[:220],
        "meta": {
            "n_nodes": len(nodes),
            "n_edges": min(len(edges), 220),
            "truncated_edges": len(edges) > 220,
            "top_signal_count": len(top_signal_names),
        },
    }


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
    journey_points: list[dict] = []
    media_assets: list[dict] = []
    parent_docs: dict[str, dict] = {}
    risk_signal_counts: dict[str, int] = {}
    folder_counts: dict[str, int] = {}

    by_row = {r.get("row_id"): r for r in results}
    for row in rows:
        row_id = row.get("row_id") or "row"
        text = row.get("text") or ""
        scored = by_row.get(row_id) or {}
        kind = _file_kind(row_id, text)
        doc_type_counts[kind] = doc_type_counts.get(kind, 0) + 1
        parent_doc = row.get("parent_doc") or row_id
        parent = parent_docs.setdefault(parent_doc, {
            "document_id": parent_doc,
            "source": row.get("source"),
            "source_path": row.get("source_path") or row_id,
            "folders": row.get("folders") or [],
            "folder_context": row.get("folder_context"),
            "chunks": 0,
            "page_indexes": [],
            "document_types": {},
            "media_type": row.get("media_type"),
            "needs_ocr": bool(row.get("needs_ocr")),
        })
        parent["chunks"] += 1
        if row.get("page_index") is not None and row.get("page_index") not in parent["page_indexes"]:
            parent["page_indexes"].append(row.get("page_index"))
        parent["document_types"][kind] = parent["document_types"].get(kind, 0) + 1
        parent["needs_ocr"] = bool(parent.get("needs_ocr") or row.get("needs_ocr"))
        if row.get("needs_ocr"):
            media_assets.append({
                "row_id": row_id,
                "document_id": parent_doc,
                "media_type": row.get("media_type") or ("pdf" if kind == "scanned_pdf" else "image"),
                "bytes": int(row.get("binary_size") or 0),
                "status": "queued_for_ocr_and_multimodal_extraction",
                "source_path": row.get("source_path") or row_id,
                "folders": row.get("folders") or [],
                "folder_context": row.get("folder_context"),
                "recommended_passes": [
                    "OCR or document text extraction",
                    "Gemma 4 multimodal page description",
                    "entity extraction from OCR plus image description",
                    "edge linking into the local graph",
                ],
                "gemma_questions": [
                    "What type of document or screenshot is this page?",
                    "What names, agencies, employers, amounts, dates, and locations are visible?",
                    "Do visual features contradict or confirm the plain-text OCR?",
                    "Which trafficking, fee, document-control, or coercion indicators are visible?",
                ],
            })
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
            "folders": [],
        })
        person["row_ids"].append(row_id)
        person["document_types"][kind] = person["document_types"].get(kind, 0) + 1
        person["name"] = person["name"] or _first_match(_NAME_RE, text)
        person["employer"] = person["employer"] or _first_match(_EMPLOYER_RE, text)
        person["agency"] = person["agency"] or _first_match(_AGENCY_RE, text)
        for folder in row.get("folders") or []:
            folder_counts[folder] = folder_counts.get(folder, 0) + 1
            if folder not in person["folders"]:
                person["folders"].append(folder)
        row_locations: list[str] = []
        row_dates: list[str] = []
        row_payments: list[dict] = []
        row_signals: list[str] = []
        row_severities: list[str] = []

        for loc in _LOCATION_RE.findall(text):
            loc_norm = str(loc).title()
            locations[loc_norm] = locations.get(loc_norm, 0) + 1
            if loc_norm not in person["locations"]:
                person["locations"].append(loc_norm)
            if loc_norm not in row_locations:
                row_locations.append(loc_norm)

        for date in _DATE_RE.findall(text)[:6]:
            item = {"case_id": case_id, "row_id": row_id, "date": date, "document_type": kind}
            timeline.append(item)
            person["timeline"].append(item)
            row_dates.append(date)

        for amt in (scored.get("entities") or {}).get("AMOUNT", []):
            value = _amount_value(amt)
            pay = {"case_id": case_id, "row_id": row_id, "amount": amt, "value": value, "document_type": kind}
            payments.append(pay)
            person["amounts"].append(pay)
            row_payments.append(pay)

        for hit in scored.get("grep_hits") or []:
            severity = (hit.get("severity") or "medium").lower()
            inc = {"critical": 30, "high": 20, "medium": 12, "low": 6}.get(severity, 8)
            person["risk_score"] += inc
            rid = _clean_signal(
                hit.get("rule_id") or hit.get("indicator") or hit.get("category"),
                fallback="grep:" + _slug_id(hit.get("category") or "rule"),
            )
            label = _clean_signal(hit.get("indicator") or rid, fallback=rid)
            if rid not in person["risk_signals"]:
                person["risk_signals"].append(rid)
            if rid not in row_signals:
                row_signals.append(rid)
                risk_signal_counts[rid] = risk_signal_counts.get(rid, 0) + 1
            row_severities.append(severity)
            evidence_edges.append({
                "case_id": case_id,
                "row_id": row_id,
                "rule_id": rid,
                "label": label,
                "severity": severity,
                "document_type": kind,
                "edge_type": "grep_rule",
                "modalities": ["plain_text"],
                "methods": ["grep_rule", "entity_regex", "row_chunk_linking"],
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
            if needle not in lower:
                continue
            if label not in person["risk_signals"]:
                person["risk_score"] += 6
                person["risk_signals"].append(label)
            if label not in row_signals:
                row_signals.append(label)
                risk_signal_counts[label] = risk_signal_counts.get(label, 0) + 1
                evidence_edges.append({
                    "case_id": case_id,
                    "row_id": row_id,
                    "rule_id": "keyword:" + _slug_id(label),
                    "label": label,
                    "severity": "medium",
                    "document_type": kind,
                    "edge_type": "keyword_signal",
                    "modalities": ["plain_text"],
                    "methods": ["keyword_signal", "entity_regex", "row_chunk_linking"],
                })

        folder_context = row.get("folder_context")
        if folder_context:
            evidence_edges.append({
                "case_id": case_id,
                "row_id": row_id,
                "rule_id": "folder_context:" + _slug_id(folder_context),
                "label": str(folder_context),
                "severity": "info",
                "document_type": kind,
                "edge_type": "folder_context",
                "source_path": row.get("source_path") or row_id,
                "modalities": ["file_structure"],
                "methods": ["zip_inventory", "folder_path_context"],
            })

        stage = _journey_stage(row_id, text, kind)
        if row_signals or row_payments or kind != "other":
            journey_points.append({
                "stage": stage,
                "stage_order": _JOURNEY_STAGE_ORDER.get(stage, 99),
                "case_id": case_id,
                "row_id": row_id,
                "document_type": kind,
                "date": row_dates[0] if row_dates else None,
                "locations": row_locations[:6],
                "payments": row_payments[:6],
                "risk_signals": row_signals[:8],
                "severity": _row_severity(row_severities),
                "summary": _journey_summary(stage, kind, row_signals, row_payments, row_locations),
                "is_critical": bool(row_payments or any(s in {"critical", "high"} for s in row_severities)),
            })

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
            "folders": (p.get("folders") or [])[:12],
        })
    person_rows.sort(key=lambda p: (-p.get("risk_score", 0), p.get("case_id", "")))
    timeline.sort(key=lambda x: str(x.get("date", "")))
    payments.sort(key=lambda x: -float(x.get("value") or 0))
    journey_points.sort(key=lambda x: (
        x.get("stage_order", 99),
        str(x.get("date") or "9999"),
        x.get("case_id", ""),
        x.get("row_id", ""),
    ))
    critical_fee_points = [
        {
            "stage": p.get("stage"),
            "case_id": p.get("case_id"),
            "row_id": p.get("row_id"),
            "date": p.get("date"),
            "document_type": p.get("document_type"),
            "payments": p.get("payments", []),
            "risk_signals": p.get("risk_signals", []),
            "summary": p.get("summary"),
        }
        for p in journey_points
        if p.get("payments")
    ][:30]
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
    parent_document_rows = []
    for doc in parent_docs.values():
        pages = sorted(int(x) for x in doc.get("page_indexes", []) if x is not None)
        row = {k: v for k, v in doc.items() if k != "page_indexes"}
        row["n_pages"] = len(pages)
        row["page_indexes"] = pages[:60]
        parent_document_rows.append(row)

    cleaned_signal_counts: dict[str, int] = {}
    for key, count in risk_signal_counts.items():
        clean = _clean_signal(key)
        if clean == "unknown_signal":
            continue
        cleaned_signal_counts[clean] = cleaned_signal_counts.get(clean, 0) + count
    top_risk_signals = [
        {"signal": k, "count": v}
        for k, v in sorted(cleaned_signal_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    ]
    graph = _build_graph_view(
        doc_type_counts=doc_type_counts,
        person_rows=person_rows,
        journey_points=journey_points,
        risk_signal_counts=cleaned_signal_counts,
        folder_counts=folder_counts,
        evidence_edges=evidence_edges,
    )

    processing_plan = {
        "schema_version": "duecare.process.processing_plan.v1",
        "n_parent_documents": len(parent_docs),
        "n_pages": sum(int(d.get("n_pages") or 0) for d in parent_document_rows),
        "n_chunks": len(rows),
        "n_media_assets": len(media_assets),
        "chunk_chars": _CHUNK_CHARS,
        "analysis_methods": [
            {
                "id": "plain_text",
                "label": "Plain-text extraction",
                "detail": "Text, CSV, JSONL, markdown, logs, and extractable PDF pages are chunked locally and scanned.",
            },
            {
                "id": "file_structure",
                "label": "File and folder structure",
                "detail": "ZIP paths and folder names are preserved as graph edges because case folders are often named by client, agency, stage, or source.",
            },
            {
                "id": "investigative_search",
                "label": "Investigative document search",
                "detail": "The contract mirrors common e-discovery and investigative review patterns: inventory, OCR queue, entity extraction, link analysis, timeline, and graph chat.",
            },
            {
                "id": "gemma_page_questions",
                "label": "Gemma 4 page-question pass",
                "detail": "Each queued image, scan, or PDF page carries standard questions for document identification, visible entities, visual/text agreement, and trafficking indicators.",
            },
        ],
        "passes": [
            {
                "id": "inventory",
                "label": "Document inventory",
                "status": "implemented",
                "detail": "ZIP, CSV, JSONL, text, PDF, and image assets are enumerated locally.",
            },
            {
                "id": "chunking",
                "label": "Document and page chunking",
                "status": "implemented_for_text_and_extractable_pdfs",
                "detail": f"Text files and extractable PDF pages are split into chunks of about {_CHUNK_CHARS} characters; scanned pages and images become media work items.",
            },
            {
                "id": "ocr",
                "label": "OCR and layout extraction",
                "status": "queued_contract",
                "detail": "Media assets are detected and queued; OCR engine wiring is the next implementation step.",
            },
            {
                "id": "gemma_multimodal",
                "label": "Gemma 4 multimodal extraction",
                "status": "queued_contract",
                "detail": "Each media asset needs a Gemma vision pass over image plus OCR text to extract entities and edges.",
            },
            {
                "id": "entity_resolution",
                "label": "Entity resolution and edge linking",
                "status": "implemented_basic",
                "detail": "Case IDs, people, agencies, employers, amounts, locations, dates, rule hits, and journey stages are linked deterministically.",
            },
            {
                "id": "review_loop",
                "label": "Iterative reviewer loop",
                "status": "implemented_basic",
                "detail": "Graph chat asks Gemma questions over the local graph; unresolved OCR/media work remains visible.",
            },
        ],
        "media_assets": media_assets[:80],
        "parent_documents": parent_document_rows[:120],
    }
    return {
        "version": "process-intelligence-v1",
        "n_people": len([p for p in person_rows if p.get("case_id") != "UNKNOWN"]),
        "n_documents": len(rows),
        "n_evidence_edges": len(evidence_edges),
        "document_type_counts": doc_type_counts,
        "folder_counts": [
            {"folder": k, "count": v}
            for k, v in sorted(folder_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:30]
        ],
        "people": person_rows,
        "hierarchy": hierarchy,
        "top_payments": payments[:20],
        "top_risk_signals": top_risk_signals,
        "timeline": timeline[:40],
        "locations": [{"name": k, "count": v} for k, v in sorted(locations.items(), key=lambda kv: (-kv[1], kv[0]))[:20]],
        "evidence_edges": evidence_edges[:80],
        "graph": graph,
        "journey_points": journey_points[:120],
        "critical_fee_points": critical_fee_points,
        "processing_plan": processing_plan,
    }


def _deterministic_case_brief(bundle: dict, intelligence: dict) -> dict:
    people = (intelligence.get("people") or [])[:10]
    top_people = [
        {
            "case_id": p.get("case_id"),
            "name": p.get("name"),
            "risk_score": p.get("risk_score"),
            "total_payment_value": p.get("total_payment_value"),
            "signals": (p.get("risk_signals") or [])[:5],
            "row_ids": (p.get("row_ids") or [])[:5],
        }
        for p in people[:6]
    ]
    signals = intelligence.get("top_risk_signals") or []
    media = ((intelligence.get("processing_plan") or {}).get("media_assets") or [])
    return {
        "case_theory": (
            "The bundle shows a PH to HK recruitment pattern with worker-paid "
            "fees, salary-deduction repayment, debt indicators, and document "
            "control signals. The deterministic graph should be reviewed before "
            "any escalation because it preserves row IDs, folder-derived context, "
            "and media items still queued for OCR or Gemma 4 vision review."
        ),
        "priority_people": top_people,
        "risk_clusters": [
            f"{s.get('signal')} x {s.get('count')}" for s in signals[:8]
        ],
        "missing_evidence": [
            "OCR text and Gemma 4 vision extraction for queued media assets",
            "original employment contracts and side letters",
            "proof of payment recipient, account, wallet, or remittance trail",
            "agency, employer, and broker identifiers across folders",
            "complaint status and any retaliation evidence",
        ],
        "recommended_questions": [
            "Which people have the highest total payment demands?",
            "Which folders or agencies connect multiple cases?",
            "Which media assets still require OCR or Gemma 4 page review?",
            "Which cases share the same fee pattern and could be grouped?",
        ],
        "media_assets_queued": len(media),
    }


def _gemma_case_brief(app: Any, bundle: dict, intelligence: dict) -> dict:
    gc = getattr(app.state, "gemma_call", None)
    deterministic = _deterministic_case_brief(bundle, intelligence)
    if gc is None:
        return {
            "available": False,
            "status": "deterministic_no_model",
            "json": deterministic,
            "text": _json.dumps(deterministic, indent=2),
        }
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
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        try:
            model_out = gc(messages, max_new_tokens=700, temperature=0.2)
        except TypeError:
            model_out = gc(messages)
        text = model_out if isinstance(model_out, str) else (
            (model_out or {}).get("text") or (model_out or {}).get("response") or ""
        )
        text = sanitize_model_output(text)
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
            "json": parsed or deterministic,
            "prompt_chars": len(prompt),
        }
    except Exception as exc:
        return {
            "available": True,
            "status": "model_error_deterministic_fallback",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "json": deterministic,
            "text": _json.dumps(deterministic, indent=2),
        }


def _parse_upload(filename: str, contents: bytes) -> list[dict]:
    fname_l = filename.lower()
    rows: list[dict] = []
    if fname_l.endswith(".zip"):
        with zipfile.ZipFile(_io.BytesIO(contents)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                data = zf.read(name)
                if _ext(name) == ".pdf":
                    pdf_rows = _try_pdf_text_rows(name, data, filename)
                    if pdf_rows:
                        rows.extend(pdf_rows)
                        continue
                    rows.append(_media_row(name, data, filename))
                    continue
                if not _is_probably_text(name, data):
                    rows.append(_media_row(name, data, filename))
                    continue
                try:
                    txt = data.decode("utf-8", errors="replace")
                except Exception:
                    continue
                rows.extend(_chunk_text_rows(name, txt, filename))
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
            row_id = f"line_{i}"
            rows.append({
                "row_id": row_id,
                "text": txt,
                "source": filename,
                **_path_metadata(row_id),
            })
    elif fname_l.endswith(".csv"):
        buf = _io.StringIO(contents.decode("utf-8", errors="replace"))
        reader = _csv.reader(buf)
        all_rows = list(reader)
        headers = [str(h or "").strip() for h in (all_rows[0] if all_rows else [])]
        start = 1 if headers else 0
        for i, row in enumerate(all_rows[start:]):
            if not row:
                continue
            if headers:
                parts = []
                for idx, value in enumerate(row):
                    header = headers[idx] if idx < len(headers) and headers[idx] else f"col_{idx + 1}"
                    parts.append(f"{header}: {value}")
                txt = "; ".join(parts)
            else:
                txt = ", ".join(str(v) for v in row)
            row_id = f"row_{i}"
            rows.append({
                "row_id": row_id,
                "text": txt,
                "source": filename,
                **_path_metadata(row_id),
            })
    else:
        if _ext(filename) == ".pdf":
            pdf_rows = _try_pdf_text_rows(filename, contents, filename)
            if pdf_rows:
                return pdf_rows
            rows.append(_media_row(filename, contents, filename))
            return rows
        if not _is_probably_text(filename, contents):
            rows.append(_media_row(filename, contents, filename))
            return rows
        blob = contents.decode("utf-8", errors="replace")
        for i, chunk in enumerate([c for c in blob.split("\n\n") if c.strip()]):
            rows.extend(_chunk_text_rows(f"chunk_{i}", chunk, filename))
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
                    rid = h.get("rule_id") or h.get("id") or h.get("rule") or "unknown_rule"
                    grep_hits.append({
                        "rule_id": rid,
                        "indicator": h.get("indicator") or h.get("description") or rid,
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


def _format_money(value: float) -> str:
    return f"PHP {int(value):,}" if value else "not quantified"


def _person_support_rows(person: dict, limit: int = 4) -> list[str]:
    rows = person.get("row_ids") or []
    priority = [
        r for r in rows
        if any(part in str(r).lower() for part in ("payment", "complaint", "chat"))
    ]
    merged = list(dict.fromkeys(priority + rows))
    return [str(r) for r in merged[:limit]]


def _looks_like_reasoning_leak(text: str) -> bool:
    """Detect plain-language scratchpad leakage from a graph-chat model.

    The normal model-output sanitizer removes Gemma template tokens and
    explicit <think> blocks. Some runtimes still emit natural-language
    planning such as "The user is asking..." without a template marker.
    Process graph chat is an evidence-review surface, so a deterministic
    brief is preferable to exposing scratchpad text.
    """
    stripped = (text or "").strip().lower()
    if not stripped:
        return False
    starts_like_scratchpad = stripped.startswith((
        "the user is asking",
        "we need to answer",
        "i need to answer",
        "i need to look",
        "let's analyze",
        "let us analyze",
    ))
    if not starts_like_scratchpad:
        return False
    planning_markers = (
        "identify relevant information",
        "scan the summary",
        "scan the grounding",
        "examine critical",
        "based only on the provided",
        "i should",
    )
    return any(marker in stripped for marker in planning_markers)


def _graph_chat_deterministic_answer(bundle: dict, question: str) -> dict | None:
    """Answer common investigative graph questions without model drift.

    Gemma is useful for synthesis, but ranking fees, citing row IDs, listing
    queued media, and grouping repeated patterns should be computed directly
    from the graph so the page behaves like a document review tool.
    """
    q = (question or "").lower()
    intelligence = bundle.get("intelligence") or {}
    people = intelligence.get("people") or []
    summary = bundle.get("summary") or {}
    cited_rows: list[str] = []

    def add_rows(rows: list[str]) -> None:
        for row in rows:
            if row and row not in cited_rows:
                cited_rows.append(row)

    wants_fee = any(k in q for k in (
        "fee", "overcharg", "payment", "salary deduction", "legal cap",
        "placement", "charged", "debt",
    ))
    wants_strongest = any(k in q for k in (
        "strongest", "move forward", "priority", "prioritize", "rank",
    ))
    wants_group = any(k in q for k in (
        "class action", "group", "grouped", "same pattern", "common",
        "cluster", "collective",
    ))
    wants_folder = any(k in q for k in (
        "folder", "file structure", "path", "directory", "client",
    ))
    wants_media = any(k in q for k in (
        "media", "ocr", "image", "scan", "pdf", "photo", "screenshot",
        "vision",
    ))
    wants_missing = any(k in q for k in (
        "missing evidence", "missing", "strengthen", "next evidence",
    ))

    if wants_media:
        media = ((intelligence.get("processing_plan") or {}).get("media_assets") or [])
        if not media:
            return {
                "answer": (
                    "No queued image, scan, or PDF media assets were found in "
                    "the processed rows. That means this bundle is currently "
                    "being analyzed through plain text, CSV, JSONL, extractable "
                    "PDF text, and folder-path evidence only."
                ),
                "cited_rows": [],
                "analysis_kind": "media_queue",
            }
        lines = [
            "Queued OCR and Gemma 4 vision review items:",
            "",
        ]
        for idx, asset in enumerate(media[:12], start=1):
            rid = str(asset.get("row_id") or "")
            add_rows([rid])
            questions = "; ".join((asset.get("gemma_questions") or [])[:2])
            lines.append(
                f"{idx}. `{rid}` | type: {asset.get('media_type')} | "
                f"source: {asset.get('source_path') or rid} | questions: {questions}"
            )
        lines.append("")
        lines.append(
            "Review order: run OCR first, ask Gemma 4 to identify document type "
            "and visible entities, then reconcile image findings with row IDs, "
            "payments, folders, and person nodes."
        )
        return {
            "answer": "\n".join(lines),
            "cited_rows": cited_rows,
            "analysis_kind": "media_queue",
        }

    if wants_folder:
        folders = intelligence.get("folder_counts") or []
        lines = [
            "Folder and file-structure evidence:",
            "",
        ]
        for item in folders[:12]:
            folder = str(item.get("folder") or "")
            reason = (
                "Potential source, client, stage, agency, or evidence-type label "
                "from the original ZIP path."
            )
            lines.append(
                f"- folder: `{folder}` | rows: {item.get('count')} | why: {reason}"
            )
        edges = [
            e for e in (intelligence.get("evidence_edges") or [])
            if e.get("edge_type") == "folder_context"
        ][:8]
        if edges:
            lines.append("")
            lines.append("Example folder-derived row links:")
            for edge in edges:
                row = str(edge.get("row_id") or "")
                add_rows([row])
                lines.append(
                    f"- `{edge.get('case_id')}` linked to folder "
                    f"`{edge.get('label')}` via `{row}`"
                )
        return {
            "answer": "\n".join(lines),
            "cited_rows": cited_rows,
            "analysis_kind": "folder_structure",
        }

    if wants_group:
        signal_groups: dict[str, list[dict]] = {}
        for person in people:
            for signal in (person.get("risk_signals") or [])[:8]:
                signal_groups.setdefault(str(signal), []).append(person)
        ranked = sorted(
            signal_groups.items(),
            key=lambda kv: (-len(kv[1]), kv[0]),
        )[:6]
        lines = [
            "Potential grouped or pattern-case candidates:",
            "",
        ]
        for signal, members in ranked:
            rows: list[str] = []
            for person in members[:5]:
                rows.extend(_person_support_rows(person, limit=2))
            rows = list(dict.fromkeys(rows))[:8]
            add_rows(rows)
            lines.append(
                f"- shared pattern: {signal} | people: {len(members)} | support rows: "
                + ", ".join(f"`{r}`" for r in rows)
            )
        lines.append("")
        lines.append(
            "These are investigative groupings, not legal conclusions. A reviewer "
            "should confirm common agency, employer, fee recipient, contract form, "
            "and retaliation pattern before treating cases as one coordinated matter."
        )
        return {
            "answer": "\n".join(lines),
            "cited_rows": cited_rows,
            "analysis_kind": "pattern_grouping",
        }

    if wants_fee or wants_strongest:
        ranked_people = sorted(
            people,
            key=lambda p: (
                -float(p.get("total_payment_value") or 0),
                -int(p.get("risk_score") or 0),
                str(p.get("case_id") or ""),
            ),
        )[:10]
        title = (
            "Strongest cases to move forward first"
            if wants_strongest else
            "People with strongest overcharging or placement-fee evidence"
        )
        lines = [
            title + ":",
            "",
        ]
        for idx, person in enumerate(ranked_people, start=1):
            rows = _person_support_rows(person)
            add_rows(rows)
            signals = ", ".join((person.get("risk_signals") or [])[:5])
            label = person.get("name") or person.get("case_id")
            lines.append(
                f"{idx}. {label} (`{person.get('case_id')}`) | "
                f"payments found: {_format_money(float(person.get('total_payment_value') or 0))} | "
                f"risk: {person.get('risk_score')} | signals: {signals} | support rows: "
                + ", ".join(f"`{r}`" for r in rows)
            )
        lines.append("")
        lines.append(
            "Why these rank high: the graph combines payment amounts, row-level "
            "risk signals, document types, and person-level linked records. For "
            "PH to HK domestic-worker scenarios, any worker-paid placement, "
            "training, medical, or repayment fee should be checked against the "
            "zero-fee rule and wage-deduction restrictions."
        )
        if wants_missing:
            lines.append("")
            lines.append(
                "Missing evidence to strengthen review: original receipts, payment "
                "recipient identity, agency license records, employment contract, "
                "screenshots with timestamps, passport-control evidence, complaint "
                "status, and any retaliation messages."
            )
        return {
            "answer": "\n".join(lines),
            "cited_rows": cited_rows,
            "analysis_kind": "fee_or_priority_ranking",
        }

    if wants_missing:
        media_count = ((intelligence.get("processing_plan") or {})
                       .get("n_media_assets", 0))
        answer = (
            "Evidence that would strengthen this bundle before escalation:\n\n"
            "1. Original receipts or transfer records showing fee recipient and date.\n"
            "2. Agency, broker, employer, and payment-account identifiers.\n"
            "3. Employment contract, side letter, and any replacement contract.\n"
            "4. Screenshots with timestamps and sender handles.\n"
            "5. Passport or identity-document custody evidence.\n"
            "6. Complaint filings, case numbers, and retaliation messages.\n"
            f"7. OCR and Gemma 4 vision review for queued media assets: {media_count}."
        )
        return {
            "answer": answer,
            "cited_rows": [],
            "analysis_kind": "missing_evidence",
        }

    return None


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
                "Upload a ZIP/CSV/JSONL on the Bulk File Review page first, then "
                "ask the question again.",
                "bundle_present": False,
                "cited_rows": [],
                "grep_hits": 0,
            })

        deterministic = _graph_chat_deterministic_answer(bundle, question)
        if deterministic is not None:
            summary = bundle.get("summary") or {}
            cited = deterministic.get("cited_rows") or []
            try:
                from .._training_log import log_interaction as _log
                _log(
                    "process",
                    input_payload={"question": question, "bundle_run_id": bundle.get("run_id")},
                    output_payload=deterministic.get("answer", ""),
                    applied_layers={"graph_analyst": {"fired": True}},
                    trace={
                        "cited_rows": cited,
                        "analysis_kind": deterministic.get("analysis_kind"),
                    },
                    extra={"kind": "graph_chat"},
                )
            except Exception:
                pass
            return JSONResponse({
                "answer": deterministic.get("answer", ""),
                "bundle_present": True,
                "cited_rows": cited[:30],
                "grep_hits": summary.get("n_grep_rules_fired", 0),
                "evidence_edges": (bundle.get("summary") or {}).get("n_evidence_edges", 0),
                "analysis_kind": deterministic.get("analysis_kind"),
                "applied_layers": {"graph_analyst": {"fired": True}},
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
            response_text = sanitize_model_output(response_text)
            if _looks_like_reasoning_leak(response_text):
                fallback = _deterministic_case_brief(bundle, bundle.get("intelligence") or {})
                return JSONResponse({
                    "answer": (
                        "The model returned scratchpad-style reasoning, so I am "
                        "suppressing it and returning the deterministic case-graph "
                        "brief instead.\n\n"
                        + _json.dumps(fallback, indent=2)
                    ),
                    "bundle_present": True,
                    "cited_rows": [],
                    "grep_hits": (bundle.get("summary") or {}).get("n_grep_rules_fired", 0),
                    "fallback": "reasoning_leak_suppressed",
                    "evidence_edges": (bundle.get("summary") or {}).get("n_evidence_edges", 0),
                })
        except Exception as e:
            fallback = _deterministic_case_brief(bundle, bundle.get("intelligence") or {})
            return JSONResponse({
                "answer": (
                    "Gemma graph-chat failed, so I am returning the deterministic "
                    "case-graph brief instead.\n\n"
                    + _json.dumps(fallback, indent=2)
                ),
                "bundle_present": True,
                "cited_rows": [],
                "grep_hits": (bundle.get("summary") or {}).get("n_grep_rules_fired", 0),
                "fallback": "model_error_deterministic_brief",
                "error": f"{type(e).__name__}: {e}"[:240],
            })

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
