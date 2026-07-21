"""Tests for the DueCare corpus exporter."""
from __future__ import annotations

import json

import pandas as pd

from duecare.kit.corpus import describe, export_corpus


def test_describe_reports_schema_and_null_rates():
    df = pd.DataFrame({"a": [1, 2, None, 4], "b": ["x", "y", "z", "w"]})
    d = describe(df)
    assert d["n_rows"] == 4
    assert d["n_columns"] == 2
    assert set(d["columns"]) == {"a", "b"}
    assert d["null_rates"]["a"] == 0.25
    assert d["null_rates"]["b"] == 0.0


def _write_sources(tmp_path):
    csv = tmp_path / "grades.csv"
    pd.DataFrame({"model": ["gemma4:31b", "glm-5.2"], "score_0_100": [89.0, 70.0]}).to_csv(csv, index=False)
    jsonl = tmp_path / "panel.jsonl"
    with jsonl.open("w", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(json.dumps({"prompt_id": f"P{i}", "arm": "baseline"}) + "\n")
    return csv, jsonl


def test_export_corpus_writes_manifest_and_readme(tmp_path):
    csv, jsonl = _write_sources(tmp_path)
    out = export_corpus(tmp_path / "corpus", [csv, jsonl], corpus_name="test corpus")
    manifest_path = out / "MANIFEST.json"
    readme_path = out / "README.md"
    assert manifest_path.exists() and readme_path.exists()
    assert (out / "data" / "grades.csv").exists()
    assert (out / "data" / "panel.jsonl").exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["corpus"] == "test corpus"
    assert manifest["n_files"] == 2
    names = {f["name"]: f for f in manifest["files"]}
    assert names["grades.csv"]["rows"] == 2
    assert names["grades.csv"]["columns"] == ["model", "score_0_100"]
    assert names["panel.jsonl"]["rows"] == 3
    for entry in manifest["files"]:
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
        assert entry["license"]
        assert entry["description"]

    readme = readme_path.read_text(encoding="utf-8")
    assert "test corpus" in readme
    assert "grades.csv" in readme


def test_export_corpus_missing_source_raises(tmp_path):
    try:
        export_corpus(tmp_path / "corpus", [tmp_path / "nope.csv"])
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError for a missing source file")
