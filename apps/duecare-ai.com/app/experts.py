"""Expert discovery for the outreach loop: match civil-society support orgs to a context gap.

The outreach loop already (a) re-prioritizes gaps as field observations corroborate them and
(b) targets opted-in *subscribers*. This module adds the missing third piece: proactively
SCANNING the vetted support-org directory (configs/.../migrant_support_orgs.yaml, ~532 public
orgs) to suggest WHICH experts are best placed to answer a given gap -- so a curator has a
ranked shortlist to reach out to, instead of only waiting for inbound subscribers.

These are PUBLIC organisations (NGO hotlines, unions, shelters, IOM/ILO desks), not
individuals -- naming them + showing their public contact is in-scope (rule 10 allows real NGO
names). The module only SUGGESTS; a human does the actual outreach. Deterministic + offline;
an optional GLM/Kimi re-rank can layer on top later.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

# repo-root config by default; override for a minimal deploy that bundles its own copy.
_DEFAULT_PATH = (Path(__file__).resolve().parents[3]
                 / "configs" / "duecare" / "research_monitor" / "migrant_support_orgs.yaml")


def _orgs_path() -> Path:
    return Path(os.environ.get("DUECARE_SUPPORT_ORGS", str(_DEFAULT_PATH)))


_CACHE: list[dict[str, Any]] | None = None


def load_orgs(*, force: bool = False) -> list[dict[str, Any]]:
    """Load the support-org directory (cached). Returns [] gracefully if not bundled."""
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    p = _orgs_path()
    if not p.exists():
        _CACHE = []
        return _CACHE
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    orgs = data.get("organizations") or data.get("orgs") or (data if isinstance(data, list) else [])
    _CACHE = [o for o in orgs if isinstance(o, dict) and o.get("name")]
    return _CACHE


def _corridor_countries(corridor: str) -> set[str]:
    """'PH-HK' -> {'ph','hk'}; ISO2-ish tokens only ('multi' -> {})."""
    return {t.lower() for t in re.split(r"[^A-Za-z]+", corridor or "") if len(t) == 2}


# gap.kind -> service keywords that signal a relevant org
_KIND_KEYWORDS: dict[str, list[str]] = {
    "fee_cap": ["recruit", "fee", "placement", "migrant"],
    "emerging_pattern": ["recruit", "fraud", "scam", "migrant", "traffick"],
    "contact_currency": ["hotline", "helpline", "support", "assist"],
    "statute": ["legal", "law", "rights", "advocacy"],
    "sector_pattern": ["worker", "labour", "labor", "union"],
    "proposed": ["migrant", "worker", "traffick"],
}
_WORD_RE = re.compile(r"[a-z]{4,}")


def score_org(gap: Any, org: dict[str, Any]) -> tuple[float, list[str]]:
    """Score one org against a gap; returns (score, reasons). Higher = better fit."""
    score = 0.0
    why: list[str] = []

    gap_countries = _corridor_countries(getattr(gap, "corridor", "") or "")
    org_country = str(org.get("country") or "").lower()
    if org_country and org_country in gap_countries:
        score += 3.0
        why.append(f"based in {org_country.upper()} (on the corridor)")

    text = " ".join(str(org.get(k) or "") for k in ("org_type", "services", "name", "scope")).lower()
    kws = _KIND_KEYWORDS.get(getattr(gap, "kind", "") or "", ["migrant", "worker"])
    hits = [k for k in kws if k in text]
    if hits:
        score += min(2.0, 0.6 * len(hits))
        why.append("services match: " + ", ".join(hits[:3]))

    audience_words = set(_WORD_RE.findall((getattr(gap, "audience", "") or "").lower()))
    if audience_words & set(_WORD_RE.findall(text)):
        score += 0.5
        why.append("audience fit")

    if "anti_trafficking" in str(org.get("org_type") or ""):
        score += 0.5  # broadly relevant to any exploitation gap
    if not gap_countries and str(org.get("scope") or "").lower() in {"global", "international", "regional"}:
        score += 0.4
        why.append("broad scope for a multi-corridor gap")

    return round(score, 2), why


def match_experts(gap: Any, orgs: list[dict[str, Any]] | None = None, *, limit: int = 8) -> list[dict[str, Any]]:
    """Ranked org suggestions for a gap (public contact included; a human reaches out)."""
    orgs = orgs if orgs is not None else load_orgs()
    scored: list[dict[str, Any]] = []
    for o in orgs:
        s, why = score_org(gap, o)
        if s <= 0:
            continue
        scored.append({
            "name": o.get("name"),
            "country": o.get("country"),
            "org_type": o.get("org_type"),
            "contact_phone": o.get("contact_phone") or "",
            "contact_email": o.get("contact_email") or "",
            "url": o.get("url") or "",
            "languages": o.get("languages") or "",
            "score": s,
            "why": why,
        })
    scored.sort(key=lambda x: (-x["score"], str(x["name"])))
    return scored[:limit]
