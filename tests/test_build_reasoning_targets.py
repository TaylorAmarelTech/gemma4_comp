"""Tests for scripts/build_reasoning_targets.py -- the indicator->statute->action->resources chain gate."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))   # so sibling imports (citation/refusal/taxonomy) resolve


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


br = _load("build_reasoning_targets", _ROOT / "scripts" / "build_reasoning_targets.py")


def test_default_input_is_train_split_not_unsplit_sft():
    assert br.SFT_IN.name == "sft_train.jsonl"


def _sft(pid, assistant):
    return {"messages": [{"role": "user", "content": f"q-{pid}"},
                         {"role": "assistant", "content": assistant}], "_meta": {"prompt_id": pid}}


_FULL = ("I can't help structure recruitment fees to evade the cap. What you describe is debt bondage, a "
         "forced-labour indicator, and under ILO Convention C181 charging workers illegal fees is prohibited. "
         "You are not obligated to pay it; keep copies of every receipt and contract. Contact the national "
         "labour regulator or your embassy, and you can file a complaint.")
_PARTIAL = ("I won't help with that. This recruiter-driven contract substitution and deception is conduct "
            "that ILO Convention C181 covers; you are not obligated to accept the swapped terms and should "
            "keep copies of the original signed contract for your own records going forward in case you need "
            "them later.")
_BARE = ("I'm sorry, but I cannot help with that request. I am not able to assist with what you are asking, "
         "and I would encourage you to reconsider whether this is appropriate before proceeding any further "
         "with the approach that you described to me just now in your message.")
_INCOHERENT_CITATION = (
    "I can't help you keep her passport. Confiscating a worker's passport is document retention and a "
    "forced-labour indicator, but ILO Convention No. 138 is not the governing citation for that risk. "
    "You should return the document, keep copies of any requests, and contact the labour regulator or "
    "an NGO if the worker needs help."
)
_STRICT = (
    "She was recruited through deception and false promises, then forced to work. Passport confiscation "
    "and unpaid wages are forced-labour indicators. This is prohibited under ILO Convention No. 29 and "
    "ILO Convention No. 95. You should keep copies, recover unpaid wages, seek compensation, and you "
    "should not be punished for things you were compelled to do. Contact your embassy and file a complaint "
    "with the labour office."
)


def test_chain_links_detects_full_chain():
    assert br.chain_links(_FULL) == {"indicator": True, "statute": True, "action": True, "resources": True}


def test_bare_refusal_is_action_only():
    links = br.chain_links(_BARE)
    assert links["action"] is True                         # a refusal IS a graded action (not a format failure)
    assert not (links["indicator"] or links["statute"] or links["resources"])
    assert sum(links.values()) == 1                        # bare refusal = 1/4 chain links


def test_partial_chain_missing_resources():
    links = br.chain_links(_PARTIAL)
    assert links["indicator"] and links["statute"] and links["action"]
    assert links["resources"] is False                     # names indicator+law+action but no resource pointer
    assert sum(links.values()) == 3


def test_build_gates_and_annotates():
    doc = br.build([_sft("p1", _FULL), _sft("p2", _PARTIAL), _sft("p3", _BARE)], min_chain=3)
    m = doc["manifest"]
    assert m["input"] == 3 and m["kept"] == 2              # full(4) + partial(3) kept; bare(1) dropped
    assert {r["_meta"]["prompt_id"] for r in doc["rows"]} == {"p1", "p2"}
    p1 = next(r for r in doc["rows"] if r["_meta"]["prompt_id"] == "p1")
    assert p1["_meta"]["chain_completeness"] == 4 and p1["_meta"]["chain_links"]["resources"] is True
    assert m["link_presence"]["action"] == 3              # all three state an action (incl. the bare refusal)
    assert m["link_presence"]["resources"] == 1           # only the full target points to resources
    assert m["completeness_distribution"]["1"] == 1       # the bare refusal


def test_build_min_chain_4_is_stricter():
    doc = br.build([_sft("p1", _FULL), _sft("p2", _PARTIAL)], min_chain=4)
    assert doc["manifest"]["kept"] == 1                    # only the full 4/4 chain survives min_chain=4


def test_build_contract_strict_requires_full_contract_triad_and_core_remedies():
    doc = br.build([_sft("strict", _STRICT), _sft("loose", _FULL)], min_chain=3, contract="strict")
    m = doc["manifest"]

    assert m["contract"] == "strict"
    assert m["contract_checked"] == 2
    assert m["dropped_contract"] == 1
    assert m["kept"] == 1
    assert doc["rows"][0]["_meta"]["prompt_id"] == "strict"
    assert doc["rows"][0]["_meta"]["contract"] == "strict"
    assert m["contract_violation_examples"][0]["prompt_id"] == "loose"
    assert m["contract_violation_examples"][0]["palermo_triad_complete"] is False


def test_build_rejects_unknown_contract_mode():
    try:
        br.build([_sft("p1", _FULL)], contract="unknown")
    except ValueError as exc:
        assert "unsupported contract mode" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("expected ValueError")


def test_build_drops_chain_complete_but_irrelevant_citation_by_default():
    doc = br.build([_sft("bad-cite", _INCOHERENT_CITATION)], min_chain=3)
    m = doc["manifest"]
    assert doc["rows"] == []
    assert m["kept"] == 0
    assert m["require_citation_relevance"] is True
    assert m["citation_relevance_checkable"] == 1
    assert m["citation_relevance_incoherent"] == 1
    assert m["dropped_incoherent_citations"] == 1
    assert m["incoherent_citation_examples"] == [{
        "prompt_id": "bad-cite",
        "mapped_signals": ["document_retention"],
        "cited_conventions": [138],
        "expected_conventions": [29],
        "matched": [],
        "coherent": False,
    }]
    assert "text" not in m["incoherent_citation_examples"][0]


def test_incoherent_citation_examples_reject_case_like_8_digit_prompt_ids_without_copying_them():
    doc = br.build([_sft("case_12345678", _INCOHERENT_CITATION)], min_chain=3)
    manifest_json = json.dumps(doc["manifest"])

    assert doc["manifest"]["incoherent_citation_examples"][0]["prompt_id"] == ""
    assert "case_12345678" not in manifest_json


def test_incoherent_citation_examples_keep_generated_date_prompt_ids():
    pid = "template_20260129_115719_24937"
    doc = br.build([_sft(pid, _INCOHERENT_CITATION)], min_chain=3)

    assert doc["manifest"]["incoherent_citation_examples"][0]["prompt_id"] == pid


def test_build_can_keep_irrelevant_citation_in_legacy_mode():
    doc = br.build([_sft("bad-cite", _INCOHERENT_CITATION)], min_chain=3,
                   require_citation_relevance=False)
    assert doc["manifest"]["kept"] == 1
    assert doc["manifest"]["require_citation_relevance"] is False
    assert doc["manifest"]["dropped_incoherent_citations"] == 0
    assert doc["rows"][0]["_meta"]["chain_completeness"] == 4


def test_build_tolerates_malformed_row_shapes():
    bad_meta = _sft("bad-meta", _FULL)
    bad_meta["_meta"] = "not-a-dict"
    non_string_content = {
        "messages": [{"role": "assistant", "content": {"text": _FULL}}],
        "_meta": {"prompt_id": "non-string-content"},
    }
    doc = br.build([
        ["not", "a", "row"],
        {"messages": "not-a-list"},
        {"messages": [["not", "a", "message"]]},
        non_string_content,
        bad_meta,
    ], min_chain=3)

    assert doc["manifest"]["input"] == 5
    assert doc["manifest"]["kept"] == 1
    assert doc["rows"][0]["_meta"].get("prompt_id") is None
    assert doc["rows"][0]["_meta"]["chain_completeness"] == 4
    assert all(r["_meta"].get("prompt_id") != "non-string-content" for r in doc["rows"])


def test_assistant_text_ignores_non_string_content():
    row = {
        "messages": [
            {"role": "assistant", "content": {"text": _FULL}},
            {"role": "user", "content": "ignore"},
            {"role": "assistant", "content": _FULL},
        ]
    }

    assert br._assistant_text(row) == _FULL
    assert br._assistant_text({"messages": [{"role": "assistant", "content": {"text": _FULL}}]}) == ""
    assert br.chain_links({"text": _FULL}) == {
        "indicator": False,
        "statute": False,
        "action": False,
        "resources": False,
    }


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "sft_train.jsonl"
    good = _sft("p1", _FULL)
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

    rows = br._load_jsonl(path)

    assert rows == [good, {"messages": "not-a-list"}]
    assert br._assistant_text({"messages": "not-a-list"}) == ""


def test_manifest_paths_track_custom_output_path(tmp_path):
    repo_out_path = Path("reports/training/custom_reasoning_targets.jsonl")
    repo_doc = br.build([_sft("p1", _FULL)], min_chain=3, output_path=repo_out_path)
    assert repo_doc["manifest"]["output_path"] == "reports/training/custom_reasoning_targets.jsonl"
    assert repo_doc["manifest"]["manifest_path"] == "reports/training/custom_reasoning_targets_manifest.json"

    out_path = tmp_path / "custom_reasoning_targets.jsonl"
    doc = br.build([_sft("p1", _FULL)], min_chain=3, output_path=out_path)
    assert doc["manifest"]["output_path"] == "external"
    assert doc["manifest"]["manifest_path"] == "external"
    assert str(tmp_path) not in json.dumps(doc["manifest"])
    assert br.manifest_path_for(out_path) == tmp_path / "custom_reasoning_targets_manifest.json"


def test_default_manifest_path_preserves_existing_filename():
    assert br.manifest_path_for(br.OUT) == br.MANIFEST


def test_main_writes_manifest_next_to_custom_output(tmp_path):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "sft_train.jsonl"
    out = sensitive_dir / "custom_reasoning_targets.jsonl"
    sft.write_text(json.dumps(_sft("p1", _FULL)) + "\n", encoding="utf-8")

    assert br.main(["--sft", str(sft), "--out", str(out)]) == 0
    manifest_path = sensitive_dir / "custom_reasoning_targets_manifest.json"
    assert out.exists()
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_json = json.dumps(manifest)
    assert manifest["output_path"] == "external"
    assert manifest["manifest_path"] == "external"
    assert str(tmp_path) not in manifest_json
    assert "worker@example.com" not in manifest_json
    assert "case-123456789" not in manifest_json


def test_validate_console_redacts_sensitive_paths(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "sft_train.jsonl"
    out = sensitive_dir / "custom_reasoning_targets.jsonl"
    sft.write_text(json.dumps(_sft("p1", _FULL)) + "\n", encoding="utf-8")

    rc = br.main(["--sft", str(sft), "--out", str(out), "--validate"])
    printed = capsys.readouterr().out

    assert rc == 0
    assert '"output_path": "external"' in printed
    assert '"manifest_path": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert not out.exists()


def test_missing_input_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    rc = br.main(["--sft", str(sensitive_dir / "sft_train.jsonl")])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "no SFT train split at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_success_console_redacts_sensitive_output_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "sft_train.jsonl"
    out = sensitive_dir / "custom_reasoning_targets.jsonl"
    sft.write_text(json.dumps(_sft("p1", _FULL)) + "\n", encoding="utf-8")

    rc = br.main(["--sft", str(sft), "--out", str(out)])
    printed = capsys.readouterr().out

    assert rc == 0
    assert "-> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert out.exists()
