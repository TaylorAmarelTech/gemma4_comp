"""Domain pack discovery + loading."""

from __future__ import annotations

from pathlib import Path

from duecare.domains.pack import FileDomainPack


_EXTERNAL_ROOT = Path("configs/duecare/domains")
_BUNDLED_ROOT = Path(__file__).resolve().parent.parent / "_data"

DEFAULT_ROOT = _EXTERNAL_ROOT if _EXTERNAL_ROOT.exists() else _BUNDLED_ROOT


def load_domain_pack(
    domain_id: str,
    root: Path | str | None = None,
) -> FileDomainPack:
    """Load a domain pack by id.

    Looks up `{root}/{domain_id}/`. Falls back to bundled data shipped
    inside the wheel when `configs/duecare/domains/` does not exist
    (e.g., on Kaggle).
    """
    if root is not None:
        root_path = Path(root)
    elif _EXTERNAL_ROOT.exists():
        root_path = _EXTERNAL_ROOT
    else:
        root_path = _BUNDLED_ROOT
    pack_dir = root_path / domain_id
    return FileDomainPack(root=pack_dir)


def discover_all(
    root: Path | str | None = None,
) -> list[FileDomainPack]:
    """Walk `root` and return a FileDomainPack for every discoverable pack.

    A pack is "discoverable" if its directory contains a card.yaml.
    """
    if root is not None:
        root_path = Path(root)
    elif _EXTERNAL_ROOT.exists():
        root_path = _EXTERNAL_ROOT
    else:
        root_path = _BUNDLED_ROOT
    if not root_path.exists():
        return []
    packs: list[FileDomainPack] = []
    for child in sorted(root_path.iterdir()):
        if not child.is_dir():
            continue
        if (child / "card.yaml").exists():
            try:
                packs.append(FileDomainPack(root=child))
            except Exception:
                continue
    return packs
