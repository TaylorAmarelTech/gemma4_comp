from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType


def load_setup_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "setup_consumer.py"
    spec = importlib.util.spec_from_file_location("setup_consumer", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_install_does_not_call_subprocess(monkeypatch) -> None:
    module = load_setup_module()

    def fail_run(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not be called in dry-run mode")

    monkeypatch.setattr(subprocess, "run", fail_run)

    setup = module.ConsumerSetup(mode="desktop", source="pypi", dry_run=True)

    assert setup.install_dependencies()


def test_model_manifest_records_no_download(tmp_path: Path) -> None:
    module = load_setup_module()
    setup = module.ConsumerSetup(mode="desktop", home=tmp_path)

    assert setup.setup_models()

    config_path = tmp_path / "models" / "config.json"
    config = config_path.read_text(encoding="utf-8")
    assert '"primary_model": "gemma4:e2b"' in config
    assert '"weights_downloaded_by_setup": false' in config
    assert "Raw worker chats and case documents stay on this device" in config


def test_desktop_launcher_uses_existing_cli(tmp_path: Path) -> None:
    module = load_setup_module()
    setup = module.ConsumerSetup(mode="desktop", home=tmp_path)

    assert setup.create_desktop_shortcuts()

    script_path = next((tmp_path / "scripts").glob("start_duecare.*"))
    script_text = script_path.read_text(encoding="utf-8")
    assert "duecare serve --host 127.0.0.1 --port 8080" in script_text
    assert "python -m duecare.cli start" not in script_text


def test_auto_source_prefers_local_checkout() -> None:
    module = load_setup_module()
    setup = module.ConsumerSetup(mode="desktop", source="auto", dry_run=True)

    assert setup._resolve_source() == "local"
