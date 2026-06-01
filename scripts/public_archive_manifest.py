#!/usr/bin/env python3
"""Create deterministic public-source archive/replay manifests.

The manifest plans how approved public fetches should be captured later
without committing raw response bodies. It is intentionally no-network and
manifest-only: WARC/cache paths are planned, not created.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "configs" / "duecare" / "benchmarks" / "research_spider"
SCHEMA_VERSION = "public_source_archive_manifest.v1"


def stable_hash(value: str, *, n: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:n]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
            count += 1
    return count


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def archive_rows(fetch_manifest: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in sorted(fetch_manifest, key=lambda row: (-int(row.get("score", 0)), row.get("url", ""))):
        url = item.get("url", "")
        archive_id = f"ARCH-{stable_hash(url).upper()}"
        content_kind = item.get("content_kind", "unknown")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": archive_id,
                "source_candidate_id": item.get("source_candidate_id", ""),
                "url": url,
                "domain": item.get("domain", ""),
                "content_kind": content_kind,
                "source_family": item.get("source_family", ""),
                "signals": item.get("signals", []),
                "planned_cache": {
                    "warc_path_template": f"reports/public_source_archive/{archive_id}.warc.gz",
                    "metadata_path_template": f"reports/public_source_archive/{archive_id}.metadata.json",
                    "redacted_text_path_template": f"reports/public_source_archive/{archive_id}.redacted.txt",
                    "commit_raw_archive_to_git": False,
                    "commit_metadata_to_git": False,
                },
                "capture_policy": {
                    "network_fetch_default": False,
                    "requires_manual_source_review": True,
                    "requires_robots_check": True,
                    "respect_rate_limits": True,
                    "warc_capture_after_approval": True,
                    "store_content_sha256": True,
                    "store_response_headers": True,
                    "store_raw_body_outside_git_only": True,
                    "publish_redacted_extract_only": True,
                    "max_bytes": item.get("fetch_policy", {}).get("max_bytes", 8_000_000),
                },
                "replay_policy": {
                    "can_replay_from_metadata_only": True,
                    "can_replay_raw_content_only_if_local_archive_exists": True,
                    "extractor_plan": item.get("extractor_plan", {}),
                    "fallback_without_archive": "use_public_url_metadata_and_source_profile_only",
                },
                "privacy": {
                    "raw_private_cases_ingested": False,
                    "public_source_only": True,
                    "pii_redaction_required_before_publish": True,
                    "raw_response_committed": False,
                },
            }
        )
    return rows


def replay_manifest(rows: list[dict]) -> dict:
    by_kind = collections.Counter(row["content_kind"] for row in rows)
    by_domain = collections.Counter(row["domain"] for row in rows)
    by_family = collections.Counter(row["source_family"] for row in rows)
    return {
        "schema_version": "public_source_replay_manifest.v1",
        "archive_manifest": "source_archive_manifest.jsonl",
        "counts": {
            "archive_entries": len(rows),
            "content_kinds": dict(sorted(by_kind.items())),
            "domains": len(by_domain),
            "source_families": dict(sorted(by_family.items())),
        },
        "replay_order": [row["id"] for row in rows[:40]],
        "operational_boundary": {
            "network_fetch_default": False,
            "raw_archives_committed_to_git": False,
            "manual_review_and_robots_required": True,
            "no_private_case_archives": True,
        },
        "next_steps": [
            "Implement optional warcio capture only after manual source review and robots checks.",
            "Keep raw WARC files outside git; commit only metadata and redacted extracts when useful.",
            "Use source profiles as deterministic fallback when live fetches are unavailable.",
        ],
    }


def run_pipeline(out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    fetch_manifest = read_jsonl(out_dir / "source_fetch_manifest.jsonl")
    rows = archive_rows(fetch_manifest)
    replay = replay_manifest(rows)
    write_jsonl(out_dir / "source_archive_manifest.jsonl", rows)
    write_json(out_dir / "source_replay_manifest.json", replay)
    summary = {
        "schema_version": "public_source_archive_summary.v1",
        "source_archive_manifest": len(rows),
        "source_replay_manifest": 1,
        "privacy": replay["operational_boundary"],
    }
    write_json(out_dir / "source_archive_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_pipeline(args.out_dir)
    print(
        "public-archive-manifest: "
        f"archive_entries={summary['source_archive_manifest']} "
        f"replay_manifest={summary['source_replay_manifest']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
