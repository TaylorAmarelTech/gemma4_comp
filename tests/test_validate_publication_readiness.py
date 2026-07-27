from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_publication_readiness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_publication_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


vpr = _load_module()


def test_gate_inventory_is_explicitly_model_and_network_free():
    gates = vpr.gates_for_scope("all")
    command_text = " ".join(arg for gate in gates for arg in gate.args).lower()

    assert len(vpr.CORE_GATES) == 8
    assert len(vpr.HANDOFF_GATES) == 2
    assert len(vpr.TRAINING_GATES) == 3
    assert "ollama" not in command_text
    assert "http://" not in command_text
    assert "https://" not in command_text


def test_run_gate_uses_python_checkout_and_offline_environment(monkeypatch):
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(vpr.subprocess, "run", fake_run)
    gate = vpr.Gate("sample", ("scripts/sample.py",), "sample purpose")
    result = vpr.run_gate(gate, timeout=12)

    assert result.passed
    assert observed["command"] == [sys.executable, "scripts/sample.py"]
    assert observed["cwd"] == ROOT
    assert observed["timeout"] == 12
    assert observed["env"]["DUECARE_MAX_PLANNED_MODEL_CALLS"] == "0"
    assert observed["env"]["HF_HUB_OFFLINE"] == "1"


def test_handoff_scope_is_separate_from_portable_core_and_strict_training():
    assert vpr.gates_for_scope("handoff") == vpr.HANDOFF_GATES
    assert vpr.gates_for_scope("all") == (
        vpr.CORE_GATES + vpr.HANDOFF_GATES + vpr.TRAINING_GATES
    )


def test_main_reports_training_failure_without_hiding_other_gates(monkeypatch, capsys):
    calls = []

    def fake_run(gate, *, timeout):
        calls.append(gate.name)
        rc = 1 if gate is vpr.TRAINING_GATES[0] else 0
        return vpr.GateResult(gate, rc, "quality gap" if rc else "ok")

    monkeypatch.setattr(vpr, "run_gate", fake_run)
    rc = vpr.main(["--scope", "training"])
    output = capsys.readouterr().out

    assert rc == 1
    assert calls == [gate.name for gate in vpr.TRAINING_GATES]
    assert "NOT READY" in output
    assert "strict training-data quality" in output
