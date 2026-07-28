"""Tests for scripts/model_failure_report.py.

Offline synthetic rows cover report rendering and privacy-safe CLI output.
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


mfr = _load("model_failure_report", _ROOT / "scripts" / "model_failure_report.py")


def _row(model: str = "model-a") -> dict:
    return {
        "ok": True,
        "model": model,
        "prompt_id": "probe-1",
        "ambiguous_term": "bond",
        "response": "This is a debt-bondage warning.",
        "grade": {
            "pct_score": 80.0,
            "domain_sense_resolution": {
                "applicable": True,
                "status": "PASS",
                "score_0_10": 8.0,
            },
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_render_redacts_sensitive_model_and_judge_labels():
    model = "worker@example.com-case-123456789"
    judge = "judge@example.com-case-987654321"
    md = mfr.render(
        [_row(model)],
        [
            {
                "model": model,
                "dimension": "sense_resolution",
                "verdict": "PASS",
                "judge_model": judge,
            }
        ],
    )

    assert model not in md
    assert judge not in md
    assert "`redacted`" in md


def test_render_redacts_sensitive_probe_metadata():
    row = _row("model-a")
    row["prompt_id"] = "worker@example.com-case-123456789"
    row["ambiguous_term"] = "bond | call +1 555 0100"

    md = mfr.render([row])

    assert "| `redacted` | redacted |" in md
    assert "worker@example.com" not in md
    assert "case-123456789" not in md
    assert "+1 555 0100" not in md
    assert "bond | call" not in md


def test_render_preserves_safe_probe_metadata():
    row = _row("model-a")
    row["prompt_id"] = "probe.debt-bondage-01"
    row["ambiguous_term"] = "debt bond"

    md = mfr.render([row])

    assert "| `probe.debt-bondage-01` | debt bond |" in md


def test_main_success_console_redacts_sensitive_output_path_and_model_label(tmp_path, capsys):
    model = "worker@example.com-case-123456789"
    inp = tmp_path / "input.jsonl"
    out = tmp_path / "worker@example.com-case-123456789" / "model_failure.md"
    _write_jsonl(inp, [_row(model)])

    assert mfr.main(["--in", str(inp), "--out", str(out)]) == 0

    captured = capsys.readouterr()
    md = out.read_text(encoding="utf-8")
    assert out.exists()
    assert "wrote external" in captured.out
    assert "redacted" in captured.out
    assert str(tmp_path) not in captured.out
    assert model not in captured.out
    assert model not in md


def test_main_missing_input_console_redacts_sensitive_input_path(tmp_path, capsys):
    inp = tmp_path / "worker@example.com-case-123456789" / "missing.jsonl"

    assert mfr.main(["--in", str(inp), "--out", str(tmp_path / "out.md")]) == 1

    printed = capsys.readouterr().err
    assert "no OK rows in external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_skips_malformed_jsonl_rows_and_judge_rows(tmp_path, capsys):
    inp = tmp_path / "results.jsonl"
    judge = tmp_path / "judge.jsonl"
    out = tmp_path / "report.md"
    inp.write_text(
        "\n".join(
            [
                json.dumps(_row("model-a")),
                "{not-json",
                json.dumps({"ok": True, "model": "model-b", "response": "missing grade"}),
                json.dumps(
                    {
                        "ok": True,
                        "model": {"private": "worker@example.com"},
                        "prompt_id": "probe-1",
                        "response": "Structured model should be skipped.",
                        "grade": _row()["grade"],
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-c",
                        "prompt_id": ["probe-1"],
                        "response": "Structured prompt_id should be skipped.",
                        "grade": _row()["grade"],
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-d",
                        "prompt_id": "probe-1",
                        "response": {"private": "worker@example.com"},
                        "grade": _row()["grade"],
                    }
                ),
                json.dumps(
                    {
                        "ok": True,
                        "model": "model-e",
                        "prompt_id": "probe-1",
                        "response": "Malformed grade should be skipped.",
                        "grade": {"domain_sense_resolution": ["not", "a", "dict"]},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    judge.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "model": "model-a",
                        "dimension": "sense_resolution",
                        "verdict": "PASS",
                        "judge_model": "judge-a",
                    }
                ),
                "{not-json",
                json.dumps(
                    {"dimension": "sense_resolution", "verdict": "FAIL", "judge_model": "judge-a"}
                ),
                json.dumps({"model": "model-a", "verdict": "FAIL", "judge_model": "judge-a"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert mfr.main(["--in", str(inp), "--judge", str(judge), "--out", str(out)]) == 0

    md = out.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert "1 responses, 1 models" in printed
    assert "| `model-a` | 100% (1/1) |" in md
    assert "| `model-a` | 100% (1/1) | — | — | — |" in md
    assert "model-b" not in md
    assert "model-c" not in md
    assert "model-d" not in md
    assert "model-e" not in md
    assert "worker@example.com" not in md


def test_holistic_cross_family_and_self_judges_stay_separate():
    base = {
        "model": "kimi-k3",
        "prompt_id": "probe-1",
        "protocol": "holistic",
        "dimension": "holistic",
        "dimensions": {
            "sense_resolution": {"verdict": "PASS"},
            "legal_grounding": {"verdict": "PARTIAL"},
            "harm_safety": {"verdict": "PASS"},
            "actionability": {"verdict": "FAIL"},
        },
    }
    judge_rows = [
        {
            **base,
            "judge_model": "gemini-3.1-pro-preview",
            "judge_relationship": "cross_family",
            "primary_eligible": True,
        },
        {
            **base,
            "judge_model": "kimi-k3",
            "judge_relationship": "self_family",
            "self_judge": True,
        },
    ]

    md = mfr.render([_row("kimi-k3")], judge_rows)

    assert "Cross-family contextual judge" in md
    assert "Same-family contextual self-judge (diagnostic)" in md
    assert "one structured call per response; directional pilot evidence" in md
    assert "Judge-to-judge agreement" in md
    assert "4/4 (100%)" in md
    assert "verdicts (definitive)" not in md.lower()
    assert "this is the credible verdict" not in md.lower()


def test_main_accepts_multiple_judge_files(tmp_path):
    inp = tmp_path / "results.jsonl"
    cross = tmp_path / "cross.jsonl"
    self_judge = tmp_path / "self.jsonl"
    out = tmp_path / "report.md"
    _write_jsonl(inp, [_row("kimi-k3")])
    _write_jsonl(
        cross,
        [
            {
                "model": "kimi-k3",
                "prompt_id": "probe-1",
                "dimension": "sense_resolution",
                "verdict": "PASS",
                "judge_model": "gemini-3.1-pro-preview",
                "protocol": "per-dimension",
                "judge_relationship": "cross_family",
            }
        ],
    )
    _write_jsonl(
        self_judge,
        [
            {
                "model": "kimi-k3",
                "prompt_id": "probe-1",
                "dimension": "sense_resolution",
                "verdict": "PARTIAL",
                "judge_model": "kimi-k3",
                "protocol": "per-dimension",
                "judge_relationship": "self_family",
            }
        ],
    )

    assert (
        mfr.main(
            [
                "--in",
                str(inp),
                "--judge",
                str(cross),
                str(self_judge),
                "--out",
                str(out),
            ]
        )
        == 0
    )

    md = out.read_text(encoding="utf-8")
    assert "gemini-3.1-pro-preview" in md
    assert "Same-family contextual self-judge" in md
