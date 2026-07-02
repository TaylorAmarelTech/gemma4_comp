"""Shared text-cleanup helpers for user-facing fact / share / search
output.

Any handler that emits a value the reviewer or NGO partner will read —
an evidence_quote, source_excerpt, snippet, summary, text_preview,
non_pii_example, test_phrase, or any other prose-shaped field — should
route the value through `clean_for_knowledge_fact()` before serializing
it. The shared scrub removes operational kernel metadata (run IDs,
/kaggle/working/... paths, ZIP / JSONL / JSON / TAR filenames, synthetic
case folder names like DC-PH-HK-101_Ana_Cruz/...) that ships with
upstream process-bundle summaries and would otherwise leak the staging
filenames of synthetic demo cases into a fact reviewers think is generic.

Use `fact_excerpt(text, limit)` whenever you need a length-capped
excerpt of cleaned text. It picks a sentence boundary so quotes don't
trail off mid-word.

Use `smart_excerpt(text, limit)` for content that is NOT a knowledge
fact but still benefits from a sentence-boundary cut — for example
external web-search snippets, where you want the cleaner cut but should
NOT scrub kernel-metadata patterns (because the patterns are about our
synthetic case data, not the broader web).

`clean_for_knowledge_fact` is idempotent: clean(clean(x)) == clean(x).
"""
from __future__ import annotations

import re as _re

# Operational noise that should never appear in a saved knowledge fact
# or a shareable envelope. Each pattern matches a class of kernel-internal
# string that upstream process-bundle summaries ship into the text
# fields of envelopes that downstream UIs (knowledge.html, search.html,
# share.html, graph-chat synthesis) render as if it were anonymized
# pattern prose.
_KNOWLEDGE_NOISE_PATTERNS = [
    # Kernel run IDs: "RUN_ID: process_dad7c52a7a15"
    _re.compile(r"\bRUN[_ ]?ID\s*[:=]\s*\S+", _re.I),
    # Bare job IDs: "process_dad7c52a7a15"
    _re.compile(r"\bprocess_[a-f0-9]{8,}", _re.I),
    # Kaggle / Linux workspace paths anchored at start or whitespace
    # so we consume any leading slash and don't leave an orphan "/".
    _re.compile(
        r"(?:^|(?<=\s))/?(?:kaggle/working|kaggle/input|tmp|home/[\w-]+)/\S+"
    ),
    # Bare data filenames: foo.zip, audit.tar, messages.jsonl, etc.
    _re.compile(r"\b[\w./-]+\.(?:zip|tar|tgz|gz|json|jsonl)\b", _re.I),
    # Synthetic case-corpus folders
    _re.compile(r"\bmedia_rich_cases/\S+"),
    _re.compile(r"\bcase_files_\S+"),
    _re.compile(r"\bprocess[_-]staging\S*", _re.I),
    # Synthetic case folder names: DC-PH-HK-101_Ana_Cruz/messages.jsonl
    _re.compile(r"\bDC[-_][A-Z]{2}[-_][A-Z]{2}[-_]\d+_[A-Za-z][\w-]*\S*"),
]
_NOISE_REPLACEMENT = "[case material]"


def clean_for_knowledge_fact(text: str | None) -> str:
    """Remove kernel run paths, ZIP names, synthetic case folder names,
    and job IDs from text. Returns prose suitable for embedding in a
    public-facing envelope field."""
    if not text:
        return ""
    cleaned = str(text)
    for pat in _KNOWLEDGE_NOISE_PATTERNS:
        cleaned = pat.sub(_NOISE_REPLACEMENT, cleaned)
    # Collapse runs of the replacement token and excess whitespace so
    # the cleaned text reads as continuous prose.
    cleaned = _re.sub(
        r"(?:\[case material\]\s*){2,}", "[case material] ", cleaned
    )
    cleaned = _re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _smart_cut(text: str, limit: int) -> str:
    """Length-cap `text` at `limit` chars, preferring a sentence /
    clause boundary so the result reads as a self-contained statement
    instead of a mid-word slice."""
    if not text or len(text) <= limit:
        return text or ""
    head = text[:limit]
    min_boundary = max(8, int(limit * 0.30))
    for sep in (". ", "? ", "! ", "; ", ", "):
        idx = head.rfind(sep)
        if idx >= min_boundary:
            return head[: idx + 1].strip()
    idx = head.rfind(" ")
    if idx >= int(limit * 0.55):
        return head[:idx].strip()
    return head.strip()


def fact_excerpt(text: str | None, limit: int) -> str:
    """Cleaned + length-capped + boundary-aware excerpt. Use for any
    field that ends up in a fact-shaped envelope (evidence_quote,
    source_excerpt, non_pii_example, test_phrase). Strips kernel
    metadata before truncating."""
    cleaned = clean_for_knowledge_fact(text)
    return _smart_cut(cleaned, limit)


def smart_excerpt(text: str | None, limit: int) -> str:
    """Length-capped + boundary-aware excerpt WITHOUT noise scrubbing.
    Use for external content (web search snippets, third-party
    descriptions) where the cleaner cut is welcome but the kernel
    metadata patterns don't apply."""
    return _smart_cut(text or "", limit)


def was_scrubbed(original: str | None, cleaned: str | None) -> bool:
    """True if `cleaned` differs in length from `original`, i.e. the
    scrub removed something. Useful for surfacing a
    `noise_scrubbed_before_gemma` provenance flag."""
    if original is None or cleaned is None:
        return False
    return len(original) != len(cleaned)


# ---------------------------------------------------------------------
# Standardized fact-envelope shape
# ---------------------------------------------------------------------
#
# Every page that drafts a knowledge object (search, share, knowledge,
# process graph chat) historically used slightly different field names
# and field orders. A reviewer scanning the workbench saw
# `evidence_quote` on one page, `source_excerpt` on another,
# `non_pii_example` on a third — same idea, different label. That makes
# bulk review slower and looks unfinished in the demo.
#
# `standardize_fact_envelope()` is the single chokepoint: every draft
# envelope goes through it before the UI renders it. The result is a
# dict with predictable keys in a predictable order, all string values
# scrubbed of kernel metadata, indicators / corridors / stages
# normalized to the canonical vocabulary the GREP rules + benchmark
# already use.

# Canonical key order for fact-shaped envelopes. The renderer iterates
# this list so every page shows fields in the same sequence.
STANDARD_FACT_KEY_ORDER: tuple[str, ...] = (
    "fact_type",
    "fact_summary",
    "pattern_name",
    "indicators",
    "corridors",
    "journey_stage",
    "entity_names",
    "entity_type",
    "amount",
    "currency",
    "locations",
    "evidence_quote",
    "source_excerpt",
    "non_pii_example",
    "test_phrases",
    "false_positive_notes",
    "response_guidance",
    "confidence_0_10",
    "share_scope",
    "aggregation_keys",
    "citation_ids",
    "applicable_corridors",
    "applies_to_indicators",
    "applies_to_corridors",
    "stages",
    "related_fact_types",
    "chart_dimensions",
    "fields",
    "label",
    "question",
    "scale",
    "weight",
    "title",
    "jurisdiction",
    "source_url",
    "name",
    "phone",
    "email",
    "url",
    "verification_note",
    "text",
    "category",
    "severity",
    "pattern",
    "description",
    "generalized_pattern",
    "pii_status",
    "source_context",
)

# Canonical ILO indicator vocabulary. Drafts arriving with synonyms
# (e.g. "feeBondage", "fee-bondage", "FeeCamouflage") are normalized to
# the matching member here so chart filters and aggregation keys line
# up across pages. Kept lower_snake_case to match the rest of the
# codebase.
STANDARD_FACT_INDICATORS: tuple[str, ...] = (
    "fee_camouflage",
    "fee_bondage",
    "salary_deduction",
    "wage_assignment",
    "debt_bondage",
    "passport_retention",
    "document_control",
    "retaliation_risk",
    "jurisdiction_shopping",
    "wage_theft",
    "deceptive_recruitment",
    "movement_restriction",
    "isolation",
    "abuse_of_vulnerability",
    "excessive_overtime",
    "withheld_wages",
    "case_signal",
)

# Canonical journey-stage vocabulary.
STANDARD_FACT_STAGES: tuple[str, ...] = (
    "recruitment",
    "training",
    "payment_and_debt",
    "departure",
    "transit",
    "arrival_and_placement",
    "employment",
    "exit",
    "post_return",
)

_INDICATOR_ALIASES: dict[str, str] = {
    "feebondage": "fee_bondage",
    "fee-bondage": "fee_bondage",
    "fee_bondage": "fee_bondage",
    "fee_camouflage": "fee_camouflage",
    "feecamouflage": "fee_camouflage",
    "fee-camouflage": "fee_camouflage",
    "salarydeduction": "salary_deduction",
    "salary-deduction": "salary_deduction",
    "salary_deduction": "salary_deduction",
    "wage assignment": "wage_assignment",
    "wageassignment": "wage_assignment",
    "wage-assignment": "wage_assignment",
    "wage_assignment": "wage_assignment",
    "debtbondage": "debt_bondage",
    "debt-bondage": "debt_bondage",
    "debt_bondage": "debt_bondage",
    "passport": "passport_retention",
    "passportretention": "passport_retention",
    "passport-retention": "passport_retention",
    "passport_retention": "passport_retention",
    "documentconfiscation": "passport_retention",
    "document-confiscation": "passport_retention",
    "document_confiscation": "passport_retention",
    "retentionofdocuments": "passport_retention",
    "retention-of-documents": "passport_retention",
    "retention_of_documents": "passport_retention",
    "retentionofidentitydocuments": "passport_retention",
    "retention-of-identity-documents": "passport_retention",
    "retention_of_identity_documents": "passport_retention",
    "doccontrol": "document_control",
    "document-control": "document_control",
    "document_control": "document_control",
    "retaliation": "retaliation_risk",
    "retaliation-risk": "retaliation_risk",
    "retaliation_risk": "retaliation_risk",
    "jurisdictionshopping": "jurisdiction_shopping",
    "jurisdiction-shopping": "jurisdiction_shopping",
    "jurisdiction_shopping": "jurisdiction_shopping",
    "wagetheft": "wage_theft",
    "wage-theft": "wage_theft",
    "wage_theft": "wage_theft",
    "deceptiverecruitment": "deceptive_recruitment",
    "deceptive-recruitment": "deceptive_recruitment",
    "deceptive_recruitment": "deceptive_recruitment",
    "deception": "deceptive_recruitment",
    "contract substitution": "deceptive_recruitment",
    "contractsubstitution": "deceptive_recruitment",
    "contract-substitution": "deceptive_recruitment",
    "contract_substitution": "deceptive_recruitment",
    "movementrestriction": "movement_restriction",
    "movement-restriction": "movement_restriction",
    "movement_restriction": "movement_restriction",
    "restrictionofmovement": "movement_restriction",
    "restriction-of-movement": "movement_restriction",
    "restriction_of_movement": "movement_restriction",
    "withheld wages": "withheld_wages",
    "withheldwages": "withheld_wages",
    "withheld-wages": "withheld_wages",
    "withheld_wages": "withheld_wages",
    "withholding of wages": "withheld_wages",
    "withholdingofwages": "withheld_wages",
    "withholding wages": "withheld_wages",
    "withholdingwages": "withheld_wages",
    "withholding_wages": "withheld_wages",
    "withholding-of-wages": "withheld_wages",
    "withholding_of_wages": "withheld_wages",
    "wage withholding": "withheld_wages",
    "wagewithholding": "withheld_wages",
    "wage-withholding": "withheld_wages",
    "wage_withholding": "withheld_wages",
}


def _normalize_indicator(value: str) -> str | None:
    """Map an indicator string (any case, hyphens, camelCase) to the
    canonical lower_snake_case form. Returns None if the value doesn't
    match any known indicator (caller should drop it)."""
    if not value:
        return None
    key = _re.sub(r"\s+", "", str(value).strip()).lower()
    if not key:
        return None
    if key in _INDICATOR_ALIASES:
        return _INDICATOR_ALIASES[key]
    if key in STANDARD_FACT_INDICATORS:
        return key
    return None


def normalize_fact_indicator(value: str | None) -> str | None:
    """Public wrapper for canonical indicator normalization.

    Template selection, saved envelopes, and free-prose normalization should
    all use the same curated indicator vocabulary and aliases.
    """
    return _normalize_indicator(str(value or ""))


_STAGE_ALIASES: dict[str, str] = {
    "recruit": "recruitment",
    "recruitment": "recruitment",
    "training": "training",
    "payment": "payment_and_debt",
    "payment_and_debt": "payment_and_debt",
    "debt": "payment_and_debt",
    "departure": "departure",
    "transit": "transit",
    "arrival": "arrival_and_placement",
    "arrival_and_placement": "arrival_and_placement",
    "placement": "arrival_and_placement",
    "employment": "employment",
    "work": "employment",
    "exit": "exit",
    "post_return": "post_return",
    "return": "post_return",
}


def _normalize_stage(value: str) -> str | None:
    if not value:
        return None
    key = _re.sub(r"\s+", "_", str(value).strip()).lower()
    if not key:
        return None
    return _STAGE_ALIASES.get(key) or (
        key if key in STANDARD_FACT_STAGES else None
    )


def _normalize_corridor(value: str) -> str | None:
    """Corridors are uppercase two-letter pairs joined by a hyphen
    (PH-HK, ID-MY, BD-LB). Accept lowercase / spaced variants."""
    if not value:
        return None
    s = _re.sub(r"\s+", "", str(value).upper())
    m = _re.match(r"^([A-Z]{2})[-_/]([A-Z]{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def _inline_token_pattern(token: str) -> _re.Pattern[str]:
    return _re.compile(
        r"(?<![A-Za-z0-9_])" + _re.escape(token) + r"(?![A-Za-z0-9_])",
        _re.I,
    )


def normalize_inline_vocabulary(text: str | None) -> str:
    """Canonicalize known indicator, corridor, and stage terms inside
    free prose without changing surrounding words.

    This is intentionally separate from clean_for_knowledge_fact() and
    standardize_fact_envelope(): graph-chat synthesis is not an envelope,
    but reviewers should still see the same vocabulary strings that
    saved envelopes and filters use.
    """
    if not text:
        return ""
    out = str(text)

    indicator_aliases = sorted(
        _INDICATOR_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, canonical in indicator_aliases:
        out = _inline_token_pattern(alias).sub(canonical, out)

    stage_aliases = sorted(
        _STAGE_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, canonical in stage_aliases:
        out = _inline_token_pattern(alias).sub(canonical, out)

    def _corridor_repl(match: _re.Match[str]) -> str:
        return _normalize_corridor(match.group(0)) or match.group(0)

    return _re.sub(
        r"(?<![A-Za-z0-9])(?:[A-Z]{2})[-_/](?:[A-Z]{2})(?![A-Za-z0-9])",
        _corridor_repl,
        out,
        flags=_re.I,
    )


# Fields that get scrubbed but not truncated (short labels/titles).
_SHORT_STR_FIELDS: frozenset[str] = frozenset({
    "fact_type", "fact_summary", "pattern_name", "label", "title",
    "name", "category", "severity", "journey_stage",
    "share_scope", "pii_status", "source_context",
    "entity_type", "jurisdiction", "verification_note",
    "description", "false_positive_notes", "response_guidance",
    "question", "scale", "currency",
})
# Long prose fields: scrubbed + boundary-truncated.
_LONG_PROSE_FIELDS: frozenset[str] = frozenset({
    "evidence_quote", "source_excerpt", "non_pii_example",
    "generalized_pattern", "text", "pattern",
})


def _scrub_nested(value):
    """Recursively apply clean_for_knowledge_fact to every string leaf inside
    lists and dicts so structured fields (citation_ids, entity_names, etc.)
    satisfy the same noise-scrub contract as plain string fields. Non-string
    scalars pass through unchanged."""
    if isinstance(value, str):
        return clean_for_knowledge_fact(value)
    if isinstance(value, list):
        return [_scrub_nested(item) for item in value]
    if isinstance(value, dict):
        return {k: _scrub_nested(v) for k, v in value.items()}
    return value


def standardize_fact_envelope(
    content: dict | None,
    target_type: str,
    *,
    excerpt_limit: int = 500,
) -> dict:
    """Return a re-shaped copy of `content` so every fact-shaped
    envelope across the workbench uses the same field names, field
    ordering, and vocabulary.

    What it does:
      - Scrubs every string value through clean_for_knowledge_fact()
      - Truncates the long prose fields at a sentence boundary via
        fact_excerpt()
      - Normalizes `indicators` / `applies_to_indicators` /
        `signal_types` against the canonical indicator vocabulary
        (drops unknowns; lower_snake_cases known ones)
      - Normalizes `corridor` / `corridors` / `applicable_corridors`
        to the `XX-YY` form
      - Normalizes `journey_stage` / `stages` to the canonical vocab
      - Re-orders keys per STANDARD_FACT_KEY_ORDER (unknown keys go
        at the end, in their original order)

    Idempotent: standardize(standardize(x, t), t) == standardize(x, t).
    Unknown target_types pass through with key reorder + scrub only."""
    if not isinstance(content, dict):
        return {}

    out: dict = {}
    for k, v in content.items():
        if v is None:
            out[k] = None
            continue
        # ORDER MATTERS: vocab-specific branches must come BEFORE the
        # generic short/long string branches, otherwise `journey_stage`
        # gets dropped into the short-string branch and never reaches
        # the stage normalizer.
        if k in {"indicators", "applies_to_indicators", "signal_types"} and isinstance(v, list):
            seen: list[str] = []
            for item in v:
                norm = _normalize_indicator(str(item))
                if norm and norm not in seen:
                    seen.append(norm)
            out[k] = seen
        elif k in {"corridors", "applicable_corridors", "applies_to_corridors"} and isinstance(v, list):
            seen2: list[str] = []
            for item in v:
                norm = _normalize_corridor(str(item))
                if norm and norm not in seen2:
                    seen2.append(norm)
            out[k] = seen2
        elif k == "corridor" and isinstance(v, str):
            normalized = _normalize_corridor(v) or ""
            out[k] = normalized
        elif k == "journey_stage" and isinstance(v, str):
            out[k] = _normalize_stage(v) or v
        elif k == "stages" and isinstance(v, list):
            seen3: list[str] = []
            for item in v:
                norm = _normalize_stage(str(item))
                if norm and norm not in seen3:
                    seen3.append(norm)
            out[k] = seen3
        elif k == "test_phrases" and isinstance(v, list):
            out[k] = [
                fact_excerpt(str(p), 200)
                for p in v if str(p).strip()
            ]
        elif k in _SHORT_STR_FIELDS and isinstance(v, str):
            out[k] = clean_for_knowledge_fact(v)
        elif k in _LONG_PROSE_FIELDS and isinstance(v, str):
            out[k] = fact_excerpt(v, excerpt_limit)
        elif isinstance(v, str):
            # Conservative default: scrub any remaining string field
            # too. Nothing in the canonical schema should ship a path
            # or RUN_ID.
            out[k] = clean_for_knowledge_fact(v)
        else:
            # Recursively scrub strings nested inside lists/dicts (e.g.
            # citation_ids, related_fact_types, entity_names dicts) so the
            # "every string value is scrubbed" contract holds for structured
            # fields too — a /kaggle/working/... path or RUN_ID buried one
            # level down must not bypass the noise scrub. Ints/floats/bools
            # pass through unchanged.
            out[k] = _scrub_nested(v)

    # Re-order keys: canonical first (in STANDARD_FACT_KEY_ORDER), then
    # unknown keys in their original order.
    canonical_present = [k for k in STANDARD_FACT_KEY_ORDER if k in out]
    unknown = [k for k in out if k not in STANDARD_FACT_KEY_ORDER]
    final: dict = {}
    for k in canonical_present:
        final[k] = out[k]
    for k in unknown:
        final[k] = out[k]
    return final


def standardize_envelope_extensions(
    extensions: dict | None,
    *,
    scrubbed: bool | None = None,
    polished_passes: int | None = None,
) -> dict:
    """Normalize the `extensions` dict on a draft envelope so every
    surface uses the same provenance keys. Adds the supplied scrub +
    polish flags when given; leaves existing keys intact otherwise."""
    out: dict = dict(extensions or {})
    if scrubbed is not None:
        out["noise_scrubbed_before_gemma"] = bool(scrubbed)
    if polished_passes is not None and polished_passes > 0:
        out["polished_by_gemma"] = True
        out["polish_passes"] = int(polished_passes)
    return out
