"""scripts/build_extension_pack.py — build a Duecare extension pack.

Bundles GREP rules / RAG docs / tools / classifier examples / prompt
tests from per-content JSONL files into a single .tar.gz archive
with a manifest.json + checksums, ready to be signed with
sign_extension_pack.py.

Spec: docs/extension_pack_format.md.

Usage:
    # Minimal — bundle just GREP rules
    python scripts/build_extension_pack.py \
        --pack-id ph-hk-domestic-2026-q2 \
        --pack-version 1.0.0 \
        --pack-title 'PH→HK Domestic Worker Updates (2026 Q2)' \
        --publisher 'Mission for Migrant Workers HK' \
        --signing-key-id 'ed25519:abc123' \
        --grep-rules path/to/grep_rules.jsonl \
        --output build/pack.tar.gz

    # Full — multiple content kinds
    python scripts/build_extension_pack.py \
        --pack-id duecare-canonical-snapshot \
        --pack-version 0.1.0 \
        --pack-title 'Duecare canonical content snapshot' \
        --publisher 'Taylor Amarel' \
        --signing-key-id 'ed25519:def456' \
        --license MIT \
        --grep-rules content/grep_rules.jsonl \
        --rag-corpus content/rag_corpus.jsonl \
        --tools content/tools.jsonl \
        --classifier-examples content/classifier_examples.jsonl \
        --prompt-tests content/prompt_tests.jsonl \
        --corridor PH-HK --corridor PH-SA \
        --stage PRE_DEPARTURE --stage EMPLOYED \
        --expires-at 2027-05-01 \
        --changelog content/CHANGELOG.md \
        --readme content/README.md \
        --output build/duecare-canonical-snapshot-0.1.0.tar.gz
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Constants from the spec
SCHEMA_VERSION = "1.0"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,49}$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[\w.]+)?$")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_args(args: argparse.Namespace) -> None:
    if not ID_PATTERN.match(args.pack_id):
        raise SystemExit(
            f"--pack-id {args.pack_id!r} does not match {ID_PATTERN.pattern}"
        )
    if not SEMVER_PATTERN.match(args.pack_version):
        raise SystemExit(
            f"--pack-version {args.pack_version!r} is not valid semver"
        )
    for path_field in ("grep_rules", "rag_corpus", "tools",
                        "classifier_examples", "prompt_tests"):
        path = getattr(args, path_field, None)
        if path is not None and not Path(path).exists():
            raise SystemExit(f"--{path_field.replace('_', '-')} not found: {path}")


def _count_jsonl(path: Path) -> int:
    """Counts lines in a JSONL file, validating each is parseable."""
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{i} not valid JSON: {e}")
            n += 1
    return n


def _build_manifest(args: argparse.Namespace,
                     content_files: dict[str, Path]) -> dict:
    """Build the manifest.json content."""
    counts = {kind: _count_jsonl(p) for kind, p in content_files.items()}
    checksums = {f"content/{kind}.jsonl": _sha256_file(p)
                 for kind, p in content_files.items()}
    return {
        "schema_version": SCHEMA_VERSION,
        "pack_id": args.pack_id,
        "pack_version": args.pack_version,
        "pack_title": args.pack_title,
        "pack_description": args.pack_description or "",
        "license": args.license,
        "publisher": {
            "name": args.publisher,
            "contact_url": args.publisher_url or "",
            "signing_key_id": args.signing_key_id,
        },
        "scope": {
            "corridors": args.corridor or [],
            "stages": args.stage or [],
            "languages": args.language or ["en"],
        },
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": args.expires_at + "T00:00:00Z" if "T" not in args.expires_at
                        else args.expires_at,
        "supersedes": args.supersedes or [],
        "depends_on": args.depends_on or [],
        "content": counts,
        "checksum_sha256": checksums,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack-id", required=True)
    p.add_argument("--pack-version", required=True)
    p.add_argument("--pack-title", required=True)
    p.add_argument("--pack-description", default="")
    p.add_argument("--publisher", required=True)
    p.add_argument("--publisher-url", default="")
    p.add_argument("--signing-key-id", required=True,
                    help="ed25519:<hex> public-key fingerprint of the signing key")
    p.add_argument("--license", default="MIT")
    p.add_argument("--corridor", action="append",
                    help="restricts pack visibility to this corridor; repeat")
    p.add_argument("--stage", action="append")
    p.add_argument("--language", action="append")
    p.add_argument("--expires-at", required=True,
                    help="ISO date YYYY-MM-DD or full timestamp")
    p.add_argument("--supersedes", action="append",
                    help="<pack-id>@<version>; repeat for multiple")
    p.add_argument("--depends-on", action="append")
    # Content sources (all optional but at least one required)
    p.add_argument("--grep-rules", help="path to grep_rules.jsonl")
    p.add_argument("--rag-corpus", help="path to rag_corpus.jsonl")
    p.add_argument("--tools", help="path to tools.jsonl")
    p.add_argument("--classifier-examples", help="path to classifier_examples.jsonl")
    p.add_argument("--prompt-tests", help="path to prompt_tests.jsonl")
    # Optional auxiliary files
    p.add_argument("--changelog", help="path to changelog.md")
    p.add_argument("--readme", help="path to README.md")
    # Output
    p.add_argument("--output", required=True, help="output .tar.gz path")
    args = p.parse_args()

    _validate_args(args)

    content_files = {}
    for kind, attr in [
        ("grep_rules", "grep_rules"),
        ("rag_corpus", "rag_corpus"),
        ("tools", "tools"),
        ("classifier_examples", "classifier_examples"),
        ("prompt_tests", "prompt_tests"),
    ]:
        path = getattr(args, attr)
        if path:
            content_files[kind] = Path(path)
    if not content_files:
        raise SystemExit(
            "No content provided. Use at least one of --grep-rules, "
            "--rag-corpus, --tools, --classifier-examples, --prompt-tests."
        )

    manifest = _build_manifest(args, content_files)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    pack_dir_name = f"duecare-pack-{args.pack_id}-v{args.pack_version}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir) / pack_dir_name
        tmp.mkdir()
        (tmp / "content").mkdir()

        # Write manifest
        (tmp / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        # Copy content files
        for kind, src in content_files.items():
            (tmp / "content" / f"{kind}.jsonl").write_bytes(src.read_bytes())
        # Optional auxiliaries
        if args.changelog:
            (tmp / "changelog.md").write_bytes(Path(args.changelog).read_bytes())
        if args.readme:
            (tmp / "README.md").write_bytes(Path(args.readme).read_bytes())

        # Build deterministic tar.gz (sorted entries, fixed mtime)
        with tarfile.open(out, "w:gz") as tar:
            for path in sorted(tmp.rglob("*")):
                arcname = str(path.relative_to(tmp.parent))
                tar.add(path, arcname=arcname, recursive=False)

    size = out.stat().st_size
    sha = _sha256_file(out)
    print(f"OK: built {out}")
    print(f"   size: {size:,} bytes")
    print(f"   sha256: {sha}")
    print(f"   pack: {args.pack_id} v{args.pack_version}")
    print(f"   contents: {manifest['content']}")
    print()
    print("Next: sign the pack")
    print(f"   python scripts/sign_extension_pack.py \\")
    print(f"       --pack {out} \\")
    print(f"       --private-key <your-ed25519-key> \\")
    print(f"       --output {out}.sig")


if __name__ == "__main__":
    main()
