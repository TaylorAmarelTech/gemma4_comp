"""Single-source-of-truth for product naming, harness layer metadata,
version stamps, and copy text that would otherwise need to change in
multiple files.

If you find yourself editing the same string in two places, the answer
is to add it here and have both sites read from this module.

Structure:
- Versions and protocol stamps live as module constants.
- Layer metadata is dataclasses indexed by `LAYERS[key]`.
- Copy text (taglines, privacy promise, refusal templates) is grouped
  by audience under `COPY`.

Backed by an /api/brand endpoint so the frontend can read the same
data without duplicating it inline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib.metadata import PackageNotFoundError, version as _pkg_version


# ---------------------------------------------------------------------------
# Product identity
# ---------------------------------------------------------------------------

PRODUCT_NAME = "Duecare"
PRODUCT_TAGLINE = "Exercising due care in LLM safety design"
PRIVACY_PROMISE = (
    "Privacy is non-negotiable. So the harness runs on your laptop."
)
NAMED_FOR = (
    "Cal. Civ. Code §1714(a) — the duty-of-care standard a California "
    "jury applied in March 2026 to find Meta and Google negligent for "
    "defective platform design."
)


def chat_package_version() -> str:
    """Read the installed chat-package version from importlib.metadata.

    Falls back to 'unknown' so callers don't have to handle missing
    metadata themselves. Cached: the wheel version is fixed at import
    time, so we resolve once and stash on the module.
    """
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION
    try:
        _CACHED_VERSION = _pkg_version("duecare-llm-chat")
    except PackageNotFoundError:
        _CACHED_VERSION = "unknown"
    return _CACHED_VERSION


_CACHED_VERSION: str | None = None


# Wire-format / protocol versions. These are stable contracts between
# the chat-package server and any consumer (the chat UI, kernels,
# external tools). Bump only when the JSON shape changes.
WIRE_FORMAT_VERSION = "v2.0"


# ---------------------------------------------------------------------------
# Harness layers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarnessLayer:
    """One row of the 6-layer harness toggle bar."""

    key: str
    """Stable id used in API + JS (`persona`, `grep`, ...)."""

    label: str
    """User-facing display label (`Persona`, `GREP`)."""

    color: str
    """Hex color for the toggle tile + per-layer pipeline card."""

    short_desc: str
    """One-sentence summary for the chat top-bar tooltip."""

    description: str
    """Long-form description for the inspector / About modal."""

    viewer_path: str
    """Static page that renders the layer's catalog view."""


LAYERS: dict[str, HarnessLayer] = {
    "persona": HarnessLayer(
        key="persona",
        label="Persona",
        color="#a855f7",
        short_desc="40-year anti-trafficking expert persona.",
        description=(
            "Persona system prompt loaded into the model context. The "
            "default 40-year anti-trafficking expert persona is "
            "user-replaceable via the curator-block library and "
            "persists in localStorage between sessions."
        ),
        viewer_path="/static/persona.html",
    ),
    "grep": HarnessLayer(
        key="grep",
        label="GREP",
        color="#ef4444",
        short_desc="Hand-curated regex rules over the prompt.",
        description=(
            "Regex KB across debt bondage, fee camouflage, corridor "
            "caps, ILO indicators, kafala framework, cross-border "
            "loan novation, multi-party / governed-by stripping. Every "
            "rule is tagged with the controlling ILO convention or "
            "national statute, severity, and indicator description; "
            "a hit prepends to the model context with citation + "
            "indicator + match excerpt."
        ),
        viewer_path="/static/grep-rules.html",
    ),
    "rag": HarnessLayer(
        key="rag",
        label="RAG",
        color="#3b82f6",
        short_desc="BM25 retrieval over the curated legal corpus.",
        description=(
            "BM25 (+ optional dense + RRF fusion) over a curated "
            "in-kernel corpus spanning ILO conventions, national "
            "recruitment statutes, and NGO briefs. Citation graph "
            "expands 1-hop neighbors at retrieval time."
        ),
        viewer_path="/static/rag-corpus.html",
    ),
    "imports": HarnessLayer(
        key="imports",
        label="Imports",
        color="#14b8a6",
        short_desc="User-attached evidence (images / docs / posts).",
        description=(
            "Evidence the user attaches to a prompt — recruitment "
            "receipts, contract photos, social-media screenshots — "
            "auto-bound to the model context. The classifier surface "
            "uses the same Imports layer to receive image uploads."
        ),
        viewer_path="/static/harness.html",
    ),
    "tools": HarnessLayer(
        key="tools",
        label="Tools",
        color="#10b981",
        short_desc="Function-calling lookups (corridors / fees / ILO).",
        description=(
            "Function-calling lookups Gemma invokes via its native "
            "tool-call API: corridor fee caps, fee-camouflage decoder, "
            "ILO indicator matcher, NGO intake hotlines, ILO "
            "convention reference. Each tool returns structured JSON."
        ),
        viewer_path="/static/tools.html",
    ),
    "online": HarnessLayer(
        key="online",
        label="Online",
        color="#f59e0b",
        short_desc="Live web search with deep-fetch (BYOK Brave / DDG).",
        description=(
            "Live web search hook: Brave Search API (with BYOK key), "
            "DuckDuckGo HTML fallback, httpx deep-fetch on result "
            "URLs, Wikipedia API fallback. Results are prepended with "
            "a cross-check warning so the model treats them as "
            "candidate evidence requiring URL attribution."
        ),
        viewer_path="/static/online.html",
    ),
}


# Render order — matches the toggle-tile order in the chat UI.
LAYER_ORDER: tuple[str, ...] = ("persona", "grep", "rag", "imports", "tools", "online")


# ---------------------------------------------------------------------------
# RAG corpus jurisdiction grouping
# ---------------------------------------------------------------------------
# Maps a doc-id PREFIX to its jurisdiction group. Used by every surface
# that needs to color-code or filter the corpus: /api/rag/graph,
# /api/harness-catalog/rag, the standalone rag-graph.html and
# rag-corpus.html viewers. Adding a new jurisdiction is one entry here
# and zero code edits everywhere else.
#
# Order matters: longer prefixes first, so `ilo_p` matches before `ilo_c`.


# ---------------------------------------------------------------------------
# Severity palette (used by GREP rules + grader)
# ---------------------------------------------------------------------------
# Centralised here so /static/grep-rules.html, /static/grep-tester.html,
# /static/search.html, and index.html all read the same hex codes.
# Currently the static pages still inline these — but exposing them
# via /api/brand lets a future P1 change make them CSS variables in
# one place.
SEVERITY_PALETTE: dict[str, str] = {
    "critical": "#ef4444",
    "high":     "#f59e0b",
    "medium":   "#3b82f6",
    "low":      "#94a3b8",
    "info":     "#94a3b8",
}


@dataclass(frozen=True)
class Jurisdiction:
    """One row of the RAG-corpus jurisdiction grouping."""

    prefix: str   # doc-id startswith() match (e.g. "ilo_c", "poea_")
    group:  str   # stable id used in API + chips (e.g. "ilo_convention")
    label:  str   # display label (e.g. "ILO Convention")
    color:  str   # hex color for the legend chip + graph node


JURISDICTIONS: tuple[Jurisdiction, ...] = (
    Jurisdiction("ilo_p",   "ilo_protocol",   "ILO Protocol",        "#a855f7"),
    Jurisdiction("ilo_c",   "ilo_convention", "ILO Convention",      "#7c3aed"),
    Jurisdiction("poea_",   "poea",           "POEA / PH",           "#10b981"),
    Jurisdiction("ra_",     "ph_ra",          "PH RA Statute",       "#059669"),
    Jurisdiction("bp2mi_",  "bp2mi",          "BP2MI / Indonesia",   "#0891b2"),
    Jurisdiction("nepal_",  "nepal",          "Nepal FEA",           "#0e7490"),
    Jurisdiction("bd_",     "bangladesh",     "Bangladesh OEA",      "#0d9488"),
    Jurisdiction("hk_",     "hk",             "Hong Kong",           "#3b82f6"),
    Jurisdiction("sg_",     "sg",             "Singapore",           "#1d4ed8"),
    Jurisdiction("uae_",    "uae",            "UAE",                 "#1e3a8a"),
    Jurisdiction("difc_",   "uae",            "UAE",                 "#1e3a8a"),
    Jurisdiction("saudi_",  "ksa",            "Saudi Arabia",        "#0c4a6e"),
    Jurisdiction("kuwait_", "kuwait",         "Kuwait",              "#1e40af"),
    Jurisdiction("lebanon_","lebanon",        "Lebanon",             "#3730a3"),
    Jurisdiction("palermo_","palermo",        "Palermo Protocol",    "#db2777"),
    Jurisdiction("icrmw_",  "icrmw",          "UN ICRMW",            "#be185d"),
    Jurisdiction("hague_",  "hague",          "Hague Convention",    "#86198f"),
    Jurisdiction("eu_",     "eu",             "EU Directive",        "#dc2626"),
    Jurisdiction("coe_",    "coe",            "Council of Europe",   "#b91c1c"),
    Jurisdiction("asean_",  "asean",          "ASEAN ACTIP",         "#9d174d"),
    Jurisdiction("uncrc_",  "uncrc",          "UNCRC",               "#f59e0b"),
    Jurisdiction("cedaw_",  "cedaw",          "CEDAW",               "#d97706"),
    Jurisdiction("who_",    "who",            "WHO Code",            "#16a34a"),
    Jurisdiction("pacific_","pacific",        "Pacific Framework",   "#06b6d4"),
    Jurisdiction("bali_",   "bali",           "Bali Process",        "#0284c7"),
    Jurisdiction("fatf_",   "fatf",           "FATF Recommendation", "#475569"),
    Jurisdiction("ijm_",    "ngo",            "NGO Brief (IJM)",     "#64748b"),
    Jurisdiction("polaris_","ngo",            "NGO Brief (Polaris)", "#64748b"),
)


# Doc-ids that don't fit a prefix-based jurisdiction but are recognisable
# as cross-cutting "pattern brief" entries (analytical, not jurisdictional).
PATTERN_BRIEF_IDS: frozenset[str] = frozenset({
    "digital_fee_collection_qr_wallets",
    "side_letters_two_contract_deception",
    "substance_over_form_general",
})


_OTHER = ("other", "Other", "#94a3b8")
_PATTERN_BRIEF = ("pattern_brief", "Pattern Brief", "#7c3aed")


def classify_doc(doc_id: str) -> tuple[str, str, str]:
    """Resolve a doc-id to (group_id, group_label, color).

    Single source of truth for how a corpus document gets bucketed
    on every UI surface. The fallback is the grey "Other" group, but
    the canonical 46-doc corpus has 0 docs in Other (Pattern Brief
    catches the cross-cutting analytical entries).
    """
    if doc_id in PATTERN_BRIEF_IDS:
        return _PATTERN_BRIEF
    for j in JURISDICTIONS:
        if doc_id.startswith(j.prefix):
            return (j.group, j.label, j.color)
    return _OTHER


def jurisdiction_groups() -> dict[str, dict[str, str]]:
    """Return the {group_id: {label, color}} legend dict — what
    /api/rag/graph and /api/harness-catalog/rag both expose to the
    frontend. Includes Pattern Brief and Other so the legend is
    complete even when 0 docs land in those buckets.
    """
    out: dict[str, dict[str, str]] = {}
    for j in JURISDICTIONS:
        out[j.group] = {"label": j.label, "color": j.color}
    out[_PATTERN_BRIEF[0]] = {"label": _PATTERN_BRIEF[1], "color": _PATTERN_BRIEF[2]}
    out[_OTHER[0]] = {"label": _OTHER[1], "color": _OTHER[2]}
    return out


# ---------------------------------------------------------------------------
# Refusal / pre-context copy text used by the harness
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CopyText:
    """User-facing copy strings grouped by site."""

    privacy_promise: str = PRIVACY_PROMISE
    grade_modes_intro: str = (
        "4 grade modes: Universal (deterministic, ~2s), Expert "
        "(legacy per-category), Evaluator (LLM-as-judge), Combined "
        "(50/50 Universal + Evaluator with disagreement panel)."
    )
    rubric_label_template: str = (
        "{n_dims}-dimension rubric ({version})"
    )
    audience_buckets: tuple[str, ...] = (
        "model_capability",
        "enterprise_moderation",
        "ngo_intake",
        "individual_query",
        "research",
        "image_prompts",
        "data_intelligence",
        "regulator_audit",
    )


COPY = CopyText()


# ---------------------------------------------------------------------------
# Serialization for /api/brand
# ---------------------------------------------------------------------------


def to_dict() -> dict:
    """Serialize all brand metadata for the /api/brand endpoint.

    Frontend pages can fetch this once at load time and avoid
    hardcoding any of the values that live here.
    """
    return {
        "product": {
            "name":            PRODUCT_NAME,
            "tagline":         PRODUCT_TAGLINE,
            "privacy_promise": PRIVACY_PROMISE,
            "named_for":       NAMED_FOR,
        },
        "versions": {
            "chat_package":        chat_package_version(),
            "wire_format":         WIRE_FORMAT_VERSION,
        },
        "layers": [asdict(LAYERS[k]) for k in LAYER_ORDER],
        "severity_palette": dict(SEVERITY_PALETTE),
        "extras": [
            # Card-style entries that aren't formal harness layers
            # but still surface in /static/harness.html. Keep this
            # list here so adding a new viewer page is a one-file
            # edit (no code-edit in harness.html required).
            {
                "key":         "rag",
                "label":       "RAG GRAPH",
                "color":       LAYERS["rag"].color,
                "viewer_path": "/static/rag-graph.html",
                "short_desc":  "Force-directed view of the citation graph (different angle on RAG).",
            },
            {
                "key":         "grep",
                "label":       "LIVE TESTER",
                "color":       LAYERS["grep"].color,
                "viewer_path": "/static/grep-tester.html",
                "short_desc":  "Paste any text — see which GREP rules fire. No LLM call. Tangible in 30 seconds.",
            },
            {
                "key":         "persona",
                "label":       "SEARCH",
                "color":       LAYERS["persona"].color,
                "viewer_path": "/static/search.html",
                "short_desc":  "Cross-layer search across persona / GREP / RAG / tools.",
            },
            {
                "key":         "tools",
                "label":       "HOTLINES",
                "color":       LAYERS["tools"].color,
                "viewer_path": "/static/hotlines.html",
                "short_desc":  "Searchable directory of regulators, NGOs, embassies, hotlines. The user submits — we never auto-send.",
            },
        ],
        "copy": asdict(COPY),
    }


__all__ = [
    "PRODUCT_NAME",
    "PRODUCT_TAGLINE",
    "PRIVACY_PROMISE",
    "NAMED_FOR",
    "WIRE_FORMAT_VERSION",
    "chat_package_version",
    "HarnessLayer",
    "LAYERS",
    "LAYER_ORDER",
    "CopyText",
    "COPY",
    "to_dict",
]
