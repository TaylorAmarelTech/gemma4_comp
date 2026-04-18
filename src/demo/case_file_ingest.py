"""File-based migration case intake utilities for the DueCare demo.

Turns uploaded files into the structured document bundle expected by the
existing migration-case workflow.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .models import MigrationCaseDocument

_TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".md", ".txt", ".tsv"}
_HTML_SUFFIXES = {".htm", ".html"}
_PDF_SUFFIXES = {".pdf"}
_DOCX_SUFFIXES = {".docx"}
_IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}

_CHAT_TEXT_KEYS = ("text", "message", "body", "content")
_CHAT_SENDER_KEYS = ("sender", "author", "from", "speaker", "name", "role")
_CHAT_TIME_KEYS = ("timestamp", "time", "date", "sent_at", "created_at")

_MAX_FILE_COUNT = 25
_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_TOTAL_BYTES = 40 * 1024 * 1024


class CaseBundleParseError(ValueError):
    """Raised when an uploaded case bundle cannot be normalized."""


@dataclass(slots=True)
class UploadedCaseFile:
    """Serializable representation of one uploaded file."""

    filename: str
    content_type: str
    payload: bytes


def parse_mapping_json(raw: str, field_name: str) -> dict[str, str]:
    """Parse a JSON object used to annotate uploaded files."""
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CaseBundleParseError(f"{field_name} must be valid JSON.") from exc
    if not isinstance(value, dict):
        raise CaseBundleParseError(f"{field_name} must be a JSON object keyed by filename.")
    return {_normalize_lookup_key(str(key)): str(item) for key, item in value.items()}


def build_case_documents_from_uploads(
    uploaded_files: list[UploadedCaseFile],
    *,
    document_contexts: dict[str, str] | None = None,
    document_dates: dict[str, str] | None = None,
    document_notes: dict[str, str] | None = None,
) -> tuple[list[MigrationCaseDocument], list[str]]:
    """Convert uploaded files into the document bundle used by the case workflow."""
    if not uploaded_files:
        raise CaseBundleParseError("At least one file must be uploaded.")
    if len(uploaded_files) > _MAX_FILE_COUNT:
        raise CaseBundleParseError(f"Upload up to {_MAX_FILE_COUNT} files per case bundle.")

    total_bytes = sum(len(item.payload) for item in uploaded_files)
    if total_bytes > _MAX_TOTAL_BYTES:
        raise CaseBundleParseError(
            f"Case bundle is too large. Keep total upload size under {_MAX_TOTAL_BYTES // (1024 * 1024)} MB."
        )

    normalized_contexts = document_contexts or {}
    normalized_dates = document_dates or {}
    normalized_notes = document_notes or {}

    documents: list[MigrationCaseDocument] = []
    warnings: list[str] = []

    for index, uploaded in enumerate(uploaded_files, start=1):
        if not uploaded.filename.strip():
            warnings.append(f"File {index} had no filename and was skipped.")
            continue
        if len(uploaded.payload) > _MAX_FILE_BYTES:
            raise CaseBundleParseError(
                f"{uploaded.filename} exceeds the per-file limit of {_MAX_FILE_BYTES // (1024 * 1024)} MB."
            )

        lookup_key = _normalize_lookup_key(uploaded.filename)
        operator_note = normalized_notes.get(lookup_key, "").strip()
        extracted_text = _extract_text(uploaded)
        file_warnings: list[str] = []

        if extracted_text and operator_note:
            text = f"{extracted_text}\n\nOperator note:\n{operator_note}"
        elif extracted_text:
            text = extracted_text
        elif operator_note:
            text = operator_note
            file_warnings.append(
                f"{uploaded.filename}: used operator note because automatic extraction returned no text."
            )
        else:
            text = _fallback_text(uploaded.filename)
            file_warnings.append(
                f"{uploaded.filename}: automatic extraction returned no text; added a file-level placeholder only."
            )

        if _suffix_for(uploaded.filename) in _IMAGE_SUFFIXES and not operator_note:
            file_warnings.append(
                f"{uploaded.filename}: image uploaded without OCR or operator note; add document_notes_json for better extraction."
            )

        cleaned_text = _normalize_whitespace(text)[:100_000]
        context = normalized_contexts.get(lookup_key, "").strip() or _guess_context(
            filename=uploaded.filename,
            content_type=uploaded.content_type,
            preview_text=cleaned_text,
        )
        title = _humanize_title(uploaded.filename)

        documents.append(
            MigrationCaseDocument(
                document_id=f"upload-{index:02d}",
                title=title,
                text=cleaned_text,
                context=context,
                captured_at=normalized_dates.get(lookup_key, "").strip(),
            )
        )
        warnings.extend(file_warnings)

    if not documents:
        raise CaseBundleParseError("No usable files were found in the upload bundle.")
    return documents, warnings


def _normalize_lookup_key(filename: str) -> str:
    return Path(filename).name.strip().lower()


def _suffix_for(filename: str) -> str:
    return Path(filename).suffix.lower()


def _humanize_title(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem or Path(filename).name


def _normalize_whitespace(text: str) -> str:
    collapsed = re.sub(r"\r\n?", "\n", text)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    collapsed = re.sub(r"[ \t]+", " ", collapsed)
    return collapsed.strip()


def _guess_context(*, filename: str, content_type: str, preview_text: str) -> str:
    lowered_name = filename.lower()
    lowered_preview = preview_text.lower()
    content_hint = f"{lowered_name} {content_type.lower()} {lowered_preview[:800]}"

    if any(token in content_hint for token in ["whatsapp", "viber", "messenger", "chat", "conversation"]):
        return "chat"
    if any(token in content_hint for token in ["interrogatory", "questionnaire", "intake form", "intake sheet", "written questions", "case intake", "case questionnaire"]):
        return "legal_intake"
    if any(token in content_hint for token in ["police report", "embassy", "consulate", "immigration department", "labour office", "labor office", "cease and desist", "demand letter", "government letter", "case officer"]):
        return "government_letter"
    if any(token in content_hint for token in ["passport", "visa", "work permit", "travel document", "identity card", "id card"]):
        return "identity_document"
    if any(token in content_hint for token in ["loan", "lender", "promissory", "interest", "debt", "repayment", "finance", "credit"]):
        return "debt_note"
    if any(token in content_hint for token in ["clinic", "medical", "hospital", "laboratory", "x-ray", "fit to work", "health screening", "med exam"]):
        return "medical_record"
    if any(token in content_hint for token in ["contract", "agreement", "offer letter", "salary"]):
        return "contract"
    if any(token in content_hint for token in ["receipt", "invoice", "payment", "transfer", "deposit"]):
        return "receipt"
    if any(token in content_hint for token in ["vacancy", "job posting", "apply now", "hiring"]):
        return "job_posting"
    if any(token in content_hint for token in ["certificate", "license", "permit", "clearance"]):
        return "certificate"
    if any(token in content_hint for token in ["agency", "recruitment", "manpower", "placement office", "broker"]):
        return "agency_record"
    if any(token in content_hint for token in ["interview", "narrative", "statement", "affidavit"]):
        return "narrative"
    return "document"


def _fallback_text(filename: str) -> str:
    title = _humanize_title(filename)
    return f"Uploaded file: {title}. Automatic text extraction was unavailable in the local fallback path."


def _extract_text(uploaded: UploadedCaseFile) -> str:
    suffix = _suffix_for(uploaded.filename)
    if suffix in _TEXT_SUFFIXES:
        return _extract_text_like(uploaded.filename, uploaded.payload)
    if suffix in _HTML_SUFFIXES or "html" in uploaded.content_type.lower():
        return _strip_html(_decode_bytes(uploaded.payload))
    if suffix in _PDF_SUFFIXES or "pdf" in uploaded.content_type.lower():
        return _extract_pdf_text(uploaded.payload)
    if suffix in _DOCX_SUFFIXES:
        return _extract_docx_text(uploaded.payload)
    if suffix in _IMAGE_SUFFIXES:
        return ""
    return _extract_text_like(uploaded.filename, uploaded.payload)


def _extract_text_like(filename: str, payload: bytes) -> str:
    suffix = _suffix_for(filename)
    decoded = _decode_bytes(payload)
    if suffix == ".json":
        return _json_to_text(decoded)
    if suffix == ".jsonl":
        return _jsonl_to_text(decoded)
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        return _table_to_text(decoded, delimiter=delimiter)
    return decoded


def _decode_bytes(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="ignore")


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _json_to_text(raw_json: str) -> str:
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        return raw_json
    structured = _structured_json_lines(value)
    if structured:
        return "\n".join(structured)
    strings = _collect_strings(value)
    return "\n".join(strings) if strings else raw_json


def _jsonl_to_text(raw_jsonl: str) -> str:
    strings: list[str] = []
    for line in raw_jsonl.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
            structured = _structured_json_lines(parsed)
            if structured:
                strings.extend(structured)
            else:
                strings.extend(_collect_strings(parsed))
        except json.JSONDecodeError:
            strings.append(stripped)
    return "\n".join(strings)


def _structured_json_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            lines.extend(_structured_json_lines(item))
        return lines

    if isinstance(value, dict):
        message_line = _format_message_like_dict(value)
        if message_line:
            return [message_line]

        nested_lines: list[str] = []
        for item in value.values():
            nested_lines.extend(_structured_json_lines(item))

        scalar_line = _format_scalar_dict(value)
        if nested_lines:
            return ([scalar_line] if scalar_line else []) + nested_lines
        return [scalar_line] if scalar_line else []

    return []


def _format_message_like_dict(value: dict[str, Any]) -> str:
    text = next((str(value[key]).strip() for key in _CHAT_TEXT_KEYS if isinstance(value.get(key), str) and str(value[key]).strip()), "")
    if not text:
        return ""

    sender = next((str(value[key]).strip() for key in _CHAT_SENDER_KEYS if value.get(key) is not None and str(value[key]).strip()), "")
    timestamp = next((str(value[key]).strip() for key in _CHAT_TIME_KEYS if value.get(key) is not None and str(value[key]).strip()), "")

    prefix_parts: list[str] = []
    if timestamp:
        prefix_parts.append(f"[{timestamp}]")
    if sender:
        prefix_parts.append(f"{sender}:")
    prefix = " ".join(prefix_parts)
    return f"{prefix} {text}".strip()


def _format_scalar_dict(value: dict[str, Any]) -> str:
    pairs: list[str] = []
    for key, item in value.items():
        if isinstance(item, (dict, list)) or item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        pairs.append(f"{str(key).strip()}: {text}")
    return " | ".join(pairs[:8])


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            key_text = str(key).strip()
            if key_text:
                strings.append(key_text)
            strings.extend(_collect_strings(item))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_collect_strings(item))
        return strings
    if value is None:
        return []
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    return []


def _table_to_text(raw_table: str, *, delimiter: str) -> str:
    reader = csv.reader(io.StringIO(raw_table), delimiter=delimiter)
    parsed_rows: list[list[str]] = []
    for row in reader:
        cleaned = [cell.strip() for cell in row if cell.strip()]
        if cleaned:
            parsed_rows.append(cleaned)

    if len(parsed_rows) >= 2:
        header = parsed_rows[0]
        data_rows = parsed_rows[1:]
        if header and all(len(row) <= len(header) for row in data_rows[:10]):
            rendered_rows: list[str] = []
            for row in data_rows:
                pairs = [
                    f"{header[index]}: {cell}"
                    for index, cell in enumerate(row)
                    if index < len(header) and header[index] and cell
                ]
                if pairs:
                    rendered_rows.append(" | ".join(pairs))
            if rendered_rows:
                return "\n".join(rendered_rows)

    return "\n".join(" | ".join(row) for row in parsed_rows)


def _extract_pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(payload), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(page.strip() for page in pages if page.strip())
    except Exception:
        return ""


def _extract_docx_text(payload: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            xml_members = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
            chunks: list[str] = []
            for member in xml_members:
                root = ET.fromstring(archive.read(member))
                text_nodes = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
                if text_nodes:
                    chunks.append(" ".join(text_nodes))
            return "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    except Exception:
        return ""
