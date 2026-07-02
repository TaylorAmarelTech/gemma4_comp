"""Tests for scripts/build_contract_dpo.py -- contract-derived hard-negative DPO pairs.

Pins the core guarantee: ablating exactly one chain link from a full gold trace yields a rejected that is
identical except for that missing link (statute or action), and only full-chain traces are eligible."""
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


bcd = _load("build_contract_dpo", _ROOT / "scripts" / "build_contract_dpo.py")
rc = _load("reasoning_contract", _ROOT / "scripts" / "reasoning_contract.py")

_FULL = ("This situation shows passport confiscation, a recognised ILO forced labour indicator. "
         "It is prohibited under ILO Convention No. 29 (Forced Labour). "
         "You should keep copies of your documents and do not hand over your passport to the recruiter. "
         "Contact your embassy and file a complaint with the labour office, which helps migrant workers.")


def _row(assistant, pid="T1"):
    return {"messages": [{"role": "user", "content": "My recruiter took my passport, what do I do?"},
                         {"role": "assistant", "content": assistant}], "_meta": {"prompt_id": pid}}


def test_ablate_statute_removes_only_the_citation():
    reduced = bcd.ablate_link(_FULL, "statute")
    assert reduced is not None
    v = rc.verify_reasoning(reduced)
    assert v.steps["statute"] is False                      # the citation is gone
    assert v.steps["indicator"] and v.steps["action"] and v.steps["resources"]   # everything else stays


def test_ablate_action_removes_only_the_action():
    reduced = bcd.ablate_link(_FULL, "action")
    assert reduced is not None
    v = rc.verify_reasoning(reduced)
    assert v.steps["action"] is False
    assert v.steps["indicator"] and v.steps["statute"] and v.steps["resources"]


def test_ablate_returns_none_when_link_absent():
    neutral = "The weather is mild and the report describes general background information only."
    assert bcd.ablate_link(neutral, "statute") is None
    assert bcd.ablate_link(neutral, "action") is None
    assert bcd.ablate_link({"text": _FULL}, "statute") is None


def test_swap_citation_to_wrong_convention_keeps_statute_but_breaks_coherence():
    rejected = bcd.swap_citation_to_wrong_convention(_FULL)

    assert rejected is not None
    assert rejected != _FULL
    chosen = rc.verify_reasoning(_FULL)
    swapped = rc.verify_reasoning(rejected)
    assert chosen.citation_valid is True
    assert swapped.steps["statute"] is True
    assert swapped.citation_valid is False


def test_build_pairs_yields_one_hard_negative_per_present_link():
    doc = bcd.build_pairs([_row(_FULL)])
    pairs = doc["pairs"]
    assert doc["manifest"]["eligible_gold"] == 1
    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["contract_manifest_issues"] == []
    assert doc["manifest"]["pair_integrity_counts"] == {}
    assert doc["manifest"]["pair_integrity_issues"] == []
    assert doc["manifest"]["metadata_sanitized"] == {}
    assert {p["_meta"]["ablated_link"] for p in pairs} == {"statute", "action", "citation_coherence"}
    assert {p["_meta"]["prompt_id"] for p in pairs} == {"T1"}
    for p in pairs:
        assert p["chosen"] == _FULL                         # chosen is the untouched gold trace
        assert p["rejected"] != _FULL
        if p["_meta"]["ablated_link"] in {"statute", "action"}:
            assert len(p["rejected"]) < len(_FULL)           # deletion negatives are strictly reduced
        else:
            assert p["_meta"]["source"] == "contract_citation_swap"
            assert rc.verify_reasoning(p["rejected"]).citation_valid is False
        assert p["prompt"].startswith("My recruiter")        # the user turn carried through


def test_non_satisfying_trace_is_not_eligible():
    doc = bcd.build_pairs([_row("I'm sorry, but I can't help with that.")])
    manifest = doc["manifest"]
    assert manifest["eligible_gold"] == 0 and doc["pairs"] == []
    assert manifest["safe_to_train"] is False
    assert manifest["contract_manifest_issues"] == ["contract_dpo_no_eligible_gold", "contract_dpo_no_pairs"]


def test_build_pairs_dedupes_identical_pairs():
    doc = bcd.build_pairs([_row(_FULL), _row(_FULL)])
    manifest = doc["manifest"]
    assert manifest["pairs"] == 3
    assert manifest["skipped_duplicate_pairs"] == 3
    assert manifest["duplicate_output_pair_rows"] == 0
    assert manifest["safe_to_train"] is True
    assert manifest["contract_manifest_issues"] == []
    assert manifest["pair_integrity_issues"] == []


def test_build_pairs_tolerates_malformed_row_shapes():
    bad_meta = _row(_FULL)
    bad_meta["_meta"] = "not-a-dict"
    non_string_assistant = {
        "messages": [
            {"role": "user", "content": "My recruiter took my passport, what do I do?"},
            {"role": "assistant", "content": {"text": _FULL}},
        ],
        "_meta": {"prompt_id": "bad-assistant"},
    }
    non_string_user = {
        "messages": [
            {"role": "user", "content": {"text": "do not stringify prompt"}},
            {"role": "assistant", "content": _FULL},
        ],
        "_meta": {"prompt_id": "bad-user"},
    }
    doc = bcd.build_pairs([
        ["not", "a", "row"],
        {"messages": "not-a-list"},
        {"messages": [["not", "a", "message"]]},
        non_string_assistant,
        non_string_user,
        bad_meta,
    ])

    assert doc["manifest"]["input"] == 6
    assert doc["manifest"]["eligible_gold"] == 1
    assert doc["manifest"]["pairs"] == 3
    assert {pair["_meta"].get("prompt_id") for pair in doc["pairs"]} == {None}
    assert doc["manifest"]["safe_to_train"] is True
    assert all(pair["_meta"].get("prompt_id") not in {"bad-assistant", "bad-user"} for pair in doc["pairs"])


def test_build_pairs_sanitizes_sensitive_prompt_ids_without_copying_values():
    row = _row(_FULL, pid=r"worker@example.com case-123456789 C:\Users\amare\private.txt")

    doc = bcd.build_pairs([row], output_path=Path("contract_dpo.jsonl"))
    doc_json = json.dumps(doc)

    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["metadata_sanitized"] == {"prompt_id": 1}
    assert {pair["_meta"].get("prompt_id") for pair in doc["pairs"]} == {None}
    assert "worker@example.com" not in doc_json
    assert "case-123456789" not in doc_json
    assert "private.txt" not in doc_json


def test_build_pairs_sanitizes_non_code_prompt_ids_without_copying_values():
    row = _row(_FULL, pid="free text worker clue")

    doc = bcd.build_pairs([row], output_path=Path("contract_dpo.jsonl"))
    doc_json = json.dumps(doc)

    assert doc["manifest"]["safe_to_train"] is True
    assert doc["manifest"]["metadata_sanitized"] == {"prompt_id": 1}
    assert {pair["_meta"].get("prompt_id") for pair in doc["pairs"]} == {None}
    assert "free text worker clue" not in doc_json


def test_chat_text_extractors_ignore_non_string_content():
    row = {
        "messages": [
            {"role": "user", "content": {"text": "do not stringify"}},
            {"role": "user", "content": "My recruiter took my passport, what do I do?"},
            {"role": "assistant", "content": {"text": _FULL}},
            {"role": "assistant", "content": _FULL},
        ]
    }

    assert bcd._user_text(row) == "My recruiter took my passport, what do I do?"
    assert bcd._assistant_text(row) == _FULL
    assert bcd._user_text({"messages": [{"role": "user", "content": {"text": "no"}}]}) == ""
    assert bcd._assistant_text({"messages": [{"role": "assistant", "content": {"text": _FULL}}]}) == ""


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "reasoning_sft.jsonl"
    good = _row(_FULL)
    path.write_text(
        "\n".join([
            "{not-json",
            json.dumps(["not", "a", "row"]),
            json.dumps("not a row"),
            json.dumps(good),
            json.dumps({"messages": "not-a-list"}),
        ]) + "\n",
        encoding="utf-8",
    )

    rows = bcd._load_jsonl(path)

    assert rows == [good, {"messages": "not-a-list"}]
    assert bcd._assistant_text({"messages": "not-a-list"}) == ""
    assert bcd._user_text({"messages": [["not", "a", "message"]]}) == ""


def test_manifest_paths_track_custom_output_path(tmp_path):
    repo_out_path = Path("reports/training/custom_contract_dpo.jsonl")
    repo_doc = bcd.build_pairs([_row(_FULL)], output_path=repo_out_path)
    assert repo_doc["manifest"]["output_path"] == "reports/training/custom_contract_dpo.jsonl"
    assert repo_doc["manifest"]["manifest_path"] == "reports/training/custom_contract_dpo_manifest.json"

    out_path = tmp_path / "custom_contract_dpo.jsonl"
    doc = bcd.build_pairs([_row(_FULL)], output_path=out_path)
    assert doc["manifest"]["output_path"] == "external"
    assert doc["manifest"]["manifest_path"] == "external"
    assert str(tmp_path) not in json.dumps(doc["manifest"])
    assert bcd.manifest_path_for(out_path) == tmp_path / "custom_contract_dpo_manifest.json"


def test_default_manifest_path_preserves_existing_filename():
    assert bcd.manifest_path_for(bcd.OUT) == bcd.MANIFEST


def test_main_writes_manifest_next_to_custom_output(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    out = sensitive_dir / "custom_contract_dpo.jsonl"
    sft.write_text(json.dumps(_row(_FULL)) + "\n", encoding="utf-8")

    assert bcd.main(["--sft", str(sft), "--out", str(out)]) == 0
    manifest_path = sensitive_dir / "custom_contract_dpo_manifest.json"
    assert out.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_json = json.dumps(manifest)
    assert manifest["output_path"] == "external"
    assert manifest["manifest_path"] == "external"
    assert manifest["safe_to_train"] is True
    assert manifest["contract_manifest_issues"] == []
    assert str(tmp_path) not in manifest_json
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json


def test_validate_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    out = sensitive_dir / "custom_contract_dpo.jsonl"
    sft.write_text(json.dumps(_row(_FULL)) + "\n", encoding="utf-8")

    rc = bcd.main(["--sft", str(sft), "--out", str(out), "--validate"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"output_path": "external"' in printed
    assert '"manifest_path": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_missing_input_console_redacts_sensitive_path(tmp_path, capsys):
    missing = tmp_path / "worker@example.com-case-123456789" / "reasoning_sft.jsonl"

    rc = bcd.main(["--sft", str(missing)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no reasoning traces at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_unsafe_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    out = sensitive_dir / "custom_contract_dpo.jsonl"
    sft.write_text(json.dumps(_row("I'm sorry, but I can't help with that.")) + "\n", encoding="utf-8")

    rc = bcd.main(["--sft", str(sft), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 1
    assert '"output_path": "external"' in printed
    assert "unsafe contract-DPO shape" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_pair_integrity_flags_unchanged_rejected_pair():
    pair = bcd.build_pairs([_row(_FULL)])["pairs"][0]
    pair["rejected"] = pair["chosen"]
    counts, issues = bcd._pair_integrity([pair], min_steps=4)
    assert counts["unchanged_rejected"] == 1
    assert "contract_dpo_pair_rejected_unchanged" in issues


def test_pair_integrity_rejects_non_string_pair_fields_without_leaking_values():
    pair = {
        "prompt": ["worker@example.com"],
        "chosen": {"case": "case-123456789"},
        "rejected": "short",
        "_meta": {"source": "contract_ablation", "ablated_link": "statute"},
    }

    counts, issues = bcd._pair_integrity([pair], min_steps=4)
    details = json.dumps({"counts": counts, "issues": issues})

    assert counts["invalid_pair_shape"] == 1
    assert issues == ["contract_dpo_pair_invalid_shape"]
    assert bcd._duplicate_pair_rows([pair, pair]) == 0
    assert "worker@example.com" not in details
    assert "case-123456789" not in details


def test_pair_integrity_flags_rejected_that_still_carries_link():
    pair = bcd.build_pairs([_row(_FULL)])["pairs"][0]
    pair["rejected"] = pair["chosen"].replace("documents", "records")
    counts, issues = bcd._pair_integrity([pair], min_steps=4)
    assert counts["rejected_still_carries_ablated_link"] == 1
    assert "contract_dpo_pair_rejected_still_carries_ablated_link" in issues


def test_main_validate_fails_when_no_contract_pairs(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    sft.write_text(json.dumps(_row("I'm sorry, but I can't help with that.")) + "\n", encoding="utf-8")

    assert bcd.main(["--sft", str(sft), "--validate"]) == 1


def test_main_refuses_to_write_unsafe_contract_pairs(tmp_path):
    sft = tmp_path / "reasoning_sft.jsonl"
    out = tmp_path / "custom_contract_dpo.jsonl"
    sft.write_text(json.dumps(_row("I'm sorry, but I can't help with that.")) + "\n", encoding="utf-8")

    assert bcd.main(["--sft", str(sft), "--out", str(out)]) == 1
    assert not out.exists()
    assert not (tmp_path / "custom_contract_dpo_manifest.json").exists()
