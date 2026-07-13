"""scripts/durable_archive.py: partitioned, gzipped, sha256-verified archive of the irreplaceable but
gitignored benchmark data, so a local or website failure never loses it. Round-trip + integrity + safety.
"""
from __future__ import annotations

import importlib.util
import os
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


def test_large_input_is_chunked_and_reassembles(sandbox):
    src = sandbox / "src" / "big" / "results.jsonl"
    content = os.urandom(12000)         # incompressible -> gzip ~same size -> several 4096-byte chunks
    src.write_bytes(content)
    manifest = da.archive(quiet=True, include_large=True)
    entry = next(e for e in manifest["files"] if e["path"].endswith("results.jsonl"))
    assert len(entry["chunks"]) >= 2, "large file must be partitioned"
    assert da.verify()[0] == manifest["n_files"]
    src.unlink()
    da.restore()
    assert src.read_bytes() == content


def test_verify_detects_corruption(sandbox):
    (sandbox / "src" / "panel.jsonl").write_bytes(b"grade rows here " * 500)
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
    sha1 = da.archive(quiet=True)["files"][0]["sha256"]
    src.write_bytes(b'{"v":1}\n{"v":2}\n')            # grow it
    sha2 = da.archive(quiet=True)["files"][0]["sha256"]
    assert sha1 != sha2
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
    src.write_bytes(b"original archived")
    da.archive(quiet=True)
    src.write_bytes(b"newer local edits")            # local file is newer than the archive
    da.restore()                                     # default: keep the newer local file
    assert src.read_bytes() == b"newer local edits"
    da.restore(force=True)                           # force: overwrite from archive
    assert src.read_bytes() == b"original archived"
