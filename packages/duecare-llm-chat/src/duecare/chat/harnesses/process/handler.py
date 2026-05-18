"""Bulk File Review harness handler.

Owns:
  - POST /api/process/batch: multipart upload to v1.0 bundle envelope
  - POST /api/process/graph-chat: Gemma 4 query over the last bundle
"""
from __future__ import annotations

import csv as _csv
import hashlib as _hashlib
import io as _io
import json as _json
import os as _os
import re as _re
import threading as _threading
import zipfile
import xml.etree.ElementTree as _ET
from datetime import UTC as _UTC, datetime as _dt
from pathlib import Path as _Path
from typing import Any
from uuid import uuid4 as _uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..._model_output import sanitize_model_output
from .._replay import demo_replay
from .extractor import ENTITY_PATTERNS
from .prompts import (
    EDGE_EXTRACTION_POINTED_QUESTIONS,
    EDGE_QUALITY_DIMENSIONS,
    GRAPH_CHAT_SYSTEM_PROMPT,
    GRAPH_EDGE_EXTRACTION_SYSTEM_PROMPT,
    GRAPH_EDGE_PROMPT_TEMPLATES,
    PAGE_ITEM_PROMPT_TREE,
    build_context_block,
    build_graph_edge_extraction_prompt,
)


_ROW_CAP = 300
_TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".jsonl", ".log", ".rtf", ".html", ".htm", ".eml"}
_MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
_SPREADSHEET_EXTS = {".xlsx"}
_OFFICE_DOC_EXTS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".msg"}
_DOC_IMAGE_EXTS = _MEDIA_EXTS | {".pdf"} | _OFFICE_DOC_EXTS
_CHUNK_CHARS = 4500
_PROCESS_REVIEW_MODES: dict[str, dict[str, Any]] = {
    "quick_triage": {
        "id": "quick_triage",
        "label": "Quick triage",
        "runtime_budget_minutes": 5,
        "max_gemma_calls": 20,
        "gemma_calls_per_item": 1,
        "edge_strictness": "conservative",
        "routing": "deterministic_all_items_gemma_high_risk_only",
        "description": "Fast first pass for very large uploads. Deterministic extraction runs everywhere; Gemma is reserved for highest-risk items and repeated entities.",
    },
    "standard_review": {
        "id": "standard_review",
        "label": "Standard review",
        "runtime_budget_minutes": 15,
        "max_gemma_calls": 75,
        "gemma_calls_per_item": 1,
        "edge_strictness": "balanced",
        "routing": "classify_all_items_gemma_high_signal_and_media",
        "description": "Recommended default. OCR/layout and deterministic edges run broadly; Gemma reviews high-signal text, media, receipts, chats, contracts, and repeated clusters.",
    },
    "exhaustive_review": {
        "id": "exhaustive_review",
        "label": "Exhaustive review",
        "runtime_budget_minutes": 60,
        "max_gemma_calls": 240,
        "gemma_calls_per_item": 2,
        "edge_strictness": "exploratory",
        "routing": "classify_and_target_every_page_item_with_budget",
        "description": "Deep local review for smaller bundles or final case prep. Gemma can run multiple targeted prompts per page item until the local budget is exhausted.",
    },
}
_DEFAULT_PAGE_ITEM_TYPES = [
    "text_block",
    "table",
    "image_or_screenshot",
    "receipt",
    "contract_or_form",
    "signature_or_stamp",
    "audio_segment",
    "video_frame_or_scene",
]
_MODEL_CAPABILITY_NOTES: list[dict[str, Any]] = [
    {
        "capability": "deterministic_processing",
        "status": "available_without_model",
        "detail": "Archive inventory, text extraction, GREP, entity regex, folder edges, journey mapping, typed deterministic edges, and media queueing do not require Gemma.",
    },
    {
        "capability": "text_edge_pass",
        "status": "works_with_small_text_models",
        "detail": "Smaller local Gemma text models can propose text-grounded typed edges and RAG candidates, but use conservative budgets and expect more reviewer validation on long or messy bundles.",
    },
    {
        "capability": "multimodal_page_review",
        "status": "requires_multimodal_support_and_local_preprocessing",
        "detail": "Image, scan, audio, and video edge extraction requires local OCR/layout/ASR and a model/runtime that can consume the relevant media or rendered page context.",
    },
    {
        "capability": "exhaustive_review",
        "status": "larger_or_more_capable_models_recommended",
        "detail": "Exhaustive multi-prompt review over many page items can be slow or low-quality on smaller models; use Quick or Standard mode when runtime or memory is constrained.",
    },
    {
        "capability": "finetuned_document_classifier",
        "status": "recommended_for_quality_when_available",
        "detail": "A fine-tuned Gemma 4 adapter trained on reviewed document classification and graph-edge examples can improve page-item routing, edge typing, and cross-document linking while keeping the same local-only review contract.",
    },
]
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


def _process_staging_root() -> _Path | None:
    """Return a writable staging directory for uploaded process bundles."""
    for root in (_Path("/kaggle/working/process-staging"), _Path(".duecare-process-staging")):
        try:
            root.mkdir(parents=True, exist_ok=True)
            return root
        except Exception:
            continue
    return None


def _safe_stage_name(name: str) -> str:
    base = _re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "uploaded").strip())
    return (base[:120] or "uploaded").strip("._") or "uploaded"


def _stage_upload(filename: str, contents: bytes, run_id: str) -> dict:
    """Persist the uploaded archive so the UI can truthfully report staging."""
    root = _process_staging_root()
    digest = _hashlib.sha256(contents).hexdigest()
    out = {
        "saved": False,
        "root": str(root) if root else None,
        "filename": filename,
        "bytes": len(contents),
        "sha256": digest,
    }
    if root is None:
        out["error"] = "no writable process-staging directory"
        return out
    try:
        run_dir = root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / _safe_stage_name(filename)
        path.write_bytes(contents)
        out.update({"saved": True, "path": str(path)})
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:240]
    return out


def _process_mode(mode_id: str | None = None) -> dict[str, Any]:
    mode = _PROCESS_REVIEW_MODES.get(str(mode_id or "").strip()) or _PROCESS_REVIEW_MODES["standard_review"]
    return dict(mode)


def _int_setting(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        out = int(value)
    except Exception:
        out = default
    return max(minimum, min(maximum, out))


def _bool_setting(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "checked"}


def _parse_json_list(value: Any, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, list):
        raw = value
    else:
        try:
            raw = _json.loads(str(value))
        except Exception:
            raw = str(value).split(",")
    out: list[str] = []
    for item in raw:
        text = _slug_id(str(item or ""))
        if text and text not in out:
            out.append(text)
    return out or list(default)


def _process_settings_from_mapping(data: Any | None = None) -> dict[str, Any]:
    data = data or {}
    mode = _process_mode(data.get("review_mode") or data.get("mode"))
    page_item_types = _parse_json_list(data.get("page_item_types"), _DEFAULT_PAGE_ITEM_TYPES)
    runtime_default = int(mode.get("runtime_budget_minutes") or 15)
    calls_default = int(mode.get("max_gemma_calls") or 75)
    per_item_default = int(mode.get("gemma_calls_per_item") or 1)
    max_gemma_calls = _int_setting(
        data.get("max_gemma_calls"),
        calls_default,
        minimum=0,
        maximum=1000,
    )
    gemma_calls_per_item = _int_setting(
        data.get("gemma_calls_per_item"),
        per_item_default,
        minimum=0,
        maximum=5,
    )
    strictness = str(data.get("edge_strictness") or mode.get("edge_strictness") or "balanced")
    if strictness not in {"conservative", "balanced", "exploratory"}:
        strictness = str(mode.get("edge_strictness") or "balanced")
    return {
        "schema_version": "duecare.process.settings.v1",
        "review_mode": mode,
        "runtime_budget_minutes": _int_setting(
            data.get("runtime_budget_minutes"),
            runtime_default,
            minimum=1,
            maximum=240,
        ),
        "max_gemma_calls": max_gemma_calls,
        "gemma_calls_per_item": gemma_calls_per_item,
        "run_inline_gemma_text": _bool_setting(
            data.get("run_inline_gemma_text"),
            bool(max_gemma_calls > 0 and gemma_calls_per_item > 0),
        ),
        "edge_strictness": strictness,
        "generate_knowledge_candidates": _bool_setting(
            data.get("generate_knowledge_candidates"),
            True,
        ),
        "include_imported_knowledge": _bool_setting(
            data.get("include_imported_knowledge"),
            True,
        ),
        "page_item_types": page_item_types,
        "advanced_open_by_default": False,
    }


def _process_settings_from_form(form: Any) -> dict[str, Any]:
    return _process_settings_from_mapping({
        "review_mode": form.get("review_mode"),
        "runtime_budget_minutes": form.get("runtime_budget_minutes"),
        "max_gemma_calls": form.get("max_gemma_calls"),
        "gemma_calls_per_item": form.get("gemma_calls_per_item"),
        "run_inline_gemma_text": form.get("run_inline_gemma_text"),
        "edge_strictness": form.get("edge_strictness"),
        "generate_knowledge_candidates": form.get("generate_knowledge_candidates"),
        "include_imported_knowledge": form.get("include_imported_knowledge"),
        "page_item_types": form.get("page_item_types"),
    })


def _knowledge_roots_for_process() -> list[_Path]:
    roots: list[_Path] = []
    env_root = _os.getenv("DUECARE_KNOWLEDGE_ROOT")
    if env_root:
        roots.append(_Path(env_root))
    roots.extend((_Path("/kaggle/working/knowledge"), _Path(".") / ".duecare-knowledge"))
    return roots


def _load_local_knowledge_context(limit: int = 24) -> dict[str, Any]:
    """Read imported/promoted KnowledgeObject envelopes for local Gemma context."""
    objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in _knowledge_roots_for_process():
        if not root.exists():
            continue
        for path in sorted(root.glob("*/*.json")):
            if len(objects) >= limit:
                break
            try:
                env = _json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            ko_type = str(env.get("knowledge_object_type") or path.parent.name)
            ko_id = str(env.get("id") or path.stem)
            key = f"{ko_type}/{ko_id}"
            if key in seen:
                continue
            seen.add(key)
            content = env.get("content") or {}
            summary = ""
            if isinstance(content, dict):
                for candidate_key in ("title", "label", "description", "text", "pattern", "name"):
                    val = content.get(candidate_key)
                    if val:
                        summary = " ".join(str(val).split())[:360]
                        break
                if not summary:
                    summary = _json.dumps(content, ensure_ascii=False)[:360]
            objects.append({
                "type": ko_type,
                "id": ko_id,
                "version": env.get("version"),
                "summary": summary,
                "tags": env.get("tags") or [],
                "path": str(path),
                "last_verified_at": (env.get("provenance") or {}).get("last_verified_at")
                    or (env.get("extensions") or {}).get("last_verified_at"),
            })
        if len(objects) >= limit:
            break
    by_type: dict[str, int] = {}
    for obj in objects:
        by_type[obj["type"]] = by_type.get(obj["type"], 0) + 1
    return {
        "schema_version": "duecare.process.knowledge_context.v1",
        "local_only": True,
        "sources": [str(root) for root in _knowledge_roots_for_process()],
        "n_objects": len(objects),
        "by_type": by_type,
        "objects": objects,
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
        ("complaint", ("complaints/", "intake/", "intake_forms/", "forms/")),
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


def _rtf_to_text(text: str) -> str:
    """Best-effort RTF cleanup for legacy Word exports saved as RTF/.doc."""
    clean = _re.sub(r"\\'[0-9a-fA-F]{2}", " ", text or "")
    clean = _re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", clean)
    clean = clean.replace("{", " ").replace("}", " ")
    return "\n".join(line.strip() for line in clean.splitlines() if line.strip())


def _markup_to_text(text: str) -> str:
    clean = _re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text or "")
    clean = _re.sub(r"(?is)<br\s*/?>", "\n", clean)
    clean = _re.sub(r"(?is)</p\s*>", "\n", clean)
    clean = _re.sub(r"(?is)<[^>]+>", " ", clean)
    clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return "\n".join(" ".join(line.split()) for line in clean.splitlines() if line.strip())


def _decode_documentish_text(name: str, data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    ext = _ext(name)
    if ext in {".rtf", ".doc"} and text.lstrip().startswith("{\\rtf"):
        return _rtf_to_text(text)
    if ext in {".html", ".htm"}:
        return _markup_to_text(text)
    return text


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


def _try_docx_text_rows(name: str, data: bytes, source: str) -> list[dict]:
    """Extract paragraph text from a DOCX without adding a heavyweight dependency."""
    try:
        with zipfile.ZipFile(_io.BytesIO(data)) as zf:
            document_xml = zf.read("word/document.xml")
    except Exception:
        return []

    try:
        root = _ET.fromstring(document_xml)
    except Exception:
        return []

    paragraphs: list[str] = []
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for para in root.iter(f"{ns}p"):
        parts = [node.text or "" for node in para.iter(f"{ns}t")]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)

    if paragraphs:
        text = "\n".join(paragraphs)
    else:
        text = " ".join(t.strip() for t in root.itertext() if str(t).strip())
    if not text.strip():
        return []
    return _chunk_text_rows(name, text, source, parent_doc=name)


def _try_legacy_doc_text_rows(name: str, data: bytes, source: str) -> list[dict]:
    """Parse RTF/text-backed .doc exports; queue true binary .doc files."""
    if data.lstrip().startswith(b"{\\rtf"):
        text = _rtf_to_text(data.decode("utf-8", errors="replace"))
    elif _is_probably_text(name + ".txt", data):
        text = data.decode("utf-8", errors="replace")
    else:
        return []
    if not text.strip():
        return []
    return _chunk_text_rows(name, text, source, parent_doc=name)


def _try_xlsx_text_rows(name: str, data: bytes, source: str) -> list[dict]:
    """Extract visible cell values from simple XLSX workbooks without openpyxl."""
    try:
        with zipfile.ZipFile(_io.BytesIO(data)) as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                root = _ET.fromstring(zf.read("xl/sharedStrings.xml"))
                ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                for item in root.iter(f"{ns}si"):
                    shared.append("".join(t.text or "" for t in item.iter(f"{ns}t")))
            sheet_names = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml"))
            sheet_text: list[str] = []
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            for sheet_index, sheet_name in enumerate(sheet_names, start=1):
                root = _ET.fromstring(zf.read(sheet_name))
                sheet_text.append(f"sheet_{sheet_index}: {sheet_name}")
                for row in root.iter(f"{ns}row"):
                    cells: list[str] = []
                    for cell in row.iter(f"{ns}c"):
                        ref = cell.attrib.get("r", "cell")
                        value_node = cell.find(f"{ns}v")
                        value = value_node.text if value_node is not None else ""
                        if cell.attrib.get("t") == "s":
                            try:
                                value = shared[int(value or "0")]
                            except Exception:
                                value = ""
                        elif cell.attrib.get("t") == "inlineStr":
                            inline = cell.find(f"{ns}is")
                            value = "".join(t.text or "" for t in (inline.iter(f"{ns}t") if inline is not None else []))
                        if value:
                            cells.append(f"{ref}={value}")
                    if cells:
                        sheet_text.append("; ".join(cells))
            text = "\n".join(sheet_text)
    except Exception:
        return []
    if not text.strip():
        return []
    return _chunk_text_rows(name, text, source, parent_doc=name)


def _media_row(name: str, data: bytes, source: str) -> dict:
    ext = _ext(name)
    if ext == ".pdf":
        media_type = "pdf"
    elif ext in _OFFICE_DOC_EXTS:
        media_type = "document"
    else:
        media_type = "image"
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


def _balanced_journey_points(points: list[dict], limit: int = 120, per_stage: int = 12) -> list[dict]:
    """Keep the UI sample broad enough to show each journey stage."""
    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    stages = sorted(
        {str(p.get("stage") or "other_evidence") for p in points},
        key=lambda s: _JOURNEY_STAGE_ORDER.get(s, 99),
    )
    for stage in stages:
        for point in [p for p in points if p.get("stage") == stage][:per_stage]:
            key = (str(point.get("case_id") or ""), str(point.get("row_id") or ""))
            if key in seen:
                continue
            selected.append(point)
            seen.add(key)
            if len(selected) >= limit:
                return selected
    for point in points:
        key = (str(point.get("case_id") or ""), str(point.get("row_id") or ""))
        if key in seen:
            continue
        selected.append(point)
        seen.add(key)
        if len(selected) >= limit:
            break
    selected.sort(key=lambda x: (
        x.get("stage_order", 99),
        str(x.get("date") or "9999"),
        x.get("case_id", ""),
        x.get("row_id", ""),
    ))
    return selected


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


def _node_id(kind: str, value: Any) -> str:
    return f"{_slug_id(kind)}:{_slug_id(str(value or 'unknown'))}"


def _edge_id(*parts: Any) -> str:
    raw = "|".join(str(p or "") for p in parts)
    return _hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:14]


def _chunk_id(row: dict) -> str:
    parent = str(row.get("parent_doc") or row.get("row_id") or "row")
    page = row.get("page_index")
    chunk = int(row.get("chunk_index") or 0)
    if page is not None:
        return f"{parent}#page-{int(page):03d}-chunk-{chunk + 1:03d}"
    return f"{parent}#chunk-{chunk + 1:03d}"


def _money_parts(raw: str) -> dict[str, Any]:
    currency_match = _re.search(r"\b(PHP|HKD|USD|SGD|AED|SAR)\b", raw or "", _re.I)
    return {
        "raw": raw,
        "currency": currency_match.group(1).upper() if currency_match else None,
        "value": _amount_value(raw),
    }


def _evidence_quote(text: str, *needles: Any, max_chars: int = 260) -> str:
    flat = " ".join(str(text or "").split())
    if not flat:
        return ""
    search_terms = [
        str(n).lower()
        for n in needles
        if n is not None and str(n).strip()
    ]
    chunks = _re.split(r"(?<=[.!?])\s+|\n+|;\s+", flat)
    for chunk in chunks:
        low = chunk.lower()
        if search_terms and any(term[:80] in low for term in search_terms):
            return chunk[:max_chars]
    return flat[:max_chars]


def _typed_edge(
    *,
    edge_type: str,
    source_node: str,
    target_node: str,
    row: dict,
    case_id: str,
    label: str,
    extractors: list[str],
    confidence: float,
    text: str,
    modalities: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    row_id = str(row.get("row_id") or "")
    edge = {
        "schema_version": "duecare.process.typed_edge.v1",
        "edge_id": _edge_id(edge_type, source_node, target_node, row_id, label),
        "edge_type": edge_type,
        "source_node": source_node,
        "target_node": target_node,
        "case_id": case_id,
        "row_id": row_id,
        "label": label,
        "evidence": {
            "file": row.get("source_path") or row_id,
            "parent_doc": row.get("parent_doc") or row_id,
            "page": row.get("page_index"),
            "chunk_id": _chunk_id(row),
            "quote": _evidence_quote(text, label, extra.get("amount", {}).get("raw") if isinstance(extra.get("amount"), dict) else ""),
        },
        "extractors": list(dict.fromkeys(extractors)),
        "modalities": modalities or ["plain_text"],
        "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
        "review_status": "needs_review",
        "local_only": True,
    }
    edge.update({k: v for k, v in extra.items() if v is not None})
    return edge


def _typed_edge_counts(edges: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for edge in edges:
        edge_type = str(edge.get("edge_type") or "edge")
        counts[edge_type] = counts.get(edge_type, 0) + 1
    return [
        {"edge_type": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:24]
    ]


def _build_rag_candidates(
    *,
    person_rows: list[dict],
    typed_edges: list[dict],
    top_risk_signals: list[dict],
    media_assets: list[dict],
    critical_fee_points: list[dict],
) -> list[dict]:
    """Create local reviewable RAG/knowledge candidates from graph facts."""
    candidates: list[dict] = []
    fee_edges = [
        e for e in typed_edges
        if e.get("edge_type") in {"charged_or_collected_fee", "fee_amount_observed"}
    ]
    signal_names = [str(s.get("signal") or "") for s in top_risk_signals]
    top_cases = [
        str(p.get("case_id") or "")
        for p in person_rows
        if p.get("case_id") and p.get("case_id") != "UNKNOWN"
    ][:8]

    if fee_edges:
        source_rows = list(dict.fromkeys(str(e.get("row_id") or "") for e in fee_edges if e.get("row_id")))[:12]
        edge_ids = [str(e.get("edge_id") or "") for e in fee_edges[:20]]
        candidates.append({
            "schema_version": "duecare.process.rag_candidate.v1",
            "candidate_id": "ph_hk_fee_salary_deduction_pattern",
            "knowledge_object_type": "modus_operandi",
            "title": "PH-HK worker-paid fee or debt pattern with post-arrival collection",
            "text": (
                "Local bundle evidence shows worker-paid recruitment, processing, "
                "training, medical, loan, or salary-deduction signals across "
                f"{len(source_rows)} row(s). Candidate cases include: "
                + ", ".join(top_cases)
                + ". Review against zero-fee recruitment rules, wage-deduction "
                "limits, debt-bondage indicators, and source/destination corridor law."
            ),
            "source_edge_ids": edge_ids,
            "source_row_ids": source_rows,
            "tags": ["local_graph", "fees", "salary_deduction", "needs_review"],
            "review_status": "needs_review",
            "local_only": True,
        })

    if any("passport" in s.lower() or "document" in s.lower() for s in signal_names):
        doc_edges = [
            e for e in typed_edges
            if e.get("edge_type") == "document_control_signal"
        ]
        candidates.append({
            "schema_version": "duecare.process.rag_candidate.v1",
            "candidate_id": "identity_document_control_pattern",
            "knowledge_object_type": "context_snippet",
            "title": "Identity-document control signal",
            "text": (
                "Rows in this local bundle mention passport or identity-document "
                "control. Treat this as a high-priority review signal and link it "
                "to any worker-paid fee, debt, threat, live-in, or movement-control "
                "evidence before drawing conclusions."
            ),
            "source_edge_ids": [str(e.get("edge_id") or "") for e in doc_edges[:20]],
            "source_row_ids": list(dict.fromkeys(str(e.get("row_id") or "") for e in doc_edges if e.get("row_id")))[:12],
            "tags": ["local_graph", "document_control", "needs_review"],
            "review_status": "needs_review",
            "local_only": True,
        })

    if media_assets:
        candidates.append({
            "schema_version": "duecare.process.rag_candidate.v1",
            "candidate_id": "queued_media_local_ocr_vision_review",
            "knowledge_object_type": "fact_template",
            "title": "Queued media local OCR and Gemma 4 vision review",
            "text": (
                f"{len(media_assets)} media asset(s) require local OCR and, when "
                "a multimodal Gemma 4 model is loaded, vision extraction. Store "
                "page-level entities, visible amounts, document type, screenshots, "
                "receipts, and contradictions as typed edges with row/page evidence."
            ),
            "source_edge_ids": [
                str(e.get("edge_id") or "") for e in typed_edges
                if e.get("edge_type") in {"media_requires_ocr", "media_requires_gemma_vision"}
            ][:20],
            "source_row_ids": [str(m.get("row_id") or "") for m in media_assets[:12]],
            "tags": ["local_graph", "ocr", "gemma4_vision", "needs_review"],
            "review_status": "needs_review",
            "local_only": True,
        })

    if critical_fee_points:
        candidates.append({
            "schema_version": "duecare.process.rag_candidate.v1",
            "candidate_id": "critical_journey_fee_points",
            "knowledge_object_type": "extracted_fact",
            "title": "Critical fee points along the worker journey",
            "text": (
                "The journey graph has critical payment/debt points that can feed "
                "timelines, overcharging charts, entity clustering, and reviewer "
                "questions about strongest cases or grouped patterns."
            ),
            "source_edge_ids": [str(e.get("edge_id") or "") for e in fee_edges[:20]],
            "source_row_ids": list(dict.fromkeys(str(p.get("row_id") or "") for p in critical_fee_points if p.get("row_id")))[:12],
            "tags": ["local_graph", "journey", "fees", "needs_review"],
            "review_status": "needs_review",
            "local_only": True,
        })

    return candidates


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


def _build_intelligence(
    rows: list[dict],
    results: list[dict],
    *,
    process_settings: dict[str, Any] | None = None,
    knowledge_context: dict[str, Any] | None = None,
) -> dict:
    process_settings = process_settings or _process_settings_from_mapping({})
    knowledge_context = knowledge_context or _load_local_knowledge_context(limit=24)
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
    typed_edges: list[dict] = []
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
        if row.get("needs_ocr"):
            document_node = _node_id("document", parent_doc)
            typed_edges.append(_typed_edge(
                edge_type="media_requires_ocr",
                source_node=document_node,
                target_node=_node_id("work_item", "local_ocr"),
                row=row,
                case_id=case_id,
                label="queued for local OCR/layout extraction",
                extractors=["zip_inventory", "media_detector"],
                confidence=0.98,
                text=text,
                modalities=["file_structure", row.get("media_type") or "media"],
                media_type=row.get("media_type"),
            ))
            typed_edges.append(_typed_edge(
                edge_type="media_requires_gemma_vision",
                source_node=document_node,
                target_node=_node_id("work_item", "gemma4_local_multimodal"),
                row=row,
                case_id=case_id,
                label="queued for Gemma 4 local multimodal extraction",
                extractors=["zip_inventory", "media_detector", "gemma4_prompt_contract"],
                confidence=0.92,
                text=text,
                modalities=["file_structure", row.get("media_type") or "media"],
                media_type=row.get("media_type"),
            ))
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
                typed_edges.append(_typed_edge(
                    edge_type="located_at",
                    source_node=_node_id("case", case_id),
                    target_node=_node_id("location", loc_norm),
                    row=row,
                    case_id=case_id,
                    label=loc_norm,
                    extractors=["location_regex", "row_chunk_linking"],
                    confidence=0.74,
                    text=text,
                ))

        for date in _DATE_RE.findall(text)[:6]:
            item = {"case_id": case_id, "row_id": row_id, "date": date, "document_type": kind}
            timeline.append(item)
            person["timeline"].append(item)
            row_dates.append(date)
            typed_edges.append(_typed_edge(
                edge_type="dated_evidence",
                source_node=_node_id("case", case_id),
                target_node=_node_id("date", date),
                row=row,
                case_id=case_id,
                label=date,
                extractors=["date_regex", "row_chunk_linking"],
                confidence=0.76,
                text=text,
            ))

        for amt in (scored.get("entities") or {}).get("AMOUNT", []):
            value = _amount_value(amt)
            pay = {"case_id": case_id, "row_id": row_id, "amount": amt, "value": value, "document_type": kind}
            payments.append(pay)
            person["amounts"].append(pay)
            row_payments.append(pay)
            money = _money_parts(amt)
            actor = person.get("agency") or person.get("employer")
            if actor:
                source_node = _node_id("entity", actor)
                target_node = _node_id("case", case_id)
                edge_type = "charged_or_collected_fee"
            else:
                source_node = _node_id("case", case_id)
                target_node = _node_id("amount", amt)
                edge_type = "fee_amount_observed"
            typed_edges.append(_typed_edge(
                edge_type=edge_type,
                source_node=source_node,
                target_node=target_node,
                row=row,
                case_id=case_id,
                label=amt,
                extractors=["amount_regex", "row_chunk_linking", "entity_regex"],
                confidence=0.78 if actor else 0.7,
                text=text,
                amount=money,
                document_type=kind,
            ))

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
            typed_edges.append(_typed_edge(
                edge_type="rule_hit",
                source_node=_node_id("case", case_id),
                target_node=_node_id("rule", rid),
                row=row,
                case_id=case_id,
                label=label,
                extractors=["grep_rule", "row_chunk_linking"],
                confidence=0.86 if severity in {"critical", "high"} else 0.76,
                text=text,
                severity=severity,
                rule_id=rid,
                document_type=kind,
            ))

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
                if "passport" in label or "document" in label:
                    edge_type = "document_control_signal"
                elif "deduction" in label:
                    edge_type = "salary_deduction_signal"
                elif "threat" in label or "coercion" in label:
                    edge_type = "threat_or_retaliation_signal"
                else:
                    edge_type = "journey_stage_observation"
                typed_edges.append(_typed_edge(
                    edge_type=edge_type,
                    source_node=_node_id("case", case_id),
                    target_node=_node_id("signal", label),
                    row=row,
                    case_id=case_id,
                    label=label,
                    extractors=["keyword_signal", "row_chunk_linking"],
                    confidence=0.68,
                    text=text,
                    document_type=kind,
                ))

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
            typed_edges.append(_typed_edge(
                edge_type="filed_under",
                source_node=_node_id("case", case_id),
                target_node=_node_id("folder", folder_context),
                row=row,
                case_id=case_id,
                label=str(folder_context),
                extractors=["zip_inventory", "folder_path_context"],
                confidence=0.82,
                text=text,
                modalities=["file_structure"],
                source_path=row.get("source_path") or row_id,
            ))

        stage = _journey_stage(row_id, text, kind)
        if row_signals or row_payments or kind != "other":
            typed_edges.append(_typed_edge(
                edge_type="journey_stage_observation",
                source_node=_node_id("case", case_id),
                target_node=_node_id("journey_stage", stage),
                row=row,
                case_id=case_id,
                label=stage.replace("_", " "),
                extractors=["document_classifier", "journey_stage_heuristic"],
                confidence=0.72,
                text=text,
                document_type=kind,
            ))
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
    rag_candidates = _build_rag_candidates(
        person_rows=person_rows,
        typed_edges=typed_edges,
        top_risk_signals=top_risk_signals,
        media_assets=media_assets,
        critical_fee_points=critical_fee_points,
    )
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
        "review_mode": process_settings.get("review_mode") or _process_mode(),
        "process_settings": process_settings,
        "gemma_budget": {
            "runtime_budget_minutes": process_settings.get("runtime_budget_minutes", 15),
            "max_gemma_calls": process_settings.get("max_gemma_calls", 75),
            "gemma_calls_per_item": process_settings.get("gemma_calls_per_item", 1),
            "run_inline_gemma_text": bool(process_settings.get("run_inline_gemma_text", False)),
            "edge_strictness": process_settings.get("edge_strictness", "balanced"),
            "knowledge_candidates_enabled": bool(process_settings.get("generate_knowledge_candidates", True)),
            "include_imported_knowledge": bool(process_settings.get("include_imported_knowledge", True)),
        },
        "model_capability_notes": _MODEL_CAPABILITY_NOTES,
        "edge_quality_dimensions": EDGE_QUALITY_DIMENSIONS,
        "pointed_edge_questions": EDGE_EXTRACTION_POINTED_QUESTIONS,
        "page_item_prompt_tree": PAGE_ITEM_PROMPT_TREE,
        "knowledge_context": knowledge_context if process_settings.get("include_imported_knowledge", True) else {
            "schema_version": "duecare.process.knowledge_context.v1",
            "local_only": True,
            "n_objects": 0,
            "objects": [],
            "disabled_by_settings": True,
        },
        "n_parent_documents": len(parent_docs),
        "n_pages": sum(int(d.get("n_pages") or 0) for d in parent_document_rows),
        "n_chunks": len(rows),
        "n_media_assets": len(media_assets),
        "chunk_chars": _CHUNK_CHARS,
        "local_processing_contract": {
            "local_only": True,
            "remote_api_calls": False,
            "staging_roots": ["/kaggle/working/process-staging", ".duecare-process-staging"],
            "privacy_boundary": "Raw files, OCR text, graph edges, and Gemma prompts stay in the kernel unless the reviewer explicitly exports or submits a sanitized bundle.",
            "deterministic_layers": [
                "archive_inventory",
                "text_extraction",
                "file_structure_edges",
                "grep_rules",
                "entity_regex",
                "journey_stage_mapping",
                "typed_edge_contract",
            ],
            "optional_local_engines": [
                {
                    "id": "ocr_layout_engine",
                    "examples": ["Tesseract", "EasyOCR", "PaddleOCR", "Docling", "Marker", "MinerU"],
                    "status": "queued_contract",
                },
                {
                    "id": "gemma4_text_edge_pass",
                    "examples": ["Gemma 4 local text model over OCR/text chunks"],
                    "status": "implemented_as_post_process_endpoint",
                },
                {
                    "id": "gemma4_multimodal_edge_pass",
                    "examples": ["Gemma 4 multimodal local model over image/page plus OCR context"],
                    "status": "queued_contract_when_multimodal_model_loaded",
                },
            ],
            "knowledge_object_context": (
                "Imported/promoted local KnowledgeObject envelopes can be read "
                "into the Gemma edge/RAG prompt as versioned context. They are "
                "not treated as automatic truth; they guide extraction and "
                "remain visible for reviewer audit."
            ),
            "frontier_model_note": (
                "Frontier cloud models could enhance OCR or visual QA in other deployments, "
                "but this workbench is designed for local Gemma 4 and local preprocessing."
            ),
        },
        "scalable_queue_contract": {
            "schema_version": "duecare.process.queue_contract.v1",
            "purpose": "Scale from one ZIP to thousands of files or years of case history without a single long request.",
            "work_item_levels": [
                "collection",
                "archive_member",
                "document",
                "page",
                "page_region",
                "text_block",
                "table",
                "image_or_screenshot",
                "signature_or_stamp",
                "audio_segment",
                "video_frame_or_scene",
            ],
            "recommended_phases": [
                "inventory_and_hash",
                "deduplicate",
                "page_split",
                "layout_region_detection",
                "local_ocr_or_asr",
                "document_classification",
                "page_item_classification",
                "targeted_prompt_branching",
                "deterministic_entity_edges",
                "gemma4_text_edge_pass",
                "gemma4_multimodal_edge_pass_when_available",
                "entity_resolution",
                "edge_merge_and_conflict_check",
                "review_queue",
            ],
            "batching_policy": {
                "max_request_rows": _ROW_CAP,
                "queue_large_archives": True,
                "idempotency_key": "sha256(file_bytes)+source_path+page+region",
                "resume_strategy": "skip completed work items and retry failed OCR/Gemma items independently",
            },
        },
        "analysis_methods": [
            {
                "id": "plain_text",
                "label": "Plain-text extraction",
                "detail": "Text, CSV, JSONL, markdown, logs, DOCX, simple XLSX, RTF/HTML/email, and extractable PDF pages are chunked locally and scanned.",
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
                "label": "Gemma 4 page-item prompt tree",
                "detail": "Each document/page/page-region starts with classification, then routes into targeted prompts for receipts, chats, contracts, cross-document linking, and knowledge-object candidates within the selected local budget.",
            },
            {
                "id": "knowledge_object_context",
                "label": "Local knowledge-object context",
                "detail": "Imported knowledge files can supply reviewed rules, patterns, prompt templates, RAG docs, and fact templates for continuous local improvement of the Gemma edge/RAG pass.",
            },
            {
                "id": "typed_graph_edges",
                "label": "Typed graph-edge contract",
                "detail": "Deterministic passes emit typed edges with source_node, target_node, evidence file/page/chunk, extractors, confidence, local_only, and review_status fields. Gemma 4 can propose additional edges against the same schema.",
            },
            {
                "id": "rag_candidate_generation",
                "label": "RAG and knowledge candidates",
                "detail": "Repeated local patterns are turned into reviewable RAG/context/modus-operandi candidates before any promotion into knowledge files.",
            },
        ],
        "passes": [
            {
                "id": "inventory",
                "label": "Document inventory",
                "status": "implemented",
                "detail": "ZIP, CSV, JSONL, text, DOCX, legacy Office, spreadsheet, email, PDF, and image assets are enumerated locally.",
            },
            {
                "id": "chunking",
                "label": "Document and page chunking",
                "status": "implemented_for_text_and_extractable_pdfs",
                "detail": f"Text, DOCX, simple XLSX, RTF/HTML/email, and extractable PDF pages are split into chunks of about {_CHUNK_CHARS} characters; scanned pages, legacy Office binaries, and images become media work items.",
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
                "id": "gemma_text_edges",
                "label": "Gemma 4 text edge extraction",
                "status": "implemented_post_process",
                "detail": "After deterministic processing, /api/process/graph-extract asks local Gemma 4 to propose typed edges and RAG candidates from bounded text, OCR, folder, and graph context.",
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
        "gemma_edge_prompt_templates": GRAPH_EDGE_PROMPT_TEMPLATES,
    }
    return {
        "version": "process-intelligence-v1",
        "n_people": len([p for p in person_rows if p.get("case_id") != "UNKNOWN"]),
        "n_documents": len(rows),
        "n_evidence_edges": len(evidence_edges),
        "n_typed_edges": len(typed_edges),
        "document_type_counts": doc_type_counts,
        "folder_counts": [
            {"folder": k, "count": v}
            for k, v in sorted(folder_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:30]
        ],
        "people": person_rows,
        "hierarchy": hierarchy,
        "top_payments": payments[:20],
        "top_risk_signals": top_risk_signals,
        "typed_edge_counts": _typed_edge_counts(typed_edges),
        "timeline": timeline[:40],
        "locations": [{"name": k, "count": v} for k, v in sorted(locations.items(), key=lambda kv: (-kv[1], kv[0]))[:20]],
        "evidence_edges": evidence_edges[:80],
        "typed_edges": typed_edges[:240],
        "rag_candidates": rag_candidates,
        "gemma_edge_pass": {
            "status": "not_run",
            "detail": "Run /api/process/graph-extract after review to ask local Gemma 4 for additional typed edges and RAG candidates.",
            "prompt_templates": GRAPH_EDGE_PROMPT_TEMPLATES,
            "page_item_prompt_tree": PAGE_ITEM_PROMPT_TREE,
        },
        "graph": graph,
        "journey_points": _balanced_journey_points(journey_points, limit=120),
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


def _gemma_case_brief(
    app: Any,
    bundle: dict,
    intelligence: dict,
    *,
    max_new_tokens: int = 900,
) -> dict:
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
        "Given a locally extracted migrant-worker exploitation case-bundle "
        "intelligence object, "
        "produce compact JSON with keys: case_theory, priority_people, "
        "risk_clusters, missing_evidence, recommended_questions. "
        "Use only the supplied facts and row_ids. Do not invent facts.\n\n"
        + _json.dumps(compact, ensure_ascii=False)[:12000]
    )
    try:
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        try:
            model_out = gc(messages, max_new_tokens=max_new_tokens, temperature=0.2)
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
                if _ext(name) == ".docx":
                    docx_rows = _try_docx_text_rows(name, data, filename)
                    if docx_rows:
                        rows.extend(docx_rows)
                        continue
                    rows.append(_media_row(name, data, filename))
                    continue
                if _ext(name) == ".doc":
                    doc_rows = _try_legacy_doc_text_rows(name, data, filename)
                    if doc_rows:
                        rows.extend(doc_rows)
                        continue
                    rows.append(_media_row(name, data, filename))
                    continue
                if _ext(name) == ".xlsx":
                    xlsx_rows = _try_xlsx_text_rows(name, data, filename)
                    if xlsx_rows:
                        rows.extend(xlsx_rows)
                        continue
                    rows.append(_media_row(name, data, filename))
                    continue
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
                    txt = _decode_documentish_text(name, data)
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
        if _ext(filename) == ".docx":
            docx_rows = _try_docx_text_rows(filename, contents, filename)
            if docx_rows:
                return docx_rows
            rows.append(_media_row(filename, contents, filename))
            return rows
        if _ext(filename) == ".doc":
            doc_rows = _try_legacy_doc_text_rows(filename, contents, filename)
            if doc_rows:
                return doc_rows
            rows.append(_media_row(filename, contents, filename))
            return rows
        if _ext(filename) == ".xlsx":
            xlsx_rows = _try_xlsx_text_rows(filename, contents, filename)
            if xlsx_rows:
                return xlsx_rows
            rows.append(_media_row(filename, contents, filename))
            return rows
        if _ext(filename) == ".pdf":
            pdf_rows = _try_pdf_text_rows(filename, contents, filename)
            if pdf_rows:
                return pdf_rows
            rows.append(_media_row(filename, contents, filename))
            return rows
        if not _is_probably_text(filename, contents):
            rows.append(_media_row(filename, contents, filename))
            return rows
        blob = _decode_documentish_text(filename, contents)
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
    typed_edges = intelligence.get("typed_edges") or []
    cited_rows: list[str] = []

    def add_rows(rows: list[str]) -> None:
        for row in rows:
            if row and row not in cited_rows:
                cited_rows.append(row)

    wants_camouflage = any(k in q for k in (
        "fee camouflage", "fee_camouflage", "camouflage",
        "disguised fee", "hidden fee", "relabeled fee",
    ))
    wants_provider_choice = any(k in q for k in (
        "provider choice", "provider_choice", "restricted provider",
        "provider restriction", "choice restriction",
        "limited provider", "must use this", "must use the",
    ))
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

    if wants_camouflage or wants_provider_choice:
        # The demo's flagship question pairs two distinct TIP indicators:
        # fee camouflage (recruitment cost re-labeled as training,
        # medical, repayment, or salary deduction) and restricted
        # provider choice (worker is forced to use a single agency,
        # housing, medical centre, or remittance provider).
        #
        # Deterministic processing emits proxies for these without a
        # model: fee_amount_observed, salary_deduction_signal, and
        # rule_hit edges fire on the camouflage side; located_at,
        # filed_under, and journey_stage_observation edges plus
        # provider/agency risk signals cover the provider side.
        # Explicit fee_camouflage_evidence and
        # provider_choice_restriction edges come from the optional
        # local Gemma edge pass; this branch points the reviewer at
        # both surfaces and at the upgrade path.
        camouflage_proxy_types = {
            "fee_camouflage_evidence",
            "fee_amount_observed",
            "salary_deduction_signal",
        }
        provider_proxy_types = {
            "provider_choice_restriction",
            "affiliate_or_common_control_signal",
            "located_at",
            "filed_under",
            "journey_stage_observation",
        }
        camouflage_edges: list[dict] = []
        provider_edges: list[dict] = []
        for edge in typed_edges:
            etype = str(edge.get("edge_type") or "")
            label_low = str(edge.get("label") or "").lower()
            if wants_camouflage and etype in camouflage_proxy_types:
                camouflage_edges.append(edge)
            if wants_provider_choice and (
                etype in provider_proxy_types
                or "provider" in label_low
                or "agency" in label_low
            ):
                provider_edges.append(edge)

        provider_signal_people: list[dict] = []
        if wants_provider_choice:
            for person in people:
                signals = [str(s).lower() for s in (person.get("risk_signals") or [])]
                matched = False
                for signal in signals:
                    for marker in (
                        "provider", "agency_control", "limited_choice",
                        "single_provider", "affiliate",
                    ):
                        if marker in signal:
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    provider_signal_people.append(person)

        lines: list[str] = []
        if wants_camouflage:
            lines.append("Fee camouflage candidates")
            lines.append("")
            lines.append(
                "Deterministic proxies for fee camouflage are "
                "fee_amount_observed, salary_deduction_signal, and rule_hit "
                "edges with placement/training/medical/repayment language. "
                "Explicit fee_camouflage_evidence edges come from the "
                "optional local Gemma edge pass."
            )
            if not camouflage_edges:
                lines.append("")
                lines.append(
                    "No fee-camouflage proxy edges fired in this bundle. Run "
                    "the local Gemma edge pass on a richer source bundle to "
                    "surface explicit fee_camouflage_evidence edges, or "
                    "upload rows that name placement, training, medical, "
                    "transport, deposit, or wage-deduction fees."
                )
            else:
                lines.append("")
                for edge in camouflage_edges[:10]:
                    row = str(edge.get("row_id") or "")
                    add_rows([row])
                    label = str(edge.get("label") or edge.get("edge_type") or "")
                    quote = str(((edge.get("evidence") or {}).get("quote") or "")).strip().replace("\n", " ")
                    quote_clip = (quote[:140] + "...") if len(quote) > 140 else quote
                    lines.append(
                        f"- `{row}` | edge: {edge.get('edge_type')} | label: {label}"
                        + (f" | quote: {quote_clip}" if quote_clip else "")
                    )

        if wants_provider_choice:
            if lines:
                lines.append("")
            lines.append("Restricted provider choice candidates")
            lines.append("")
            lines.append(
                "Deterministic proxies for restricted provider choice are "
                "located_at, filed_under, and journey_stage_observation edges, "
                "plus risk signals naming a single provider, agency control, "
                "or limited choice. Explicit provider_choice_restriction "
                "edges come from the optional local Gemma edge pass."
            )
            if not provider_edges and not provider_signal_people:
                lines.append("")
                lines.append(
                    "No deterministic provider-choice proxies fired. Run the "
                    "local Gemma edge pass to surface "
                    "provider_choice_restriction edges, or upload rows that "
                    "name a single broker, medical centre, housing provider, "
                    "or remittance channel."
                )
            if provider_edges:
                lines.append("")
                for edge in provider_edges[:8]:
                    row = str(edge.get("row_id") or "")
                    add_rows([row])
                    lines.append(
                        f"- `{row}` | edge: {edge.get('edge_type')} | label: "
                        f"{edge.get('label') or edge.get('edge_type')}"
                    )
            if provider_signal_people:
                lines.append("")
                lines.append("People with provider-related risk signals:")
                for person in provider_signal_people[:6]:
                    rows = _person_support_rows(person)
                    add_rows(rows)
                    lines.append(
                        f"- {person.get('name') or person.get('case_id')} "
                        f"(`{person.get('case_id')}`) | support rows: "
                        + ", ".join(f"`{r}`" for r in rows)
                    )

        if not lines:
            return None

        lines.append("")
        lines.append(
            "Both fee camouflage and restricted provider choice are TIP "
            "indicators. The combination strongly suggests recruitment-fee "
            "concealment that the worker cannot avoid. Run the local Gemma "
            "edge pass to upgrade these proxies into explicit "
            "fee_camouflage_evidence and provider_choice_restriction edges, "
            "and confirm with original receipts, contract clauses, and "
            "broker/recipient identifiers before any escalation."
        )
        return {
            "answer": "\n".join(lines),
            "cited_rows": cited_rows,
            "analysis_kind": "fee_camouflage_and_provider_choice",
        }

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


def _extract_json_object(text: str) -> dict | None:
    match = _re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        return None
    try:
        parsed = _json.loads(match.group(0))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_model_edge(edge: Any, *, fallback_case_id: str = "UNKNOWN") -> dict | None:
    if not isinstance(edge, dict):
        return None
    edge_type = str(edge.get("edge_type") or "").strip()
    source_node = str(edge.get("source_node") or "").strip()
    target_node = str(edge.get("target_node") or "").strip()
    if not edge_type or not source_node or not target_node:
        return None
    evidence = edge.get("evidence") if isinstance(edge.get("evidence"), dict) else {}
    normalized = {
        "schema_version": "duecare.process.typed_edge.v1",
        "edge_id": str(edge.get("edge_id") or _edge_id(
            "gemma4", edge_type, source_node, target_node,
            evidence.get("file"), evidence.get("quote"),
        )),
        "edge_type": edge_type,
        "source_node": source_node,
        "target_node": target_node,
        "case_id": str(edge.get("case_id") or fallback_case_id),
        "row_id": str(edge.get("row_id") or evidence.get("file") or ""),
        "label": str(edge.get("label") or edge_type.replace("_", " ")),
        "evidence": {
            "file": evidence.get("file") or edge.get("row_id") or "",
            "page": evidence.get("page"),
            "chunk_id": evidence.get("chunk_id") or "",
            "quote": str(evidence.get("quote") or "")[:320],
        },
        "extractors": list(dict.fromkeys(
            [str(x) for x in (edge.get("extractors") or []) if str(x).strip()]
            + ["gemma4_local"]
        )),
        "modalities": edge.get("modalities") or ["plain_text"],
        "confidence": round(max(0.0, min(1.0, float(edge.get("confidence") or 0.5))), 2),
        "review_status": "needs_review",
        "local_only": True,
    }
    for key in ("amount", "severity", "rule_id", "document_type", "notes"):
        if key in edge:
            normalized[key] = edge[key]
    return normalized


def _gemma_edge_pass(
    app: Any,
    bundle: dict,
    *,
    prompt_id: str,
    limit: int,
    progress: Any | None = None,
) -> dict:
    def mark(phase: str, pct: int, detail: str) -> None:
        if progress:
            progress(phase=phase, pct=pct, detail=detail)

    intelligence = bundle.get("intelligence") or {}
    mark("seed_edges", 20, "Collecting deterministic typed edges, RAG candidates, and review settings.")
    deterministic_edges = (intelligence.get("typed_edges") or [])[:limit]
    deterministic_candidates = intelligence.get("rag_candidates") or []
    gc = getattr(app.state, "gemma_call", None)
    base = {
        "schema_version": "duecare.process.gemma_edge_pass.v1",
        "prompt_id": prompt_id,
        "local_only": True,
        "remote_api_calls": False,
        "prompt_templates": GRAPH_EDGE_PROMPT_TEMPLATES,
        "edge_quality_dimensions": EDGE_QUALITY_DIMENSIONS,
        "pointed_edge_questions": EDGE_EXTRACTION_POINTED_QUESTIONS,
        "page_item_prompt_tree": PAGE_ITEM_PROMPT_TREE,
        "model_capability_notes": _MODEL_CAPABILITY_NOTES,
        "process_settings": (bundle.get("config") or {}).get("process_settings") or {},
        "knowledge_context": (bundle.get("config") or {}).get("local_knowledge_context") or {},
        "seed_typed_edges": deterministic_edges,
        "rag_candidates": deterministic_candidates,
    }
    if gc is None:
        mark("deterministic_fallback", 100, "No local Gemma 4 model is loaded; returning deterministic edge contract.")
        return {
            **base,
            "status": "deterministic_no_model",
            "model_edges": [],
            "uncertainties": [
                "No local Gemma 4 model is loaded; deterministic typed edges and RAG candidates are returned for review.",
            ],
        }

    mark("prompt_build", 34, "Building bounded Gemma 4 edge-extraction prompt from graph, rows, media queue, and knowledge context.")
    prompt = build_graph_edge_extraction_prompt(bundle, prompt_id=prompt_id, limit=limit)
    messages = [
        {"role": "system", "content": [{"type": "text", "text": GRAPH_EDGE_EXTRACTION_SYSTEM_PROMPT}]},
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
    ]
    try:
        mark("model_call", 58, "Calling local Gemma 4 for typed edge and RAG-candidate synthesis.")
        try:
            model_out = gc(messages, max_new_tokens=1200, temperature=0.15)
        except TypeError:
            model_out = gc(messages)
        mark("parse_model_output", 76, "Gemma returned; sanitizing and parsing JSON edge contract.")
        text = model_out if isinstance(model_out, str) else (
            (model_out or {}).get("text") or (model_out or {}).get("response") or ""
        )
        text = sanitize_model_output(text)
        parsed = _extract_json_object(text)
        if not parsed:
            mark("parse_model_output", 100, "Gemma output was not valid JSON; keeping deterministic fallback edges visible.")
            return {
                **base,
                "status": "model_unparsed_deterministic_fallback",
                "model_edges": [],
                "text_preview": text[:900],
                "uncertainties": ["Gemma output did not parse as JSON; review deterministic edges."],
            }
        fallback_case_id = ((intelligence.get("people") or [{}])[0] or {}).get("case_id") or "UNKNOWN"
        model_edges = [
            e for e in (
                _normalize_model_edge(edge, fallback_case_id=fallback_case_id)
                for edge in (parsed.get("edges") or [])
            )
            if e
        ][:limit]
        candidates = parsed.get("rag_candidates")
        if not isinstance(candidates, list):
            candidates = deterministic_candidates
        uncertainties = parsed.get("uncertainties")
        if not isinstance(uncertainties, list):
            uncertainties = []
        mark("merge_results", 92, "Merging model-proposed edges with deterministic review context.")
        return {
            **base,
            "status": "ok",
            "model_edges": model_edges,
            "rag_candidates": candidates[:12],
            "uncertainties": [str(x)[:240] for x in uncertainties[:12]],
            "prompt_chars": len(prompt),
        }
    except Exception as exc:
        mark("model_error", 100, "Gemma edge pass failed; returning deterministic fallback edges.")
        return {
            **base,
            "status": "model_error_deterministic_fallback",
            "model_edges": [],
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "uncertainties": ["Gemma edge pass failed; deterministic typed edges remain available."],
        }


def register_routes(app: Any) -> None:
    """Attach the process routes to a FastAPI app."""

    def _process_jobs() -> tuple[dict[str, dict[str, Any]], _threading.Lock]:
        if not hasattr(app.state, "process_jobs"):
            app.state.process_jobs = {}
        if not hasattr(app.state, "process_jobs_lock"):
            app.state.process_jobs_lock = _threading.Lock()
        return app.state.process_jobs, app.state.process_jobs_lock

    def _process_job_update(job_id: str, **fields: Any) -> None:
        jobs, lock = _process_jobs()
        with lock:
            job = jobs.setdefault(job_id, {"job_id": job_id, "events": []})
            event = {
                "ts": _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status": fields.get("status", job.get("status", "running")),
                "phase": fields.get("phase", job.get("phase", "")),
                "pct": fields.get("pct", job.get("pct", 0)),
                "detail": fields.get("detail", ""),
            }
            # Forward small, non-payload telemetry fields onto the
            # individual event record so reviewers and contract tests
            # can read them directly from the events stream without
            # diffing the job-level dict. `result` is intentionally
            # excluded because it can be the full processed bundle.
            for key in ("media_assets_queued", "error", "fallback"):
                if key in fields and fields[key] is not None:
                    event[key] = fields[key]
            job.update(fields)
            job.setdefault("events", []).append(event)
            job["updated_at"] = event["ts"]

    def _build_process_bundle(
        filename: str,
        contents: bytes,
        *,
        progress: Any | None = None,
        job_id: str | None = None,
        process_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the process bundle synchronously, with optional job progress."""
        process_settings = process_settings or _process_settings_from_mapping({})
        knowledge_context = (
            _load_local_knowledge_context(limit=24)
            if process_settings.get("include_imported_knowledge", True)
            else {
                "schema_version": "duecare.process.knowledge_context.v1",
                "local_only": True,
                "n_objects": 0,
                "objects": [],
                "disabled_by_settings": True,
            }
        )
        def mark(phase: str, pct: int, detail: str) -> None:
            if progress:
                progress(phase=phase, pct=pct, detail=detail)

        mark("staging", 12, "Saving the uploaded knowledge/source bundle in local process staging.")
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"01_process_{ts}"
        staging = _stage_upload(filename, contents, run_id)

        mark("parsing", 24, "Enumerating ZIP members, folders, pages, tables, messages, and media assets.")
        try:
            rows = _parse_upload(filename, contents)
        except Exception as e:
            raise HTTPException(400, f"parse failed: {e}")

        mark("scoring", 42, "Running GREP rules and deterministic entity extraction over parsed rows.")
        capped = rows[:_ROW_CAP]
        results, agg_grep, agg_entity, agg_statute = _score_rows(
            capped, getattr(app.state, "grep_call", None)
        )

        mark("linking", 63, "Building people, folders, journey stages, payments, locations, and evidence edges.")
        top_grep = sorted(agg_grep.items(), key=lambda x: -x[1])[:10]
        top_statute = sorted(agg_statute.items(), key=lambda x: -x[1])[:10]
        bundle = {
            "schema_version": "1.0",
            "kernel_id": "01-duecare-exploration-workbench",
            "run_id": run_id,
            "job_id": job_id,
            "config": {
                "row_cap": _ROW_CAP,
                "source": filename,
                "gemma_case_brief": "deferred",
                "processing_mode": "async_job" if job_id else "direct",
                "process_settings": process_settings,
                "local_knowledge_context": {
                    "local_only": True,
                    "n_objects": knowledge_context.get("n_objects", 0),
                    "by_type": knowledge_context.get("by_type", {}),
                    "sources": knowledge_context.get("sources", []),
                    "disabled_by_settings": knowledge_context.get("disabled_by_settings", False),
                },
            },
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
        intelligence = _build_intelligence(
            capped,
            results,
            process_settings=process_settings,
            knowledge_context=knowledge_context,
        )
        mark("brief", 80, "Creating case brief and deciding whether local Gemma text passes can run.")
        deterministic_brief = _deterministic_case_brief(bundle, intelligence)
        gemma_available = bool(getattr(app.state, "gemma_call", None))
        gemma_budget = int(process_settings.get("max_gemma_calls") or 0)
        gemma_per_item = int(process_settings.get("gemma_calls_per_item") or 0)
        inline_gemma_enabled = bool(process_settings.get("run_inline_gemma_text"))
        run_gemma_text = bool(
            gemma_available
            and inline_gemma_enabled
            and gemma_budget > 0
            and gemma_per_item > 0
        )
        n_gemma_calls_attempted = 0
        if run_gemma_text:
            mark("gemma_case_brief", 82, "Calling local Gemma 4 for the text case brief.")
            n_gemma_calls_attempted += 1
            gemma_brief = _gemma_case_brief(app, bundle, intelligence)
            gemma_brief["deferred"] = False
            gemma_brief["detail"] = (
                "Local Gemma 4 was loaded, so the background process job "
                "called it for a bounded text case brief. OCR/media vision "
                "remains a separate queued capability."
            )
        else:
            reason = (
                "model not loaded"
                if not gemma_available else
                (
                    "inline Gemma text passes disabled for this upload"
                    if not inline_gemma_enabled else
                    "Gemma budget disabled by processing settings"
                )
            )
            gemma_brief = {
                "available": gemma_available,
                "status": "deterministic_deferred_model",
                "json": deterministic_brief,
                "text": _json.dumps(deterministic_brief, indent=2),
                "deferred": True,
                "detail": (
                    "The upload endpoint returned a deterministic case brief "
                    f"because {reason}. After confirming the graph, use the "
                    "explicit Gemma edge pass for model-backed text analysis."
                ),
            }
        intelligence["gemma_case_brief"] = gemma_brief
        gemma_edge_out = intelligence.get("gemma_edge_pass") or {}
        if run_gemma_text and gemma_budget > 1:
            edge_limit = max(4, min(32, gemma_budget - 1))
            def _edge_progress(*, phase: str, pct: int, detail: str, **_: Any) -> None:
                mapped_pct = 84 + round(max(0, min(100, int(pct))) * 0.10)
                mark(f"gemma_edge_{phase}", mapped_pct, detail)

            n_gemma_calls_attempted += 1
            gemma_edge_out = _gemma_edge_pass(
                app,
                bundle,
                prompt_id="case_graph_edges",
                limit=edge_limit,
                progress=_edge_progress,
            )
            intelligence["gemma_edge_pass"] = gemma_edge_out
        media_count = ((intelligence.get("processing_plan") or {}).get("n_media_assets", 0))
        if run_gemma_text:
            mark("model_passes_done", 94, "Local Gemma 4 text passes finished; finalizing bundle.")
        edge_status = str(gemma_edge_out.get("status") or "not_run")
        text_status = "complete" if run_gemma_text else "deferred"
        if run_gemma_text and (
            gemma_brief.get("status") in {"model_error_deterministic_fallback"}
            and edge_status in {"model_error_deterministic_fallback"}
        ):
            text_status = "deferred"
        intelligence["harness_trace"] = [
            {
                "id": "upload",
                "label": "Upload accepted",
                "status": "complete",
                "detail": f"{filename} ({len(contents)} bytes) received",
            },
            {
                "id": "stage",
                "label": "Stored in process staging",
                "status": "complete" if staging.get("saved") else "skipped",
                "detail": staging.get("path") or staging.get("error") or staging.get("root") or "staging unavailable",
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
                "id": "gemma_text",
                "label": "Gemma 4 text brief / edge pass",
                "status": text_status,
                "detail": (
                    f"case_brief={gemma_brief.get('status', 'not_run')}; "
                    f"edge_pass={edge_status}; "
                    f"model_calls_attempted={n_gemma_calls_attempted}"
                ),
            },
            {
                "id": "media_queue",
                "label": "OCR and Gemma 4 media vision queue",
                "status": "deferred" if media_count else "skipped",
                "detail": (
                    f"{media_count} media item(s) queued for OCR/Gemma 4 page review. "
                    "The current upload pass does not run image/page vision."
                ),
            },
            {
                "id": "graph",
                "label": "Local graph cached",
                "status": "complete",
                "detail": (
                    f"{intelligence.get('n_evidence_edges', 0)} evidence edges; "
                    f"{intelligence.get('n_typed_edges', 0)} typed edges"
                ),
            },
        ]
        bundle["intelligence"] = intelligence
        bundle["staging"] = staging
        bundle["summary"]["n_people_detected"] = intelligence.get("n_people", 0)
        bundle["summary"]["n_evidence_edges"] = intelligence.get("n_evidence_edges", 0)
        bundle["summary"]["n_typed_edges"] = intelligence.get("n_typed_edges", 0)
        bundle["summary"]["gemma_case_brief_status"] = gemma_brief.get("status")
        bundle["summary"]["gemma_edge_pass_status"] = edge_status
        bundle["summary"]["n_model_proposed_edges"] = len(gemma_edge_out.get("model_edges") or [])
        bundle["summary"]["n_gemma_calls_attempted"] = n_gemma_calls_attempted
        bundle["summary"]["gemma_model_loaded"] = gemma_available
        bundle["config"]["gemma_case_brief"] = gemma_brief.get("status") or "deferred"
        bundle["demo_replay"] = demo_replay(
            lane="bulk_file_review",
            endpoint="/api/process/batch/start" if job_id else "/api/process/batch",
            request={
                "filename": filename,
                "file_bytes": len(contents),
                "file_sha256": _hashlib.sha256(contents).hexdigest(),
                "process_settings": process_settings,
                "job_id": job_id,
            },
            response_summary={
                "run_id": run_id,
                "n_rows_total": len(rows),
                "n_rows_processed": len(capped),
                "n_people_detected": bundle["summary"].get("n_people_detected"),
                "n_typed_edges": bundle["summary"].get("n_typed_edges"),
                "gemma_case_brief_status": bundle["summary"].get("gemma_case_brief_status"),
                "gemma_edge_pass_status": bundle["summary"].get("gemma_edge_pass_status"),
                "n_gemma_calls_attempted": bundle["summary"].get("n_gemma_calls_attempted"),
            },
            artifacts=[{
                "name": "processed_bundle",
                "kind": "inline_response_json",
                "run_id": run_id,
            }],
            note=(
                "Reattach the same local file to replay the multipart upload. "
                "The full processed bundle is this response JSON and can be "
                "downloaded from Step 5."
            ),
        )
        app.state.last_process_bundle = bundle
        mark("caching", 92, "Caching local graph for graph chat and export.")
        try:
            from .._training_log import log_interaction as _log
            _summary = bundle.get("summary") or {}
            _log(
                "process",
                input_payload={
                    "filename": filename,
                    "n_rows": len(rows),
                    "review_mode": (process_settings.get("review_mode") or {}).get("id"),
                    "max_gemma_calls": process_settings.get("max_gemma_calls"),
                },
                output_payload={
                    "run_id": bundle.get("run_id"),
                    "n_processed": _summary.get("n_rows_processed", 0),
                    "top_grep": _summary.get("top_grep", []),
                    "entity_totals": _summary.get("entity_totals", {}),
                    "n_people_detected": _summary.get("n_people_detected", 0),
                    "n_typed_edges": _summary.get("n_typed_edges", 0),
                    "n_imported_knowledge_objects": knowledge_context.get("n_objects", 0),
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
        mark("complete", 100, "Processing complete. Review extracted intelligence before graph chat or export.")
        return bundle

    @app.post("/api/process/batch")
    async def api_process_batch(request: Request) -> Any:
        """Multipart upload -> rows -> GREP hits + entity regex -> v1.0 bundle."""
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no `file` field in multipart upload")
        contents = await upload.read()
        filename = getattr(upload, "filename", "uploaded") or "uploaded"
        process_settings = _process_settings_from_form(form)
        return JSONResponse(_build_process_bundle(
            filename,
            contents,
            process_settings=process_settings,
        ))

    @app.post("/api/process/batch/start")
    async def api_process_batch_start(request: Request) -> Any:
        """Start a background process job and return immediately for polling."""
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no `file` field in multipart upload")
        contents = await upload.read()
        filename = getattr(upload, "filename", "uploaded") or "uploaded"
        process_settings = _process_settings_from_form(form)
        if form.get("run_inline_gemma_text") is None:
            # Async upload is the public-demo path. Keep it deterministic
            # unless the user explicitly opts into inline model calls; a
            # slow 31B call should not block the upload result and graph.
            process_settings["run_inline_gemma_text"] = False
        job_id = f"process_{_uuid4().hex[:12]}"
        now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        jobs, lock = _process_jobs()
        with lock:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "received",
                "pct": 6,
                "filename": filename,
                "bytes": len(contents),
                "process_settings": process_settings,
                "created_at": now,
                "updated_at": now,
                "events": [{
                    "ts": now,
                    "status": "queued",
                    "phase": "received",
                    "pct": 6,
                    "detail": f"{filename} received by Kaggle kernel; background parsing queued.",
                }],
            }

        def worker() -> None:
            try:
                _process_job_update(
                    job_id,
                    status="running",
                    phase="starting",
                    pct=8,
                    detail="Background worker started inside the Kaggle kernel.",
                )
                bundle = _build_process_bundle(
                    filename,
                    contents,
                    job_id=job_id,
                    process_settings=process_settings,
                    progress=lambda **kw: _process_job_update(job_id, status="running", **kw),
                )
                # Honest completion: even at pct=100 the deterministic
                # pass is what finished. Media assets in the queue still
                # need OCR or Gemma 4 vision review; surface that so the
                # UI does not imply OCR/Gemma vision completed.
                intel = (bundle.get("intelligence") or {})
                media_queued = int(
                    ((intel.get("processing_plan") or {}).get("n_media_assets") or 0)
                )
                gemma_calls = int((bundle.get("summary") or {}).get("n_gemma_calls_attempted") or 0)
                done_prefix = (
                    f"Deterministic parsing and {gemma_calls} Gemma text call(s) complete"
                    if gemma_calls else
                    "Deterministic parsing complete"
                )
                if media_queued:
                    completion_detail = (
                        f"{done_prefix}; {media_queued} media asset(s) "
                        "remain queued for OCR or Gemma 4 vision review. Bundle cached "
                        "for graph chat."
                    )
                else:
                    completion_detail = (
                        f"{done_prefix}; no media items queued. Bundle cached for graph chat."
                    )
                _process_job_update(
                    job_id,
                    status="complete",
                    phase="complete",
                    pct=100,
                    detail=completion_detail,
                    media_assets_queued=media_queued,
                    result=bundle,
                )
            except Exception as e:
                _process_job_update(
                    job_id,
                    status="error",
                    phase="failed",
                    pct=100,
                    detail=str(e),
                    error=str(e),
                )

        thread = _threading.Thread(target=worker, name=f"duecare-{job_id}", daemon=True)
        thread.start()
        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "phase": "received",
            "pct": 6,
            "filename": filename,
            "bytes": len(contents),
            "process_settings": process_settings,
            "poll_url": f"/api/process/batch/status/{job_id}",
            "demo_replay": demo_replay(
                lane="bulk_file_review",
                endpoint="/api/process/batch/start",
                request={
                    "filename": filename,
                    "file_bytes": len(contents),
                    "file_sha256": _hashlib.sha256(contents).hexdigest(),
                    "process_settings": process_settings,
                },
                response_summary={
                    "job_id": job_id,
                    "poll_url": f"/api/process/batch/status/{job_id}",
                },
                artifacts=[{
                    "name": "process_job_status",
                    "kind": "poll_endpoint",
                    "path": f"/api/process/batch/status/{job_id}",
                }],
            ),
        })

    @app.get("/api/process/batch/status/{job_id}")
    def api_process_batch_status(job_id: str) -> Any:
        """Return current process-job progress and result when complete."""
        jobs, lock = _process_jobs()
        with lock:
            job = dict(jobs.get(job_id) or {})
        if not job:
            raise HTTPException(404, f"unknown process job: {job_id}")
        return JSONResponse(job)

    def _run_graph_extract_job(
        *,
        prompt_id: str,
        limit: int,
        progress: Any | None = None,
    ) -> dict[str, Any]:
        """Run the local graph-edge extraction pass and update bundle state."""
        bundle = getattr(app.state, "last_process_bundle", None)
        if bundle is None:
            if progress:
                progress(
                    phase="no_bundle",
                    pct=100,
                    detail="No processed bundle is cached on this kernel.",
                )
            return {
                "status": "no_bundle",
                "bundle_present": False,
                "message": "Upload and process a bundle before running the Gemma edge pass.",
            }
        settings = (
            (bundle.get("config") or {}).get("process_settings")
            or _process_settings_from_mapping({})
        )
        if progress:
            progress(
                phase="knowledge_context",
                pct=12,
                detail="Loading local KnowledgeObject context for the bounded edge prompt.",
            )
        if settings.get("include_imported_knowledge", True):
            knowledge_context = _load_local_knowledge_context(limit=24)
        else:
            knowledge_context = {
                "schema_version": "duecare.process.knowledge_context.v1",
                "local_only": True,
                "n_objects": 0,
                "objects": [],
                "disabled_by_settings": True,
            }
        if progress:
            progress(
                phase="context_ready",
                pct=18,
                detail=(
                    f"{knowledge_context.get('n_objects', 0)} local KnowledgeObject(s) "
                    "available for graph-edge prompting."
                ),
            )
        bundle.setdefault("config", {})["process_settings"] = settings
        bundle["config"]["local_knowledge_context"] = {
            "local_only": True,
            "n_objects": knowledge_context.get("n_objects", 0),
            "by_type": knowledge_context.get("by_type", {}),
            "sources": knowledge_context.get("sources", []),
            "disabled_by_settings": knowledge_context.get("disabled_by_settings", False),
        }
        bundle["config"]["imported_knowledge_objects"] = (
            knowledge_context.get("objects", [])[:12]
            if settings.get("include_imported_knowledge", True)
            else []
        )
        out = _gemma_edge_pass(
            app,
            bundle,
            prompt_id=prompt_id,
            limit=limit,
            progress=progress,
        )
        intelligence = bundle.setdefault("intelligence", {})
        intelligence["gemma_edge_pass"] = out
        bundle.setdefault("summary", {})["gemma_edge_pass_status"] = out.get("status")
        bundle["summary"]["n_model_proposed_edges"] = len(out.get("model_edges") or [])
        try:
            from .._training_log import log_interaction as _log
            _log(
                "process",
                input_payload={"prompt_id": prompt_id, "bundle_run_id": bundle.get("run_id")},
                output_payload={
                    "status": out.get("status"),
                    "n_model_edges": len(out.get("model_edges") or []),
                    "n_rag_candidates": len(out.get("rag_candidates") or []),
                },
                applied_layers={"gemma_edge_pass": {"fired": bool(out.get("model_edges"))}},
                trace={
                    "local_only": True,
                    "remote_api_calls": False,
                    "prompt_templates": [t.get("id") for t in GRAPH_EDGE_PROMPT_TEMPLATES],
                    "page_item_prompt_tree": [p.get("phase") for p in PAGE_ITEM_PROMPT_TREE],
                    "knowledge_context": bundle["config"].get("local_knowledge_context"),
                },
                extra={"kind": "graph_extract"},
            )
        except Exception:
            pass
        return {
            **out,
            "bundle_present": True,
            "evidence_edges": (bundle.get("summary") or {}).get("n_evidence_edges", 0),
            "typed_edges": (intelligence.get("typed_edges") or [])[:limit],
            "knowledge_context": bundle["config"].get("local_knowledge_context"),
            "page_item_prompt_tree": PAGE_ITEM_PROMPT_TREE,
            "model_capability_notes": _MODEL_CAPABILITY_NOTES,
        }

    @app.post("/api/process/graph-extract")
    async def api_process_graph_extract(request: Request) -> Any:
        """Ask local Gemma 4 to propose typed graph edges and RAG candidates."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        prompt_id = str(body.get("prompt_id") or "case_graph_edges")
        try:
            limit = int(body.get("limit") or 24)
        except Exception:
            limit = 24
        limit = max(4, min(limit, 80))
        return JSONResponse(_run_graph_extract_job(prompt_id=prompt_id, limit=limit))

    @app.post("/api/process/graph-extract/start")
    async def api_process_graph_extract_start(request: Request) -> Any:
        """Start a background local Gemma edge pass and return a poll URL."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        prompt_id = str(body.get("prompt_id") or "case_graph_edges")
        try:
            limit = int(body.get("limit") or 24)
        except Exception:
            limit = 24
        limit = max(4, min(limit, 80))
        job_id = f"edge_{_uuid4().hex[:12]}"
        now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        jobs, lock = _process_jobs()
        with lock:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "queued",
                "pct": 4,
                "prompt_id": prompt_id,
                "limit": limit,
                "created_at": now,
                "updated_at": now,
                "events": [{
                    "ts": now,
                    "status": "queued",
                    "phase": "queued",
                    "pct": 4,
                    "detail": "Local Gemma edge pass queued; deterministic fallback remains available.",
                }],
            }

        def worker() -> None:
            try:
                _process_job_update(
                    job_id,
                    status="running",
                    phase="starting",
                    pct=8,
                    detail="Background edge worker started inside the Kaggle kernel.",
                )
                result = _run_graph_extract_job(
                    prompt_id=prompt_id,
                    limit=limit,
                    progress=lambda **kw: _process_job_update(job_id, status="running", **kw),
                )
                _process_job_update(
                    job_id,
                    status="complete",
                    phase="complete",
                    pct=100,
                    detail=(
                        f"Gemma edge pass finished with status={result.get('status')}; "
                        f"model_edges={len(result.get('model_edges') or [])}."
                    ),
                    result=result,
                )
            except Exception as e:
                _process_job_update(
                    job_id,
                    status="error",
                    phase="failed",
                    pct=100,
                    detail=str(e),
                    error=str(e),
                )

        thread = _threading.Thread(target=worker, name=f"duecare-{job_id}", daemon=True)
        thread.start()
        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "phase": "queued",
            "pct": 4,
            "prompt_id": prompt_id,
            "limit": limit,
            "poll_url": f"/api/process/graph-extract/status/{job_id}",
        })

    @app.get("/api/process/graph-extract/status/{job_id}")
    def api_process_graph_extract_status(job_id: str) -> Any:
        """Return current local Gemma edge-pass progress and result."""
        jobs, lock = _process_jobs()
        with lock:
            job = dict(jobs.get(job_id) or {})
        if not job:
            raise HTTPException(404, f"unknown graph-extract job: {job_id}")
        return JSONResponse(job)

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
