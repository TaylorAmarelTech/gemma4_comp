"""
ILO-specific document scraper.

Knows the URL conventions for ILO Conventions, Recommendations, and
Protocols.  Returns ``RawDocument`` instances using the generic scraper.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .scraper import RawDocument, fetch_url


# ---------------------------------------------------------------------------
# ILO metadata model
# ---------------------------------------------------------------------------

class ILOConventionMeta(BaseModel):
    """Metadata for an ILO instrument (convention / recommendation / protocol)."""

    number: int
    kind: str = "convention"  # convention | recommendation | protocol
    title: str = ""
    url: str = ""
    adoption_year: Optional[int] = None
    status: str = "unknown"  # in_force | not_in_force | shelved | withdrawn


# ---------------------------------------------------------------------------
# Well-known ILO instruments relevant to forced labour / trafficking
# ---------------------------------------------------------------------------

KNOWN_INSTRUMENTS: list[ILOConventionMeta] = [
    ILOConventionMeta(number=29, kind="convention", title="Forced Labour Convention", adoption_year=1930, status="in_force"),
    ILOConventionMeta(number=105, kind="convention", title="Abolition of Forced Labour Convention", adoption_year=1957, status="in_force"),
    ILOConventionMeta(number=111, kind="convention", title="Discrimination (Employment and Occupation) Convention", adoption_year=1958, status="in_force"),
    ILOConventionMeta(number=143, kind="convention", title="Migrant Workers (Supplementary Provisions) Convention", adoption_year=1975, status="in_force"),
    ILOConventionMeta(number=181, kind="convention", title="Private Employment Agencies Convention", adoption_year=1997, status="in_force"),
    ILOConventionMeta(number=189, kind="convention", title="Domestic Workers Convention", adoption_year=2011, status="in_force"),
    ILOConventionMeta(number=190, kind="convention", title="Violence and Harassment Convention", adoption_year=2019, status="in_force"),
    ILOConventionMeta(number=97, kind="convention", title="Migration for Employment Convention (Revised)", adoption_year=1949, status="in_force"),
]


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

_NORMLEX_BASE = "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE"


def _convention_url(number: int) -> str:
    """Build the NORMLEX full-text URL for a convention."""
    return f"{_NORMLEX_BASE}:C{number:03d}"


def _recommendation_url(number: int) -> str:
    return f"{_NORMLEX_BASE}:R{number:03d}"


def _protocol_url(number: int) -> str:
    return f"{_NORMLEX_BASE}:P{number:03d}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_convention(
    number: int,
    *,
    kind: str = "convention",
    timeout: float = 30.0,
) -> RawDocument:
    """
    Fetch the full text of an ILO instrument from NORMLEX.

    Args:
        number: The instrument number (e.g. 29, 189).
        kind: One of ``convention``, ``recommendation``, ``protocol``.
        timeout: HTTP request timeout in seconds.

    Returns:
        A ``RawDocument`` with the instrument text.

    Raises:
        httpx.HTTPStatusError: On 4xx / 5xx from the ILO server.
        ValueError: If ``kind`` is not recognised.
    """
    url_builders = {
        "convention": _convention_url,
        "recommendation": _recommendation_url,
        "protocol": _protocol_url,
    }
    builder = url_builders.get(kind)
    if builder is None:
        raise ValueError(f"Unknown ILO instrument kind: {kind!r}.  Expected one of {list(url_builders)}")

    url = builder(number)
    doc = fetch_url(url, timeout=timeout)
    doc.title = doc.title or f"ILO {kind.title()} C{number:03d}"
    return doc


def list_known_instruments() -> list[ILOConventionMeta]:
    """Return metadata for the built-in list of trafficking-relevant ILO instruments."""
    return list(KNOWN_INSTRUMENTS)
