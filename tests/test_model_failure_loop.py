"""Tests for scripts/model_failure_loop.py.

These keep the orchestration layer offline while checking privacy-safe logging.
"""
from __future__ import annotations

import io
import importlib.util
import json
import sys
import types
import urllib.error
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mfl = _load("model_failure_loop", _ROOT / "scripts" / "model_failure_loop.py")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_run_script_redacts_display_args_but_preserves_subprocess_args(tmp_path, monkeypatch, capsys):
    raw_out = tmp_path / "worker@example.com-case-123456789" / "out.jsonl"
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(mfl, "_venv_python", lambda: str(tmp_path / "venv" / "python.exe"))
    monkeypatch.setattr(mfl.subprocess, "run", fake_run)

    assert mfl.run_script("model_failure_judge.py", [
        "--out", str(raw_out),
        "--judge-model", "judge@example.com-case-987654321",
    ]) == 0

    printed = capsys.readouterr().out
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert "judge@example.com" not in printed
    assert "redacted" in printed
    assert str(raw_out) in calls[0][0]


def test_dry_run_console_redacts_sensitive_paths_and_model_labels(tmp_path, monkeypatch, capsys):
    out_dir = tmp_path / "worker@example.com-case-123456789"
    responses = out_dir / "responses.jsonl"
    report = out_dir / "report.md"
    sensitive_model = "worker@example.com-case-123456789"
    sensitive_judge = "judge@example.com-case-987654321"
    _write_jsonl(responses, [{
        "ok": True,
        "model": sensitive_model,
        "prompt_id": "p1",
        "response": "This is a response.",
    }])
    monkeypatch.setattr(mfl, "_git_sha", lambda: "abc1234")
    monkeypatch.setattr(mfl, "_venv_python", lambda: str(tmp_path / "venv" / "python.exe"))
    monkeypatch.setattr(mfl, "resolve_provider", lambda requested: ("test-provider", "live"))
    monkeypatch.setitem(mfl.PROVIDERS, "test-provider", {
        "base_url": "https://example.test/v1/chat/completions",
        "key_env": "TEST_KEY",
        "gen_models": [sensitive_model],
        "judge_model": sensitive_judge,
        "probe_model": "probe",
    })

    assert mfl.main([
        "--provider", "test-provider",
        "--run-tag", "worker@example.com-case-123456789",
        "--out-dir", str(out_dir),
        "--responses", str(responses),
        "--report-out", str(report),
        "--dry-run",
        "--limit", "1",
    ]) == 0

    printed = capsys.readouterr().out
    assert "worker@example.com" not in printed
    assert "judge@example.com" not in printed
    assert "case-123456789" not in printed
    assert str(tmp_path) not in printed
    assert "run_tag=redacted" in printed
    assert "judge_model=redacted" in printed
    assert "report=external" in printed
    assert "checkpoint -> external" in printed


def test_write_checkpoint_redacts_sensitive_state_without_merging_counts(tmp_path, capsys):
    checkpoint = tmp_path / "loop_state.json"
    raw_model_a = "worker@example.com-case-123456789"
    raw_model_b = "worker2@example.com-case-987654321"
    raw_report = tmp_path / "worker@example.com-case-123456789" / "report.md"

    mfl.write_checkpoint(checkpoint, {
        "provider": "openrouter",
        "base_url": "https://example.test/v1/chat/completions?api_key=secret",
        "run_tag": raw_model_a,
        "gen_models": ["openai/gpt-4o", raw_model_a, raw_model_b],
        "judge_model": "anthropic/claude-3.7-sonnet",
        "gen_counts": {
            "openai/gpt-4o": {"ok": 2, "err": 0},
            raw_model_a: {"ok": 1, "err": 0},
            raw_model_b: {"ok": 0, "err": 1},
        },
        "gen_gaps": [raw_model_a, raw_model_b],
        "report": str(raw_report),
    })

    printed = capsys.readouterr().out
    text = checkpoint.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert "checkpoint -> external" in printed
    assert "worker@example.com" not in text
    assert "worker2@example.com" not in text
    assert "case-123456789" not in text
    assert "case-987654321" not in text
    assert str(tmp_path) not in text
    assert "api_key=secret" not in text
    assert payload["provider"] == "openrouter"
    assert payload["base_url"] == "redacted"
    assert payload["run_tag"] == "redacted"
    assert payload["gen_models"] == ["openai/gpt-4o", "redacted", "redacted"]
    assert payload["gen_gaps"] == ["redacted", "redacted"]
    assert set(payload["gen_counts"]) == {"openai/gpt-4o", "redacted", "redacted_2"}
    assert payload["gen_counts"]["redacted"]["ok"] == 1
    assert payload["gen_counts"]["redacted_2"]["err"] == 1
    assert payload["report"] == "external"


def test_provider_probe_redacts_sensitive_error_details(monkeypatch, capsys):
    provider = "worker@example.com-provider-123456789"
    raw_body = (
        b'{"error":"token=sk-abcdefghijklmnopqrstuvwxyz123456 sent by worker@example.com '
        b'from C:\\Users\\Taylor\\case-123456789.txt"}'
    )
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setitem(mfl.PROVIDERS, provider, {
        "base_url": "https://example.test/v1/chat/completions",
        "key_env": "MODEL_FAILURE_TEST_KEY",
        "gen_models": ["model-a"],
        "judge_model": "judge-a",
        "probe_model": "probe-a",
    })

    def fake_urlopen(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://example.test/v1/chat/completions",
            401,
            "Unauthorized",
            {},
            io.BytesIO(raw_body),
        )

    monkeypatch.setattr(mfl.urllib.request, "urlopen", fake_urlopen)

    live, detail = mfl.probe_provider(provider)
    assert live is False
    assert "HTTP 401" in detail
    assert "worker@example.com" not in detail
    assert "abcdefghijklmnopqrstuvwxyz123456" not in detail
    assert "C:\\Users\\Taylor" not in detail
    assert "case-123456789" not in detail
    assert "[redacted-email]" in detail
    assert "[redacted-secret]" in detail

    try:
        mfl.resolve_provider(provider)
    except SystemExit as exc:
        assert "worker@example.com" not in str(exc)
        assert "abcdefghijklmnopqrstuvwxyz123456" not in str(exc)
    printed = capsys.readouterr().out
    assert "probe redacted" in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_loop_validation_skips_malformed_and_unjoinable_rows(tmp_path):
    responses = tmp_path / "responses.jsonl"
    judge = tmp_path / "judge.jsonl"
    responses.write_text(
        "\n".join([
            json.dumps({
                "ok": True,
                "model": "model-a",
                "prompt_id": "probe-1",
                "response": "This is a usable response.",
            }),
            json.dumps({
                "ok": False,
                "model": "model-b",
                "prompt_id": "probe-1",
                "error": "rate_limit",
            }),
            "{not-json",
            json.dumps(["not", "an", "object"]),
            json.dumps({
                "ok": True,
                "prompt_id": "probe-2",
                "response": "Missing model should not crash count_responses.",
            }),
            json.dumps({
                "ok": True,
                "model": "model-c",
                "response": "Missing prompt_id should not inflate judge total.",
            }),
            json.dumps({
                "ok": True,
                "model": "model-d",
                "prompt_id": "probe-3",
                "response": {"private": "worker@example.com"},
            }),
            json.dumps({
                "ok": True,
                "model": {"private": "worker@example.com"},
                "prompt_id": "probe-4",
                "response": "Structured model should be ignored.",
            }),
            json.dumps({
                "ok": True,
                "model": "model-e",
                "prompt_id": ["probe-5"],
                "response": "Structured prompt_id should not count as usable.",
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    judge.write_text(
        "\n".join([
            json.dumps({
                "model": "model-a",
                "prompt_id": "probe-1",
                "dimension": "sense_resolution",
                "verdict": "PASS",
            }),
            json.dumps({
                "model": "model-a",
                "prompt_id": "probe-1",
                "dimension": "legal_grounding",
                "verdict": "ERROR",
            }),
            "{not-json",
            json.dumps(["not", "an", "object"]),
            json.dumps({"prompt_id": "probe-1", "dimension": "sense_resolution", "verdict": "FAIL"}),
            json.dumps({"model": "model-a", "dimension": "sense_resolution", "verdict": "UNPARSED"}),
            json.dumps({
                "model": "model-z",
                "prompt_id": "probe-z",
                "dimension": "sense_resolution",
                "verdict": "PASS",
            }),
            json.dumps({
                "model": "model-a",
                "prompt_id": {"private": "worker@example.com"},
                "dimension": "sense_resolution",
                "verdict": "PASS",
            }),
        ]) + "\n",
        encoding="utf-8",
    )

    assert mfl.count_responses(responses) == {
        "model-a": {"ok": 1, "err": 0},
        "model-b": {"ok": 0, "err": 1},
        "model-c": {"ok": 0, "err": 1},
        "model-d": {"ok": 0, "err": 1},
        "model-e": {"ok": 0, "err": 1},
    }
    assert mfl.gen_gaps(responses, ["model-a", "model-b", "model-c"], 1) == ["model-b", "model-c"]
    coverage = mfl.judge_coverage(responses, judge, ["sense_resolution", "legal_grounding"])
    assert coverage == {
        "done": 1,
        "total": 2,
        "errors": 1,
        "complete": False,
        "pct": 0.5,
    }
