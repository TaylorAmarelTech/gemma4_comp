"""Tests for scripts/finetune_registry.py -- the fine-tune run provenance ledger."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fr = _load("finetune_registry", _ROOT / "scripts" / "finetune_registry.py")


def test_make_record_builds_provenance(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sft_examples": 200, "dpo_examples": 200, "selected_pairs": 200}),
                        encoding="utf-8")
    rec = fr.make_record(model_id="m-v0.1.0", base_model="google/gemma-4-e4b-it", status="trained",
                         created_utc="2026-06-26T22:40:00+00:00", git="abc1234", data_manifest=manifest)
    assert rec["model_id"] == "m-v0.1.0" and rec["status"] == "trained" and rec["git_sha"] == "abc1234"
    assert rec["data"]["manifest_sha256"] and len(rec["data"]["manifest_sha256"]) == 16   # dataset fingerprint
    assert rec["data"]["sft_examples"] == 200 and rec["data"]["dpo_examples"] == 200       # pulled from manifest


def test_make_record_rejects_bad_status():
    import pytest
    with pytest.raises(ValueError):
        fr.make_record(model_id="m", base_model="b", status="bogus", created_utc="t")


def test_file_sha256_is_deterministic_and_content_sensitive(tmp_path):
    p = tmp_path / "a.json"; p.write_text("hello", encoding="utf-8")
    q = tmp_path / "b.json"; q.write_text("world", encoding="utf-8")
    assert fr.file_sha256(p) == fr.file_sha256(p)        # deterministic -> reproducible dataset version
    assert fr.file_sha256(p) != fr.file_sha256(q)        # content-sensitive
    assert fr.file_sha256(tmp_path / "missing.json") is None and fr.file_sha256(None) is None


def test_append_preserves_history_and_latest_wins(tmp_path):
    reg = tmp_path / "finetune_registry.jsonl"
    r1 = fr.make_record(model_id="m", base_model="b", status="planned",
                        created_utc="2026-06-26T20:00:00+00:00")
    r2 = fr.make_record(model_id="m", base_model="b", status="trained",
                        created_utc="2026-06-26T22:00:00+00:00")
    fr.append(r1, reg)
    fr.append(r2, reg)
    records = fr.load(reg)
    assert len(records) == 2                              # append-only: prior 'planned' row never destroyed
    assert fr.latest_by_id(records)["m"]["status"] == "trained"   # queries collapse to the latest status
    assert r1["data"]["manifest_sha256"] is None         # no manifest -> None, no crash
