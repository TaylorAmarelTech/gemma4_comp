"""Tests for scripts/build_dpo_mix_variant.py -- base+contract DPO comparison arm."""
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


mix = _load("build_dpo_mix_variant", _ROOT / "scripts" / "build_dpo_mix_variant.py")


def _pair(prompt="p", chosen="good", rejected="bad", meta=None):
    row = {"prompt": prompt, "chosen": chosen, "rejected": rejected}
    if meta:
        row["_meta"] = meta
    return row


def _contract_manifest(path=Path("contract_dpo.jsonl"), pairs=1, safe=True, link="statute"):
    return {
        "path": str(Path(path).with_name(f"{Path(path).stem}_manifest.json")),
        "output_path": str(path),
        "pairs": pairs,
        "safe_to_train": safe,
        "by_ablated_link": {link: pairs},
        "pair_integrity_issues": [],
        "contract_manifest_issues": [],
        "duplicate_output_pair_rows": 0,
    }


def _base_manifest(path=Path("organize_manifest.json"), train=1):
    return {
        "path": str(path),
        "seed": 17,
        "heldout_fraction": 0.2,
        "dedup": {"dpo": {"kept_pre_split": train}},
        "dpo": {"train": train, "heldout": 0},
    }


def test_build_mix_combines_base_and_contract_rows():
    base_path = Path("dpo_train.jsonl")
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=base_path,
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is True
    assert manifest["base_rows"] == 1
    assert manifest["contract_rows"] == 1
    assert manifest["pairs"] == 2
    assert manifest["by_ablated_link"] == {"statute": 1}
    assert manifest["source_manifest_issues"] == []
    assert manifest["source_manifests"]["base_dpo"]["dpo_train"] == 1
    assert manifest["source_manifests"]["contract_dpo"]["safe_to_train"] is True
    assert doc["rows"][0]["_meta"]["dpo_variant"]["component"] == "base"
    assert doc["rows"][1]["_meta"]["source"] == "contract_ablation"


def test_build_mix_fails_closed_on_duplicate_pair():
    duplicate = _pair("p", "same", "same bad")
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [duplicate],
        [_pair("p", "same", "same bad", {"source": "contract_ablation", "ablated_link": "action"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path, link="action"),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["skipped_duplicate_pairs"] == 1
    assert manifest["pairs"] == 1


def test_build_mix_rejects_non_string_pair_fields_without_copying_nested_payload():
    contract_path = Path("contract_dpo.jsonl")
    base_invalid = _pair(["worker@example.com"], "good", "bad")
    contract_invalid = _pair(
        "p3",
        {"case": "case-123456789"},
        "missing",
        {"source": "contract_ablation", "ablated_link": "statute"},
    )

    doc = mix.build_mix(
        [_pair("p1", "good", "bad"), base_invalid],
        [
            _pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"}),
            contract_invalid,
        ],
        base_manifest=_base_manifest(train=2),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path, pairs=2),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    rows_json = json.dumps(doc["rows"])

    assert manifest["safe_to_train"] is False
    assert manifest["base_input_rows"] == 2
    assert manifest["contract_input_rows"] == 2
    assert manifest["base_rows"] == 1
    assert manifest["contract_rows"] == 1
    assert manifest["skipped"]["base_invalid_pair"] == 1
    assert manifest["skipped"]["contract_invalid_pair"] == 1
    assert manifest["skipped_invalid_pairs"] == 2
    assert "worker@example.com" not in rows_json
    assert "case-123456789" not in rows_json


def test_build_mix_fails_closed_on_missing_contract_link():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair()],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["by_ablated_link"] == {}
    assert "contract_row_missing_ablated_link" in manifest["contract_row_metadata_issues"]


def test_build_mix_rejects_malformed_contract_metadata_without_crashing_or_leaking():
    contract_path = Path("contract_dpo.jsonl")
    contract_row = _pair("p2", "complete", "missing")
    contract_row["_meta"] = "worker@example.com case-123456789 raw metadata"

    doc = mix.build_mix(
        [_pair()],
        [contract_row],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    doc_json = json.dumps(doc)

    assert manifest["safe_to_train"] is False
    assert manifest["contract_row_metadata_counts"]["missing_meta"] == 1
    assert manifest["contract_row_metadata_counts"]["wrong_source"] == 1
    assert manifest["contract_row_metadata_counts"]["missing_ablated_link"] == 1
    assert "contract_row_missing_meta" in manifest["contract_row_metadata_issues"]
    assert "worker@example.com" not in doc_json
    assert "case-123456789" not in doc_json


def test_build_mix_fails_closed_on_invalid_contract_link_without_copying_value():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path, link="action")
    source_manifest["by_ablated_link"]["raw worker clue"] = 1
    doc = mix.build_mix(
        [_pair()],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "raw worker clue"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    manifest_json = json.dumps(manifest)
    row_json = json.dumps(doc["rows"])
    assert manifest["safe_to_train"] is False
    assert manifest["by_ablated_link"] == {}
    assert manifest["source_manifests"]["contract_dpo"]["by_ablated_link"] is None
    assert "contract_row_invalid_ablated_link" in manifest["contract_row_metadata_issues"]
    assert "contract_dpo_manifest_link_counts_invalid" in manifest["source_manifest_issues"]
    assert "raw worker clue" not in manifest_json
    assert "raw worker clue" not in row_json


def test_build_mix_fails_closed_on_contract_row_without_source_tag():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair()],
        [_pair("p2", "complete", "missing", {"ablated_link": "action"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path, link="action"),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["contract_row_metadata_counts"]["wrong_source"] == 1
    assert "contract_row_wrong_source" in manifest["contract_row_metadata_issues"]


def test_build_mix_fails_closed_on_contract_link_type_mismatch_with_source_manifest():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair()],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path, link="statute"),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "contract_row_link_counts_mismatch_source_manifest" in manifest["contract_row_metadata_issues"]
    assert "contract_dpo_manifest_link_count_by_type_mismatch" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_without_contract_manifest():
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert manifest["source_manifest_issues"] == ["contract_dpo_manifest_missing"]


def test_build_mix_fails_closed_on_stale_contract_manifest_count():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path, pairs=2),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "contract_dpo_manifest_pair_count_mismatch" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_on_contract_manifest_issues():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path)
    source_manifest["contract_manifest_issues"] = ["contract_dpo_no_pairs"]
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "contract_dpo_manifest_issues_present" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_on_contract_pair_integrity_issues():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path)
    source_manifest["pair_integrity_issues"] = ["contract_dpo_pair_rejected_unchanged"]
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "contract_dpo_manifest_pair_integrity_issues" in manifest["source_manifest_issues"]


def test_build_mix_sanitizes_raw_source_manifest_issue_values():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path)
    source_manifest["pair_integrity_issues"] = [
        "contract_dpo_pair_rejected_unchanged",
        "worker@example.com case-123456789 C:\\Users\\amare\\private.txt",
        {"detail": "case-123456789"},
    ]
    source_manifest["contract_manifest_issues"] = [
        "contract_dpo_no_pairs",
        "call +1 555 555 0100",
    ]

    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
        output_path=Path("dpo_mix.jsonl"),
    )
    manifest = doc["manifest"]
    contract_summary = manifest["source_manifests"]["contract_dpo"]
    manifest_json = json.dumps(manifest)

    assert manifest["safe_to_train"] is False
    assert contract_summary["pair_integrity_issues"] == [
        "contract_dpo_pair_rejected_unchanged",
        "manifest_issue_redacted",
        "manifest_issue_redacted",
    ]
    assert contract_summary["contract_manifest_issues"] == [
        "contract_dpo_no_pairs",
        "manifest_issue_redacted",
    ]
    assert "contract_dpo_manifest_pair_integrity_issues" in manifest["source_manifest_issues"]
    assert "contract_dpo_manifest_issues_present" in manifest["source_manifest_issues"]
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json
    assert "Users" not in manifest_json
    assert "private.txt" not in manifest_json
    assert "+1 555 555 0100" not in manifest_json


def test_build_mix_sanitizes_8_digit_case_like_manifest_issue_codes():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path)
    source_manifest["contract_manifest_issues"] = [
        "contract_dpo_no_pairs",
        "case_12345678",
    ]

    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
    )
    contract_summary = doc["manifest"]["source_manifests"]["contract_dpo"]
    manifest_json = json.dumps(doc["manifest"])

    assert contract_summary["contract_manifest_issues"] == [
        "contract_dpo_no_pairs",
        "manifest_issue_redacted",
    ]
    assert "case_12345678" not in manifest_json


def test_build_mix_fails_closed_on_invalid_manifest_link_counts():
    contract_path = Path("contract_dpo.jsonl")
    source_manifest = _contract_manifest(contract_path)
    source_manifest["by_ablated_link"] = {"statute": "not-a-number"}
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=source_manifest,
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "contract_dpo_manifest_link_counts_invalid" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_without_base_manifest():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "organize_manifest_missing" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_on_stale_base_manifest_count():
    contract_path = Path("contract_dpo.jsonl")
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=_base_manifest(train=2),
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "organize_manifest_dpo_train_count_mismatch" in manifest["source_manifest_issues"]


def test_build_mix_fails_closed_on_invalid_base_manifest_count():
    contract_path = Path("contract_dpo.jsonl")
    base_manifest = _base_manifest()
    base_manifest["dpo"]["train"] = "one"
    doc = mix.build_mix(
        [_pair("p1", "good", "bad")],
        [_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "statute"})],
        base_manifest=base_manifest,
        base_path=Path("dpo_train.jsonl"),
        contract_manifest=_contract_manifest(contract_path),
        contract_path=contract_path,
    )
    manifest = doc["manifest"]
    assert manifest["safe_to_train"] is False
    assert "organize_manifest_dpo_train_count_invalid" in manifest["source_manifest_issues"]


def test_main_writes_manifest_next_to_custom_output(tmp_path):
    base = tmp_path / "dpo_train.jsonl"
    base_manifest = tmp_path / "organize_manifest.json"
    contract = tmp_path / "contract_dpo.jsonl"
    out = tmp_path / "custom_mix.jsonl"
    base.write_text(json.dumps(_pair("p1", "good", "bad")) + "\n", encoding="utf-8")
    base_manifest.write_text(json.dumps(_base_manifest(base_manifest, train=1)) + "\n", encoding="utf-8")
    contract.write_text(
        json.dumps(_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"}))
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "contract_dpo_manifest.json").write_text(
        json.dumps(_contract_manifest(contract, pairs=1, link="action")) + "\n",
        encoding="utf-8",
    )

    assert mix.main(["--base-dpo", str(base), "--base-manifest", str(base_manifest),
                     "--contract-dpo", str(contract), "--out", str(out)]) == 0
    manifest_path = tmp_path / "custom_mix_manifest.json"
    assert out.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["output_path"] == str(out)
    assert manifest["manifest_path"] == str(manifest_path)
    assert manifest["source_manifest_issues"] == []
    assert manifest["source_manifests"]["base_dpo"]["dpo_train"] == 1


def test_validate_console_redacts_nested_source_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "dpo_train.jsonl"
    base_manifest = sensitive_dir / "organize_manifest.json"
    contract = sensitive_dir / "contract_dpo.jsonl"
    out = sensitive_dir / "custom_mix.jsonl"
    base.write_text(json.dumps(_pair("p1", "good", "bad")) + "\n", encoding="utf-8")
    base_manifest.write_text(json.dumps(_base_manifest(base_manifest, train=1)) + "\n", encoding="utf-8")
    contract.write_text(
        json.dumps(_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"}))
        + "\n",
        encoding="utf-8",
    )
    (sensitive_dir / "contract_dpo_manifest.json").write_text(
        json.dumps(_contract_manifest(contract, pairs=1, link="action")) + "\n",
        encoding="utf-8",
    )

    rc = mix.main(["--base-dpo", str(base), "--base-manifest", str(base_manifest),
                   "--contract-dpo", str(contract), "--out", str(out), "--validate"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"output_path": "external"' in printed
    assert '"manifest_path": "external"' in printed
    assert '"base_path": "external"' in printed
    assert '"path": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_missing_base_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    contract = sensitive_dir / "contract_dpo.jsonl"

    rc = mix.main(["--base-dpo", str(sensitive_dir / "dpo_train.jsonl"), "--contract-dpo", str(contract)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no base DPO rows at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_unsafe_console_redacts_nested_source_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    base = sensitive_dir / "dpo_train.jsonl"
    base_manifest = sensitive_dir / "organize_manifest.json"
    contract = sensitive_dir / "contract_dpo.jsonl"
    out = sensitive_dir / "custom_mix.jsonl"
    base.write_text(json.dumps(_pair("p1", "good", "bad")) + "\n", encoding="utf-8")
    base_manifest.write_text(json.dumps(_base_manifest(base_manifest, train=99)) + "\n", encoding="utf-8")
    contract.write_text(
        json.dumps(_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"}))
        + "\n",
        encoding="utf-8",
    )
    (sensitive_dir / "contract_dpo_manifest.json").write_text(
        json.dumps(_contract_manifest(contract, pairs=1, link="action")) + "\n",
        encoding="utf-8",
    )

    rc = mix.main(["--base-dpo", str(base), "--base-manifest", str(base_manifest),
                   "--contract-dpo", str(contract), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert '"output_path": "external"' in printed
    assert "unsafe mixed DPO shape" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_refuses_missing_contract_manifest(tmp_path):
    base = tmp_path / "dpo_train.jsonl"
    base_manifest = tmp_path / "organize_manifest.json"
    contract = tmp_path / "contract_dpo.jsonl"
    out = tmp_path / "custom_mix.jsonl"
    base.write_text(json.dumps(_pair("p1", "good", "bad")) + "\n", encoding="utf-8")
    base_manifest.write_text(json.dumps(_base_manifest(base_manifest, train=1)) + "\n", encoding="utf-8")
    contract.write_text(
        json.dumps(_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"}))
        + "\n",
        encoding="utf-8",
    )

    assert mix.main(["--base-dpo", str(base), "--base-manifest", str(base_manifest),
                     "--contract-dpo", str(contract), "--out", str(out)]) == 1
    assert not out.exists()


def test_main_refuses_missing_base_manifest(tmp_path):
    base = tmp_path / "dpo_train.jsonl"
    contract = tmp_path / "contract_dpo.jsonl"
    out = tmp_path / "custom_mix.jsonl"
    base.write_text(json.dumps(_pair("p1", "good", "bad")) + "\n", encoding="utf-8")
    contract.write_text(
        json.dumps(_pair("p2", "complete", "missing", {"source": "contract_ablation", "ablated_link": "action"}))
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "contract_dpo_manifest.json").write_text(
        json.dumps(_contract_manifest(contract, pairs=1, link="action")) + "\n",
        encoding="utf-8",
    )

    assert mix.main(["--base-dpo", str(base), "--base-manifest", str(tmp_path / "missing.json"),
                     "--contract-dpo", str(contract), "--out", str(out)]) == 1
    assert not out.exists()
