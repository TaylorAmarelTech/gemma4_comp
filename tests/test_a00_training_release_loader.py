"""Focused release-bundle tests for the active A-00 Kaggle workbench."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
A00 = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    training_row_sha256,
    validate_training_rows,
)


SOURCE_KIND = "duecare.a00.synthetic.training_bundle.v2"
RELEASE_KIND = "duecare.kaggle.training_dataset_release.v1"


def _load_script(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RELEASE_BUILDER = _load_script(
    "a00_test_build_kaggle_training_release",
    ROOT / "scripts" / "build_kaggle_training_release.py",
)
PROOF_BUILDER = _load_script(
    "a00_test_build_kaggle_proof_training_bundle",
    ROOT / "scripts" / "build_kaggle_proof_training_bundle.py",
)


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class TrainRequest:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)


def _load_kernel_functions(names: set[str], namespace: dict[str, Any]) -> dict[str, Any]:
    tree = ast.parse(A00.read_text(encoding="utf-8"), filename=str(A00))
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    missing = names - {node.name for node in functions}
    assert not missing, f"A-00 functions missing from focused test loader: {sorted(missing)}"
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            *functions,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    exec(compile(module, str(A00), "exec"), namespace)
    return namespace


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _release_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, Any]]:
    source = tmp_path / "source"
    PROOF_BUILDER.build_bundle(source, force=True)
    root = tmp_path / "release"
    RELEASE_BUILDER.build_release(
        source / "source_manifest.json",
        approval_path=source / "publication_approval.json",
        output_dir=root,
    )
    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest_path, root / "sft_train.jsonl", root / "preference_train.jsonl", manifest


def _a00_release_validator() -> Any:
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "HTTPException": HTTPException,
        "TrainRequest": TrainRequest,
        "A00_RELEASE_TRAINING_HANDOFF_KIND": RELEASE_KIND,
        "A00_UPLOAD_LIMITS": {
            "max_jsonl_rows": 20_000,
            "max_jsonl_bytes": 200_000_000,
            "max_jsonl_line_chars": 200_000,
        },
        "hashlib": hashlib,
        "json": json,
        "re": re,
        "training_text_sha256": canonical_sha256,
        "validate_training_rows": validate_training_rows,
        "_canonical_release_verifier": lambda: RELEASE_BUILDER.verify_release_dir,
    }
    _load_kernel_functions(
        {
            "_artifact_sha256",
            "_contained_artifact",
            "_declared_hash_set",
            "_declared_lineage_set",
            "_read_training_jsonl",
            "_release_training_artifacts",
            "_resolve_release_training_file",
            "_selected_release_preference_path",
            "_training_row_prompt",
            "_verify_release_with_canonical_publisher",
            "_validated_release_training_bundle",
        },
        namespace,
    )
    return namespace["_validated_release_training_bundle"]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _refresh_release_file(root: Path, filename: str) -> dict[str, Any]:
    manifest_path = root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    path = root / filename
    entry = manifest["files"][filename]
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["bytes"] = path.stat().st_size
    if filename.endswith(".jsonl"):
        entry["rows"] = len(_read_jsonl(path))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _rewrite_release_rows(
    root: Path,
    filename: str,
    mutate: Any,
    *,
    every_row: bool = False,
) -> None:
    path = root / filename
    rows = _read_jsonl(path)
    targets = rows if every_row else rows[:1]
    for row in targets:
        mutate(row)
        row["sha256"] = training_row_sha256(row)
    _write_jsonl(path, rows)
    _refresh_release_file(root, filename)


def _a00_upload_loader(
    tmp_path: Path,
    *,
    limit_overrides: dict[str, int] | None = None,
) -> Any:
    upload_limits = {
        "max_jsonl_rows": 20_000,
        "max_zip_bytes": 200_000_000,
        "max_jsonl_bytes": 200_000_000,
        "max_jsonl_line_chars": 200_000,
        "max_member_bytes": 100_000_000,
        "max_uncompressed_bytes": 500_000_000,
        "max_upload_files": 8,
    }
    upload_limits.update(limit_overrides or {})
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "HTTPException": HTTPException,
        "TrainRequest": TrainRequest,
        "TRAIN_DIR": tmp_path / "uploads",
        "A00_RELEASE_TRAINING_HANDOFF_KIND": RELEASE_KIND,
        "A00_SUPPORTED_TRAINING_HANDOFF_KINDS": {SOURCE_KIND, RELEASE_KIND},
        "A00_UPLOAD_LIMITS": upload_limits,
        "A00_TRAINING_UPLOAD_MAX_FILES": 12,
        "A00_TRAINING_UPLOAD_MAX_COMPRESSION_RATIO": 200.0,
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
        "io": io,
        "json": json,
        "re": re,
        "zipfile": zipfile,
        "_inspect_training_rows": lambda path: {"path": str(path), "shape": "sft_messages"},
        "_training_suggestion": lambda path, manifest, inspection: {
            "data_path": str(path),
            "execute": False,
        },
        "_validated_training_bundle": lambda req, path: {"validation": {"ok": True}},
    }
    _load_kernel_functions(
        {
            "_contained_artifact",
            "_enforce_training_upload_size",
            "_load_training_data_upload",
            "_resolve_release_training_file",
            "_safe_slug",
            "_select_uploaded_training_manifest",
            "_training_upload_byte_limit",
            "_training_manifest_kind",
            "_validated_training_zip_members",
        },
        namespace,
    )
    return namespace["_load_training_data_upload"]


def test_a00_upload_maps_release_sft_and_preference_files(tmp_path: Path) -> None:
    load_upload = _a00_upload_loader(tmp_path)
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": RELEASE_KIND,
        "files": {
            "sft_train.jsonl": {},
            "preference_train.jsonl": {},
        },
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("release-manifest.json", json.dumps(manifest))
        archive.writestr("sft_train.jsonl", '{"messages": []}\n')
        archive.writestr("preference_train.jsonl", '{"chosen": "a", "rejected": "b"}\n')

    result = load_upload("release.zip", buffer.getvalue())

    assert Path(result["selected_data_path"]).name == "sft_train.jsonl"
    assert Path(result["selected_preference_path"]).name == "preference_train.jsonl"
    suggestion = result["suggested_train_request"]
    assert Path(suggestion["manifest_path"]).name == "release-manifest.json"
    assert Path(suggestion["dpo_path"]).name == "preference_train.jsonl"
    assert suggestion["method"] == "sft_then_dpo"


def test_a00_release_training_profile_distinguishes_full_preview_without_execution(
    tmp_path: Path,
) -> None:
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "HTTPException": HTTPException,
        "A00_RELEASE_TRAINING_HANDOFF_KIND": RELEASE_KIND,
        "A00_TRAINING_DEFAULT": {
            "base_model_ref": "google/gemma-4-E2B-it",
            "max_steps": 60,
            "dpo_max_steps": 30,
            "method": "sft_then_dpo",
        },
        "A00_SMALL_MODEL_REF": "google/gemma-4-E2B-it",
    }
    _load_kernel_functions({"_training_suggestion"}, namespace)
    manifest = {
        "handoff_kind": RELEASE_KIND,
        "release_tier": "preview",
        "counts": {"sft_train": 2048, "preference_train": 2048},
        "training_profile": {
            "id": "gemma4-e4b-full-preview",
            "scope": "full-preview",
            "base_model_ref": "google/gemma-4-E4B-it",
            "base_model_revision": "0" * 40,
            "max_steps": 400,
            "dpo_max_steps": 256,
            "method": "sft_then_dpo",
            "dpo_file": "preference_train.jsonl",
            "execute": False,
        },
    }

    suggestion = namespace["_training_suggestion"](
        tmp_path / "sft_train.jsonl",
        manifest,
        {"generator_modes": [], "harness_profiles": []},
    )

    assert suggestion["training_profile_id"] == "gemma4-e4b-full-preview"
    assert suggestion["training_scope"] == "full-preview"
    assert suggestion["dataset_counts"]["sft_train"] == 2048
    assert suggestion["base_model_ref"] == "google/gemma-4-E4B-it"
    assert suggestion["base_model_revision"] == "0" * 40
    assert suggestion["max_steps"] == 400
    assert suggestion["dpo_max_steps"] == 256
    assert suggestion["method"] == "sft_then_dpo"
    assert suggestion["profile_dpo_file"] == "preference_train.jsonl"
    assert suggestion["profile_execute_requested"] is False
    assert suggestion["execute"] is False

    manifest["training_profile"]["dpo_file"] = "unbound.jsonl"
    with pytest.raises(HTTPException, match="bind DPO to preference_train.jsonl"):
        namespace["_training_suggestion"](
            tmp_path / "sft_train.jsonl",
            manifest,
            {"generator_modes": [], "harness_profiles": []},
        )


def test_a00_training_script_uses_manifest_dpo_max_steps(tmp_path: Path) -> None:
    namespace: dict[str, Any] = {
        "Path": Path,
        "A00_TRAINING_DEFAULT": {
            "max_seq_length": 2048,
            "per_device_train_batch_size": 1,
            "gradient_accumulation_steps": 8,
            "warmup_steps": 5,
            "lora_r": 16,
            "lora_alpha": 16,
            "lora_dropout": 0.0,
            "random_state": 3407,
            "target_modules": ["q_proj", "k_proj"],
            "dpo_max_steps": 30,
            "dpo_learning_rate": 5e-6,
            "dpo_beta": 0.1,
        },
    }
    _load_kernel_functions({"_training_script"}, namespace)
    req = SimpleNamespace(
        base_model_ref="unsloth/gemma-4-E2B-it",
        base_model_revision="4abfca14e6c6bfb5888b80288185b1243fb8d539",
        dpo_path=str(tmp_path / "preference_train.jsonl"),
        method="sft_then_dpo",
        max_steps=400,
        dpo_max_steps=256,
        learning_rate=2e-5,
        resume_from_checkpoint="",
        save_steps=20,
        save_total_limit=2,
    )

    script = namespace["_training_script"](req, str(tmp_path / "sft_train.jsonl"), tmp_path / "out")

    assert "MAX_STEPS = 400" in script
    assert "DPO_MAX_STEPS = 256" in script
    assert "DPO_MAX_STEPS = 30" not in script


def test_a00_ui_applies_manifest_profile_but_keeps_execution_manual() -> None:
    text = A00.read_text(encoding="utf-8")
    for marker in (
        'id="training-profile-summary"',
        "function applyTrainingSuggestion(suggestion)",
        '$("execute-train").value = "false"',
        "lastTrainingSuggestion.data_path === selectedDataPath",
        'dpo_path: profile.dpo_path || ""',
        'manifest_path: profile.manifest_path || ""',
        'method: profile.method || "sft_then_dpo"',
    ):
        assert marker in text


def test_a00_training_zip_rejects_sanitized_path_collisions(tmp_path: Path) -> None:
    load_upload = _a00_upload_loader(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("same path/data.jsonl", "{}\n")
        archive.writestr("same-path/data.jsonl", "{}\n")

    with pytest.raises(HTTPException, match="colliding member paths"):
        load_upload("collision.zip", buffer.getvalue())


def test_a00_training_zip_rejects_member_count_and_compression_bombs(tmp_path: Path) -> None:
    load_upload = _a00_upload_loader(tmp_path)
    too_many = io.BytesIO()
    with zipfile.ZipFile(too_many, "w") as archive:
        for index in range(13):
            archive.writestr(f"row-{index}.jsonl", "{}\n")
    with pytest.raises(HTTPException, match="12-file limit"):
        load_upload("too-many.zip", too_many.getvalue())

    compressed = io.BytesIO()
    with zipfile.ZipFile(compressed, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("sft_train.jsonl", "A" * 1_000_000)
    with pytest.raises(HTTPException, match="unsafe compression ratio"):
        load_upload("compression-bomb.zip", compressed.getvalue())


def test_a00_training_upload_rejects_compressed_member_and_total_size_limits(
    tmp_path: Path,
) -> None:
    with pytest.raises(HTTPException, match="5-byte limit"):
        _a00_upload_loader(tmp_path, limit_overrides={"max_jsonl_bytes": 5})(
            "rows.jsonl",
            b'{"row": 1}\n',
        )

    one_member = io.BytesIO()
    with zipfile.ZipFile(one_member, "w") as archive:
        archive.writestr("sft_train.jsonl", "123456")
    with pytest.raises(HTTPException, match="member is too large"):
        _a00_upload_loader(tmp_path, limit_overrides={"max_member_bytes": 5})(
            "member.zip",
            one_member.getvalue(),
        )

    total = io.BytesIO()
    with zipfile.ZipFile(total, "w") as archive:
        archive.writestr("one.jsonl", "123456")
        archive.writestr("two.jsonl", "123456")
    with pytest.raises(HTTPException, match="total uncompressed-byte limit"):
        _a00_upload_loader(tmp_path, limit_overrides={"max_uncompressed_bytes": 10})(
            "total.zip",
            total.getvalue(),
        )

    with pytest.raises(HTTPException, match="10-byte limit"):
        _a00_upload_loader(tmp_path, limit_overrides={"max_zip_bytes": 10})(
            "compressed.zip",
            one_member.getvalue(),
        )


def test_a00_training_zip_allows_the_exact_ten_file_release_surface(tmp_path: Path) -> None:
    manifest_path, _, _, _ = _release_fixture(tmp_path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(manifest_path.parent.iterdir()):
            archive.write(path, arcname=path.name)

    result = _a00_upload_loader(tmp_path)("verified-release.zip", buffer.getvalue())

    assert Path(result["selected_data_path"]).name == "sft_train.jsonl"
    assert len(result["jsonl_candidates"]) == 4


def _verifier_namespace(**overrides: Any) -> dict[str, Any]:
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "Callable": Any,
        "A00_DUECARE_SOURCE_ROOT": ROOT,
        "DUECARE_COMMIT_SHA": "test-source",
        "_A00_CANONICAL_RELEASE_VERIFIER": None,
        "_A00_CANONICAL_RELEASE_VERIFIER_SHA256": None,
        "hashlib": hashlib,
        "os": __import__("os"),
        "importlib": __import__("importlib"),
        "sys": sys,
    }
    namespace.update(overrides)
    _load_kernel_functions(
        {"_canonical_release_verifier", "_verifier_module_sha256"}, namespace
    )
    return namespace


def test_a00_loads_the_canonical_verifier_from_pinned_source(tmp_path: Path) -> None:
    manifest_path, _, _, _ = _release_fixture(tmp_path)
    namespace = _verifier_namespace()

    verifier = namespace["_canonical_release_verifier"]()

    assert verifier(manifest_path.parent)["ok"] is True


def test_a00_records_the_verifier_bytes_for_audit(monkeypatch: Any) -> None:
    monkeypatch.delenv("DUECARE_A00_EXPECTED_VERIFIER_SHA256", raising=False)
    namespace = _verifier_namespace()
    namespace["_canonical_release_verifier"]()
    verifier_path = ROOT / "scripts" / "build_kaggle_training_release.py"
    expected = namespace["_verifier_module_sha256"](verifier_path)
    assert namespace["_A00_CANONICAL_RELEASE_VERIFIER_SHA256"] == expected
    assert len(expected) == 64


def test_a00_verifier_fails_closed_on_expected_hash_mismatch(monkeypatch: Any) -> None:
    monkeypatch.setenv("DUECARE_A00_EXPECTED_VERIFIER_SHA256", "deadbeef" * 8)
    namespace = _verifier_namespace()
    with pytest.raises(RuntimeError, match="does not match the pinned"):
        namespace["_canonical_release_verifier"]()


def test_a00_verifier_accepts_matching_pinned_hash(tmp_path: Path, monkeypatch: Any) -> None:
    verifier_path = ROOT / "scripts" / "build_kaggle_training_release.py"
    probe = _verifier_namespace()
    real_hash = probe["_verifier_module_sha256"](verifier_path)
    monkeypatch.setenv("DUECARE_A00_EXPECTED_VERIFIER_SHA256", real_hash.upper())
    manifest_path, _, _, _ = _release_fixture(tmp_path)
    namespace = _verifier_namespace()
    verifier = namespace["_canonical_release_verifier"]()
    assert verifier(manifest_path.parent)["ok"] is True


def test_a00_training_jsonl_reader_enforces_byte_row_and_line_limits(tmp_path: Path) -> None:
    def reader(limits: dict[str, int]) -> Any:
        namespace: dict[str, Any] = {
            "Any": Any,
            "Path": Path,
            "HTTPException": HTTPException,
            "A00_UPLOAD_LIMITS": limits,
            "json": json,
        }
        _load_kernel_functions({"_read_training_jsonl"}, namespace)
        return namespace["_read_training_jsonl"]

    path = tmp_path / "rows.jsonl"
    path.write_text("{}\n{}\n{}\n", encoding="utf-8")
    with pytest.raises(HTTPException, match="row limit"):
        reader({"max_jsonl_bytes": 100, "max_jsonl_rows": 2, "max_jsonl_line_chars": 20})(path)

    path.write_text(json.dumps({"value": "x" * 30}) + "\n", encoding="utf-8")
    with pytest.raises(HTTPException, match="line limit"):
        reader({"max_jsonl_bytes": 100, "max_jsonl_rows": 2, "max_jsonl_line_chars": 20})(path)

    with pytest.raises(HTTPException, match="exceeds 5 bytes"):
        reader({"max_jsonl_bytes": 5, "max_jsonl_rows": 2, "max_jsonl_line_chars": 200})(path)


def test_a00_release_validation_accepts_bound_rows_and_blocks_tampering(tmp_path: Path) -> None:
    validate_release = _a00_release_validator()
    manifest_path, sft_path, preference_path, manifest = _release_fixture(tmp_path)
    req = SimpleNamespace(dpo_path=str(preference_path), method="sft_then_dpo")

    verified = validate_release(req, sft_path, manifest_path, manifest)

    assert verified["validation"]["ok"] is True
    assert verified["canonical_release_verification"]["ok"] is True
    assert verified["dpo_path"] == preference_path.resolve()
    assert verified["sft_rows"] == 24
    assert verified["dpo_rows"] == 24

    preference_path.write_text(
        preference_path.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )
    with pytest.raises(HTTPException, match="checksum mismatch"):
        validate_release(req, sft_path, manifest_path, manifest)


def _apply_release_defect(root: Path, defect: str) -> str:
    if defect == "rights_holder":
        _rewrite_release_rows(
            root,
            "sft_train.jsonl",
            lambda row: row.__setitem__("rights_holder", "Different rights holder"),
        )
        return "rights holder"
    if defect == "training_permission":
        _rewrite_release_rows(
            root,
            "sft_train.jsonl",
            lambda row: row.__setitem__("allow_training_use", False),
        )
        return "training-use permission"
    if defect == "redistribution_permission":
        _rewrite_release_rows(
            root,
            "sft_train.jsonl",
            lambda row: row.__setitem__("allow_public_redistribution", False),
        )
        return "redistribution permission"
    if defect == "model_revision":
        _rewrite_release_rows(
            root,
            "sft_train.jsonl",
            lambda row: row.__setitem__("model_revision", "main"),
        )
        return "unpinned model revision"
    if defect == "id_parity":
        _rewrite_release_rows(
            root,
            "preference_train.jsonl",
            lambda row: row.__setitem__("id", "different-preference-id"),
        )
        return "ids do not match"
    if defect == "length_bias":
        _rewrite_release_rows(
            root,
            "preference_train.jsonl",
            lambda row: row.__setitem__(
                "chosen",
                "Preserve records and seek trusted support. " * 80,
            ),
            every_row=True,
        )
        return "length-bias"
    if defect == "grounding":
        def unground_sft(row: dict[str, Any]) -> None:
            row["source_refs"] = []
            row["knowledge_pack_refs"] = []
            for message in row["messages"]:
                if message.get("role") == "assistant":
                    message["content"] = "Keep a private copy and ask a trusted person for support."

        def unground_preference(row: dict[str, Any]) -> None:
            row["source_refs"] = []
            row["knowledge_pack_refs"] = []
            row["chosen"] = "Keep a private copy and ask a trusted person for support."
            row["rejected"] = "Do nothing and discard the records."

        _rewrite_release_rows(root, "sft_train.jsonl", unground_sft, every_row=True)
        _rewrite_release_rows(
            root,
            "preference_train.jsonl",
            unground_preference,
            every_row=True,
        )
        return "source-grounding"
    if defect == "approval_binding":
        approval_path = root / "publication_approval.json"
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approval["source_manifest_sha256"] = "0" * 64
        approval_path.write_text(json.dumps(approval, indent=2), encoding="utf-8")
        manifest = _refresh_release_file(root, "publication_approval.json")
        manifest["publication_approval"]["approval_sha256"] = hashlib.sha256(
            approval_path.read_bytes()
        ).hexdigest()
        (root / "release-manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return "not bound"
    if defect == "source_audit":
        audit_path = root / "source_audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["clean"] = False
        audit["risk_flags"] = ["review_pending"]
        audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        _refresh_release_file(root, "source_audit.json")
        return "source audit is not clean"
    if defect == "release_surface":
        (root / "DATA_CARD.md").unlink()
        manifest_path = root / "release-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].pop("DATA_CARD.md")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return "required publication surface"
    raise AssertionError(f"unknown test defect: {defect}")


@pytest.mark.parametrize(
    "defect",
    [
        "rights_holder",
        "training_permission",
        "redistribution_permission",
        "model_revision",
        "id_parity",
        "length_bias",
        "grounding",
        "approval_binding",
        "source_audit",
        "release_surface",
    ],
)
def test_a00_release_validation_mirrors_every_publication_gate(
    tmp_path: Path,
    defect: str,
) -> None:
    validate_release = _a00_release_validator()
    manifest_path, sft_path, preference_path, _ = _release_fixture(tmp_path)
    expected = _apply_release_defect(manifest_path.parent, defect)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    req = SimpleNamespace(dpo_path=str(preference_path), method="sft_then_dpo")

    with pytest.raises(HTTPException, match=expected):
        validate_release(req, sft_path, manifest_path, manifest)
