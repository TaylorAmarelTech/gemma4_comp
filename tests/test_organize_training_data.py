"""Tests for scripts/organize_training_data.py -- anti-shortcut organisation of training data."""
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


org = _load("organize_training_data", _ROOT / "scripts" / "organize_training_data.py")


def _sft(pid, user, asst="ok"):
    return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": asst}],
            "_meta": {"prompt_id": pid}}


def test_organize_holds_out_whole_typologies():
    pid2cat = {"p1": "A", "p2": "A", "p3": "B", "p4": "B", "p5": "C", "p6": "C"}
    sft = [_sft(pid, f"q-{pid}") for pid in pid2cat]
    doc = org.organize(sft, [], pid2cat, heldout_fraction=0.34, cap_per_category=0, seed=17)
    m = doc["manifest"]
    assert m["n_categories"] == 3 and m["n_heldout_categories"] == 1
    ho = set(m["heldout_categories"])
    train_cats = {pid2cat[r["_meta"]["prompt_id"]] for r in doc["sft_train"]}
    assert train_cats.isdisjoint(ho)                                          # train never sees held-out typology
    assert all(pid2cat[r["_meta"]["prompt_id"]] in ho for r in doc["sft_heldout"])
    assert len(doc["sft_train"]) + len(doc["sft_heldout"]) == 6               # all rows accounted for


def test_organize_caps_and_interleaves():
    pid2cat = {}
    sft = []
    for i in range(5):
        pid2cat[f"a{i}"] = "A"
        pid2cat[f"b{i}"] = "B"
        sft.append(_sft(f"a{i}", f"qa{i}"))
        sft.append(_sft(f"b{i}", f"qb{i}"))
    doc = org.organize(sft, [], pid2cat, heldout_fraction=0.0, cap_per_category=3, seed=17)
    cats = [pid2cat[r["_meta"]["prompt_id"]] for r in doc["sft_train"]]
    assert cats.count("A") == 3 and cats.count("B") == 3                      # capped per typology
    assert not any(cats[i] == cats[i + 1] == cats[i + 2] for i in range(len(cats) - 2))  # interleaved


def test_organize_dedups_identical_text():
    pid2cat = {"p1": "A", "p2": "A"}
    sft = [_sft("p1", "same text"), _sft("p2", "same text")]                  # identical user text
    doc = org.organize(sft, [], pid2cat, heldout_fraction=0.0, cap_per_category=0, seed=17)
    assert len(doc["sft_train"]) + len(doc["sft_heldout"]) == 1               # text-hash dedup


def test_near_dedup_conservative_default_but_tunable():
    """Default dist keeps borderline near-copies (preserve diversity); a looser dist drops them."""
    import pytest
    if not org._HAVE_NEAR_DEDUP:
        pytest.skip("research_tools near-dedup unavailable")
    base = "I paid a recruitment agency a very large fee for a factory job in another country"
    para = base + " overseas"        # ~6-bit SimHash distance -- a near-copy, not exact, not <=3
    distinct = "what are the minimum wage protections for domestic workers leaving this corridor"
    pid2cat = {"p1": "A", "p2": "A", "p3": "A"}
    sft = [_sft("p1", base), _sft("p2", para), _sft("p3", distinct)]
    keep = org.organize(sft, [], pid2cat, heldout_fraction=0.0, cap_per_category=0, near_dup_dist=3)
    assert len(keep["sft_train"]) == 3                                        # strict default keeps the near-copy
    assert keep["manifest"]["dedup"]["sft"]["near_dropped"] == 0
    drop = org.organize(sft, [], pid2cat, heldout_fraction=0.0, cap_per_category=0, near_dup_dist=8)
    assert len(drop["sft_train"]) == 2                                        # looser dist drops the near-copy
    assert drop["manifest"]["dedup"]["sft"]["near_dropped"] == 1              # param wires through to dedup_new


def test_manifest_records_dedup_block():
    pid2cat = {"p1": "A", "p2": "A"}
    sft = [_sft("p1", "same text here"), _sft("p2", "same text here")]        # exact dup
    doc = org.organize(sft, [], pid2cat, heldout_fraction=0.0, cap_per_category=0)
    dd = doc["manifest"]["dedup"]
    assert dd["sft"]["in"] == 2 and dd["sft"]["kept_pre_split"] == 1          # exact dup collapsed, counted
    assert "method" in dd and dd["sft"]["near_dropped"] == 0
    assert dd["dpo"]["in"] == 0 and dd["dpo"]["kept_pre_split"] == 0


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "sft.jsonl"
    good = _sft("p1", "same text here")
    malformed_shape = {"messages": "not-a-list", "_meta": "not-a-dict"}
    path.write_text(
        "\n".join([
            "{not-json",
            json.dumps(["not", "a", "row"]),
            json.dumps("not a row"),
            json.dumps(good),
            json.dumps(malformed_shape),
        ]) + "\n",
        encoding="utf-8",
    )

    rows = org.load_jsonl(path)

    assert rows == [good, malformed_shape]
    assert org._sft_text(malformed_shape) == ""
    assert org._cat_of(malformed_shape, {"p1": "A"}) == "unknown"


def test_load_pid2cat_skips_malformed_prompt_documents(tmp_path):
    bad_json = tmp_path / "bad.json"
    non_list = tmp_path / "non_list.json"
    good = tmp_path / "good.json"
    bad_json.write_text("{not-json", encoding="utf-8")
    non_list.write_text(json.dumps({"prompts": {"id": "not-a-list"}}), encoding="utf-8")
    good.write_text(json.dumps({
        "prompts": [
            ["not", "a", "prompt"],
            {"category": "missing-id"},
            {"id": "p1", "category": "A"},
        ]
    }), encoding="utf-8")

    assert org.load_pid2cat(bad_json, non_list, good) == {"p1": "A"}


def test_organize_drops_malformed_or_empty_training_rows():
    pid2cat = {"p1": "A"}
    sft = [
        ["not", "a", "row"],
        {"messages": "not-a-list"},
        {"messages": [{"role": "assistant", "content": "assistant only"}]},
        {"messages": [{"role": "user", "content": {"text": "worker@example.com raw prompt"}}],
         "_meta": {"prompt_id": "bad-sft"}},
        _sft("p1", "valid user text"),
    ]
    dpo = [
        ["not", "a", "row"],
        {"chosen": "good", "rejected": "bad"},
        {"prompt": "", "chosen": "good", "rejected": "bad"},
        {"prompt": {"text": "worker@example.com raw prompt"}, "chosen": "good", "rejected": "bad",
         "_meta": {"prompt_id": "bad-dpo"}},
        {"prompt": "valid dpo prompt", "chosen": "good", "rejected": "bad", "_meta": {"prompt_id": "p1"}},
    ]

    doc = org.organize(sft, dpo, pid2cat, heldout_fraction=0.0, cap_per_category=0)
    dd = doc["manifest"]["dedup"]
    doc_json = json.dumps(doc)

    assert dd["malformed_or_empty"] == {"sft_dropped": 4, "dpo_dropped": 4}
    assert doc["manifest"]["sft"] == {"train": 1, "heldout": 0}
    assert doc["manifest"]["dpo"] == {"train": 1, "heldout": 0}
    assert doc["sft_train"][0]["_meta"]["prompt_id"] == "p1"
    assert doc["dpo_train"][0]["_meta"]["prompt_id"] == "p1"
    assert "worker@example.com" not in doc_json


def test_main_console_redacts_sensitive_output_dir(tmp_path, monkeypatch, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "sft.jsonl"
    out_dir = sensitive_dir / "organized"
    sft.write_text(json.dumps(_sft("p1", "same text here")) + "\n", encoding="utf-8")
    monkeypatch.setattr(org, "load_pid2cat", lambda *paths: {"p1": "A"})

    result = org.main(["--sft", str(sft), "--dpo", str(sensitive_dir / "dpo.jsonl"),
                       "--out-dir", str(out_dir)])
    printed = capsys.readouterr().out

    assert result == 0
    assert "-> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert (out_dir / "organize_manifest.json").exists()
