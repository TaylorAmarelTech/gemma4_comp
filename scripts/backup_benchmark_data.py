"""Durable OFF-OneDrive backup of the irreplaceable benchmark artifacts.

The whole project tree lives under OneDrive, which has already corrupted the system Python down to the
stdlib. The graded benchmark data (panel.jsonl, results.jsonl, pairwise.jsonl, benchmark.db) is the one
thing that CANNOT be regenerated without re-spending days of model credits, yet it sits in that same
OneDrive tree. This copies it to a location OUTSIDE OneDrive (``%LOCALAPPDATA%\\gemma4-backups`` by
default, next to the recovery venv), verifies each copy by sha256, and writes a manifest so a restore is
auditable. Default run mirrors the latest; ``--snapshot`` also keeps a timestamped point-in-time copy.

Run:
    python scripts/backup_benchmark_data.py            # mirror latest off-OneDrive + manifest
    python scripts/backup_benchmark_data.py --snapshot # also keep a timestamped snapshot
    python scripts/backup_benchmark_data.py --dest D:/backups/gemma4   # explicit destination
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The irreplaceable artifacts (repo-relative). Missing ones are skipped, not fatal -- an early-stage
# checkout may not have every file yet.
CRITICAL_ARTIFACTS = (
    "reports/rich_lift/panel.jsonl",
    "reports/rich_lift/results.jsonl",
    "reports/rich_lift/pairwise.jsonl",
    "reports/rich_lift/benchmark.db",
    "reports/autonomous_engine_state.json",
)


def _sha256(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def default_dest() -> Path:
    """Off-OneDrive backup root: %LOCALAPPDATA%\\gemma4-backups (Windows) or ~/.local/share fallback."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "gemma4-backups"


def _copy_verified(src: Path, dst: Path) -> dict:
    """Copy src -> dst atomically (temp + replace) and verify by sha256. Returns a manifest entry."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    src_hash = _sha256(src)
    tmp = dst.with_suffix(dst.suffix + ".part")
    shutil.copy2(src, tmp)
    if _sha256(tmp) != src_hash:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"checksum mismatch copying {src} -> {dst}")
    os.replace(tmp, dst)
    return {"artifact": src.relative_to(REPO_ROOT).as_posix(), "bytes": src.stat().st_size,
            "sha256": src_hash}


def backup(dest_root: Path, *, snapshot: bool, now: datetime | None = None,
           artifacts: tuple[str, ...] = CRITICAL_ARTIFACTS) -> dict:
    """Mirror the critical artifacts into ``dest_root/latest`` (and a timestamped dir if ``snapshot``).
    Returns the manifest dict (also written to disk beside the copies)."""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    entries, skipped = [], []
    targets = [("latest", dest_root / "latest")]
    if snapshot:
        targets.append((stamp, dest_root / "snapshots" / stamp))
    for label, out_dir in targets:
        for rel in artifacts:
            src = REPO_ROOT / rel
            if not src.exists():
                if label == "latest":
                    skipped.append(rel)
                continue
            entry = _copy_verified(src, out_dir / Path(rel).name)
            if label == "latest":
                entries.append(entry)
    manifest = {"_backup": True, "backed_up_at": stamp, "source_root": str(REPO_ROOT),
                "dest_root": str(dest_root), "snapshot": bool(snapshot),
                "artifacts": entries, "skipped_missing": skipped,
                "total_bytes": sum(e["bytes"] for e in entries)}
    (dest_root / "latest").mkdir(parents=True, exist_ok=True)
    (dest_root / "latest" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Durable off-OneDrive backup of benchmark artifacts.")
    ap.add_argument("--dest", type=Path, default=None, help="backup root (default: %LOCALAPPDATA%/gemma4-backups)")
    ap.add_argument("--snapshot", action="store_true", help="also keep a timestamped point-in-time copy")
    args = ap.parse_args(argv)
    dest = args.dest or default_dest()
    on_onedrive = "onedrive" in str(dest).lower()
    m = backup(dest, snapshot=args.snapshot)
    print(f"backed up {len(m['artifacts'])} artifact(s), {m['total_bytes']/1e6:.1f} MB -> {dest / 'latest'}")
    for e in m["artifacts"]:
        print(f"  {e['artifact']:42s} {e['bytes']/1e6:7.1f} MB  {e['sha256'][:12]}")
    if m["skipped_missing"]:
        print(f"  skipped (missing): {', '.join(m['skipped_missing'])}")
    if on_onedrive:
        print("  WARNING: destination is inside a OneDrive path -- this defeats the purpose; pass --dest "
              "to a non-OneDrive drive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
