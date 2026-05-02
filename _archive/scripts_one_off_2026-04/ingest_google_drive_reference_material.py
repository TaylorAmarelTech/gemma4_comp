from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Final
from xml.etree import ElementTree

import gdown
from bs4 import BeautifulSoup
from gdown.download import _get_session as _gdown_get_session
from gdown.download import _sanitize_filename as _gdown_sanitize_filename
from gdown.download_folder import _parse_embedded_folder_view
from gdown.exceptions import DownloadError as GDownDownloadError
from pydantic import BaseModel, Field


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
REFERENCE_ROOT: Final[Path] = REPO_ROOT / "_reference" / "google_drive_reference_material"
PACKAGE_SRCS: Final[tuple[Path, ...]] = (
    REPO_ROOT / "packages" / "duecare-llm-core" / "src",
    REPO_ROOT / "packages" / "duecare-llm-models" / "src",
    REPO_ROOT / "packages" / "duecare-llm-domains" / "src",
    REPO_ROOT / "packages" / "duecare-llm-tasks" / "src",
    REPO_ROOT / "packages" / "duecare-llm-agents" / "src",
    REPO_ROOT / "packages" / "duecare-llm-workflows" / "src",
    REPO_ROOT / "packages" / "duecare-llm-publishing" / "src",
    REPO_ROOT / "packages" / "duecare-llm" / "src",
)

for package_src in PACKAGE_SRCS:
    package_src_str = str(package_src)
    if package_src.exists() and package_src_str not in sys.path:
        sys.path.insert(0, package_src_str)

from duecare.agents.anonymizer.anonymizer import redact
from duecare.domains.pipeline.classifier import ClassifiedFact, classify_fact


TEXT_SUFFIXES: Final[set[str]] = {
    ".txt",
    ".md",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".csv",
    ".tsv",
    ".log",
}
IMAGE_SUFFIXES: Final[set[str]] = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
BINARY_OFFICE_SUFFIXES: Final[set[str]] = {".pdf", ".docx", ".pptx", ".xlsx"}
HTML_LIKE_PREFIXES: Final[tuple[bytes, ...]] = (
    b"<!doctype html",
    b"<html",
    b"<!doc",
)
FOLDER_ENUMERATION_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
)
FIRST_PASS_GMLC_TOP_LEVELS: Final[set[str]] = {
    "agencies - operation shutdown super predators",
    "atm schemes for money laundering",
    "google forms updated",
    "key facilitators - operation prevent exploitation",
    "medical clinics",
    "mila case",
    "money lenders - operation starve the hydra",
    "new wish employment agency",
    "ola",
    "philippines sec documents",
    "referral letters",
    "talent kenya agency",
    "template - law letters",
}
DEFERRED_GMLC_TOP_LEVELS: Final[set[str]] = {
    "bulk scans",
    "client folders - generic",
    "isaac starting folder",
    "misc",
    "msos - operation shutdown money transfers",
    "other cases - operation shutdown scams",
    "other ngos",
    "tcsps - operation shutdown company secretaries",
}
DEFAULT_COLLECTION_ITEM_LIMITS: Final[dict[str, int]] = {
    "gmlc_cases": 250,
}


class DriveCollection(BaseModel):
    label: str
    url: str


class DriveManifestItem(BaseModel):
    collection: str
    file_id: str
    relative_path: str
    remote_type: str = "application/octet-stream"


class DownloadRecord(BaseModel):
    collection: str
    file_id: str
    relative_path: str
    status: str
    local_path: str = ""
    mode: str = ""
    bytes_downloaded: int = 0
    message: str = ""


class DerivedArtifact(BaseModel):
    kind: str
    path: str


class ProcessedRecord(BaseModel):
    source_id: str
    collection: str
    relative_path: str
    local_path: str
    suffix: str
    extraction_status: str
    anonymization_status: str
    redaction_count: int = 0
    text_chars: int = 0
    document_kind: str
    audience: str
    context_hint: str
    template_candidate: bool
    example_candidate: bool
    tool_call_candidate: bool
    use_case_tags: list[str] = Field(default_factory=list)
    sector: str = "unknown"
    corridor: str = ""
    exploitation_type: str = "unknown"
    severity: str = "medium"
    confidence: float = 0.0
    artifacts: list[DerivedArtifact] = Field(default_factory=list)


class CollectionSummary(BaseModel):
    collection: str
    manifest_items: int = 0
    downloaded_files: int = 0
    downloaded_bytes: int = 0
    extracted_files: int = 0
    template_candidates: int = 0
    example_candidates: int = 0
    tool_call_candidates: int = 0
    unresolved_downloads: int = 0


class CollectionSelectionPlan(BaseModel):
    collection: str
    strategy: str = "full_recursive"
    total_candidates: int = 0
    selected_candidates: int = 0
    max_selected: int | None = None
    accessible_top_level: list[str] = Field(default_factory=list)
    included_top_level: list[str] = Field(default_factory=list)
    skipped_top_level: list[str] = Field(default_factory=list)
    skipped_folders: list[dict[str, str]] = Field(default_factory=list)


COLLECTIONS: Final[tuple[DriveCollection, ...]] = (
    DriveCollection(
        label="migrasia_binders_2017_present",
        url="https://drive.google.com/drive/u/0/folders/1m_P2OtvYFWdDBprscCzydSbi8ufw_mO1",
    ),
    DriveCollection(
        label="facebook_binder",
        url="https://drive.google.com/drive/u/0/folders/1Ov5pIUXXPfkGvBStSDX5zp35SlEBgzYK",
    ),
    DriveCollection(
        label="client_manual_templates_and_sample_complaints",
        url="https://drive.google.com/drive/folders/1MN9I83UuKm7K6E73lhPP6iDHGAQ6WO9c?usp=sharing",
    ),
    DriveCollection(
        label="gmlc_cases",
        url="https://drive.google.com/drive/folders/1soev7vNpF-ACwWR4NrjD3S89U3GA4TpK?usp=sharing",
    ),
)

PROPOSED_TOOL_SPECS: Final[dict[str, dict[str, Any]]] = {
    "extract_contract_terms": {
        "status": "proposed",
        "description": "Extract worker-charged fees, deduction schedules, passport retention language, employer identity, and contract duration from a migration contract.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "jurisdiction": {"type": "string"},
            },
            "required": ["text"],
        },
        "use_cases": ["contract_data_extraction"],
    },
    "analyze_chat_messages": {
        "status": "proposed",
        "description": "Parse chat logs for coercion, deadline pressure, fee escalation, threats, and document-control language.",
        "parameters": {
            "type": "object",
            "properties": {
                "messages": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
            },
            "required": ["messages"],
        },
        "use_cases": ["chat_message_analytics"],
    },
    "draft_overcharging_complaint": {
        "status": "proposed",
        "description": "Draft a complaint focused on illegal recruitment fees, excessive interest, or salary deductions charged to the worker.",
        "parameters": {
            "type": "object",
            "properties": {
                "facts": {"type": "string"},
                "target": {"type": "string"},
                "jurisdiction": {"type": "string"},
            },
            "required": ["facts", "target"],
        },
        "use_cases": ["overcharging"],
    },
    "draft_money_lender_complaint": {
        "status": "proposed",
        "description": "Draft a regulator-ready complaint against a lender or debt collector tied to migrant-worker fee schemes.",
        "parameters": {
            "type": "object",
            "properties": {
                "facts": {"type": "string"},
                "lender_name": {"type": "string"},
                "jurisdiction": {"type": "string"},
            },
            "required": ["facts"],
        },
        "use_cases": ["complaint_against_money_lender"],
    },
    "draft_agency_complaint": {
        "status": "proposed",
        "description": "Draft a labor-regulator or embassy complaint against a recruitment agency based on fees, document retention, or contract substitution evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "facts": {"type": "string"},
                "agency_name": {"type": "string"},
                "corridor": {"type": "string"},
            },
            "required": ["facts"],
        },
        "use_cases": ["complaint_against_agency"],
    },
}


def _safe_collection_map() -> dict[str, DriveCollection]:
    return {collection.label: collection for collection in COLLECTIONS}


def _collection_item_limit(collection: str, override: int | None = None) -> int | None:
    if override is not None:
        return override
    return DEFAULT_COLLECTION_ITEM_LIMITS.get(collection)


def _source_id(collection: str, relative_path: str) -> str:
    digest = hashlib.sha256(f"{collection}:{relative_path}".encode("utf-8")).hexdigest()
    return digest[:16]


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _file_head(path: Path, n_bytes: int = 256) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(n_bytes)
    except OSError:
        return b""


def _looks_like_html_payload(raw: bytes) -> bool:
    sniff = raw.lstrip().lower()
    return any(sniff.startswith(prefix) for prefix in HTML_LIKE_PREFIXES)


def _looks_like_invalid_binary_download(path: Path) -> bool:
    if path.suffix.lower() not in BINARY_OFFICE_SUFFIXES:
        return False
    head = _file_head(path)
    return not head or _looks_like_html_payload(head)


def _curl_binary() -> str | None:
    for name in ("curl.exe", "curl"):
        binary = shutil.which(name)
        if binary:
            return binary
    return None


def _download_with_curl(url: str, output_path: Path) -> tuple[bool, str, int]:
    binary = _curl_binary()
    if binary is None:
        return False, "curl is not available", 0

    _ensure_dir(output_path.parent)
    command = [binary, "-L", "--fail", url, "-o", str(output_path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        message = completed.stderr.strip() or completed.stdout.strip() or "curl failed"
        return False, message, 0

    size = output_path.stat().st_size if output_path.exists() else 0
    if size <= 0:
        output_path.unlink(missing_ok=True)
        return False, "downloaded zero-byte file", 0
    if _looks_like_invalid_binary_download(output_path):
        output_path.unlink(missing_ok=True)
        return False, "downloaded HTML interstitial instead of binary content", 0
    return True, "", size


def _native_export_targets(file_id: str) -> tuple[tuple[str, str, str], ...]:
    return (
        (
            f"https://docs.google.com/document/d/{file_id}/export?format=docx",
            ".docx",
            "google_doc_docx",
        ),
        (
            f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx",
            ".xlsx",
            "google_sheet_xlsx",
        ),
        (
            f"https://docs.google.com/presentation/d/{file_id}/export/pptx",
            ".pptx",
            "google_slide_pptx",
        ),
        (
            f"https://docs.google.com/document/d/{file_id}/export?format=pdf",
            ".pdf",
            "google_doc_pdf",
        ),
    )


def _top_level_name(relative_path: str) -> str:
    return relative_path.replace("\\", "/").split("/")[0].strip().lower()


def _top_level_folder_policy(collection: str, folder_name: str, selection_policy: str) -> tuple[bool, str]:
    if selection_policy == "all" or collection != "gmlc_cases":
        return True, "included by default"

    normalized = folder_name.strip().lower()
    if normalized in FIRST_PASS_GMLC_TOP_LEVELS:
        return True, "high-yield top-level folder"
    if normalized in DEFERRED_GMLC_TOP_LEVELS:
        return False, "deferred in first pass to protect disk space"
    return False, "not in first-pass allowlist"


def _manifest_item_priority(collection: str, relative_path: str, remote_type: str) -> tuple[int, str]:
    path_lower = relative_path.lower()
    suffix = Path(relative_path).suffix.lower()
    score = 0
    reasons: list[str] = []

    if collection == "gmlc_cases":
        top_level = _top_level_name(relative_path)
        if top_level in FIRST_PASS_GMLC_TOP_LEVELS:
            score += 4
            reasons.append("first-pass top-level")
        if top_level in DEFERRED_GMLC_TOP_LEVELS:
            score -= 8
            reasons.append("deferred top-level")

    if suffix in {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".json", ".jsonl"}:
        score += 3
        reasons.append("text-bearing format")
    elif suffix in {".pptx", ".xlsx", ".csv", ".tsv"}:
        score += 1
        reasons.append("structured office format")
    elif suffix in IMAGE_SUFFIXES:
        score -= 4
        reasons.append("image-heavy asset")
    elif suffix == "":
        score += 1
        reasons.append("extensionless or Google-native file")

    strong_keywords = (
        "template",
        "letter",
        "complaint",
        "demand",
        "referral",
        "form",
        "manual",
        "instructions",
        "compliance",
        "pdpo",
        "dar",
        "privacy",
        "agency",
        "lender",
        "loan",
        "sec",
        "owtel",
        "customs",
        "bank account",
    )
    medium_keywords = (
        "case",
        "statement",
        "narrative",
        "medical",
        "facebook",
        "messenger",
        "whatsapp",
        "evidence",
        "facilitator",
        "license",
    )
    low_yield_keywords = (
        "photo",
        "photos",
        "scan",
        "scans",
        "page 1",
        "page 2",
        "page 3",
        "qr code",
        "screenshot",
        "messenger name",
        "upload (unorganized)",
    )
    if any(keyword in path_lower for keyword in strong_keywords):
        score += 5
        reasons.append("strong legal/template keyword")
    if any(keyword in path_lower for keyword in medium_keywords):
        score += 2
        reasons.append("casework keyword")
    if any(keyword in path_lower for keyword in low_yield_keywords):
        score -= 3
        reasons.append("likely scan or low-yield artifact")

    if remote_type == "application/vnd.google-apps.folder":
        score -= 100

    return score, ", ".join(reasons) or "neutral"


def _select_manifest_items(
    collection: str,
    manifest_items: list[DriveManifestItem],
    *,
    selection_policy: str,
    max_selected_per_collection: int | None = None,
    existing_plan: CollectionSelectionPlan | None = None,
) -> tuple[list[DriveManifestItem], CollectionSelectionPlan]:
    plan = existing_plan or CollectionSelectionPlan(collection=collection)
    plan.strategy = "disk_conscious_first_pass" if selection_policy == "auto" and collection == "gmlc_cases" else "full_recursive"
    plan.total_candidates = len(manifest_items)
    plan.max_selected = _collection_item_limit(collection, max_selected_per_collection)

    if selection_policy == "all" or collection != "gmlc_cases":
        plan.selected_candidates = len(manifest_items)
        return manifest_items, plan

    ranked_items: list[tuple[int, str, DriveManifestItem]] = []
    for item in manifest_items:
        score, reason = _manifest_item_priority(collection, item.relative_path, item.remote_type)
        if score >= 4:
            ranked_items.append((score, reason, item))

    ranked_items.sort(key=lambda entry: (-entry[0], entry[2].relative_path.lower()))
    selected_items = [item for _, _, item in ranked_items]
    if plan.max_selected is not None:
        selected_items = selected_items[: plan.max_selected]
    plan.selected_candidates = len(selected_items)
    return selected_items, plan


def _build_manifest_via_embedded_view(
    collection: DriveCollection,
    *,
    selection_policy: str,
    max_selected_per_collection: int | None = None,
) -> tuple[list[DriveManifestItem], CollectionSelectionPlan]:
    sess, _ = _gdown_get_session(
        proxy=None,
        use_cookies=True,
        user_agent=FOLDER_ENUMERATION_USER_AGENT,
    )
    root_id = collection.url.split("/")[-1].split("?")[0]
    plan = CollectionSelectionPlan(collection=collection.label)

    try:
        _, children = _parse_embedded_folder_view(sess=sess, folder_id=root_id, verify=True)
    except GDownDownloadError as exc:
        plan.skipped_folders.append(
            {
                "folder_id": root_id,
                "path": collection.label,
                "reason": str(exc),
            }
        )
        return [], plan

    candidate_items: list[DriveManifestItem] = []

    def walk_folder(folder_id: str, prefix: str, depth: int = 0) -> None:
        try:
            _, nested_children = _parse_embedded_folder_view(sess=sess, folder_id=folder_id, verify=True)
        except GDownDownloadError as exc:
            plan.skipped_folders.append(
                {
                    "folder_id": folder_id,
                    "path": prefix or collection.label,
                    "reason": str(exc),
                }
            )
            return

        for child_id, child_name, child_type in nested_children:
            safe_name = _gdown_sanitize_filename(filename=child_name)
            child_path = f"{prefix}/{safe_name}".strip("/") if prefix else safe_name
            if child_type == "application/vnd.google-apps.folder":
                walk_folder(child_id, child_path, depth + 1)
                continue
            candidate_items.append(
                DriveManifestItem(
                    collection=collection.label,
                    file_id=child_id,
                    relative_path=child_path,
                    remote_type=child_type,
                )
            )

    for child_id, child_name, child_type in children:
        safe_name = _gdown_sanitize_filename(filename=child_name)
        if child_type == "application/vnd.google-apps.folder":
            plan.accessible_top_level.append(safe_name)
            include_folder, reason = _top_level_folder_policy(collection.label, safe_name, selection_policy)
            if not include_folder:
                plan.skipped_top_level.append(f"{safe_name}: {reason}")
                continue
            plan.included_top_level.append(safe_name)
            walk_folder(child_id, safe_name, 1)
            continue

        keep_item, reason = _manifest_item_priority(collection.label, safe_name, child_type)
        plan.accessible_top_level.append(f"FILE:{safe_name}")
        if selection_policy == "all" or collection.label != "gmlc_cases" or keep_item >= 4:
            candidate_items.append(
                DriveManifestItem(
                    collection=collection.label,
                    file_id=child_id,
                    relative_path=safe_name,
                    remote_type=child_type,
                )
            )
            plan.included_top_level.append(f"FILE:{safe_name}")
        else:
            plan.skipped_top_level.append(f"FILE:{safe_name}: {reason}")

    return _select_manifest_items(
        collection.label,
        candidate_items,
        selection_policy=selection_policy,
        max_selected_per_collection=max_selected_per_collection,
        existing_plan=plan,
    )


def build_manifest(
    *,
    collections: list[str] | None = None,
    selection_policy: str = "auto",
    max_selected_per_collection: int | None = None,
) -> tuple[list[DriveManifestItem], dict[str, CollectionSelectionPlan]]:
    selected = _safe_collection_map()
    if collections:
        selected = {label: selected[label] for label in collections if label in selected}

    manifest: list[DriveManifestItem] = []
    plans: dict[str, CollectionSelectionPlan] = {}
    for collection in selected.values():
        try:
            items = gdown.download_folder(url=collection.url, skip_download=True, quiet=True)
            collection_manifest = [
                DriveManifestItem(
                    collection=collection.label,
                    file_id=item.id,
                    relative_path=item.path.replace("\\", "/"),
                )
                for item in items
            ]
            collection_manifest, plan = _select_manifest_items(
                collection.label,
                collection_manifest,
                selection_policy=selection_policy,
                max_selected_per_collection=max_selected_per_collection,
            )
        except Exception:
            collection_manifest, plan = _build_manifest_via_embedded_view(
                collection,
                selection_policy=selection_policy,
                max_selected_per_collection=max_selected_per_collection,
            )
        manifest.extend(collection_manifest)
        plans[collection.label] = plan
    return manifest, plans


def sync_downloads(
    *,
    root: Path,
    manifest: list[DriveManifestItem],
    limit: int | None = None,
) -> list[DownloadRecord]:
    records: list[DownloadRecord] = []
    for item in manifest[:limit] if limit else manifest:
        collection_root = root / item.collection
        target = collection_root / Path(item.relative_path)
        if target.exists() and target.stat().st_size > 0 and not _looks_like_invalid_binary_download(target):
            records.append(
                DownloadRecord(
                    collection=item.collection,
                    file_id=item.file_id,
                    relative_path=item.relative_path,
                    status="existing",
                    local_path=str(target),
                    bytes_downloaded=target.stat().st_size,
                )
            )
            continue

        candidate_downloads: list[tuple[str, Path, str]] = []
        candidate_downloads.append(
            (f"https://drive.google.com/uc?export=download&id={item.file_id}", target, "direct_file")
        )
        for export_url, extension, mode in _native_export_targets(item.file_id):
            export_target = target if target.suffix.lower() == extension else target.with_suffix(extension)
            if any(existing_target == export_target for _, existing_target, _ in candidate_downloads):
                continue
            candidate_downloads.append((export_url, export_target, mode))

        downloaded = False
        last_message = ""
        last_mode = ""
        for candidate_url, candidate_target, mode in candidate_downloads:
            success, message, size = _download_with_curl(candidate_url, candidate_target)
            if success:
                records.append(
                    DownloadRecord(
                        collection=item.collection,
                        file_id=item.file_id,
                        relative_path=str(candidate_target.relative_to(collection_root)).replace("\\", "/"),
                        status="downloaded",
                        local_path=str(candidate_target),
                        mode=mode,
                        bytes_downloaded=size,
                    )
                )
                downloaded = True
                break
            last_message = message
            last_mode = mode
        if not downloaded:
            records.append(
                DownloadRecord(
                    collection=item.collection,
                    file_id=item.file_id,
                    relative_path=item.relative_path,
                    status="unresolved",
                    mode=last_mode or "native_export",
                    message=last_message or "native export attempts failed",
                )
            )
    return records


def _extract_docx_text(path: Path) -> str:
    try:
        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        with zipfile.ZipFile(path) as archive:
            xml_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("word/") and name.endswith(".xml")
            )
            blocks: list[str] = []
            for xml_name in xml_names:
                if not any(token in xml_name for token in ("document", "header", "footer", "footnotes", "endnotes")):
                    continue
                root = ElementTree.fromstring(archive.read(xml_name))
                for paragraph in root.findall(".//w:p", namespaces):
                    text_nodes = [node.text or "" for node in paragraph.findall(".//w:t", namespaces)]
                    paragraph_text = "".join(text_nodes).strip()
                    if paragraph_text:
                        blocks.append(paragraph_text)
            return _clean_text("\n".join(blocks))
    except Exception:
        return ""


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return _clean_text("\n\n".join(pages))
    except Exception:
        return ""


def _extract_html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    return _clean_text(soup.get_text("\n"))


def extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in BINARY_OFFICE_SUFFIXES and _looks_like_invalid_binary_download(path):
        return "", "download_interstitial"
    if suffix == ".docx":
        text = _extract_docx_text(path)
        return text, "docx" if text else "docx_empty"
    if suffix == ".pdf":
        text = _extract_pdf_text(path)
        return text, "pdf" if text else "pdf_empty"
    if suffix in {".html", ".htm"}:
        text = _extract_html_text(path)
        return text, "html" if text else "html_empty"
    if suffix in TEXT_SUFFIXES:
        text = _clean_text(path.read_text(encoding="utf-8", errors="ignore"))
        return text, "text" if text else "text_empty"
    if suffix in IMAGE_SUFFIXES or suffix in {".drawio", ".pptx", ".xlsx"}:
        return "", "binary_unsupported"
    return "", "unsupported"


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def infer_document_kind(relative_path: str, text: str) -> str:
    combined = f"{relative_path} {text[:4000]}".lower()
    if _contains_any(combined, ("cease and desist", "cease_and_desist")):
        return "cease_and_desist_template"
    if "support letter" in combined:
        return "support_letter_template"
    if "pdpo" in combined and _contains_any(combined, ("request", "complaint", "form", "response", "dar")):
        return "privacy_complaint_template"
    if _contains_any(combined, ("client intake manual", "intake manual", "manual")):
        return "intake_manual"
    if "narrative" in combined:
        return "complaint_narrative"
    if "complaint" in combined and "template" in combined:
        return "complaint_template"
    if "complaint" in combined:
        return "complaint_example"
    if "binder" in combined:
        return "evidence_binder"
    if "letter" in combined:
        return "regulator_letter"
    if _contains_any(combined, ("diagram", ".drawio", ".jpg", ".png", ".jpeg")):
        return "diagram_reference"
    return "reference_document"


def infer_audience(document_kind: str) -> str:
    audience_map = {
        "cease_and_desist_template": "Company legal or compliance team",
        "support_letter_template": "NGO advocate or legal aid partner",
        "privacy_complaint_template": "Privacy regulator or data-protection officer",
        "intake_manual": "NGO case worker",
        "complaint_narrative": "Paralegal or affidavit drafter",
        "complaint_template": "Regulator or platform complaints desk",
        "complaint_example": "Researcher reviewing complaint patterns",
        "evidence_binder": "Investigator or NGO case lead",
        "regulator_letter": "Financial, labor, or law-enforcement regulator",
        "diagram_reference": "Researcher or explainer author",
    }
    return audience_map.get(document_kind, "Research or template library")


def infer_context_hint(document_kind: str, text: str) -> str:
    text_lower = text.lower()
    if _contains_any(
        text_lower,
        ("receipt", "fee paid", "paid by worker", "placement fee", "recruitment fee"),
    ):
        return "receipt"
    if _contains_any(text_lower, ("employment contract", "contract period", "employer will", "salary deduction")):
        return "contract"
    if _contains_any(text_lower, ("chat", "message", "whatsapp", "facebook", "messenger")):
        return "chat"
    if document_kind in {"complaint_template", "complaint_example", "complaint_narrative"}:
        return "complaint"
    if document_kind == "support_letter_template":
        return "support_letter"
    return "document"


def infer_use_case_tags(document_kind: str, text: str, context_hint: str) -> list[str]:
    combined = f"{document_kind} {context_hint} {text[:6000]}".lower()
    tags: list[str] = []
    if _contains_any(
        combined,
        (
            "overcharg",
            "excessive fee",
            "recruitment fee",
            "placement fee",
            "service charge",
            "interest",
            "salary deduction",
        ),
    ):
        tags.append("overcharging")
    if context_hint == "contract" or _contains_any(
        combined,
        (
            "employment contract",
            "contract period",
            "salary deduction",
            "passport retention",
            "employer will",
        ),
    ):
        tags.append("contract_data_extraction")
    if context_hint == "chat" or _contains_any(
        combined,
        ("messenger", "facebook", "whatsapp", "chat", "message thread", "pay now or", "deadline"),
    ):
        tags.append("chat_message_analytics")
    if _contains_any(
        combined,
        (
            "money lender",
            "owtel",
            "ace power",
            "lucky peso",
            "rich credit",
            "elend",
            "loan",
            "lending",
            "interest rate",
        ),
    ):
        tags.append("complaint_against_money_lender")
    if _contains_any(
        combined,
        (
            "agency",
            "recruitment agency",
            "employment agency",
            "recruiter",
            "placement fee",
            "deployment",
        ),
    ):
        tags.append("complaint_against_agency")
    return _dedupe(tags)


def _is_template_candidate(document_kind: str, text: str) -> bool:
    if document_kind in {
        "cease_and_desist_template",
        "support_letter_template",
        "privacy_complaint_template",
        "complaint_template",
        "intake_manual",
        "complaint_narrative",
    }:
        return True
    return "template" in text.lower()


def _is_example_candidate(document_kind: str, text: str) -> bool:
    return document_kind in {
        "complaint_example",
        "complaint_narrative",
        "evidence_binder",
        "regulator_letter",
        "diagram_reference",
        "support_letter_template",
    } or len(text) >= 500


def _is_tool_call_candidate(document_kind: str, text: str) -> bool:
    keywords = ("fee", "passport", "complaint", "law", "regulator", "support letter")
    return document_kind != "diagram_reference" and _contains_any(text.lower(), keywords)


def _classify_document(document_kind: str, text: str) -> ClassifiedFact:
    context = text[:5000]
    value = document_kind.replace("_", " ")
    return classify_fact(fact_type="reference_document", value=value, context=context)


def _artifact_text_header(record: ProcessedRecord) -> str:
    return (
        f"Source ID: {record.source_id}\n"
        f"Collection: {record.collection}\n"
        f"Document kind: {record.document_kind}\n"
        f"Audience: {record.audience}\n"
        f"Context hint: {record.context_hint}\n"
        f"Use-case tags: {', '.join(record.use_case_tags) or 'none'}\n"
        f"Sector: {record.sector}\n"
        f"Corridor: {record.corridor or 'unspecified'}\n"
        f"Exploitation type: {record.exploitation_type}\n"
        f"Severity: {record.severity}\n"
    )


def _write_text_artifact(path: Path, header: str, body: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(f"{header}\n---\n\n{body}\n", encoding="utf-8")


def _country_code(record: ProcessedRecord, text: str) -> str:
    if record.corridor:
        return record.corridor.split("-")[0].upper()
    text_upper = text.upper()
    for token in ("PH", "HK", "SG", "SA", "AE", "QA", "MY"):
        if token in text_upper:
            return token
    return "PH"


def _scenario_from_text(record: ProcessedRecord, text: str) -> str:
    text_lower = text.lower()
    if "passport" in text_lower:
        return "passport_retention"
    if "salary deduction" in text_lower or "deduct" in text_lower:
        return "salary_deduction"
    if "debt" in text_lower or "loan" in text_lower or "interest" in text_lower:
        return "debt_bondage"
    if "contract substitution" in text_lower:
        return "contract_substitution"
    if "wage" in text_lower and "withhold" in text_lower:
        return "wage_withholding"
    return "recruitment_fee"


def _extract_fee_amount_and_currency(text: str) -> tuple[float, str]:
    pattern = re.compile(
        r"(?:(PHP|HKD|SGD|SAR|AED|QAR|USD)\s*([0-9][0-9,]*(?:\.[0-9]+)?))|(?:([0-9][0-9,]*(?:\.[0-9]+)?)\s*(PHP|HKD|SGD|SAR|AED|QAR|USD))",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return 0.0, "PHP"
    currency = (match.group(1) or match.group(4) or "PHP").upper()
    amount_text = match.group(2) or match.group(3) or "0"
    try:
        return float(amount_text.replace(",", "")), currency
    except ValueError:
        return 0.0, currency


def _worker_type_for_record(record: ProcessedRecord) -> str:
    return {
        "domestic_work": "domestic",
        "construction": "construction",
        "agriculture": "agriculture",
        "fishing": "fishing",
        "manufacturing": "factory",
    }.get(record.sector, "domestic")


def _build_tool_call_examples(record: ProcessedRecord, anonymized_text: str) -> list[dict]:
    excerpt = anonymized_text[:2000]
    country = _country_code(record, anonymized_text)
    scenario = _scenario_from_text(record, anonymized_text)
    jurisdiction = record.corridor.replace("-", "_") if record.corridor else country
    fee_amount, currency = _extract_fee_amount_and_currency(anonymized_text)
    examples = [
        {
            "source_id": record.source_id,
            "tool_name": "identify_trafficking_indicators",
            "arguments": {"text": excerpt},
            "expected": {
                "document_kind": record.document_kind,
                "exploitation_type": record.exploitation_type,
                "severity": record.severity,
            },
        },
        {
            "source_id": record.source_id,
            "tool_name": "score_exploitation_risk",
            "arguments": {"text": excerpt},
            "expected": {"sector": record.sector, "severity": record.severity},
        },
        {
            "source_id": record.source_id,
            "tool_name": "check_legal_framework",
            "arguments": {
                "jurisdiction": jurisdiction,
                "scenario": scenario,
            },
            "expected": {"audience": record.audience, "corridor": record.corridor or ""},
        },
    ]
    if any(tag in record.use_case_tags for tag in ("overcharging", "complaint_against_agency", "complaint_against_money_lender")):
        examples.append(
            {
                "source_id": record.source_id,
                "tool_name": "check_fee_legality",
                "arguments": {
                    "country": country,
                    "fee_amount": fee_amount,
                    "currency": currency,
                    "worker_type": _worker_type_for_record(record),
                },
                "expected": {"document_kind": record.document_kind, "severity": record.severity},
            }
        )
    examples.append(
        {
            "source_id": record.source_id,
            "tool_name": "lookup_hotline",
            "arguments": {"country": country},
            "expected": {"audience": record.audience},
        }
    )
    return examples


def _build_specific_tool_call_scenarios(record: ProcessedRecord, anonymized_text: str) -> list[dict]:
    excerpt = anonymized_text[:1500]
    country = _country_code(record, anonymized_text)
    scenario = _scenario_from_text(record, anonymized_text)
    jurisdiction = record.corridor.replace("-", "_") if record.corridor else country
    use_case_flows: list[dict] = []

    for tag in record.use_case_tags:
        if tag == "overcharging":
            use_case_flows.append(
                {
                    "source_id": record.source_id,
                    "use_case": tag,
                    "status": "supported",
                    "tool_flow": [
                        "check_fee_legality",
                        "identify_trafficking_indicators",
                        "check_legal_framework",
                        "score_exploitation_risk",
                        "lookup_hotline",
                    ],
                    "prompt": excerpt,
                }
            )
        elif tag == "contract_data_extraction":
            use_case_flows.append(
                {
                    "source_id": record.source_id,
                    "use_case": tag,
                    "status": "proposed_extension",
                    "tool_flow": [
                        "extract_contract_terms",
                        "identify_trafficking_indicators",
                        "check_legal_framework",
                        "score_exploitation_risk",
                    ],
                    "arguments": {"jurisdiction": jurisdiction, "scenario": scenario},
                }
            )
        elif tag == "chat_message_analytics":
            use_case_flows.append(
                {
                    "source_id": record.source_id,
                    "use_case": tag,
                    "status": "proposed_extension",
                    "tool_flow": [
                        "analyze_chat_messages",
                        "identify_trafficking_indicators",
                        "score_exploitation_risk",
                        "lookup_hotline",
                    ],
                    "prompt": excerpt,
                }
            )
        elif tag == "complaint_against_money_lender":
            use_case_flows.append(
                {
                    "source_id": record.source_id,
                    "use_case": tag,
                    "status": "proposed_extension",
                    "tool_flow": [
                        "draft_money_lender_complaint",
                        "check_legal_framework",
                        "identify_trafficking_indicators",
                        "lookup_hotline",
                    ],
                    "arguments": {"jurisdiction": jurisdiction},
                }
            )
        elif tag == "complaint_against_agency":
            use_case_flows.append(
                {
                    "source_id": record.source_id,
                    "use_case": tag,
                    "status": "proposed_extension",
                    "tool_flow": [
                        "draft_agency_complaint",
                        "check_fee_legality",
                        "check_legal_framework",
                        "identify_trafficking_indicators",
                    ],
                    "arguments": {"jurisdiction": jurisdiction},
                }
            )
    return use_case_flows


def _render_use_case_template(record: ProcessedRecord, anonymized_text: str, use_case: str) -> str:
    excerpt = anonymized_text[:1800].strip()
    jurisdiction = record.corridor or "unspecified corridor"
    if use_case == "overcharging":
        return (
            f"Template: Overcharging complaint\n\n"
            f"Subject: Request for review of worker-charged fees and deductions in {jurisdiction}\n\n"
            f"Facts to include:\n- The worker was asked to pay or finance fees before or after deployment.\n"
            f"- The amount, currency, interest, or deduction schedule should be itemized from the evidence.\n"
            f"- Explain why the charge appears unlawful or coercive.\n\n"
            f"Evidence excerpt:\n{excerpt}\n\n"
            f"Requested relief:\n- Stop further fee collection or deductions.\n- Review whether the fees breach recruitment-law or wage-protection rules.\n"
        )
    if use_case == "contract_data_extraction":
        return (
            "Template: Contract data extraction worksheet\n\n"
            "Extract these fields from the contract evidence:\n"
            "- employer name\n- recruitment agency\n- worker-charged fee amount\n- deduction schedule\n- passport retention clause\n- contract duration\n- jurisdiction and corridor\n\n"
            f"Evidence excerpt:\n{excerpt}\n"
        )
    if use_case == "chat_message_analytics":
        return (
            "Template: Chat message analytics worksheet\n\n"
            "Review the chat log for:\n"
            "- payment demands\n- urgency or deadline pressure\n- threats, deportation language, or passport leverage\n- platform/account identifiers\n- escalation path to hotline or regulator\n\n"
            f"Evidence excerpt:\n{excerpt}\n"
        )
    if use_case == "complaint_against_money_lender":
        return (
            f"Template: Complaint against money lender\n\n"
            f"Subject: Complaint regarding lending-linked recruitment exploitation in {jurisdiction}\n\n"
            f"Facts to include:\n- identify the lender or collection channel\n- explain the fee or loan origin\n- document interest escalation, coercion, or salary deductions\n\n"
            f"Evidence excerpt:\n{excerpt}\n\n"
            "Requested action:\n- investigate the lender and related entities\n- stop collections tied to unlawful recruitment charges\n"
        )
    if use_case == "complaint_against_agency":
        return (
            f"Template: Complaint against recruitment agency\n\n"
            f"Subject: Request for investigation of recruitment agency conduct in {jurisdiction}\n\n"
            f"Facts to include:\n- agency or recruiter identity\n- worker-paid fees or deductions\n- document retention, deception, or contract substitution\n\n"
            f"Evidence excerpt:\n{excerpt}\n\n"
            "Requested action:\n- verify licensing and compliance status\n- review fee collection, contract terms, and any document-control conduct\n"
        )
    return ""


def process_reference_root(root: Path) -> tuple[list[ProcessedRecord], dict[str, CollectionSummary]]:
    processed_root = root / "processed"
    templates_root = root / "templates"
    examples_root = root / "examples"
    _ensure_dir(processed_root)
    _ensure_dir(templates_root)
    _ensure_dir(examples_root)

    migration_case_examples: list[dict] = []
    tool_call_examples: list[dict] = []
    specific_tool_call_scenarios: list[dict] = []
    records: list[ProcessedRecord] = []
    summaries: dict[str, CollectionSummary] = {
        collection.label: CollectionSummary(collection=collection.label) for collection in COLLECTIONS
    }

    reserved_dirs = {"processed", "templates", "examples", "_probe"}
    for collection_root in sorted(path for path in root.iterdir() if path.is_dir() and path.name not in reserved_dirs):
        summary = summaries.setdefault(collection_root.name, CollectionSummary(collection=collection_root.name))
        for path in sorted(collection_root.rglob("*")):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(collection_root)).replace("\\", "/")
            text, extraction_status = extract_text(path)
            if not text:
                records.append(
                    ProcessedRecord(
                        source_id=_source_id(collection_root.name, relative_path),
                        collection=collection_root.name,
                        relative_path=relative_path,
                        local_path=str(path),
                        suffix=path.suffix.lower(),
                        extraction_status=extraction_status,
                        anonymization_status="not_applicable",
                        document_kind=infer_document_kind(relative_path, ""),
                        audience=infer_audience(infer_document_kind(relative_path, "")),
                        context_hint="document",
                        template_candidate=False,
                        example_candidate=False,
                        tool_call_candidate=False,
                    )
                )
                continue

            anonymized_text, audit_records = redact(text)
            document_kind = infer_document_kind(relative_path, anonymized_text)
            audience = infer_audience(document_kind)
            context_hint = infer_context_hint(document_kind, anonymized_text)
            use_case_tags = infer_use_case_tags(document_kind, anonymized_text, context_hint)
            classification = _classify_document(document_kind, anonymized_text)
            record = ProcessedRecord(
                source_id=_source_id(collection_root.name, relative_path),
                collection=collection_root.name,
                relative_path=relative_path,
                local_path=str(path),
                suffix=path.suffix.lower(),
                extraction_status=extraction_status,
                anonymization_status="redacted" if audit_records else "clean",
                redaction_count=len(audit_records),
                text_chars=len(anonymized_text),
                document_kind=document_kind,
                audience=audience,
                context_hint=context_hint,
                template_candidate=_is_template_candidate(document_kind, anonymized_text),
                example_candidate=_is_example_candidate(document_kind, anonymized_text),
                tool_call_candidate=_is_tool_call_candidate(document_kind, anonymized_text),
                use_case_tags=use_case_tags,
                sector=classification.sector.value,
                corridor=classification.corridor,
                exploitation_type=classification.exploitation_type.value,
                severity=classification.severity.value,
                confidence=classification.confidence,
            )

            summary.extracted_files += 1
            summary.downloaded_files += 1
            summary.downloaded_bytes += path.stat().st_size

            anonymized_path = processed_root / "anonymized_text" / collection_root.name / f"{record.source_id}.txt"
            _write_text_artifact(anonymized_path, _artifact_text_header(record), anonymized_text)
            record.artifacts.append(DerivedArtifact(kind="anonymized_text", path=str(anonymized_path)))

            if record.template_candidate:
                template_path = templates_root / record.document_kind / f"{record.source_id}.md"
                _write_text_artifact(template_path, _artifact_text_header(record), anonymized_text)
                record.artifacts.append(DerivedArtifact(kind="template", path=str(template_path)))
                summary.template_candidates += 1

            if record.example_candidate:
                example_path = examples_root / record.document_kind / f"{record.source_id}.md"
                _write_text_artifact(example_path, _artifact_text_header(record), anonymized_text)
                record.artifacts.append(DerivedArtifact(kind="example", path=str(example_path)))
                summary.example_candidates += 1

            if record.tool_call_candidate:
                tool_call_examples.extend(_build_tool_call_examples(record, anonymized_text))
                specific_tool_call_scenarios.extend(_build_specific_tool_call_scenarios(record, anonymized_text))
                summary.tool_call_candidates += 1

            for use_case in record.use_case_tags:
                template_body = _render_use_case_template(record, anonymized_text, use_case)
                if not template_body:
                    continue
                use_case_path = templates_root / use_case / f"{record.source_id}.md"
                _write_text_artifact(use_case_path, _artifact_text_header(record), template_body)
                record.artifacts.append(DerivedArtifact(kind=f"use_case_template:{use_case}", path=str(use_case_path)))

            migration_case_examples.append(
                {
                    "document_id": record.source_id,
                    "title": f"{record.document_kind.replace('_', ' ').title()} Example {record.source_id[:6]}",
                    "context": record.context_hint,
                    "text": anonymized_text[:4000],
                    "collection": record.collection,
                    "document_kind": record.document_kind,
                    "corridor": record.corridor,
                }
            )
            records.append(record)

    manifest_path = processed_root / "document_manifest.jsonl"
    manifest_lines = [record.model_dump_json() for record in records]
    manifest_path.write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")

    migration_path = examples_root / "migration_case_documents.jsonl"
    migration_lines = [json.dumps(item, ensure_ascii=True) for item in migration_case_examples]
    migration_path.write_text("\n".join(migration_lines) + ("\n" if migration_lines else ""), encoding="utf-8")

    tool_calls_path = examples_root / "tool_call_examples.jsonl"
    tool_call_lines = [json.dumps(item, ensure_ascii=True) for item in tool_call_examples]
    tool_calls_path.write_text("\n".join(tool_call_lines) + ("\n" if tool_call_lines else ""), encoding="utf-8")

    specific_scenarios_path = examples_root / "specific_tool_call_scenarios.jsonl"
    specific_scenario_lines = [json.dumps(item, ensure_ascii=True) for item in specific_tool_call_scenarios]
    specific_scenarios_path.write_text(
        "\n".join(specific_scenario_lines) + ("\n" if specific_scenario_lines else ""),
        encoding="utf-8",
    )

    tool_spec_path = processed_root / "proposed_tool_specs.json"
    tool_spec_path.write_text(json.dumps(PROPOSED_TOOL_SPECS, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return records, summaries


def _write_download_outputs(
    root: Path,
    manifest: list[DriveManifestItem],
    downloads: list[DownloadRecord],
    selection_plans: dict[str, CollectionSelectionPlan],
) -> None:
    output_root = root / "processed"
    _ensure_dir(output_root)
    manifest_path = output_root / "drive_manifest.jsonl"
    manifest_lines = [item.model_dump_json() for item in manifest]
    manifest_path.write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")

    downloads_path = output_root / "download_status.jsonl"
    download_lines = [item.model_dump_json() for item in downloads]
    downloads_path.write_text("\n".join(download_lines) + ("\n" if download_lines else ""), encoding="utf-8")

    selection_path = output_root / "drive_selection_plan.json"
    selection_payload = {label: plan.model_dump() for label, plan in selection_plans.items()}
    selection_path.write_text(json.dumps(selection_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_summary(root: Path, summaries: dict[str, CollectionSummary], records: list[ProcessedRecord]) -> Path:
    output_root = root / "processed"
    _ensure_dir(output_root)
    summary_payload = {
        "collections": {label: summary.model_dump() for label, summary in summaries.items()},
        "totals": {
            "processed_records": len(records),
            "template_candidates": sum(1 for record in records if record.template_candidate),
            "example_candidates": sum(1 for record in records if record.example_candidate),
            "tool_call_candidates": sum(1 for record in records if record.tool_call_candidate),
            "redacted_records": sum(1 for record in records if record.redaction_count > 0),
            "use_case_tags": {
                tag: sum(1 for record in records if tag in record.use_case_tags)
                for tag in sorted({tag for record in records for tag in record.use_case_tags})
            },
        },
    }
    summary_path = output_root / "ingest_summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and process Google Drive reference material.")
    parser.add_argument("--root", type=Path, default=REFERENCE_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-process", action="store_true")
    parser.add_argument("--limit-downloads", type=int, default=None)
    parser.add_argument(
        "--selection-policy",
        choices=("auto", "all"),
        default="auto",
        help="auto keeps full sync for normal collections and a disk-conscious first pass for very large archives; all disables selection.",
    )
    parser.add_argument(
        "--max-selected-per-collection",
        type=int,
        default=None,
        help="Optional hard cap on the number of manifest items to retain per collection before download.",
    )
    parser.add_argument(
        "--collections",
        nargs="*",
        default=None,
        help="Optional subset of collection labels to sync or process.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    _ensure_dir(root)

    manifest: list[DriveManifestItem] = []
    downloads: list[DownloadRecord] = []
    selection_plans: dict[str, CollectionSelectionPlan] = {}
    summaries: dict[str, CollectionSummary] = {
        collection.label: CollectionSummary(collection=collection.label) for collection in COLLECTIONS
    }

    if not args.skip_download:
        manifest, selection_plans = build_manifest(
            collections=args.collections,
            selection_policy=args.selection_policy,
            max_selected_per_collection=args.max_selected_per_collection,
        )
        if selection_plans:
            for label, plan in selection_plans.items():
                summaries.setdefault(label, CollectionSummary(collection=label)).manifest_items = plan.total_candidates
        else:
            for item in manifest:
                summaries.setdefault(item.collection, CollectionSummary(collection=item.collection)).manifest_items += 1
        downloads = sync_downloads(root=root, manifest=manifest, limit=args.limit_downloads)
        for record in downloads:
            summary = summaries.setdefault(record.collection, CollectionSummary(collection=record.collection))
            if record.status in {"existing", "downloaded"}:
                summary.downloaded_files += 1
                summary.downloaded_bytes += record.bytes_downloaded
            if record.status == "unresolved":
                summary.unresolved_downloads += 1
        _write_download_outputs(root, manifest, downloads, selection_plans)

    records: list[ProcessedRecord] = []
    if not args.skip_process:
        records, process_summaries = process_reference_root(root)
        for label, summary in process_summaries.items():
            existing = summaries.setdefault(label, CollectionSummary(collection=label))
            existing.extracted_files = summary.extracted_files
            existing.template_candidates = summary.template_candidates
            existing.example_candidates = summary.example_candidates
            existing.tool_call_candidates = summary.tool_call_candidates
            if existing.downloaded_files == 0:
                existing.downloaded_files = summary.downloaded_files
                existing.downloaded_bytes = summary.downloaded_bytes

    summary_path = _write_summary(root, summaries, records)
    print(f"Ingest summary written to {summary_path}")
    print(f"Processed {len(records)} extracted documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())