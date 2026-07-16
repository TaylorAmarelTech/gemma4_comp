#!/usr/bin/env python3
"""Verify the public training-dataset claims against locally staged artifacts.

The docs, README, and Kaggle index assert a `release_manifest_sha256` (and, for
the corpora, exact row counts) for each published training dataset. Those digits
are otherwise offline-unverifiable prose. This script re-derives each claimed
SHA-256 from the gitignored staged or re-downloaded `release-manifest.json`
under `reports/kaggle_publish/`, and — when the manifest records per-lane row
counts — re-checks the claimed counts too.

It is a developer/reviewer tool, not a CI gate: the staged artifacts are
gitignored, so a fresh checkout reports every claim as `published_only`
(the dataset is on Kaggle but not staged here) rather than failing. When the
artifacts ARE present, any mismatch is a hard failure (exit 1), which turns the
rubric's "reproducible from (git_sha, dataset_version)" invariant into an
executable check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "configs" / "duecare" / "training" / "published_dataset_claims.json"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_staged_manifest(root: Path, globs: list[str]) -> Path | None:
    for pattern in globs:
        direct = root / pattern
        if direct.is_file():
            return direct
        for match in sorted(root.glob(pattern)):
            if match.is_file():
                return match
    return None


def _manifest_row_counts(manifest: dict[str, Any]) -> dict[str, int]:
    counts = manifest.get("counts")
    if isinstance(counts, dict):
        return {key: value for key, value in counts.items() if isinstance(value, int)}
    return {}


def verify_claim(claim: dict[str, Any], *, root: Path) -> dict[str, Any]:
    """Re-derive one claim from staged artifacts. Pure aside from reading files."""
    dataset_id = str(claim.get("dataset_id") or "")
    expected_sha = str(claim.get("release_manifest_sha256") or "").lower()
    globs = [str(item) for item in (claim.get("staged_manifest_globs") or [])]
    result: dict[str, Any] = {
        "dataset_id": dataset_id,
        "expected_release_manifest_sha256": expected_sha,
        "status": "published_only",
        "issues": [],
    }
    manifest_path = _resolve_staged_manifest(root, globs)
    if manifest_path is None:
        result["detail"] = "no staged release-manifest.json found; dataset is published-only here"
        return result
    result["staged_manifest"] = str(manifest_path.relative_to(root)).replace("\\", "/")
    actual_sha = _file_sha256(manifest_path)
    result["actual_release_manifest_sha256"] = actual_sha
    if actual_sha != expected_sha:
        result["status"] = "mismatch"
        result["issues"].append(
            f"release_manifest_sha256 mismatch: expected {expected_sha}, staged {actual_sha}"
        )
        return result
    expected_counts = claim.get("row_counts")
    if isinstance(expected_counts, dict) and expected_counts:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["status"] = "mismatch"
            result["issues"].append(f"could not read staged manifest for row counts: {exc}")
            return result
        staged_counts = _manifest_row_counts(manifest)
        mismatched = {
            key: {"claimed": value, "staged": staged_counts.get(key)}
            for key, value in expected_counts.items()
            if key in staged_counts and staged_counts[key] != value
        }
        if mismatched:
            result["status"] = "mismatch"
            result["issues"].append(f"row-count mismatch: {mismatched}")
            return result
        result["row_counts_verified"] = {
            key: value for key, value in expected_counts.items() if key in staged_counts
        }
    result["status"] = "verified"
    return result


def verify_registry(registry: dict[str, Any], *, root: Path) -> dict[str, Any]:
    claims = registry.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("registry has no claims")
    results = [verify_claim(claim, root=root) for claim in claims]
    verified = sum(1 for row in results if row["status"] == "verified")
    published_only = sum(1 for row in results if row["status"] == "published_only")
    mismatched = [row for row in results if row["status"] == "mismatch"]
    return {
        "schema_version": registry.get("schema_version"),
        "total": len(results),
        "verified": verified,
        "published_only": published_only,
        "mismatched": len(mismatched),
        "ok": not mismatched,
        "results": results,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    value.add_argument("--root", type=Path, default=ROOT)
    value.add_argument("--json", action="store_true", help="print the full JSON report")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    report = verify_registry(registry, root=args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        markers = {"verified": "OK  ", "published_only": "-   ", "mismatch": "FAIL"}
        for row in report["results"]:
            marker = markers[row["status"]]
            print(f"[{marker}] {row['dataset_id']} :: {row['status']}")
            for issue in row["issues"]:
                print(f"        {issue}")
        print(
            f"{report['verified']} verified, {report['published_only']} published-only, "
            f"{report['mismatched']} mismatched of {report['total']}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
