"""scripts/verify_extension_pack.py — verify a Duecare extension pack.

Used by:
  - Clients before merging a pack into their local catalog
  - The registry CI before accepting a PR'd pack
  - Anyone who wants to manually audit a pack

Verifies:
  1. Signature is cryptographically valid (Ed25519 over pack SHA256)
  2. Signing key is present in the trust root + still valid
  3. Pack manifest schema_version matches expected
  4. Per-content-file SHA256s in the manifest match the actual files
  5. Pack hasn't passed its expires_at + 30 day grace window

Exits 0 on success, 1 on any failure with a clear reason.

Usage:
    python scripts/verify_extension_pack.py \
        --pack build/pack.tar.gz \
        --signature build/pack.tar.gz.sig \
        --trust-root ~/.duecare/trust_root.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: this script requires `cryptography`. Install with:")
    print("    pip install cryptography")
    sys.exit(1)


SCHEMA_VERSION = "1.0"
EXPIRY_GRACE_DAYS = 30


def _sha256_file(path: Path) -> bytes:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.digest()


def _load_trust_root(path: Path) -> dict[str, dict]:
    """Returns key_id -> trust-root entry. Validates schema."""
    if not path.exists():
        raise SystemExit(f"trust root not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(
            f"trust root schema version mismatch: "
            f"got {doc.get('schema_version')}, expected {SCHEMA_VERSION}"
        )
    return {k["key_id"]: k for k in doc.get("keys", [])}


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _public_key_from_fingerprint(fingerprint: str, trust_root_dir: Path) -> Ed25519PublicKey:
    """Look up the actual Ed25519 public key for a fingerprint. The
    public-key bytes live alongside the trust root in `keys/<fp>.pub`
    (PEM)."""
    safe_fp = fingerprint.replace(":", "_")
    key_path = trust_root_dir / "keys" / f"{safe_fp}.pub"
    if not key_path.exists():
        raise SystemExit(
            f"public key file for {fingerprint} not found at {key_path}\n"
            f"(every trusted key id needs a sibling .pub file)"
        )
    pem = key_path.read_bytes()
    pub = serialization.load_pem_public_key(pem)
    if not isinstance(pub, Ed25519PublicKey):
        raise SystemExit(f"key {fingerprint} is not Ed25519")
    return pub


def verify(pack_path: Path, sig_path: Path, trust_root_path: Path) -> None:
    print(f"Verifying {pack_path.name}...")
    if not pack_path.exists():
        raise SystemExit(f"pack file not found: {pack_path}")
    if not sig_path.exists():
        raise SystemExit(f"signature file not found: {sig_path}")

    # 1. Load + validate the signature document
    sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
    if sig_doc.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(
            f"signature schema version mismatch: "
            f"got {sig_doc.get('schema_version')}, expected {SCHEMA_VERSION}"
        )
    expected_digest = bytes.fromhex(sig_doc["pack_sha256"])
    actual_digest = _sha256_file(pack_path)
    if expected_digest != actual_digest:
        raise SystemExit(
            f"pack SHA256 mismatch (file modified or signature is for a different file)"
        )
    print(f"  [OK] pack SHA256 matches signature: {actual_digest.hex()}")

    # 2. Load trust root, look up signing key
    trust_root = _load_trust_root(trust_root_path)
    signing_key_id = sig_doc["signing_key_id"]
    if signing_key_id not in trust_root:
        raise SystemExit(
            f"signing key {signing_key_id} is NOT in the trust root.\n"
            f"REFUSED. Trusted keys: {sorted(trust_root)}"
        )
    key_entry = trust_root[signing_key_id]
    print(f"  [OK] signing key {signing_key_id} is in the trust root")
    print(f"        publisher: {key_entry.get('publisher')}")
    print(f"        authority: {key_entry.get('authority')}")

    # 3. Check key validity window
    now = datetime.now(timezone.utc)
    valid_from = _parse_iso(key_entry["valid_from"])
    valid_until = _parse_iso(key_entry["valid_until"])
    if now < valid_from:
        raise SystemExit(f"key {signing_key_id} not yet valid (starts {valid_from})")
    if now > valid_until:
        raise SystemExit(f"key {signing_key_id} expired at {valid_until}")
    print(f"  [OK] key valid from {valid_from} to {valid_until}")

    # 4. Verify the cryptographic signature
    public_key = _public_key_from_fingerprint(
        signing_key_id, trust_root_path.parent
    )
    signature = base64.b64decode(sig_doc["signature_b64"])
    try:
        public_key.verify(signature, actual_digest)
    except InvalidSignature:
        raise SystemExit("REFUSED: cryptographic signature INVALID")
    print(f"  [OK] cryptographic signature valid")

    # 5. Open the pack, validate manifest + per-file checksums
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(pack_path, "r:gz") as tar:
            tar.extractall(tmpdir)
        # Find the manifest
        manifest_paths = list(Path(tmpdir).rglob("manifest.json"))
        if not manifest_paths:
            raise SystemExit("no manifest.json in pack")
        manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))

        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise SystemExit(
                f"manifest schema version mismatch: got "
                f"{manifest.get('schema_version')}, expected {SCHEMA_VERSION}"
            )
        print(f"  [OK] manifest schema {SCHEMA_VERSION}: "
              f"{manifest['pack_id']} v{manifest['pack_version']}")

        # 6. expires_at + grace
        expires = _parse_iso(manifest["expires_at"])
        if now > expires + timedelta(days=EXPIRY_GRACE_DAYS):
            raise SystemExit(
                f"pack expired at {expires}; "
                f">{EXPIRY_GRACE_DAYS}-day grace window passed"
            )
        elif now > expires:
            print(f"  [WARN] pack expired at {expires} but within "
                  f"{EXPIRY_GRACE_DAYS}-day grace window")
        else:
            print(f"  [OK] pack valid until {expires}")

        # 7. Per-content-file checksums
        pack_root = manifest_paths[0].parent
        for rel, expected_sha in manifest["checksum_sha256"].items():
            f = pack_root / rel
            if not f.exists():
                raise SystemExit(f"manifest references missing file: {rel}")
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
            if actual != expected_sha:
                raise SystemExit(
                    f"checksum mismatch on {rel}:\n"
                    f"  expected: {expected_sha}\n"
                    f"  actual:   {actual}"
                )
        print(f"  [OK] all {len(manifest['checksum_sha256'])} content "
              f"checksums match manifest")

    print()
    print(f"VERIFIED: {manifest['pack_id']} v{manifest['pack_version']}")
    print(f"          publisher: {manifest['publisher']['name']}")
    print(f"          contents:  {manifest['content']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack", required=True)
    p.add_argument("--signature", required=True)
    p.add_argument("--trust-root", required=True)
    args = p.parse_args()
    verify(Path(args.pack), Path(args.signature), Path(args.trust_root))


if __name__ == "__main__":
    main()
