"""Redact stored model completions from the public trafficking seed corpus.

INPUT/OUTPUT: configs/duecare/domains/trafficking/seed_prompts.jsonl
              (rewritten in place; untouched rows pass through byte-identical)
ARCHIVE:      reports/private/seed_prompt_responses_full.jsonl
              (gitignored -- retains every stripped body verbatim)

WHY THIS EXISTS
---------------
A small subset of seed rows carry `metadata.response`: the verbatim answer a
frontier model gave when the prompt was first run. Those bodies are the
benchmark's *failure records*, and some of them are genuine operational uplift
-- drafted wage-withholding contract clauses, deduction ceilings tuned to stay
under a regulator's scrutiny threshold, step-by-step passport-retention
procedures. Publishing the prompts and the grades is standard safety-benchmark
practice; publishing the successful harmful completions ungated is not, and it
reads badly against the Gemma Prohibited Use Policy.

This script removes only the response *text*. Everything that carries
scientific value stays in the public file: the prompt, the category, the
difficulty, the graded ladder, and the response's own `score`, `outcome`,
`model`, and `latency_ms`. The grade survives; the uplift does not.

Nothing is destroyed. Every stripped body is written to the gitignored archive
keyed by row id, so the full corpus is one command away locally.

USAGE
-----
    python scripts/redact_seed_prompt_responses.py            # redact in place
    python scripts/redact_seed_prompt_responses.py --check    # CI guard, no writes
    python scripts/redact_seed_prompt_responses.py --restore  # rehydrate from archive

`--check` exits 1 if any unredacted response body is present, so the corpus
cannot silently regress.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = (REPO_ROOT / "configs" / "duecare" / "domains" / "trafficking"
          / "seed_prompts.jsonl")
ARCHIVE = REPO_ROOT / "reports" / "private" / "seed_prompt_responses_full.jsonl"

REDACTION_MARKER = (
    "[redacted: stored model completion withheld from the public corpus. "
    "The response grade, outcome, and model are retained above. "
    "See scripts/redact_seed_prompt_responses.py]"
)


def _is_redacted(value: object) -> bool:
    """True when a response field has already been replaced by the marker."""
    return isinstance(value, str) and value.startswith("[redacted:")


def _iter_rows(path: Path):
    """Yield (line_number, raw_line, parsed_row_or_None) for a JSONL file."""
    with path.open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                yield number, raw, None
                continue
            try:
                yield number, raw, json.loads(stripped)
            except json.JSONDecodeError:
                yield number, raw, None


def _response_of(row: object) -> str | None:
    """Return a row's stored completion, or None when it carries none."""
    if not isinstance(row, dict):
        return None
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        return None
    response = metadata.get("response")
    if not response or not isinstance(response, str):
        return None
    return response


def check() -> int:
    """Report unredacted completions without writing. Exit code doubles as CI gate."""
    offenders: list[str] = []
    total = 0
    for _, _, row in _iter_rows(CORPUS):
        if row is None:
            continue
        total += 1
        response = _response_of(row)
        if response is not None and not _is_redacted(response):
            offenders.append(str(row.get("id", "?")))

    print(f"corpus rows scanned          : {total}")
    print(f"unredacted stored completions: {len(offenders)}")
    if offenders:
        print("first offending ids          : " + ", ".join(offenders[:10]))
        print("\nFAIL -- run: python scripts/redact_seed_prompt_responses.py")
        return 1
    print("\nOK -- no stored completions in the public corpus.")
    return 0


def redact() -> int:
    """Strip completion bodies in place, archiving each one first."""
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = CORPUS.with_suffix(".jsonl.tmp")

    archived = 0
    passed_through = 0

    with temp_path.open("w", encoding="utf-8", newline="") as out, \
            ARCHIVE.open("a", encoding="utf-8", newline="") as archive:
        for _, raw, row in _iter_rows(CORPUS):
            response = _response_of(row)
            if response is None or _is_redacted(response):
                # Byte-identical pass-through keeps the diff to changed rows only.
                out.write(raw)
                passed_through += 1
                continue

            assert isinstance(row, dict)  # guaranteed by _response_of
            archive.write(json.dumps(
                {"id": row.get("id"), "response": response},
                ensure_ascii=False,
            ) + "\n")

            row["metadata"]["response"] = REDACTION_MARKER
            row["metadata"]["response_redacted"] = True
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            archived += 1

    os.replace(temp_path, CORPUS)

    print(f"rows passed through unchanged: {passed_through}")
    print(f"completions redacted         : {archived}")
    print(f"bodies archived to           : {ARCHIVE.relative_to(REPO_ROOT)}")
    if archived == 0:
        print("\nNothing to do -- corpus was already clean.")
    return 0


def restore() -> int:
    """Rehydrate the corpus from the gitignored archive (local use only)."""
    if not ARCHIVE.exists():
        print(f"No archive at {ARCHIVE} -- nothing to restore.", file=sys.stderr)
        return 1

    bodies: dict[str, str] = {}
    for _, _, row in _iter_rows(ARCHIVE):
        if isinstance(row, dict) and row.get("id"):
            bodies[str(row["id"])] = str(row.get("response") or "")

    temp_path = CORPUS.with_suffix(".jsonl.tmp")
    restored = 0
    with temp_path.open("w", encoding="utf-8", newline="") as out:
        for _, raw, row in _iter_rows(CORPUS):
            response = _response_of(row)
            if response is None or not _is_redacted(response):
                out.write(raw)
                continue
            assert isinstance(row, dict)
            body = bodies.get(str(row.get("id")))
            if body is None:
                out.write(raw)
                continue
            row["metadata"]["response"] = body
            row["metadata"].pop("response_redacted", None)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            restored += 1

    os.replace(temp_path, CORPUS)
    print(f"completions restored: {restored}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true",
                       help="report unredacted completions and exit non-zero")
    group.add_argument("--restore", action="store_true",
                       help="rehydrate bodies from the gitignored archive")
    args = parser.parse_args()

    if not CORPUS.exists():
        print(f"Corpus not found: {CORPUS}", file=sys.stderr)
        return 1
    if args.check:
        return check()
    if args.restore:
        return restore()
    return redact()


if __name__ == "__main__":
    raise SystemExit(main())
