"""Knowledge-pack registry: file-backed loader + filter + sync helpers.

Packs are stored as JSON files under ``app/data/packs/`` with the naming
convention ``<pack_id>__<version>.json`` (double underscore separates the
identity from the version). The loader reads every file at process start
and keeps an in-memory index. For the hackathon scope this is enough; a
production deployment would back this with object storage and a database.

Public API:

* :func:`list_packs(filters)` -> filtered list of pack envelopes
* :func:`get_pack(pack_id, version=None)` -> latest or specific version
* :func:`list_versions(pack_id)` -> all known versions for a pack
* :func:`sync_since(cursor)` -> packs vetted after the cursor

Each function returns plain ``dict`` (the JSON body) so the FastAPI route
can stream the same payload that lives on disk without re-validating.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

LOGGER = logging.getLogger(__name__)

PACKS_DIR = Path(__file__).resolve().parent / "data" / "packs"

PackKind = Literal[
    "ContextPack",
    "GrepRulePack",
    "ToolPack",
    "ContactPack",
    "RubricPack",
    "EvalPromptPack",
    "TrainingExamplePack",
]


@dataclass(slots=True)
class _PackEntry:
    """In-memory index entry for one pack version."""

    pack_id: str
    version: str
    type_: str
    status: str
    jurisdictions: tuple[str, ...]
    corridors: tuple[str, ...]
    tags: tuple[str, ...]
    vetted_at: datetime | None
    body: dict[str, Any]


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_index() -> list[_PackEntry]:
    """Read every pack file under PACKS_DIR; return them in load order."""
    if not PACKS_DIR.is_dir():
        return []
    entries: list[_PackEntry] = []
    for path in sorted(PACKS_DIR.glob("*.json")):
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Skipping invalid pack file %s: %s", path.name, exc)
            continue
        provenance = body.get("provenance") or {}
        entries.append(
            _PackEntry(
                pack_id=str(body.get("id", "")),
                version=str(body.get("version", "")),
                type_=str(body.get("@type", "")),
                status=str(body.get("status", "proposed")),
                jurisdictions=tuple(body.get("jurisdictions") or ()),
                corridors=tuple(body.get("corridors") or ()),
                tags=tuple(body.get("tags") or ()),
                vetted_at=_parse_iso(provenance.get("vetted_at")),
                body=body,
            )
        )
    return entries


_INDEX: list[_PackEntry] = _load_index()


def reload() -> int:
    """Reload the in-memory index. Returns the new count."""
    global _INDEX
    _INDEX = _load_index()
    return len(_INDEX)


def _matches(entry: _PackEntry, **filters: Any) -> bool:
    """Apply filter kwargs against an entry. Empty filter means accept-all."""
    if (kind := filters.get("kind")) and entry.type_ != kind:
        return False
    if (status := filters.get("status")) and entry.status != status:
        return False
    if (jurisdiction := filters.get("jurisdiction")) and jurisdiction not in entry.jurisdictions:
        return False
    if (corridor := filters.get("corridor")) and corridor not in entry.corridors:
        return False
    if (tag := filters.get("tag")) and tag not in entry.tags:
        return False
    if (pack_id := filters.get("pack_id")) and entry.pack_id != pack_id:
        return False
    return True


def _sort_versions(version: str) -> tuple[int, ...]:
    """Crude semver sort: ``"1.7.10"`` -> ``(1, 7, 10)``. Non-numeric -> 0."""
    parts: list[int] = []
    for chunk in version.replace("-", ".").split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def list_packs(
    *,
    kind: str | None = None,
    status: str | None = None,
    jurisdiction: str | None = None,
    corridor: str | None = None,
    tag: str | None = None,
    latest_only: bool = True,
) -> list[dict[str, Any]]:
    """Return matching pack bodies.

    By default, only the highest version of each pack is returned (most
    clients want the latest). Set ``latest_only=False`` to get every
    version that matches the filter.
    """
    matches = [
        entry
        for entry in _INDEX
        if _matches(
            entry,
            kind=kind,
            status=status,
            jurisdiction=jurisdiction,
            corridor=corridor,
            tag=tag,
        )
    ]
    if not latest_only:
        return [entry.body for entry in matches]
    by_id: dict[str, _PackEntry] = {}
    for entry in matches:
        existing = by_id.get(entry.pack_id)
        if existing is None or _sort_versions(entry.version) > _sort_versions(existing.version):
            by_id[entry.pack_id] = entry
    return [by_id[pack_id].body for pack_id in sorted(by_id)]


def get_pack(pack_id: str, version: str | None = None) -> dict[str, Any] | None:
    """Return one pack body. ``version=None`` resolves to the highest version."""
    matches = [entry for entry in _INDEX if entry.pack_id == pack_id]
    if not matches:
        return None
    if version is None:
        matches.sort(key=lambda entry: _sort_versions(entry.version), reverse=True)
        return matches[0].body
    for entry in matches:
        if entry.version == version:
            return entry.body
    return None


def list_versions(pack_id: str) -> list[dict[str, Any]]:
    """Return one summary row per known version of ``pack_id``."""
    matches = [entry for entry in _INDEX if entry.pack_id == pack_id]
    matches.sort(key=lambda entry: _sort_versions(entry.version), reverse=True)
    return [
        {
            "id": entry.pack_id,
            "version": entry.version,
            "@type": entry.type_,
            "status": entry.status,
            "vetted_at": entry.vetted_at.isoformat() if entry.vetted_at else None,
        }
        for entry in matches
    ]


def sync_since(cursor: datetime | None) -> dict[str, Any]:
    """Return packs vetted strictly after ``cursor`` (or all if ``None``)."""
    matches: list[_PackEntry] = []
    for entry in _INDEX:
        if entry.status != "vetted":
            continue
        if cursor is None or (entry.vetted_at is not None and entry.vetted_at > cursor):
            matches.append(entry)
    matches.sort(key=lambda entry: entry.vetted_at or datetime.min.replace(tzinfo=UTC))
    next_cursor = matches[-1].vetted_at.isoformat() if matches and matches[-1].vetted_at else (
        cursor.isoformat() if cursor else None
    )
    return {
        "since": cursor.isoformat() if cursor else None,
        "next_cursor": next_cursor,
        "count": len(matches),
        "packs": [
            {
                "id": entry.pack_id,
                "version": entry.version,
                "@type": entry.type_,
                "vetted_at": entry.vetted_at.isoformat() if entry.vetted_at else None,
                "download_url": f"/api/hub/packs/{entry.pack_id}/{entry.version}",
            }
            for entry in matches
        ],
    }


def index_size() -> int:
    return len(_INDEX)


def known_kinds() -> list[str]:
    return sorted({entry.type_ for entry in _INDEX})


def known_corridors() -> list[str]:
    seen: set[str] = set()
    for entry in _INDEX:
        seen.update(entry.corridors)
    return sorted(seen)


def known_jurisdictions() -> list[str]:
    seen: set[str] = set()
    for entry in _INDEX:
        seen.update(entry.jurisdictions)
    return sorted(seen)


def known_tags() -> list[str]:
    seen: set[str] = set()
    for entry in _INDEX:
        seen.update(entry.tags)
    return sorted(seen)


__all__ = [
    "PACKS_DIR",
    "PackKind",
    "get_pack",
    "index_size",
    "known_corridors",
    "known_jurisdictions",
    "known_kinds",
    "known_tags",
    "list_packs",
    "list_versions",
    "reload",
    "sync_since",
]
