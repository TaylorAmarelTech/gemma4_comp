"""Lightweight feature-flag layer.

Reads flags from a YAML / JSON file pointed at by
``DUECARE_FEATURE_FLAGS_FILE``. If the file is missing, every
flag is False (the system behaves as if the flag layer didn't exist —
fail-closed).

Usage:

    from duecare.server import feature_flags as ff

    if ff.is_enabled("agentic_research_v2", tenant=tenant):
        ... new code path ...
    else:
        ... existing code path ...

Flag definition file (YAML):

    flags:
      agentic_research_v2:
        default: false
        rollout:
          tenants: [ngo-mfmw-hk, ngo-pathfinders]   # explicit allow
          percent: 0.0                              # gradual rollout
      new_grep_pack_2026q3:
        default: false
        rollout:
          percent: 10.0    # serve to 10% of all tenants

Or JSON:

    {"flags": {"agentic_research_v2": {"default": false,
                                          "rollout": {"percent": 5}}}}

Tenants in the explicit allow-list always see the flag enabled; all
other tenants are bucketed by a stable hash of their id so the same
tenant consistently lands on the same side of a percentage rollout.

This file deliberately doesn't depend on a remote provider
(LaunchDarkly / Unleash / Flagsmith). For those, swap this module's
implementation while keeping the same public API
([`is_enabled`][duecare.server.feature_flags.is_enabled] +
[`reload`][duecare.server.feature_flags.reload]).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:                              # pragma: no cover
    _YAML_AVAILABLE = False
    yaml = None                                   # type: ignore


@dataclass
class _Rollout:
    tenants: list[str] = field(default_factory=list)
    percent: float = 0.0


@dataclass
class _Flag:
    default: bool = False
    rollout: _Rollout = field(default_factory=_Rollout)


_LOCK = threading.Lock()
_FLAGS: dict[str, _Flag] = {}
_LOADED_FROM: str | None = None


def _coerce(raw: Any) -> _Flag:
    if not isinstance(raw, dict):
        return _Flag(default=bool(raw))
    rollout_raw = raw.get("rollout") or {}
    rollout = _Rollout(
        tenants=list(rollout_raw.get("tenants") or []),
        percent=float(rollout_raw.get("percent") or 0.0),
    )
    return _Flag(default=bool(raw.get("default", False)), rollout=rollout)


def _load_from_file(path: str) -> dict[str, _Flag]:
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    raw: Any
    if path.endswith((".yaml", ".yml")):
        if not _YAML_AVAILABLE:
            return {}
        raw = yaml.safe_load(text) or {}
    else:
        raw = json.loads(text)
    flags_dict = (raw or {}).get("flags") or {}
    return {name: _coerce(value) for name, value in flags_dict.items()}


def reload() -> None:
    """Re-read the flags file from disk. Call after a control-plane
    push or via SIGHUP if you wire one. Idempotent + thread-safe."""
    global _FLAGS, _LOADED_FROM
    path = os.environ.get("DUECARE_FEATURE_FLAGS_FILE", "").strip()
    with _LOCK:
        if not path:
            _FLAGS = {}
            _LOADED_FROM = None
            return
        _FLAGS = _load_from_file(path)
        _LOADED_FROM = path


# Auto-load at import time so first `is_enabled` call sees the file
reload()


def _bucket(tenant: str, flag_name: str) -> float:
    """Stable 0-100 bucket for a (tenant, flag) pair. Rollout
    percentages compare against this number — same tenant always
    lands on the same side."""
    digest = hashlib.sha256(
        f"{flag_name}::{tenant}".encode("utf-8"),
    ).digest()
    # Take the first 4 bytes as a uint32, normalize to 0..100
    n = int.from_bytes(digest[:4], "big")
    return (n % 10_000) / 100.0


def is_enabled(name: str, tenant: str | None = None) -> bool:
    """Return True if flag ``name`` is enabled for ``tenant``.

    Resolution order:
      1. Tenant in the explicit allow-list → True
      2. Tenant's stable bucket < rollout.percent → True
      3. Otherwise → flag.default
    """
    flag = _FLAGS.get(name)
    if flag is None:
        return False
    t = (tenant or "public").strip().lower()
    if flag.rollout.tenants and t in {x.strip().lower() for x in flag.rollout.tenants}:
        return True
    if flag.rollout.percent > 0.0 and _bucket(t, name) < flag.rollout.percent:
        return True
    return flag.default


def all_flags() -> dict[str, dict[str, Any]]:
    """Inspect the loaded flag config (for /admin/flags or debug)."""
    return {
        name: {
            "default": f.default,
            "rollout": {
                "tenants": list(f.rollout.tenants),
                "percent": f.rollout.percent,
            },
        }
        for name, f in _FLAGS.items()
    }


def loaded_from() -> str | None:
    """Path of the loaded flag file, or None if no file is configured."""
    return _LOADED_FROM
