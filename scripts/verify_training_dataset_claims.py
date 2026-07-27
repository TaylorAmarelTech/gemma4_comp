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


def _dig(payload: Any, path: list[str]) -> Any:
    for key in path:
        if not isinstance(payload, dict) or key not in payload:
            return None
        payload = payload[key]
    return payload


def _verify_evidence_claims(
    dataset_dir: Path, evidence_claims: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Re-derive each pinned headline number from the staged dataset artifacts.

    These are the notebook-prose numbers most likely to silently drift on a
    re-run (harness lift, adversarial mean, recorded delta, run metrics), so
    they are re-read from their source JSON and compared at the stated rounding.
    """
    verified: list[dict[str, Any]] = []
    issues: list[str] = []
    for claim in evidence_claims:
        label = str(claim.get("label") or "")
        source = dataset_dir / str(claim.get("source") or "")
        path = [str(part) for part in (claim.get("json_path") or [])]
        expected = claim.get("expected")
        round_to = int(claim.get("round_to", 2))
        if not source.is_file():
            issues.append(f"{label}: source artifact missing ({claim.get('source')})")
            continue
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"{label}: could not read source ({exc})")
            continue
        actual = _dig(payload, path)
        if not isinstance(actual, (int, float)):
            issues.append(f"{label}: value at {path} is not numeric ({actual!r})")
            continue
        actual_rounded = round(float(actual), round_to) if round_to else round(float(actual))
        if actual_rounded != expected:
            issues.append(
                f"{label}: expected {expected}, staged re-derives {actual_rounded} "
                f"(raw {actual})"
            )
            continue
        verified.append({"label": label, "value": actual_rounded, "prose": claim.get("prose")})
    return verified, issues


def _live_kaggle_metadata_matches(dataset_id: str) -> dict[str, Any]:
    """Opt-in, read-only spot-check that the dataset is live on Kaggle.

    Requires the kaggle CLI plus configured credentials. This confirms the
    dataset id resolves to a public dataset; it does not publish anything.
    Never called by default — only via --check-live so no unprompted Kaggle
    call happens.
    """
    import subprocess

    try:
        completed = subprocess.run(
            ["kaggle", "datasets", "metadata", dataset_id, "--dir", "-"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return {"checked": False, "reason": "kaggle CLI not installed"}
    except subprocess.TimeoutExpired:
        return {"checked": False, "reason": "kaggle metadata lookup timed out"}
    if completed.returncode != 0:
        return {
            "checked": True,
            "live": False,
            "reason": (completed.stderr or completed.stdout or "").strip()[:200],
        }
    return {"checked": True, "live": True}


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
    evidence_claims = claim.get("evidence_claims")
    if isinstance(evidence_claims, list) and evidence_claims:
        verified_evidence, evidence_issues = _verify_evidence_claims(
            manifest_path.parent, evidence_claims
        )
        if evidence_issues:
            result["status"] = "mismatch"
            result["issues"].extend(evidence_issues)
            return result
        result["evidence_claims_verified"] = verified_evidence
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
    value.add_argument(
        "--check-live",
        action="store_true",
        help=(
            "additionally spot-check that each dataset id resolves to a live public "
            "Kaggle dataset via a read-only `kaggle datasets metadata` lookup. "
            "Requires configured Kaggle credentials; makes no publish call. Off by "
            "default so no unprompted Kaggle request happens."
        ),
    )
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    report = verify_registry(registry, root=args.root)
    if args.check_live:
        for row in report["results"]:
            row["live_kaggle"] = _live_kaggle_metadata_matches(row["dataset_id"])
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
