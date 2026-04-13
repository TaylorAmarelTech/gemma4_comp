"""Git sha resolution. Returns 'unknown' if not inside a git repo."""

from __future__ import annotations

import subprocess


def get_git_sha() -> str:
    """Return the current git sha, or 'unknown' if not in a repo."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def get_short_sha(length: int = 8) -> str:
    """Return the first `length` chars of the git sha, or 'unknown'."""
    sha = get_git_sha()
    if sha == "unknown":
        return sha
    return sha[:length]
