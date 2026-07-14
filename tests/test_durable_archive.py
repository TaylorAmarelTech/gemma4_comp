"""scripts/durable_archive.py: partitioned, gzipped, sha256-verified archive of the irreplaceable but
gitignored benchmark data, so a local or website failure never loses it. Round-trip + integrity + safety.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("durable_archive", _ROOT / "scripts" / "durable_archive.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["durable_archive"] = mod
    spec.loader.exec_module(mod)
    return mod


da = _load()


def _write_manifest(entry: dict) -> None:
    da.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated": "2026-07-14T00:00:00Z",
        "chunk_bytes": da.CHUNK_BYTES,
        "n_files": 1,
        "total_source_bytes": entry["bytes"],
        "total_compressed_bytes": entry["compressed_bytes"],
        "files": [entry],
    }
    da.MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "big").mkdir()
    arch = tmp_path / "archive"
    monkeypatch.setattr(da, "_ROOT", tmp_path)
    monkeypatch.setattr(da, "ARCHIVE_DIR", arch)
    monkeypatch.setattr(da, "MANIFEST", arch / "manifest.json")
    monkeypatch.setattr(da, "SOURCE_GLOBS", ["src/*.jsonl"])
    monkeypatch.setattr(da, "OPTIONAL_LARGE_GLOBS", ["src/big/*.jsonl"])
    monkeypatch.setattr(da, "CHUNK_BYTES", 4096)   # small, to force multi-chunk on larger inputs
    return tmp_path


def test_round_trip_restore_is_byte_identical(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    content = "\n".join(f'{{"prompt_id":"P{i}","score":{i % 100}}}' for i in range(2000)).encode()
    src.write_bytes(content)
    da.archive(quiet=True)
    assert da.verify() == (1, 1)
    src.unlink()                       # simulate a local loss
    da.restore()
    assert src.read_bytes() == content


def test_default_sources_include_complete_perdim_closure_artifacts():
    assert {
        "reports/rich_lift/panel_perdim.jsonl",
        "reports/rich_lift/panel_perdim.coverage.json",
        "reports/rich_lift/panel_perdim.jsonl.components.sqlite3",
    }.issubset(set(da.SOURCE_GLOBS))


def test_live_wal_sqlite_is_archived_through_consistent_backup(sandbox, monkeypatch):
    monkeypatch.setattr(da, "SOURCE_GLOBS", ["src/*.sqlite3"])
    monkeypatch.setattr(da, "OPTIONAL_LARGE_GLOBS", [])
    source = sandbox / "src" / "panel_perdim.jsonl.components.sqlite3"
    live = sqlite3.connect(source)
    try:
        assert live.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("CREATE TABLE component_cells (cell_id TEXT PRIMARY KEY, slot_count INTEGER)")
        live.execute("INSERT INTO component_cells VALUES ('cell-1', 5)")
        live.commit()
        assert Path(f"{source}-wal").exists(), "fixture must exercise an active WAL database"

        manifest = da.archive(quiet=True)
        entry = manifest["files"][0]
        snapshot = sandbox / "snapshot.sqlite3"
        snapshot.write_bytes(da._reassemble(entry))
        with sqlite3.connect(snapshot) as archived:
            assert archived.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert archived.execute(
                "SELECT cell_id, slot_count FROM component_cells"
            ).fetchall() == [("cell-1", 5)]
    finally:
        live.close()


def test_large_input_is_chunked_and_reassembles(sandbox):
    src = sandbox / "src" / "big" / "results.jsonl"
    content = b"\n".join(
        json.dumps({"row": i, "payload": os.urandom(96).hex()}, sort_keys=True).encode()
        for i in range(160)
    )
    src.write_bytes(content)
    manifest = da.archive(quiet=True, include_large=True)
    entry = next(e for e in manifest["files"] if e["path"].endswith("results.jsonl"))
    assert len(entry["chunks"]) >= 2, "large file must be partitioned"
    assert da.verify()[0] == manifest["n_files"]
    src.unlink()
    da.restore()
    assert src.read_bytes() == content


def test_verify_detects_corruption(sandbox):
    (sandbox / "src" / "panel.jsonl").write_bytes(b'{"grade":"complete"}\n' * 500)
    manifest = da.archive(quiet=True)
    chunk = da.ARCHIVE_DIR / manifest["files"][0]["chunks"][0]
    chunk.write_bytes(b"\x00" * chunk.stat().st_size)   # tamper: overwrite with zeros
    ok, total = da.verify()
    assert ok < total, "corruption must be caught, not silently accepted"


def test_deterministic_and_idempotent(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    src.write_bytes(b'{"a":1}\n' * 1000)
    m1 = da.archive(quiet=True)
    chunk = da.ARCHIVE_DIR / m1["files"][0]["chunks"][0]
    first = chunk.read_bytes()
    m2 = da.archive(quiet=True)                     # re-run, unchanged source
    assert chunk.read_bytes() == first, "deterministic gzip must not churn"
    assert m2["files"][0]["sha256"] == m1["files"][0]["sha256"]


def test_changed_source_is_re_archived(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    src.write_bytes(b'{"v":1}\n')
    first = da.archive(quiet=True)["files"][0]
    sha1 = first["sha256"]
    old_chunks = {da.ARCHIVE_DIR / name for name in first["chunks"]}
    src.write_bytes(b'{"v":1}\n{"v":2}\n')            # grow it
    second = da.archive(quiet=True)["files"][0]
    sha2 = second["sha256"]
    assert sha1 != sha2
    assert not any(path.exists() for path in old_chunks), "obsolete chunks must not be orphaned"
    src.unlink()
    da.restore()
    assert src.read_bytes() == b'{"v":1}\n{"v":2}\n'


def test_forbidden_pii_and_binary_paths_excluded(sandbox, monkeypatch):
    monkeypatch.setattr(da, "SOURCE_GLOBS", ["src/**/*"])
    (sandbox / "src" / "drive_text_cache").mkdir()
    (sandbox / "src" / "drive_text_cache" / "case.txt").write_text("real worker narrative")
    (sandbox / "src" / "model.safetensors").write_bytes(b"weights")
    (sandbox / "src" / "safe.jsonl").write_text("{}")
    rels = {da._rel(p) for p in da.iter_sources()}
    assert "src/safe.jsonl" in rels
    assert not any("drive_text_cache" in r for r in rels), "PII cache must never be archived"
    assert not any(r.endswith(".safetensors") for r in rels), "model weights must never be archived"


def test_include_large_is_opt_in(sandbox):
    (sandbox / "src" / "panel.jsonl").write_text("{}")
    (sandbox / "src" / "big" / "results.jsonl").write_text("{}")
    default = {da._rel(p) for p in da.iter_sources()}
    with_large = {da._rel(p) for p in da.iter_sources(include_large=True)}
    assert "src/big/results.jsonl" not in default
    assert "src/big/results.jsonl" in with_large


def test_restore_does_not_clobber_without_force(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    src.write_bytes(b'{"state":"original archived"}\n')
    da.archive(quiet=True)
    src.write_bytes(b'{"state":"newer local edits"}\n')  # local file is newer than the archive
    assert da.main(["--restore"]) == 1              # incomplete: default keeps the newer local file
    assert src.read_bytes() == b'{"state":"newer local edits"}\n'
    assert da.main(["--restore", "--force"]) == 0  # force: overwrite from archive
    assert src.read_bytes() == b'{"state":"original archived"}\n'


def test_optional_entry_survives_rerun_without_include_large(sandbox):
    panel = sandbox / "src" / "panel.jsonl"
    results = sandbox / "src" / "big" / "results.jsonl"
    panel.write_text('{"panel":1}\n', encoding="utf-8")
    results.write_text('{"result":1}\n', encoding="utf-8")
    first = da.archive(quiet=True, include_large=True)
    optional = next(e for e in first["files"] if e["path"].endswith("results.jsonl"))

    panel.write_text('{"panel":2}\n', encoding="utf-8")
    second = da.archive(quiet=True)

    retained = next(e for e in second["files"] if e["path"].endswith("results.jsonl"))
    assert retained == optional
    assert all((da.ARCHIVE_DIR / chunk).exists() for chunk in retained["chunks"])
    assert da.verify() == (2, 2)


def test_missing_source_entry_survives_rerun_and_can_be_restored(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    content = b'{"grade":"irreplaceable"}\n'
    src.write_bytes(content)
    first = da.archive(quiet=True)
    src.unlink()

    second = da.archive(quiet=True)

    assert second["files"] == first["files"]
    assert da.restore() == (1, 1)
    assert src.read_bytes() == content


def test_populated_pii_like_field_is_rejected_without_exposing_value(sandbox, capsys):
    src = sandbox / "src" / "panel.jsonl"
    private_value = "named.person@private-mail.example.org"
    src.write_text(json.dumps({"worker_email": private_value}) + "\n", encoding="utf-8")

    assert da.main([]) == 1

    output = capsys.readouterr().out
    assert "contact_field=1" in output
    assert "matched values are intentionally omitted" in output
    assert private_value not in output
    assert not da.MANIFEST.exists()


def test_contact_named_aggregate_metrics_are_not_treated_as_contact_records(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    src.write_text(json.dumps({"audit": {"ok_phone": True, "phone": 0}}) + "\n", encoding="utf-8")

    manifest = da.archive(quiet=True)

    assert manifest["n_files"] == 1


def test_corrupt_restore_returns_nonzero_without_writing_target(sandbox):
    src = sandbox / "src" / "panel.jsonl"
    src.write_bytes(b'{"grade":"complete"}\n')
    manifest = da.archive(quiet=True)
    chunk = da.ARCHIVE_DIR / manifest["files"][0]["chunks"][0]
    src.unlink()
    chunk.write_bytes(b"not a gzip stream")

    assert da.main(["--restore"]) == 1
    assert not src.exists()


def test_unreadable_manifest_restore_returns_nonzero(sandbox):
    da.ARCHIVE_DIR.mkdir(parents=True)
    da.MANIFEST.write_text("{not valid json", encoding="utf-8")

    assert da.main(["--restore"]) == 1


def test_restore_rejects_source_traversal_before_writing(sandbox):
    outside = sandbox.parent / f"{sandbox.name}-outside.jsonl"
    outside.write_bytes(b"do not overwrite")
    try:
        raw = b'{"archived":true}\n'
        compressed = da._gzip_deterministic(raw)
        source = f"../{outside.name}"
        _write_manifest({
            "path": source,
            "sha256": da._sha256_bytes(raw),
            "bytes": len(raw),
            "compressed_bytes": len(compressed),
            "chunks": [f"{source}.gz.000"],
        })

        assert da.main(["--restore", "--force"]) == 1
        assert outside.read_bytes() == b"do not overwrite"
    finally:
        outside.unlink(missing_ok=True)


def test_restore_rejects_chunk_traversal_before_reading(sandbox):
    raw = b'{"archived":true}\n'
    compressed = da._gzip_deterministic(raw)
    _write_manifest({
        "path": "src/panel.jsonl",
        "sha256": da._sha256_bytes(raw),
        "bytes": len(raw),
        "compressed_bytes": len(compressed),
        "chunks": ["../outside.gz.000"],
    })

    assert da.main(["--restore"]) == 1
    assert not (sandbox / "src" / "panel.jsonl").exists()


def test_restore_rejects_destination_directory_symlink_escape(sandbox):
    source = sandbox / "src" / "panel.jsonl"
    source.write_bytes(b'{"grade":"irreplaceable"}\n')
    da.archive(quiet=True)
    source.unlink()
    (sandbox / "src" / "big").rmdir()
    (sandbox / "src").rmdir()
    outside = sandbox.parent / f"{sandbox.name}-restore-target"
    outside.mkdir()
    try:
        try:
            os.symlink(outside, sandbox / "src", target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            pytest.skip(f"directory symlinks are unavailable: {type(exc).__name__}")

        assert da.main(["--restore", "--force"]) == 1
        assert not (outside / "panel.jsonl").exists()
    finally:
        link = sandbox / "src"
        if link.is_symlink():
            link.unlink()
        outside.rmdir()
