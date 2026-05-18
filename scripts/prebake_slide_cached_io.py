"""Pre-bake every (audience, use_case) cached row for the slide deck.

The `/slides#demo-chat` slide reads a single row from
`localStorage['duecare.slides.demo.chat']`. To prepare a recording,
Taylor picks one row from this matrix and pastes the matching JS
snippet into the browser console (or visits `/slides/setup` and
clicks Generate/Save).

This script walks every (audience, use_case) pair, calls the
deterministic `build_cached_io(...)` generator in-process (no live
server needed), and writes:

  - a JSON document keyed by `audience/use_case`, suitable for `--out`
  - a copy-paste JS snippet for each row, suitable for pasting into
    the browser DevTools console with a chosen row index

Usage:
    python scripts/prebake_slide_cached_io.py
    python scripts/prebake_slide_cached_io.py --out prebaked.json
    python scripts/prebake_slide_cached_io.py --pretty
    python scripts/prebake_slide_cached_io.py --js-snippet worker/ph_hk_placement_fee
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _import_generator():
    """Resolve `build_cached_io`, `AUDIENCE_KEYS`, `USE_CASE_KEYS`,
    `_audience_label`, and `_USE_CASES` from the in-tree server
    package without requiring an editable install.
    """
    server_src = (
        Path(__file__).resolve().parents[1]
        / "packages"
        / "duecare-llm-server"
        / "src"
    )
    if str(server_src) not in sys.path:
        sys.path.insert(0, str(server_src))
    from duecare.server.slides_cache import (  # type: ignore[import-not-found]
        AUDIENCE_KEYS,
        USE_CASE_KEYS,
        _USE_CASES,
        _audience_label,
        build_cached_io,
    )
    return (
        AUDIENCE_KEYS,
        USE_CASE_KEYS,
        _USE_CASES,
        _audience_label,
        build_cached_io,
    )


def _row_payload(
    audience_key: str,
    use_case_key: str,
    cached,
    use_cases_table,
    audience_label,
) -> dict:
    """Shape the localStorage payload that /slides/setup writes.

    `cached` is a `CachedIO` dataclass with `.prompt` and `.response`.
    """
    use_case_title = (
        use_cases_table[use_case_key].title
        if use_case_key in use_cases_table
        else use_case_key
    )
    return {
        "audience": audience_label(audience_key),
        "use_case": use_case_title,
        "audience_key": audience_key,
        "use_case_key": use_case_key,
        "prompt": cached.prompt,
        "response": cached.response,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
    }


def _js_snippet(row: dict) -> str:
    """Render the one-liner Taylor can paste into the browser console
    to populate localStorage on /slides directly.
    """
    encoded = json.dumps(json.dumps(row))  # double-encode for string literal
    return (
        "localStorage.setItem("
        "'duecare.slides.demo.chat', "
        f"{encoded}"
        ");"
    )


def _build_matrix(verbose: bool = False) -> dict[str, dict]:
    (
        audience_keys,
        use_case_keys,
        use_cases_table,
        audience_label,
        build,
    ) = _import_generator()
    out: dict[str, dict] = {}
    for audience in audience_keys:
        for use_case in use_case_keys:
            try:
                cached = build(audience, use_case, None)
            except Exception as exc:  # pragma: no cover - defensive
                print(
                    f"# skipped {audience}/{use_case}: {exc}",
                    file=sys.stderr,
                )
                continue
            key = f"{audience}/{use_case}"
            row = _row_payload(
                audience,
                use_case,
                cached,
                use_cases_table,
                audience_label,
            )
            out[key] = row
            if verbose:
                print(
                    f"# {key} :: {row['prompt'][:80]}",
                    file=sys.stderr,
                )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pre-bake every cached (audience, use_case) row for "
            "/slides#demo-chat"
        )
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write the full matrix JSON to this path",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON (default: compact)",
    )
    parser.add_argument(
        "--js-snippet",
        metavar="audience/use_case",
        default=None,
        help=(
            "Print only the browser-console JS snippet for one row, "
            "e.g. --js-snippet worker/ph_hk_placement_fee"
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List every audience/use_case key and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Echo per-row prompt previews on stderr",
    )
    args = parser.parse_args()

    if args.list:
        audience_keys, use_case_keys, _, _, _ = _import_generator()
        print("audiences:")
        for key in audience_keys:
            print(f"  - {key}")
        print("use cases:")
        for key in use_case_keys:
            print(f"  - {key}")
        return 0

    matrix = _build_matrix(verbose=args.verbose)

    if args.js_snippet:
        row = matrix.get(args.js_snippet)
        if row is None:
            print(
                f"unknown key {args.js_snippet!r}. "
                "use --list to see valid keys.",
                file=sys.stderr,
            )
            return 2
        print("// 1. open https://<your-cloudflare-url>/slides")
        print("// 2. open DevTools (F12), paste this in the console,")
        print("//    then reload the slide:")
        print(_js_snippet(row))
        return 0

    payload = json.dumps(matrix, indent=2 if args.pretty else None)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {len(matrix)} rows to {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
