"""The keep-alive HTTP connection pool in ``scripts/llm_generate.py`` -- the fix for Windows WSAENOBUFS
(WinError 10055) socket exhaustion under the concurrent benchmark sweep.

Before the pool, every LLM call was a bare ``urllib.request.urlopen()`` that opened and closed a fresh
TCP socket per request; a full sweep (10k prompts x arms x judges ~= 100k+ requests under 12-way
concurrency) piled the closed sockets into TIME_WAIT and exhausted the ephemeral-port table, so every
call then failed. These tests stand a local ``http.server`` in for the cloud endpoint and assert that
many requests REUSE one connection instead of opening a socket per call -- offline, no network, no
mocks of the transport under test.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import socketserver
import sys
import threading
import urllib.error
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lg = _load("llm_generate", _ROOT / "scripts" / "llm_generate.py")


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"          # keep-alive, so a well-behaved client CAN reuse the socket
    timeout = 5                            # a stranded keep-alive handler self-closes instead of hanging

    def setup(self):
        super().setup()
        with self.server.lock:             # one handler instance == one accepted TCP connection
            self.server.conn_count += 1

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        with self.server.lock:
            self.server.request_count += 1
        body = json.dumps({"choices": [{"message": {"content": "pong"}}]}).encode("utf-8")
        self.send_response(self.server.status_code)
        if self.server.retry_after is not None:
            self.send_header("Retry-After", str(self.server.retry_after))
        if self.server.location is not None:
            self.send_header("Location", self.server.location)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_a):            # keep pytest output clean
        pass


class _ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True                  # per-connection threads die with the process; teardown never hangs


class _Server:
    def __init__(self) -> None:
        self.httpd = _ThreadingServer(("127.0.0.1", 0), _Handler)
        self.httpd.lock = threading.Lock()
        self.httpd.conn_count = 0
        self.httpd.request_count = 0
        self.httpd.status_code = 200
        self.httpd.retry_after = None
        self.httpd.location = None
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._t.start()

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address
        return f"http://{host}:{port}/v1/chat/completions"

    @property
    def conn_count(self) -> int:
        return self.httpd.conn_count

    @property
    def request_count(self) -> int:
        return self.httpd.request_count

    def set_status(self, code: int, retry_after: int | None = None,
                   location: str | None = None) -> None:
        self.httpd.status_code = code
        self.httpd.retry_after = retry_after
        self.httpd.location = location

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = _Server()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _fresh_pool(monkeypatch):
    # Isolate each test: its own pool + pooling ON (the module default) so conn_count reflects only this test.
    monkeypatch.setattr(lg, "_HTTP_POOL", lg._ConnPool(16))
    monkeypatch.setattr(lg, "_HTTP_POOL_ENABLED", True)
    monkeypatch.setattr(lg.urllib.request, "getproxies", lambda: {})


def _post(url, timeout=5):
    return lg._http_post_json(url, data=b"{}", headers={"Content-Type": "application/json"}, timeout=timeout)


def test_pool_reuses_one_connection_across_many_requests(server):
    for _ in range(15):
        assert b"pong" in _post(server.url)
    assert server.request_count == 15
    assert server.conn_count == 1          # THE FIX: 15 requests served over ONE socket, not 15


def test_kill_switch_falls_back_to_urlopen(server, monkeypatch):
    monkeypatch.setattr(lg, "_HTTP_POOL_ENABLED", False)
    assert b"pong" in _post(server.url)     # DUECARE_HTTP_POOL=0 path still works via urlopen
    assert server.request_count == 1


def test_pool_maps_non_2xx_to_httperror_with_retry_after(server):
    server.set_status(503, retry_after=7)
    with pytest.raises(urllib.error.HTTPError) as ei:
        _post(server.url)
    assert ei.value.code == 503
    # the Retry-After header must survive the http.client -> HTTPError mapping so the caller can honour it
    assert lg._retry_after(ei.value) == 7.0


def test_pool_rejects_redirect_body_instead_of_treating_it_as_json(server):
    server.set_status(307, location="https://other.invalid/v1/chat/completions")
    with pytest.raises(urllib.error.HTTPError) as ei:
        _post(server.url)
    assert ei.value.code == 307
    assert ei.value.headers["Location"] == "https://other.invalid/v1/chat/completions"


def test_configured_proxy_uses_urlopen_semantics(monkeypatch):
    seen = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"proxied": true}'

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["data"] = req.data
        seen["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(lg.urllib.request, "getproxies",
                        lambda: {"https": "http://proxy.invalid:8080"})
    monkeypatch.setattr(lg.urllib.request, "proxy_bypass", lambda _host: False)
    monkeypatch.setattr(lg.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(lg._HTTP_POOL, "acquire",
                        lambda *_args, **_kwargs: pytest.fail("direct pool bypassed configured proxy"))

    url = "https://api.example.test/v1/chat/completions"
    assert _post(url, timeout=17) == b'{"proxied": true}'
    assert seen == {"url": url, "data": b"{}", "timeout": 17}


def test_pool_recovers_from_stale_keepalive(server):
    class _Broken:
        def request(self, *_a, **_k):
            raise ConnectionResetError("peer closed the keep-alive connection")

        def close(self):
            pass

    key = lg._HTTP_POOL._key(server.url)
    lg._HTTP_POOL._idle[key] = [_Broken()]           # a dead pooled conn the peer already dropped
    assert b"pong" in _post(server.url)              # transparently retried on a fresh socket
    assert server.conn_count == 1


def test_ollama_chat_reuses_connection_over_pool(server, monkeypatch):
    base = server.url[: -len("/chat/completions")]   # -> http://host:port/v1
    monkeypatch.setattr(lg, "OLLAMA_CLOUD_BASE", base)
    monkeypatch.setattr(lg, "_load_key", lambda: "k")
    assert lg.ollama_chat("hi", model="x") == "pong"
    assert lg.ollama_chat("hi again", model="x") == "pong"
    assert server.request_count == 2
    assert server.conn_count == 1          # the real caller reuses the connection across calls


def test_is_socket_exhaustion_flags_wsaenobufs():
    exc = OSError("buffer")
    exc.winerror = 10055                    # WSAENOBUFS -- the exact Windows error the pool fixes
    assert lg._is_socket_exhaustion(exc) is True
    assert lg._is_socket_exhaustion(TimeoutError("slow")) is False
