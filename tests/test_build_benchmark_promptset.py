"""Tests for scripts/build_benchmark_promptset.py domain promptset support."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bps = _load("build_benchmark_promptset", _ROOT / "scripts" / "build_benchmark_promptset.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_developing_country_worker_protections_domain_promptset_builds_from_registry():
    doc = bps.build_domain_promptset("developing_country_worker_protections", max_prompt_chars=6000)
    assert doc["version"] == "domain-seed-0.1"
    assert doc["domain"] == "developing_country_worker_protections"
    assert doc["_build"]["seed_rows"] == 12
    assert doc["_build"]["kept"] == 12
    assert doc["_build"]["dropped"] == {}
    assert doc["_domain_spec"]["status"].startswith("seed (propose-only")
    assert "ILO C189" in doc["_domain_spec"]["instruments"]
    assert "B_law" in doc["_domain_spec"]["rubric_anchors"]
    assert doc["_grounding"]["verified_source_count"] == 4
    assert "BD" in doc["_grounding"]["pending_jurisdictions"]
    assert doc["_domain_spec"]["grounding"] == doc["_grounding"]

    prompts = doc["prompts"]
    assert {p["domain"] for p in prompts} == {"developing_country_worker_protections"}
    assert {p["source"] for p in prompts} == {"domain_seed:developing_country_worker_protections"}
    assert {p["seed_source"] for p in prompts} == {"synthetic_rights_miss_seed"}
    assert len({p["category"] for p in prompts}) >= 8


def test_domain_cli_writes_separate_promptset_without_mutating_canonical_scheme(tmp_path):
    scheme_hash_before = _sha256(bps.SCHEME)
    out = tmp_path / "worker_protections_promptset.json"
    rc = bps.main([
        "--domain", "developing_country_worker_protections",
        "--out", str(out),
    ])
    assert rc == 0
    assert _sha256(bps.SCHEME) == scheme_hash_before
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["domain"] == "developing_country_worker_protections"
    assert len(doc["prompts"]) == 12


def test_domain_cli_rejects_full_registry_for_non_trafficking_domain(tmp_path):
    with pytest.raises(SystemExit):
        bps.main([
            "--domain", "developing_country_worker_protections",
            "--full",
            "--out", str(tmp_path / "ignored.json"),
        ])


def test_domain_helper_rejects_non_jsonl_built_spec_domain():
    with pytest.raises(ValueError, match="only jsonl seed packs"):
        bps.build_domain_promptset("trafficking", max_prompt_chars=6000)
