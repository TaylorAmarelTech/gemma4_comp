"""Tests for scripts/train_lift_distill.py -- Phase 3 Unsloth runner (CPU-safe paths only).

The GPU train() path needs unsloth/trl/torch + CUDA and is not exercised here; these cover the
data loading, validation, message normalisation, chat-template rendering, and plan construction.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tr = _load("train_lift_distill", _ROOT / "scripts" / "train_lift_distill.py")

_CONTRACT_CHOSEN = (
    "This situation shows passport confiscation, a recognised ILO forced labour indicator. "
    "It is prohibited under ILO Convention No. 29 (Forced Labour). "
    "You should keep copies of your documents and do not hand over your passport to the recruiter. "
    "Contact your embassy and file a complaint with the labour office, which helps migrant workers."
)
_CONTRACT_REJECTED = {
    "statute": (
        "This situation shows passport confiscation, a recognised ILO forced labour indicator. "
        "You should keep copies of your documents and do not hand over your passport to the recruiter. "
        "Contact your embassy and file a complaint with the labour office, which helps migrant workers."
    ),
    "action": (
        "This situation shows passport confiscation, a recognised ILO forced labour indicator. "
        "It is prohibited under ILO Convention No. 29 (Forced Labour). "
        "Contact your embassy and file a complaint with the labour office, which helps migrant workers."
    ),
}


def _safe_source_repair_manifest(rows: int = 1, *, require_core_remedies: bool = False) -> dict:
    return {
        "safe_to_train": True,
        "repaired_rows": rows,
        "require_core_remedies": require_core_remedies,
        "by_added_core_remedy": (
            {"compensation_damages": rows, "non_punishment": rows} if require_core_remedies else {}
        ),
        "source_queue": {
            "metadata_only": True,
            "privacy_scan_ok": True,
            "safe_for_repair": True,
            "actionable_for_repair": True,
            "queue_manifest_issues": [],
            "queued": rows,
            "target_links": ["statute", "action"],
            "require_core_remedies": require_core_remedies,
            "by_core_missing": (
                {"compensation_damages": rows, "non_punishment": rows} if require_core_remedies else {}
            ),
        },
    }


def _safe_mixed_dpo_sources(*, base_rows: int = 1, contract_rows: int = 1, link: str = "action") -> dict:
    return {
        "base_dpo": {"dpo_train": base_rows},
        "contract_dpo": {
            "pairs": contract_rows,
            "safe_to_train": True,
            "by_ablated_link": {link: contract_rows},
            "pair_integrity_issues": [],
            "contract_manifest_issues": [],
            "duplicate_output_pair_rows": 0,
        },
    }


def _mixed_base_pair(prompt: str = "p1") -> dict:
    return {
        "prompt": prompt,
        "chosen": "better",
        "rejected": "worse",
        "_meta": {"dpo_variant": {"name": "base_plus_contract", "component": "base"}},
    }


def _mixed_contract_pair(prompt: str = "p2", link: str = "action") -> dict:
    return {
        "prompt": prompt,
        "chosen": _CONTRACT_CHOSEN,
        "rejected": _CONTRACT_REJECTED[link],
        "_meta": {
            "source": "contract_ablation",
            "ablated_link": link,
            "dpo_variant": {"name": "base_plus_contract", "component": "contract"},
        },
    }


def _contract_pair(prompt: str = "p", link: str = "statute") -> dict:
    return {
        "prompt": prompt,
        "chosen": _CONTRACT_CHOSEN,
        "rejected": _CONTRACT_REJECTED[link],
        "_meta": {"source": "contract_ablation", "ablated_link": link},
    }


def _repaired_sft_row(pid: str = "p1", *, repair_meta: dict | None = None, variant_meta: dict | None = None) -> dict:
    meta = {
        "prompt_id": pid,
        "reasoning_repair": repair_meta if repair_meta is not None else {
            "source": "reasoning_gap_queue",
            "original_prompt_id": pid,
            "added_links": ["statute"],
        },
        "sft_variant": variant_meta if variant_meta is not None else {
            "name": "reasoning_repaired",
            "base_prompt_id": pid,
            "source": "build_reasoning_sft_variant.py",
            "replacement": True,
        },
    }
    return {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}],
            "_meta": meta}


def test_defaults_use_train_splits_not_unsplit_sources():
    assert tr.SFT_DEFAULT.name == "sft_train.jsonl"
    assert tr.DPO_DEFAULT.name == "dpo_train.jsonl"
    assert tr.DEFAULT_BASE == "google/gemma-4-E4B-it"
    assert len(tr.DEFAULT_BASE_REVISION) == 40


def test_normalize_messages_maps_assistant_and_wraps_content():
    out = tr.normalize_messages([
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "I cannot help with that"},
    ])
    assert out[0]["role"] == "user" and out[1]["role"] == "model"   # assistant -> model
    assert out[0]["content"] == [{"type": "text", "text": "hi"}]    # str -> [{type,text}]
    assert out[1]["content"][0]["text"].startswith("I cannot")


def test_normalize_messages_skips_malformed_message_items():
    out = tr.normalize_messages([
        {"role": "user", "content": "hi"},
        "worker@example.com case-123456789 raw message",
        {"role": "user", "content": {"text": "worker@example.com nested prompt"}},
        {"role": "assistant", "content": ["case-123456789 nested reply"]},
        {"role": "assistant", "content": "safe reply"},
    ])

    assert [msg["role"] for msg in out] == ["user", "model"]
    assert "worker@example.com" not in json.dumps(out)
    assert "case-123456789" not in json.dumps(out)


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "sft_train.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}),
            "[1, 2, 3]",
            '"worker@example.com case-123456789 raw row"',
            "{bad json",
        ]) + "\n",
        encoding="utf-8",
    )

    rows = tr.load_jsonl(path)

    assert len(rows) == 1
    assert rows[0]["messages"][0]["content"] == "q"


def test_validate_counts_valid_and_flags_empty():
    sft = [
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},  # ok
        {"messages": [{"role": "user", "content": "q only"}]},                                     # no assistant
    ]
    dpo = [
        {"prompt": "p", "chosen": "good", "rejected": "bad"},   # ok
        {"prompt": "p", "chosen": "", "rejected": "bad"},        # empty chosen
    ]
    v = tr.validate(sft, dpo)
    assert v["sft_valid"] == 1 and v["dpo_valid"] == 1
    assert v["ok"] is True   # at least some valid rows, no blocking issue


def test_validate_tolerates_non_object_rows_without_copying_values():
    sft = [
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},
        "worker@example.com case-123456789 raw sft row",
    ]
    dpo = [
        {"prompt": "p", "chosen": "good", "rejected": "bad"},
        ["worker@example.com case-123456789 raw dpo row"],
    ]

    v = tr.validate(sft, dpo)
    report_json = json.dumps(v)

    assert v["ok"] is True
    assert v["sft_rows"] == 1
    assert v["dpo_rows"] == 1
    assert v["sft_malformed_rows"] == 1
    assert v["dpo_malformed_rows"] == 1
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json


def test_validate_rejects_non_string_training_text_without_copying_values():
    sft = [{
        "messages": [
            {"role": "user", "content": {"text": "worker@example.com raw prompt"}},
            {"role": "assistant", "content": "a"},
        ]
    }]
    dpo = [{
        "prompt": "p",
        "chosen": {"text": "worker@example.com raw chosen"},
        "rejected": "bad",
    }]

    v = tr.validate(sft, dpo)
    report_json = json.dumps(v)

    assert v["ok"] is False
    assert v["sft_valid"] == 0
    assert v["dpo_valid"] == 0
    assert "no valid SFT rows" in "; ".join(v["issues"])
    assert "no valid DPO rows" in "; ".join(v["issues"])
    assert "worker@example.com" not in report_json


def test_validate_accepts_safe_sft_variant_manifest():
    sft_path = Path("reports/training/sft_train_reasoning_repaired.jsonl")
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "output_path": str(sft_path),
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest, sft_path=sft_path)
    assert v["ok"] is True
    assert v["sft_manifest"]["safe_to_train"] is True
    assert v["sft_variant_rows"] == 1
    assert v["sft_variant_names"] == ["reasoning_repaired"]


def test_validate_accepts_sft_variant_with_untouched_rows_without_prompt_ids():
    sft_path = Path("reports/training/sft_train_reasoning_repaired.jsonl")
    sft = [
        _repaired_sft_row(),
        {
            "messages": [{"role": "user", "content": "q2"}, {"role": "assistant", "content": "a2"}],
            "_meta": {"prompt_id": "worker@example.com-case-123456789"},
        },
    ]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 2,
        "output_prompt_ids": 1,
        "output_path": str(sft_path),
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest, sft_path=sft_path)

    assert v["ok"] is True
    assert v["sft_rows"] == 2
    assert v["sft_variant_rows"] == 1
    assert "worker@example.com" not in json.dumps(v)


def test_validate_accepts_core_remedy_only_sft_variant_when_source_manifest_is_core_enabled():
    repair_meta = {
        "source": "reasoning_gap_queue",
        "original_prompt_id": "p1",
        "added_links": [],
        "added_core_remedies": ["compensation_damages", "non_punishment"],
        "original_target_core_missing": ["compensation_damages", "non_punishment"],
    }
    sft_path = Path("reports/training/sft_train_reasoning_repaired.jsonl")
    sft = [_repaired_sft_row(repair_meta=repair_meta)]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "output_path": str(sft_path),
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(require_core_remedies=True),
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest, sft_path=sft_path)

    assert v["ok"] is True
    repair = v["sft_manifest"]["source_repair_manifest"]
    assert repair["require_core_remedies"] is True
    assert repair["by_added_core_remedy"] == {"compensation_damages": 1, "non_punishment": 1}
    assert repair["source_queue"]["require_core_remedies"] is True
    assert repair["source_queue"]["by_core_missing"] == {
        "compensation_damages": 1,
        "non_punishment": 1,
    }


def test_validate_rejects_core_remedy_sft_variant_without_core_enabled_source_manifest():
    repair_meta = {
        "source": "reasoning_gap_queue",
        "original_prompt_id": "p1",
        "added_links": [],
        "added_core_remedies": ["compensation_damages"],
        "original_target_core_missing": ["compensation_damages"],
    }
    sft = [_repaired_sft_row(repair_meta=repair_meta)]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)

    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "without a core-enabled source manifest" in issues
    assert "at least one added repair item" not in issues


def test_validate_rejects_unsafe_sft_variant_manifest():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": False,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": False,
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "safe_to_train=true" in "; ".join(v["issues"])


def test_validate_rejects_incomplete_sft_variant_manifest():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "output_rows": 1,
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "safe_to_train=true" in issues
    assert "one_row_per_base_prompt=true" in issues
    assert "output_prompt_ids" in issues


def test_validate_rejects_sft_variant_manifest_path_mismatch():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "output_path": "reports/training/other.jsonl",
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest, sft_path=Path("reports/training/selected.jsonl"))
    assert v["ok"] is False
    assert "output_path" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_manifest_name_mismatch():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "other_variant",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "variant does not match" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_manifest_source_repair_issues():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": ["reasoning_repair_manifest_source_queue_privacy_scan_not_ok"],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "source_repair_manifest_issues" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_manifest_source_repair_manifest_issues():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["repair_manifest_issues"] = ["reasoning_repair_no_repaired_rows"]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_path": "reports/training/sft_train_reasoning_repaired.jsonl",
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "repair manifest must have no repair_manifest_issues" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_manifest_source_repair_privacy_flag():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["source_queue"]["privacy_scan_ok"] = False
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "privacy_scan_ok=true" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_manifest_source_queue_issues():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["source_queue"]["safe_for_repair"] = False
    source_repair["source_queue"]["queue_manifest_issues"] = ["reasoning_gap_queue_target_links_invalid"]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "safe_for_repair=true" in issues
    assert "no queue_manifest_issues" in issues


def test_validate_rejects_sft_variant_manifest_source_repair_count_mismatch():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 2,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(rows=1),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "repaired_rows must match repaired_input_rows" in "; ".join(v["issues"])


def test_validate_sanitizes_sft_source_repair_summary_without_copying_values():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["prompt"] = "raw prompt must not appear"
    source_repair["source_queue"]["queue"] = [{"assistant": "raw queue row must not appear"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)

    report_json = json.dumps(v)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "metadata summary keys only" in issues
    assert "raw prompt must not appear" not in report_json
    assert "raw queue row must not appear" not in report_json
    assert "prompt" not in v["sft_manifest"]["source_repair_manifest"]
    assert "queue" not in v["sft_manifest"]["source_repair_manifest"]["source_queue"]


def test_validate_rejects_sft_source_queue_invalid_target_links_without_copying_values():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["source_queue"]["target_links"] = ["statute", "raw worker clue"]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)

    assert v["ok"] is False
    assert "target_links must be statute/action" in "; ".join(v["issues"])
    assert "raw worker clue" not in json.dumps(v)


def test_validate_sanitizes_sft_manifest_issue_lists_without_copying_values():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    source_repair = _safe_source_repair_manifest()
    source_repair["repair_manifest_issues"] = [
        "reasoning_repair_no_repaired_rows",
        "worker@example.com case-123456789",
    ]
    source_repair["source_queue"]["queue_manifest_issues"] = [
        "reasoning_gap_queue_target_links_invalid",
        {"detail": "case-123456789"},
        "call +1 555 555 0100",
    ]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": source_repair,
        "source_repair_manifest_issues": [
            "reasoning_repair_manifest_source_queue_privacy_scan_not_ok",
            r"C:\Users\amare\private.txt",
        ],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)
    report_json = json.dumps(v)
    summary = v["sft_manifest"]["source_repair_manifest"]

    assert v["ok"] is False
    assert summary["repair_manifest_issues"] == [
        "reasoning_repair_no_repaired_rows",
        "manifest_issue_redacted",
    ]
    assert summary["source_queue"]["queue_manifest_issues"] == [
        "reasoning_gap_queue_target_links_invalid",
        "manifest_issue_redacted",
        "manifest_issue_redacted",
    ]
    assert v["sft_manifest"]["source_repair_manifest_issues"] == [
        "reasoning_repair_manifest_source_queue_privacy_scan_not_ok",
        "manifest_issue_redacted",
    ]
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "private.txt" not in report_json
    assert "+1 555 555 0100" not in report_json


def test_validate_rejects_sft_variant_row_missing_repair_metadata():
    sft = [{
        "messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}],
        "_meta": {
            "prompt_id": "p1",
            "sft_variant": {
                "name": "reasoning_repaired",
                "base_prompt_id": "p1",
                "source": "build_reasoning_sft_variant.py",
                "replacement": True,
            },
        },
    }]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "reasoning_repair metadata" in "; ".join(v["issues"])


def test_validate_rejects_sft_variant_row_unexpected_repair_metadata():
    repair_meta = {
        "source": "reasoning_gap_queue",
        "original_prompt_id": "p1",
        "added_links": ["statute"],
        "case_notes": "raw case detail must not appear",
    }
    sft = [_repaired_sft_row(repair_meta=repair_meta)]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)

    assert v["ok"] is False
    assert "expected reasoning_repair metadata" in "; ".join(v["issues"])
    assert "raw case detail" not in json.dumps(v)


def test_validate_rejects_sft_variant_row_invalid_added_links_without_copying_values():
    repair_meta = {
        "source": "reasoning_gap_queue",
        "original_prompt_id": "p1",
        "added_links": ["statute", "raw worker clue"],
    }
    sft = [_repaired_sft_row(repair_meta=repair_meta)]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 1,
        "output_prompt_ids": 1,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }

    v = tr.validate(sft, dpo, sft_manifest=manifest)

    assert v["ok"] is False
    assert "source_queue target_links" in "; ".join(v["issues"])
    assert "raw worker clue" not in json.dumps(v)


def test_validate_rejects_sft_variant_row_count_mismatch():
    sft = [_repaired_sft_row("p1"), _repaired_sft_row("p2")]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    manifest = {
        "path": "reports/training/sft_train_reasoning_repaired_manifest.json",
        "variant": "reasoning_repaired",
        "safe_to_train": True,
        "output_rows": 2,
        "output_prompt_ids": 2,
        "one_row_per_base_prompt": True,
        "repaired_input_rows": 1,
        "replaced_rows": 1,
        "source_repair_manifest": _safe_source_repair_manifest(),
        "source_repair_manifest_issues": [],
    }
    v = tr.validate(sft, dpo, sft_manifest=manifest)
    assert v["ok"] is False
    assert "row count must match manifest replaced_rows" in "; ".join(v["issues"])


def test_validate_variant_rows_require_manifest():
    sft = [_repaired_sft_row()]
    dpo = [{"prompt": "p", "chosen": "good", "rejected": "bad"}]
    v = tr.validate(sft, dpo)
    assert v["ok"] is False
    assert v["sft_variant_rows"] == 1
    assert "adjacent manifest" in "; ".join(v["issues"])


def test_validate_accepts_contract_dpo_manifest():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
        "min_steps": 4,
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is True
    assert v["contract_dpo_rows"] == 1
    assert v["dpo_manifest"]["pairs"] == 1


def test_validate_contract_dpo_rows_require_manifest():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo = [_contract_pair(link="action")]
    v = tr.validate(sft, dpo)
    assert v["ok"] is False
    assert "DPO rows require an adjacent manifest" in "; ".join(v["issues"])


def test_validate_rejects_contract_dpo_manifest_count_mismatch():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": "reports/training/contract_dpo.jsonl",
        "pairs": 2,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 2},
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest)
    assert v["ok"] is False
    assert "pairs does not match" in "; ".join(v["issues"])


def test_validate_rejects_contract_dpo_manifest_duplicate_pairs():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": "reports/training/contract_dpo.jsonl",
        "pairs": 1,
        "by_ablated_link": {"statute": 1},
        "duplicate_output_pair_rows": 1,
        "safe_to_train": False,
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "not safe_to_train" in issues
    assert "duplicate_output_pair_rows=0" in issues


def test_validate_rejects_contract_dpo_manifest_issues():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
        "contract_manifest_issues": ["contract_dpo_no_pairs"],
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "contract_manifest_issues" in issues


def test_validate_rejects_contract_dpo_pair_integrity_manifest_issues():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
        "pair_integrity_issues": ["contract_dpo_pair_rejected_unchanged"],
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "pair_integrity_issues" in issues


def test_validate_rejects_contract_dpo_pair_text_that_does_not_ablate():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="statute")]
    dpo[0]["rejected"] = dpo[0]["chosen"]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
        "pair_integrity_issues": [],
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "rejected text must differ from chosen" in issues
    assert "rejected text must remove the ablated_link" in issues


def test_validate_rejects_empty_selected_contract_dpo():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 0,
        "safe_to_train": True,
        "by_ablated_link": {},
        "contract_manifest_issues": [],
    }
    v = tr.validate(sft, [], dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "pairs>0" in issues
    assert "at least one pair" in issues


def test_validate_rejects_contract_dpo_manifest_path_mismatch():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": "reports/training/other_contract_dpo.jsonl",
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=Path("reports/training/contract_dpo.jsonl"))
    assert v["ok"] is False
    assert "output_path" in "; ".join(v["issues"])


def test_validate_accepts_display_safe_external_contract_dpo_manifest_path(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    dpo_path = sensitive_dir / "contract_dpo.jsonl"
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo = [_contract_pair(link="statute")]
    manifest = {
        "path": "external",
        "output_path": "external",
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
    }

    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    report_json = json.dumps(v)

    assert v["ok"] is True
    assert not any("output_path" in issue for issue in v["issues"])
    assert str(tmp_path) not in report_json
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json


def test_validate_rejects_contract_dpo_rows_missing_source_marker():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="statute")]
    dpo[0]["_meta"].pop("source")
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "rows must all be contract_ablation rows" in issues
    assert "source=contract_ablation" in issues


def test_validate_rejects_contract_dpo_row_link_count_mismatch():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="action")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"statute": 1},
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is False
    assert "ablated_link counts must match" in "; ".join(v["issues"])


def test_validate_rejects_contract_dpo_manifest_invalid_links_without_copying_values():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/contract_dpo.jsonl")
    dpo = [_contract_pair(link="action")]
    manifest = {
        "path": "reports/training/contract_dpo_manifest.json",
        "output_path": str(dpo_path),
        "pairs": 1,
        "safe_to_train": True,
        "by_ablated_link": {"action": 1, "raw worker clue": 1},
    }

    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)

    report_json = json.dumps(v)
    assert v["ok"] is False
    assert "by_ablated_link must use statute/action numeric counts" in "; ".join(v["issues"])
    assert v["dpo_manifest"]["by_ablated_link"] == {"action": 1}
    assert "raw worker clue" not in report_json


def test_validate_accepts_mixed_dpo_manifest():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is True
    assert v["contract_dpo_rows"] == 1
    assert v["dpo_manifest"]["variant"] == "base_plus_contract"
    assert v["dpo_manifest"]["safe_to_train"] is True


def test_validate_rejects_mixed_dpo_manifest_source_issues():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": ["contract_dpo_manifest_pair_count_mismatch"],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is False
    assert "source_manifest_issues" in "; ".join(v["issues"])


def test_validate_sanitizes_mixed_dpo_source_manifests_without_copying_values():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["base_dpo"]["prompt"] = "raw base prompt must not appear"
    source_manifests["contract_dpo"]["queue"] = [{"chosen": "raw contract row must not appear"}]
    source_manifests["extra"] = {"prompt": "raw top-level source must not appear"}
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": source_manifests,
    }

    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)

    report_json = json.dumps(v)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "source_manifests must contain base_dpo and contract_dpo only" in issues
    assert "base source manifest must contain metadata summary keys only" in issues
    assert "contract source manifest must contain metadata summary keys only" in issues
    assert "raw base prompt" not in report_json
    assert "raw contract row" not in report_json
    assert "raw top-level source" not in report_json
    assert "prompt" not in v["dpo_manifest"]["source_manifests"]["base_dpo"]
    assert "queue" not in v["dpo_manifest"]["source_manifests"]["contract_dpo"]
    assert "extra" not in v["dpo_manifest"]["source_manifests"]


def test_validate_sanitizes_mixed_dpo_manifest_issue_lists_without_copying_values():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["contract_dpo"]["contract_manifest_issues"] = [
        "contract_dpo_no_pairs",
        "worker@example.com case-123456789",
    ]
    source_manifests["contract_dpo"]["pair_integrity_issues"] = [
        "contract_dpo_pair_rejected_unchanged",
        {"detail": "case-123456789"},
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "pair_integrity_issues": ["contract_dpo_pair_rejected_unchanged", "call +1 555 555 0100"],
        "contract_manifest_issues": ["contract_dpo_no_pairs", r"C:\Users\amare\private.txt"],
        "source_manifest_issues": [
            "contract_dpo_manifest_pair_count_mismatch",
            "worker@example.com case-123456789",
        ],
        "source_manifests": source_manifests,
    }

    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    report_json = json.dumps(v)
    contract_summary = v["dpo_manifest"]["source_manifests"]["contract_dpo"]

    assert v["ok"] is False
    assert v["dpo_manifest"]["pair_integrity_issues"] == [
        "contract_dpo_pair_rejected_unchanged",
        "manifest_issue_redacted",
    ]
    assert v["dpo_manifest"]["contract_manifest_issues"] == [
        "contract_dpo_no_pairs",
        "manifest_issue_redacted",
    ]
    assert v["dpo_manifest"]["source_manifest_issues"] == [
        "contract_dpo_manifest_pair_count_mismatch",
        "manifest_issue_redacted",
    ]
    assert contract_summary["contract_manifest_issues"] == [
        "contract_dpo_no_pairs",
        "manifest_issue_redacted",
    ]
    assert contract_summary["pair_integrity_issues"] == [
        "contract_dpo_pair_rejected_unchanged",
        "manifest_issue_redacted",
    ]
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert "private.txt" not in report_json
    assert "+1 555 555 0100" not in report_json


def test_validate_rejects_mixed_dpo_invalid_manifest_links_without_copying_values():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["contract_dpo"]["by_ablated_link"] = {"action": 1, "raw worker clue": 1}
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1, "raw worker clue": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": source_manifests,
    }

    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)

    report_json = json.dumps(v)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "mixed DPO manifest by_ablated_link must use statute/action numeric counts" in issues
    assert "contract source link counts must use statute/action numeric counts" in issues
    assert v["dpo_manifest"]["by_ablated_link"] == {"action": 1}
    assert v["dpo_manifest"]["source_manifests"]["contract_dpo"]["by_ablated_link"] == {"action": 1}
    assert "raw worker clue" not in report_json


def test_validate_rejects_mixed_dpo_manifest_unsafe_contract_source_summary():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["contract_dpo"]["safe_to_train"] = False
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": source_manifests,
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is False
    assert "contract source manifest must have safe_to_train=true" in "; ".join(v["issues"])


def test_validate_rejects_mixed_dpo_manifest_contract_source_issues():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["contract_dpo"]["contract_manifest_issues"] = ["contract_dpo_no_pairs"]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": source_manifests,
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is False
    assert "contract source manifest must have no contract_manifest_issues" in "; ".join(v["issues"])


def test_validate_rejects_mixed_dpo_manifest_contract_pair_integrity_source_issues():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    source_manifests = _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action")
    source_manifests["contract_dpo"]["pair_integrity_issues"] = ["contract_dpo_pair_rejected_unchanged"]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": source_manifests,
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    assert v["ok"] is False
    assert "contract source manifest must have no pair_integrity_issues" in "; ".join(v["issues"])


def test_validate_rejects_mixed_dpo_rows_missing_variant_tags():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        {"prompt": "p1", "chosen": "better", "rejected": "worse"},
        {
            "prompt": "p2",
            "chosen": _CONTRACT_CHOSEN,
            "rejected": _CONTRACT_REJECTED["action"],
            "_meta": {"source": "contract_ablation", "ablated_link": "action"},
        },
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "dpo_variant metadata" in issues
    assert "contract_ablation rows must be tagged as contract component" in issues


def test_validate_rejects_mixed_dpo_rows_component_count_mismatch():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        {
            "prompt": "p2",
            "chosen": _CONTRACT_CHOSEN,
            "rejected": _CONTRACT_REJECTED["action"],
            "_meta": {
                "source": "contract_ablation",
                "ablated_link": "action",
                "dpo_variant": {"name": "base_plus_contract", "component": "base"},
            },
        },
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "base components must match manifest base_rows" in issues
    assert "contract components must match manifest contract_rows" in issues
    assert "contract_ablation rows must be tagged as contract component" in issues


def test_validate_rejects_mixed_dpo_row_link_count_mismatch():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "action"),
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"statute": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="statute"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "contract row ablated_link counts must match" in issues


def test_validate_rejects_mixed_dpo_contract_component_missing_link():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        {
            "prompt": "p2",
            "chosen": _CONTRACT_CHOSEN,
            "rejected": _CONTRACT_REJECTED["action"],
            "_meta": {
                "source": "contract_ablation",
                "dpo_variant": {"name": "base_plus_contract", "component": "contract"},
            },
        },
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "contract component rows must include ablated_link" in issues


def test_validate_rejects_mixed_dpo_contract_component_that_does_not_ablate():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    bad_contract = _mixed_contract_pair("p2", "action")
    bad_contract["rejected"] = bad_contract["chosen"]
    dpo = [
        _mixed_base_pair("p1"),
        bad_contract,
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": True,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"action": 1},
        "duplicate_output_pair_rows": 0,
        "source_manifest_issues": [],
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="action"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "rejected text must differ from chosen" in issues
    assert "rejected text must remove the ablated_link" in issues


def test_validate_rejects_unsafe_mixed_dpo_manifest():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [
        _mixed_base_pair("p1"),
        _mixed_contract_pair("p2", "statute"),
    ]
    manifest = {
        "path": "reports/training/dpo_train_plus_contract_manifest.json",
        "variant": "base_plus_contract",
        "safe_to_train": False,
        "output_path": str(dpo_path),
        "output_rows": 2,
        "pairs": 2,
        "base_rows": 1,
        "contract_rows": 1,
        "by_ablated_link": {"statute": 1},
        "duplicate_output_pair_rows": 1,
        "source_manifests": _safe_mixed_dpo_sources(base_rows=1, contract_rows=1, link="statute"),
    }
    v = tr.validate(sft, dpo, dpo_manifest=manifest, dpo_path=dpo_path)
    issues = "; ".join(v["issues"])
    assert v["ok"] is False
    assert "safe_to_train=true" in issues
    assert "duplicate_output_pair_rows=0" in issues


def test_validate_mixed_dpo_rows_require_manifest():
    sft = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    dpo_path = Path("reports/training/dpo_train_plus_contract.jsonl")
    dpo = [_contract_pair(link="action")]
    v = tr.validate(sft, dpo, dpo_path=dpo_path)
    assert v["ok"] is False
    issues = "; ".join(v["issues"])
    assert "contract-derived DPO rows require an adjacent manifest" in issues
    assert "mixed DPO variant requires an adjacent manifest" in issues


def test_load_sft_manifest_requires_reasoning_repaired_manifest(tmp_path):
    path = tmp_path / tr.REPAIRED_SFT_NAME
    path.write_text("", encoding="utf-8")
    manifest = tr.load_sft_manifest(path)
    assert manifest["missing"] is True
    assert manifest["path"].endswith("sft_train_reasoning_repaired_manifest.json")


def test_load_dpo_manifest_requires_contract_manifest(tmp_path):
    path = tmp_path / tr.CONTRACT_DPO_NAME
    path.write_text("", encoding="utf-8")
    manifest = tr.load_dpo_manifest(path)
    assert manifest["missing"] is True
    assert manifest["path"].endswith("contract_dpo_manifest.json")


def test_load_dpo_manifest_requires_mixed_dpo_manifest(tmp_path):
    path = tmp_path / tr.DPO_MIX_NAME
    path.write_text("", encoding="utf-8")
    manifest = tr.load_dpo_manifest(path)
    assert manifest["missing"] is True
    assert manifest["path"].endswith("dpo_train_plus_contract_manifest.json")


def test_validate_fails_when_no_data():
    v = tr.validate([], [])
    assert v["ok"] is False and v["issues"]


def test_validate_cli_redacts_paths_in_console_output(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / tr.REPAIRED_SFT_NAME
    dpo = sensitive_dir / "dpo_train.jsonl"
    out_dir = sensitive_dir / "adapter"
    base_model = sensitive_dir / "local-base-model"
    sft.write_text(json.dumps(_repaired_sft_row()) + "\n", encoding="utf-8")
    dpo.write_text(json.dumps({"prompt": "p", "chosen": "grounded", "rejected": "weak"}) + "\n",
                   encoding="utf-8")

    rc = tr.main([
        "--validate",
        "--base-model", str(base_model),
        "--sft", str(sft),
        "--dpo", str(dpo),
        "--out", str(out_dir),
    ])
    out = capsys.readouterr().out

    assert rc == 1
    assert '"base_model": "redacted"' in out
    assert "SFT variant manifest missing" in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out
    assert str(tmp_path) not in out


def test_display_validation_report_redacts_unknown_sensitive_issue():
    display = tr._display_validation_report({
        "issues": [r"worker@example.com says call +1 555 0100 about C:\Users\case-123456789"],
    })

    assert display == {"issues": ["validation issue redacted"]}


def test_train_console_output_uses_display_safe_values(tmp_path, monkeypatch, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_out = sensitive_dir / "adapter"
    (sensitive_dir / "local-base-model").mkdir(parents=True)
    calls = {"gguf": ""}

    class FakeModel:
        def save_pretrained(self, out_dir):
            calls["save"] = out_dir

        def save_pretrained_gguf(self, out_dir, tokenizer, quantization_method):
            calls["gguf"] = out_dir
            raise RuntimeError(f"failed to write {out_dir}")

    class FakeTokenizer:
        def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False):
            return "<bos>rendered"

        def save_pretrained(self, out_dir):
            calls["tokenizer_save"] = out_dir

    class FakeFastModel:
        @staticmethod
        def from_pretrained(**kwargs):
            calls["model_name"] = kwargs["model_name"]
            return FakeModel(), FakeTokenizer()

        @staticmethod
        def get_peft_model(model, **kwargs):
            return model

    class FakeDataset:
        @staticmethod
        def from_list(rows):
            return rows

    class FakeSFTConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeSFTTrainer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def train(self):
            calls["trained"] = True

    class FakeCuda:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def is_bf16_supported():
            return False

    unsloth_mod = types.ModuleType("unsloth")
    unsloth_mod.__path__ = []
    unsloth_mod.FastModel = FakeFastModel
    chat_mod = types.ModuleType("unsloth.chat_templates")
    chat_mod.get_chat_template = lambda tokenizer, chat_template: tokenizer
    chat_mod.train_on_responses_only = (
        lambda trainer, instruction_part, response_part: trainer
    )
    datasets_mod = types.ModuleType("datasets")
    datasets_mod.Dataset = FakeDataset
    trl_mod = types.ModuleType("trl")
    trl_mod.SFTConfig = FakeSFTConfig
    trl_mod.SFTTrainer = FakeSFTTrainer
    torch_mod = types.ModuleType("torch")
    torch_mod.cuda = FakeCuda()
    for name, module in {
        "unsloth": unsloth_mod,
        "unsloth.chat_templates": chat_mod,
        "datasets": datasets_mod,
        "trl": trl_mod,
        "torch": torch_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    class VerifiedBundle:
        sft_sha256 = "b" * 64
        preference_sha256 = "c" * 64
        sft_rows = (
            {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},
        )
        preference_rows = ()

        @staticmethod
        def summary():
            return {
                "ok": True,
                "manifest_sha256": "a" * 64,
                "counts": {"sft": 1, "preference": 0},
            }

    monkeypatch.setattr(tr, "validate_training_bundle", lambda *args, **kwargs: VerifiedBundle())

    plan = {
        "base_model": str(sensitive_dir / "local-base-model"),
        "chat_template": tr.CHAT_TEMPLATE,
        "max_seq_length": 128,
        "lora": {"r": 2, "alpha": 2, "dropout": 0.0},
        "sft": {
            "file": str(sensitive_dir / "sft.jsonl"),
            "per_device_batch": 1,
            "grad_accum": 1,
            "epochs": 1,
            "max_steps": 1,
            "lr": 1e-4,
        },
        "dpo": {"enabled": False, "file": str(sensitive_dir / "dpo.jsonl")},
        "training_manifest": str(sensitive_dir / "manifest.json"),
        "output_dir": str(sensitive_out),
        "gguf": True,
    }

    returned = tr.train(plan)
    out = capsys.readouterr().out

    assert returned == str(sensitive_out)
    assert calls["model_name"] == str(sensitive_dir / "local-base-model")
    assert calls["gguf"] == f"{sensitive_out}-gguf"
    assert "[train] loading redacted (4-bit) ..." in out
    assert "[train] SFT adapter saved to external" in out
    assert "[train] GGUF export skipped: RuntimeError: details redacted" in out
    assert str(tmp_path) not in out
    assert "worker@example.com" not in out
    assert "case-123456789" not in out


def test_remote_training_requires_an_immutable_base_revision() -> None:
    with pytest.raises(SystemExit, match="remote base models require --base-revision"):
        tr.train(
            {
                "base_model": "example/custom-remote-model",
                "base_model_revision": "",
                "dpo": {"enabled": False},
            }
        )


def test_gpu_training_requires_canonical_bundle_manifest(tmp_path) -> None:
    local_model = tmp_path / "local-model"
    local_model.mkdir()

    with pytest.raises(SystemExit, match="canonical --training-manifest is required"):
        tr.train({"base_model": str(local_model), "base_model_revision": ""})


def test_pin_adapter_revision_updates_standard_peft_fields(tmp_path) -> None:
    config = tmp_path / "adapter_config.json"
    config.write_text(json.dumps({"peft_type": "LORA"}), encoding="utf-8")

    tr._pin_adapter_revision(
        tmp_path,
        base_model=tr.DEFAULT_BASE,
        revision=tr.DEFAULT_BASE_REVISION,
    )

    payload = json.loads(config.read_text(encoding="utf-8"))
    assert payload["base_model_name_or_path"] == tr.DEFAULT_BASE
    assert payload["revision"] == tr.DEFAULT_BASE_REVISION


def test_render_sft_applies_template_and_strips_bos():
    rows = [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
    seen = {}

    def fake_apply(msgs):
        seen["roles"] = [m["role"] for m in msgs]
        return "<bos>RENDERED"

    out = tr.render_sft(rows, fake_apply)
    assert out == [{"text": "RENDERED"}]               # <bos> stripped
    assert seen["roles"] == ["user", "model"]          # normalized before templating


def test_render_sft_skips_rows_with_incomplete_or_non_string_messages():
    rows = [
        {"messages": [{"role": "user", "content": {"text": "worker@example.com"}}, {"role": "assistant", "content": "a"}]},
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": ["case-123456789"]}]},
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},
    ]
    rendered_inputs = []

    def fake_apply(msgs):
        rendered_inputs.append(msgs)
        return "<bos>SAFE"

    out = tr.render_sft(rows, fake_apply)
    out_json = json.dumps({"out": out, "inputs": rendered_inputs})

    assert out == [{"text": "SAFE"}]
    assert len(rendered_inputs) == 1
    assert [msg["role"] for msg in rendered_inputs[0]] == ["user", "model"]
    assert "worker@example.com" not in out_json
    assert "case-123456789" not in out_json


def test_render_dpo_skips_non_string_pair_fields_without_leaking_values():
    rows = [
        {"prompt": "p", "chosen": "grounded", "rejected": "weak"},
        {"prompt": ["worker@example.com"], "chosen": "good", "rejected": "bad"},
        {"prompt": "p2", "chosen": {"case": "case-123456789"}, "rejected": "bad"},
        {"prompt": "p3", "chosen": "good", "rejected": ""},
    ]

    out = tr.render_dpo(rows, lambda prompt: f"rendered:{prompt}")
    out_json = json.dumps(out)

    assert out == [{"prompt": "rendered:p", "chosen": "grounded", "rejected": "weak"}]
    assert "worker@example.com" not in out_json
    assert "case-123456789" not in out_json


def test_missing_dpo_trainer_is_fatal_unless_dpo_was_explicitly_disabled(monkeypatch):
    trl_mod = types.ModuleType("trl")
    monkeypatch.setitem(sys.modules, "trl", trl_mod)

    assert tr._load_dpo_components(enabled=False) == (None, None)
    with pytest.raises(SystemExit, match=r"DPO was requested.*--skip-dpo explicitly"):
        tr._load_dpo_components(enabled=True)


def test_build_plan_test_run_overrides_steps():
    ns = argparse.Namespace(
        base_model="google/gemma-4-E4B-it", sft=Path("s"), dpo=Path("d"), out=Path("o"),
        max_seq=2048, epochs=2, max_steps=-1, batch=2, grad_accum=4, lr=2e-4,
        lora_r=16, lora_alpha=16, skip_dpo=False, dpo_beta=0.1, dpo_max_steps=200,
        dpo_lr=5e-6, rpo_alpha=1.0, gguf=False, test_run=True,
    )
    plan = tr.build_plan(ns)
    assert plan["sft"]["max_steps"] == 20 and plan["sft"]["epochs"] == 1   # test-run overrides
    assert plan["dpo"]["enabled"] is True and plan["dpo"]["max_steps"] == 10
    assert plan["base_model"] == "google/gemma-4-E4B-it"
    assert plan["base_model_revision"] == tr.DEFAULT_BASE_REVISION
    # DPO truncation lengths are set (the silent length-bias fix) + the tunable knobs
    assert plan["dpo"]["lr"] == 5e-6 and plan["dpo"]["rpo_alpha"] == 1.0
    assert plan["dpo"]["max_length"] == 2048 and plan["dpo"]["max_prompt_length"] == 1024
