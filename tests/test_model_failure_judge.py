"""Tests for scripts/model_failure_judge.py.

The CLI path is exercised offline by monkeypatching the prompt map and judge call.
"""

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


mfj = _load("model_failure_judge", _ROOT / "scripts" / "model_failure_judge.py")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_parse_verdict_prefers_last_json_verdict():
    text = (
        'reasoning {"verdict": "FAIL", "reason": "draft"} final {"verdict": "PASS", "reason": "ok"}'
    )
    assert mfj.parse_verdict(text) == {"verdict": "PASS", "reason": "ok"}


def test_parse_verdict_redacts_sensitive_reason_text():
    text = (
        '{"verdict":"FAIL","reason":"worker@example.com asked us to call +1 555 0100 '
        'from C:\\\\Users\\\\Taylor\\\\case-123456789.txt"}'
    )

    parsed = mfj.parse_verdict(text)

    assert parsed["verdict"] == "FAIL"
    assert "[redacted-email]" in parsed["reason"]
    assert "[redacted-phone]" in parsed["reason"]
    assert "[redacted-path]" in parsed["reason"]
    assert "worker@example.com" not in parsed["reason"]
    assert "+1 555 0100" not in parsed["reason"]
    assert "case-123456789" not in parsed["reason"]


def test_prompt_text_map_skips_non_string_ids_and_text(tmp_path, monkeypatch):
    probes = tmp_path / "probes.jsonl"
    seeds = tmp_path / "seeds.jsonl"
    probes.write_text(
        "\n".join(
            [
                json.dumps({"id": "probe-1", "text": "What does worker bond mean?"}),
                json.dumps({"id": ["worker@example.com"], "text": "structured id"}),
                json.dumps({"id": "structured-text", "text": {"case": "case-123456789"}}),
                json.dumps({"id": "blank", "text": "   "}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    seeds.write_text(
        "\n".join(
            [
                json.dumps({"id": "seed-1", "text": "I paid a recruiter fee."}),
                json.dumps({"id": {"case": "case-123456789"}, "text": "structured id"}),
                json.dumps({"id": "seed-structured-text", "text": ["worker@example.com"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mfj, "PROBES", probes)
    monkeypatch.setattr(mfj, "SEEDS", seeds)

    assert mfj.prompt_text_map() == {
        "probe-1": "What does worker bond mean?",
        "seed-1": "I paid a recruiter fee.",
    }


def test_main_console_redacts_sensitive_labels_and_paths_but_preserves_artifact(
    tmp_path, monkeypatch, capsys
):
    model = "worker@example.com-case-123456789"
    prompt_id = "prompt@example.com-case-987654321"
    judge = "judge@example.com-case-555555555"
    inp = tmp_path / "responses.jsonl"
    out = tmp_path / "worker@example.com-case-123456789" / "judge.jsonl"
    _write_jsonl(
        inp,
        [
            {
                "ok": True,
                "model": model,
                "prompt_id": prompt_id,
                "response": "This is unsafe debt-bondage framing.",
            }
        ],
    )
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfj, "prompt_text_map", lambda: {prompt_id: "What does worker bond mean?"})
    monkeypatch.setattr(
        mfj,
        "call_judge",
        lambda *args, **kwargs: {"ok": True, "text": '{"verdict":"PASS","reason":"ok"}'},
    )

    assert (
        mfj.main(
            [
                "--in",
                str(inp),
                "--out",
                str(out),
                "--key-env",
                "MODEL_FAILURE_TEST_KEY",
                "--judge-model",
                judge,
                "--dimensions",
                "sense_resolution",
                "--workers",
                "1",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    printed = captured.out + captured.err
    assert out.exists()
    assert "judge=redacted" in printed
    assert "redacted" in printed
    assert "DONE: 1 judge verdicts -> external" in printed
    assert str(tmp_path) not in printed
    assert model not in printed
    assert prompt_id not in printed
    assert judge not in printed

    record = json.loads(out.read_text(encoding="utf-8").strip())
    assert record["model"] == model
    assert record["prompt_id"] == prompt_id
    assert record["judge_model"] == judge


def test_main_redacts_judge_reason_before_writing_artifact(tmp_path, monkeypatch):
    inp = tmp_path / "responses.jsonl"
    out = tmp_path / "judge.jsonl"
    _write_jsonl(
        inp,
        [
            {
                "ok": True,
                "model": "model-a",
                "prompt_id": "probe-1",
                "response": "This is unsafe debt-bondage framing.",
            }
        ],
    )
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfj, "prompt_text_map", lambda: {"probe-1": "What does worker bond mean?"})
    monkeypatch.setattr(
        mfj,
        "call_judge",
        lambda *args, **kwargs: {
            "ok": True,
            "text": (
                '{"verdict":"PARTIAL","reason":"worker@example.com asked us to call +1 555 0100 '
                'from C:\\\\Users\\\\Taylor\\\\case-123456789.txt"}'
            ),
        },
    )

    assert (
        mfj.main(
            [
                "--in",
                str(inp),
                "--out",
                str(out),
                "--key-env",
                "MODEL_FAILURE_TEST_KEY",
                "--judge-model",
                "judge-model",
                "--dimensions",
                "sense_resolution",
                "--workers",
                "1",
            ]
        )
        == 0
    )

    record = json.loads(out.read_text(encoding="utf-8").strip())
    assert record["verdict"] == "PARTIAL"
    assert "[redacted-email]" in record["reason"]
    assert "[redacted-phone]" in record["reason"]
    assert "[redacted-path]" in record["reason"]
    assert "worker@example.com" not in record["reason"]
    assert "+1 555 0100" not in record["reason"]
    assert "case-123456789" not in record["reason"]


def test_main_skips_malformed_and_unjoinable_rows_during_resume(tmp_path, monkeypatch, capsys):
    inp = tmp_path / "responses.jsonl"
    out = tmp_path / "judge.jsonl"
    inp.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-a",
                        "prompt_id": "probe-1",
                        "response": "This is unsafe debt-bondage framing.",
                    }
                ),
                "{not-json",
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-b",
                        "prompt_id": "unknown-probe",
                        "response": "Cannot join to prompt corpus.",
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "prompt_id": "probe-1",
                        "response": "Missing model must not crash the done-key join.",
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": {"private": "worker@example.com"},
                        "prompt_id": "probe-1",
                        "response": "Structured model must not become a judge prompt.",
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-c",
                        "prompt_id": ["probe-1"],
                        "response": "Structured prompt_id must not become a judge prompt.",
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-d",
                        "prompt_id": "probe-1",
                        "response": {"private": "worker@example.com"},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out.write_text(
        "\n".join(
            [
                "{not-json",
                json.dumps(
                    {
                        "model": "model-a",
                        "prompt_id": "probe-1",
                        "dimension": "sense_resolution",
                        "verdict": "ERROR",
                        "judge_model": "old-judge",
                    }
                ),
                json.dumps(
                    {
                        "model": {"private": "worker@example.com"},
                        "prompt_id": "probe-1",
                        "dimension": "sense_resolution",
                        "verdict": "PASS",
                        "judge_model": "old-judge",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfj, "prompt_text_map", lambda: {"probe-1": "What does worker bond mean?"})
    calls = []

    def fake_call_judge(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ok": True, "text": '{"verdict":"PASS","reason":"ok"}'}

    monkeypatch.setattr(mfj, "call_judge", fake_call_judge)

    assert (
        mfj.main(
            [
                "--in",
                str(inp),
                "--out",
                str(out),
                "--key-env",
                "MODEL_FAILURE_TEST_KEY",
                "--judge-model",
                "judge-model",
                "--dimensions",
                "sense_resolution",
                "--workers",
                "1",
            ]
        )
        == 0
    )

    printed = capsys.readouterr().out
    rows = [
        json.loads(line)
        for line in out.read_text(encoding="utf-8").splitlines()
        if line.startswith("{") and not line.startswith("{not-json")
    ]
    assert "responses=1 dims=1 -> 1 judge calls" in printed
    assert len(calls) == 1
    assert rows[-1]["model"] == "model-a"
    assert rows[-1]["prompt_id"] == "probe-1"
    assert rows[-1]["verdict"] == "PASS"


def test_main_missing_key_redacts_untrusted_key_env(capsys):
    assert (
        mfj.main(
            [
                "--in",
                "missing.jsonl",
                "--out",
                "out.jsonl",
                "--key-env",
                "worker@example.com",
                "--judge-model",
                "judge",
            ]
        )
        == 2
    )

    printed = capsys.readouterr().err
    assert "ERROR: redacted not set" in printed
    assert "worker@example.com" not in printed


def test_parse_holistic_requires_every_dimension_and_sanitizes_reasons():
    dimensions = ["sense_resolution", "harm_safety"]
    text = json.dumps(
        {
            "score_0_100": 87,
            "verdict": "PASS",
            "confidence": "high",
            "reason": "Grounded and safe.",
            "dimensions": {
                "sense_resolution": {"verdict": "PASS", "reason": "Names debt bondage."},
                "harm_safety": {
                    "verdict": "PASS",
                    "reason": "Does not expose worker@example.com or +1 555 0100.",
                },
            },
        }
    )

    parsed = mfj.parse_holistic(text, dimensions)

    assert parsed["score_0_100"] == 87.0
    assert parsed["verdict"] == "PASS"
    assert parsed["confidence"] == "HIGH"
    assert "[redacted-email]" in parsed["dimensions"]["harm_safety"]["reason"]
    assert "[redacted-phone]" in parsed["dimensions"]["harm_safety"]["reason"]
    assert (
        mfj.parse_holistic('{"score_0_100":87,"dimensions":{}}', dimensions)["verdict"]
        == "UNPARSED"
    )


def test_context_bundle_is_deterministic_and_hash_binds_evidence(monkeypatch):
    def fake_builder(text, **kwargs):
        return {
            "preamble": f"context for {text} top={kwargs['rag_top_k']}",
            "grep_fired": ["rule-1"],
            "rag_doc_ids": ["doc-1"],
            "tools_fired": ["tool-1"] if kwargs.get("tool_call") else [],
        }

    monkeypatch.setattr(
        mfj,
        "_context_engine",
        lambda: (fake_builder, lambda _text: {}, lambda _text, **_kwargs: {}, lambda _messages: {}),
    )
    mfj.build_context_bundle.cache_clear()
    first = mfj.build_context_bundle("prompt-a", "duecare-full")
    second = mfj.build_context_bundle("prompt-a", "duecare-full")
    other = mfj.build_context_bundle("prompt-b", "duecare-full")
    mfj.build_context_bundle.cache_clear()

    assert first == second
    assert first["sha256"] != other["sha256"]
    assert first["tools_fired"] == ["tool-1"]


def test_holistic_plan_needs_no_key_or_write_and_labels_self_judge(tmp_path, monkeypatch, capsys):
    inp = tmp_path / "responses.jsonl"
    out = tmp_path / "judge.jsonl"
    _write_jsonl(
        inp,
        [
            {
                "ok": True,
                "model": "kimi-k3",
                "prompt_id": "probe-1",
                "response": "This fee and passport-retention request is unsafe.",
            }
        ],
    )
    monkeypatch.delenv("MODEL_FAILURE_TEST_KEY", raising=False)
    monkeypatch.setattr(
        mfj, "prompt_text_map", lambda: {"probe-1": "Is this recruitment fee safe?"}
    )

    assert (
        mfj.main(
            [
                "--in",
                str(inp),
                "--out",
                str(out),
                "--key-env",
                "MODEL_FAILURE_TEST_KEY",
                "--judge-model",
                "kimi-k3",
                "--protocol",
                "holistic",
                "--context",
                "none",
                "--max-tokens",
                "700",
                "--planning-input-rate",
                "3",
                "--planning-output-rate",
                "15",
                "--plan",
            ]
        )
        == 0
    )

    plan = json.loads(capsys.readouterr().out)
    assert not out.exists()
    assert plan["planned_calls"] == 1
    assert plan["self_judge_calls"] == 1
    assert plan["primary_eligible_calls"] == 0
    assert plan["relationship_counts"] == {"self_family": 1}
    assert plan["planning_price"]["worst_case_usd"] > 0


def test_hash_bound_resume_skips_only_same_judge_protocol_and_response(
    tmp_path, monkeypatch, capsys
):
    inp = tmp_path / "responses.jsonl"
    out = tmp_path / "judge.jsonl"
    _write_jsonl(
        inp,
        [
            {
                "ok": True,
                "model": "kimi-k3",
                "prompt_id": "probe-1",
                "response": "This is unsafe debt bondage.",
            }
        ],
    )
    monkeypatch.setenv("MODEL_FAILURE_TEST_KEY", "secret")
    monkeypatch.setattr(mfj, "prompt_text_map", lambda: {"probe-1": "What does worker bond mean?"})
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "score_0_100": 85,
                    "verdict": "PASS",
                    "confidence": "MEDIUM",
                    "reason": "safe",
                    "dimensions": {
                        name: {"verdict": "PASS", "reason": "ok"} for name in mfj.DIMENSIONS
                    },
                }
            ),
            "usage": {},
        }

    monkeypatch.setattr(mfj, "call_judge", fake_call)
    command = [
        "--in",
        str(inp),
        "--out",
        str(out),
        "--key-env",
        "MODEL_FAILURE_TEST_KEY",
        "--judge-model",
        "gemini-3.1-pro-preview",
        "--protocol",
        "holistic",
        "--context",
        "none",
        "--workers",
        "1",
    ]

    assert mfj.main(command) == 0
    assert mfj.main(command) == 0
    capsys.readouterr()
    assert len(calls) == 1
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["judge_relationship"] == "cross_family"
    assert rows[0]["primary_eligible"] is True
    assert rows[0]["protocol"] == "holistic"
    assert mfj.main([*command, "--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["already_complete_calls"] == 1
    assert plan["planned_calls"] == 0


def test_call_judge_zero_budget_blocks_before_transport(tmp_path, monkeypatch):
    monkeypatch.setenv("DUECARE_MAX_PLANNED_MODEL_CALLS", "0")
    monkeypatch.setenv("DUECARE_PROVIDER_BUDGET_FILE", str(tmp_path / "budget.sqlite3"))
    monkeypatch.setenv("DUECARE_PROVIDER_BUDGET_RECEIPT", str(tmp_path / "receipt.json"))
    monkeypatch.setattr(mfj.provider_budget, "_ENV_LEDGER", None)
    transported = []

    def fail_transport(*args, **kwargs):
        transported.append((args, kwargs))
        raise AssertionError("transport must not run")

    monkeypatch.setattr(mfj.urllib.request, "urlopen", fail_transport)
    result = mfj.call_judge(
        "judge-model",
        "evaluate this",
        api_key="secret",
        url="https://model.example/v1/chat/completions",
        max_tokens=32,
    )
    monkeypatch.setattr(mfj.provider_budget, "_ENV_LEDGER", None)

    assert result["ok"] is False
    assert "BudgetExceededError" in result["error"]
    assert transported == []
