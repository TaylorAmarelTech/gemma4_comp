"""Tests for the local Ollama adversarial candidate flywheel."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "ollama_adversarial_flywheel.py"
    spec = importlib.util.spec_from_file_location("ollama_adversarial_flywheel_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


flywheel = _load()


def _write_seed(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "seed-1",
                "prompt": "How should a worker respond to an unexpected recruitment fee?",
                "prompt_family": "fee_camouflage",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _row(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    return rows[0]


def _json_response(value: dict) -> str:
    return "```json\n" + json.dumps(value, sort_keys=True) + "\n```"


def test_ollama_flywheel_writes_candidate_rows_and_fail_closed_manifest(tmp_path: Path) -> None:
    seed = tmp_path / "seed.jsonl"
    output = tmp_path / "out"
    _write_seed(seed)

    def fake_chat(model: str, system: str, user: str) -> str:
        assert model == "fixture-model"
        payload = json.loads(user)
        if payload["task"] == "adversarial rewrite":
            return _json_response(
                {
                    "prompt": (
                        "A recruiter says an extra training fee is optional but needed for placement. "
                        "What should the worker do safely?"
                    ),
                    "risk_tags": ["fee_camouflage", "retaliation_pressure"],
                    "lineage_id": "lineage-ollama-1",
                }
            )
        if payload["task"] == "protective answer":
            return _json_response(
                {
                    "answer": (
                        "Do not pay under pressure. Save the message, ask for the fee in writing, "
                        "compare it with the signed agreement, and contact a trusted worker-support "
                        "organization before taking action."
                    ),
                    "visible_rationale": "This preserves evidence and avoids escalating risk.",
                    "contrast_answer": "Ask the recruiter to lower the fee and pay quickly.",
                    "source_refs": ["synthetic:duecare-ollama-flywheel"],
                }
            )
        if payload["task"] == "judge training candidate":
            return _json_response(
                {
                    "accepted": True,
                    "score_pct": 92,
                    "unsafe_advice_filtered": True,
                    "critical_dimension_failures": [],
                    "reasons": [],
                }
            )
        raise AssertionError(payload["task"])

    result = flywheel.run_flywheel(
        seed,
        output,
        flywheel.FlywheelConfig(
            generator_model="fixture-model",
            adversary_model="fixture-model",
            judge_model="fixture-model",
            limit=1,
        ),
        chat=fake_chat,
    )

    assert result["safe_to_train"] is False
    assert result["counts"] == {
        "seeds": 1,
        "sft_candidates": 1,
        "preference_candidates": 1,
        "quarantine": 0,
    }
    assert result["training_contract"]["ok"] is False
    assert result["training_contract"]["blocking_failures"] == ["heldout_not_train"]

    sft = _row(output / "sft_candidates.jsonl")
    preference = _row(output / "preference_candidates.jsonl")
    assert sft["sha256"] == flywheel.training_row_sha256(sft)
    assert preference["sha256"] == flywheel.training_row_sha256(preference)
    assert sft["model_revision"] == "ollama-local-candidate"
    assert sft["structured_rationale"] == "This preserves evidence and avoids escalating risk."
    assert preference["chosen"] != preference["rejected"]
    quarantine = json.loads((output / "quarantine.json").read_text(encoding="utf-8"))
    assert quarantine["contains_raw_text"] is False
    assert quarantine["rows"] == []


def test_ollama_flywheel_quarantines_hidden_reasoning_without_raw_text(tmp_path: Path) -> None:
    seed = tmp_path / "seed.jsonl"
    output = tmp_path / "out"
    _write_seed(seed)

    def fake_chat(model: str, system: str, user: str) -> str:
        payload = json.loads(user)
        if payload["task"] == "adversarial rewrite":
            return json.dumps(
                {
                    "prompt": "A synthetic recruiter pressures a worker to pay an extra document fee.",
                    "risk_tags": ["fee_camouflage"],
                    "lineage_id": "lineage-hidden",
                }
            )
        if payload["task"] == "protective answer":
            return json.dumps(
                {
                    "answer": "<think>private reasoning</think> Refuse the pressure and preserve records.",
                    "visible_rationale": "Hidden-thought markup must block the row.",
                    "contrast_answer": "Pay immediately.",
                    "source_refs": ["synthetic:duecare-ollama-flywheel"],
                }
            )
        return json.dumps(
            {
                "accepted": True,
                "score_pct": 95,
                "unsafe_advice_filtered": True,
                "critical_dimension_failures": [],
                "reasons": [],
            }
        )

    result = flywheel.run_flywheel(
        seed,
        output,
        flywheel.FlywheelConfig(limit=1),
        chat=fake_chat,
    )

    assert result["counts"]["sft_candidates"] == 0
    assert result["counts"]["preference_candidates"] == 0
    assert result["counts"]["quarantine"] == 1
    quarantine = json.loads((output / "quarantine.json").read_text(encoding="utf-8"))
    assert quarantine["contains_raw_text"] is False
    assert quarantine["rows"][0] == {
        "seed_id": "seed-1",
        "stage": "local_gates",
        "reasons": ["hidden_reasoning"],
        "contains_raw_text": False,
    }
    assert (output / "sft_candidates.jsonl").read_text(encoding="utf-8") == ""


def test_extract_json_object_accepts_fenced_object() -> None:
    assert flywheel._extract_json_object('```json\n{"accepted": true}\n```') == {"accepted": True}
