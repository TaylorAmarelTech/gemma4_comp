#!/usr/bin/env python3
"""Bridge: LLM knowledge-proposal DRAFTS -> the hub curator review queue.

`scripts/llm_generate.py --task knowledge-proposals` stages UNVERIFIED drafts to gitignored
`reports/llm_proposals/`. This bridge turns each draft into a valid KnowledgeObject v1.0
envelope (type `context_snippet`, clearly marked unverified + needs-source-verification) and
submits the batch to the hub's `POST /api/submit/knowledge`, which validates every envelope,
re-runs the PII hard gate, and stages them `status="proposed"` for a human curator (Stage 04).

The boundary holds end to end: generating a proposal NEVER makes it a "fact". It becomes a
candidate in the REVIEW queue; a curator must accept + source-verify before it is promoted to
a vetted pack (`/api/curator/decide` -> PACKS_DIR -> `/api/hub/sync`). This bridge only reaches
the *proposed* state, never the vetted layer.

Usage:
    # dry-run: build + locally validate the envelopes, print them (no network)
    python scripts/curator_submit.py reports/llm_proposals/knowledge-proposals.json --dry-run
    # submit to a running hub
    python scripts/curator_submit.py reports/llm_proposals/knowledge-proposals.json \
        --hub-url https://duecare-ai.com
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "duecare-llm-chat" / "src"))

from duecare.chat.knowledge_taxonomy import (  # noqa: E402  (path set above)
    node_id, stamp_provenance, validate_envelope,
)

PROPOSAL_TYPE = "context_snippet"   # generic free-text observation; required content key: text
SUBMIT_PATH = "/api/submit/knowledge"
_PROPOSAL_TAGS = ("llm-proposed", "unverified", "needs-source-verification")


def _slug(text: str, *, n: int = 6) -> str:
    """A kebab-case envelope id (matches the taxonomy's id pattern) from the observation."""
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48] or "proposal"
    h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:n]
    return f"llm-proposal-{base}-{h}".strip("-")


def proposal_to_envelope(item: dict, *, model: str, created_at: str,
                         node: str | None = None) -> dict:
    """One knowledge-proposal draft -> a valid `context_snippet` envelope, marked unverified."""
    observation = str(item.get("observation") or "").strip()
    content = {
        "text": observation,
        "claim_to_verify": item.get("claim_to_verify", ""),
        "source_type_to_check": item.get("source_type_to_check", ""),
        "confidence": "unverified",
        "needs_source_verification": True,
        "generated_by": f"{model} (LLM draft)",
    }
    env = {
        "schema_version": "1.0",
        "knowledge_object_type": PROPOSAL_TYPE,
        "id": _slug(observation),
        "version": "v1",
        "content": content,
        "tags": list(_PROPOSAL_TAGS),
        "extensions": {"_synthetic": True, "_propose_only": True, "review_status": "proposed"},
    }
    stamp_provenance(env, created_at=created_at, created_by=node or node_id())
    return env


def build_submission(items: list, *, model: str, created_at: str, submission_id: str) -> dict:
    """A KnowledgeSubmissionIn payload {submission_id, ts, items:[envelope,...]} for the hub."""
    envelopes = [
        proposal_to_envelope(it, model=model, created_at=created_at)
        for it in items
        if isinstance(it, dict) and str(it.get("observation") or "").strip()
    ]
    return {"submission_id": submission_id, "ts": created_at, "items": envelopes}


def validate_local(submission: dict) -> list[str]:
    """Wrapper-shape validation before bothering the server (catalog/PII checks run server-side)."""
    errs = []
    for i, env in enumerate(submission.get("items") or []):
        ok, why = validate_envelope(env, known_types={PROPOSAL_TYPE})
        if not ok:
            errs.append(f"item[{i}]: {why}")
    return errs


def submit_to_curator(submission: dict, *, hub_url: str,
                      poster: Callable[[str, dict], dict] | None = None) -> dict:
    """POST the submission to `<hub_url>/api/submit/knowledge`. `poster` is injectable for tests."""
    url = hub_url.rstrip("/") + SUBMIT_PATH
    if poster is None:
        def poster(u: str, payload: dict) -> dict:   # default real HTTP backend
            req = urllib.request.Request(
                u, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
    return poster(url, submission)


def load_staged(path: Path) -> tuple[list, str]:
    """Read a staged llm_generate proposal file -> (items, model)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(data.get("items") or []), str(data.get("model") or "llm")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proposal_file", help="a staged reports/llm_proposals/*.json file")
    ap.add_argument("--hub-url", default=os.environ.get("DUECARE_HUB_URL", ""),
                    help="hub base URL (or DUECARE_HUB_URL); omit for --dry-run")
    ap.add_argument("--dry-run", action="store_true",
                    help="build + validate + print envelopes, do not submit")
    ap.add_argument("--created-at", default="", help="ISO-8601 stamp (default: now, UTC)")
    args = ap.parse_args(argv)

    items, model = load_staged(Path(args.proposal_file))
    created_at = args.created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    sub_id = "llm_curator_" + hashlib.sha256(
        f"{args.proposal_file}|{created_at}".encode("utf-8")).hexdigest()[:10]
    submission = build_submission(items, model=model, created_at=created_at, submission_id=sub_id)

    errs = validate_local(submission)
    if errs:
        for e in errs:
            print(f"  INVALID {e}", file=sys.stderr)
        return 1

    n = len(submission["items"])
    print(f"built {n} context_snippet envelope(s) from '{args.proposal_file}' "
          f"(all marked unverified + needs-source-verification)", file=sys.stderr)

    if args.dry_run or not args.hub_url:
        print(json.dumps(submission, indent=2, ensure_ascii=False))
        print("DRY-RUN: not submitted (pass --hub-url to submit to the curator queue)",
              file=sys.stderr)
        return 0

    receipt = submit_to_curator(submission, hub_url=args.hub_url)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    accepted = receipt.get("n_accepted", 0)
    print(f"submitted -> {args.hub_url}{SUBMIT_PATH}: status={receipt.get('status')} "
          f"accepted={accepted} (now PENDING curator review, not vetted)", file=sys.stderr)
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
