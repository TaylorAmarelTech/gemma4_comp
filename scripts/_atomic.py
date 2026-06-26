#!/usr/bin/env python3
"""Atomic file writes -- write to a temp file in the same directory, then os.replace.

``os.replace`` is atomic on POSIX and Windows, so a crash (or kill) mid-write leaves the old file
intact and the temp file orphaned -- a reader NEVER sees a half-written target. Used for the small,
frequently-rewritten, read-critical JSON/text files (engine state, benchmark board, prompt-set spec):
those are the ones whose corruption would reset progress or break the site. Append-only JSONL stores
do not need this -- their loaders already skip a truncated final line.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
from typing import Any


def write_text_atomic(path: "pathlib.Path | str", text: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace ``path`` with ``text`` (temp file in the same dir + fsync + os.replace)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # atomic rename over the target
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path: "pathlib.Path | str", obj: Any, *, indent: "int | None" = 2) -> None:
    """Atomically write ``obj`` as JSON to ``path``."""
    write_text_atomic(path, json.dumps(obj, indent=indent, ensure_ascii=False) + "\n")
