"""Tests for scripts/model_failure_study.py.

The generation CLI is exercised with a fake grader and fake API call.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mfs = _load("model_failure_study", _ROOT / "scripts" / "model_failure_study.py")


def _install_fake_grader(monkeypatch) -> None:
    duecare = types.ModuleType("duecare")
    chat = types.ModuleType("duecare.chat")
    harness = types.ModuleType("duecare.chat.harness")

    def grade_response_universal(_response, *, prompt_text):
        return {
            "pct_score": 90.0,
            "score_0_10": 9.0,
            "dimensions": [
                {
                    "id": "domain_sense_resolution",
                    "status": "PASS",
                    "score_0_10": 9.0,
                }
            ],
        }

    harness.grade_response_universal = grade_response_universal
    monkeypatch.setitem(sys.modules, "duecare", duecare)
    monkeypatch.setitem(sys.modules, "duecare.chat", chat)
    monkeypatch.setitem(sys.modules, "duecare.chat.harness", harness)


def test_load_prompts_skips_malformed_and_incomplete_jsonl_rows(tmp_path, monkeypatch):
    probes = tmp_path / "probes.jsonl"
    seeds = tmp_path / "seeds.jsonl"
    probes.write_text(
        "\n".join([
            json.dumps({
                "id": "probe-1",
                "text": "What does a worker bond mean?",
                "category": "equivocation",
                "metadata": {"ambiguous_term": "bond"},
            }),
            "{not-json",
            json.dumps(["not", "an", "object"]),
            json.dumps({"id": "missing-text"}),
            json.dumps({"id": ["worker@example.com"], "text": "structured id"}),
            json.dumps({"id": "structured-text", "text": {"case": "case-123456789"}}),
            json.dumps({
                "id": "probe-2",
                "text": "What is passport safekeeping?",
                "metadata": "not-a-dict",
                "category": {"private": "worker@example.com"},
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    seeds.write_text(
        "\n".join([
            json.dumps({"id": "seed-1", "text": "I paid a recruiter fee.", "category": "seed"}),
            "{not-json",
            json.dumps({"id": "missing-seed-text"}),
            json.dumps({"id": {"case": "case-123456789"}, "text": "structured seed id"}),
            json.dumps({"id": "seed-structured-text", "text": ["worker@example.com"]}),
        ]) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mfs, "PROBES", probes)
    monkeypatch.setattr(mfs, "SEEDS", seeds)

    prompts = mfs.load_prompts(include_seeds=True, limit=None)

    assert [prompt["id"] for prompt in prompts] == ["probe-1", "probe-2", "seed-1"]
    assert prompts[0]["ambiguous_term"] == "bond"
    assert prompts[1]["ambiguous_term"] == ""
    assert prompts[1]["category"] == ""
    assert prompts[2]["ambiguous_term"] == ""


def test_done_pairs_skips_non_string_resume_keys(tmp_path):
    out = tmp_path / "results.jsonl"
    out.write_text(
        "\n".join([
            json.dumps({"ok": True, "model": "model-a", "prompt_id": "probe-1"}),
            json.dumps({"ok": True, "model": {"private": "worker@example.com"}, "prompt_id": "probe-1"}),
            json.dumps({"ok": True, "model": "model-b", "prompt_id": ["probe-2"]}),
            json.dumps({"ok": False, "model": "model-c", "prompt_id": "probe-3"}),
        ]) + "\n",
        encoding="utf-8",
    )

    assert mfs._done_pairs(out) == {("model-a", "probe-1"), ("model-c", "probe-3")}
    assert mfs._done_pairs(out, only_ok=True) == {("model-a", "probe-1")}


def test_main_console_redacts_sensitive_labels_and_path_but_preserves_artifact(tmp_path, monkeypatch, capsys):
    model = "worker@example.com-case-123456789"
    prompt_id = "prompt@example.com-case-987654321"
    out = tmp_path / "worker@example.com-case-123456789" / "results.jsonl"
    _install_fake_grader(monkeypatch)
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfs, "load_prompts", lambda **_kwargs: [{
        "id": prompt_id,
        "text": "What does a worker bond mean?",
        "category": "synthetic",
        "ambiguous_term": "bond",
    }])
    monkeypatch.setattr(mfs, "call_chat", lambda *args, **kwargs: {
        "ok": True,
        "text": "This is debt-bondage framing.",
        "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        "error": None,
    })

    assert mfs.main([
        "--models", model,
        "--out", str(out),
        "--key-env", "MODEL_FAILURE_TEST_KEY",
        "--workers", "1",
    ]) == 0

    printed = capsys.readouterr().out
    assert out.exists()
    assert "redacted" in printed
    assert "Results appended to external" in printed
    assert str(tmp_path) not in printed
    assert model not in printed
    assert prompt_id not in printed

    record = json.loads(out.read_text(encoding="utf-8").strip())
    assert record["model"] == model
    assert record["prompt_id"] == prompt_id
    assert record["ok"] is True


def test_main_error_console_redacts_sensitive_error_but_preserves_artifact_error(tmp_path, monkeypatch, capsys):
    model = "worker@example.com-case-123456789"
    prompt_id = "prompt@example.com-case-987654321"
    raw_error = str(tmp_path / "worker@example.com-case-123456789" / "provider.log")
    out = tmp_path / "worker@example.com-case-123456789" / "results.jsonl"
    _install_fake_grader(monkeypatch)
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfs, "load_prompts", lambda **_kwargs: [{
        "id": prompt_id,
        "text": "What does a worker bond mean?",
        "category": "synthetic",
        "ambiguous_term": "bond",
    }])
    monkeypatch.setattr(mfs, "call_chat", lambda *args, **kwargs: {
        "ok": False,
        "text": "",
        "usage": {},
        "error": raw_error,
    })

    assert mfs.main([
        "--models", model,
        "--out", str(out),
        "--key-env", "MODEL_FAILURE_TEST_KEY",
        "--workers", "1",
    ]) == 0

    printed = capsys.readouterr().out
    assert "ERROR details redacted" in printed
    assert str(tmp_path) not in printed
    assert model not in printed
    assert prompt_id not in printed
    assert raw_error not in printed

    record = json.loads(out.read_text(encoding="utf-8").strip())
    assert record["error"] == raw_error


def test_main_missing_key_redacts_untrusted_key_env(capsys):
    assert mfs.main([
        "--models", "m",
        "--out", "out.jsonl",
        "--key-env", "worker@example.com",
    ]) == 2

    printed = capsys.readouterr().err
    assert "ERROR: redacted not set" in printed
    assert "worker@example.com" not in printed
