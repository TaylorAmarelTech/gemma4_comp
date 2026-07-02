"""Tests for scripts/build_reasoning_gap_queue.py -- privacy-safe weak-link repair queue."""
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


gap = _load("build_reasoning_gap_queue", _ROOT / "scripts" / "build_reasoning_gap_queue.py")

_FULL = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
         "It is prohibited under ILO Convention No. 29. "
         "You should keep copies of your documents and do not hand over your passport. "
         "Contact your embassy and file a complaint with the labour office.")
_NO_STATUTE = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
               "You should keep copies of your documents and do not hand over your passport. "
               "Contact your embassy and file a complaint with the labour office.")
_NO_ACTION = ("This situation shows passport confiscation, a recognised ILO forced labour indicator "
              "prohibited under ILO Convention No. 29. Contact your embassy and file a complaint with "
              "the labour office for worker protection and follow-up support.")
_NO_RESOURCES = ("This situation shows passport confiscation, a recognised ILO forced labour indicator "
                 "prohibited under ILO Convention No. 29. You should keep copies of your documents and "
                 "do not hand over your passport or sign anything you have not read.")
_CORE_REMEDY_INCOMPLETE = (
    "This situation shows passport confiscation and unpaid wages, recognised ILO forced labour indicators. "
    "It is prohibited under ILO Convention No. 29. You should keep copies of your documents, recover your "
    "unpaid wages, and file a complaint with the labour office. Contact your embassy and a lawyer."
)
_CORE_REMEDY_COMPLETE = (
    "This situation shows passport confiscation and unpaid wages, recognised ILO forced labour indicators. "
    "It is prohibited under ILO Convention No. 29. You should keep copies of your documents, recover your "
    "unpaid wages, seek compensation, and you should not be punished for things you were compelled to do. "
    "Contact your embassy and a lawyer."
)


def _row(pid: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": f"secret user prompt {pid}"},
            {"role": "assistant", "content": assistant},
        ],
        "_meta": {"prompt_id": pid},
    }


def test_queue_targets_missing_statute_and_action_only_by_default():
    doc = gap.build_queue([
        _row("full", _FULL),
        _row("no-statute", _NO_STATUTE),
        _row("no-action", _NO_ACTION),
        _row("no-resources", _NO_RESOURCES),
    ], pid2cat={"no-statute": "docs", "no-action": "contracts"})
    queue = doc["queue"]
    assert [e["prompt_id"] for e in queue] == ["no-statute", "no-action"]
    assert queue[0]["target_missing_links"] == ["statute"]
    assert queue[1]["target_missing_links"] == ["action"]
    assert doc["manifest"]["queued"] == 2
    assert doc["manifest"]["by_target_missing_link"] == {"action": 1, "statute": 1}
    assert doc["manifest"]["metadata_only"] is True
    assert doc["manifest"]["privacy_scan"]["ok"] is True
    assert doc["manifest"]["queue_manifest_issues"] == []
    assert doc["manifest"]["safe_for_repair"] is True
    assert doc["manifest"]["actionable_for_repair"] is True


def test_queue_can_target_resources_when_requested():
    doc = gap.build_queue([_row("no-resources", _NO_RESOURCES)], target_links=("resources",))
    assert doc["manifest"]["queued"] == 1
    assert doc["queue"][0]["target_missing_links"] == ["resources"]


def test_core_remedy_gaps_are_not_queued_by_default():
    doc = gap.build_queue([_row("core-incomplete", _CORE_REMEDY_INCOMPLETE)])

    assert doc["queue"] == []
    assert doc["manifest"]["require_core_remedies"] is False
    assert doc["manifest"]["core_triggered"] == 0
    assert doc["manifest"]["by_core_missing"] == {}


def test_queue_can_target_core_remedy_gaps_when_requested():
    doc = gap.build_queue(
        [
            _row("core-incomplete", _CORE_REMEDY_INCOMPLETE),
            _row("core-complete", _CORE_REMEDY_COMPLETE),
        ],
        require_core_remedies=True,
    )

    assert [e["prompt_id"] for e in doc["queue"]] == ["core-incomplete"]
    entry = doc["queue"][0]
    assert entry["missing_links"] == []
    assert entry["target_missing_links"] == []
    assert set(entry["target_core_missing"]) == {"compensation_damages", "non_punishment"}
    assert entry["core_remedies"]["complete"] is False
    assert "core remedies incomplete" in " ".join(entry["violations"])
    assert doc["manifest"]["require_core_remedies"] is True
    assert doc["manifest"]["core_triggered"] == 1
    assert doc["manifest"]["by_core_missing"] == {"compensation_damages": 1, "non_punishment": 1}
    assert doc["manifest"]["privacy_scan"]["ok"] is True


def test_queue_skips_rows_with_malformed_metadata_instead_of_empty_prompt_id():
    row = _row("no-statute", _NO_STATUTE)
    row["_meta"] = "worker@example.com case-123456789 must not leak"

    doc = gap.build_queue([row])
    manifest_json = json.dumps(doc["manifest"])

    assert doc["queue"] == []
    assert doc["manifest"]["skipped"] == {"missing_prompt_id": 1}
    assert doc["manifest"]["safe_for_repair"] is True
    assert doc["manifest"]["actionable_for_repair"] is False
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json


def test_queue_skips_sensitive_prompt_ids_and_sanitizes_category_labels():
    sensitive = _row("worker@example.com-case-123456789", _NO_STATUTE)
    safe = _row("no-statute", _NO_STATUTE)

    doc = gap.build_queue([
        sensitive,
        safe,
    ], pid2cat={
        "no-statute": r"C:\Users\Taylor\case-123456789",
        "worker@example.com-case-123456789": "private@example.com",
    })
    encoded = json.dumps(doc)

    assert [entry["prompt_id"] for entry in doc["queue"]] == ["no-statute"]
    assert doc["queue"][0]["category"] == "unknown"
    assert doc["manifest"]["by_category"] == {"unknown": 1}
    assert doc["manifest"]["skipped"] == {"missing_prompt_id": 1}
    assert doc["manifest"]["privacy_scan"]["ok"] is True
    assert "worker@example.com" not in encoded
    assert "case-123456789" not in encoded
    assert "C:\\Users" not in encoded


def test_queue_omits_raw_prompt_and_assistant_text():
    doc = gap.build_queue([_row("no-statute", _NO_STATUTE)])
    encoded = json.dumps(doc)
    assert "secret user prompt" not in encoded
    assert "This situation shows passport confiscation" not in encoded
    entry = doc["queue"][0]
    assert not {"messages", "prompt", "chosen", "rejected", "assistant", "text"} & set(entry)
    assert entry["repair_hint"]
    assert entry["citation"]["mapped_signals"] == ["document_retention"]
    assert doc["manifest"]["privacy_scan"]["ok"] is True


def test_privacy_scan_flags_forbidden_fields_and_pii_like_values():
    scan = gap._privacy_scan({
        "queue": [
            {
                "prompt_id": "template_20260129_115719_24937",
                "messages": [{"role": "user", "content": "raw"}],
                "repair_hint": "email worker@example.org or call +1 555 0100",
                "case_number": "1234567890",
            }
        ]
    })
    assert scan["ok"] is False
    assert "$.queue[0].messages" in scan["forbidden_field_paths"]
    assert "$.queue[0].repair_hint" in scan["email_like_paths"]
    assert "$.queue[0].repair_hint" in scan["phone_like_paths"]
    assert "$.queue[0].case_number" in scan["long_digit_paths"]
    assert "$.queue[0].prompt_id" not in scan["phone_like_paths"]


def test_privacy_scan_rejects_unexpected_queue_entry_fields_without_copying_values():
    scan = gap._privacy_scan({
        "queue": [
            {
                "prompt_id": "template_20260129_115719_24937",
                "category": "labor_trafficking",
                "case_notes": "raw worker narrative must not be queued",
            }
        ]
    })
    encoded = json.dumps(scan)
    assert scan["ok"] is False
    assert "$.queue[0].case_notes" in scan["unexpected_queue_field_paths"]
    assert "raw worker narrative" not in encoded


def test_privacy_scan_rejects_unexpected_nested_queue_fields_without_copying_values():
    scan = gap._privacy_scan({
        "queue": [
            {
                "prompt_id": "template_20260129_115719_24937",
                "category": "labor_trafficking",
                "citation": {
                    "mapped_signals": ["document_retention"],
                    "cited_conventions": [],
                    "expected_conventions": [29],
                    "matched": [],
                    "coherent": False,
                    "raw_excerpt": "private narrative must not be nested",
                },
            }
        ]
    })
    encoded = json.dumps(scan)
    assert scan["ok"] is False
    assert "$.queue[0].citation.raw_excerpt" in scan["unexpected_queue_field_paths"]
    assert "private narrative" not in encoded


def test_queue_manifest_flags_invalid_target_links():
    doc = gap.build_queue([_row("no-statute", _NO_STATUTE)], target_links=("statute", "bogus"))
    manifest = doc["manifest"]
    assert manifest["safe_for_repair"] is False
    assert manifest["actionable_for_repair"] is True
    assert "reasoning_gap_queue_target_links_invalid" in manifest["queue_manifest_issues"]


def test_queue_manifest_records_empty_but_safe_queue_as_not_actionable():
    doc = gap.build_queue([_row("full", _FULL)])
    manifest = doc["manifest"]
    assert manifest["queued"] == 0
    assert manifest["safe_for_repair"] is True
    assert manifest["actionable_for_repair"] is False
    assert manifest["queue_manifest_issues"] == []


def test_missing_input_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    rc = gap.main(["--sft", str(sensitive_dir / "reasoning_sft.jsonl")])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no reasoning set at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_success_console_redacts_sensitive_output_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    out = sensitive_dir / "reasoning_gap_queue.json"
    sft.write_text(json.dumps(_row("no-statute", _NO_STATUTE)) + "\n", encoding="utf-8")

    rc = gap.main(["--sft", str(sft), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 0
    assert "repair -> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert out.exists()
