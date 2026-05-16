"""Regression coverage for the cloudflared tunnel adapter.

`duecare.chat.kernel_shell.build_minimal_shell()` imports
`start_cloudflared_tunnel` from `duecare.chat.extensions.tunnel`. If
that import path disappears or the function changes signature, every
appendix kernel (25 of 27) loses its public-URL capability silently.
These tests pin both the import path and the function contract.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_extensions_tunnel_module_importable() -> None:
    """The module path that kernel_shell imports must exist."""
    mod = importlib.import_module("duecare.chat.extensions.tunnel")
    assert hasattr(mod, "start_cloudflared_tunnel"), (
        "start_cloudflared_tunnel must be exported; kernel_shell.py:396 "
        "imports it by name."
    )


def test_start_cloudflared_tunnel_signature() -> None:
    """The function must accept (port, timeout=...) and return Optional[str]."""
    from duecare.chat.extensions.tunnel import start_cloudflared_tunnel
    import inspect

    sig = inspect.signature(start_cloudflared_tunnel)
    params = sig.parameters
    assert "port" in params, "must accept `port` arg"
    if "timeout" in params:
        assert params["timeout"].default is not inspect.Parameter.empty


def test_returns_none_when_cloudflared_missing(monkeypatch) -> None:
    """If cloudflared is not on PATH and the server adapter is
    unavailable, the function must return None (NEVER raise)."""
    import duecare.chat.extensions.tunnel as t

    monkeypatch.setattr(t.shutil, "which", lambda _name: None)
    import sys

    saved = sys.modules.pop("duecare.server.tunnel", None)
    try:
        monkeypatch.setitem(sys.modules, "duecare.server.tunnel", None)
        result = t.start_cloudflared_tunnel(port=8080, timeout=0.5)
        assert result is None
    finally:
        if saved is not None:
            sys.modules["duecare.server.tunnel"] = saved


def test_kernel_shell_can_boot_without_tunnel() -> None:
    """`build_minimal_shell(tunnel=False)` must boot cleanly."""
    from duecare.chat.kernel_shell import build_minimal_shell
    from duecare.chat.harnesses import anonymization, extraction

    app, url = build_minimal_shell(
        summary={"title": "tunnel-test", "role": "test"},
        kernel_id="tunnel-test",
        harnesses=[anonymization, extraction],
        tunnel=False,
        background=False,
    )
    assert app is not None
    assert url is None


def test_kernel_shell_handles_tunnel_failure_gracefully(monkeypatch) -> None:
    """When tunnel=True but cloudflared isn't available, the shell
    must still return successfully (url=None or local fallback)."""
    from duecare.chat.kernel_shell import build_minimal_shell
    import duecare.chat.extensions.tunnel as tunnel
    from duecare.chat.harnesses import anonymization

    monkeypatch.setattr(tunnel, "start_cloudflared_tunnel", lambda port: None)
    app, url = build_minimal_shell(
        summary={"title": "tunnel-fail-test", "role": "test"},
        kernel_id="tunnel-fail-test",
        harnesses=[anonymization],
        tunnel=True,
        background=False,
    )
    assert app is not None
    assert url is None or url.startswith("http")


def test_server_tunnel_auto_installs_to_temp_not_system_bin() -> None:
    """The live-demo kernel uses duecare.server.tunnel directly.

    Kaggle does not guarantee that /usr/local/bin is writable, so the
    helper must download cloudflared to a temp path just like the
    exploration workbench/minimal-shell path.
    """
    repo = Path(__file__).parents[3]
    source = (
        repo
        / "packages"
        / "duecare-llm-server"
        / "src"
        / "duecare"
        / "server"
        / "tunnel.py"
    ).read_text(encoding="utf-8")
    assert "tempfile.gettempdir()" in source
    assert 'target = "/usr/local/bin/cloudflared"' not in source
    assert "downloaded" in source and "cloudflared" in source
