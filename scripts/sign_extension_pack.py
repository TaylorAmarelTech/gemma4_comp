"""scripts/sign_extension_pack.py — sign a Duecare extension pack.

Detached Ed25519 signature over SHA256 of the entire .tar.gz archive
(per docs/extension_pack_format.md). Produces a sibling `.sig` file
clients verify against the trust root.

Usage:
    # Generate a new key pair (one-time, then keep the private key safe)
    python scripts/sign_extension_pack.py gen-key \
        --out-private-key ~/.duecare/keys/mfmw-hk.ed25519 \
        --out-public-fingerprint ~/.duecare/keys/mfmw-hk.fingerprint

    # Sign a pack
    python scripts/sign_extension_pack.py sign \
        --pack build/pack.tar.gz \
        --private-key ~/.duecare/keys/mfmw-hk.ed25519 \
        --output build/pack.tar.gz.sig

Requires `cryptography` (`pip install cryptography`).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: this script requires `cryptography`. Install with:")
    print("    pip install cryptography")
    sys.exit(1)


def _sha256_file(path: Path) -> bytes:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.digest()


def _key_fingerprint(public_key: Ed25519PublicKey) -> str:
    """Compute a stable fingerprint for a public key. Format:
    `ed25519:<first-16-bytes-of-sha256-of-raw-key-as-hex>`."""
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    h = hashlib.sha256(raw).digest()[:16].hex()
    return f"ed25519:{h}"


def cmd_gen_key(args: argparse.Namespace) -> None:
    """Generate a new Ed25519 key pair."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    out_priv = Path(args.out_private_key)
    out_priv.parent.mkdir(parents=True, exist_ok=True)
    out_priv.write_bytes(private_pem)
    out_priv.chmod(0o600)

    fingerprint = _key_fingerprint(public_key)
    out_fp = Path(args.out_public_fingerprint)
    out_fp.write_text(fingerprint + "\n", encoding="utf-8")

    print(f"OK: generated Ed25519 key pair.")
    print(f"   private key (KEEP SECRET): {out_priv}")
    print(f"   public fingerprint:        {out_fp}")
    print(f"   fingerprint value:         {fingerprint}")
    print()
    print("Next: ask the Duecare maintainer to add this fingerprint to")
    print("the trust root (with your name + scope of authority + expiry).")


def cmd_sign(args: argparse.Namespace) -> None:
    """Sign a pack with an Ed25519 private key."""
    pack_path = Path(args.pack)
    if not pack_path.exists():
        raise SystemExit(f"pack not found: {pack_path}")

    private_pem = Path(args.private_key).read_bytes()
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise SystemExit("private key is not Ed25519")
    public_key = private_key.public_key()

    digest = _sha256_file(pack_path)
    signature_bytes = private_key.sign(digest)

    sig_doc = {
        "schema_version": "1.0",
        "pack_path": pack_path.name,
        "pack_sha256": digest.hex(),
        "signing_key_id": _key_fingerprint(public_key),
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signature_b64": base64.b64encode(signature_bytes).decode(),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sig_doc, indent=2), encoding="utf-8")

    print(f"OK: signed {pack_path}")
    print(f"   signature: {out}")
    print(f"   key id:    {sig_doc['signing_key_id']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("gen-key", help="generate a new Ed25519 key pair")
    gen.add_argument("--out-private-key", required=True)
    gen.add_argument("--out-public-fingerprint", required=True)
    gen.set_defaults(fn=cmd_gen_key)

    sign = sub.add_parser("sign", help="sign a pack")
    sign.add_argument("--pack", required=True)
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--output", required=True)
    sign.set_defaults(fn=cmd_sign)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
