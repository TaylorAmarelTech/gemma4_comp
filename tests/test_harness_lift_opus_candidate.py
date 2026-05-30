"""Test the Opus-candidate ingest plumbing (no agents, no keys)."""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

cand = importlib.import_module("harness_lift_opus_candidate")


def test_ingest_folds_answers_with_model_tag_and_dedupes(tmp_path, monkeypatch):
    adir = tmp_path / "ans"
    adir.mkdir()
    resp = tmp_path / "cand.responses.jsonl"
    monkeypatch.setattr(cand, "_ANSWER_DIR", adir)
    monkeypatch.setattr(cand, "_RESPONSES", resp)
    monkeypatch.setattr(cand, "CAND_MODEL", "opus")
    (adir / "batch_0000.json").write_text(json.dumps({"responses": [
        {"prompt_id": "p1", "arm": "baseline", "response": "raw answer"},
        {"prompt_id": "p1", "arm": "harnessed", "response": "grounded answer with statute"},
    ]}), encoding="utf-8")

    n1 = cand.ingest()
    assert n1 == 2
    rows = [json.loads(x) for x in resp.read_text(encoding="utf-8").splitlines()]
    assert {r["arm"] for r in rows} == {"baseline", "harnessed"}
    assert all(r["model"] == "opus" for r in rows)
    assert rows[0]["chars"] == len("raw answer")

    # Re-ingest -> idempotent (same prompt_id|arm keys already present).
    assert cand.ingest() == 0
