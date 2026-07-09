"""Durable off-OneDrive backup of the irreplaceable benchmark artifacts (verified copy + manifest)."""
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


sys.path.insert(0, str(_ROOT / "scripts"))
bk = _load("backup_benchmark_data", _ROOT / "scripts" / "backup_benchmark_data.py")


def test_backup_copies_verifies_and_manifests(tmp_path, monkeypatch):
    # a fake repo with one artifact present, one missing
    monkeypatch.setattr(bk, "REPO_ROOT", tmp_path)
    (tmp_path / "reports" / "rich_lift").mkdir(parents=True)
    art = tmp_path / "reports" / "rich_lift" / "panel.jsonl"
    art.write_text('{"model":"m","score":88}\n', encoding="utf-8")
    dest = tmp_path / "backups"
    m = bk.backup(dest, snapshot=False,
                  artifacts=("reports/rich_lift/panel.jsonl", "reports/rich_lift/results.jsonl"))
    copied = dest / "latest" / "panel.jsonl"
    assert copied.exists() and copied.read_text(encoding="utf-8") == art.read_text(encoding="utf-8")
    assert m["artifacts"][0]["artifact"] == "reports/rich_lift/panel.jsonl"
    assert m["artifacts"][0]["bytes"] == art.stat().st_size
    assert "reports/rich_lift/results.jsonl" in m["skipped_missing"]     # missing -> skipped, not fatal
    manifest = json.loads((dest / "latest" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["total_bytes"] == art.stat().st_size


def test_snapshot_keeps_timestamped_copy(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr(bk, "REPO_ROOT", tmp_path)
    (tmp_path / "reports" / "rich_lift").mkdir(parents=True)
    (tmp_path / "reports" / "rich_lift" / "panel.jsonl").write_text("x", encoding="utf-8")
    dest = tmp_path / "backups"
    fixed = datetime(2026, 7, 9, 14, 0, 0, tzinfo=timezone.utc)
    bk.backup(dest, snapshot=True, now=fixed, artifacts=("reports/rich_lift/panel.jsonl",))
    assert (dest / "latest" / "panel.jsonl").exists()
    assert (dest / "snapshots" / "20260709T140000Z" / "panel.jsonl").exists()


def test_default_dest_is_off_onedrive(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\x\AppData\Local")
    assert "onedrive" not in str(bk.default_dest()).lower()      # the whole point: not in the OneDrive tree
