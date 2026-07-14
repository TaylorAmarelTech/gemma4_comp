#!/usr/bin/env python3
"""Import immutable public answer/rationale data into a review-only queue.

Supported sources are curator-declared Hugging Face JSONL files, Kaggle dataset
files, and explicitly scoped local JSONL fixtures.  Every remote source must
pin a revision/version plus the exact file SHA-256.  Imported content is never
trainer-ready: clean rows become candidates, rejected rows become metadata-only
quarantine entries, and the manifest always records ``safe_to_train=false``.

Only final answers and explicitly public, author-written visible rationales are
mapped.  Hidden chain-of-thought, scratchpads, analysis-channel content,
credentials, PII findings, mutable revisions, and unlicensed sources fail or
quarantine without copying rejected raw text into reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import urllib.parse
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import canonical_sha256, pii_findings  # noqa: E402

DEFAULT_REGISTRY = ROOT / "configs" / "duecare" / "training" / "source_registry.yaml"
DEFAULT_OUTPUT_ROOT = ROOT / "reports" / "training_candidates"
ALLOWED_LICENSES = frozenset({"CC-BY-4.0", "CC-BY-SA-4.0", "Apache-2.0", "MIT"})
SOURCE_TYPES = frozenset({"huggingface_jsonl", "kaggle_dataset_file", "local_jsonl"})
REASONING_POLICY = "final_answers_and_visible_rationales_only"
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SAFE_DATASET_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SAFE_FILE = re.compile(r"^[A-Za-z0-9_.\-/]+\.jsonl$")
_HEX40_PLUS = re.compile(r"^[0-9a-f]{40,64}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HIDDEN_REASONING = re.compile(
    r"<\|?(?:think|thought)(?:\|>|>)|<\|channel\|>\s*(?:analysis|thought)|"
    r"\b(?:hidden|private)\s+chain[- ]of[- ]thought\b|\bprivate\s+scratchpad\b",
    re.I,
)
_PRIVATE_PATH = re.compile(
    r"(?i)(?:[A-Z]:[/\\]Users[/\\][^/\\\s]+|/home/[^/\s]+/|"
    r"(?:^|[/\\])(?:AppData|OneDrive)(?:[/\\]|$)|file:/{1,3})"
)
_SECRET_LITERAL = re.compile(
    r"(?i)(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"AIza[0-9A-Za-z_-]{35}|-----BEGIN(?: RSA| EC| OPENSSH)? PRIVATE KEY-----)"
)


class ImportBlocked(ValueError):
    """A metadata-only source/import validation failure."""


def _utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _strings(child)


def _load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as exc:
            raise ImportBlocked("YAML registry requires PyYAML") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ImportBlocked("source registry must contain an object")
    return value


def load_source(registry_path: Path, source_id: str) -> dict[str, Any]:
    registry = _load_document(registry_path)
    if registry.get("schema_version") != "1.0":
        raise ImportBlocked("source registry schema_version is not 1.0")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise ImportBlocked("source registry sources must be a list")
    matches = [item for item in sources if isinstance(item, dict) and item.get("id") == source_id]
    if len(matches) != 1:
        raise ImportBlocked("source id is missing or duplicated in the registry")
    return validate_source(matches[0])


def validate_source(raw: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(raw)
    source_id = source.get("id")
    if not isinstance(source_id, str) or not _SAFE_ID.fullmatch(source_id):
        raise ImportBlocked("source id is invalid")
    if source.get("enabled") is not True:
        raise ImportBlocked("source is not curator-enabled")
    source_type = source.get("source_type")
    if source_type not in SOURCE_TYPES:
        raise ImportBlocked("source_type is unsupported")
    dataset_id = source.get("dataset_id")
    if not isinstance(dataset_id, str) or not _SAFE_DATASET_ID.fullmatch(dataset_id):
        raise ImportBlocked("dataset_id must use owner/slug form")
    data_file = source.get("data_file")
    if not isinstance(data_file, str) or not _SAFE_FILE.fullmatch(data_file):
        raise ImportBlocked("data_file must be a safe JSONL path")
    if ".." in Path(data_file).parts or Path(data_file).is_absolute():
        raise ImportBlocked("data_file must not traverse or be absolute")
    expected_sha = source.get("expected_sha256")
    if not isinstance(expected_sha, str) or not _HEX64.fullmatch(expected_sha):
        raise ImportBlocked("expected_sha256 must be an exact SHA-256")
    revision = source.get("revision")
    if source_type == "huggingface_jsonl" and (
        not isinstance(revision, str) or not _HEX40_PLUS.fullmatch(revision)
    ):
        raise ImportBlocked("Hugging Face revision must be an immutable commit hash")
    if source_type == "kaggle_dataset_file" and (
        not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0
    ):
        raise ImportBlocked("Kaggle revision must be a positive dataset version")
    if source_type == "local_jsonl" and not isinstance(revision, str):
        raise ImportBlocked("local source revision is required")
    if source.get("license") not in ALLOWED_LICENSES:
        raise ImportBlocked("source license is missing or unsupported")
    terms_url = source.get("terms_url")
    if not isinstance(terms_url, str) or urllib.parse.urlparse(terms_url).scheme != "https":
        raise ImportBlocked("source terms_url must be HTTPS")
    if not str(source.get("rights_holder") or "").strip():
        raise ImportBlocked("source rights_holder is required")
    if source.get("allow_training_use") is not True:
        raise ImportBlocked("source does not grant training use")
    if source.get("allow_public_redistribution") is not True:
        raise ImportBlocked("source does not grant public redistribution")
    if source.get("reasoning_policy") != REASONING_POLICY:
        raise ImportBlocked("source reasoning policy is not explicit")
    if source.get("rationale_visibility") != "explicitly_public":
        raise ImportBlocked("source rationale visibility is not explicitly public")
    fields = source.get("fields")
    if not isinstance(fields, Mapping):
        raise ImportBlocked("source field mapping is required")
    for key in ("id", "prompt", "answer"):
        if not isinstance(fields.get(key), str) or not fields[key].strip():
            raise ImportBlocked(f"source field mapping is missing {key}")
    mapped_names = {str(value).strip().lower() for value in fields.values() if isinstance(value, str)}
    if any(re.search(r"(?:chain.?of.?thought|private.?analysis|scratchpad|hidden.?thought)", name) for name in mapped_names):
        raise ImportBlocked("source field mapping requests private reasoning")
    max_rows = source.get("max_rows")
    if not isinstance(max_rows, int) or isinstance(max_rows, bool) or not 1 <= max_rows <= 1_000_000:
        raise ImportBlocked("source max_rows is invalid")
    return source


def acquire_source_file(
    source: Mapping[str, Any],
    *,
    target: Path,
    local_source_root: Path | None,
    kaggle_bin: str | None,
    max_download_bytes: int,
) -> None:
    source_type = source["source_type"]
    if source_type == "local_jsonl":
        if local_source_root is None:
            raise ImportBlocked("local source requires --local-source-root")
        root = local_source_root.resolve(strict=True)
        source_path = (root / str(source["data_file"])).resolve(strict=True)
        try:
            source_path.relative_to(root)
        except ValueError as exc:
            raise ImportBlocked("local source escapes --local-source-root") from exc
        if not source_path.is_file() or source_path.stat().st_size > max_download_bytes:
            raise ImportBlocked("local source file is missing or too large")
        shutil.copyfile(source_path, target)
    elif source_type == "huggingface_jsonl":
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as exc:
            raise ImportBlocked("Hugging Face import requires huggingface_hub") from exc
        with tempfile.TemporaryDirectory(prefix="duecare-hf-import-") as temp_dir:
            try:
                downloaded = Path(
                    hf_hub_download(
                        repo_id=str(source["dataset_id"]),
                        filename=str(source["data_file"]),
                        revision=str(source["revision"]),
                        repo_type="dataset",
                        local_dir=temp_dir,
                    )
                )
            except Exception as exc:
                raise ImportBlocked("Hugging Face dataset download failed") from exc
            if not downloaded.is_file() or downloaded.stat().st_size > max_download_bytes:
                raise ImportBlocked("Hugging Face source file is missing or too large")
            shutil.copyfile(downloaded, target)
    else:
        if kaggle_bin:
            raise ImportBlocked(
                "--kaggle-bin cannot guarantee a historical dataset version; "
                "use the version-pinned kagglehub importer"
            )
        try:
            import kagglehub
        except ImportError as exc:
            raise ImportBlocked("Kaggle import requires kagglehub") from exc
        with tempfile.TemporaryDirectory(prefix="duecare-kaggle-import-") as temp_dir:
            handle = f"{source['dataset_id']}/versions/{source['revision']}"
            try:
                downloaded = Path(
                    kagglehub.dataset_download(
                        handle,
                        path=str(source["data_file"]),
                        output_dir=temp_dir,
                        force_download=True,
                    )
                )
            except Exception as exc:
                raise ImportBlocked("Kaggle dataset download failed") from exc
            if downloaded.is_dir():
                exact = [
                    path
                    for path in downloaded.rglob("*")
                    if path.is_file() and path.as_posix().endswith(str(source["data_file"]))
                ]
            else:
                exact = [downloaded] if downloaded.is_file() else []
            if len(exact) != 1 or exact[0].stat().st_size > max_download_bytes:
                raise ImportBlocked("Kaggle download did not produce the pinned file")
            shutil.copyfile(exact[0], target)
    if _sha256_file(target) != source["expected_sha256"]:
        raise ImportBlocked("downloaded source checksum does not match the registry")


def _field(row: Mapping[str, Any], fields: Mapping[str, Any], name: str) -> Any:
    key = fields.get(name)
    return row.get(key) if isinstance(key, str) else None


def _safe_row_id(value: Any, index: int) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 256 or pii_findings({"id": text}) or _PRIVATE_PATH.search(text):
        return f"row-{index:08d}"
    return text


def import_rows(source: Mapping[str, Any], raw_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fields = source["fields"]
    candidates: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with raw_path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if index > int(source["max_rows"]):
                raise ImportBlocked("source contains more rows than the registry permits")
            reasons: list[str] = []
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                raw = None
                reasons.append("invalid_json")
            if not isinstance(raw, dict):
                reasons.append("row_not_object")
                raw = {}
            source_row_id = _safe_row_id(_field(raw, fields, "id"), index)
            public_id = f"{source['id']}:{source_row_id}"
            if public_id in seen_ids:
                reasons.append("duplicate_row_id")
            seen_ids.add(public_id)
            prompt = _field(raw, fields, "prompt")
            answer = _field(raw, fields, "answer")
            rationale = _field(raw, fields, "visible_rationale")
            if not isinstance(prompt, str) or not prompt.strip():
                reasons.append("prompt_missing")
                prompt = ""
            if not isinstance(answer, str) or not answer.strip():
                reasons.append("answer_missing")
                answer = ""
            if rationale is not None and not isinstance(rationale, str):
                reasons.append("visible_rationale_not_string")
                rationale = ""
            mapped = {"prompt": prompt, "final_answer": answer, "visible_rationale": rationale or ""}
            findings = pii_findings(mapped)
            reasons.extend(f"pii_{finding}" for finding in findings)
            if any(_HIDDEN_REASONING.search(text) for text in _strings(mapped)):
                reasons.append("hidden_reasoning")
            if any(_PRIVATE_PATH.search(text) or _SECRET_LITERAL.search(text) for text in _strings(mapped)):
                reasons.append("private_path_or_secret")
            source_refs = _field(raw, fields, "source_refs")
            if isinstance(source_refs, str):
                source_refs = [source_refs]
            if not isinstance(source_refs, list):
                source_refs = []
            source_refs = [str(value).strip() for value in source_refs if str(value).strip()]
            if pii_findings(source_refs) or any(
                _PRIVATE_PATH.search(text) or _SECRET_LITERAL.search(text) for text in source_refs
            ):
                reasons.append("source_refs_private")
            lineage = _field(raw, fields, "lineage_id")
            lineage_text = str(lineage or "").strip()
            if (
                not lineage_text
                or len(lineage_text) > 256
                or pii_findings({"lineage": lineage_text})
                or _PRIVATE_PATH.search(lineage_text)
            ):
                lineage_text = canonical_sha256(source_row_id)[:24]
            lineage_id = f"{source['id']}:{lineage_text}"
            raw_row_sha = canonical_sha256(raw)
            if reasons:
                quarantine.append(
                    {
                        "source_id": source["id"],
                        "source_row_id_hash": canonical_sha256(source_row_id),
                        "source_row_sha256": raw_row_sha,
                        "index": index,
                        "reason_codes": sorted(set(reasons)),
                        "contains_raw_text": False,
                    }
                )
                continue
            candidate = {
                "id": public_id,
                "prompt": prompt.strip(),
                "final_answer": answer.strip(),
                "visible_rationale": str(rationale or "").strip(),
                "source_refs": source_refs,
                "lineage_id": lineage_id,
                "license": source["license"],
                "rights_holder": source["rights_holder"],
                "allow_training_use": True,
                "allow_public_redistribution": True,
                "source_provenance": {
                    "source_id": source["id"],
                    "dataset_id": source["dataset_id"],
                    "revision": source["revision"],
                    "data_file": source["data_file"],
                    "source_row_id": source_row_id,
                    "source_row_sha256": raw_row_sha,
                    "terms_url": source["terms_url"],
                },
                "candidate_status": "pending_curator_privacy_license_and_quality_review",
                "safe_to_train": False,
            }
            candidate["sha256"] = canonical_sha256(candidate)
            candidates.append(candidate)
    return candidates, quarantine


def _prepare_output(path: Path) -> Path:
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ImportBlocked("output directory must be absent or empty")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()
    return path.resolve()


def run_import(
    source: Mapping[str, Any],
    *,
    output_dir: Path,
    local_source_root: Path | None = None,
    kaggle_bin: str | None = None,
    max_download_bytes: int = 256 * 1024 * 1024,
) -> dict[str, Any]:
    source = validate_source(source)
    target = _prepare_output(output_dir)
    with tempfile.NamedTemporaryFile(prefix="duecare-source-", suffix=".jsonl", delete=False) as handle:
        raw_path = Path(handle.name)
    try:
        acquire_source_file(
            source,
            target=raw_path,
            local_source_root=local_source_root,
            kaggle_bin=kaggle_bin,
            max_download_bytes=max_download_bytes,
        )
        candidates, quarantine = import_rows(source, raw_path)
    finally:
        raw_path.unlink(missing_ok=True)

    candidate_path = target / "candidates.jsonl"
    quarantine_path = target / "quarantine.json"
    with candidate_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in candidates:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    quarantine_doc = {
        "schema_version": "1.0",
        "source_id": source["id"],
        "contains_raw_text": False,
        "rows": quarantine,
    }
    quarantine_path.write_text(json.dumps(quarantine_doc, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": "duecare.training.candidate_import.v1",
        "created_at": _utc(),
        "source": {
            key: source[key]
            for key in (
                "id",
                "source_type",
                "dataset_id",
                "revision",
                "data_file",
                "expected_sha256",
                "license",
                "terms_url",
                "rights_holder",
                "allow_training_use",
                "allow_public_redistribution",
                "reasoning_policy",
                "rationale_visibility",
            )
        },
        "counts": {"candidate": len(candidates), "quarantined": len(quarantine)},
        "artifacts": {
            "candidates.jsonl": {"sha256": _sha256_file(candidate_path), "bytes": candidate_path.stat().st_size},
            "quarantine.json": {"sha256": _sha256_file(quarantine_path), "bytes": quarantine_path.stat().st_size},
        },
        "raw_source_retained": False,
        "safe_to_train": False,
        "promotion_blockers": [
            "curator_approval_required",
            "privacy_review_required",
            "license_compatibility_review_required",
            "quality_and_citation_grading_required",
            "lineage_split_and_heldout_exclusion_required",
            "canonical_training_contract_required",
        ],
    }
    manifest_path = target / "candidate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--local-source-root", type=Path)
    parser.add_argument("--kaggle-bin")
    parser.add_argument("--max-download-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = load_source(args.registry, args.source_id)
        revision_slug = canonical_sha256(str(source["revision"]))[:12]
        output = args.output_dir or DEFAULT_OUTPUT_ROOT / f"{source['id']}-{revision_slug}"
        if args.dry_run:
            report = {
                "ok": True,
                "dry_run": True,
                "source_id": source["id"],
                "source_type": source["source_type"],
                "dataset_id": source["dataset_id"],
                "revision": source["revision"],
                "data_file": source["data_file"],
                "output_dir": output.as_posix(),
                "safe_to_train": False,
            }
        else:
            report = run_import(
                source,
                output_dir=output,
                local_source_root=args.local_source_root,
                kaggle_bin=args.kaggle_bin,
                max_download_bytes=max(1, args.max_download_bytes),
            )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ImportBlocked) as exc:
        print(f"[training-candidate-import] BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
