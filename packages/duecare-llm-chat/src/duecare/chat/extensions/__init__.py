"""Duecare extension-pack client.

Loads installed packs (verified, signed bundles per
`docs/extension_pack_format.md`) and merges their content into the
in-memory harness catalogs. Built-in rules + RAG docs + tools shipped
in this wheel stay frozen; packs are additive.

Entry point:

    from duecare.chat.extensions import ExtensionPackClient

    client = ExtensionPackClient(
        registry_url="https://tayloramareltech.github.io/duecare-extension-packs/",
        cache_dir=Path("~/.duecare/packs").expanduser(),
        trust_root_path=Path("~/.duecare/trust_root.json").expanduser(),
    )

    # List what the registry offers
    available = client.list_available()
    # Install a specific pack (downloads + verifies + caches)
    pack = client.install("ph-hk-domestic-2026-q2", version="1.2.0")
    # Get the merged catalog
    grep_rules = client.merged_grep_rules()
    rag_docs = client.merged_rag_docs()

The harness module exposes `merge_extension_packs(pack_paths)` to
splice loaded pack content into `GREP_RULES`, `RAG_CORPUS`, etc.
without forcing every consumer to know about the extension system.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"


class PackTrustError(Exception):
    """Raised when a pack signature is invalid, the signing key isn't
    in the trust root, or the pack has expired beyond its grace window."""


@dataclasses.dataclass(frozen=True)
class InstalledPack:
    """A pack that's been downloaded, verified, and cached locally.
    The harness reads its content lazily — call `load_grep_rules()`
    etc. to deserialize."""
    pack_id: str
    pack_version: str
    pack_title: str
    publisher_name: str
    cache_path: Path
    manifest: dict

    @property
    def grep_rules_path(self) -> Path:
        return self.cache_path / "content" / "grep_rules.jsonl"

    @property
    def rag_corpus_path(self) -> Path:
        return self.cache_path / "content" / "rag_corpus.jsonl"

    def load_grep_rules(self) -> list[dict]:
        return _load_jsonl(self.grep_rules_path)

    def load_rag_corpus(self) -> list[dict]:
        return _load_jsonl(self.rag_corpus_path)

    def load_tools(self) -> list[dict]:
        return _load_jsonl(self.cache_path / "content" / "tools.jsonl")

    def load_classifier_examples(self) -> list[dict]:
        return _load_jsonl(self.cache_path / "content" / "classifier_examples.jsonl")

    def load_prompt_tests(self) -> list[dict]:
        return _load_jsonl(self.cache_path / "content" / "prompt_tests.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    """Returns [] if the file doesn't exist (a pack may not contain
    every content type)."""
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


class ExtensionPackClient:
    """Pull-side client: refresh the registry index, download packs,
    verify signatures + trust root, cache locally, expose merged
    catalogs.

    All operations are synchronous + offline-capable: once a pack is
    installed, nothing requires the network. The registry is only
    contacted on `list_available()` and `install()`.
    """

    def __init__(
        self,
        registry_url: str,
        cache_dir: Path,
        trust_root_path: Path,
        *,
        verify: bool = True,
    ) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.trust_root_path = Path(trust_root_path).expanduser()
        self._verify = verify
        self._installed: dict[str, InstalledPack] = {}
        self._scan_cached()

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------
    def list_available(self) -> list[dict]:
        """Fetch the registry index. Returns the list of pack entries
        from the index.json. Each entry: {pack_id, available_versions,
        latest_version, manifest_url, signature_url, signing_key_id,
        publisher_name, scope}."""
        with urllib.request.urlopen(f"{self.registry_url}/index.json") as r:
            doc = json.loads(r.read().decode("utf-8"))
        if doc.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError(
                f"registry schema version mismatch: "
                f"got {doc.get('schema_version')}, expected {SCHEMA_VERSION}"
            )
        return doc.get("packs", [])

    def install(self, pack_id: str, version: str) -> InstalledPack:
        """Download + verify + cache a pack. Idempotent."""
        cache_key = f"{pack_id}-v{version}"
        if cache_key in self._installed:
            return self._installed[cache_key]

        pack_url = f"{self.registry_url}/packs/{pack_id}/{version}.tar.gz"
        sig_url = f"{self.registry_url}/packs/{pack_id}/{version}.tar.gz.sig"

        cache_dir_for_pack = self.cache_dir / cache_key
        cache_dir_for_pack.mkdir(parents=True, exist_ok=True)
        local_pack = cache_dir_for_pack / "pack.tar.gz"
        local_sig = cache_dir_for_pack / "pack.tar.gz.sig"

        urllib.request.urlretrieve(pack_url, local_pack)
        urllib.request.urlretrieve(sig_url, local_sig)

        if self._verify:
            self._verify_signed_pack(local_pack, local_sig)

        # Extract
        extract_dir = cache_dir_for_pack / "extracted"
        if extract_dir.exists():
            for child in extract_dir.rglob("*"):
                if child.is_file():
                    child.unlink()
        else:
            extract_dir.mkdir()
        with tarfile.open(local_pack, "r:gz") as tar:
            tar.extractall(extract_dir)

        # Locate the inner pack dir + load manifest
        pack_dirs = [p for p in extract_dir.iterdir() if p.is_dir()]
        if not pack_dirs:
            raise PackTrustError("pack archive contains no top-level dir")
        pack_root = pack_dirs[0]
        manifest = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))

        installed = InstalledPack(
            pack_id=manifest["pack_id"],
            pack_version=manifest["pack_version"],
            pack_title=manifest["pack_title"],
            publisher_name=manifest["publisher"]["name"],
            cache_path=pack_root,
            manifest=manifest,
        )
        self._installed[cache_key] = installed
        return installed

    def installed_packs(self) -> list[InstalledPack]:
        return list(self._installed.values())

    def uninstall(self, pack_id: str, version: str) -> None:
        cache_key = f"{pack_id}-v{version}"
        self._installed.pop(cache_key, None)
        target = self.cache_dir / cache_key
        if target.exists():
            for child in target.rglob("*"):
                if child.is_file():
                    child.unlink()
            for child in sorted(target.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            target.rmdir()

    # ------------------------------------------------------------------
    # Merged catalogs
    # ------------------------------------------------------------------
    def merged_grep_rules(self) -> list[dict]:
        out = []
        for p in self._installed.values():
            out.extend(p.load_grep_rules())
        return out

    def merged_rag_corpus(self) -> list[dict]:
        out = []
        for p in self._installed.values():
            out.extend(p.load_rag_corpus())
        return out

    def merged_classifier_examples(self) -> list[dict]:
        out = []
        for p in self._installed.values():
            out.extend(p.load_classifier_examples())
        return out

    def merged_prompt_tests(self) -> list[dict]:
        out = []
        for p in self._installed.values():
            out.extend(p.load_prompt_tests())
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _scan_cached(self) -> None:
        """Re-load any packs that were installed previously."""
        if not self.cache_dir.exists():
            return
        for entry in self.cache_dir.iterdir():
            if not entry.is_dir():
                continue
            pack_root_candidates = list((entry / "extracted").iterdir()) \
                if (entry / "extracted").exists() else []
            if not pack_root_candidates:
                continue
            pack_root = pack_root_candidates[0]
            manifest_path = pack_root / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                self._installed[entry.name] = InstalledPack(
                    pack_id=manifest["pack_id"],
                    pack_version=manifest["pack_version"],
                    pack_title=manifest["pack_title"],
                    publisher_name=manifest["publisher"]["name"],
                    cache_path=pack_root,
                    manifest=manifest,
                )
            except (KeyError, json.JSONDecodeError):
                continue

    def _verify_signed_pack(self, pack_path: Path, sig_path: Path) -> None:
        """Defer to scripts/verify_extension_pack.py logic. Imported
        lazily to avoid forcing the cryptography dep on chat-only
        consumers."""
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
        except ImportError as e:
            raise PackTrustError(
                "extension-pack verification requires `cryptography` "
                "(install via `pip install duecare-llm-chat[extensions]`)"
            ) from e

        # Load trust root
        if not self.trust_root_path.exists():
            raise PackTrustError(
                f"trust root not found at {self.trust_root_path}; "
                "refusing to install unverified packs"
            )
        trust_root = json.loads(self.trust_root_path.read_text(encoding="utf-8"))
        keys_by_id = {k["key_id"]: k for k in trust_root.get("keys", [])}

        # Load signature doc
        sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
        signing_key_id = sig_doc["signing_key_id"]
        if signing_key_id not in keys_by_id:
            raise PackTrustError(
                f"signing key {signing_key_id} not in trust root"
            )

        # Verify pack SHA256 matches signature
        actual = hashlib.sha256(pack_path.read_bytes()).digest()
        expected = bytes.fromhex(sig_doc["pack_sha256"])
        if actual != expected:
            raise PackTrustError("pack SHA256 does not match signature")

        # Look up public key file
        safe_fp = signing_key_id.replace(":", "_")
        key_file = self.trust_root_path.parent / "keys" / f"{safe_fp}.pub"
        if not key_file.exists():
            raise PackTrustError(
                f"public key file for {signing_key_id} not found at {key_file}"
            )
        pub = serialization.load_pem_public_key(key_file.read_bytes())
        if not isinstance(pub, Ed25519PublicKey):
            raise PackTrustError(f"key {signing_key_id} is not Ed25519")

        # Verify signature
        import base64
        signature = base64.b64decode(sig_doc["signature_b64"])
        try:
            pub.verify(signature, actual)
        except InvalidSignature as e:
            raise PackTrustError("cryptographic signature INVALID") from e


__all__ = [
    "ExtensionPackClient",
    "InstalledPack",
    "PackTrustError",
]
