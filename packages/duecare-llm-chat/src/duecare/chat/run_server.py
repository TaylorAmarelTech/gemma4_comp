"""Runnable entry point so ``python -m duecare.chat.run_server`` starts the server.

The Docker image's ENTRYPOINT and the quick-launch paths invoke this module.
It is a thin CLI around :func:`duecare.chat.app.run_server`: it builds the
FastAPI workbench app (no model loaded yet -- the model is loaded from the UI or
a subsequent API call) and serves it with uvicorn in the foreground.

Examples
--------
    python -m duecare.chat.run_server                       # 0.0.0.0:8080
    python -m duecare.chat.run_server --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse

from duecare.chat.app import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m duecare.chat.run_server",
        description="Launch the DueCare chat/harness workbench web server.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="bind host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="bind port (default 8080)")
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="uvicorn log level (default warning)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_server(host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
