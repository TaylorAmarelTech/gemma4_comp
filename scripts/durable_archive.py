#!/usr/bin/env python3
"""Durable, partitioned, GitHub-committable archive of the benchmark's irreplaceable local-only data.

The graded panel + verbatim results (days of Ollama-cloud grading), the 78,719-prompt registry, and the
distilled SFT/DPO training sets are all gitignored -- a single local disk / OneDrive-sync failure would
lose them, and they cannot be cheaply regenerated. This tool gzips each source, splits it into chunks
that fit comfortably under GitHub's per-file limit, and writes them under ``archive/`` next to a
checksummed manifest. Committing ``archive/`` then gives an off-machine, version-controlled copy that
survives a local OR website failure -- ``--restore`` reassembles and sha256-verifies everything back.

Design guarantees:
  * DETERMINISTIC: gzip is written with a fixed header (mtime=0), so re-archiving unchanged data produces
    byte-identical chunks -- no spurious git churn.
  * IDEMPOTENT: a source whose sha256 already matches the manifest is skipped; changed sources are
    re-chunked and stale chunks are removed.
  * SAFE: an explicit PII/binary exclusion guard refuses to archive raw-case caches, reference corpora,
    or model weights even if a caller passes them.
  * VERIFIABLE: every chunk set reassembles to the manifest's sha256 of the ORIGINAL bytes.
  * SQLITE-CONSISTENT: live component checkpoints are archived through SQLite's backup API, so WAL
    state is captured in one integrity-checked database image instead of copying a changing file.

    python scripts/durable_archive.py            # archive changed sources -> archive/
    python scripts/durable_archive.py --verify   # check every archived file reassembles to its sha256
    python scripts/durable_archive.py --restore  # rebuild missing originals from archive/ (verified)
    python scripts/durable_archive.py --restore --force   # also overwrite existing originals

The guarded PowerShell workflow is read-only by default. ``-Refresh`` updates the local archive and
``-Publish`` creates an isolated orphan snapshot and pushes only ``origin/data-archive`` with an exact
``--force-with-lease``; neither mode stages the working tree's normal Git index::

    pwsh scripts/refresh_durable_archive.ps1
    pwsh scripts/refresh_durable_archive.ps1 -Refresh
    pwsh scripts/refresh_durable_archive.ps1 -Publish
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = _ROOT / "archive"
MANIFEST = ARCHIVE_DIR / "manifest.json"
CHUNK_BYTES = 40 * 1024 * 1024   # 40 MiB: safely under GitHub's 50 MB warn / 100 MB hard per-file limit

# Sources to preserve (repo-relative globs). Curated to the valuable, hard-to-regenerate, NON-PII data:
# the panel GRADES (days of judging), the prompt registry, the distilled training materials, the registry.
SOURCE_GLOBS = [
    "reports/rich_lift/panel.jsonl",
    "reports/rich_lift/panel_holistic_v1.jsonl",
    "reports/rich_lift/panel_perdim.jsonl",
    "reports/rich_lift/panel_perdim.coverage.json",
    "reports/rich_lift/panel_perdim.jsonl.components.sqlite3",
    "reports/multi_judge/panel.jsonl",
    "reports/multi_judge/perdim_panel.jsonl",
    "reports/benchmark/full_promptset.json",
    "reports/autonomous_engine_state.json",
    "reports/training/*.jsonl",
    "reports/training/*.json",
]
# Large, volatile artifacts (the verbatim model responses grow by ~hundreds of MB and change every day):
# included only with --include-large, so the daily-committed archive does not bloat git history. The
# grades in panel.jsonl reference these by (model, prompt_id, arm) and regeneration is possible if lost.
OPTIONAL_LARGE_GLOBS = [
    "reports/rich_lift/results.jsonl",
]

# Defence-in-depth: never archive raw-case PII caches, the separate reference corpus, or model weights,
# even if a future SOURCE_GLOBS edit reaches them. (Safety rule 10: no raw PII in git.)
_FORBIDDEN = re.compile(
    r"(?:^|[\\/])(?:_reference|drive_[a-z_]*cache|drive_[a-z_]*\.json|curation_cache|"
    r"multimodal_test_set|adapters?)(?:[\\/]|$)|\.(?:safetensors|gguf|bin|pt|onnx|parquet|arrow)$",
    re.IGNORECASE,
)

# JSON/JSONL sources are expected to contain curated benchmark or training data, not direct
# contact or identity records. Match field names structurally rather than echoing values into logs.
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE)
_SENSITIVE_FIELDS = {
    "address": "address_field",
    "contact_details": "contact_field",
    "contacts": "contact_field",
    "date_of_birth": "identity_field",
    "dob": "identity_field",
    "email": "contact_field",
    "email_address": "contact_field",
    "emergency_contact": "contact_field",
    "full_name": "name_field",
    "given_name": "name_field",
    "government_id": "identity_field",
    "home_address": "address_field",
    "id_number": "identity_field",
    "last_name": "name_field",
    "mobile": "contact_field",
    "mobile_number": "contact_field",
    "national_id": "identity_field",
    "national_id_number": "identity_field",
    "passport_no": "identity_field",
    "passport_number": "identity_field",
    "personal_email": "contact_field",
    "person_name": "name_field",
    "phone": "contact_field",
    "phone_number": "contact_field",
    "postal_address": "address_field",
    "residential_address": "address_field",
    "social_security_number": "identity_field",
    "street_address": "address_field",
    "surname": "name_field",
    "telephone": "contact_field",
    "unredacted_text": "raw_case_field",
    "visa_number": "identity_field",
    "whatsapp": "contact_field",
    "worker_name": "name_field",
    "work_permit_number": "identity_field",
}
_SENSITIVE_SUFFIXES = {
    "_email": "contact_field",
    "_full_name": "name_field",
    "_phone": "contact_field",
}
class UnsafeArchiveContentError(ValueError):
    """Raised when structured source data cannot pass the content-safety gate."""


class ArchiveManifestError(RuntimeError):
    """Raised when an existing manifest cannot be trusted for a non-destructive operation."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve(strict=False).relative_to(_ROOT.resolve(strict=False)).as_posix()
    except (OSError, RuntimeError, ValueError):
        raise ArchiveManifestError("path resolves outside the approved repository root") from None


def _normalise_manifest_rel(value: object, *, label: str) -> str:
    """Return one canonical POSIX relative path, rejecting traversal and Windows escapes."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ArchiveManifestError(f"archive manifest contains an invalid {label} path")
    if "\\" in value or ":" in value or any(ord(char) < 32 for char in value):
        raise ArchiveManifestError(f"archive manifest contains an invalid {label} path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(any(marker in part for marker in "*?[]") for part in path.parts)
    ):
        raise ArchiveManifestError(f"archive manifest contains an unsafe {label} path")
    return value


def _resolved_within(path: Path, root: Path, *, label: str) -> Path:
    """Validate the current filesystem resolution while preserving the intended logical path."""
    try:
        root_resolved = root.resolve(strict=False)
        resolved = path.resolve(strict=False)
        resolved.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError):
        raise ArchiveManifestError(f"{label} resolves outside its approved root") from None
    return path


def _archive_root() -> Path:
    """The archive directory itself may not be redirected outside the repository by a symlink."""
    _resolved_within(ARCHIVE_DIR, _ROOT, label="archive directory")
    return ARCHIVE_DIR


def _manifest_path() -> Path:
    return _resolved_within(MANIFEST, _archive_root(), label="archive manifest")


def _matches_allowed_source(rel: str) -> bool:
    path = PurePosixPath(rel)
    return any(
        path.match(pattern)
        for pattern in (*SOURCE_GLOBS, *OPTIONAL_LARGE_GLOBS)
    )


def _source_path(value: object) -> Path:
    rel = _normalise_manifest_rel(value, label="source")
    if _is_forbidden(rel) or not _matches_allowed_source(rel):
        raise ArchiveManifestError("archive manifest source is outside the approved allowlist")
    logical = _ROOT.joinpath(*PurePosixPath(rel).parts)
    return _resolved_within(logical, _ROOT, label="archive source destination")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_forbidden(rel: str) -> bool:
    return bool(_FORBIDDEN.search(rel))


def _normalise_field_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _has_content(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _sensitive_field_category(key: object, value: object) -> str | None:
    """Classify populated direct-identifier fields without retaining or displaying their values."""
    raw_key = str(key)
    if _EMAIL.fullmatch(raw_key.strip()):
        return "identifier_as_key"
    name = _normalise_field_name(raw_key)
    category = _SENSITIVE_FIELDS.get(name)
    if category is None:
        for suffix, suffix_category in _SENSITIVE_SUFFIXES.items():
            if name.endswith(suffix):
                category = suffix_category
                break
    if category is None or not _has_content(value):
        return None
    # Boolean and small numeric contact fields are commonly aggregate quality metrics (for example
    # ok_phone=True or fragile.phone=0), whereas direct contact records are strings or objects.
    if category == "contact_field" and isinstance(value, bool):
        return None
    if category == "contact_field" and isinstance(value, (int, float)) and abs(value) < 1_000_000:
        return None
    return category


def _content_safety_findings(src: Path, raw: bytes) -> dict[str, int]:
    """Parse JSON/JSONL and return category counts only; never retain matched scalar values."""
    if src.suffix.lower() not in {".json", ".jsonl"}:
        return {}

    findings: dict[str, int] = {}

    def record(category: str) -> None:
        findings[category] = findings.get(category, 0) + 1

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                category = _sensitive_field_category(key, item)
                if category:
                    record(category)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    try:
        if src.suffix.lower() == ".jsonl":
            for line in io.BytesIO(raw):
                if line.strip():
                    walk(json.loads(line.decode("utf-8")))
        else:
            walk(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"invalid_json": 1}
    return findings


def _assert_content_safe(src: Path, raw: bytes) -> None:
    findings = _content_safety_findings(src, raw)
    if not findings:
        return
    summary = ", ".join(f"{category}={count}" for category, count in sorted(findings.items()))
    raise UnsafeArchiveContentError(
        "content safety check rejected a JSON/JSONL source "
        f"({summary}); matched values are intentionally omitted"
    )


def iter_sources(*, include_large: bool = False) -> list[Path]:
    """Existing, non-forbidden source files, de-duplicated and stably ordered."""
    seen: dict[str, Path] = {}
    globs = list(SOURCE_GLOBS) + (list(OPTIONAL_LARGE_GLOBS) if include_large else [])
    for pattern in globs:
        for p in sorted(_ROOT.glob(pattern)):
            if not p.is_file():
                continue
            rel = _rel(p)
            if _is_forbidden(rel):
                continue
            seen.setdefault(rel, p)
    return [seen[k] for k in sorted(seen)]


def _gzip_deterministic(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(data)
    return buf.getvalue()


def _sqlite_snapshot_bytes(src: Path) -> bytes:
    """Return one transactionally consistent SQLite image, including committed WAL state."""
    source_path = _source_path(_rel(src))
    try:
        with tempfile.TemporaryDirectory(prefix="duecare-archive-sqlite-") as temp_dir:
            snapshot_path = Path(temp_dir) / "snapshot.sqlite3"
            source_uri = source_path.resolve(strict=True).as_uri() + "?mode=ro"
            source_db = sqlite3.connect(source_uri, uri=True, timeout=30.0)
            try:
                source_db.execute("PRAGMA query_only=ON")
                source_db.execute("PRAGMA busy_timeout=30000")
                snapshot_db = sqlite3.connect(snapshot_path, timeout=30.0)
                try:
                    source_db.backup(snapshot_db)
                    snapshot_db.commit()
                    integrity = [row[0] for row in snapshot_db.execute("PRAGMA integrity_check")]
                    if integrity != ["ok"]:
                        raise sqlite3.DatabaseError("snapshot integrity check failed")
                finally:
                    snapshot_db.close()
            finally:
                source_db.close()
            return snapshot_path.read_bytes()
    except (OSError, RuntimeError, sqlite3.Error):
        raise ArchiveManifestError(
            "could not create a consistent SQLite snapshot for an approved source"
        ) from None


def _read_source_bytes(src: Path) -> bytes:
    if src.suffix.lower() == ".sqlite3":
        return _sqlite_snapshot_bytes(src)
    return src.read_bytes()


def _chunk_names(rel: str, n: int, sha256: str | None = None) -> list[str]:
    """Content-address changed archives so an interrupted update cannot corrupt the prior entry."""
    version = f".{sha256[:16]}" if sha256 else ""
    return [f"{rel}{version}.gz.{i:03d}" for i in range(n)]


def _chunk_path(source_rel: object, chunk_rel: object) -> Path:
    source = _normalise_manifest_rel(source_rel, label="source")
    chunk = _normalise_manifest_rel(chunk_rel, label="chunk")
    if not re.fullmatch(
        rf"{re.escape(source)}(?:\.[0-9a-f]{{16}})?\.gz\.[0-9]{{3,}}",
        chunk,
    ):
        raise ArchiveManifestError("archive manifest chunk does not belong to its source")
    logical = _archive_root().joinpath(*PurePosixPath(chunk).parts)
    return _resolved_within(logical, _archive_root(), label="archive chunk")


def _nonnegative_manifest_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArchiveManifestError(f"archive manifest contains an invalid {label}")
    return value


def _validate_manifest(manifest: object) -> dict:
    """Validate every path and integrity field before archive data can be read or restored."""
    _manifest_path()
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise ArchiveManifestError(
            "existing archive manifest has an invalid structure; refusing to continue"
        )
    files = manifest["files"]
    if "chunk_bytes" in manifest:
        chunk_bytes = _nonnegative_manifest_int(manifest["chunk_bytes"], label="chunk size")
        if chunk_bytes == 0:
            raise ArchiveManifestError("archive manifest contains an invalid chunk size")
    if "n_files" in manifest and (
        isinstance(manifest["n_files"], bool)
        or not isinstance(manifest["n_files"], int)
        or manifest["n_files"] != len(files)
    ):
        raise ArchiveManifestError("archive manifest file count does not match its entries")

    sources: set[str] = set()
    all_chunks: set[str] = set()
    total_source = 0
    total_compressed = 0
    for entry in files:
        if not isinstance(entry, dict):
            raise ArchiveManifestError("archive manifest contains an invalid file entry")
        source = _normalise_manifest_rel(entry.get("path"), label="source")
        _source_path(source)
        if source in sources:
            raise ArchiveManifestError("archive manifest contains duplicate source paths")
        sources.add(source)

        sha256 = entry.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ArchiveManifestError("archive manifest contains an invalid source checksum")
        source_bytes = _nonnegative_manifest_int(entry.get("bytes"), label="source byte count")
        compressed_bytes = _nonnegative_manifest_int(
            entry.get("compressed_bytes"), label="compressed byte count"
        )
        total_source += source_bytes
        total_compressed += compressed_bytes

        chunks = entry.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            raise ArchiveManifestError("archive manifest entry must contain archive chunks")
        normalised_chunks = [
            _normalise_manifest_rel(chunk, label="chunk") for chunk in chunks
        ]
        expected_legacy = _chunk_names(source, len(normalised_chunks))
        expected_versioned = _chunk_names(source, len(normalised_chunks), sha256)
        if normalised_chunks not in (expected_legacy, expected_versioned):
            raise ArchiveManifestError("archive manifest contains an invalid chunk sequence")
        for chunk in normalised_chunks:
            if chunk in all_chunks:
                raise ArchiveManifestError("archive manifest contains duplicate archive chunks")
            all_chunks.add(chunk)
            _chunk_path(source, chunk)

    for field, expected in (
        ("total_source_bytes", total_source),
        ("total_compressed_bytes", total_compressed),
    ):
        if field in manifest and (
            isinstance(manifest[field], bool)
            or not isinstance(manifest[field], int)
            or manifest[field] != expected
        ):
            raise ArchiveManifestError(f"archive manifest {field} does not match its entries")
    return manifest


def _load_manifest() -> dict:
    manifest_path = _manifest_path()
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise ArchiveManifestError(
                "existing archive manifest is unreadable; refusing to continue"
            ) from None
        return _validate_manifest(manifest)
    return {"chunk_bytes": CHUNK_BYTES, "files": []}


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _write_text_atomic(path: Path, text: str) -> None:
    _write_bytes_atomic(path, text.encode("utf-8"))


def _referenced_chunks(entries: list[dict] | tuple[dict, ...]) -> set[str]:
    return {str(chunk) for entry in entries for chunk in entry.get("chunks", [])}


def _prune_unreferenced_chunks(manifest: dict, candidates: set[str]) -> None:
    """Remove prior chunks made obsolete by the manifest; leave unrelated files alone."""
    referenced = _referenced_chunks(manifest.get("files", []))
    archive_root = _archive_root().resolve(strict=False)
    for rel in candidates - referenced:
        path = (_archive_root() / rel).resolve(strict=False)
        try:
            path.relative_to(archive_root)
        except ValueError:
            continue
        path.unlink(missing_ok=True)


def archive(*, quiet: bool = False, include_large: bool = False) -> dict:
    """Archive changed sources; return the manifest. Deterministic + idempotent."""
    _archive_root().mkdir(parents=True, exist_ok=True)
    previous_entries = list(_load_manifest().get("files", []))
    prev = {e["path"]: e for e in previous_entries}
    entries_by_path = dict(prev)
    previous_chunks = _referenced_chunks(previous_entries)
    transaction_chunks: set[Path] = set()
    manifest_committed = False
    try:
        for src in iter_sources(include_large=include_large):
            rel = _rel(src)
            _source_path(rel)
            raw = _read_source_bytes(src)
            _assert_content_safe(src, raw)
            sha = _sha256_bytes(raw)
            old = prev.get(rel)
            if old and old.get("sha256") == sha and _chunks_present(old):
                # Unchanged: retain the prior entry and chunks without churn.
                continue

            comp = _gzip_deterministic(raw)
            chunks = _chunk_names(
                rel,
                max(1, (len(comp) + CHUNK_BYTES - 1) // CHUNK_BYTES),
                sha,
            )
            for i, name in enumerate(chunks):
                out = _chunk_path(rel, name)
                _write_bytes_atomic(out, comp[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES])
                if name not in previous_chunks:
                    transaction_chunks.add(out)
            entries_by_path[rel] = {
                "path": rel,
                "sha256": sha,
                "bytes": len(raw),
                "compressed_bytes": len(comp),
                "chunks": chunks,
                "mtime": int(src.stat().st_mtime),
                "archived_at": _now(),
            }
            if not quiet:
                print(
                    f"  archived {rel}  "
                    f"({len(raw):,} -> {len(comp):,} bytes, {len(chunks)} chunk(s))"
                )

        # Entries not selected in this invocation remain restorable. This covers temporarily missing
        # sources and optional large sources when a later routine archive omits --include-large.
        entries = [entries_by_path[path] for path in sorted(entries_by_path)]
        total_c = sum(int(entry.get("compressed_bytes", 0)) for entry in entries)
        manifest = {
            "generated": _now(),
            "chunk_bytes": CHUNK_BYTES,
            "n_files": len(entries),
            "total_source_bytes": sum(int(entry.get("bytes", 0)) for entry in entries),
            "total_compressed_bytes": total_c,
            "files": entries,
        }
        _validate_manifest(manifest)
        _write_text_atomic(_manifest_path(), json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        manifest_committed = True
    except Exception:
        if not manifest_committed:
            for path in transaction_chunks:
                path.unlink(missing_ok=True)
        raise

    try:
        _write_readme(manifest)
    finally:
        _prune_unreferenced_chunks(manifest, previous_chunks)
    if not quiet:
        print(
            f"archive: {len(entries)} files, {total_c:,} compressed bytes "
            f"-> {_rel(ARCHIVE_DIR)}/"
        )
    return manifest


def _chunks_present(entry: dict) -> bool:
    return all(_chunk_path(entry.get("path"), chunk).is_file() for chunk in entry.get("chunks", []))


def _reassemble(entry: dict) -> bytes:
    """Concatenate an entry's chunks and gunzip; raise if a chunk is missing."""
    comp = b""
    for c in entry.get("chunks", []):
        p = _chunk_path(entry.get("path"), c)
        if not p.is_file():
            raise FileNotFoundError("missing archive chunk for approved source")
        comp += p.read_bytes()
    return gzip.decompress(comp)


def verify(manifest: dict | None = None) -> tuple[int, int]:
    """Reassemble every file and check it matches the manifest sha256. Returns (ok, total)."""
    manifest = _load_manifest() if manifest is None else _validate_manifest(manifest)
    ok = 0
    files = manifest.get("files", [])
    for e in files:
        try:
            data = _reassemble(e)
            good = _sha256_bytes(data) == e.get("sha256") and len(data) == e.get("bytes")
        # A corrupt/truncated chunk must report failure rather than abort verification.
        except Exception as exc:
            print(
                f"  FAIL {e['path']}: archive chunks are missing or corrupt "
                f"({type(exc).__name__})"
            )
            continue
        if good:
            ok += 1
            print(f"  ok   {e['path']}  ({len(data):,} bytes)")
        else:
            print(f"  FAIL {e['path']}: checksum/size mismatch")
    print(f"verify: {ok}/{len(files)} files reassemble to their recorded sha256")
    return ok, len(files)


def restore(*, force: bool = False) -> tuple[int, int]:
    """Rebuild original files from the archive (verified).

    Missing targets are restored. Existing targets are skipped unless forced. Returns
    ``(complete, total)``; a conflicting target or invalid archive is incomplete.
    """
    manifest = _load_manifest()
    files = manifest.get("files", [])
    restored = 0
    complete = 0
    for e in files:
        target = _source_path(e.get("path"))
        try:
            data = _reassemble(e)
        # Every corrupt/missing chunk must become a failed restore rather than aborting the run.
        except Exception as exc:
            print(
                f"  FAIL {e['path']}: archive chunks are missing or corrupt "
                f"({type(exc).__name__})"
            )
            continue
        if _sha256_bytes(data) != e.get("sha256") or len(data) != e.get("bytes"):
            print(f"  FAIL {e['path']}: archive checksum mismatch, refusing to write")
            continue
        if target.exists() and not force:
            try:
                target_data = target.read_bytes()
                same = (
                    _sha256_bytes(target_data) == e.get("sha256")
                    and len(target_data) == e.get("bytes")
                )
            except OSError:
                same = False
            reason = "identical" if same else "exists, use --force to overwrite"
            print(f"  skip {e['path']} ({reason})")
            complete += int(same)
            continue
        try:
            _write_bytes_atomic(target, data)
        except OSError as exc:
            print(f"  FAIL {e['path']}: could not write restored file ({type(exc).__name__})")
            continue
        restored += 1
        complete += 1
        print(f"  restored {e['path']}  ({len(data):,} bytes)")
    print(f"restore: {restored} file(s) written, {complete}/{len(files)} complete")
    return complete, len(files)


def _write_readme(manifest: dict) -> None:
    _validate_manifest(manifest)
    lines = [
        "# Durable archive",
        "",
        "Partitioned, gzipped, sha256-verified copies of the benchmark's irreplaceable but gitignored data ",
        "(the graded panel + results, the full prompt registry, the distilled training sets), so a local or ",
        "website failure never loses them. Generated by `scripts/durable_archive.py` -- do not edit by hand.",
        "Live per-dimension SQLite checkpoints use SQLite's backup API and an integrity check, so committed ",
        "WAL state is preserved as one consistent database image.",
        "",
        f"- generated: `{manifest.get('generated')}`",
        f"- files: **{manifest.get('n_files', 0)}**  ·  source bytes: "
        f"**{manifest.get('total_source_bytes', 0):,}**  ·  compressed: **{manifest.get('total_compressed_bytes', 0):,}**",
        f"- chunk size: {manifest.get('chunk_bytes', CHUNK_BYTES):,} bytes",
        "",
        "Restore everything with `python scripts/durable_archive.py --restore` (verifies each file's sha256 ",
        "before writing; existing files are kept unless `--force`).",
        "",
        "Guarded refresh/publication workflow:",
        "",
        "- `pwsh scripts/refresh_durable_archive.ps1` is a read-only verification and plan.",
        "- `pwsh scripts/refresh_durable_archive.ps1 -Refresh` refreshes and verifies the local archive.",
        "- `pwsh scripts/refresh_durable_archive.ps1 -Publish` refreshes, verifies, creates an isolated orphan ",
        "  commit, and updates only `origin/data-archive` with an exact `--force-with-lease`. It does not stage ",
        "  or replace the working tree's normal Git index.",
        "",
        "| file | bytes | compressed | chunks |",
        "|---|---:|---:|---:|",
    ]
    for e in manifest.get("files", []):
        lines.append(f"| `{e['path']}` | {e['bytes']:,} | {e['compressed_bytes']:,} | {len(e['chunks'])} |")
    readme = _resolved_within(_archive_root() / "README.md", _archive_root(), label="archive README")
    _write_text_atomic(readme, "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Durable, partitioned, GitHub-committable data archive.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--verify", action="store_true", help="check every archived file reassembles to its sha256")
    g.add_argument("--restore", action="store_true", help="rebuild original files from the archive")
    ap.add_argument("--force", action="store_true", help="with --restore, overwrite existing files")
    ap.add_argument("--include-large", action="store_true",
                    help="also archive the large, daily-changing verbatim results.jsonl (bloats git history)")
    args = ap.parse_args(argv)
    if args.verify:
        try:
            ok, total = verify()
        except ArchiveManifestError as exc:
            print(f"verify: FAIL: {exc}")
            return 1
        return 0 if ok == total else 1
    if args.restore:
        try:
            complete, total = restore(force=args.force)
        except ArchiveManifestError as exc:
            print(f"restore: FAIL: {exc}")
            return 1
        return 0 if complete == total else 1
    try:
        archive(include_large=args.include_large)
    except (ArchiveManifestError, UnsafeArchiveContentError) as exc:
        print(f"archive: FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
