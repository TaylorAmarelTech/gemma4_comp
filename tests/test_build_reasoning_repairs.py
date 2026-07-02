"""Tests for scripts/build_reasoning_repairs.py -- proposed repaired reasoning SFT rows."""
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


repairs = _load("build_reasoning_repairs", _ROOT / "scripts" / "build_reasoning_repairs.py")
rc = _load("reasoning_contract", _ROOT / "scripts" / "reasoning_contract.py")

_NO_STATUTE = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
               "You should keep copies of your documents and do not hand over your passport. "
               "Contact your embassy and file a complaint with the labour office.")
_NO_ACTION = ("This situation shows passport confiscation, a recognised ILO forced labour indicator "
              "prohibited under ILO Convention No. 29. Contact your embassy and file a complaint with "
              "the labour office for worker protection and follow-up support.")
_CORE_REMEDY_INCOMPLETE = (
    "This situation shows passport confiscation and unpaid wages, recognised ILO forced labour indicators. "
    "It is prohibited under ILO Convention No. 29. You should keep copies of your documents, recover your "
    "unpaid wages, and file a complaint with the labour office. Contact your embassy and a lawyer."
)


def _row(pid: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": f"secret prompt {pid}"},
            {"role": "assistant", "content": assistant},
        ],
        "_meta": {"prompt_id": pid},
    }


def _queue(pid: str, missing: list[str], expected: list[int] | None = None) -> dict:
    expected_conventions = [29] if expected is None else expected
    return {
        "prompt_id": pid,
        "category": "labor_trafficking",
        "missing_links": missing,
        "target_missing_links": missing,
        "citation": {
            "mapped_signals": ["document_retention"],
            "cited_conventions": [],
            "expected_conventions": expected_conventions,
            "matched": [],
            "coherent": True,
        },
    }


def _queue_doc(
    rows: list[dict],
    *,
    privacy_ok: bool = True,
    metadata_only: bool = True,
    require_core_remedies: bool = False,
) -> dict:
    queue_manifest_issues = [] if privacy_ok and metadata_only else ["synthetic_queue_manifest_issue"]
    return {
        "queue": rows,
        "manifest": {
            "queued": len(rows),
            "target_links": ["statute", "action"],
            "require_core_remedies": require_core_remedies,
            "by_core_missing": {},
            "metadata_only": metadata_only,
            "privacy_scan": {"ok": privacy_ok},
            "queue_manifest_issues": queue_manifest_issues,
            "safe_for_repair": not queue_manifest_issues,
            "actionable_for_repair": bool(rows),
        },
    }


def _core_queue(pid: str, missing: list[str] | None = None) -> dict:
    missing = ["compensation_damages", "non_punishment"] if missing is None else missing
    row = _queue(pid, [], [29])
    row["target_missing_links"] = []
    row["target_core_missing"] = missing
    row["core_remedies"] = {
        "triggers": ["exploitation_or_forced_labour", "wage_harm"],
        "required": ["compensation_damages", "non_punishment", "unpaid_wage_recovery"],
        "missing": missing,
        "complete": False,
    }
    row["violations"] = [
        "core remedies incomplete: name the mandatory remedy guarantees "
        f"({', '.join(missing)})"
    ]
    return row


def test_repair_missing_statute_yields_strict_contract_row():
    doc = repairs.build_repairs([_row("p1", _NO_STATUTE)], [_queue("p1", ["statute"], [29])])
    assert doc["manifest"]["repaired_rows"] == 1
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["repair_manifest_issues"] == []
    out = doc["rows"][0]
    text = out["messages"][-1]["content"]
    assert "ILO Convention No. 29" in text
    assert rc.verify_reasoning(text).satisfied is True
    assert out["_meta"]["reasoning_repair"]["selected_convention"] == 29
    assert out["_meta"]["reasoning_repair"]["added_links"] == ["statute"]
    assert "added_core_remedies" not in out["_meta"]["reasoning_repair"]
    assert out["_meta"]["reasoning_repair"]["category"] == "labor_trafficking"


def test_repair_tolerates_malformed_message_items_when_replacing_assistant():
    row = _row("p1", _NO_STATUTE)
    row["messages"].insert(1, "worker@example.com case-123456789 raw item")

    doc = repairs.build_repairs([row], [_queue("p1", ["statute"], [29])])
    doc_json = json.dumps(doc)

    assert doc["manifest"]["repaired_rows"] == 1
    assert doc["manifest"]["safe_to_train"] is True
    assert rc.verify_reasoning(doc["rows"][0]["messages"][-1]["content"]).satisfied is True
    assert "worker@example.com" not in doc_json
    assert "case-123456789" not in doc_json


def test_repair_missing_action_yields_strict_contract_row():
    doc = repairs.build_repairs([_row("p2", _NO_ACTION)], [_queue("p2", ["action"], [29])])
    assert doc["manifest"]["repaired_rows"] == 1
    assert doc["manifest"]["repair_manifest_issues"] == []
    text = doc["rows"][0]["messages"][-1]["content"]
    assert "Protective action:" in text
    assert rc.verify_reasoning(text).satisfied is True
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["added_links"] == ["action"]
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["category"] == "labor_trafficking"


def test_repair_core_remedies_yields_core_contract_row():
    doc = repairs.build_repairs(
        [_row("p-core", _CORE_REMEDY_INCOMPLETE)],
        [_core_queue("p-core")],
        require_core_remedies=True,
        queue_manifest=_queue_doc([_core_queue("p-core")], require_core_remedies=True)["manifest"],
    )

    assert doc["manifest"]["repaired_rows"] == 1
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["by_added_link"] == {}
    assert doc["manifest"]["by_added_core_remedy"] == {
        "compensation_damages": 1,
        "non_punishment": 1,
    }
    out = doc["rows"][0]
    text = out["messages"][-1]["content"]
    assert "Core remedy:" in text
    assert rc.verify_reasoning(text, require_core_remedies=True).satisfied is True
    meta = out["_meta"]["reasoning_repair"]
    assert meta["added_links"] == []
    assert set(meta["added_core_remedies"]) == {"compensation_damages", "non_punishment"}
    assert set(meta["original_target_core_missing"]) == {"compensation_damages", "non_punishment"}


def test_missing_statute_without_expected_convention_is_skipped():
    doc = repairs.build_repairs([_row("p3", _NO_STATUTE)], [_queue("p3", ["statute"], [])])
    assert doc["rows"] == []
    assert doc["manifest"]["skipped"]["no_statute_repair"] == 1
    assert doc["manifest"]["safe_to_train"] is False
    assert "reasoning_repair_no_repaired_rows" in doc["manifest"]["repair_manifest_issues"]


def test_queue_shape_allows_opaque_numeric_prompt_ids_but_rejects_contact_like_ids():
    safe = _queue("template_20260129_115719_24937", ["statute"], [29])
    spaced = _queue("corridor_Sri Lanka_Saudi Arabia_35_18825", ["statute"], [29])
    unsafe = _queue("worker@example.com-case-123456789", ["statute"], [29])

    assert repairs._queue_shape_issues([safe]) == []
    assert repairs._queue_shape_issues([spaced]) == []
    assert "queue[0].prompt_id" in repairs._queue_shape_issues([unsafe])


def test_repair_ignores_sensitive_queue_prompt_ids_without_leaking():
    queue = _queue("worker@example.com-case-123456789", ["statute"], [29])
    queue["category"] = r"C:\Users\Taylor\case-123456789"

    doc = repairs.build_repairs([_row("p1", _NO_STATUTE)], [queue])
    encoded = json.dumps(doc)

    assert doc["rows"] == []
    assert doc["manifest"]["safe_to_train"] is False
    assert "reasoning_repair_no_repaired_rows" in doc["manifest"]["repair_manifest_issues"]
    assert "worker@example.com" not in encoded
    assert "case-123456789" not in encoded
    assert "C:\\Users" not in encoded


def test_repair_sanitizes_sensitive_category_metadata():
    queue = _queue("p1", ["statute"], [29])
    queue["category"] = "worker@example.com-case-123456789"

    doc = repairs.build_repairs([_row("p1", _NO_STATUTE)], [queue])
    encoded = json.dumps(doc)

    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["by_category"] == {"unknown": 1}
    assert doc["rows"][0]["_meta"]["reasoning_repair"]["category"] == "unknown"
    assert "worker@example.com" not in encoded
    assert "case-123456789" not in encoded


def test_manifest_does_not_copy_raw_training_text():
    doc = repairs.build_repairs([_row("p1", _NO_STATUTE)], [_queue("p1", ["statute"], [29])])
    manifest_json = json.dumps(doc["manifest"])
    assert "secret prompt" not in manifest_json
    assert "passport confiscation" not in manifest_json
    assert doc["manifest"]["output_contains_repaired_training_text"] is True
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["repair_manifest_issues"] == []


def test_manifest_paths_track_custom_output_path(tmp_path):
    repo_out_path = Path("reports/training/custom_reasoning_repairs.jsonl")
    repo_doc = repairs.build_repairs(
        [_row("p1", _NO_STATUTE)],
        [_queue("p1", ["statute"], [29])],
        output_path=repo_out_path,
    )
    assert repo_doc["manifest"]["output_path"] == "reports/training/custom_reasoning_repairs.jsonl"
    assert repo_doc["manifest"]["manifest_path"] == "reports/training/custom_reasoning_repairs_manifest.json"

    out_path = tmp_path / "custom_reasoning_repairs.jsonl"
    doc = repairs.build_repairs([_row("p1", _NO_STATUTE)], [_queue("p1", ["statute"], [29])], output_path=out_path)
    assert doc["manifest"]["output_path"] == "external"
    assert doc["manifest"]["manifest_path"] == "external"
    assert str(tmp_path) not in json.dumps(doc["manifest"])
    assert repairs.manifest_path_for(out_path) == tmp_path / "custom_reasoning_repairs_manifest.json"


def test_main_writes_manifest_next_to_custom_output(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    queue = sensitive_dir / "reasoning_gap_queue.json"
    out = sensitive_dir / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_queue("p1", ["statute"], [29])])), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out)]) == 0
    manifest_path = sensitive_dir / "custom_reasoning_repairs_manifest.json"
    assert out.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_json = json.dumps(manifest)
    assert manifest["output_path"] == "external"
    assert manifest["manifest_path"] == "external"
    assert manifest["safe_to_train"] is True
    assert manifest["repair_manifest_issues"] == []
    assert manifest["source_queue"]["privacy_scan_ok"] is True
    assert manifest["source_queue"]["safe_for_repair"] is True
    assert manifest["source_queue"]["queue_manifest_issues"] == []
    assert str(tmp_path) not in manifest_json
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json


def test_validate_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    queue = sensitive_dir / "reasoning_gap_queue.json"
    out = sensitive_dir / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_queue("p1", ["statute"], [29])])), encoding="utf-8")

    rc = repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"output_path": "external"' in printed
    assert '"manifest_path": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_core_repair_cli_requires_core_enabled_source_queue(tmp_path, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p-core", _CORE_REMEDY_INCOMPLETE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_core_queue("p-core")], require_core_remedies=False)), encoding="utf-8")

    assert repairs.main([
        "--sft", str(sft),
        "--queue", str(queue),
        "--out", str(out),
        "--validate",
        "--require-core-remedies",
    ]) == 1

    printed = capsys.readouterr().out
    assert "reasoning_gap_queue_manifest_core_remedies_not_enabled" in printed
    assert not out.exists()


def test_core_repair_cli_validates_core_enabled_source_queue(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    core_entry = _core_queue("p-core")
    queue_doc = _queue_doc([core_entry], require_core_remedies=True)
    queue_doc["manifest"]["by_core_missing"] = {"compensation_damages": 1, "non_punishment": 1}
    sft.write_text(json.dumps(_row("p-core", _CORE_REMEDY_INCOMPLETE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main([
        "--sft", str(sft),
        "--queue", str(queue),
        "--out", str(out),
        "--validate",
        "--require-core-remedies",
    ]) == 0


def test_missing_inputs_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    rc = repairs.main(["--sft", str(sensitive_dir / "reasoning_sft.jsonl")])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no reasoning set at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_missing_queue_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    queue = sensitive_dir / "reasoning_gap_queue.json"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")

    rc = repairs.main(["--sft", str(sft), "--queue", str(queue)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no gap queue at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_unsafe_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    queue = sensitive_dir / "reasoning_gap_queue.json"
    out = sensitive_dir / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_queue("p1", ["statute"], [29])], privacy_ok=False)),
                     encoding="utf-8")

    rc = repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert '"output_path": "external"' in printed
    assert "source gap queue is unsafe" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_refuses_when_all_queue_entries_are_skipped(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p3", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_queue("p3", ["statute"], [])])), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1
    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out)]) == 1
    assert not out.exists()


def test_main_refuses_queue_without_metadata_manifest(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps({"queue": [_queue("p1", ["statute"], [29])]}), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out)]) == 1
    assert not out.exists()


def test_main_refuses_queue_with_failed_privacy_scan(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue.write_text(json.dumps(_queue_doc([_queue("p1", ["statute"], [29])], privacy_ok=False)),
                     encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1
    assert not out.exists()


def test_main_refuses_tampered_queue_even_if_manifest_privacy_scan_claims_ok(tmp_path, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue_doc = _queue_doc([_queue("p1", ["statute"], [29])])
    queue_doc["queue"][0]["case_notes"] = "raw worker message must not be trusted"
    queue_doc["queue"][0]["citation"]["raw_excerpt"] = "nested worker detail must not be trusted"
    assert queue_doc["manifest"]["privacy_scan"]["ok"] is True
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1

    printed = capsys.readouterr().out
    assert "reasoning_gap_queue_actual_privacy_scan_not_ok" in printed
    assert "raw worker message" not in printed
    assert "nested worker detail" not in printed
    assert not out.exists()


def test_main_refuses_malformed_queue_convention_metadata_without_crashing(tmp_path, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue_doc = _queue_doc([_queue("p1", ["statute"], [29])])
    queue_doc["queue"][0]["citation"]["expected_conventions"] = ["not-a-convention"]
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1

    printed = capsys.readouterr().out
    assert "reasoning_gap_queue_entry_shape_invalid" in printed
    assert "not-a-convention" not in printed
    assert not out.exists()


def test_main_refuses_queue_with_non_object_entries_without_silent_drop(tmp_path, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue_doc = _queue_doc([_queue("p1", ["statute"], [29])])
    queue_doc["queue"].append("raw queue row must not be trusted")
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1

    printed = capsys.readouterr().out
    assert "reasoning_gap_queue_non_object_entries" in printed
    assert "raw queue row" not in printed
    assert not out.exists()


def test_main_refuses_queue_root_that_is_not_a_list(tmp_path, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue_doc = _queue_doc([])
    queue_doc["queue"] = {"prompt_id": "p1", "raw": "raw queue shape must not be trusted"}
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1

    printed = capsys.readouterr().out
    assert "reasoning_gap_queue_not_list" in printed
    assert "raw queue shape" not in printed
    assert not out.exists()


def test_main_refuses_queue_with_manifest_issues(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    queue = tmp_path / "reasoning_gap_queue.json"
    out = tmp_path / "custom_reasoning_repairs.jsonl"
    sft.write_text(json.dumps(_row("p1", _NO_STATUTE)) + "\n", encoding="utf-8")
    queue_doc = _queue_doc([_queue("p1", ["statute"], [29])])
    queue_doc["manifest"]["queue_manifest_issues"] = ["reasoning_gap_queue_target_links_invalid"]
    queue_doc["manifest"]["safe_for_repair"] = False
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")

    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out), "--validate"]) == 1
    assert repairs.main(["--sft", str(sft), "--queue", str(queue), "--out", str(out)]) == 1
    assert not out.exists()
