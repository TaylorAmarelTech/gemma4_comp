from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = _ROOT / "scripts" / "verify_training_dataset_claims.py"
SPEC = importlib.util.spec_from_file_location("verify_training_dataset_claims", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["verify_training_dataset_claims"] = MODULE
SPEC.loader.exec_module(MODULE)


def _stage_manifest(root: Path, rel: str, payload: dict) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_verified_when_staged_sha_and_counts_match(tmp_path: Path) -> None:
    rel = "reports/kaggle_publish/corpus_v1/dataset/release-manifest.json"
    sha = _stage_manifest(tmp_path, rel, {"counts": {"supervised_train": 100}})
    claim = {
        "dataset_id": "acct/corpus",
        "release_manifest_sha256": sha,
        "row_counts": {"supervised_train": 100},
        "staged_manifest_globs": [rel],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "verified"
    assert result["row_counts_verified"] == {"supervised_train": 100}


def test_mismatched_sha_is_a_hard_failure(tmp_path: Path) -> None:
    rel = "reports/kaggle_publish/corpus_v1/dataset/release-manifest.json"
    _stage_manifest(tmp_path, rel, {"counts": {"supervised_train": 100}})
    claim = {
        "dataset_id": "acct/corpus",
        "release_manifest_sha256": "0" * 64,
        "staged_manifest_globs": [rel],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "mismatch"
    assert any("release_manifest_sha256 mismatch" in issue for issue in result["issues"])


def test_row_count_mismatch_is_a_hard_failure(tmp_path: Path) -> None:
    rel = "reports/kaggle_publish/corpus_v1/dataset/release-manifest.json"
    sha = _stage_manifest(tmp_path, rel, {"counts": {"supervised_train": 99}})
    claim = {
        "dataset_id": "acct/corpus",
        "release_manifest_sha256": sha,
        "row_counts": {"supervised_train": 100},
        "staged_manifest_globs": [rel],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "mismatch"
    assert any("row-count mismatch" in issue for issue in result["issues"])


def test_missing_staged_artifact_is_published_only(tmp_path: Path) -> None:
    claim = {
        "dataset_id": "acct/corpus",
        "release_manifest_sha256": "a" * 64,
        "staged_manifest_globs": ["reports/kaggle_publish/nowhere/release-manifest.json"],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "published_only"
    assert result["issues"] == []


def test_registry_ok_is_false_on_any_mismatch(tmp_path: Path) -> None:
    good_rel = "reports/kaggle_publish/good/release-manifest.json"
    good_sha = _stage_manifest(tmp_path, good_rel, {"counts": {}})
    bad_rel = "reports/kaggle_publish/bad/release-manifest.json"
    _stage_manifest(tmp_path, bad_rel, {"counts": {}})
    registry = {
        "schema_version": "duecare.published_dataset_claims.v1",
        "claims": [
            {"dataset_id": "a/good", "release_manifest_sha256": good_sha,
             "staged_manifest_globs": [good_rel]},
            {"dataset_id": "a/bad", "release_manifest_sha256": "f" * 64,
             "staged_manifest_globs": [bad_rel]},
        ],
    }
    report = MODULE.verify_registry(registry, root=tmp_path)
    assert report["ok"] is False
    assert report["verified"] == 1 and report["mismatched"] == 1


def test_evidence_claims_verify_when_source_numbers_match(tmp_path: Path) -> None:
    rel = "reports/kaggle_publish/study_v1/dataset/release-manifest.json"
    sha = _stage_manifest(tmp_path, rel, {"counts": {}})
    receipt = tmp_path / "reports/kaggle_publish/study_v1/dataset/system-evidence/receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"judge": {"lift": 1.7329}}), encoding="utf-8")
    claim = {
        "dataset_id": "acct/study",
        "release_manifest_sha256": sha,
        "staged_manifest_globs": [rel],
        "evidence_claims": [
            {"label": "lift", "source": "system-evidence/receipt.json",
             "json_path": ["judge", "lift"], "expected": 1.73, "round_to": 2},
        ],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "verified"
    assert result["evidence_claims_verified"][0]["value"] == 1.73


def test_evidence_claim_drift_is_a_hard_failure(tmp_path: Path) -> None:
    rel = "reports/kaggle_publish/study_v1/dataset/release-manifest.json"
    sha = _stage_manifest(tmp_path, rel, {"counts": {}})
    receipt = tmp_path / "reports/kaggle_publish/study_v1/dataset/system-evidence/receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"judge": {"lift": 2.10}}), encoding="utf-8")
    claim = {
        "dataset_id": "acct/study",
        "release_manifest_sha256": sha,
        "staged_manifest_globs": [rel],
        "evidence_claims": [
            {"label": "lift", "source": "system-evidence/receipt.json",
             "json_path": ["judge", "lift"], "expected": 1.73, "round_to": 2},
        ],
    }
    result = MODULE.verify_claim(claim, root=tmp_path)
    assert result["status"] == "mismatch"
    assert any("lift: expected 1.73" in issue for issue in result["issues"])


def test_committed_registry_matches_docs_and_staged_when_present() -> None:
    registry = json.loads(MODULE.DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    report = MODULE.verify_registry(registry, root=_ROOT)
    # Every claim resolves to a verified or published-only state; a mismatch
    # here means the docs drifted from the staged release manifest.
    assert report["mismatched"] == 0
    assert report["total"] == len(registry["claims"])
    docs = (_ROOT / "docs" / "training_and_finetuning.md").read_text(encoding="utf-8")
    for claim in registry["claims"]:
        assert claim["release_manifest_sha256"] in docs
