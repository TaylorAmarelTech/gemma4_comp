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


def test_prep_tops_up_after_open_model_overlap(tmp_path, monkeypatch):
    import duecare.chat.harness as harness_mod
    import duecare.chat.harness_lift as lift_mod

    bench = tmp_path / "bench"
    bench.mkdir()
    (bench / "prompts.json").write_text(json.dumps({"prompts": [
        {"id": "p1", "text": "one"},
        {"id": "p2", "text": "two"},
        {"id": "p3", "text": "three"},
    ]}), encoding="utf-8")
    open_responses = tmp_path / "open.responses.jsonl"
    open_responses.write_text(
        json.dumps({"prompt_id": "p2"}) + "\n" +
        json.dumps({"prompt_id": "p2"}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cand, "_BENCH", bench)
    monkeypatch.setattr(cand, "_BATCH_DIR", tmp_path / "batches")
    monkeypatch.setenv("LIFT_OPEN_RESPONSES", str(open_responses))
    monkeypatch.setattr(harness_mod, "default_harness",
                        lambda: {"grep_call": object(), "rag_call": object()})
    monkeypatch.setattr(lift_mod, "build_harness_preamble",
                        lambda text, **_kw: {"preamble": "PRE:" + text})

    assert cand.prep("prompts.json", 3, batch_size=10) == 1
    batch = json.loads((tmp_path / "batches" / "batch_0000.json").read_text(encoding="utf-8"))
    baseline_ids = [i["prompt_id"] for i in batch["items"] if i["arm"] == "baseline"]
    assert baseline_ids == ["p2", "p1", "p3"]
    harnessed = [i for i in batch["items"] if i["arm"] == "harnessed"]
    assert all(i["prompt"].startswith("PRE:") for i in harnessed)
