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
import shutil
import subprocess
import threading
import time
from typing import Optional

_URL_RE = re.compile(r"https?://[A-Za-z0-9.\-_]+\.trycloudflare\.com")


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
        if url and url.startswith("http"):
            return url
    except Exception:
        # Fall back to inline implementation below.
        pass

    bin_path = shutil.which("cloudflared")
    if not bin_path:
        return None

    cmd = [bin_path, "tunnel", "--url", f"http://localhost:{port}"]
    try:
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

    def _scan() -> None:
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                line = proc.stdout.readline() if proc.stdout else ""
                if not line:
                    if proc.poll() is not None:
                        return
                    time.sleep(0.1)
                    continue
                m = _URL_RE.search(line)
                if m:
                    holder["url"] = m.group(0)
                    return
        except Exception:
            return

    t = threading.Thread(target=_scan, daemon=True, name="cloudflared-scan")
    t.start()
    t.join(timeout=timeout)
    return holder["url"]
