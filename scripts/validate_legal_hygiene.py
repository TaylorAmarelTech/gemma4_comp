"""Guard the legal and licensing posture against silent regression.

Each check here exists because the corresponding mistake was actually found in
this repository, fixed, and could come back the moment someone pastes an old
snippet or copies an archived kernel. A comment above each rule says what went
wrong, so a future maintainer can judge whether a new exception is legitimate
rather than widening the allowlist to make the build green.

Scope: git-tracked text files only. Untracked and gitignored files are not
inspected, because they never reach anyone else.

USAGE
-----
    python scripts/validate_legal_hygiene.py

Exit code 0 when clean, 1 when any check fails, so it can gate CI.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".jsonl", ".yaml", ".yml",
    ".txt", ".html", ".ipynb", ".cfg", ".toml",
}

# ---------------------------------------------------------------------------
# Rule 1 -- no safety-stripped model identifiers.
#
# The repo once carried 129 hardcoded references to refusal-ablated Gemma
# checkpoints across kernels, the shipped variants module, the workbench model
# picker, and archived notebooks. Collectively that was a download index for
# exactly the weights DueCare's threat-model study exists to defend against.
# Evaluating such a model is legitimate research; shipping a list of where to
# obtain one is not. Operators supply their own via DUECARE_STRIPPED_MODEL*.
# ---------------------------------------------------------------------------
STRIPPED_MODEL_PATTERN = re.compile(
    r"dealignai/[A-Za-z0-9_.\-]+"
    r"|JANG_4M[A-Za-z0-9_.\-]*"
    r"|huihui-ai/gemma[A-Za-z0-9_.\-]*"
    r"|mlabonne/Gemma[A-Za-z0-9_.\-]*abliterated"
    r"|AEON-7/Gemma[A-Za-z0-9_.\-]*"
    r"|TrevorS/gemma[A-Za-z0-9_.\-]*"
    r"|TrevorJS/gemma[A-Za-z0-9_.\-]*"
)

# ---------------------------------------------------------------------------
# Rule 2 -- Gemma 4 is Apache 2.0, not the older "Gemma Terms of Use".
#
# Google's terms page states that for Gemma 4 terms, see the Gemma 4 license,
# which is Apache 2.0. The repo cited the superseded terms in 21 files,
# including both license summaries a judge is pointed at. Citing the wrong
# license is a factual error in a submission judged partly on rigor.
#
# The files below may reference the old URL because they explain the
# distinction deliberately.
# ---------------------------------------------------------------------------
SUPERSEDED_TERMS_URL = "ai.google.dev/gemma/terms"
SUPERSEDED_TERMS_ALLOWLIST = {"NOTICE", "THIRD_PARTY_LICENSES.md"}

# ---------------------------------------------------------------------------
# Rule 3 -- the NOTICE file must exist and carry the Apache 2.0 attribution.
#
# DueCare distributes LoRA adapters that are Derivative Works of Gemma 4.
# Apache 2.0 section 4 requires recipients receive the license and a statement
# of changes. There was no NOTICE file at all until this was caught.
# ---------------------------------------------------------------------------
NOTICE_REQUIRED_SUBSTRINGS = (
    "Apache License",
    "ai.google.dev/gemma/apache_2",
    "prohibited_use_policy",
)

# ---------------------------------------------------------------------------
# Rule 4 -- no local absolute developer paths in shipped files.
#
# A published data manifest and an extraction script both embedded the author's
# OneDrive path, leaking an OS username and reading as unpolished.
#
# tests/ is excluded deliberately: several tests use a literal local path as a
# PII-scrub fixture, asserting that such paths get stripped. That is the guard
# working, not a leak. Archives are excluded as frozen historical records.
# ---------------------------------------------------------------------------
LOCAL_PATH_PATTERN = re.compile(r"C:[\\/]{1,2}Users[\\/]{1,2}amare", re.IGNORECASE)
LOCAL_PATH_EXCLUDED_PREFIXES = ("tests/", "_archive/", "docs/_archive/", ".claude/")


def tracked_text_files() -> list[Path]:
    """Return git-tracked files with a text suffix, as repo-relative paths."""
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        path = Path(line)
        if path.suffix.lower() in TEXT_SUFFIXES and (REPO_ROOT / path).exists():
            files.append(path)
    return files


def _read(path: Path) -> str:
    """Read a tracked file, returning empty string for unreadable content."""
    try:
        return (REPO_ROOT / path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def check_no_stripped_model_ids(files: list[Path]) -> list[str]:
    """Fail if any safety-stripped checkpoint identifier is referenced."""
    findings = []
    for path in files:
        for match in sorted(set(STRIPPED_MODEL_PATTERN.findall(_read(path)))):
            findings.append(
                f"{path.as_posix()} references safety-stripped model '{match}'"
            )
    return findings


def check_gemma4_license_reference(files: list[Path]) -> list[str]:
    """Fail if Gemma 4 is described under the superseded Gemma Terms of Use."""
    findings = []
    for path in files:
        if path.as_posix() in SUPERSEDED_TERMS_ALLOWLIST:
            continue
        if SUPERSEDED_TERMS_URL in _read(path):
            findings.append(
                f"{path.as_posix()} cites the superseded {SUPERSEDED_TERMS_URL}; "
                "Gemma 4 is Apache 2.0 (ai.google.dev/gemma/apache_2)"
            )
    return findings


def check_notice_file() -> list[str]:
    """Fail if the Apache 2.0 NOTICE is missing or incomplete."""
    notice = REPO_ROOT / "NOTICE"
    if not notice.exists():
        return [
            "NOTICE file is missing; Apache 2.0 attribution for Gemma 4 requires it"
        ]
    body = notice.read_text(encoding="utf-8")
    return [
        f"NOTICE is missing required content: {needle!r}"
        for needle in NOTICE_REQUIRED_SUBSTRINGS
        if needle not in body
    ]


def check_no_local_paths(files: list[Path]) -> list[str]:
    """Fail if a shipped file embeds the author's local filesystem path."""
    findings = []
    for path in files:
        posix = path.as_posix()
        if posix.startswith(LOCAL_PATH_EXCLUDED_PREFIXES):
            continue
        if LOCAL_PATH_PATTERN.search(_read(path)):
            findings.append(f"{posix} embeds a local developer path")
    return findings


def main() -> int:
    files = tracked_text_files()
    checks = [
        ("no_safety_stripped_model_ids", check_no_stripped_model_ids(files)),
        ("gemma4_license_is_apache_2", check_gemma4_license_reference(files)),
        ("notice_file_present", check_notice_file()),
        ("no_local_developer_paths", check_no_local_paths(files)),
    ]

    print("Legal hygiene gate")
    print("=" * 72)
    total = 0
    for name, findings in checks:
        if findings:
            total += len(findings)
            print(f"[FAIL] {name}  ({len(findings)} finding(s))")
            for finding in findings[:10]:
                print(f"  - {finding}")
            if len(findings) > 10:
                print(f"  ... and {len(findings) - 10} more")
        else:
            print(f"[OK  ] {name}")
    print("=" * 72)
    print(f"Scanned {len(files)} tracked text files.")

    if total:
        print(
            f"FAILED: {total} finding(s). Read the rule comment in this script "
            "for why each check exists before adding an exception."
        )
        return 1
    print("PASS: licensing references, model identifiers, NOTICE, and paths are clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
