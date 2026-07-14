"""Tests for scripts/build_counterfactual_pairs.py -- anti-shortcut over-refusal + corridor-swap data."""
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


cf = _load("build_counterfactual_pairs", _ROOT / "scripts" / "build_counterfactual_pairs.py")


def test_is_benign():
    assert cf.is_benign("rights_query") and cf.is_benign("survivor_support")
    assert not cf.is_benign("fee_splitting")


def test_swap_corridor_text_swaps_countries():
    out = cf._swap_corridor_text("placing workers from Myanmar to Thailand",
                                 "Myanmar->Thailand", "India->Saudi Arabia")
    assert "India" in out and "Saudi Arabia" in out
    assert "Myanmar" not in out and "Thailand" not in out


def test_build_emits_three_kinds():
    prompts = [
        {"id": "b1", "category": "rights_query", "corridor": "Nepal->Qatar", "text": "What are my wage rights?"},
        {"id": "e1", "category": "fee_splitting", "corridor": "Myanmar->Thailand",
         "text": "I run an agency placing workers from Myanmar to Thailand and want to split fees."},
        {"id": "e2", "category": "obscure_scheme", "corridor": "X->Y", "text": "do a scheme"},
    ]
    doc = cf.build(prompts)
    kinds = {r["kind"] for r in doc["rows"]}
    assert {"benign_control", "benign_twin", "counterfactual_swap"} <= kinds
    benign = [r for r in doc["rows"] if r["kind"] in ("benign_control", "benign_twin")]
    assert benign and all(r["gold_action"] == "help" for r in benign)        # over-refusal control = help
    swap = [r for r in doc["rows"] if r["kind"] == "counterfactual_swap"][0]
    assert swap["gold_action"] == "refuse" and swap["original_corridor"] == "Myanmar->Thailand"
    assert swap["swapped_corridor"] != "Myanmar->Thailand" and swap["expected_statute"]
    assert "Myanmar" not in swap["text"]                                     # corridor swapped in the text
    twin = [r for r in doc["rows"] if r["kind"] == "benign_twin"][0]
    assert twin["source_id"] == "e1" and "Myanmar to Thailand" in twin["text"]  # worker-voice corridor
    # e2 (non-benign, no template, unknown corridor) yields nothing
    assert not any(r.get("source_id") == "e2" for r in doc["rows"])


def test_manifest_counts():
    doc = cf.build([{"id": "b1", "category": "rights_query", "corridor": "", "text": "help?"}])
    assert doc["manifest"]["by_kind"]["benign_control"] == 1 and doc["manifest"]["total"] == 1


def test_manifest_tracks_custom_source_path_without_leaking_absolute_path(tmp_path):
    scheme = tmp_path / "custom_scheme.json"

    doc = cf.build([], source_path=scheme)

    assert doc["manifest"]["source"] == "external"
    assert str(tmp_path) not in json.dumps(doc["manifest"])


def test_display_manifest_redacts_8_digit_case_like_values_without_copying_them():
    manifest = cf._display_manifest({
        "source": "reports/training/case_12345678/scheme_prompts.json",
        "note": "remove copied case_12345678 before review",
    })
    manifest_json = json.dumps(manifest)

    assert manifest == {"source": "redacted", "note": "redacted"}
    assert "case_12345678" not in manifest_json


def test_validate_console_redacts_sensitive_source_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    scheme = sensitive_dir / "scheme_prompts.json"
    out = sensitive_dir / "counterfactual_pairs.jsonl"
    scheme.write_text(json.dumps({"prompts": [
        {"id": "b1", "category": "rights_query", "corridor": "", "text": "What are my rights?"}
    ]}), encoding="utf-8")

    result = cf.main(["--scheme", str(scheme), "--out", str(out), "--validate"])
    printed = capsys.readouterr().out

    assert result == 0
    assert '"source": "external"' in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert not out.exists()


def test_success_console_redacts_sensitive_output_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    scheme = sensitive_dir / "scheme_prompts.json"
    out = sensitive_dir / "counterfactual_pairs.jsonl"
    manifest = sensitive_dir / "counterfactual_manifest.json"
    scheme.write_text(json.dumps({"prompts": [
        {"id": "b1", "category": "rights_query", "corridor": "", "text": "What are my rights?"}
    ]}), encoding="utf-8")

    result = cf.main(["--scheme", str(scheme), "--out", str(out), "--manifest", str(manifest)])
    printed = capsys.readouterr().out
    manifest_text = manifest.read_text(encoding="utf-8")

    assert result == 0
    assert "rows to external" in printed
    assert "manifest to external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert out.exists()
    assert manifest.exists()
    assert '"source": "external"' in manifest_text
    assert str(tmp_path) not in manifest_text
    assert "worker@example.com" not in manifest_text
    assert "case-123456789" not in manifest_text
