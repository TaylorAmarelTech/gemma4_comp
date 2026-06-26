"""Tests for scripts/_atomic.py -- atomic file writes (temp + os.replace)."""
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


at = _load("_atomic", _ROOT / "scripts" / "_atomic.py")


def test_write_text_atomic_replaces_and_leaves_no_temp(tmp_path):
    p = tmp_path / "sub" / "state.json"
    at.write_text_atomic(p, "hello\n")               # creates parent dir + file
    assert p.read_text(encoding="utf-8") == "hello\n"
    at.write_text_atomic(p, "world\n")               # overwrite in place
    assert p.read_text(encoding="utf-8") == "world\n"
    assert [f.name for f in p.parent.iterdir()] == ["state.json"]   # temp renamed away, none left


def test_write_json_atomic_roundtrips_unicode(tmp_path):
    p = tmp_path / "board.json"
    obj = {"a": 1, "b": ["x", "y"], "n": "café"}
    at.write_json_atomic(p, obj)
    assert json.loads(p.read_text(encoding="utf-8")) == obj
