"""Tests for scripts/build_reasoning_sft_variant.py -- non-duplicating repaired SFT arm."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


variant = _load("build_reasoning_sft_variant", _ROOT / "scripts" / "build_reasoning_sft_variant.py")


def _row(pid: str, assistant: str, *, repaired: bool = False) -> dict:
    meta = {"prompt_id": pid}
    if repaired:
        meta["reasoning_repair"] = {
            "source": "reasoning_gap_queue",
            "original_prompt_id": pid,
            "category": "labor_trafficking",
            "added_links": ["statute"],
            "repaired_n_steps": 4,
        }
    return {
        "messages": [
            {"role": "user", "content": f"private prompt {pid}"},
            {"role": "assistant", "content": assistant},
        ],
        "_meta": meta,
    }


def _assistant(row: dict) -> str:
    return row["messages"][-1]["content"]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _repair_manifest(repaired_path: Path, *, rows: int, safe: bool = True,
                     privacy_ok: bool = True) -> dict:
    return {
        "output_path": str(repaired_path),
        "repaired_rows": rows,
        "safe_to_train": safe,
        "require_core_remedies": False,
        "by_added_core_remedy": {},
        "metadata_only": True,
        "repair_manifest_issues": [],
        "source_queue_issues": [],
        "source_queue": {
            "metadata_only": True,
            "privacy_scan_ok": privacy_ok,
            "safe_for_repair": privacy_ok,
            "actionable_for_repair": True,
            "queue_manifest_issues": [] if privacy_ok else ["reasoning_gap_queue_privacy_scan_not_ok"],
            "queued": rows,
            "target_links": ["statute", "action"],
            "require_core_remedies": False,
            "by_core_missing": {},
        },
    }


def test_variant_replaces_matching_prompt_id_without_appending():
    base = [_row("a", "old a"), _row("b", "old b")]
    repaired = [_row("b", "new b", repaired=True)]
    doc = variant.build_variant(base, repaired)
    assert len(doc["rows"]) == 2
    assert [_assistant(r) for r in doc["rows"]] == ["old a", "new b"]
    assert doc["manifest"]["base_rows"] == 2
    assert doc["manifest"]["output_rows"] == 2
    assert doc["manifest"]["replaced_rows"] == 1
    assert doc["manifest"]["same_size_as_base"] is True
    assert doc["manifest"]["by_category"] == {"labor_trafficking": 1}
    assert doc["manifest"]["base_prompt_ids"] == 2
    assert doc["manifest"]["output_prompt_ids"] == 2
    assert doc["manifest"]["repaired_row_metadata_issues"] == []
    assert doc["manifest"]["one_row_per_base_prompt"] is True
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["rows"][1]["_meta"]["sft_variant"]["replacement"] is True


def test_variant_accepts_core_remedy_only_repairs_when_source_manifest_is_core_enabled():
    repaired = [_row("a", "new a", repaired=True)]
    repair = repaired[0]["_meta"]["reasoning_repair"]
    repair["added_links"] = []
    repair["added_core_remedies"] = ["compensation_damages", "non_punishment"]
    repair["original_target_core_missing"] = ["compensation_damages", "non_punishment"]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1)
    manifest["require_core_remedies"] = True
    manifest["by_added_core_remedy"] = {"compensation_damages": 1, "non_punishment": 1}
    manifest["source_queue"]["require_core_remedies"] = True
    manifest["source_queue"]["by_core_missing"] = {"compensation_damages": 1, "non_punishment": 1}

    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["by_added_link"] == {}
    assert doc["manifest"]["by_added_core_remedy"] == {
        "compensation_damages": 1,
        "non_punishment": 1,
    }
    assert doc["manifest"]["require_core_remedies"] is True
    assert doc["manifest"]["source_repair_manifest"]["require_core_remedies"] is True
    assert doc["manifest"]["source_repair_manifest"]["by_added_core_remedy"] == {
        "compensation_damages": 1,
        "non_punishment": 1,
    }
    assert doc["manifest"]["source_repair_manifest"]["source_queue"]["require_core_remedies"] is True
    assert doc["manifest"]["source_repair_manifest"]["source_queue"]["by_core_missing"] == {
        "compensation_damages": 1,
        "non_punishment": 1,
    }
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["added_core_remedies"] == [
        "compensation_damages",
        "non_punishment",
    ]


def test_variant_rejects_core_remedy_metadata_without_core_enabled_source_manifest():
    repaired = [_row("a", "new a", repaired=True)]
    repair = repaired[0]["_meta"]["reasoning_repair"]
    repair["added_links"] = []
    repair["added_core_remedies"] = ["compensation_damages"]
    repair["original_target_core_missing"] = ["compensation_damages"]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1)

    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    assert doc["manifest"]["safe_to_train"] is False
    assert doc["manifest"]["repaired_row_metadata_counts"]["core_remedy_metadata_without_core_manifest"] == 1
    assert "repaired_row_core_remedy_metadata_without_core_manifest" in (
        doc["manifest"]["repaired_row_metadata_issues"]
    )


def test_manifest_paths_track_custom_output_path(tmp_path):
    repo_out_path = Path("reports/training/custom_reasoning_variant.jsonl")
    repo_doc = variant.build_variant(
        [_row("a", "old a")],
        [_row("a", "new a", repaired=True)],
        output_path=repo_out_path,
    )
    assert repo_doc["manifest"]["output_path"] == "reports/training/custom_reasoning_variant.jsonl"
    assert repo_doc["manifest"]["manifest_path"] == "reports/training/custom_reasoning_variant_manifest.json"

    out_path = tmp_path / "custom_reasoning_variant.jsonl"
    doc = variant.build_variant([_row("a", "old a")], [_row("a", "new a", repaired=True)], output_path=out_path)
    assert doc["manifest"]["output_path"] == "external"
    assert doc["manifest"]["manifest_path"] == "external"
    assert str(tmp_path) not in json.dumps(doc["manifest"])
    assert variant.manifest_path_for(out_path) == tmp_path / "custom_reasoning_variant_manifest.json"


def test_variant_reports_orphan_and_duplicate_repairs():
    base = [_row("a", "old a")]
    repaired = [_row("b", "new b1", repaired=True), _row("b", "new b2", repaired=True)]
    doc = variant.build_variant(base, repaired)
    assert doc["rows"] == base
    assert doc["manifest"]["orphan_repaired_rows"] == 1
    assert doc["manifest"]["duplicate_repaired_prompt_ids"] == 1
    assert doc["manifest"]["safe_to_train"] is False


def test_variant_allows_untouched_base_rows_without_prompt_ids():
    base = [_row("a", "old a"), _row("", "legacy untagged")]
    repaired = [_row("a", "new a", repaired=True)]

    doc = variant.build_variant(base, repaired)

    assert [_assistant(r) for r in doc["rows"]] == ["new a", "legacy untagged"]
    assert doc["manifest"]["base_missing_prompt_ids"] == 1
    assert doc["manifest"]["output_missing_prompt_ids"] == 1
    assert doc["manifest"]["repaired_missing_prompt_ids"] == 0
    assert doc["manifest"]["one_row_per_base_prompt"] is True
    assert doc["manifest"]["safe_to_train"] is True


def test_variant_accepts_generated_prompt_ids_with_spaces():
    pid = "corridor_Sri Lanka_Saudi Arabia_35_18825"
    base = [_row(pid, "old a")]
    repaired = [_row(pid, "new a", repaired=True)]
    repaired[0]["_meta"]["reasoning_repair"]["original_prompt_id"] = pid

    doc = variant.build_variant(base, repaired)

    assert [_assistant(r) for r in doc["rows"]] == ["new a"]
    assert doc["manifest"]["base_missing_prompt_ids"] == 0
    assert doc["manifest"]["repaired_missing_prompt_ids"] == 0
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["original_prompt_id"] == pid


def test_variant_rejects_malformed_repaired_metadata_without_crashing_or_leaking():
    base = [_row("a", "old a")]
    repaired = [_row("a", "new a", repaired=True)]
    repaired[0]["_meta"] = "worker@example.com case-123456789 raw metadata"

    doc = variant.build_variant(base, repaired)
    manifest_json = json.dumps(doc["manifest"])
    row_json = json.dumps(doc["rows"])

    assert doc["rows"] == base
    assert doc["manifest"]["safe_to_train"] is False
    assert doc["manifest"]["repaired_missing_prompt_ids"] == 1
    assert doc["manifest"]["repaired_row_metadata_counts"]["missing_reasoning_repair"] == 1
    assert "repaired_row_missing_reasoning_repair" in doc["manifest"]["repaired_row_metadata_issues"]
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json
    assert "worker@example.com" not in row_json
    assert "case-123456789" not in row_json


def test_variant_detects_duplicate_base_prompt_ids():
    base = [_row("a", "old a1"), _row("a", "old a2")]
    repaired = [_row("a", "new a", repaired=True)]
    doc = variant.build_variant(base, repaired)
    assert len(doc["rows"]) == 2
    assert doc["manifest"]["base_duplicate_prompt_id_rows"] == 1
    assert doc["manifest"]["output_duplicate_prompt_id_rows"] == 1
    assert doc["manifest"]["same_size_as_base"] is True
    assert doc["manifest"]["one_row_per_base_prompt"] is False
    assert doc["manifest"]["safe_to_train"] is False


def test_variant_detects_missing_prompt_ids():
    base = [_row("", "old missing")]
    repaired = [_row("", "new missing", repaired=True)]
    doc = variant.build_variant(base, repaired)
    assert doc["manifest"]["base_missing_prompt_ids"] == 1
    assert doc["manifest"]["repaired_missing_prompt_ids"] == 1
    assert doc["manifest"]["output_missing_prompt_ids"] == 1
    assert doc["manifest"]["one_row_per_base_prompt"] is False
    assert doc["manifest"]["safe_to_train"] is False


def test_manifest_does_not_copy_training_text():
    doc = variant.build_variant([_row("a", "old private answer")], [_row("a", "new private answer", repaired=True)])
    manifest_json = json.dumps(doc["manifest"])
    assert "private prompt" not in manifest_json
    assert "private answer" not in manifest_json
    assert doc["manifest"]["metadata_only"] is True
    assert doc["manifest"]["output_contains_training_text"] is True


def test_variant_rejects_unsafe_source_repair_manifest():
    repaired = [_row("a", "new a", repaired=True)]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1, privacy_ok=False)
    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    assert doc["manifest"]["safe_to_train"] is False
    assert "reasoning_repair_manifest_source_queue_privacy_scan_not_ok" in (
        doc["manifest"]["source_repair_manifest_issues"]
    )


def test_variant_rejects_repair_manifest_issues():
    repaired = [_row("a", "new a", repaired=True)]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1)
    manifest["repair_manifest_issues"] = ["reasoning_repair_no_repaired_rows"]
    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    assert doc["manifest"]["safe_to_train"] is False
    assert "reasoning_repair_manifest_issues_present" in doc["manifest"]["source_repair_manifest_issues"]


def test_variant_rejects_source_queue_manifest_issues():
    repaired = [_row("a", "new a", repaired=True)]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1)
    manifest["source_queue"]["queue_manifest_issues"] = ["reasoning_gap_queue_target_links_invalid"]
    manifest["source_queue"]["safe_for_repair"] = False
    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    assert doc["manifest"]["safe_to_train"] is False
    issues = doc["manifest"]["source_repair_manifest_issues"]
    assert "reasoning_repair_manifest_source_queue_not_safe_for_repair" in issues
    assert "reasoning_repair_manifest_source_queue_manifest_issues" in issues


def test_variant_rejects_source_queue_non_metadata_keys_without_copying_values():
    repaired = [_row("a", "new a", repaired=True)]
    manifest = _repair_manifest(Path("reasoning_repaired_sft.jsonl"), rows=1)
    manifest["source_queue"]["prompt"] = "must not reach the variant manifest"
    manifest["source_queue"]["queue"] = [{"assistant": "raw repaired source text"}]

    doc = variant.build_variant([_row("a", "old a")], repaired, repair_manifest=manifest)

    manifest_json = json.dumps(doc["manifest"])
    assert doc["manifest"]["safe_to_train"] is False
    assert "reasoning_repair_manifest_source_queue_non_metadata_keys" in (
        doc["manifest"]["source_repair_manifest_issues"]
    )
    assert "must not reach" not in manifest_json
    assert "raw repaired source text" not in manifest_json
    assert "prompt" not in doc["manifest"]["source_repair_manifest"]["source_queue"]
    assert "queue" not in doc["manifest"]["source_repair_manifest"]["source_queue"]


def test_variant_rejects_repaired_rows_without_repair_metadata():
    doc = variant.build_variant([_row("a", "old a")], [_row("a", "new a")])

    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["repaired_row_metadata_counts"]["missing_reasoning_repair"] == 1
    assert "repaired_row_missing_reasoning_repair" in manifest["repaired_row_metadata_issues"]


def test_variant_rejects_repaired_rows_with_mismatched_repair_prompt_id():
    repaired = [_row("a", "new a", repaired=True)]
    repaired[0]["_meta"]["reasoning_repair"]["original_prompt_id"] = "other"

    doc = variant.build_variant([_row("a", "old a")], repaired)

    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["repaired_row_metadata_counts"]["prompt_id_mismatch"] == 1
    assert "repaired_row_prompt_id_mismatch" in manifest["repaired_row_metadata_issues"]


def test_variant_rejects_unexpected_repair_metadata_without_copying_values():
    repaired = [_row("a", "new a", repaired=True)]
    repaired[0]["_meta"]["reasoning_repair"]["case_notes"] = "raw case details must not be trusted"

    doc = variant.build_variant([_row("a", "old a")], repaired)

    manifest = doc["manifest"]
    manifest_json = json.dumps(manifest)
    row_json = json.dumps(doc["rows"])
    assert manifest["safe_to_train"] is False
    assert manifest["repaired_row_metadata_counts"]["unexpected_reasoning_repair_keys"] == 1
    assert "repaired_row_reasoning_repair_unexpected_keys" in manifest["repaired_row_metadata_issues"]
    assert "raw case details" not in manifest_json
    assert "raw case details" not in row_json
    assert "case_notes" not in doc["rows"][0]["_meta"]["reasoning_repair"]


def test_variant_rejects_invalid_added_links_without_copying_values():
    repaired = [_row("a", "new a", repaired=True)]
    repaired[0]["_meta"]["reasoning_repair"]["added_links"] = ["statute", "raw worker clue"]

    doc = variant.build_variant([_row("a", "old a")], repaired)

    manifest = doc["manifest"]
    manifest_json = json.dumps(manifest)
    row_json = json.dumps(doc["rows"])
    assert manifest["safe_to_train"] is False
    assert manifest["repaired_row_metadata_counts"]["invalid_added_links"] == 1
    assert "repaired_row_invalid_added_links" in manifest["repaired_row_metadata_issues"]
    assert manifest["by_added_link"] == {"statute": 1}
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["added_links"] == ["statute"]
    assert "raw worker clue" not in manifest_json
    assert "raw worker clue" not in row_json


def test_variant_sanitizes_sensitive_repair_metadata_fields():
    repaired = [_row("a", "new a", repaired=True)]
    repair = repaired[0]["_meta"]["reasoning_repair"]
    repair["source"] = "worker@example.com"
    repair["original_prompt_id"] = "worker@example.com-case-123456789"
    repair["category"] = r"C:\Users\Taylor\case-123456789"
    repair["repaired_n_steps"] = "worker@example.com"
    repair["selected_convention"] = "case-123456789"

    doc = variant.build_variant([_row("a", "old a")], repaired)
    encoded = json.dumps(doc)
    repair_meta = doc["rows"][0]["_meta"]["reasoning_repair"]

    assert doc["manifest"]["safe_to_train"] is False
    assert doc["manifest"]["repaired_row_metadata_counts"]["wrong_repair_source"] == 1
    assert doc["manifest"]["repaired_row_metadata_counts"]["missing_original_prompt_id"] == 1
    assert repair_meta["source"] == "redacted"
    assert repair_meta["original_prompt_id"] == ""
    assert repair_meta["category"] == "unknown"
    assert repair_meta["repaired_n_steps"] is None
    assert repair_meta["selected_convention"] is None
    assert "worker@example.com" not in encoded
    assert "case-123456789" not in encoded
    assert "C:\\Users" not in encoded


def test_main_writes_manifest_with_safe_repair_manifest(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "sft_train.jsonl"
    repaired = sensitive_dir / "reasoning_repaired_sft.jsonl"
    out = sensitive_dir / "sft_train_reasoning_repaired.jsonl"
    base_rows = [_row("a", "old a"), _row("b", "old b")]
    repaired_rows = [_row("b", "new b", repaired=True)]
    _write_jsonl(base, base_rows)
    _write_jsonl(repaired, repaired_rows)
    variant.manifest_path_for(repaired).write_text(
        json.dumps(_repair_manifest(repaired, rows=1)) + "\n",
        encoding="utf-8",
    )

    assert variant.main(["--sft", str(base), "--repaired", str(repaired), "--out", str(out)]) == 0
    assert out.exists()
    manifest = json.loads(variant.manifest_path_for(out).read_text(encoding="utf-8"))
    manifest_json = json.dumps(manifest)
    assert manifest["safe_to_train"] is True
    assert manifest["output_path"] == "external"
    assert manifest["manifest_path"] == "external"
    assert manifest["source_repair_manifest"]["path"] == "external"
    assert manifest["source_repair_manifest"]["output_path"] == "external"
    assert manifest["source_repair_manifest"]["safe_to_train"] is True
    assert str(tmp_path) not in manifest_json
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json


def test_validate_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "sft_train.jsonl"
    repaired = sensitive_dir / "reasoning_repaired_sft.jsonl"
    out = sensitive_dir / "sft_train_reasoning_repaired.jsonl"
    _write_jsonl(base, [_row("a", "old a")])
    _write_jsonl(repaired, [_row("a", "new a", repaired=True)])
    variant.manifest_path_for(repaired).write_text(
        json.dumps(_repair_manifest(repaired, rows=1)) + "\n",
        encoding="utf-8",
    )

    rc = variant.main(["--sft", str(base), "--repaired", str(repaired), "--out", str(out),
                       "--validate"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"output_path": "external"' in printed
    assert '"manifest_path": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert not out.exists()


def test_missing_inputs_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    rc = variant.main(["--sft", str(sensitive_dir / "sft_train.jsonl")])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no base train split at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_missing_repaired_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "sft_train.jsonl"
    repaired = sensitive_dir / "reasoning_repaired_sft.jsonl"
    _write_jsonl(base, [_row("a", "old a")])

    rc = variant.main(["--sft", str(base), "--repaired", str(repaired)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no repaired rows at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_unsafe_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "sft_train.jsonl"
    repaired = sensitive_dir / "reasoning_repaired_sft.jsonl"
    out = sensitive_dir / "sft_train_reasoning_repaired.jsonl"
    _write_jsonl(base, [_row("a", "old a")])
    _write_jsonl(repaired, [_row("a", "new a", repaired=True)])
    variant.manifest_path_for(repaired).write_text(
        json.dumps(_repair_manifest(repaired, rows=1, privacy_ok=False)) + "\n",
        encoding="utf-8",
    )

    rc = variant.main(["--sft", str(base), "--repaired", str(repaired), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert '"output_path": "external"' in printed
    assert "unsafe variant shape" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert not out.exists()


def test_main_refuses_missing_repair_manifest(tmp_path):
    base = tmp_path / "sft_train.jsonl"
    repaired = tmp_path / "reasoning_repaired_sft.jsonl"
    out = tmp_path / "sft_train_reasoning_repaired.jsonl"
    _write_jsonl(base, [_row("a", "old a")])
    _write_jsonl(repaired, [_row("a", "new a", repaired=True)])

    assert variant.main(["--sft", str(base), "--repaired", str(repaired), "--out", str(out)]) == 1
    assert not out.exists()


def test_main_refuses_failed_repair_source_queue_privacy(tmp_path):
    base = tmp_path / "sft_train.jsonl"
    repaired = tmp_path / "reasoning_repaired_sft.jsonl"
    out = tmp_path / "sft_train_reasoning_repaired.jsonl"
    _write_jsonl(base, [_row("a", "old a")])
    _write_jsonl(repaired, [_row("a", "new a", repaired=True)])
    variant.manifest_path_for(repaired).write_text(
        json.dumps(_repair_manifest(repaired, rows=1, privacy_ok=False)) + "\n",
        encoding="utf-8",
    )

    assert variant.main(["--sft", str(base), "--repaired", str(repaired), "--out", str(out),
                         "--validate"]) == 1
    assert not out.exists()
