"""Cloudflared quick-tunnel adapter used by `kernel_shell`.

`kernel_shell.build_minimal_shell` imports
`start_cloudflared_tunnel(port)` from here. The function returns the
public `https://*.trycloudflare.com` URL (or None on failure) and
keeps the cloudflared subprocess alive in the background for the
kernel session's lifetime.

Provider preference:
  1. If `duecare.server.tunnel` is installed (workspace package),
     delegate to its `open_tunnel('cloudflared', port)` which has
     auto-install + URL-scraping logic.
  2. Else, run cloudflared inline via subprocess. The binary is
     expected to be on PATH (Kaggle's Linux image ships it; local
     dev needs a manual install).

The function is intentionally fault-tolerant: every failure path
returns None and logs a warning rather than raising, so a kernel
without internet can still finish booting (only the public URL is
missing).
"""
from __future__ import annotations

import re
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import urllib.request
from typing import Optional
from urllib.parse import urlsplit

_URL_RE = re.compile(r"https://[A-Za-z0-9.\-_]+\.trycloudflare\.com(?:/[^\s\"']*)?")


def _is_public_tunnel_url(url: str) -> bool:
    try:
        parsed = urlsplit(url.strip())
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    suffix = ".trycloudflare.com"
    if not host.endswith(suffix):
        return False
    label = host[: -len(suffix)]
    if label in {"api", "www"}:
        return False
    return bool(re.fullmatch(r"[a-z0-9-]{3,63}", label))


def _extract_public_url(line: str) -> Optional[str]:
    for match in _URL_RE.finditer(line or ""):
        raw = match.group(0).rstrip(".,)")
        if _is_public_tunnel_url(raw):
            parsed = urlsplit(raw)
            return f"{parsed.scheme}://{parsed.hostname}"
    return None


def _install_cloudflared() -> Optional[str]:
    """Best-effort local install for Kaggle-style Linux notebook runtimes."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system != "linux" or machine not in {"x86_64", "amd64"}:
        print(
            "[tunnel] cloudflared auto-install skipped: unsupported platform "
            f"{platform.system()} {platform.machine()}",
            flush=True,
        )
        return None

    target = os.path.join(tempfile.gettempdir(), "cloudflared")
    if os.path.exists(target) and os.access(target, os.X_OK):
        return target

    url = (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64"
    )
    try:
        print("[tunnel] cloudflared not found on PATH; downloading...", flush=True)
        urllib.request.urlretrieve(url, target)
        os.chmod(target, stat.S_IRWXU | stat.S_IXGRP | stat.S_IXOTH)
        size_mb = os.path.getsize(target) // 1_000_000
        print(f"[tunnel] downloaded cloudflared ({size_mb} MB) to {target}", flush=True)
        return target
    except Exception as exc:  # noqa: BLE001
        print(
            f"[tunnel] cloudflared auto-install failed: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return None


def start_cloudflared_tunnel(port: int, timeout: float = 60.0) -> Optional[str]:
    """Launch a cloudflared quick-tunnel on the given port.

    Returns the public URL string once detected, or None if the tunnel
    fails to start within `timeout` seconds. Never raises.
    """
    # Prefer the server package's helper if available -- it carries
    # the auto-install + cross-platform URL scraping that's been
    # battle-tested in the live-demo kernel.
    try:
        from duecare.server.tunnel import open_tunnel  # type: ignore

        url = open_tunnel("cloudflared", int(port))
        if url and _is_public_tunnel_url(url):
            return url
    except Exception:
        # Fall back to inline implementation below.
        pass

    bin_path = shutil.which("cloudflared") or _install_cloudflared()
    if not bin_path:
        print("[tunnel] cloudflared unavailable; serving local-only on notebook port", flush=True)
        return None

    cmd = [bin_path, "tunnel", "--url", f"http://localhost:{port}"]
    try:
        print(f"[tunnel] launching cloudflared for http://localhost:{port}", flush=True)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception:
        return None

    holder = {"url": None}
    ready = threading.Event()

    def _scan() -> None:
        try:
            while True:
                line = proc.stdout.readline() if proc.stdout else ""
                if not line:
                    if proc.poll() is not None:
                        if not ready.is_set():
                            ready.set()
                        return
                    time.sleep(0.1)
                    continue
                print(f"[tunnel] {line.rstrip()}", flush=True)
                url = _extract_public_url(line)
                if url and not holder["url"]:
                    holder["url"] = url
                    ready.set()
        except Exception:
            if not ready.is_set():
                ready.set()
            return

    t = threading.Thread(target=_scan, daemon=True, name="cloudflared-scan")
    t.start()
    ready.wait(timeout=timeout)
    if holder["url"]:
        print(f"[tunnel] public URL ready: {holder['url']}", flush=True)
    else:
        print(f"[tunnel] no public URL announced within {timeout:.0f}s", flush=True)
        try:
            proc.terminate()
        except Exception:
            pass
    return holder["url"]
