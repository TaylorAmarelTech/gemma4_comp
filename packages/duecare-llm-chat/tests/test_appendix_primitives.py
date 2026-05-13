"""Tests for duecare.appendix_primitives.

Covers: make_run_id contract, BundleEnvelope round-trip, extras
acceptance, HarnessTrace 5-layer invariant, validate_canonical
drift detection (incl. the Tier-1+2 rollover state), and
write_v1_bundle / read_v1_bundle round-trip.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from duecare.appendix_primitives import (
    BundleEnvelope,
    HarnessGrep,
    HarnessTrace,
    PerRow,
    make_run_id,
    read_v1_bundle,
    sha256_of_file,
    validate_canonical,
    write_v1_bundle,
)


# ---- make_run_id -----------------------------------------------------------

def test_make_run_id_with_variant() -> None:
    rid = make_run_id(
        "a01", "stock", "e2b-it", iso_ts="2026-05-12T19-30-00Z"
    )
    assert rid == "a01_e2b-it_stock_2026-05-12T19-30-00Z"


def test_make_run_id_no_variant() -> None:
    rid = make_run_id("a16", "local_kb", iso_ts="2026-05-12T19-30-00Z")
    assert rid == "a16_local_kb_2026-05-12T19-30-00Z"


def test_make_run_id_auto_ts_filename_safe() -> None:
    rid = make_run_id("a15", "ugc")
    ts = rid.split("_")[-1]
    assert ts.endswith("Z")
    assert "T" in ts
    assert ":" not in ts


def test_make_run_id_rejects_empty_slot() -> None:
    with pytest.raises(ValueError):
        make_run_id("", "stock")


def test_make_run_id_rejects_empty_purpose() -> None:
    with pytest.raises(ValueError):
        make_run_id("a01", "")


# ---- BundleEnvelope / PerRow / HarnessTrace --------------------------------

def test_bundle_envelope_defaults() -> None:
    env = BundleEnvelope(
        kernel_id="a-15-ugc",
        run_id="a15_ugc_2026-05-12T19-30-00Z",
    )
    assert env.schema_version == "1.0"
    assert env.summary == {}
    assert env.results == []


def test_bundle_envelope_round_trip() -> None:
    rows = [PerRow(row_id="r1", prompt_text="hi", response="hello")]
    env = BundleEnvelope(
        kernel_id="a-15-ugc",
        run_id="a15_ugc_2026-05-12T19-30-00Z",
        summary={"n": 1},
        results=rows,
    )
    dumped = env.model_dump(mode="json")
    assert dumped["schema_version"] == "1.0"
    assert dumped["results"][0]["row_id"] == "r1"
    revived = BundleEnvelope.model_validate(dumped)
    assert revived.results[0].response == "hello"


def test_bundle_envelope_extras_allowed() -> None:
    env = BundleEnvelope.model_validate({
        "schema_version": "1.0",
        "kernel_id": "a-11-pii",
        "run_id": "a11_pii_2026-05-12T19-30-00Z",
        "summary": {},
        "results": [],
        "results_by_condition": {"fine_tuned": [], "stock": []},
        "aggregate": {"acc": 0.95},
    })
    dumped = env.model_dump()
    assert dumped["results_by_condition"] == {
        "fine_tuned": [],
        "stock": [],
    }
    assert dumped["aggregate"] == {"acc": 0.95}


def test_per_row_extras_allowed() -> None:
    row = PerRow.model_validate({
        "row_id": "p1",
        "prompt_text": "test",
        "response": "ok",
        "verdict": "high_risk",
        "indicators": ["fee_camouflage"],
        "condition": "fine_tuned",
    })
    dumped = row.model_dump()
    assert dumped["verdict"] == "high_risk"
    assert dumped["condition"] == "fine_tuned"


def test_harness_trace_5_layers_always_present() -> None:
    trace = HarnessTrace()
    dumped = trace.model_dump(mode="json")
    for key in ("persona", "grep", "rag", "tools", "online"):
        assert key in dumped, f"missing layer key: {key}"
        assert dumped[key]["enabled"] is False


def test_harness_grep_with_rules_fired() -> None:
    grep = HarnessGrep(
        enabled=True,
        rules_evaluated=161,
        rules_fired=[
            {"rule_id": "ph_hk_zero_fee", "severity": "high"},
        ],
        elapsed_ms=4.2,
    )
    dumped = grep.model_dump(mode="json")
    assert dumped["rules_evaluated"] == 161
    assert dumped["rules_fired"][0]["rule_id"] == "ph_hk_zero_fee"


# ---- validate_canonical ----------------------------------------------------

def test_validate_canonical_clean() -> None:
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-15-ugc",
        "run_id": "a15_ugc_2026-05-12T19-30-00Z",
        "config": {},
        "metadata": {},
        "summary": {"n_results": 0},
        "results": [],
    }
    assert validate_canonical(payload) == []


def test_validate_canonical_flags_schema_drift() -> None:
    payload = {
        "schema_version": "duecare.a04_handoff.v1",
        "kernel_id": "a-06-prompt-generation",
        "run_id": "a06_synth_2026-05-12T19-30-00Z",
        "summary": {},
        "results": [],
    }
    findings = validate_canonical(payload)
    assert any("schema_version drift" in f for f in findings)


def test_validate_canonical_flags_aggregate_only() -> None:
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-15-ugc",
        "run_id": "a15_ugc_2026-05-12T19-30-00Z",
        "config": {},
        "metadata": {},
        "aggregate": {"n_results": 0},
        "results": [],
    }
    findings = validate_canonical(payload)
    assert any("aggregate" in f for f in findings)


def test_validate_canonical_flags_legacy_results_key() -> None:
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-18-sentinel-research-monitor",
        "run_id": "a18_sentinel_2026-05-12T19-30-00Z",
        "summary": {},
        "proposals": [],
    }
    findings = validate_canonical(payload)
    assert any("proposals[]" in f for f in findings)


def test_validate_canonical_rollover_state_is_clean() -> None:
    """Tier-1+2 rollover: BOTH canonical + alias present is OK."""
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-15-ugc",
        "run_id": "a15_ugc_2026-05-12T19-30-00Z",
        "config": {},
        "metadata": {},
        "summary": {"n_results": 0},
        "aggregate": {"n_results": 0},
        "results": [],
    }
    assert validate_canonical(payload) == []


# ---- write_v1_bundle / read_v1_bundle --------------------------------------

def test_write_v1_bundle_round_trip(tmp_path: Path) -> None:
    rows = [
        PerRow(row_id="p1", prompt_text="hi", response="hello"),
        PerRow(
            row_id="p2",
            prompt_text="risk?",
            response="see POEA MC 14-2017",
            citations=["POEA MC 14-2017"],
        ),
    ]
    env = BundleEnvelope(
        kernel_id="a-15-ugc",
        run_id="a15_ugc_2026-05-12T19-30-00Z",
        summary={"n_results": 2},
        results=rows,
    )
    paths = write_v1_bundle(env, tmp_path)

    assert paths["results_json"].is_file()
    assert paths["run_jsonl"].is_file()
    assert paths["metadata_json"].is_file()
    assert paths["bundle_zip"].is_file()

    manifest = paths["manifest"]
    assert manifest["schema_version"] == "1.0"
    assert manifest["files"] == [
        "results.json", "run.jsonl", "metadata.json",
    ]
    assert set(manifest["checksums"]) == {
        "results.json", "run.jsonl", "metadata.json",
    }

    jsonl_lines = (
        paths["run_jsonl"].read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(jsonl_lines) == 2
    first = json.loads(jsonl_lines[0])
    assert first["schema_version"] == "1.0"
    assert first["run_id"] == env.run_id
    assert first["kernel_id"] == env.kernel_id
    assert first["row_id"] == "p1"

    with zipfile.ZipFile(paths["bundle_zip"], "r") as zf:
        names = set(zf.namelist())
    assert names == {
        "manifest.json", "results.json", "run.jsonl", "metadata.json",
    }

    revived = read_v1_bundle(paths["bundle_zip"])
    assert revived.kernel_id == "a-15-ugc"
    assert len(revived.results) == 2
    assert revived.results[1].citations == ["POEA MC 14-2017"]


def test_metadata_json_omits_results(tmp_path: Path) -> None:
    env = BundleEnvelope(
        kernel_id="a-15-ugc",
        run_id="a15_ugc_2026-05-12T19-30-00Z",
        summary={"n_results": 1},
        results=[
            PerRow(row_id="p1", prompt_text="hi", response="hello"),
        ],
    )
    paths = write_v1_bundle(env, tmp_path)
    metadata = json.loads(
        paths["metadata_json"].read_text(encoding="utf-8")
    )
    assert "results" not in metadata
    assert metadata["summary"] == {"n_results": 1}
    assert metadata["kernel_id"] == "a-15-ugc"


def test_read_v1_bundle_rejects_unsupported_version(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad_bundle.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"schema_version": "0.5"}))
        zf.writestr("results.json", "{}")
    with pytest.raises(ValueError, match="schema_version"):
        read_v1_bundle(bad_zip)


def test_write_v1_bundle_creates_missing_dir(tmp_path: Path) -> None:
    env = BundleEnvelope(
        kernel_id="a-01-baseline",
        run_id="a01_stock_2026-05-12T19-30-00Z",
        summary={"n_results": 0},
        results=[],
    )
    nested = tmp_path / "kaggle" / "working"
    paths = write_v1_bundle(env, nested)
    assert nested.is_dir()
    assert paths["bundle_zip"].is_file()


# ---- sha256_of_file --------------------------------------------------------

def test_sha256_of_file_matches_known_digest(tmp_path: Path) -> None:
    """Digest for b'hello world\\n' is well-known."""
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello world\n")
    expected = (
        "a948904f2f0f479b8f8197694b30184b"
        "0d2ed1c1cd2a1ec0fb85d299a192a447"
    )
    assert sha256_of_file(f) == expected


def test_sha256_of_file_chunked_read_matches(tmp_path: Path) -> None:
    """Chunk size doesn't affect the digest (file > 8 KB chunks)."""
    f = tmp_path / "big.bin"
    f.write_bytes(b"x" * 32768)  # 4 chunks at default 8 KB
    a = sha256_of_file(f)
    b = sha256_of_file(f, chunk_size=1024)  # forces 32 chunks
    assert a == b
    assert len(a) == 64  # hex sha256 is 64 chars


def test_sha256_of_file_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    # Empty-content sha256 hex digest
    expected = (
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855"
    )
    assert sha256_of_file(f) == expected
