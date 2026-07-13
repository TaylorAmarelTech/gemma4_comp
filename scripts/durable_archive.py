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

    python scripts/durable_archive.py            # archive changed sources -> archive/
    python scripts/durable_archive.py --verify   # check every archived file reassembles to its sha256
    python scripts/durable_archive.py --restore  # rebuild missing originals from archive/ (verified)
    python scripts/durable_archive.py --restore --force   # also overwrite existing originals
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = _ROOT / "archive"
MANIFEST = ARCHIVE_DIR / "manifest.json"
CHUNK_BYTES = 40 * 1024 * 1024   # 40 MiB: safely under GitHub's 50 MB warn / 100 MB hard per-file limit

# Sources to preserve (repo-relative globs). Curated to the valuable, hard-to-regenerate, NON-PII data:
# the panel GRADES (days of judging), the prompt registry, the distilled training materials, the registry.
SOURCE_GLOBS = [
    "reports/rich_lift/panel.jsonl",
    "reports/rich_lift/panel_holistic_v1.jsonl",
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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return p.resolve().relative_to(_ROOT).as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_forbidden(rel: str) -> bool:
    return bool(_FORBIDDEN.search(rel))


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


def _chunk_names(rel: str, n: int) -> list[str]:
    return [f"{rel}.gz.{i:03d}" for i in range(n)]


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"chunk_bytes": CHUNK_BYTES, "files": []}


def archive(*, quiet: bool = False, include_large: bool = False) -> dict:
    """Archive changed sources; return the manifest. Deterministic + idempotent."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    prev = {e["path"]: e for e in _load_manifest().get("files", [])}
    entries: list[dict] = []
    total_c = 0
    for src in iter_sources(include_large=include_large):
        rel = _rel(src)
        raw = src.read_bytes()
        sha = _sha256_bytes(raw)
        old = prev.get(rel)
        if old and old.get("sha256") == sha and _chunks_present(old):
            entries.append(old)                      # unchanged -> keep as-is (no re-write, no churn)
            total_c += int(old.get("compressed_bytes", 0))
            continue
        if old:                                      # changed -> drop the previous chunks first
            _remove_chunks(old)
        comp = _gzip_deterministic(raw)
        chunks = _chunk_names(rel, max(1, (len(comp) + CHUNK_BYTES - 1) // CHUNK_BYTES))
        for i, name in enumerate(chunks):
            out = ARCHIVE_DIR / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(comp[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES])
        entries.append({"path": rel, "sha256": sha, "bytes": len(raw), "compressed_bytes": len(comp),
                        "chunks": chunks, "mtime": int(src.stat().st_mtime), "archived_at": _now()})
        total_c += len(comp)
        if not quiet:
            print(f"  archived {rel}  ({len(raw):,} -> {len(comp):,} bytes, {len(chunks)} chunk(s))")
    manifest = {"generated": _now(), "chunk_bytes": CHUNK_BYTES, "n_files": len(entries),
                "total_source_bytes": sum(e["bytes"] for e in entries),
                "total_compressed_bytes": total_c, "files": entries}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_readme(manifest)
    if not quiet:
        print(f"archive: {len(entries)} files, {total_c:,} compressed bytes -> {_rel(ARCHIVE_DIR)}/")
    return manifest


def _chunks_present(entry: dict) -> bool:
    return all((ARCHIVE_DIR / c).exists() for c in entry.get("chunks", []))


def _remove_chunks(entry: dict) -> None:
    for c in entry.get("chunks", []):
        (ARCHIVE_DIR / c).unlink(missing_ok=True)


def _reassemble(entry: dict) -> bytes:
    """Concatenate an entry's chunks and gunzip; raise if a chunk is missing."""
    comp = b""
    for c in entry.get("chunks", []):
        p = ARCHIVE_DIR / c
        if not p.exists():
            raise FileNotFoundError(f"missing chunk {c} for {entry['path']}")
        comp += p.read_bytes()
    return gzip.decompress(comp)


def verify(manifest: dict | None = None) -> tuple[int, int]:
    """Reassemble every file and check it matches the manifest sha256. Returns (ok, total)."""
    manifest = manifest or _load_manifest()
    ok = 0
    files = manifest.get("files", [])
    for e in files:
        try:
            data = _reassemble(e)
            good = _sha256_bytes(data) == e.get("sha256") and len(data) == e.get("bytes")
        except Exception as exc:  # noqa: BLE001  (a corrupt/truncated chunk must report FAIL, not crash)
            print(f"  FAIL {e['path']}: {type(exc).__name__}: {exc}")
            continue
        if good:
            ok += 1
            print(f"  ok   {e['path']}  ({len(data):,} bytes)")
        else:
            print(f"  FAIL {e['path']}: checksum/size mismatch")
    print(f"verify: {ok}/{len(files)} files reassemble to their recorded sha256")
    return ok, len(files)


def restore(*, force: bool = False) -> tuple[int, int]:
    """Rebuild original files from the archive (verified). Missing targets always restored; existing
    targets skipped unless force (never clobber newer local data by default)."""
    manifest = _load_manifest()
    files = manifest.get("files", [])
    restored = 0
    for e in files:
        target = _ROOT / e["path"]
        data = _reassemble(e)
        if _sha256_bytes(data) != e.get("sha256"):
            print(f"  FAIL {e['path']}: archive checksum mismatch, refusing to write")
            continue
        if target.exists() and not force:
            same = _sha256_bytes(target.read_bytes()) == e.get("sha256")
            print(f"  skip {e['path']} ({'identical' if same else 'exists, use --force to overwrite'})")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        restored += 1
        print(f"  restored {e['path']}  ({len(data):,} bytes)")
    print(f"restore: {restored} file(s) written, {len(files)} in manifest")
    return restored, len(files)


def _write_readme(manifest: dict) -> None:
    lines = [
        "# Durable archive",
        "",
        "Partitioned, gzipped, sha256-verified copies of the benchmark's irreplaceable but gitignored data ",
        "(the graded panel + results, the full prompt registry, the distilled training sets), so a local or ",
        "website failure never loses them. Generated by `scripts/durable_archive.py` -- do not edit by hand.",
        "",
        f"- generated: `{manifest.get('generated')}`",
        f"- files: **{manifest.get('n_files', 0)}**  ·  source bytes: "
        f"**{manifest.get('total_source_bytes', 0):,}**  ·  compressed: **{manifest.get('total_compressed_bytes', 0):,}**",
        f"- chunk size: {manifest.get('chunk_bytes', CHUNK_BYTES):,} bytes",
        "",
        "Restore everything with `python scripts/durable_archive.py --restore` (verifies each file's sha256 ",
        "before writing; existing files are kept unless `--force`).",
        "",
        "| file | bytes | compressed | chunks |",
        "|---|---:|---:|---:|",
    ]
    for e in manifest.get("files", []):
        lines.append(f"| `{e['path']}` | {e['bytes']:,} | {e['compressed_bytes']:,} | {len(e['chunks'])} |")
    (ARCHIVE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        ok, total = verify()
        return 0 if ok == total else 1
    if args.restore:
        restore(force=args.force)
        return 0
    archive(include_large=args.include_large)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
