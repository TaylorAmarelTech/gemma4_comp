"""Tests for scripts/orchestrator.py backups -- the off-OneDrive durable mirror + rotation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


orch = _load("orchestrator", _ROOT / "scripts" / "orchestrator.py")


def test_rotate_keeps_newest_only(tmp_path):
    for stamp in ("20260101T000000Z", "20260102T000000Z", "20260103T000000Z"):
        (tmp_path / stamp).mkdir()
    orch._rotate(tmp_path, keep=2)
    remaining = sorted(d.name for d in tmp_path.iterdir() if d.is_dir())
    assert remaining == ["20260102T000000Z", "20260103T000000Z"]   # oldest pruned; latest is complete


def test_snapshot_copies_only_existing_targets(tmp_path, monkeypatch):
    src_root = tmp_path / "src"
    (src_root / "reports").mkdir(parents=True)
    (src_root / "reports" / "panel.jsonl").write_text("grade1\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ROOT", src_root)
    monkeypatch.setattr(orch, "BACKUP_TARGETS", ["reports/panel.jsonl", "reports/absent.jsonl"])
    dest = tmp_path / "dest"
    assert orch._snapshot(dest) == 1                                # only the existing target copied
    assert (dest / "reports" / "panel.jsonl").read_text(encoding="utf-8") == "grade1\n"


def test_backup_mirrors_panel_to_off_onedrive(tmp_path, monkeypatch):
    src_root = tmp_path / "src"
    (src_root / "reports").mkdir(parents=True)
    (src_root / "reports" / "panel.jsonl").write_text("g\n", encoding="utf-8")
    onedrive, external = tmp_path / "onedrive", tmp_path / "external"
    monkeypatch.setattr(orch, "ROOT", src_root)
    monkeypatch.setattr(orch, "BACKUP_TARGETS", ["reports/panel.jsonl"])
    monkeypatch.setattr(orch, "BACKUPS", onedrive)
    monkeypatch.setattr(orch, "EXTERNAL_BACKUPS", external)
    out = orch.backup()
    assert out["files"] == 1 and out["external"]
    # the irreplaceable panel landed in BOTH the in-tree store AND the off-OneDrive mirror
    assert any(p.name == "panel.jsonl" for p in onedrive.rglob("panel.jsonl"))
    assert any(p.name == "panel.jsonl" for p in external.rglob("panel.jsonl"))
