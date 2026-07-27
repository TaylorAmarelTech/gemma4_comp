from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "launch.py"
_SPEC = importlib.util.spec_from_file_location("duecare_launch", _SCRIPT)
assert _SPEC and _SPEC.loader
LAUNCH = importlib.util.module_from_spec(_SPEC)
sys.modules["duecare_launch"] = LAUNCH
_SPEC.loader.exec_module(LAUNCH)


def test_every_profile_has_audience_desc_hint() -> None:
    assert set(LAUNCH.PROFILES) == {"workbench", "ngo", "demo", "benchmark", "notebook"}
    for name, prof in LAUNCH.PROFILES.items():
        assert prof["who"] and prof["desc"] and prof["hint"], name
        assert callable(prof["needs"])


def test_no_profile_lists_profiles_and_returns_zero(capsys) -> None:
    assert LAUNCH.main([]) == 0
    out = capsys.readouterr().out
    for name in LAUNCH.PROFILES:
        assert name in out


def test_dry_run_prints_command_without_running(capsys) -> None:
    assert LAUNCH.main(["ngo", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "docker" in out and "compose" in out and "--build" in out


def test_workbench_command_targets_the_run_server_module() -> None:
    cmd = LAUNCH._cmd_workbench()
    assert "duecare.chat.run_server" in cmd
    assert "8080" in cmd


def test_ngo_command_uses_both_compose_files() -> None:
    joined = " ".join(LAUNCH._cmd_ngo())
    assert "docker-compose.yml" in joined
    assert "docker-compose.build.yml" in joined
    assert "--build" in joined


def test_notebook_profile_is_informational_only(capsys) -> None:
    assert LAUNCH.PROFILES["notebook"]["cmd"] is None
    assert LAUNCH.main(["notebook"]) == 0
    assert "notebook" in capsys.readouterr().out.lower()
