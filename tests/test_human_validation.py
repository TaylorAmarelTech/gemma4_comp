"""Tests for scripts/build_human_validation_sample.py -- blinded stratified sample + correlation."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hv = _load("build_human_validation_sample", _ROOT / "scripts" / "build_human_validation_sample.py")


def _responses():
    # response text deliberately avoids the words "baseline"/"harnessed" so the blinding test
    # checks the EXPORT, not the synthetic content
    out = []
    for pid in ("p1", "p2", "p3", "p4"):
        for n, arm in enumerate(("baseline", "harnessed")):
            out.append({"prompt_id": pid, "model": "m", "arm": arm, "response": f"AI reply for {pid} v{n}"})
    return out


_CORPUS = {f"p{i}": {"text": f"worker msg {i}", "category": "cat" + str(i % 2), "difficulty": "hard"}
           for i in range(1, 5)}
_GRADER = {(f"p{i}", "m", arm): (8.0 if arm == "harnessed" else 4.0)
           for i in range(1, 5) for arm in ("baseline", "harnessed")}


def test_build_items_joins_and_keeps_complete():
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    assert len(items) == 8
    assert all(i["prompt_text"] and i["grader_score"] is not None and "category" in i for i in items)


def test_read_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "responses.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"prompt_id": "p1", "response": "ok"}),
            "[1, 2, 3]",
            '"worker@example.com case-123456789 raw value"',
            "{bad json",
        ]) + "\n",
        encoding="utf-8",
    )

    rows = hv._read_jsonl(path)

    assert rows == [{"prompt_id": "p1", "response": "ok"}]


def test_load_corpus_skips_malformed_prompt_documents(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({
        "prompts": [
            {"id": "p1", "text": "worker msg", "category": "cat", "difficulty": "hard"},
            {"id": "p2", "text": {"raw": "worker@example.com case-123456789"}},
            {"id": "p3", "text": "safe worker msg", "category": ["worker@example.com"], "difficulty": {"case": "case-123456789"}},
            ["not", "a", "prompt"],
            {"text": "missing id"},
            "worker@example.com case-123456789 raw value",
        ]
    }), encoding="utf-8")

    assert hv.load_corpus(path) == {
        "p1": {"text": "worker msg", "category": "cat", "difficulty": "hard"},
        "p3": {"text": "safe worker msg", "category": "unknown", "difficulty": "unknown"},
    }

    path.write_text(json.dumps({"prompts": {"p2": {"text": "not a list"}}}), encoding="utf-8")
    assert hv.load_corpus(path) == {}


def test_build_items_skips_non_object_responses():
    items = hv.build_items(
        _responses()[:1] + ["worker@example.com case-123456789 raw value"],
        _CORPUS,
        _GRADER,
    )

    assert len(items) == 1
    assert "worker@example.com" not in json.dumps(items)


def test_build_items_requires_string_prompt_and_response_text():
    responses = [
        {"prompt_id": "p1", "model": "m", "arm": "baseline", "response": {"raw": "worker@example.com"}},
        {"prompt_id": "p2", "model": "m", "arm": "baseline", "response": "safe reply"},
    ]
    corpus = {
        "p1": {"text": "safe prompt", "category": "cat", "difficulty": "hard"},
        "p2": {"text": {"raw": "case-123456789"}, "category": "cat", "difficulty": "hard"},
    }
    grader = {("p1", "m", "baseline"): 4.0, ("p2", "m", "baseline"): 5.0}

    items = hv.build_items(responses, corpus, grader)

    assert items == []
    assert "worker@example.com" not in json.dumps(items)
    assert "case-123456789" not in json.dumps(items)


def test_stratified_sample_is_seeded_and_blinded():
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    a = hv.stratified_sample(items, per_stratum=1, seed=13)
    b = hv.stratified_sample(hv.build_items(_responses(), _CORPUS, _GRADER), per_stratum=1, seed=13)
    assert [x["item_id"] for x in a] == [x["item_id"] for x in b]    # seeded -> reproducible
    assert all(x["item_id"].startswith("HV-") for x in a)


def test_main_export_console_redacts_sensitive_paths(tmp_path, monkeypatch, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    items = hv.build_items(_responses()[:2], _CORPUS, _GRADER)
    monkeypatch.setattr(hv, "_read_jsonl", lambda path: [])
    monkeypatch.setattr(hv, "load_corpus", lambda: {})
    monkeypatch.setattr(hv, "load_grader_scores", lambda: {})
    monkeypatch.setattr(hv, "build_items", lambda responses, corpus, grader: items)
    monkeypatch.setattr(
        hv,
        "export",
        lambda picked: (sensitive_dir / "rating_sheet.md", sensitive_dir / "key.json"),
    )

    rc = hv.main(["--per-stratum", "1", "--seed", "7"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "rater sheet -> external" in captured.err
    assert "hidden key  -> external" in captured.err
    assert "manifest    -> reports/human_validation/sample_manifest.json" in captured.err
    assert str(tmp_path) not in captured.err
    assert "worker@example.com" not in captured.err
    assert "case-123456789" not in captured.err


def test_export_blinds_arm_in_sheet_but_keeps_it_in_key(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=2, seed=7)
    sheet, key = hv.export(picked, out_dir=tmp_path)
    sheet_txt = sheet.read_text(encoding="utf-8")
    assert "expert_score" in sheet_txt and "rate this" in sheet_txt.lower()
    assert "Scenario prompt" in sheet_txt and "Worker's message" not in sheet_txt
    assert "harnessed" not in sheet_txt and "baseline" not in sheet_txt   # rater is blinded
    keymap = json.loads(key.read_text(encoding="utf-8"))
    assert keymap and all("arm" in v and "grader_score" in v for v in keymap.values())  # key has the truth
    manifest = json.loads((tmp_path / hv.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["item_count"] == len(picked)
    assert manifest["rater_facing_privacy_scan"]["ok"] is True
    assert manifest["hidden_key"]["metadata_only"] is True
    assert "prompt_text" not in manifest["hidden_key"]["fields_present"]
    assert "response" not in manifest["hidden_key"]["fields_present"]
    assert manifest["safe_for_expert_review"] is True


def test_export_redacts_obvious_sensitive_text_in_rating_sheet(tmp_path):
    picked = [{
        "item_id": "HV-001",
        "prompt_id": "p1",
        "model": "m",
        "arm": "baseline",
        "category": "cat",
        "difficulty": "hard",
        "grader_score": 4.0,
        "prompt_text": r"Email worker@example.com, call +1 202 555 0199, read C:\cases\case.txt. ```break fence```",
        "response": "The case number 123456789 should not be copied into expert sheets.",
    }]

    sheet, key = hv.export(picked, out_dir=tmp_path)
    sheet_txt = sheet.read_text(encoding="utf-8")
    key_txt = key.read_text(encoding="utf-8")

    assert "[redacted-email]" in sheet_txt
    assert "[redacted-phone]" in sheet_txt
    assert "[redacted-path]" in sheet_txt
    assert "[redacted-number]" in sheet_txt
    assert "worker@example.com" not in sheet_txt
    assert "+1 202 555 0199" not in sheet_txt
    assert "C:\\cases" not in sheet_txt
    assert "case.txt" not in sheet_txt
    assert "123456789" not in sheet_txt
    assert "```break fence```" not in sheet_txt
    assert "` ` `break fence` ` `" in sheet_txt
    assert sheet_txt.count("```") == 4
    assert "worker@example.com" not in key_txt
    manifest = json.loads((tmp_path / hv.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["rater_facing_privacy_scan"]["ok"] is True
    assert manifest["safe_for_expert_review"] is True


def test_export_manifest_flags_tampered_rater_facing_artifact(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=1, seed=7)
    sheet, key = hv.export(picked, out_dir=tmp_path)
    sheet.write_text("worker@example.com should not be in the rater sheet", encoding="utf-8")

    manifest_path = hv._write_export_manifest(picked, tmp_path, sheet, key)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["rater_facing_privacy_scan"]["ok"] is False
    assert manifest["rater_facing_privacy_scan"]["rating_sheet"]["email_count"] == 1
    assert manifest["safe_for_expert_review"] is False


def test_validate_export_accepts_clean_package(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=1, seed=7)
    hv.export(picked, out_dir=tmp_path)

    result = hv.validate_export(tmp_path)

    assert result["ok"] is True
    assert result["issues"] == []
    assert result["item_count"] == len(picked)
    assert result["ratings_blank_item_count"] == len(picked)
    assert result["manifest_item_count"] == len(picked)
    assert result["rater_facing_privacy_ok"] is True
    assert result["hidden_key_metadata_only"] is True
    assert result["safe_for_expert_review"] is True


def test_validate_export_rejects_tampered_rater_sheet(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=1, seed=7)
    hv.export(picked, out_dir=tmp_path)
    (tmp_path / "rating_sheet.md").write_text("Contact worker@example.com", encoding="utf-8")

    result = hv.validate_export(tmp_path)

    assert result["ok"] is False
    assert "rater_facing_privacy_scan_failed" in result["issues"]
    assert result["safe_for_expert_review"] is False


def test_validate_export_rejects_blank_key_item_id_mismatch(tmp_path):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=1, seed=7)
    hv.export(picked, out_dir=tmp_path)
    with open(tmp_path / "ratings_blank.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-999", ""])

    result = hv.validate_export(tmp_path)

    assert result["ok"] is False
    assert "ratings_blank_hidden_key_item_id_mismatch" in result["issues"]
    assert "manifest_blank_count_mismatch" in result["issues"]


def test_main_validate_reports_safe_package(tmp_path, monkeypatch, capsys):
    items = hv.build_items(_responses(), _CORPUS, _GRADER)
    picked = hv.stratified_sample(items, per_stratum=1, seed=7)
    hv.export(picked, out_dir=tmp_path)
    monkeypatch.setattr(hv, "OUT_DIR", tmp_path)

    rc = hv.main(["--validate"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["ok"] is True
    assert "safe for expert review" in captured.err


def test_main_validate_fails_closed_on_missing_manifest(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hv, "OUT_DIR", tmp_path)

    rc = hv.main(["--validate"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 1
    assert payload["ok"] is False
    assert "manifest_missing_or_malformed" in payload["issues"]
    assert "not safe for expert review" in captured.err


def test_key_metadata_summary_rejects_raw_text_fields(tmp_path):
    key = {
        "HV-001": {
            "grader_score": 4.0,
            "response": "raw reply from worker@example.com",
        }
    }
    key_path = tmp_path / "key.json"
    key_path.write_text(json.dumps(key), encoding="utf-8")

    summary = hv._key_metadata_summary(key_path)

    assert summary["metadata_only"] is False
    assert summary["raw_text_fields"] == ["response"]
    assert summary["obvious_contact_or_path_scan"]["email_count"] == 1
    assert summary["ok"] is False


def test_export_rejects_unsafe_item_ids_before_writing_reviewer_artifacts(tmp_path):
    picked = [{
        "item_id": "=cmd|' /C calc'!A0",
        "prompt_id": "p1",
        "model": "m",
        "arm": "baseline",
        "category": "cat",
        "difficulty": "hard",
        "grader_score": 4.0,
        "prompt_text": "worker msg",
        "response": "AI reply",
    }]

    with pytest.raises(ValueError, match="unsafe human-validation item_id"):
        hv.export(picked, out_dir=tmp_path)

    assert not (tmp_path / "rating_sheet.md").exists()
    assert not (tmp_path / "ratings_blank.csv").exists()
    assert not (tmp_path / "key.json").exists()
    assert not (tmp_path / hv.MANIFEST_NAME).exists()


def test_spearman_and_correlate(tmp_path):
    assert abs(hv._spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    # build a key + a ratings csv where human tracks grader -> spearman ~ 1
    key = {"HV-001": {"prompt_id": "p1", "model": "m", "arm": "baseline", "grader_score": 4.0},
           "HV-002": {"prompt_id": "p1", "model": "m", "arm": "harnessed", "grader_score": 8.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-001", "5"]); w.writerow(["HV-002", "9"])
    res = hv.correlate(tmp_path / "r.csv", key_path=tmp_path / "key.json")
    assert res["n"] == 2 and res["spearman"] == 1.0
    assert res["n_ratings"] == 2 and res["n_invalid_scores"] == 0


def test_correlate_ignores_invalid_and_out_of_range_scores(tmp_path):
    key = {"HV-001": {"grader_score": 4.0}, "HV-002": {"grader_score": 8.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-001", "5"])
        w.writerow(["HV-002", "11"])
        w.writerow(["HV-002", "-1"])
        w.writerow(["HV-002", "not-a-number"])
        w.writerow(["HV-002", ""])
    res = hv.correlate(tmp_path / "r.csv", key_path=tmp_path / "key.json")
    assert res["n"] == 1 and res["n_ratings"] == 1
    assert res["n_invalid_scores"] == 3
    assert res["mean_human"] == 5.0


def test_correlate_counts_malformed_key_rows_without_crashing(tmp_path):
    key = {
        "HV-001": {},
        "HV-002": {"grader_score": "not-a-number"},
        "HV-003": {"grader_score": 7.0},
    }
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-001", "4"])
        w.writerow(["HV-002", "5"])
        w.writerow(["HV-003", "6"])

    res = hv.correlate(tmp_path / "r.csv", key_path=tmp_path / "key.json")

    assert res["n"] == 1
    assert res["n_ratings"] == 1
    assert res["n_invalid_key_rows"] == 2
    assert res["mean_grader"] == 7.0


def test_correlate_handles_non_object_key_without_crashing(tmp_path):
    (tmp_path / "key.json").write_text(json.dumps(["not", "a", "key"]), encoding="utf-8")
    with open(tmp_path / "r.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "expert_score"])
        w.writerow(["HV-001", "5"])

    res = hv.correlate(tmp_path / "r.csv", key_path=tmp_path / "key.json")

    assert res["n"] == 0
    assert res["n_ratings"] == 0
    assert res["n_invalid_scores"] == 0
    assert res["n_invalid_key_rows"] == 0


def test_main_correlate_fails_when_no_valid_scores(tmp_path, monkeypatch, capsys):
    key = {"HV-001": {"grader_score": 4.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "blank.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"]); w.writerow(["HV-001", ""])
    monkeypatch.setattr(hv, "OUT_DIR", tmp_path)

    rc = hv.main(["--correlate", str(tmp_path / "blank.csv")])
    captured = capsys.readouterr()

    assert rc == 1
    assert json.loads(captured.out)["n"] == 0
    assert "no valid expert scores found" in captured.err


def test_main_correlate_fails_when_only_one_valid_item(tmp_path, monkeypatch, capsys):
    key = {"HV-001": {"grader_score": 4.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "one.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score"]); w.writerow(["HV-001", "5"])
    monkeypatch.setattr(hv, "OUT_DIR", tmp_path)

    rc = hv.main(["--correlate", str(tmp_path / "one.csv")])
    captured = capsys.readouterr()

    assert rc == 1
    assert json.loads(captured.out)["n"] == 1
    assert "at least two valid scored items" in captured.err


def test_correlate_supports_wide_multi_expert_scores(tmp_path):
    key = {f"HV-00{i}": {"grader_score": float(i)} for i in range(1, 4)}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "wide.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_score_a", "expert_score_b"])
        w.writerow(["HV-001", "1", "2"])
        w.writerow(["HV-002", "2", "3"])
        w.writerow(["HV-003", "3", "4"])
    res = hv.correlate(tmp_path / "wide.csv", key_path=tmp_path / "key.json")
    assert res["n"] == 3 and res["n_ratings"] == 6
    assert res["n_experts"] == 2 and res["n_multi_rated_items"] == 3
    assert res["spearman"] == 1.0
    assert res["inter_expert_pairwise_spearman"] == 1.0


def test_correlate_ignores_wide_note_columns(tmp_path):
    key = {"HV-001": {"grader_score": 1.0}, "HV-002": {"grader_score": 2.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "wide_notes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "expert_score_a", "expert_score_notes", "expert_score_b_comment"])
        w.writerow(["HV-001", "1", "clear trafficking indicators", "comment text"])
        w.writerow(["HV-002", "2", "needs stronger citation", "another comment"])

    res = hv.correlate(tmp_path / "wide_notes.csv", key_path=tmp_path / "key.json")

    assert res["n"] == 2
    assert res["n_ratings"] == 2
    assert res["n_invalid_scores"] == 0
    assert res["spearman"] == 1.0


def test_correlate_supports_long_multi_expert_scores(tmp_path):
    key = {"HV-001": {"grader_score": 1.0}, "HV-002": {"grader_score": 2.0}}
    (tmp_path / "key.json").write_text(json.dumps(key), encoding="utf-8")
    with open(tmp_path / "long.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["item_id", "expert_id", "expert_score"])
        w.writerow(["HV-001", "r1", "1"])
        w.writerow(["HV-002", "r1", "2"])
        w.writerow(["HV-001", "r2", "2"])
        w.writerow(["HV-002", "r2", "3"])
    res = hv.correlate(tmp_path / "long.csv", key_path=tmp_path / "key.json")
    assert res["n_ratings"] == 4 and res["n_experts"] == 2
    assert res["inter_expert_pairwise_spearman"] == 1.0
