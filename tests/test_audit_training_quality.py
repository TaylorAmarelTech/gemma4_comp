"""Tests for scripts/audit_training_quality.py -- pre-train data-quality guards.

Each test pins one failure mode the audit is meant to catch: cross-split leakage (overfitting),
DPO length-bias (false pattern), single-corridor typology (jurisdiction shortcut), and fragile-fact
assertion (volatile specifics that should live in tools/RAG, not the weights)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


atq = _load("audit_training_quality", _ROOT / "scripts" / "audit_training_quality.py")


@pytest.mark.skipif(not atq._HAVE_SIMHASH, reason="research_tools.dedup SimHash unavailable")
def test_near_dup_leakage_flags_heldout_copy():
    # Arrange: a heldout prompt that duplicates a train prompt (the leak the split must not contain).
    # SimHash@dist<=3 is deliberately conservative -- it catches near-identical re-copies, not genuine
    # paraphrases -- so the leak case is an exact copy and the clean case is a clearly distinct prompt.
    train = ["A recruiter in Nepal is charging a worker a large fee for a job in Qatar, is this legal?"]
    leak_ho = [train[0]]
    fresh_ho = ["My employer in Taiwan took my passport on arrival; what are my rights as a fisher?"]
    # Act
    leaked = atq.near_dup_leakage(train, leak_ho)
    clean = atq.near_dup_leakage(train, fresh_ho)
    # Assert
    assert leaked["available"] and leaked["leaked"] == 1 and leaked["ok"] is False
    assert clean["leaked"] == 0 and clean["ok"] is True


def test_length_bias_flags_long_chosen():
    long_chosen = [{"chosen": "x" * 1000, "rejected": "y" * 100} for _ in range(5)]   # 10x ratio
    balanced = [{"chosen": "x" * 320, "rejected": "y" * 300} for _ in range(5)]
    assert atq.length_bias(long_chosen)["ok"] is False
    assert atq.length_bias(long_chosen)["chosen_over_rejected_ratio"] == 10.0
    assert atq.length_bias(balanced)["ok"] is True
    assert atq.length_bias([])["n"] == 0


def test_corridor_diversity_flags_dense_single_corridor():
    # debt_bondage spans TWO corridors (ok); passport_confiscation is DENSE but in ONE corridor (risk);
    # rare_style is single-corridor but too sparse to flag. min_rows=2 keeps the fixture small.
    pid_meta = {
        "P1": {"category": "debt_bondage", "corridor": "Nepal->Qatar"},
        "P2": {"category": "debt_bondage", "corridor": "Bangladesh->Malaysia"},
        "P3": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P4": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P5": {"category": "rare_style", "corridor": "India->Kuwait"},   # only 1 row -> sparse, not flagged
    }
    rows = [{"_meta": {"prompt_id": p}} for p in pid_meta]
    out = atq.corridor_diversity(rows, pid_meta, min_rows=2)
    assert out["distinct_corridors"] == 3
    assert out["distinct_specific_corridors"] == 3
    assert "passport_confiscation" in out["dense_single_corridor_typologies"]   # 2 rows, 1 corridor -> risk
    assert "debt_bondage" not in out["dense_single_corridor_typologies"]        # 2 corridors -> ok
    assert "rare_style" not in out["dense_single_corridor_typologies"]          # 1 row -> too sparse
    assert out["multi_corridor_typologies"] == 1 and out["sparse_typologies"] == 1
    assert out["corridor_expansion_queue_count"] == 1
    assert out["corridor_expansion_queue_metadata_only"] is True
    assert out["corridor_expansion_queue_privacy_scan"]["ok"] is True
    assert out["corridor_expansion_task_count"] == 2
    assert out["corridor_expansion_tasks_metadata_only"] is True
    assert out["corridor_expansion_tasks_privacy_scan"]["ok"] is True
    expansion = out["corridor_expansion_queue"][0]
    assert expansion["category"] == "passport_confiscation"
    assert expansion["train_rows"] == 2
    assert expansion["observed_corridors"] == ["Nepal->Qatar"]
    assert expansion["observed_corridor_counts"] == {"Nepal->Qatar": 2}
    assert expansion["coverage_gap"] == "single_specific_corridor"
    assert expansion["category_specific_candidate_count"] == 0
    assert expansion["suggestion_source"] == "global_prompt_metadata"
    assert expansion["needed_distinct_corridors"] == 2
    assert expansion["target_corridor_suggestions"] == ["Bangladesh->Malaysia", "India->Kuwait"]
    assert "text" not in expansion and "prompt" not in expansion and "chosen" not in expansion
    task = out["corridor_expansion_tasks"][0]
    assert task == {
        "task_id": "corridor-expansion-passport-confiscation-bangladesh-malaysia",
        "category": "passport_confiscation",
        "target_corridor": "Bangladesh->Malaysia",
        "origin": "Bangladesh",
        "destination": "Malaysia",
        "coverage_gap": "single_specific_corridor",
        "suggestion_source": "global_prompt_metadata",
        "suggested_min_synthetic_rows": 3,
        "required_metadata_fields": ["id", "category", "corridor", "source", "privacy_review"],
        "scenario_constraints": [
            "synthetic_or_public_only",
            "no_names",
            "no_contacts",
            "no_case_details",
            "include_ilo_indicator",
            "include_jurisdiction_context",
        ],
        "acceptance_checks": [
            "metadata_only",
            "privacy_scan_ok",
            "non_duplicate_id",
            "corridor_matches_target",
            "typology_matches_category",
        ],
        "curation_hint": (
            "Stage vetted synthetic or public-source rows for this typology and corridor; "
            "keep worker-identifying details out of generated artifacts."
        ),
    }
    forbidden = {"messages", "prompt", "chosen", "rejected", "assistant", "text"}
    assert all(not forbidden.intersection(item) for item in out["corridor_expansion_tasks"])
    assert out["ok"] is False


def test_corridor_diversity_labels_generic_corridor_coverage_gap():
    pid_meta = {
        "P1": {"category": "labor_trafficking", "corridor": "various"},
        "P2": {"category": "labor_trafficking", "corridor": "various"},
        "P3": {"category": "debt_bondage", "corridor": "Nepal->Qatar"},
    }
    rows = [{"_meta": {"prompt_id": p}} for p in pid_meta]

    out = atq.corridor_diversity(rows, pid_meta, min_rows=2)

    assert out["corridor_expansion_queue_count"] == 1
    expansion = out["corridor_expansion_queue"][0]
    assert expansion["category"] == "labor_trafficking"
    assert expansion["observed_corridors"] == ["various"]
    assert expansion["coverage_gap"] == "generic_corridor_only"
    assert expansion["category_specific_candidate_count"] == 0
    assert expansion["suggestion_source"] == "global_prompt_metadata"
    assert expansion["target_corridor_suggestions"] == ["Nepal->Qatar"]


def test_corridor_diversity_prefers_category_specific_candidate_corridors():
    pid_meta = {
        "P1": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P2": {"category": "passport_confiscation", "corridor": "Nepal->Qatar"},
        "P3": {"category": "passport_confiscation", "corridor": "India->Kuwait"},
        "P4": {"category": "debt_bondage", "corridor": "Bangladesh->Malaysia"},
    }
    rows = [{"_meta": {"prompt_id": "P1"}}, {"_meta": {"prompt_id": "P2"}}]

    out = atq.corridor_diversity(rows, pid_meta, min_rows=2)

    expansion = out["corridor_expansion_queue"][0]
    assert expansion["category"] == "passport_confiscation"
    assert expansion["observed_corridors"] == ["Nepal->Qatar"]
    assert expansion["category_specific_candidate_count"] == 1
    assert expansion["suggestion_source"] == "category_prompt_metadata"
    assert expansion["target_corridor_suggestions"] == ["India->Kuwait"]


def test_quality_audit_summary_is_metadata_only(tmp_path):
    audit = tmp_path / "quality_audit.json"
    audit.write_text(json.dumps({
        "clean": False,
        "risk_flags": ["raw worker@example.com must not appear"],
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "ok": False,
            "min_rows": 4,
            "n_dense_single_corridor": 9,
            "corridor_expansion_queue_count": 9,
            "corridor_expansion_task_count": 45,
            "corridor_expansion_queue_privacy_scan": {"ok": True},
            "corridor_expansion_tasks_privacy_scan": {"ok": True},
            "corridor_expansion_queue": [{"prompt": "must not appear"}],
        },
        "citation_relevance": {
            "n_incoherent": 0,
            "repair_queue_count": 0,
            "repair_queue_privacy_scan": {"ok": True},
            "repair_queue": [{"text": "must not appear"}],
        },
        "fragile_fact_assertions": {"with_phone_like": 0},
    }), encoding="utf-8")

    summary = atq.quality_audit_summary(audit)

    assert summary["clean"] is False
    assert summary["risk_flags"] == [
        "9 dense single-corridor typologies (>=4 rows, jurisdiction shortcut risk)"
    ]
    assert summary["corridor_expansion_queue_count"] == 9
    assert summary["corridor_expansion_task_count"] == 45
    assert summary["corridor_expansion_queue_privacy_ok"] is True
    assert summary["corridor_expansion_tasks_privacy_ok"] is True
    assert summary["citation_repair_queue_count"] == 0
    assert summary["citation_repair_queue_privacy_ok"] is True
    assert "worker@example.com" not in json.dumps(summary)
    assert "prompt" not in json.dumps(summary)
    assert "text" not in json.dumps(summary)


def test_quality_audit_summary_redacts_sensitive_paths(tmp_path):
    audit_dir = tmp_path / "worker@example.com-case-123456789"
    audit_dir.mkdir()
    audit = audit_dir / "quality_audit.json"
    audit.write_text(json.dumps({
        "clean": True,
        "overfitting_leakage": {"sft": {"leaked": 0}, "dpo": {"leaked": 0}},
        "jurisdiction_corridor_diversity": {
            "n_dense_single_corridor": 0,
            "corridor_expansion_queue_count": 0,
            "corridor_expansion_task_count": 0,
            "corridor_expansion_queue_privacy_scan": {"ok": True},
            "corridor_expansion_tasks_privacy_scan": {"ok": True},
        },
        "citation_relevance": {
            "n_incoherent": 0,
            "repair_queue_count": 0,
            "repair_queue_privacy_scan": {"ok": True},
        },
        "fragile_fact_assertions": {"with_phone_like": 0},
    }), encoding="utf-8")

    summary = atq.quality_audit_summary(audit)
    summary_json = json.dumps(summary)

    assert summary["path"] == "external"
    assert "worker@example.com" not in summary_json
    assert "case-123456789" not in summary_json
    assert str(tmp_path) not in summary_json


def test_quality_audit_summary_ignores_non_object_json(tmp_path):
    audit = tmp_path / "quality_audit.json"
    audit.write_text(json.dumps(["not", "an", "audit", "object"]), encoding="utf-8")

    assert atq.quality_audit_summary(audit) is None


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "rows.jsonl"
    good = {"messages": [{"role": "assistant", "content": "ok"}], "_meta": {"prompt_id": "P1"}}
    malformed_shape = {"messages": "not-a-list", "_meta": "not-a-dict"}
    path.write_text(
        "\n".join([
            "{not-json",
            json.dumps(["not", "an", "object"]),
            json.dumps("not an object"),
            json.dumps(good),
            json.dumps(malformed_shape),
        ]) + "\n",
        encoding="utf-8",
    )

    rows = atq._load_jsonl(path)

    assert rows == [good, malformed_shape]
    assert atq._sft_assistant(good) == "ok"
    assert atq._sft_user(malformed_shape) == ""
    assert atq._sft_assistant(malformed_shape) == ""
    assert atq._prompt_id(malformed_shape) == ""


def test_prompt_id_helpers_sanitize_sensitive_or_free_text_values():
    assert atq._safe_prompt_id("P-123") == "P-123"
    assert atq._safe_prompt_id("template_20260129_115719") == "template_20260129_115719"
    assert atq._safe_prompt_id("worker@example.com case-123456789") == ""
    assert atq._safe_prompt_id(r"C:\Users\amare\private.txt") == ""
    assert atq._safe_prompt_id("free text worker clue") == ""
    assert atq._safe_prompt_id(["P-123"]) == ""
    assert atq._prompt_id({"_meta": {"prompt_id": "worker@example.com case-123456789"}}) == ""


def test_metadata_privacy_scan_flags_sensitive_prompt_ids():
    scan = atq._metadata_privacy_scan([
        {"prompt_id": "safe-P1"},
        {"prompt_id": "worker@example.com case-123456789"},
    ])

    assert scan["ok"] is False
    assert "$.metadata[1].prompt_id" in scan["email_like_paths"]
    assert "$.metadata[1].prompt_id" in scan["long_digit_paths"]


def test_text_extractors_ignore_non_string_training_fields():
    row = {
        "messages": [
            {"role": "user", "content": ["worker@example.com"]},
            {"role": "assistant", "content": {"case": "case-123456789"}},
        ]
    }
    dpo_rows = [
        {"chosen": ["worker@example.com"], "rejected": {"case": "case-123456789"}},
        {"chosen": "grounded response", "rejected": "bad"},
    ]
    gold = [{"text": {"case": "case-123456789"}}]

    assert atq._sft_user(row) == ""
    assert atq._sft_assistant(row) == ""
    assert atq.length_bias(dpo_rows)["n"] == 1
    assert atq.citation_relevance(gold)["n_checkable"] == 0


def test_audit_tolerates_malformed_jsonl_row_shapes(tmp_path, monkeypatch):
    def write_jsonl(name: str, rows: list[object]) -> None:
        (tmp_path / name).write_text(
            "\n".join("{not-json" if row == "BAD_JSON" else json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )

    valid_sft = {
        "_meta": {"prompt_id": "P1"},
        "messages": [
            {"role": "user", "content": "Can I leave if my passport is held?"},
            {"role": "assistant", "content": "Passport confiscation can be a forced labour warning."},
        ],
    }
    valid_dpo = {"_meta": {"prompt_id": "P1"}, "prompt": "p", "chosen": "grounded", "rejected": "bad"}
    nested_sft = {
        "messages": [
            {"role": "user", "content": ["worker@example.com"]},
            {"role": "assistant", "content": {"case": "case-123456789"}},
        ]
    }
    nested_dpo = {
        "_meta": {"prompt_id": "P1"},
        "prompt": {"email": "worker@example.com"},
        "chosen": ["case-123456789"],
        "rejected": {"bad": "value"},
    }
    write_jsonl("sft_train.jsonl", ["BAD_JSON", ["not", "object"], {"messages": "bad"}, nested_sft, valid_sft])
    write_jsonl("sft_heldout.jsonl", [["not", "object"], {"messages": [["bad"]]}])
    write_jsonl("dpo_train.jsonl", [["not", "object"], {"_meta": "bad"}, nested_dpo, valid_dpo])
    write_jsonl("dpo_heldout.jsonl", ["BAD_JSON", {"prompt": ["worker@example.com"]}, {"prompt": "heldout"}])

    monkeypatch.setattr(atq, "_TRAIN", tmp_path)
    monkeypatch.setattr(atq, "load_pid_meta", lambda *paths: {
        "P1": {"category": "document_retention", "corridor": "Nepal->Qatar"}
    })
    leakage_inputs = []

    def fake_near_dup_leakage(*args, **kwargs):
        leakage_inputs.append(args)
        return {
            "available": True,
            "heldout": 0,
            "leaked": 0,
            "ok": True,
        }

    monkeypatch.setattr(atq, "near_dup_leakage", fake_near_dup_leakage)

    report = atq.audit()
    report_json = json.dumps(report)

    assert report["inputs"] == {
        "sft_train": 3,
        "sft_heldout": 1,
        "dpo_train": 3,
        "dpo_heldout": 2,
        "pid_meta": 1,
    }
    assert report["false_pattern_length_bias"]["n"] == 1
    assert report["fragile_fact_assertions"]["n"] == 2
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json
    assert all("worker@example.com" not in json.dumps(args) for args in leakage_inputs)


def test_audit_risk_flags_do_not_copy_dense_typology_names(monkeypatch):
    def fake_load_jsonl(path):
        if path.name == "sft_train.jsonl":
            return [{"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]}]
        return []

    monkeypatch.setattr(atq, "_load_jsonl", fake_load_jsonl)
    monkeypatch.setattr(atq, "load_pid_meta", lambda *paths: {})
    monkeypatch.setattr(atq, "near_dup_leakage", lambda *args, **kwargs: {
        "available": True,
        "heldout": 0,
        "leaked": 0,
        "ok": True,
    })
    monkeypatch.setattr(atq, "length_bias", lambda rows: {"ok": True, "chosen_over_rejected_ratio": 1.0})
    monkeypatch.setattr(atq, "corridor_diversity", lambda rows, pid_meta: {
        "ok": False,
        "min_rows": 2,
        "n_dense_single_corridor": 1,
        "dense_single_corridor_typologies": ["worker@example.com-case-123456789"],
        "corridor_expansion_queue_count": 1,
        "corridor_expansion_task_count": 1,
        "corridor_expansion_queue_privacy_scan": {"ok": False},
        "corridor_expansion_tasks_privacy_scan": {"ok": False},
    })
    monkeypatch.setattr(atq, "fragile_fact_assertions", lambda gold: {
        "with_phone_like": 0,
        "ok_phone": True,
    })
    monkeypatch.setattr(atq, "citation_relevance", lambda gold: {
        "ok": True,
        "n_incoherent": 0,
    })

    report = atq.audit()
    flags_json = json.dumps(report["risk_flags"])

    assert report["clean"] is False
    assert report["risk_flags"] == [
        "1 dense single-corridor typologies (>=2 rows, jurisdiction shortcut risk)"
    ]
    assert "worker@example.com" not in flags_json
    assert "case-123456789" not in flags_json


def test_fragile_fact_assertions_flags_phone_and_counts_money_date():
    gold = [
        "Call the hotline at +1 555 0100 right away.",          # phone-like -> fragile (must be ~0)
        "The recruitment fee was $4,500 which exceeds the cap.",  # money amount -> informational
        "This rule changed in 2023 for that corridor.",          # explicit date -> informational
        "Keep your contract and payslips and seek free legal aid.",  # clean grounded reply
    ]
    out = atq.fragile_fact_assertions(gold)
    assert out["n"] == 4
    assert out["with_phone_like"] == 1 and out["ok_phone"] is False
    assert out["with_money_amount"] == 1
    assert out["with_explicit_date"] == 1


def test_fragile_fact_clean_gold_passes_phone_gate():
    gold = ["Keep your contract and payslips; you can raise a wage claim with the labour office."]
    out = atq.fragile_fact_assertions(gold)
    assert out["with_phone_like"] == 0 and out["ok_phone"] is True


def test_citation_relevance_flags_real_but_irrelevant_citation_without_raw_text():
    gold = [
        "Her passport was confiscated, contrary to ILO Convention No. 29.",
        "Her passport was confiscated, contrary to ILO Convention No. 138.",
    ]
    out = atq.citation_relevance(gold)
    assert out["n_checkable"] == 2
    assert out["n_incoherent"] == 1 and out["ok"] is False
    bad = out["examples"][0]
    assert bad["index"] == 1
    assert bad["cited_conventions"] == [138]
    assert "text" not in bad


def test_citation_relevance_builds_metadata_only_repair_queue():
    gold = [
        {
            "source": "sft_train",
            "source_index": 7,
            "prompt_id": "P-123",
            "category": "labor_trafficking",
            "corridor": "PH->HK",
            "text": "Her passport was confiscated, contrary to ILO Convention No. 138.",
        },
        {
            "source": "dpo_train_chosen",
            "source_index": 8,
            "prompt_id": "P-124",
            "category": "labor_trafficking",
            "corridor": "PH->HK",
            "text": "Her passport was confiscated, contrary to ILO Convention No. 29.",
        },
    ]
    out = atq.citation_relevance(gold)

    assert out["repair_queue_count"] == 1
    assert out["repair_queue_metadata_only"] is True
    assert out["repair_queue_privacy_scan"]["ok"] is True
    assert out["by_source"] == {"sft_train": 1}
    assert out["by_category"] == {"labor_trafficking": 1}
    assert out["by_mapped_signal"]["document_retention"] == 1
    repair = out["repair_queue"][0]
    assert repair["prompt_id"] == "P-123"
    assert repair["source_index"] == 7
    assert repair["category"] == "labor_trafficking"
    assert "text" not in repair and "prompt" not in repair and "chosen" not in repair


def test_citation_relevance_sanitizes_sensitive_prompt_ids_without_raw_values():
    gold = [
        {
            "source": "sft_train",
            "source_index": 7,
            "prompt_id": "worker@example.com case-123456789",
            "category": "labor_trafficking",
            "corridor": "PH->HK",
            "text": "Her passport was confiscated, contrary to ILO Convention No. 138.",
        },
    ]

    out = atq.citation_relevance(gold)
    report_json = json.dumps(out)

    assert out["repair_queue_count"] == 1
    assert out["repair_queue_privacy_scan"]["ok"] is True
    assert out["repair_queue"][0]["prompt_id"] == ""
    assert "worker@example.com" not in report_json
    assert "case-123456789" not in report_json


def test_sft_helpers_extract_roles():
    row = {"messages": [{"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]}
    assert atq._sft_user(row) == "u"
    assert atq._sft_assistant(row) == "a"
    assert atq._sft_user({}) == "" and atq._sft_assistant({}) == ""
