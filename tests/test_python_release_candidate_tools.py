from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


baw = _load("build_all_wheels_release_test", ROOT / "scripts" / "build_all_wheels.py")
cleanroom = _load("cleanroom_install_release_test", ROOT / "scripts" / "cleanroom_install.py")


def test_sdist_fallback_build_command(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    monkeypatch.setattr(baw, "_have", lambda _name: False)
    monkeypatch.setattr(
        baw,
        "_run",
        lambda cmd, cwd: calls.append(cmd) or True,
    )

    assert baw.build_one(tmp_path, tmp_path / "dist", False, True)
    assert calls == [[
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--sdist",
        "--outdir",
        str((tmp_path / "dist").resolve()),
    ]]


def test_release_receipt_hashes_every_artifact(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "one-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "one-0.1.0.tar.gz").write_bytes(b"sdist")
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(
        baw.subprocess,
        "run",
        lambda args, **kwargs: SimpleNamespace(
            stdout="abc123\n" if args[1:3] == ["rev-parse", "HEAD"] else ""
        ),
    )
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "123456")

    baw.write_receipt(receipt, dist_dir=dist, targets=["one"])
    data = json.loads(receipt.read_text(encoding="utf-8"))

    assert data["schema"] == "duecare.python-release-candidate.v1"
    assert data["git_sha"] == "abc123"
    assert data["git_dirty"] is False
    assert data["source_date_epoch"] == "123456"
    assert data["artifact_count"] == 2
    assert all(len(item["sha256"]) == 64 for item in data["artifacts"])
    assert data["model_calls"] == 0


def test_cleanroom_wheel_collection_is_exact_and_canonical(tmp_path):
    for name in cleanroom.WHEEL_ORDER:
        filename = f"{name.replace('-', '_')}-0.1.0-py3-none-any.whl"
        (tmp_path / filename).write_bytes(b"")

    wheels = cleanroom.collect_wheels(tmp_path)

    assert len(wheels) == 18
    assert [path.name.split("-0.1.0", 1)[0] for path in wheels] == [
        name.replace("-", "_") for name in cleanroom.WHEEL_ORDER
    ]

    wheels[0].unlink()
    with pytest.raises(FileNotFoundError, match="expected exactly one"):
        cleanroom.collect_wheels(tmp_path)
