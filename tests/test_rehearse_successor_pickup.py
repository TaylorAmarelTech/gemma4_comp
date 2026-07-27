from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rehearse_successor_pickup.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("rehearse_successor_pickup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rsp = _load_module()


def test_step_inventory_is_local_model_free_and_covers_notebooks_and_archive():
    commands = [" ".join(step.args) for step in rsp.STEPS]

    assert any("--scope handoff" in command for command in commands)
    assert any("--scope core" in command for command in commands)
    assert any("validate_benchmark.py" in command for command in commands)
    assert any("durable_archive.py --verify" in command for command in commands)
    assert all("ollama" not in command.lower() for command in commands)
    assert all("publish" not in command.lower() for command in commands)


def test_offline_environment_forces_zero_call_controls():
    env = rsp.offline_environment({"DUECARE_MAX_PLANNED_MODEL_CALLS": "99"})

    assert env["DUECARE_MAX_PLANNED_MODEL_CALLS"] == "0"
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["WANDB_MODE"] == "disabled"


def test_receipt_path_must_stay_below_reports(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    accepted = rsp.receipt_path(root, "reports/handoff/rehearsal.json")
    assert accepted == (root / "reports/handoff/rehearsal.json").resolve()

    with pytest.raises(ValueError, match="below reports"):
        rsp.receipt_path(root, "docs/rehearsal.json")


def test_written_receipt_is_atomic_json_without_console_output(tmp_path):
    destination = tmp_path / "reports" / "handoff" / "receipt.json"
    payload = {
        "schema": "duecare.successor-rehearsal.v1",
        "ok": True,
        "steps": [{"output_sha256": "0" * 64, "output_line_count": 2}],
    }

    rsp.write_receipt(destination, payload)

    text = destination.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "console_tail" not in text
    assert '"ok": true' in text
