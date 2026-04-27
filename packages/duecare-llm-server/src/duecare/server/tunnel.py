"""Public-URL tunnel helpers (cloudflared / ngrok).

Lets you launch the server inside a Kaggle session and record a demo
from your laptop browser. cloudflared quick-tunnels are the default
because they need no account or auth token.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional


class TunnelError(RuntimeError):
    pass


def open_tunnel(provider: str, port: int,
                  extra_args: Optional[list[str]] = None) -> str:
    """Spawn a tunnel and return the public URL once it's available.
    Provider: "cloudflared" | "ngrok" | "none"."""
    p = (provider or "").strip().lower()
    if p in ("none", ""):
        return f"http://localhost:{port}"
    if p == "cloudflared":
        return _open_cloudflared(port, extra_args)
    if p == "ngrok":
        return _open_ngrok(port, extra_args)
    raise TunnelError(f"unknown tunnel provider: {provider!r}. "
                       f"Use 'cloudflared', 'ngrok', or 'none'.")


def _open_cloudflared(port: int,
                        extra_args: Optional[list[str]]) -> str:
    """Spawn `cloudflared tunnel --url http://localhost:<port>`. Auto-
    install the binary on Kaggle Linux if not present."""
    bin_path = shutil.which("cloudflared")
    if not bin_path:
        bin_path = _install_cloudflared()
        if not bin_path:
            raise TunnelError(
                "cloudflared not found on PATH and auto-install failed. "
                "Install manually: "
                "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
    cmd = [bin_path, "tunnel", "--url", f"http://localhost:{port}"]
    if extra_args:
        cmd.extend(extra_args)
    print(f"[tunnel] launching cloudflared: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1)
    public_url = _scan_for_url(proc, timeout=60)
    if not public_url:
        raise TunnelError(
            "cloudflared did not announce a public URL within 60s")
    print(f"[tunnel] public URL ready: {public_url}")
    return public_url


def _install_cloudflared() -> Optional[str]:
    """Best-effort install on Linux (Kaggle). Pulls the static binary
    from Cloudflare's release page."""
    if sys.platform != "linux":
        return None
    try:
        url = ("https://github.com/cloudflare/cloudflared/releases/"
               "latest/download/cloudflared-linux-amd64")
        target = "/usr/local/bin/cloudflared"
        # Try wget first, then curl, then urllib.
        if shutil.which("wget"):
            subprocess.run(["wget", "-q", "-O", target, url], check=True)
        elif shutil.which("curl"):
            subprocess.run(["curl", "-sSL", "-o", target, url], check=True)
        else:
            import urllib.request as ur
            ur.urlretrieve(url, target)
        os.chmod(target, 0o755)
        return target
    except Exception as e:
        print(f"[tunnel] cloudflared auto-install FAILED: "
              f"{type(e).__name__}: {e}")
        return None


def _open_ngrok(port: int,
                  extra_args: Optional[list[str]]) -> str:
    """Use pyngrok if available, else ngrok CLI."""
    try:
        from pyngrok import conf, ngrok   # type: ignore
        token = os.environ.get("NGROK_AUTHTOKEN")
        if token:
            conf.get_default().auth_token = token
        public_url = ngrok.connect(port, bind_tls=True).public_url
        print(f"[tunnel] ngrok public URL: {public_url}")
        return public_url
    except Exception:
        pass
    bin_path = shutil.which("ngrok")
    if not bin_path:
        raise TunnelError("ngrok not found and pyngrok not importable")
    cmd = [bin_path, "http", str(port), "--log=stdout", "--log-level=info"]
    if extra_args:
        cmd.extend(extra_args)
    print(f"[tunnel] launching ngrok: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1)
    return _scan_for_url(proc, timeout=30) or f"http://localhost:{port}"


_URL_RX = re.compile(r"https://[A-Za-z0-9_\-.]+\.(?:trycloudflare\.com|"
                       r"ngrok-free\.app|ngrok\.app|ngrok\.io)")


def _scan_for_url(proc: subprocess.Popen, timeout: float) -> Optional[str]:
    """Watch a tunnel subprocess's stdout for its public URL."""
    found: dict = {"url": None}

    def reader():
        for line in proc.stdout:   # type: ignore
            line = line.rstrip()
            if line:
                print(f"[tunnel] {line}")
            m = _URL_RX.search(line or "")
            if m and not found["url"]:
                found["url"] = m.group(0)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if found["url"]:
            return found["url"]
        time.sleep(0.5)
    return found["url"]
